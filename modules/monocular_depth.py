
import torch
import cv2
import numpy as np
import os
import ssl

# Fix for SSL: CERTIFICATE_VERIFY_FAILED
ssl._create_default_https_context = ssl._create_unverified_context

class DepthEstimator:
    def __init__(self, model_type="MiDaS_small", use_gpu=True):
        """
        Initialize MiDaS depth estimator.
        model_type: "MiDaS_small" (faster) or "DPT_Large" (more accurate)
        """
        self.device = torch.device("cuda") if use_gpu and torch.cuda.is_available() else torch.device("cpu")
        print(f"[DepthEstimator] Loading {model_type} on {self.device}...")
        
        # Load MiDaS model from torch hub
        self.model = torch.hub.load("intel-isl/MiDaS", model_type)
        self.model.to(self.device)
        self.model.eval()

        # Load transforms
        midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
        if model_type == "DPT_Large" or model_type == "DPT_Hybrid":
            self.transform = midas_transforms.dpt_transform
        else:
            self.transform = midas_transforms.small_transform
            
        print("[DepthEstimator] Model loaded successfully.")

    def estimate_depth(self, image_path_or_array):
        """
        Estimate depth from a single RGB image.
        Returns normalized depth map (numpy array).
        """
        # Load image
        if isinstance(image_path_or_array, str):
            img = cv2.imread(image_path_or_array)
            if img is None:
                raise ValueError(f"Could not load image at {image_path_or_array}")
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        else:
            img = image_path_or_array

        # Apply transforms
        input_batch = self.transform(img).to(self.device)

        # Inference
        with torch.no_grad():
            prediction = self.model(input_batch)

            # Resize to original resolution
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=img.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze()

        # Output in numpy
        depth_map = prediction.cpu().numpy()
        
        # Normalize to 0..1 for visualization/relative depth
        depth_min = depth_map.min()
        depth_max = depth_map.max()
        if depth_max - depth_min > 1e-6:
             depth_map = (depth_map - depth_min) / (depth_max - depth_min)
        else:
             depth_map = np.zeros_like(depth_map)

        return depth_map

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
