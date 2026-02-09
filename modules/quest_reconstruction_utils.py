import numpy as np
from enum import Enum
from dataclasses import dataclass
from scipy.spatial.transform import Rotation as R

class CoordinateSystem(Enum):
    """
    Enum representing different coordinate systems.
    
    - UNITY:
        - World: Y-up, left-handed
        - Camera: X-right, Y-up, Z-forward
    - OPEN3D:
        - World: Y-up, right-handed
        - Camera: X-right, Y-down, Z-forward
    """
    UNITY = "Unity"
    OPEN3D = "Open3D"
    COLMAP = "COLMAP"


@dataclass
class Transforms:
    """
    Handles coordinate system transformations for Quest 3D reconstruction.
    """
    coordinate_system: CoordinateSystem
    positions: np.ndarray  # (N, 3)
    rotations: np.ndarray  # (N, 4) quaternions (x, y, z, w)

    @property
    def extrinsics_wc(self) -> np.ndarray:
        """World-to-Camera transformations (N, 4, 4)"""
        return self._to_extrinsic_matrices(inverse=True)

    @property
    def extrinsics_cw(self) -> np.ndarray:
        """Camera-to-World transformations (N, 4, 4)"""
        return self._to_extrinsic_matrices(inverse=False)

    def _to_extrinsic_matrices(self, inverse: bool = True) -> np.ndarray:
        N = len(self.positions)
        # scipy Rotation expects (x, y, z, w)
        R_cw = R.from_quat(self.rotations).as_matrix()  # (N, 3, 3)

        extrinsic_matrices = np.eye(4)[None, ...].repeat(N, axis=0)
        extrinsic_matrices[:, :3, :3] = R_cw
        extrinsic_matrices[:, :3, 3] = self.positions

        if inverse:
            return np.linalg.inv(extrinsic_matrices)
        return extrinsic_matrices

    def get_coordinate_transform_matrix(self, source: CoordinateSystem, target: CoordinateSystem) -> np.ndarray:
        def basis(cs: CoordinateSystem) -> np.ndarray:
            if cs == CoordinateSystem.UNITY:
                return np.eye(3)
            elif cs == CoordinateSystem.OPEN3D:
                return np.diag((1, 1, -1))
            elif cs == CoordinateSystem.COLMAP:
                return np.diag((1, -1, 1))
            else:
                raise ValueError(f"Unknown coordinate system: {cs}")
            
        R_source = basis(source)
        R_target = basis(target)
        return R_target @ R_source.T

    def get_camera_basis_matrix(self, cs: CoordinateSystem) -> np.ndarray:
        if cs == CoordinateSystem.UNITY:        
            return np.eye(3)                    
        elif cs == CoordinateSystem.OPEN3D:     
            return np.diag((1, -1, -1))         
        elif cs == CoordinateSystem.COLMAP:     
            return np.eye(3)                    
        else:
            raise ValueError(f"Unknown coordinate system: {cs}")

    def convert_coordinate_system(
        self,
        target_coordinate_system: CoordinateSystem,
        is_camera: bool = False
    ) -> 'Transforms':
        if self.coordinate_system == target_coordinate_system:
            return self

        R_conv = self.get_coordinate_transform_matrix(self.coordinate_system, target_coordinate_system)

        # Apply to positions
        converted_positions = (R_conv @ self.positions.T).T

        # Apply to rotations
        rotation_matrices = R.from_quat(self.rotations).as_matrix()

        if is_camera:
            source_basis_matrix = self.get_camera_basis_matrix(self.coordinate_system)
            rotation_matrices = rotation_matrices @ source_basis_matrix.T

        converted_rotations = R_conv @ rotation_matrices @ R_conv.T

        if is_camera:
            target_basis_matrix = self.get_camera_basis_matrix(target_coordinate_system)
            converted_rotations = converted_rotations @ target_basis_matrix

        return Transforms(
            coordinate_system=target_coordinate_system,
            positions=converted_positions,
            rotations=R.from_matrix(converted_rotations).as_quat()
        )

# --- Depth Utilities ---

def compute_depth_camera_params(left, right, top, bottom, width, height):
    """Compute intrinsics from FOV tangents."""
    fx = width / (right + left)
    fy = height / (top + bottom)
    cx = width * right / (right + left)
    cy = height * top / (top + bottom)
    return fx, fy, cx, cy

def compute_ndc_to_linear_depth_params(near, far):
    if np.isinf(far) or far < near:
        x = -2.0 * near
        y = -1.0
    else:
        x = -2.0 * far * near / (far - near)
        y = -(far + near) / (far - near)
    return x, y

def to_linear_depth(d, x, y):
    ndc = d * 2.0 - 1.0
    denom = ndc + y
    return np.divide(x, denom, out=np.zeros_like(d), where=denom != 0)

def convert_depth_to_linear(depth_buffer: np.ndarray, near: float, far: float):
    """Convert raw non-linear depth buffer to linear depth in meters."""
    # Sanitize input buffer
    depth_clamped = np.clip(np.nan_to_num(depth_buffer, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)
    
    x, y = compute_ndc_to_linear_depth_params(near, far)
    depth_array = to_linear_depth(depth_clamped, x, y)
    
    # Sanitize output
    # Filter out potential negative depths or huge values that might result from division by near-zero
    depth_array = np.nan_to_num(depth_array, nan=0.0, posinf=0.0, neginf=0.0)
    depth_array[depth_array < 0] = 0.0
    
    return depth_array.astype(np.float32)
