
import torch
import cv2
import numpy as np
import os
import ssl

# Fix for SSL: CERTIFICATE_VERIFY_FAILED
ssl._create_default_https_context = ssl._create_unverified_context
# Fix for SSL: CERTIFICATE_VERIFY_FAILED
ssl._create_default_https_context = ssl._create_unverified_context

try:
    import onnxruntime as ort
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False

class DepthEstimator:
    def __init__(self, model_type="MiDaS_small", use_gpu=True, backend="auto"):
        """
        Initialize MiDaS depth estimator.
        backend: "auto", "cuda", "directml", "cpu"
        """
        self.model_type = model_type
        self.backend = backend
        
        # Decide device and provider
        self.ort_session = None
        self.torch_device = None
        
        if backend == "auto":
            if torch.cuda.is_available():
                self.backend = "cuda"
            elif HAS_ONNX and 'DmlExecutionProvider' in ort.get_available_providers():
                self.backend = "directml"
            else:
                self.backend = "cpu"
                
        print(f"[DepthEstimator] Initializing with backend: {self.backend}")
        
        if self.backend == "directml" or self.backend == "onnx_cpu":
            self._init_onnx()
        else:
            self._init_torch()

    def _init_torch(self):
        self.torch_device = torch.device("cuda" if self.backend == "cuda" else "cpu")
        print(f"[DepthEstimator] Loading {self.model_type} on Torch ({self.torch_device})...")
        self.model = torch.hub.load("intel-isl/MiDaS", self.model_type)
        self.model.to(self.torch_device)
        self.model.eval()
        
        midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
        if self.model_type in ["DPT_Large", "DPT_Hybrid"]:
            self.transform = midas_transforms.dpt_transform
        else:
            self.transform = midas_transforms.small_transform

    def _init_onnx(self):
        # We need an ONNX file. If not exists, export it once using torch
        onnx_path = os.path.join(os.path.dirname(__file__), f"{self.model_type}.onnx")
        
        if not os.path.exists(onnx_path):
            print(f"[DepthEstimator] Exporting {self.model_type} to ONNX (one-time setup)...")
            self._export_to_onnx(onnx_path)
            
        providers = ['DmlExecutionProvider', 'CPUExecutionProvider'] if self.backend == "directml" else ['CPUExecutionProvider']
        self.ort_session = ort.InferenceSession(onnx_path, providers=providers)
        print(f"[DepthEstimator] ONNX Session initialized with providers: {self.ort_session.get_providers()}")
        
        # Manual preprocessing for ONNX (simplified MiDaS small)
        self.input_size = (256, 256) if "small" in self.model_type else (384, 384)

    def _export_to_onnx(self, path):
        model = torch.hub.load("intel-isl/MiDaS", self.model_type)
        model.eval()
        dummy_input = torch.randn(1, 3, 256, 256) if "small" in self.model_type else torch.randn(1, 3, 384, 384)
        torch.onnx.export(model, dummy_input, path, opset_version=11, 
                          input_names=['input'], output_names=['output'],
                          dynamic_axes={'input': {2: 'height', 3: 'width'}, 'output': {2: 'height', 3: 'width'}})

    def estimate_depth(self, image_path_or_array):
        if isinstance(image_path_or_array, str):
            img = cv2.imread(image_path_or_array)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        else:
            img = image_path_or_array

        if self.ort_session:
            return self._estimate_onnx(img)
        else:
            return self._estimate_torch(img)

    def _estimate_onnx(self, img):
        # Preprocess
        h, w = img.shape[:2]
        img_input = cv2.resize(img, self.input_size).astype(np.float32)
        img_input = img_input / 255.0
        img_input = np.transpose(img_input, (2, 0, 1)) # HWC to CHW
        img_input = np.expand_dims(img_input, 0) # NCHW
        
        # Mean/Std normalization (MiDaS values)
        mean = np.array([0.485, 0.456, 0.406]).reshape(1, 3, 1, 1).astype(np.float32)
        std = np.array([0.229, 0.224, 0.225]).reshape(1, 3, 1, 1).astype(np.float32)
        img_input = (img_input - mean) / std
        
        # Run
        outputs = self.ort_session.run(None, {'input': img_input})
        prediction = outputs[0][0]
        
        # Resize to original
        prediction = cv2.resize(prediction, (w, h), interpolation=cv2.INTER_CUBIC)
        return self._normalize(prediction)

    def _estimate_torch(self, img):
        input_batch = self.transform(img).to(self.torch_device)
        with torch.no_grad():
            prediction = self.model(input_batch)
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1), size=img.shape[:2], mode="bicubic", align_corners=False
            ).squeeze()
        return self._normalize(prediction.cpu().numpy())

    def _normalize(self, depth_map):
        depth_min = depth_map.min()
        depth_max = depth_map.max()
        if depth_max - depth_min > 1e-6:
             return (depth_map - depth_min) / (depth_max - depth_min)
        return np.zeros_like(depth_map)

    def hybrid_fill(self, raw_depth, rgb_image):
        """
        Use AI depth to fill holes (zeros) in the raw hardware depth.
        Uses a least-squares fit to scale AI relative depth to hardware meters.
        """
        if raw_depth is None or rgb_image is None:
            return raw_depth
            
        ai_depth = self.estimate_depth(rgb_image) # Normalized 0..1 (usually inverse depth)
        
        # Hardware depth zeros are holes
        mask_valid = (raw_depth > 0.1) & (raw_depth < 10.0)
        mask_holes = (raw_depth <= 0.1) | (raw_depth >= 10.0)
        
        if not np.any(mask_valid):
            return raw_depth # Can't align
            
        # Linear Regression to find Scale and Shift
        # hardware_depth (meters) = A * ai_depth + B
        # Or more accurately for MiDaS: hardware_depth = A * (1/ai_depth) + B if ai_depth is disparity
        # MiDaS small/large returns disparity-like maps.
        
        # We'll use a simple linear fit on the valid overlap
        X = ai_depth[mask_valid]
        Y = raw_depth[mask_valid]
        
        # Solve Y = A*X + B
        # (N,2) matrix with [X, 1]
        A_mat = np.vstack([X, np.ones(len(X))]).T
        m, c = np.linalg.lstsq(A_mat, Y, rcond=None)[0]
        
        # Predict meters for every pixel
        filled_depth = np.copy(raw_depth)
        ai_predicted_meters = m * ai_depth + c
        
        # Apply filling to holes
        filled_depth[mask_holes] = np.clip(ai_predicted_meters[mask_holes], 0.1, 10.0)
        
        return filled_depth

    def save_depth_map(self, depth_map, output_path):
        """
        Save depth map as 16-bit PNG (scaled to 0-65535).
        """
        # Scale to 16-bit
        depth_16bit = (depth_map * 65535).astype(np.uint16)
        cv2.imwrite(output_path, depth_16bit)

if __name__ == "__main__":
    # Test
    print("Testing DepthEstimator...")
    try:
        estimator = DepthEstimator()
        # Create dummy image
        dummy_img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        depth = estimator.estimate_depth(dummy_img)
        print(f"Depth map shape: {depth.shape}, Range: [{depth.min():.4f}, {depth.max():.4f}]")
    except Exception as e:
        print(f"Test failed: {e}")
