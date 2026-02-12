"""
Compare old and new PLY meshes to verify improvements
"""
import open3d as o3d
import numpy as np

print("="*60)
print("MESH COMPARISON - Old vs New")
print("="*60)

# Old mesh (before geometry fixes)
old_path = r"D:\METAQUEST\20260208_074933_extracted\Export\reconstruction_20260211_045116.ply"
print(f"\n📦 OLD MESH (voxel=0.03m, no depth filter)")
print(f"   {old_path}")
old_mesh = o3d.io.read_triangle_mesh(old_path)
print(f"   Vertices: {len(old_mesh.vertices):,}")
print(f"   Triangles: {len(old_mesh.triangles):,}")
if old_mesh.has_vertex_colors():
    old_colors = np.asarray(old_mesh.vertex_colors)
    old_unique = np.unique(old_colors, axis=0)
    print(f"   Unique colors: {len(old_unique)}")
    print(f"   Color: TRUE RGB")
else:
    print(f"   Color: None")

# New mesh (after geometry fixes)
new_path = r"D:\METAQUEST\20260208_074933_extracted\Export\reconstruction_20260211_055730.ply"
print(f"\n📦 NEW MESH (voxel=0.02m, depth filter 0.1-5.0m)")
print(f"   {new_path}")
new_mesh = o3d.io.read_triangle_mesh(new_path)
print(f"   Vertices: {len(new_mesh.vertices):,}")
print(f"   Triangles: {len(new_mesh.triangles):,}")
if new_mesh.has_vertex_colors():
    new_colors = np.asarray(new_mesh.vertex_colors)
    new_unique = np.unique(new_colors, axis=0)
    print(f"   Unique colors: {len(new_unique)}")
    print(f"   Color: TRUE RGB")
else:
    print(f"   Color: None")

# Comparison
print(f"\n📊 IMPROVEMENT ANALYSIS:")
print(f"="*60)

if len(old_mesh.vertices) > 0:
    vertex_increase = ((len(new_mesh.vertices) - len(old_mesh.vertices)) / len(old_mesh.vertices)) * 100
    tri_increase = ((len(new_mesh.triangles) - len(old_mesh.triangles)) / len(old_mesh.triangles)) * 100

    print(f"   Vertex increase: {vertex_increase:+.1f}% ({len(old_mesh.vertices):,} → {len(new_mesh.vertices):,})")
    print(f"   Triangle increase: {tri_increase:+.1f}% ({len(old_mesh.triangles):,} → {len(new_mesh.triangles):,})")

    if old_mesh.has_vertex_colors() and new_mesh.has_vertex_colors():
        color_increase = ((len(new_unique) - len(old_unique)) / len(old_unique)) * 100
        print(f"   Color diversity: {color_increase:+.1f}% ({len(old_unique)} → {len(new_unique)} unique colors)")
else:
    print(f"   Old mesh was EMPTY or corrupted!")
    print(f"   New mesh: {len(new_mesh.vertices):,} vertices, {len(new_mesh.triangles):,} triangles")

# Bounding box comparison
old_bbox = old_mesh.get_axis_aligned_bounding_box()
new_bbox = new_mesh.get_axis_aligned_bounding_box()
old_extent = old_bbox.get_extent()
new_extent = new_bbox.get_extent()

print(f"\n📏 BOUNDING BOX:")
print(f"   Old: {old_extent[0]:.2f}m × {old_extent[1]:.2f}m × {old_extent[2]:.2f}m")
print(f"   New: {new_extent[0]:.2f}m × {new_extent[1]:.2f}m × {new_extent[2]:.2f}m")

# Expected input data coverage (from 706 frames)
print(f"\n📸 INPUT DATA REFERENCE:")
print(f"   Total frames: 706")
print(f"   RGB resolution: 1280×1280")
print(f"   Depth resolution: 320×320")
print(f"   Expected depth range: ~0.6m - 2.1m (with outliers up to 32m)")
print(f"   Scan type: Room rotation")

print(f"\n✅ Analysis complete!")
