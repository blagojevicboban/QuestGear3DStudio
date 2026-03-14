"""
Advanced Texture Processing for QuestGear 3D Studio.
Implements UV Unwrapping and Texture Map generation from RGBD data.
"""

import numpy as np
import cv2
import os
from pathlib import Path
from tqdm import tqdm

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False

try:
    import xatlas
    HAS_XATLAS = True
except ImportError:
    HAS_XATLAS = False

class TextureProcessor:
    """
    Handles UV unwrapping and texture extraction from camera frames.
    """
    
    def __init__(self, texture_size=2048):
        self.texture_size = texture_size
    
    def process_mesh(self, mesh, frames, project_dir, on_log=None):
        """
        Unwrap mesh and bake texture from frames.
        
        Args:
            mesh: o3d.geometry.TriangleMesh
            frames: List of dicts (processed frames with rgb, poses, etc.)
            project_dir: Path to project
            on_log: Optional log callback
        
        Returns:
            Textured mesh (geometry.TriangleMesh)
        """
        if not HAS_XATLAS:
            if on_log: on_log("ERROR: xatlas not installed. Skipping texture mapping.")
            return mesh
            
        if not mesh.has_vertices() or not mesh.has_triangles():
            return mesh

        if on_log: on_log(f"UV Unwrapping mesh ({len(mesh.vertices)} vertices)...")
        
        # 1. UV Unwrapping with xatlas
        v = np.asarray(mesh.vertices)
        f = np.asarray(mesh.triangles)
        
        atlas = xatlas.Atlas()
        atlas.add_mesh(v, f)
        atlas.generate()
        
        # Extract the unwrapped mesh data
        # atlas[0] is the first mesh
        vmapping, indices, uvs = atlas[0]
        
        # Create new mesh with duplicated vertices where UVs split
        new_mesh = o3d.geometry.TriangleMesh()
        new_mesh.vertices = o3d.utility.Vector3dVector(v[vmapping])
        new_mesh.triangles = o3d.utility.Vector3iVector(indices)
        new_mesh.triangle_uvs = o3d.utility.Vector2dVector(uvs / atlas.width) # Normalize UVs
        
        # Maintain normals if they exist
        if mesh.has_vertex_normals():
            old_normals = np.asarray(mesh.vertex_normals)
            new_mesh.vertex_normals = o3d.utility.Vector3dVector(old_normals[vmapping])
            
        if on_log: on_log(f"✓ Unwrap complete. Texture Atlas: {atlas.width}x{atlas.height}")
        
        # 2. Texture Baking
        if on_log: on_log(f"Baking texture map ({self.texture_size}x{self.texture_size})...")
        
        texture_img = self._bake_texture(new_mesh, frames, atlas.width, atlas.height, on_log)
        
        # Assign texture to mesh
        new_mesh.textures = [o3d.geometry.Image(cv2.cvtColor(texture_img, cv2.COLOR_BGR2RGB))]
        
        return new_mesh, texture_img

    def _bake_texture(self, mesh, frames, width, height, on_log=None):
        """
        Naive but effective projective texture baking.
        For each triangle, we find the 'best' camera view and copy image data.
        """
        # Note: In a production environment, we'd use a more sophisticated 
        # blending or a shader-based baker. Here we implement a CPU-based 
        # weighted projection.
        
        # 1. Prepare buffers
        # We'll work at self.texture_size
        tex_w = self.texture_size
        tex_h = self.texture_size
        
        # Scale UVs to texture size
        uvs = np.asarray(mesh.triangle_uvs) * [tex_w, tex_h]
        triangles = np.asarray(mesh.triangles)
        vertices = np.asarray(mesh.vertices)
        
        # Initialize result image and weight buffer
        out_img = np.zeros((tex_h, tex_w, 3), dtype=np.float32)
        weight_buf = np.zeros((tex_h, tex_w), dtype=np.float32)
        
        # Compute triangle normals for visibility/angle check
        mesh.compute_triangle_normals()
        tri_normals = np.asarray(mesh.triangle_normals)
        
        # For each triangle
        for tri_idx in range(len(triangles)):
            idx = triangles[tri_idx]
            
            # Find the "best" frame for this triangle
            # Best = highest cos_angle
            best_frame_idx = -1
            max_score = -1.0
            best_img_coords = None
            
            tri_center = np.mean(vertices[idx], axis=0)
            
            for f_idx, frame in enumerate(frames):
                pose = frame.get('pose')
                intrinsics = frame.get('intrinsics')
                
                cam_pos = pose[:3, 3]
                view_dir = cam_pos - tri_center
                view_dist = np.linalg.norm(view_dir)
                view_dir /= (view_dist + 1e-6)
                
                cos_angle = np.dot(tri_normals[tri_idx], view_dir)
                if cos_angle < 0.2: continue # Ignore if too grazing
                
                # Project vertices
                w2c = np.linalg.inv(pose)
                v_homo = np.hstack([vertices[idx], np.ones((3, 1))])
                v_cam = (w2c @ v_homo.T).T
                
                if np.any(v_cam[:, 2] < 0.1): continue
                
                v_img_homo = (intrinsics @ v_cam[:, :3].T).T
                u = v_img_homo[:, 0] / (v_img_homo[:, 2] + 1e-6)
                v_coord = v_img_homo[:, 1] / (v_img_homo[:, 2] + 1e-6)
                
                rgb_shape = frame['rgb'].shape
                if np.all(u >= 0) and np.all(u < rgb_shape[1]) and \
                   np.all(v_coord >= 0) and np.all(v_coord < rgb_shape[0]):
                    
                    # Score: cos_angle / distance
                    score = cos_angle / (view_dist + 1.0)
                    if score > max_score:
                        max_score = score
                        best_frame_idx = f_idx
                        best_img_coords = np.vstack([u, v_coord]).T

            if best_frame_idx != -1:
                # Warp the triangle from best frame to UV space
                tri_uv = uvs[tri_idx*3 : tri_idx*3 + 3]
                src_tri = best_img_coords.astype(np.float32)
                dst_tri = tri_uv.astype(np.float32)
                
                M = cv2.getAffineTransform(src_tri, dst_tri)
                
                # Warp only the bounding box region for speed
                min_uv = np.floor(np.min(dst_tri, axis=0)).astype(int)
                max_uv = np.ceil(np.max(dst_tri, axis=0)).astype(int)
                
                start_x, start_y = max(0, min_uv[0]), max(0, min_uv[1])
                end_x, end_y = min(tex_w, max_uv[0]+1), min(tex_h, max_uv[1]+1)
                
                if end_x <= start_x or end_y <= start_y: continue
                
                # Create mask for this triangle in UV space
                mask = np.zeros((end_y - start_y, end_x - start_x), dtype=np.uint8)
                rel_tri = (dst_tri - [start_x, start_y]).astype(np.int32)
                cv2.fillPoly(mask, [rel_tri], 255)
                
                # Warp the image patch
                rgb = frames[best_frame_idx]['rgb']
                # Inverse of M maps UV to Image
                M_inv = cv2.getAffineTransform(dst_tri, src_tri)
                # Shift M_inv to local patch coordinates
                M_inv[:, 2] = M_inv @ [start_x, start_y, 1]
                
                patch = cv2.warpAffine(rgb, M_inv, (end_x - start_x, end_y - start_y), 
                                       flags=cv2.INTER_LINEAR)
                
                # Copy to output
                # Using the mask to avoid overwriting neighbors
                out_img[start_y:end_y, start_x:end_x][mask > 0] = patch[mask > 0]
                weight_buf[start_y:end_y, start_x:end_x][mask > 0] = 255

        # Finalize image
        out_img_uint8 = np.clip(out_img, 0, 255).astype(np.uint8)
        
        # Simple seam filling: dilate the texture slightly to fill gaps
        mask_global = weight_buf > 0
        if not np.all(mask_global):
            kernel = np.ones((3,3), np.uint8)
            dilated = cv2.dilate(out_img_uint8, kernel, iterations=2)
            out_img_uint8[~mask_global] = dilated[~mask_global]
        
        return out_img_uint8
    
    def save_textured_model(self, mesh, texture_img, base_path):
        """
        Save mesh and texture.
        
        Args:
            mesh: o3d.geometry.TriangleMesh
            texture_img: numpy array
            base_path: Full path with extension (e.g. model.obj)
        """
        # Ensure texture is saved next to the model
        dir_name = os.path.dirname(base_path)
        base_name = os.path.splitext(os.path.basename(base_path))[0]
        tex_name = f"{base_name}_tex.png"
        tex_path = os.path.join(dir_name, tex_name)
        
        # Save texture
        cv2.imwrite(tex_path, texture_img)
        
        # Update mesh to point to this texture if format requires it
        # Open3D handles this during export for some formats.
        o3d.io.write_triangle_mesh(base_path, mesh)
        
        return tex_path
