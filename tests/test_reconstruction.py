import sys
import os
import unittest
import numpy as np
import open3d as o3d

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.reconstruction import QuestReconstructor
from modules.config_manager import ConfigManager

class TestReconstruction(unittest.TestCase):
    def setUp(self):
        self.cm = ConfigManager("test_config_recon.yml")
        self.recon = QuestReconstructor(self.cm)

    def tearDown(self):
        if os.path.exists("test_config_recon.yml"):
            os.remove("test_config_recon.yml")

    def test_initialization(self):
        self.assertIsNotNone(self.recon.volume)
        self.assertEqual(self.recon.voxel_size, 0.01)

    def test_integrate_dummy_frame(self):
        # Create dummy data
        w, h = 640, 480
        rgb = np.zeros((h, w, 3), dtype=np.uint8)
        depth = np.ones((h, w), dtype=np.uint16) * 1000 # 1 meter
        intrinsics = np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1]])
        pose = np.eye(4)

        try:
            self.recon.integrate_frame(rgb, depth, intrinsics, pose)
        except Exception as e:
            self.fail(f"Integration failed: {e}")

    def test_mesh_extraction(self):
        # Should return empty mesh if no data integrated, but shouldn't crash
        mesh = self.recon.extract_mesh()
        self.assertIsInstance(mesh, o3d.geometry.TriangleMesh)

if __name__ == '__main__':
    unittest.main()
