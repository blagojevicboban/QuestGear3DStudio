import cv2
import numpy as np

def yuv_to_rgb(yuv_image):
    """
    Convert YUV420 image to RGB.
    Assumes standard NV12 or similar format if coming from Android Camera2 API via Quest.
    """
    if yuv_image is None:
        return None
    # Depending on exact format (NV12 vs NV21), this might need adjustment.
    # Standard OpenCV conversion:
    rgb_image = cv2.cvtColor(yuv_image, cv2.COLOR_YUV2RGB_NV12)
    return rgb_image

def apply_intrinsics(image, intrinsics, distortion_coeffs):
    """
    Undistort image using camera intrinsics.
    intrinsics: 3x3 cameramatrix
    distortion_coeffs: 1x5 or 1x8 vector
    """
    h, w = image.shape[:2]
    new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(intrinsics, distortion_coeffs, (w, h), 1, (w, h))
    undistorted_img = cv2.undistort(image, intrinsics, distortion_coeffs, None, new_camera_matrix)
    return undistorted_img

def filter_depth(depth_map, check_val=0.0):
    """
    Apply filtering to depth map to remove noise.
    Using simple bilateral filter for now.
    """
    if depth_map is None:
        return None
        
    # Convert to float32 for processing if needed
    depth_float = depth_map.astype(np.float32)
    
    # Bilateral filter needs 8-bit or 32-bit float
    filtered_depth = cv2.bilateralFilter(depth_float, 5, 50, 50)
    
    return filtered_depth
