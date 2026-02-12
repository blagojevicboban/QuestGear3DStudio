"""
Quick script to check if PLY mesh has color data using Open3D
"""
import open3d as o3d
import numpy as np

ply_path = r"D:\METAQUEST\20260208_074933_extracted\Export\reconstruction_20260211_055730.ply"

print(f"Loading: {ply_path}")
mesh = o3d.io.read_triangle_mesh(ply_path)

print(f"\n📦 Mesh Information:")
print(f"  Vertices: {len(mesh.vertices):,}")
print(f"  Triangles: {len(mesh.triangles):,}")

# Check for vertex colors
if mesh.has_vertex_colors():
    colors = np.asarray(mesh.vertex_colors)
    print(f"\n  ✅ HAS VERTEX COLORS!")
    print(f"     Color array shape: {colors.shape}")
    print(f"     Sample colors (RGB):")
    for i in range(min(5, len(colors))):
        r, g, b = colors[i]
        print(f"       Vertex {i}: R={r:.3f}, G={g:.3f}, B={b:.3f}")
    
    # Check if colors are actually different (not grayscale)
    unique_colors = np.unique(colors, axis=0)
    print(f"\n     Unique colors: {len(unique_colors)}")
    
    # Check if it's grayscale (R==G==B for all vertices)
    is_grayscale = np.all(colors[:, 0] == colors[:, 1]) and np.all(colors[:, 1] == colors[:, 2])
    if is_grayscale:
        print(f"     ⚠️  WARNING: Colors are GRAYSCALE (R=G=B)")
    else:
        print(f"     🎨 Colors are TRUE RGB (not grayscale)!")
else:
    print(f"\n  ❌ NO VERTEX COLORS (mesh is colorless)")

print("\n✅ Done!")
