"""Quest data format adapter - converts Quest CSV/JSON to frames.json format."""

import json
import csv
import os
import numpy as np
from pathlib import Path


class QuestDataAdapter:
    """Converts Quest 3 camera/pose data to unified frames.json format."""
    
    @staticmethod
    def detect_scan_format(extraction_dir):
        """
        Detect which scan format is used.
        
        Returns:
            'new' - QuestGear3DScan format (scan_data.json + color/depth folders)
            'old' - Legacy format (hmd_poses.csv + camera_raw folders)
        """
        extraction_path = Path(extraction_dir)
        
        # Check for new format indicators
        if (extraction_path / "scan_data.json").exists() or (extraction_path / "transforms.json").exists():
            return 'new'
        
        # Check for old format indicators
        if (extraction_path / "hmd_poses.csv").exists():
            return 'old'
        
        raise ValueError("Unknown scan format - neither scan_data.json nor hmd_poses.csv found")
    
    @staticmethod
    def adapt_quest_data(extraction_dir):
        """
        Convert Quest export format to frames.json.
        Auto-detects format and uses appropriate adapter.
        
        Args:
            extraction_dir: Path to extracted Quest data
            
        Returns:
            Path to generated frames.json
        """
        format_type = QuestDataAdapter.detect_scan_format(extraction_dir)
        
        if format_type == 'new':
            return QuestDataAdapter._adapt_new_format(extraction_dir)
        else:
            return QuestDataAdapter._adapt_old_format(extraction_dir)
    
    @staticmethod
    def _adapt_new_format(extraction_dir):
        """
        Adapt new QuestGear3DScan format (scan_data.json).
        
        Format structure:
        - scan_data.json: Contains frames with poses and file paths
        - transforms.json: NerfStudio format with camera intrinsics
        - color/frame_XXXXXX.jpg: Color images
        - depth/frame_XXXXXX.png: Depth maps (16-bit PNG)
        """
        extraction_path = Path(extraction_dir)
        
        # Try to load scan_data.json first
        scan_data_file = extraction_path / "scan_data.json"
        transforms_file = extraction_path / "transforms.json"
        
        if scan_data_file.exists():
            with open(scan_data_file, 'r') as f:
                scan_data = json.load(f)
        else:
            raise FileNotFoundError("scan_data.json not found in new format scan")
        
        # Load camera intrinsics from transforms.json if available
        camera_metadata = {}
        if transforms_file.exists():
            with open(transforms_file, 'r') as f:
                transforms = json.load(f)
                camera_metadata = {
                    'intrinsic': {
                        'width': transforms.get('w', 1280),
                        'height': transforms.get('h', 720),
                        'fx': transforms.get('fl_x', 300.0),
                        'fy': transforms.get('fl_y', 300.0),
                        'cx': transforms.get('cx', 640.0),
                        'cy': transforms.get('cy', 360.0),
                        'fov_x': transforms.get('camera_angle_x', 0.0),
                        'fov_y': transforms.get('camera_angle_y', 0.0)
                    }
                }
        
        # Convert scan_data frames to frames.json format
        frames = []
        for frame_data in scan_data.get('frames', []):
            # Extract 4x4 pose matrix and convert to position + quaternion
            pose_matrix = np.array(frame_data['pose']).reshape(4, 4)
            
            # Extract position (last column, first 3 rows)
            position = pose_matrix[:3, 3].tolist()
            
            # Extract rotation matrix (top-left 3x3)
            rotation_matrix = pose_matrix[:3, :3]
            
            # Convert rotation matrix to quaternion (simplified - assumes valid rotation matrix)
            # This is a basic conversion; for production use scipy.spatial.transform.Rotation
            trace = np.trace(rotation_matrix)
            if trace > 0:
                s = 0.5 / np.sqrt(trace + 1.0)
                w = 0.25 / s
                x = (rotation_matrix[2, 1] - rotation_matrix[1, 2]) * s
                y = (rotation_matrix[0, 2] - rotation_matrix[2, 0]) * s
                z = (rotation_matrix[1, 0] - rotation_matrix[0, 1]) * s
            else:
                # Fallback for negative trace
                w, x, y, z = 1.0, 0.0, 0.0, 0.0
            
            rotation = [w, x, y, z]
            
            # 2. Determine Depth Path (Priority: Monocular fallback if folder exists)
            depth_file = frame_data.get('depth_file', '')
            mono_depth_folder = extraction_path / "depth_monocular"
            if mono_depth_folder.exists() and depth_file:
                # If we have a monocular depth folder, use it
                depth_filename = os.path.basename(depth_file)
                depth_file = f"depth_monocular/{depth_filename}"
            
            frame = {
                'frame_id': frame_data['frame_id'],
                'timestamp': frame_data.get('timestamp', 0.0),
                'pose': {
                    'position': position,
                    'rotation': rotation
                },
                'cameras': {
                    'center': {  # Single camera from Camera 1
                        'image': frame_data.get('color_file', ''),
                        'depth': depth_file
                    }
                }
            }
            frames.append(frame)
        
        # Write frames.json
        output = {
            'version': '2.0',
            'source': 'QuestGear3DScan',
            'camera_metadata': camera_metadata,
            'frames': frames
        }
        
        frames_json_path = extraction_path / "frames.json"
        with open(frames_json_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"✓ Converted new format scan: {len(frames)} frames")
        return str(frames_json_path)
    
    @staticmethod
    def _adapt_old_format(extraction_dir):
        """Adapt legacy Quest Recording Manager format (hmd_poses.csv)."""
        extraction_path = Path(extraction_dir)
        
        # Read HMD poses
        hmd_poses_file = extraction_path / "hmd_poses.csv"
        if not hmd_poses_file.exists():
            raise FileNotFoundError("hmd_poses.csv not found")
        
        poses = []
        with open(hmd_poses_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                poses.append({
                    'timestamp': int(row['unix_time']),
                    'position': [
                        float(row['pos_x']),
                        float(row['pos_y']),
                        float(row['pos_z'])
                    ],
                    'rotation': [
                        float(row['rot_w']),
                        float(row['rot_x']),
                        float(row['rot_y']),
                        float(row['rot_z'])
                    ]
                })
        
        # Read camera characteristics
        left_cam_file = extraction_path / "left_camera_characteristics.json"
        right_cam_file = extraction_path / "right_camera_characteristics.json"
        
        cameras = {}
        if left_cam_file.exists():
            with open(left_cam_file, 'r') as f:
                cameras['left'] = json.load(f)
        
        if right_cam_file.exists():
            with open(right_cam_file, 'r') as f:
                cameras['right'] = json.load(f)
        
        # Scan for image files
        left_images = sorted([f.name for f in (extraction_path / "left_camera_raw").iterdir() if f.suffix == '.yuv'])
        right_images = sorted([f.name for f in (extraction_path / "right_camera_raw").iterdir() if f.suffix == '.yuv'])
        left_depth = sorted([f.name for f in (extraction_path / "left_depth").iterdir() if f.suffix == '.raw'])
        right_depth = sorted([f.name for f in (extraction_path / "right_depth").iterdir() if f.suffix == '.raw'])
        
        # Build frames structure
        frames = []
        for i in range(min(len(left_images), len(poses))):
            frame = {
                'frame_id': i,
                'timestamp': poses[i]['timestamp'],
                'pose': {
                    'position': poses[i]['position'],
                    'rotation': poses[i]['rotation']
                },
                'cameras': {
                    'left': {
                        'image': f"left_camera_raw/{left_images[i]}",
                        'depth': f"left_depth/{left_depth[i]}" if i < len(left_depth) else None
                    },
                    'right': {
                        'image': f"right_camera_raw/{right_images[i]}" if i < len(right_images) else None,
                        'depth': f"right_depth/{right_depth[i]}" if i < len(right_depth) else None
                    }
                }
            }
            frames.append(frame)
        
        # Write frames.json
        output = {
            'version': '1.0',
            'source': 'Quest 3 (Legacy)',
            'camera_metadata': cameras,
            'frames': frames
        }
        
        frames_json_path = extraction_path / "frames.json"
        with open(frames_json_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"✓ Converted legacy format scan: {len(frames)} frames")
        return str(frames_json_path)
