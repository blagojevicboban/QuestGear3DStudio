import sys
import os
import unittest
import zipfile
import shutil
from PyQt6.QtCore import QCoreApplication

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.ingestion import ZipValidator

class TestIngestion(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_data"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        self.valid_zip = os.path.join(self.test_dir, "valid.zip")
        self.invalid_zip = os.path.join(self.test_dir, "invalid.zip")

        # Create valid zip
        with zipfile.ZipFile(self.valid_zip, 'w') as zf:
            zf.writestr("frames.json", "{}")
            zf.writestr("raw_images/test.jpg", "data")
            zf.writestr("depth_maps/test.png", "data")

        # Create invalid zip
        with zipfile.ZipFile(self.invalid_zip, 'w') as zf:
            zf.writestr("frames.json", "{}")
            # Missing dirs

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_zip_validation(self):
        valid, msg = ZipValidator.validate(self.valid_zip)
        self.assertTrue(valid, f"Valid zip failed: {msg}")

        valid, msg = ZipValidator.validate(self.invalid_zip)
        self.assertFalse(valid, "Invalid zip passed")
        self.assertIn("Missing required directories", msg)

if __name__ == '__main__':
    unittest.main()
