"""
Main GUI module for QuestStream 3D Processor.
Handles user interaction, thread management, and UI rendering using Flet.
"""

import os
import json
import threading
import time
import numpy as np
import flet as ft
from datetime import datetime

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False
    o3d = None

from .config_manager import ConfigManager
from .ingestion import ZipValidator, AsyncExtractor
from .reconstruction import QuestReconstructor
from .image_processing import yuv_to_rgb, filter_depth

class ReconstructionThread(threading.Thread):
    """
    Worker thread that handles the 3D reconstruction process.
    Iterates through frames, processes images, and integrates them into the TSDF volume.
    """
    def __init__(self, data_dir, config_manager, on_progress=None, on_status=None, on_log=None, on_finished=None, on_error=None):
        super().__init__()
        self.data_dir = data_dir
        self.config_manager = config_manager
        self.on_progress = on_progress
        self.on_status = on_status
        self.on_log = on_log
        self.on_finished = on_finished
        self.on_error = on_error
        self._is_running = True

    def run(self):
        try:
            if self.on_status: self.on_status("Initializing Reconstructor...")
            if self.on_log: self.on_log("Initializing Reconstructor...")
            reconstructor = QuestReconstructor(self.config_manager)
            
            # Load frames.json
            if self.on_log: self.on_log(f"Loading frames from {self.data_dir}")
            frames_path = os.path.join(self.data_dir, "frames.json")
            with open(frames_path, "r") as f:
                frames_data = json.load(f)
            
            if isinstance(frames_data, list):
                pass
            elif isinstance(frames_data, dict) and "frames" in frames_data:
                frames_data = frames_data["frames"]
            
            total_frames = len(frames_data)
            
            for i, frame in enumerate(frames_data):
                if not self._is_running:
                    break
                
                timestamp = frame.get("timestamp")
                
                if "file_path" in frame:
                    img_path = os.path.join(self.data_dir, frame["file_path"])
                    depth_path = img_path.replace("raw_images", "depth_maps").replace(".jpg", ".png").replace(".bin", ".bin") 
                else:
                    base_img = os.path.join(self.data_dir, "raw_images", str(timestamp))
                    if os.path.exists(base_img + ".bin"): img_path = base_img + ".bin"
                    elif os.path.exists(base_img + ".yuv"): img_path = base_img + ".yuv"
                    else: img_path = None
                    
                    base_depth = os.path.join(self.data_dir, "depth_maps", str(timestamp))
                    if os.path.exists(base_depth + ".bin"): depth_path = base_depth + ".bin"
                    elif os.path.exists(base_depth + ".depth"): depth_path = base_depth + ".depth"
                    else: depth_path = None

                if not img_path or not os.path.exists(img_path):
                    if self.on_log: self.on_log(f"Skipping frame {i}: Image not found {img_path}")
                    continue

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
                    if self.on_log: self.on_log(f"Skipping frame {i}: Invalid intrinsics format")
                    continue

                pose_data = frame.get("pose")
                pose = np.array(pose_data).reshape(4, 4)

                with open(img_path, 'rb') as f:
                    yuv_data = np.frombuffer(f.read(), dtype=np.uint8)
                    yuv_img = yuv_data.reshape((int(h * 1.5), w))
                    rgb = yuv_to_rgb(yuv_img)

                with open(depth_path, 'rb') as f:
                    depth_data = np.frombuffer(f.read(), dtype=np.uint16)
                    if depth_data.size != w * h:
                        f.seek(0)
                        depth_data = np.frombuffer(f.read(), dtype=np.float32)
                    
                    depth = depth_data.reshape((h, w))

                if self.config_manager.get("reconstruction.use_confidence_filtered_depth"):
                    depth = filter_depth(depth)

                reconstructor.integrate_frame(rgb, depth, intrinsics, pose)
                
                msg = f"Processed frame {i+1}/{total_frames}"
                if self.on_status: self.on_status(msg)
                if self.on_log: self.on_log(msg)
                if self.on_progress: self.on_progress((i + 1) / total_frames)
                
            if self.on_log: self.on_log("Extracting Mesh...")
            if self.on_status: self.on_status("Extracting Mesh...")
            mesh = reconstructor.extract_mesh()
            if self.on_log: self.on_log(f"Mesh extraction complete. Vertices: {len(mesh.vertices)}")
            if self.on_finished: self.on_finished(mesh)
            
        except Exception as e:
            if self.on_error: self.on_error(str(e))
            if self.on_log: self.on_log(f"ERROR: {str(e)}")

    def stop(self):
        self._is_running = False

def main(page: ft.Page):
    page.title = "QuestStream 3D Processor"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1024
    page.window_height = 768
    
    config_manager = ConfigManager()
    
    # State
    temp_dir = None
    current_mesh = None
    
    # Controls
    status_text = ft.Text("Ready")
    progress_bar = ft.ProgressBar(value=0, visible=False)
    log_list = ft.ListView(expand=True, spacing=2, auto_scroll=True)
    
    btn_process = ft.ElevatedButton("Start Reconstruction", disabled=True)
    btn_visualize = ft.ElevatedButton("Visualizer (External)", disabled=True)

    def add_log(msg):
        now = datetime.now().strftime("%H:%M:%S")
        log_list.controls.append(ft.Text(f"[{now}] {msg}", font_family="Consolas", size=12))
        if len(log_list.controls) > 100:
            log_list.controls.pop(0)
        page.update()

    def show_msg(text):
        page.snack_bar = ft.SnackBar(content=ft.Text(text))
        page.snack_bar.open = True
        page.update()

    def on_img_load_progress(val):
        progress_bar.value = val / 100.0
        page.update()

    def on_img_load_finished(path):
        nonlocal temp_dir
        temp_dir = path
        progress_bar.visible = False
        status_text.value = f"Extracted to {path}"
        btn_process.disabled = False
        show_msg("Data loaded successfully.")

    def on_img_load_error(err):
        progress_bar.visible = False
        status_text.value = "Extraction Failed"
        add_log(f"Extraction Error: {err}")
        show_msg(f"Error: {err}")

    def load_zip_result(e):
        if e.files and len(e.files) > 0:
            file_path = e.files[0].path
            log_list.controls.clear()
            add_log(f"Selected file: {file_path}")
            
            status_text.value = "Validating ZIP structure..."
            page.update()
            
            add_log("Starting ZIP validation...")
            valid, msg = ZipValidator.validate(file_path, log_callback=add_log)
            if not valid:
                status_text.value = "Invalid ZIP"
                show_msg(f"Invalid ZIP: {msg}")
                add_log(f"Validation FAILED: {msg}")
                return

            status_text.value = "Extracting..."
            progress_bar.visible = True
            progress_bar.value = None
            page.update()
            
            extractor = AsyncExtractor(
                file_path,
                on_progress=on_img_load_progress,
                on_finished=on_img_load_finished,
                on_error=on_img_load_error,
                on_log=add_log
            )
            extractor.start()

    file_picker = ft.FilePicker()
    file_picker.on_result = load_zip_result
    page.overlay.append(file_picker)

    def on_reconstruct_progress(val):
        progress_bar.value = val
        page.update()

    def on_reconstruct_finished(mesh):
        nonlocal current_mesh
        current_mesh = mesh
        status_text.value = "Reconstruction Complete"
        btn_process.disabled = False
        btn_visualize.disabled = False
        add_log(f"Reconstruction finished with {len(mesh.vertices)} vertices.")
        progress_bar.visible = False
        page.update()

    def on_reconstruct_error(err):
        status_text.value = "Reconstruction Failed"
        btn_process.disabled = False
        add_log(f"Reconstruction Error: {err}")
        progress_bar.visible = False
        show_msg(f"Error: {err}")

    def start_reconstruction(e):
        if not temp_dir:
            return
        
        btn_process.disabled = True
        status_text.value = "Initializing..."
        progress_bar.visible = True
        progress_bar.value = 0
        page.update()
        
        thread = ReconstructionThread(
            temp_dir,
            config_manager,
            on_progress=on_reconstruct_progress,
            on_status=lambda s: (setattr(status_text, "value", s) or page.update()),
            on_log=add_log,
            on_finished=on_reconstruct_finished,
            on_error=on_reconstruct_error
        )
        thread.start()

    btn_process.on_click = start_reconstruction

    def show_visualizer(e):
        if not HAS_OPEN3D:
            show_msg("Visualizer not available (Open3D missing).")
            return
            
        if current_mesh and hasattr(current_mesh, 'vertices') and len(current_mesh.vertices) > 0:
            o3d.visualization.draw_geometries([current_mesh], window_name="QuestStream Result")
        else:
            show_msg("No mesh to visualize.")

    btn_visualize.on_click = show_visualizer

    # Settings Dialog
    voxel_input = ft.TextField(label="Voxel Size (m)", value=str(config_manager.get("reconstruction.voxel_size", 0.01)))
    depth_max_input = ft.TextField(label="Max Depth (m)", value=str(config_manager.get("reconstruction.depth_max", 3.0)))
    filter_check = ft.Checkbox(label="Filter Depth", value=config_manager.get("reconstruction.use_confidence_filtered_depth", True))

    def save_settings(e):
        try:
            config_manager.set("reconstruction.voxel_size", float(voxel_input.value))
            config_manager.set("reconstruction.depth_max", float(depth_max_input.value))
            config_manager.set("reconstruction.use_confidence_filtered_depth", filter_check.value)
            settings_dialog.open = False
            show_msg("Settings saved")
        except ValueError:
            show_msg("Invalid numerical values")

    settings_dialog = ft.AlertDialog(
        title=ft.Text("Settings"),
        content=ft.Column([voxel_input, depth_max_input, filter_check], tight=True),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: (setattr(settings_dialog, "open", False), page.update())),
            ft.TextButton("Save", on_click=save_settings),
        ],
    )

    def open_settings(e):
        page.dialog = settings_dialog
        settings_dialog.open = True
        page.update()

    # Layout
    page.appbar = ft.AppBar(
        title=ft.Text("QuestStream 3D Processor"),
        bgcolor=ft.Colors.BLUE_800,
        actions=[
            ft.IconButton(icon=ft.Icons.SETTINGS, on_click=open_settings),
        ]
    )

    main_layout = ft.Column([
        ft.Row([
            ft.ElevatedButton("Load ZIP", icon=ft.Icons.UPLOAD_FILE, on_click=lambda _: file_picker.pick_files(
                dialog_title="Open Quest Capture ZIP",
                allowed_extensions=["zip"],
                initial_directory="D:\\METAQUEST" if os.path.exists("D:\\METAQUEST") else None
            )),
            btn_process,
            btn_visualize
        ]),
        progress_bar,
        status_text,
        ft.Divider(),
        ft.Text("Process Logs:", size=16, weight="bold"),
        ft.Container(
            content=log_list,
            expand=True,
            bgcolor="#1e1e1e",
            border_radius=5,
            padding=10
        )
    ], expand=True)

    page.add(main_layout)
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
