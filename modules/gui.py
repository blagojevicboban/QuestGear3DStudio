import os
import json
import cv2
import numpy as np
import open3d as o3d
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QProgressBar, QMessageBox)

from .config_manager import ConfigManager
from .ingestion import ZipValidator, AsyncExtractor
from .reconstruction import QuestReconstructor
from .image_processing import yuv_to_rgb, filter_depth

class ReconstructionThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(object) # signal emitting the final mesh
    error = pyqtSignal(str)

    def __init__(self, data_dir, config_manager):
        super().__init__()
        self.data_dir = data_dir
        self.config_manager = config_manager
        self._is_running = True

    def run(self):
        try:
            self.status.emit("Initializing Reconstructor...")
            reconstructor = QuestReconstructor(self.config_manager)
            
            # Load frames.json
            frames_path = os.path.join(self.data_dir, "frames.json")
            with open(frames_path, "r") as f:
                frames_data = json.load(f)
            
            if isinstance(frames_data, list):
                # Handle list of frames format
                pass
            elif isinstance(frames_data, dict) and "frames" in frames_data:
                frames_data = frames_data["frames"]
            
            total_frames = len(frames_data)
            
            for i, frame in enumerate(frames_data):
                if not self._is_running:
                    break
                
                # Assuming 'file_path' or timestamp linkage
                # Fallbck to timestamp-based filenames
                timestamp = frame.get("timestamp")
                
                # Try to determine paths
                if "file_path" in frame:
                    img_path = os.path.join(self.data_dir, frame["file_path"])
                    # Assume depth path is similar or in depth_maps/
                    depth_path = img_path.replace("raw_images", "depth_maps").replace(".jpg", ".png").replace(".bin", ".bin") 
                else:
                    # Construct paths based on description
                    # raw_images/timestamp.[bin|yuv]
                    # depth_maps/timestamp.[bin|depth]
                    # We'll check for common extensions
                    base_img = os.path.join(self.data_dir, "raw_images", str(timestamp))
                    if os.path.exists(base_img + ".bin"): img_path = base_img + ".bin"
                    elif os.path.exists(base_img + ".yuv"): img_path = base_img + ".yuv"
                    else: img_path = None
                    
                    base_depth = os.path.join(self.data_dir, "depth_maps", str(timestamp))
                    if os.path.exists(base_depth + ".bin"): depth_path = base_depth + ".bin"
                    elif os.path.exists(base_depth + ".depth"): depth_path = base_depth + ".depth"
                    else: depth_path = None

                if not img_path or not os.path.exists(img_path):
                    print(f"Skipping frame {i}: Image not found {img_path}")
                    continue

                # Parse Intrinsics & Pose
                # intrinsics: [fx, fy, cx, cy] or 3x3 matrix?
                # prompt says: "intrinsics: Camera focal length and principal point."
                intrinsics_data = frame.get("intrinsics")
                if isinstance(intrinsics_data, list) and len(intrinsics_data) == 4:
                    fx, fy, cx, cy = intrinsics_data
                    intrinsics = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])
                    w, h = int(cx * 2), int(cy * 2)
                elif isinstance(intrinsics_data, dict):
                    fx = intrinsics_data.get("fx", 0)
                    fy = intrinsics_data.get("fy", 0)
                    cx = intrinsics_data.get("cx", 0)
                    cy = intrinsics_data.get("cy", 0)
                    intrinsics = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])
                    w, h = int(cx * 2), int(cy * 2)
                else:
                    print(f"Skipping frame {i}: Invalid intrinsics format")
                    continue

                # Parse Pose (4x4 matrix)
                pose_data = frame.get("pose")
                pose = np.array(pose_data).reshape(4, 4)

                # Load Raw Images
                # YUV420 reading
                # Size: w * h * 1.5 bytes
                # We need exact resolution. 
                # If we don't have it, we might fail.
                
                with open(img_path, 'rb') as f:
                    yuv_data = np.frombuffer(f.read(), dtype=np.uint8)
                    yuv_img = yuv_data.reshape((int(h * 1.5), w))
                    rgb = yuv_to_rgb(yuv_img)

                # Load Depth (16-bit or 32-bit float?)
                # Prompt: "Normalized 16-bit or 32-bit depth buffers"
                # If 16-bit, it's usually millimeters.
                with open(depth_path, 'rb') as f:
                    # Try reading as uint16 first
                    depth_data = np.frombuffer(f.read(), dtype=np.uint16)
                    if depth_data.size != w * h:
                        # Maybe float32?
                        f.seek(0)
                        depth_data = np.frombuffer(f.read(), dtype=np.float32)
                    
                    depth = depth_data.reshape((h, w))

                # Filtering (Optional)
                if self.config_manager.get("reconstruction.use_confidence_filtered_depth"):
                    depth = filter_depth(depth)

                # Integration
                reconstructor.integrate_frame(rgb, depth, intrinsics, pose)
                
                self.status.emit(f"Processed frame {i+1}/{total_frames}")
                self.progress.emit(int(((i + 1) / total_frames) * 100))
                
            self.status.emit("Extracting Mesh...")
            mesh = reconstructor.extract_mesh()
            self.finished.emit(mesh)
            
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._is_running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.setWindowTitle("QuestStream 3D Processor")
        self.resize(1024, 768)
        self.init_ui()
        self.temp_dir = None

    def init_ui(self):
        # Menu Bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        
        open_action = file_menu.addAction("Load ZIP")
        open_action.triggered.connect(self.load_zip)
        
        settings_action = file_menu.addAction("Settings")
        settings_action.triggered.connect(self.open_settings)
        
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Top Controls
        controls_layout = QHBoxLayout()
        self.btn_process = QPushButton("Start Reconstruction")
        self.btn_process.setEnabled(False)
        self.btn_process.clicked.connect(self.start_reconstruction)
        controls_layout.addWidget(self.btn_process)
        
        self.btn_visualize = QPushButton("Visualizer (External)")
        self.btn_visualize.setEnabled(False)
        self.btn_visualize.clicked.connect(self.show_visualizer)
        controls_layout.addWidget(self.btn_visualize)
        
        layout.addLayout(controls_layout)

        # Progress
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Placeholder for 3D View (or results info)
        self.info_label = QLabel("No Data Loaded")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("background-color: #333; color: #fff; font-size: 14px;")
        layout.addWidget(self.info_label, stretch=1)

    def open_settings(self):
        dialog = SettingsDialog(self.config_manager, self)
        if dialog.exec():
            self.status_label.setText("Settings saved.")

    def load_zip(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Quest Capture ZIP", "", "ZIP Files (*.zip)")
        if file_path:
            self.status_label.setText("Validating ZIP...")
            valid, msg = ZipValidator.validate(file_path)
            if not valid:
                QMessageBox.critical(self, "Error", f"Invalid ZIP: {msg}")
                return
            
            self.status_label.setText("Extracting...")
            self.progress_bar.setRange(0, 0) # Indeterminate
            
            self.extractor = AsyncExtractor(file_path)
            self.extractor.finished.connect(self.on_extraction_finished)
            self.extractor.error.connect(self.on_extraction_error)
            self.extractor.start()

    def on_extraction_finished(self, temp_dir):
        self.temp_dir = temp_dir
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Extracted to {temp_dir}")
        self.btn_process.setEnabled(True)
        QMessageBox.information(self, "Success", "Data loaded successfully.")

    def on_extraction_error(self, msg):
        self.progress_bar.setRange(0, 100)
        self.status_label.setText("Extraction Failed")
        QMessageBox.critical(self, "Error", f"Extraction failed: {msg}")

    def start_reconstruction(self):
        if not self.temp_dir:
            return
            
        self.btn_process.setEnabled(False)
        self.reconstructor_thread = ReconstructionThread(self.temp_dir, self.config_manager)
        self.reconstructor_thread.progress.connect(self.progress_bar.setValue)
        self.reconstructor_thread.status.connect(self.status_label.setText)
        self.reconstructor_thread.finished.connect(self.on_reconstruction_finished)
        self.reconstructor_thread.error.connect(self.on_reconstruction_error)
        self.reconstructor_thread.start()

    def on_reconstruction_finished(self, mesh):
        self.current_mesh = mesh
        self.status_label.setText("Reconstruction Complete")
        self.btn_process.setEnabled(True)
        self.btn_visualize.setEnabled(True)
        self.info_label.setText(f"Mesh generated with {len(mesh.vertices)} vertices.")
        
        # Auto-save for convenience
        # o3d.io.write_triangle_mesh("output.ply", mesh)

    def on_reconstruction_error(self, msg):
        self.status_label.setText("Reconstruction Failed")
        self.btn_process.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Reconstruction error: {msg}")

    def show_visualizer(self):
        if hasattr(self, 'current_mesh') and self.current_mesh:
            o3d.visualization.draw_geometries([self.current_mesh], window_name="QuestStream Result")

