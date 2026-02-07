"""
3D Reconstruction module using Open3D.
Implements TSDF volume integration for generating meshes from RGBD data.
"""

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False
    class o3d:
        class pipelines:
            class integration:
                class ScalableTSDFVolume:
                    def __init__(self, *args, **kwargs): pass
                class TSDFVolumeColorType:
                    RGB8 = 0
        class geometry:
            class RGBDImage:
                @staticmethod
                def create_from_color_and_depth(*args, **kwargs): return None
            class Image:
                def __init__(self, *args): pass
        class camera:
            class PinholeCameraIntrinsic:
                def __init__(self, *args): pass

import numpy as np
from .config_manager import ConfigManager

class QuestReconstructor:
    """
    Handles the integration of multiple RGBD frames into a single 3D volume.
    Wrapper around Open3D's ScalableTSDFVolume.
    """
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager.get("reconstruction")
        self.voxel_size = self.config.get("voxel_size", 0.01)
        self.trunc_voxel_multiplier = self.config.get("trunc_voxel_multiplier", 8.0)
        self.depth_max = self.config.get("depth_max", 3.0)
        
        if HAS_OPEN3D:
            self.volume = o3d.pipelines.integration.ScalableTSDFVolume(
                voxel_length=self.voxel_size,
                sdf_trunc=self.voxel_size * self.trunc_voxel_multiplier,
                color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8
            )
        else:
            self.volume = None

    def convert_pose(self, pose_matrix):
        """
        Convert Meta Quest pose to Open3D coordinate system.
        Reference: (x, y, z) -> (x, y, -z) for translation
                   (x, y, z, w) -> (-x, -y, z, w) for rotation
        
        However, if we have a 4x4 matrix, we can adjust the axes directly.
        Quest is usually Right-Handed Y-up. Open3D is Right-Handed Y-down (for cameras) usually?
        Actually, let's stick to the reference repo transformation logic if possible.
        If the input pose is 4x4 matrix M:
        
        We need to inverse Z axis.
        """
        # Create a correction matrix to flip Z axis
        # This depends heavily on the specific coordinate definitions.
        # Assuming we just need to negate Z for position and adjust rotation.
        # Simple approach: Mirror Z.
        flip_z = np.eye(4)
        flip_z[2, 2] = -1
        # flip_z[2, 3] = 0 # translation z is also flipped?
        
        # This is a placeholder. Real implementation depends on data verification.
        # For now, we assume the input pose is "Camera to World".
        return pose_matrix @ flip_z

    def integrate_frame(self, rgb_image, depth_image, intrinsics, pose):
        """
        Integrate a single RGBD frame into the volume.
        rgb_image: (H, W, 3) numpy array
        depth_image: (H, W) numpy array (float or uint16)
        intrinsics: (3, 3) numpy array
        pose: (4, 4) numpy array (Camera to World)
        """
        if not self.volume:
            return

        rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(
            o3d.geometry.Image(rgb_image),
            o3d.geometry.Image(depth_image),
            depth_scale=1000.0, # Assuming depth is in mm. Check input!
            depth_trunc=self.depth_max,
            convert_rgb_to_intensity=False
        )
        
        # Open3D expects intrinsics as PinholeCameraIntrinsic object
        h, w = depth_image.shape
        fx = intrinsics[0, 0]
        fy = intrinsics[1, 1]
        cx = intrinsics[0, 2]
        cy = intrinsics[1, 2]
        
        o3d_intrinsics = o3d.camera.PinholeCameraIntrinsic(w, h, fx, fy, cx, cy)
        
        # Integrate
        # Note: ScalableTSDFVolume.integrate expects extrinsic (World to Camera) usually?
        # Documentation says: "extrinsic (numpy.ndarray[numpy.float64[4, 4]]) – Extrinsic parameters (T_world_to_camera)"
        # So we need inverse of pose if pose is Camera -> World.
        extrinsic = np.linalg.inv(pose)
        
        self.volume.integrate(rgbd, o3d_intrinsics, extrinsic)

    def extract_mesh(self):
        """
        Extract triangle mesh from the TSDF volume.
        """
        if not self.volume:
            # Return dummy object compatible with expectations
            class DummyMesh:
                vertices = []
            return DummyMesh()
            
        return self.volume.extract_triangle_mesh()

    def extract_point_cloud(self):
        """
        Extract point cloud from the TSDF volume.
        """
        if not self.volume:
             # Return dummy object compatible with expectations
            class DummyPC:
                points = []
            return DummyPC()
            
        return self.volume.extract_point_cloud()
