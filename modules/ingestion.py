"""
Data ingestion module for QuestStream.
Handles ZIP file validation and asynchronous extraction.
"""

import zipfile
import os
import shutil
import tempfile
import json


class ZipValidator:
    """Utility class for validating Meta Quest capture ZIP files."""
    REQUIRED_FILES = ["frames.json"]
    REQUIRED_DIRS = ["raw_images", "depth_maps"]

    @staticmethod
    def validate(zip_path, log_callback=None):
        """Validate ZIP file structure with optional logging."""
        def log(msg):
            if log_callback:
                log_callback(msg)
        
        if not zipfile.is_zipfile(zip_path):
            log("ERROR: Not a valid ZIP file.")
            return False, "Not a valid ZIP file."
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Check structure only for quick validation
                file_list = zf.namelist()
                log(f"ZIP contains {len(file_list)} items.")
                
                # Show first few files to understand structure
                log("First 10 items in ZIP:")
                for i, f in enumerate(file_list[:10]):
                    log(f"  - {f}")
                
                # Look for frames.json anywhere in the structure (not just root)
                frames_json_found = any('frames.json' in f for f in file_list)
                if not frames_json_found:
                    log("WARNING: frames.json not found anywhere in ZIP")
                    log("Checking for alternative metadata files...")
                    # Look for any JSON files
                    json_files = [f for f in file_list if f.endswith('.json')]
                    if json_files:
                        log(f"Found {len(json_files)} JSON file(s): {json_files[:5]}")
                    else:
                        log("ERROR: No JSON metadata files found")
                        return False, "Missing metadata file (frames.json or similar)"
                else:
                    log(f"✓ Found frames.json")
                
                # Check directories (look for image and depth files)
                has_images = any('rgb' in f.lower() or 'image' in f.lower() or '.png' in f.lower() or '.jpg' in f.lower() for f in file_list)
                has_depth = any('depth' in f.lower() for f in file_list)
                
                if has_images:
                    log(f"✓ Found image files")
                else:
                    log("WARNING: No image files detected")
                
                if has_depth:
                    log(f"✓ Found depth map files")
                else:
                    log("WARNING: No depth map files detected")
                
                # If we have at least images, proceed
                if has_images or len(file_list) > 100:
                    log("✓ Validation passed (flexible mode)")
                    return True, "Validation successful (flexible mode)"
                else:
                    return False, "ZIP does not appear to contain Quest capture data"
                
        except Exception as e:
            return False, f"Validation error: {str(e)}"

import threading

class AsyncExtractor(threading.Thread):
    def __init__(self, zip_path, on_progress=None, on_finished=None, on_error=None, on_log=None):
        super().__init__()
        self.zip_path = zip_path
        self.temp_dir = None
        self.on_progress = on_progress
        self.on_finished = on_finished
        self.on_error = on_error
        self.on_log = on_log

    def run(self):
        try:
            # Create extraction directory next to the ZIP file
            zip_dir = os.path.dirname(self.zip_path)
            zip_name = os.path.splitext(os.path.basename(self.zip_path))[0]
            self.temp_dir = os.path.join(zip_dir, f"{zip_name}_extracted")
            
            # Remove old extraction folder if it exists
            if os.path.exists(self.temp_dir):
                if self.on_log: self.on_log(f"Removing old extraction folder...")
                shutil.rmtree(self.temp_dir)
            
            if self.on_log: self.on_log(f"Creating extraction directory: {self.temp_dir}")
            os.makedirs(self.temp_dir, exist_ok=True)
            
            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                file_list = zf.namelist()
                total_files = len(file_list)
                if self.on_log: self.on_log(f"Found {total_files} items. Starting extraction to {self.temp_dir}...")
                
                # Log throttling to avoid flooding UI thread
                log_every = max(1, total_files // 20) 
                
                for i, file in enumerate(file_list):
                    if i % log_every == 0:
                        if self.on_log: self.on_log(f"[{i+1}/{total_files}] Extracting: {file}")
                    
                    zf.extract(file, self.temp_dir)
                    if self.on_progress: self.on_progress(int((i + 1) / total_files * 100))
            
            if self.on_log: self.on_log(f"SUCCESS: Extracted {total_files} files.")
            if self.on_finished: self.on_finished(self.temp_dir)
            
        except Exception as e:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            if self.on_error: self.on_error(str(e))
            if self.on_log: self.on_log(f"ERROR: {str(e)}")
