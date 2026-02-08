
import os
import numpy as np
import struct
from pathlib import Path

def inspect_depth(directory):
    print(f"Scanning {directory}...")
    files = list(Path(directory).rglob("*.raw"))
    if not files:
        print("No .raw files found.")
        return

    target = files[0]
    print(f"Inspecting: {target}")
    
    with open(target, 'rb') as f:
        data = f.read()
    
    # Assume float32
    arr = np.frombuffer(data, dtype=np.float32)
    
    print(f"Count: {len(arr)}")
    print(f"Min: {np.min(arr)}")
    print(f"Max: {np.max(arr)}")
    print(f"Mean: {np.mean(arr)}")
    
    # Check for NaN/Inf
    print(f"NaNs: {np.isnan(arr).sum()}")
    print(f"Infs: {np.isinf(arr).sum()}")

if __name__ == "__main__":
    # inspect default extraction folder if possible, or ask user
    # For now, let's look in current dir or recursively in D:\METAQUEST if accessible
    # But I can't access D: easily without knowing path.
    # I'll check 'frames.json' to find path.
    import json
    if os.path.exists("frames.json"):
        with open("frames.json") as f:
            data = json.load(f)
            first_frame = data['frames'][0]
            depth_rel = first_frame['cameras']['left']['depth']
            if depth_rel:
                # frames.json usually in project dir.
                # But where is the project dir?
                # The user ran the app on a folder.
                pass
    
    # Try to find any .raw file in current directory or subdirs
    inspect_depth(".")
