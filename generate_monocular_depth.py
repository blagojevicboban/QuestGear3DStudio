
import sys
import os
import argparse
import glob
from tqdm import tqdm
import cv2
import numpy as np

# Ensure modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules.monocular_depth import DepthEstimator

def generate_depth_for_scan(scan_folder, model_type="MiDaS_small"):
    """
    Generate monocular depth maps for all images in a scan folder.
    """
    print(f"Processing scan: {scan_folder}")
    
    # 1. Initialize Estimator
    try:
        estimator = DepthEstimator(model_type=model_type)
    except Exception as e:
        print(f"Failed to initialize DepthEstimator: {e}")
        return

    # 2. Find images
    # Support both flat folder and nested 'color' folder
    image_extensions = ["*.jpg", "*.png", "*.jpeg"]
    image_paths = []
    
    # Check 'color' subfolder first (standard QuestGear format)
    color_folder = os.path.join(scan_folder, "color")
    if os.path.exists(color_folder):
        search_path = color_folder
    else:
        search_path = scan_folder
        
    for ext in image_extensions:
        image_paths.extend(glob.glob(os.path.join(search_path, ext)))
        
    if not image_paths:
        print(f"No images found in {search_path}")
        return

    print(f"Found {len(image_paths)} images.")

    # 3. Create output directory
    output_dir = os.path.join(scan_folder, "depth_monocular")
    os.makedirs(output_dir, exist_ok=True)
    
    # 4. Process images
    for img_path in tqdm(image_paths, desc="Estimating Depth"):
        try:
            # Estimate
            depth_map = estimator.estimate_depth(img_path)
            
            # Save
            filename = os.path.basename(img_path)
            name, _ = os.path.splitext(filename)
            output_path = os.path.join(output_dir, f"{name}.png")
            
            estimator.save_depth_map(depth_map, output_path)
            
        except Exception as e:
            print(f"Error processing {img_path}: {e}")

    print(f"Done. Depth maps saved to {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Monocular Depth Maps")
    parser.add_argument("scan_folder", help="Path to the scan folder")
    parser.add_argument("--model", default="MiDaS_small", help="Model type: MiDaS_small or DPT_Large")
    
    args = parser.parse_args()
    
    if os.path.exists(args.scan_folder):
        generate_depth_for_scan(args.scan_folder, args.model)
    else:
        print(f"Folder not found: {args.scan_folder}")
