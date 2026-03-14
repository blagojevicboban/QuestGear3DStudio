"""
Drift Correction and Loop Closure for QuestGear 3D Studio.
Uses GICP and Pose Graph Optimization to correct tracking drift.
"""

import numpy as np
import open3d as o3d
from scipy.spatial.transform import Rotation as R

class PoseRefiner:
    """
    Refines the trajectory using local and global registration.
    """
    
    def __init__(self, voxel_size=0.05, max_correspondence_distance=0.1):
        self.voxel_size = voxel_size
        self.max_correspondence_distance = max_correspondence_distance
        
    def refine_local(self, source_pcd, target_pcd, initial_transform):
        """
        Refine pose between two point clouds using GICP.
        """
        # Downsample for faster registration
        source_pcd = source_pcd.voxel_down_sample(self.voxel_size)
        target_pcd = target_pcd.voxel_down_sample(self.voxel_size)
        
        # Estimate normals if missing (needed for GICP)
        if not source_pcd.has_normals():
            source_pcd.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=self.voxel_size*2, max_nn=30))
        if not target_pcd.has_normals():
            target_pcd.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=self.voxel_size*2, max_nn=30))
            
        result = o3d.pipelines.registration.registration_generalized_icp(
            source_pcd, target_pcd, self.max_correspondence_distance, initial_transform,
            o3d.pipelines.registration.TransformationEstimationForGeneralizedICP()
        )
        
        return result.transformation, result.fitness, result.information_matrix

    def optimize_trajectory(self, frames_pcd, initial_poses, loop_closure_dist=1.5, on_log=None):
        """
        Build and optimize a pose graph.
        
        Args:
            frames_pcd: List of point clouds (one per keyframe)
            initial_poses: List of 4x4 matrix initial poses
            loop_closure_dist: Proximity threshold for loop detection
        """
        if len(frames_pcd) < 2:
            return initial_poses
            
        if on_log: on_log(f"Starting Global Refinement (Pose Graph) on {len(frames_pcd)} keyframes...")
        
        pose_graph = o3d.pipelines.registration.PoseGraph()
        
        # 1. Add Odometry Constraints (and nodes)
        # We assume initial_poses are already in world space
        # Constraint between i and i+1 is inv(Pi) * Pi+1
        
        for i in range(len(frames_pcd)):
            # Add Node
            pose_graph.nodes.append(o3d.pipelines.registration.PoseGraphNode(initial_poses[i]))
            
            if i > 0:
                # Add Odometry Edge (from i-1 to i)
                # The constraint is the relative transformation in the coordinate system of i-1
                rel_transform = np.linalg.inv(initial_poses[i-1]) @ initial_poses[i]
                
                # Check with ICP if requested (Local refinement)
                refined_transform, fitness, info = self.refine_local(
                    frames_pcd[i], frames_pcd[i-1], rel_transform
                )
                
                # If refinement is good, use it, otherwise fallback to Quest (it's usually robust)
                if fitness > 0.6:
                    constraint = refined_transform
                else:
                    constraint = rel_transform
                    info = np.eye(6) # Low confidence
                
                pose_graph.edges.append(o3d.pipelines.registration.PoseGraphEdge(
                    i-1, i, constraint, info, uncertain=False
                ))

        # 2. Loop Closure Detection
        if on_log: on_log("Searching for Loop Closures...")
        
        loop_count = 0
        # Simple proximity check
        for i in range(len(initial_poses)):
            for j in range(i + 5, len(initial_poses)): # Only check frames apart
                dist = np.linalg.norm(initial_poses[i][:3, 3] - initial_poses[j][:3, 3])
                
                if dist < loop_closure_dist:
                    # Potential loop! Try to align
                    # Initial relative transform from Quest
                    rel_transform = np.linalg.inv(initial_poses[i]) @ initial_poses[j]
                    
                    refined_transform, fitness, info = self.refine_local(
                        frames_pcd[j], frames_pcd[i], rel_transform
                    )
                    
                    # If high fitness, we found a loop!
                    if fitness > 0.7:
                        pose_graph.edges.append(o3d.pipelines.registration.PoseGraphEdge(
                            i, j, refined_transform, info, uncertain=True
                        ))
                        loop_count += 1
                        
        if on_log: on_log(f"✓ Found {loop_count} Loop Closures.")

        # 3. Optimize
        method = o3d.pipelines.registration.GlobalOptimizationLevenbergMarquardt()
        criteria = o3d.pipelines.registration.GlobalOptimizationConvergenceCriteria()
        option = o3d.pipelines.registration.GlobalOptimizationOption(
            max_correspondence_distance=self.max_correspondence_distance,
            edge_pruning_threshold=0.25,
            reference_node=0
        )
        
        o3d.pipelines.registration.global_optimization(
            pose_graph, method, criteria, option
        )
        
        # 4. Extract optimized poses
        optimized_poses = [np.copy(node.pose) for node in pose_graph.nodes]
        
        if on_log: on_log("✓ Trajectory optimization complete.")
        
        return optimized_poses
