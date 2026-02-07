import sys
import os
import unittest
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.config_manager import ConfigManager, DEFAULT_CONFIG

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.test_config_path = "test_config.yml"
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)
        self.cm = ConfigManager(self.test_config_path)

    def tearDown(self):
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)

    def test_default_config(self):
        self.assertEqual(self.cm.get("reconstruction.voxel_size"), DEFAULT_CONFIG["reconstruction"]["voxel_size"])

    def test_save_load(self):
        self.cm.set("reconstruction.voxel_size", 0.05)
        self.assertEqual(self.cm.get("reconstruction.voxel_size"), 0.05)
        
        # Reload to verify persistence
        cm2 = ConfigManager(self.test_config_path)
        self.assertEqual(cm2.get("reconstruction.voxel_size"), 0.05)

    def test_nested_get(self):
        self.assertEqual(self.cm.get("export.format"), "ply")
        self.assertIsNone(self.cm.get("non.existent.key"))

if __name__ == '__main__':
    unittest.main()
