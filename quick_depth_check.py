#!/usr/bin/env python3
"""Quick depth check for new scan."""
import cv2
import numpy as np

d = cv2.imread(r'C:\Users\Mejkerslab\Desktop\Scan_20260215_221412\depth\frame_000000.png', -1)
print(f'Shape: {d.shape}')
print(f'Dtype: {d.dtype}')
print(f'Unique values: {len(np.unique(d))}')
print(f'Min: {d.min()}, Max: {d.max()}')
print(f'All same? {np.all(d == d.flat[0])}')

# Check first 5 frames
for i in range(5):
    path = rf'C:\Users\Mejkerslab\Desktop\Scan_20260215_221412\depth\frame_{i:06d}.png'
    d = cv2.imread(path, -1)
    unique_count = len(np.unique(d))
    all_same = np.all(d == d.flat[0])
    print(f'Frame {i}: Unique={unique_count}, AllSame={all_same}, Value={d.flat[0]}')
