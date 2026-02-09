import numpy as np
from modules.quest_reconstruction_utils import convert_depth_to_linear

def test_depth_conversion():
    print("Testing convert_depth_to_linear...")
    
    # Test case 1: Standard range [0, 1]
    depth_raw = np.array([[0.0, 0.5, 1.0]], dtype=np.float32)
    near = 0.1
    far = 10.0
    
    linear = convert_depth_to_linear(depth_raw, near, far)
    print(f"Standard Input: {depth_raw}")
    print(f"Linear Output: {linear}")
    
    # Test case 2: NaNs and Infs
    depth_bad = np.array([[np.nan, np.inf, -np.inf]], dtype=np.float32)
    linear_bad = convert_depth_to_linear(depth_bad, near, far)
    print(f"Bad Input: {depth_bad}")
    print(f"Linear Output (Sanitized): {linear_bad}")
    
    assert not np.any(np.isnan(linear_bad)), "Output contains NaNs!"
    assert not np.any(np.isinf(linear_bad)), "Output contains Infs!"
    assert np.all(linear_bad >= 0), "Output contains negative values!"
    
    # Test case 3: Out of range [0, 1]
    depth_out = np.array([[-0.5, 1.5, 200.0]], dtype=np.float32)
    linear_out = convert_depth_to_linear(depth_out, near, far)
    print(f"Out-of-range Input: {depth_out}")
    print(f"Linear Output (Clamped): {linear_out}")

    assert not np.any(np.isnan(linear_out)), "Output contains NaNs!"
    
    print("\n✓ All tests passed. Depth conversion is safe.")

if __name__ == "__main__":
    test_depth_conversion()
