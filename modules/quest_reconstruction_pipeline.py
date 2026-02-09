"""Quest-specific 3D reconstruction pipeline."""

import json
import numpy as np
from pathlib import Path
from threading import Thread
from datetime import datetime

from .quest_image_processor import QuestImageProcessor
from .reconstruction import QuestReconstructor, HAS_OPEN3D, o3d
from .config_manager import ConfigManager
from .quest_reconstruction_utils import (
    Transforms, CoordinateSystem, compute_depth_camera_params, convert_depth_to_linear
)


class QuestReconstructionPipeline:
    """End-to-end reconstruction pipeline for Quest data."""
    
    def __init__(self, project_dir, config_manager: ConfigManager):
        """
        Initialize reconstruction pipeline.
        
        Args:
            project_dir: Path to extracted Quest data
            config_manager: Configuration manager
        """
        self.project_dir = Path(project_dir)
        self.config = config_manager
        self.reconstructor = QuestReconstructor(config_manager) if HAS_OPEN3D else None
        
        # Load frames.json
        frames_json = self.project_dir / "frames.json"
        if not frames_json.exists():
            raise FileNotFoundError(f"frames.json not found in {project_dir}")
        
        with open(frames_json, 'r') as f:
            self.data = json.load(f)
        
        self.frames = self.data.get('frames', [])
        self.camera_metadata = self.data.get('camera_metadata', {})
        
    def get_camera_intrinsics(self, camera='left', depth_info=None):
        """
        Extract camera intrinsics from metadata or use updated info.
        
        Args:
            camera: 'left' or 'right'
            depth_info: Optional dict with 'fov_...' tangents and 'width'/'height'
        
        Returns:
            3x3 intrinsics matrix
        """
        fx, fy, cx, cy = 0, 0, 0, 0

        if depth_info:
            # Use accurate intrinsics from frame metadata
            w = depth_info.get('width', 0)
            h = depth_info.get('height', 0)
            l = depth_info.get('fov_left', 0)
            r = depth_info.get('fov_right', 0)
            t = depth_info.get('fov_top', 0)
            b = depth_info.get('fov_down', 0)
            
            if w > 0 and h > 0:
                fx, fy, cx, cy = compute_depth_camera_params(l, r, t, b, w, h)
        
        if fx == 0:
            # Fallback to global metadata or defaults
            cam_data = self.camera_metadata.get(camera, {})
            intrinsics_obj = cam_data.get('intrinsics', {})
            
            fx = intrinsics_obj.get('fx', 867.0)
            fy = intrinsics_obj.get('fy', 867.0)
            cx = intrinsics_obj.get('cx', 640.0)
            cy = intrinsics_obj.get('cy', 640.0)
        
        intrinsics = np.array([
            [fx, 0, cx],
            [0, fy, cy],
            [0, 0, 1]
        ], dtype=np.float64)
        
        return intrinsics
    
    def get_camera_extrinsics(self, camera='left'):
        """
        Get 4x4 homogenous matrix for Head-to-Camera transform (Unity Coordinates).
        """
        cam_data = self.camera_metadata.get(camera, {})
        
        # Translation
        offset_x = -0.032 if camera == 'left' else 0.032
        translation = cam_data.get('translation', [offset_x, 0, 0])
        t = np.array(translation)
        
        # Rotation
        rotation = cam_data.get('rotation', None)
        if rotation is None:
             rotation = cam_data.get('rotation_quat', [0, 0, 0, 1]) # Default Identity
             
        # Create Transforms object for easy matrix conversion
        # We treat this as a "pose" in Unity space relative to head
        # This is a bit of a hack to use Transforms for a single local offset, 
        # but it ensures consistent quaternion handling.
        
        # Note: input rotation order in metadata might need verification.
        # Assuming [x, y, z, w] or similar. Utils expects [x, y, z, w].
        # If input is [w, x, y, z], we need to swap.
        # Reference project uses `create_pose_rotation_x` etc columns.
        # Here we assume standard Unity JSON which is usually [x, y, z, w].
        
        clean_rot = np.array(rotation)
        if len(clean_rot) == 4:
            # Check if likely [w, x, y, z] (w is often close to 1 for small rotations)
            # But Unity default is [x, y, z, w].
            pass

        # Since we are just building a local matrix in Unity space, let's use scipy directly
        # to avoid confusion with the coordinate system enum which controls AXIS flips.
        from scipy.spatial.transform import Rotation as R
        r = R.from_quat(clean_rot)
        mat = r.as_matrix()
        
        H = np.eye(4)
        H[:3, :3] = mat
        H[:3, 3] = t
        
        return H

    def run_reconstruction(
        self, 
        on_progress=None, 
        on_log=None,
        on_frame=None,
        is_cancelled=None,
        camera='left',
        frame_interval=1,
        start_frame=0,
        end_frame=None
    ):
        """
        Run the reconstruction process.
        """
        if not self.reconstructor:
            if on_log:
                on_log("ERROR: Open3D not available. Cannot run reconstruction.")
            return None
        
        total_frames = len(self.frames)
        if end_frame is None or end_frame >= total_frames:
            end_frame = total_frames - 1
            
        frames_subset = self.frames[start_frame : end_frame + 1]
        
        if on_log:
            on_log(f"Starting reconstruction with {len(frames_subset)} frames (Range: {start_frame}-{end_frame})...")
            on_log(f"Using camera mode: {camera}")
            
        cameras_to_process = ['left', 'right'] if camera == 'both' else [camera]
        
        # Pre-calculate extrinsics (Head-to-Camera) in Unity space
        extrinsics_map_unity = {cam: self.get_camera_extrinsics(cam) for cam in cameras_to_process}
        
        processed_count = 0
        failed_count = 0
        
        processing_frames = frames_subset[::frame_interval]
        total_processing = len(processing_frames)
        
        for i, frame in enumerate(processing_frames):
            if is_cancelled and is_cancelled():
                if on_log: on_log("Reconstruction CANCELLED by user.")
                return None
                
            current_real_index = start_frame + i * frame_interval
            
            if on_frame: on_frame(current_real_index)
            if on_progress: on_progress(int((i + 1) / total_processing * 100))
            if on_log and i % max(1, total_processing // 20) == 0:
                on_log(f"Processing frame set {i+1}/{total_processing}...")
            
            # Get Head Pose (Unity World)
            # frame['pose']['position'] -> [x, y, z]
            # frame['pose']['rotation'] -> [x, y, z, w] ideally
            head_pos = np.array(frame['pose']['position'])
            head_rot = np.array(frame['pose']['rotation'])
            
            # Construct Head Matrix (Unity)
            from scipy.spatial.transform import Rotation as R
            head_R = R.from_quat(head_rot).as_matrix()
            head_T = np.eye(4)
            head_T[:3, :3] = head_R
            head_T[:3, 3] = head_pos
            
            for cam in cameras_to_process:
                try:
                    rgb, depth, depth_info = QuestImageProcessor.process_quest_frame(
                        str(self.project_dir),
                        frame,
                        camera=cam
                    )
                    
                    if rgb is None or depth is None:
                        failed_count += 1
                        continue
                     
                    # 1. Get accurate intrinsics
                    intrinsics = self.get_camera_intrinsics(cam, depth_info)
                    
                    # 2. Linearize depth
                    if depth_info:
                        near = depth_info.get('near_z', 0.1)
                        far = depth_info.get('far_z', 3.0)
                        depth_linear = convert_depth_to_linear(depth, near, far)
                    else:
                        # Fallback: assume depth is already linear or use defaults
                        # If raw depth was loaded as float32, it's likely non-linear NDC-like if from Quest?
                        # Or it might be meters. Existing code assumed meters.
                        # Let's assume meters to be safe for legacy support.
                        depth_linear = depth
                        
                    # 3. Compute Camera Pose in Unity World
                    # T_cam_world = T_head_world @ T_cam_head
                    unity_camera_pose = head_T @ extrinsics_map_unity[cam]
                    
                    # 4. Convert to Open3D Coordinate System
                    # Create Transforms object with this single pose
                    # Extract translation and rotation from the combined matrix
                    cam_pos_unity = unity_camera_pose[:3, 3]
                    cam_rot_unity = R.from_matrix(unity_camera_pose[:3, :3]).as_quat()
                    
                    unity_transform = Transforms(
                        coordinate_system=CoordinateSystem.UNITY,
                        positions=np.array([cam_pos_unity]),
                        rotations=np.array([cam_rot_unity]) # [x, y, z, w]
                    )
                    
                    open3d_transform = unity_transform.convert_coordinate_system(CoordinateSystem.OPEN3D)
                    
                    # Get Camera-to-World matrix in Open3D space
                    # indexing [0] because we wrapped in array
                    final_pose_open3d = open3d_transform.extrinsics_cw[0]
                    # Integation Debug Check
                    if i < 20 or (i % 10 == 0):
                         # Check for invalid values
                         t_min, t_max = np.min(depth_linear), np.max(depth_linear)
                         p_trans = final_pose_open3d[:3, 3]
                         msg = f"DEBUG Frame {i}: Depth[{t_min:.3f}, {t_max:.3f}] PoseT{p_trans} FX={intrinsics[0,0]:.1f}"
                         if on_log: on_log(msg)
                         print(msg) # Print to stdout for terminal capture
                         
                         if np.any(np.isnan(final_pose_open3d)) or np.any(np.isinf(final_pose_open3d)):
                             err_msg = f"ERROR: Invalid Pose detected in frame {i}!"
                             if on_log: on_log(err_msg)
                             print(err_msg)
                             continue

                    # Integrate
                    self.reconstructor.integrate_frame(
                        rgb, 
                        depth_linear, 
                        intrinsics, 
                        final_pose_open3d
                    )
                    processed_count += 1
                    
                except Exception as e:
                    if on_log and failed_count < 5:
                        on_log(f"Error processing {cam} frame {i}: {str(e)}")
                    failed_count += 1
        
        if on_log:
            on_log(f"Integration complete! Processed: {processed_count}, Failed: {failed_count}")
            on_log("Extracting mesh...")
        
        mesh = self.reconstructor.extract_mesh()
        
        output_path = None
        if on_log:
            if hasattr(mesh, 'vertices'):
                on_log(f"✓ Mesh extracted: {len(mesh.vertices)} vertices")
                
                export_config = self.config.get("export") if self.config else {}
                fmt = export_config.get("format", "obj")
                
                if export_config.get("save_mesh", True):
                    export_dir = self.project_dir / "Export"
                    export_dir.mkdir(exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = export_dir / f"reconstruction_{timestamp}.{fmt}"
                    
                    on_log(f"Saving mesh to {output_path}...")
                    try:
                        o3d.io.write_triangle_mesh(str(output_path), mesh)
                        on_log(f"✓ Saved successfully")
                        
                        # Thumbnail
                        try:
                            vis = o3d.visualization.Visualizer()
                            vis.create_window(visible=False, width=640, height=480)
                            vis.add_geometry(mesh)
                            vis.poll_events()
                            vis.update_renderer()
                            thumb_path = export_dir / f"thumbnail_{timestamp}.png"
                            vis.capture_screen_image(str(thumb_path), do_render=True)
                            latest_thumb = self.project_dir / "thumbnail.png"
                            import shutil
                            shutil.copy2(str(thumb_path), str(latest_thumb))
                            vis.destroy_window()
                        except: pass
                        
                    except Exception as e:
                        on_log(f"ERROR saving mesh: {e}")
            else:
                on_log("⚠ Mesh extraction failed")
        
        return {
            'mesh': mesh,
            'processed_frames': processed_count,
            'failed_frames': failed_count,
            'output_path': str(output_path) if output_path and output_path.exists() else None
        }


class AsyncQuestReconstruction(Thread):
    """Background thread for Quest reconstruction."""
    
    def __init__(self, project_dir, config_manager, on_progress=None, on_finished=None, on_error=None, on_log=None):
        super().__init__(daemon=True)
        self.project_dir = project_dir
        self.config_manager = config_manager
        self.on_progress = on_progress
        self.on_finished = on_finished
        self.on_error = on_error
        self.on_log = on_log
        
    def run(self):
        try:
            pipeline = QuestReconstructionPipeline(self.project_dir, self.config_manager)
            result = pipeline.run_reconstruction(
                on_progress=self.on_progress,
                on_log=self.on_log,
                camera='left',
                frame_interval=5  # Default interval
            )
            
            if self.on_finished:
                self.on_finished(result)
                
        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
            if self.on_log:
                self.on_log(f"ERROR: {str(e)}")
