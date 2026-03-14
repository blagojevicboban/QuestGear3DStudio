
import cv2
import os

path = r"C:\QuestGear3D\SCANS\Scan_20260219_092241\color\frame_000000.jpg"
print(f"Checking path: {path}")
print(f"Exists: {os.path.exists(path)}")
img = cv2.imread(path)
if img is not None:
    print(f"Shape: {img.shape}")
else:
    print("Failed to read image")
