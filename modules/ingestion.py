import zipfile
import os
import shutil
import tempfile
import json
from PyQt6.QtCore import QThread, pyqtSignal

class ZipValidator:
    REQUIRED_FILES = ["frames.json"]
    REQUIRED_DIRS = ["raw_images", "depth_maps"]

    @staticmethod
    def validate(zip_path):
        if not zipfile.is_zipfile(zip_path):
            return False, "Not a valid ZIP file."
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Check CRC
                bad_file = zf.testzip()
                if bad_file:
                    return False, f"CRC check failed for: {bad_file}"
                
                # Check structure
                file_list = zf.namelist()
                for req in ZipValidator.REQUIRED_FILES:
                    if req not in file_list:
                        return False, f"Missing required file: {req}"
                
                # Check directories (naive check)
                # We expect paths starting with required dirs
                found_dirs = set()
                for f in file_list:
                    for d in ZipValidator.REQUIRED_DIRS:
                        if f.startswith(d + "/"):
                            found_dirs.add(d)
                
                if len(found_dirs) < len(ZipValidator.REQUIRED_DIRS):
                    missing = set(ZipValidator.REQUIRED_DIRS) - found_dirs
                    return False, f"Missing required directories: {', '.join(missing)}"

                return True, "Validation successful."
                
        except Exception as e:
            return False, f"Validation error: {str(e)}"

class AsyncExtractor(QThread):
    finished = pyqtSignal(str) # Emits path to extracted folder
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, zip_path):
        super().__init__()
        self.zip_path = zip_path
        self.temp_dir = None

    def run(self):
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="quest_stream_")
            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                file_list = zf.namelist()
                total_files = len(file_list)
                
                for i, file in enumerate(file_list):
                    zf.extract(file, self.temp_dir)
                    self.progress.emit(int((i + 1) / total_files * 100))
            
            self.finished.emit(self.temp_dir)
            
        except Exception as e:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            self.error.emit(str(e))
