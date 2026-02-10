import open3d as o3d
import sys

print(f"Python Version: {sys.version}")
print(f"Open3D Version: {o3d.__version__}")

# Check legacy CUDA support (if compiled with it)
try:
    if o3d.core.cuda.is_available():
        print("Open3D Core CUDA: AVAILABLE")
    else:
        print("Open3D Core CUDA: NOT AVAILABLE")
except AttributeError:
    print("Open3D Core CUDA: Attribute not found (might be older version or CPU only)")

# Attempt to create a CUDA device
try:
    device = o3d.core.Device("CUDA:0")
    print(f"Successfully created CUDA device: {device}")
    
    # Try a small tensor operation
    val = o3d.core.Tensor([1.0], device=device)
    print(f"Test Tensor on CUDA: {val}")
    
except Exception as e:
    print(f"Failed to create/use CUDA device: {e}")
