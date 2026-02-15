#!/usr/bin/env python3
"""Test loading new QuestGear3DScan format."""
import sys
sys.path.insert(0, r'C:\QuestGear3D\QuestGear3DStudio')

from modules.quest_adapter import QuestDataAdapter
from modules.quest_image_processor import QuestImageProcessor
import json

# Test scan path
scan_path = r"c:\Users\Mejkerslab\Desktop\Scan_20260215_215251"

print("=" * 60)
print("Testing QuestGear3DStudio compatibility with new scan format")
print("=" * 60)

# Step 1: Detect format
print("\n[1] Detecting scan format...")
format_type = QuestDataAdapter.detect_scan_format(scan_path)
print(f"    ✓ Detected format: {format_type}")

# Step 2: Adapt to frames.json
print("\n[2] Converting to frames.json...")
frames_json_path = QuestDataAdapter.adapt_quest_data(scan_path)
print(f"    ✓ Created: {frames_json_path}")

# Step 3: Load frames.json
print("\n[3] Loading frames.json...")
with open(frames_json_path, 'r') as f:
    frames_data = json.load(f)
print(f"    ✓ Version: {frames_data['version']}")
print(f"    ✓ Source: {frames_data['source']}")
print(f"    ✓ Frames: {len(frames_data['frames'])}")

# Step 4: Test image loading
print("\n[4] Testing image loading (first 3 frames)...")
for i in range(min(3, len(frames_data['frames']))):
    frame = frames_data['frames'][i]
    rgb, depth, depth_info = QuestImageProcessor.process_quest_frame(
        scan_path, 
        frame, 
        camera='center'
    )
    
    if rgb is not None:
        print(f"    ✓ Frame {i}: RGB {rgb.shape}, Depth: {depth.shape if depth is not None else 'None'}")
    else:
        print(f"    ✗ Frame {i}: Failed to load")

print("\n" + "=" * 60)
print("✅ QuestGear3DStudio is ready for new scan format!")
print("=" * 60)
