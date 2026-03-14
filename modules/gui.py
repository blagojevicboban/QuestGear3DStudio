"""
Main GUI module for QuestStream 3D Processor.
Handles user interaction, thread management, and UI rendering using Flet.
"""

import os
import json
import threading
import time
import shutil
from pathlib import Path
import numpy as np
import flet as ft
from datetime import datetime
import webbrowser

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False
    o3d = None

# Lazy import cv2 to avoid file locking during NerfStudio installation
# cv2 will be imported on-demand when actually needed
cv2 = None

def _ensure_cv2():
    """Lazy-load cv2 module when needed."""
    global cv2
    if cv2 is None:
        import cv2 as cv2_module
        cv2 = cv2_module
    return cv2

import base64
from .config_manager import ConfigManager
from .ingestion import ZipValidator, AsyncExtractor
from .reconstruction import QuestReconstructor
from .image_processing import yuv_to_rgb, filter_depth
from .quest_image_processor import QuestImageProcessor

class ReconstructionThread(threading.Thread):
    """
    Worker thread that handles the 3D reconstruction process for Quest data.
    Uses QuestReconstructionPipeline to process YUV images and raw depth.
    """
    def __init__(self, data_dir, config_manager, on_progress=None, on_status=None, on_log=None, on_finished=None, on_error=None, on_frame=None, start_frame=0, end_frame=None):
        super().__init__()
        self.daemon = True # Ensure thread dies when app closes
        self.data_dir = data_dir
        self.config_manager = config_manager
        self.on_progress = on_progress
        self.on_status = on_status
        self.on_log = on_log
        self.on_finished = on_finished
        self.on_error = on_error
        self.on_frame = on_frame
        self.start_frame = start_frame
        self.end_frame = end_frame
        self._is_running = True

    def run(self):
        try:
            from .quest_reconstruction_pipeline import QuestReconstructionPipeline
            
            if self.on_status:
                self.on_status("Initializing Quest Reconstruction Pipeline...")
            if self.on_log:
                self.on_log("Initializing Quest Reconstruction Pipeline...")
            
            # Create pipeline
            pipeline = QuestReconstructionPipeline(self.data_dir, self.config_manager)
            
            # Run reconstruction
            result = pipeline.run_reconstruction(
                on_progress=lambda p: (
                    self.on_progress(p / 100.0) if self.on_progress else None,
                    self.on_status(f"Processing: {p}%") if self.on_status else None
                ),
                on_log=self.on_log,
                on_frame=self.on_frame,
                is_cancelled=lambda: not self._is_running, # Pass cancellation check
                camera=self.config_manager.get("reconstruction.camera", "left"),
                frame_interval=int(self.config_manager.get("reconstruction.frame_interval", 5)),
                start_frame=self.start_frame,
                end_frame=self.end_frame
            )
            
            if result and result.get('mesh'):
                if self.on_log:
                    self.on_log(f"✓ Reconstruction complete!")
                    if hasattr(result['mesh'], 'vertices'):
                        self.on_log(f"  Vertices: {len(result['mesh'].vertices)}")
                if self.on_finished:
                    self.on_finished(result) # Pass full result dict
            else:
                if self.on_error:
                    self.on_error("Reconstruction failed - no mesh generated")
        
        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
            if self.on_log:
                self.on_log(f"ERROR: {str(e)}")


    def stop(self):
        self._is_running = False

def main(page: ft.Page):
    page.title = "QuestGear 3D Studio"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1024
    page.window_height = 768
    
    config_manager = ConfigManager()
    
    # State
    temp_dirs = [] # List of extracted paths
    current_mesh = None
    frames_data = [] # List of frame objects (aggregated)
    current_extractor = None # Tracking for cancellation
    pending_zip_paths = [] # For confirmation dialog
    
    # --- UI Controls Initialized Early to prevent UnboundLocalError ---
    status_text = ft.Text("Ready")
    progress_bar = ft.ProgressBar(value=0, visible=False)
    log_list = ft.ListView(expand=True, spacing=2, auto_scroll=True)
    preview_img = ft.Image(src="placeholder.png", fit=ft.ImageFit.CONTAIN, visible=False, expand=True)
    viewer_3d = ft.WebView("about:blank", expand=True, visible=False)
    thumb_img = ft.Image(src="placeholder.png", width=320, height=240, fit=ft.ImageFit.CONTAIN, visible=False)
    
    btn_load_zip = ft.ElevatedButton("Load ZIP(s)", icon=ft.Icons.UPLOAD_FILE)
    btn_load_folder = ft.ElevatedButton("Load Folder(s)", icon=ft.Icons.FOLDER_OPEN)
    btn_stop_zip = ft.ElevatedButton("Stop", icon=ft.Icons.STOP, visible=False, bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)
    btn_process = ft.ElevatedButton("Start Reconstruction", disabled=True)
    btn_visualize = ft.ElevatedButton("Open External Window", icon=ft.Icons.OPEN_IN_NEW, disabled=True)
    btn_stop_reconstruct = ft.ElevatedButton("Stop", icon=ft.Icons.STOP, visible=False, bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)
    
    def open_in_external_browser(e):
        import webbrowser
        # Getting the actual local path to viewer.html
        path = os.path.abspath(os.path.join("assets", "viewer.html"))
        # We use a file URL. The browser can load the GLB from the same relative dir or via absolute path
        webbrowser.open(f"file:///{path}")

    btn_open_browser = ft.TextButton(
        "Open in Browser",
        icon=ft.Icons.OPEN_IN_BROWSER,
        visible=False,
        on_click=open_in_external_browser,
        tooltip="If internal viewer fails, open in Chrome/Edge"
    )

    btn_fix_webview = ft.TextButton(
        "Fix Viewer",
        icon=ft.Icons.HANDYMAN,
        visible=False,
        on_click=lambda _: webbrowser.open("https://developer.microsoft.com/en-us/microsoft-edge/webview2/"),
        tooltip="Internal viewer requires 'Microsoft Edge WebView2'. Click to download."
    )

    btn_toggle_view = ft.TextButton(
        "Switch to 3D View", 
        icon=ft.Icons.VIEW_IN_AR, 
        visible=False,
        on_click=lambda _: (
            setattr(preview_img, "visible", not preview_img.visible),
            setattr(viewer_3d, "visible", not viewer_3d.visible),
            setattr(btn_open_browser, "visible", viewer_3d.visible), 
            setattr(btn_fix_webview, "visible", viewer_3d.visible), # Show fix link in 3D mode
            setattr(frame_range_slider, "visible", preview_img.visible),
            setattr(frame_range_label, "visible", preview_img.visible),
            setattr(btn_toggle_view, "text", "Switch to 2D Preview" if preview_img.visible == False else "Switch to 3D View"),
            setattr(btn_toggle_view, "icon", ft.Icons.IMAGE if preview_img.visible == False else ft.Icons.VIEW_IN_AR),
            page.update()
        )
    )

    frame_range_slider = ft.RangeSlider(
        min=0, max=100, 
        start_value=0, end_value=100,
        label="{value}",
        visible=False,
        disabled=True
    )
    frame_range_label = ft.Text("Frame Range: -", visible=False)
    
    current_frame_indicator = ft.Slider(
        min=0, max=100, value=0,
        visible=False,
        disabled=True,
        active_color=ft.Colors.TRANSPARENT,
        inactive_color=ft.Colors.TRANSPARENT,
        thumb_color=ft.Colors.AMBER,
        on_change=lambda _: None  # Read-only
    )
    
    mem_text = ft.Text("RAM: -- MB", size=12, color=ft.Colors.GREY_400)
    
    # Splitter Handling
    video_section_height = 300
    
    def on_splitter_drag(e: ft.DragUpdateEvent):
        nonlocal video_section_height
        video_section_height += e.delta_y
        # Clamp height
        if video_section_height < 150: video_section_height = 150
        if video_section_height > 600: video_section_height = 600
        
        video_container.height = video_section_height
        page.update()

    splitter = ft.GestureDetector(
        on_vertical_drag_update=on_splitter_drag,
        mouse_cursor=ft.MouseCursor.RESIZE_UP_DOWN,
        content=ft.Container(
            bgcolor=ft.Colors.GREY_800,
            height=12,
            content=ft.Icon(ft.Icons.DRAG_HANDLE, size=10, color=ft.Colors.GREY_400),
            alignment=ft.alignment.center,
            border_radius=4,
            tooltip="Drag to resize"
        )
    )

    def update_frame_preview(index, rgb_data=None):
        if not frames_data or index < 0 or index >= len(frames_data):
            return
            
        try:
            # Update current frame indicator (visually moving circle)
            current_frame_indicator.value = index
            current_frame_indicator.visible = True
            try:
                current_frame_indicator.update()
            except: pass
            
            rgb = rgb_data
            if rgb is None:
                # Load frame using QuestImageProcessor if not provided
                # Determine which project directory this frame belongs to
                # For preview, we might need a better way to find the path
                # but currently frames_data is aggregated fs.
                # However, QuestImageProcessor.process_quest_frame needs ONLY the project_dir.
                # We need to find the dir that contains this frame.
                frame_info = frames_data[index]
                
                # Logic to find correct temp_dir for this frame
                found_dir = None
                curr_camera = config_manager.get("reconstruction.camera", "left")
                if curr_camera == "both": curr_camera = "left"
                
                # Check which cameras are available in this frame
                available_cameras = list(frame_info.get('cameras', {}).keys())
                camera_keys_to_try = [curr_camera] + available_cameras
                
                for d in temp_dirs:
                    if not os.path.exists(os.path.join(d, "frames.json")):
                        continue
                    
                    for ck in camera_keys_to_try:
                        cam_data = frame_info.get('cameras', {}).get(ck, {})
                        if not cam_data: continue
                        
                        # Support both 'image' (standard) and 'color_path' (legacy/other)
                        rgb_rel = cam_data.get('image') or cam_data.get('color_path')
                        if rgb_rel and os.path.exists(os.path.join(d, rgb_rel)):
                            found_dir = d
                            break
                    if found_dir: break
                
                if not found_dir and temp_dirs:
                    found_dir = temp_dirs[0]
                
                camera = config_manager.get("reconstruction.camera", "left")
                if camera == 'both' or camera not in available_cameras:
                    # Fallback to whatever camera we found in the loop
                    for ck in camera_keys_to_try:
                        if ck in available_cameras:
                            camera = ck
                            break
                
                rgb, _, _ = QuestImageProcessor.process_quest_frame(
                    found_dir, frame_info, camera=camera
                )
            
            if rgb is not None:
                # Ensure cv2 is loaded before use
                cv2 = _ensure_cv2()
                # Convert to base64 for Flet
                try:
                    is_success, buffer = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
                    if is_success:
                        b64_img = base64.b64encode(buffer).decode("utf-8")
                        preview_img.src_base64 = b64_img
                        preview_img.src = "" # Use empty string instead of None
                        preview_img.visible = True
                        
                        # If we're updating a frame, we likely want the 2D view visible
                        if not viewer_3d.visible:
                             preview_img.visible = True
                        
                        preview_img.update()
                        
                        # Ensure toggle button is visible if we have a preview
                        if not btn_toggle_view.visible:
                            btn_toggle_view.visible = True
                            btn_toggle_view.text = "Switch to 3D View" # Initial state when loading images
                            btn_toggle_view.icon = ft.Icons.VIEW_IN_AR
                            btn_toggle_view.update()
                    else:
                        add_log("Error: Failed to encode preview image.")
                except Exception as encode_err:
                    add_log(f"Error encoding frame: {encode_err}")
            elif rgb_data is None: # Only log if we attempted manual load and failed
                 frame_info = frames_data[index]
                 available_cams = list(frame_info.get('cameras', {}).keys())
                 add_log(f"Warning: Could not load frame {index}. RGB is None. Available cams: {available_cams}")
                 if not found_dir:
                     add_log(f"  Reason: Correct project directory not found for this frame.")
                 else:
                     add_log(f"  Reason: QuestImageProcessor returned None for dir {found_dir}")
                 # Fallback attempt ... (keeping simplified to avoid bloat)
        except Exception as e:
            add_log(f"Preview error: {e}")

    last_range_start = -1
    last_range_end = -1

    def on_range_change(e):
        nonlocal last_range_start, last_range_end
        start = int(e.control.start_value)
        end = int(e.control.end_value)
        
        frame_range_label.value = f"Frame Range: {start} - {end} (Total: {end - start + 1})"
        frame_range_label.update()
        
        # Determine which handle moved to update preview
        if abs(start - last_range_start) > 0:
            update_frame_preview(start)
        elif abs(end - last_range_end) > 0:
            update_frame_preview(end)
            
        last_range_start = start
        last_range_end = end

    frame_range_slider.on_change = on_range_change
    
    def add_log(msg):
        now = datetime.now().strftime("%H:%M:%S")
        log_list.controls.append(ft.Text(f"[{now}] {msg}", font_family="Consolas", size=12, selectable=True))
        if len(log_list.controls) > 100:
            log_list.controls.pop(0)
        try:
            page.update()
        except: pass

    def show_msg(text):
        page.snack_bar = ft.SnackBar(content=ft.Text(text))
        page.snack_bar.open = True
        try:
            page.update()
        except: pass

    def on_img_load_progress(val):
        progress_bar.value = val / 100.0
        page.update()

    def load_frames_ui_from_data(data):
        count = len(data)
        frame_range_slider.min = 0
        frame_range_slider.max = count - 1
        frame_range_slider.start_value = 0
        frame_range_slider.end_value = count - 1
        frame_range_slider.divisions = count
        frame_range_slider.visible = True
        frame_range_slider.disabled = False
        
        frame_range_label.value = f"Aggregate Frame Range: 0 - {count-1} (Total: {count})"
        frame_range_label.visible = True
        
        current_frame_indicator.min = 0
        current_frame_indicator.max = count - 1
        current_frame_indicator.divisions = count
        current_frame_indicator.value = 0
        current_frame_indicator.visible = True
        
        # Ensure we are in 2D preview mode
        preview_img.visible = True
        viewer_3d.visible = False
        btn_toggle_view.visible = True
        btn_toggle_view.text = "Switch to 3D View"
        btn_toggle_view.icon = ft.Icons.VIEW_IN_AR
        
        update_frame_preview(0)
        add_log(f"Aggregated {count} frames from {len(temp_dirs)} projects.")
        show_msg("Data loaded successfully.")

    def aggregate_frames():
        nonlocal frames_data
        frames_data = [] # Reset and aggregate
        
        for d in temp_dirs:
            fj = os.path.join(d, "frames.json")
            if os.path.exists(fj):
                try:
                    with open(fj, 'r') as f:
                        data = json.load(f)
                        fs = data.get('frames', [])
                        frames_data.extend(fs)
                except: pass
        
        if frames_data:
            load_frames_ui_from_data(frames_data)

    def on_img_load_finished(path):
        nonlocal current_extractor
        if path not in temp_dirs:
            temp_dirs.append(path)
        
        current_extractor = None
        progress_bar.visible = False
        btn_stop_zip.visible = False
        btn_load_zip.disabled = False
        btn_load_folder.disabled = False
        status_text.value = f"Loaded {len(temp_dirs)} project(s)"
        add_log(f"Extraction complete: {path}")
        
        frames_json = os.path.join(path, "frames.json")
        if not os.path.exists(frames_json):
            add_log("Quest format detected - converting to frames.json...")
            try:
                from modules.quest_adapter import QuestDataAdapter
                QuestDataAdapter.adapt_quest_data(path)
                add_log(f"✓ Created frames.json")
            except Exception as e:
                add_log(f"ERROR converting Quest data: {str(e)}")
                return
        
        aggregate_frames()
        if pending_zip_paths:
            next_zip = pending_zip_paths.pop(0)
            start_extraction(next_zip)
        else:
            btn_process.disabled = False

    def on_img_load_error(err):
        nonlocal current_extractor
        current_extractor = None
        progress_bar.visible = False
        btn_stop_zip.visible = False
        btn_load_zip.disabled = False
        btn_load_folder.disabled = False
        
        if err == "Stopped":
            status_text.value = "Ready"
            add_log("Extraction safely stopped and cleaned up.")
        else:
            status_text.value = "Extraction Failed"
            add_log(f"Extraction Error: {err}")
            show_msg(f"Error: {err}")
            
        page.update()

    def start_extraction(zip_path):
        nonlocal current_extractor
        btn_load_zip.disabled = True
        btn_load_folder.disabled = True
        btn_process.disabled = True
        btn_stop_zip.visible = True
        progress_bar.visible = True
        
        current_extractor = AsyncExtractor(zip_path, on_progress=on_img_load_progress, on_finished=on_img_load_finished, on_error=on_img_load_error, on_log=add_log)
        current_extractor.start()
        status_text.value = f"Extracting {os.path.basename(zip_path)}..."
        page.update()

    def on_file_result(e: ft.FilePickerResultEvent):
        nonlocal pending_zip_paths, temp_dirs, frames_data
        if e.files:
            temp_dirs = [] 
            frames_data = []
            pending_zip_paths = [f.path for f in e.files]
            if pending_zip_paths:
                first_zip = pending_zip_paths.pop(0)
                start_extraction(first_zip)

    def on_folder_result(e: ft.FilePickerResultEvent):
        if e.path:
            path = e.path
            if path not in temp_dirs:
                temp_dirs.append(path)
            
            fj = os.path.join(path, "frames.json")
            if not os.path.exists(fj):
                try:
                    from modules.quest_adapter import QuestDataAdapter
                    QuestDataAdapter.adapt_quest_data(path)
                    add_log(f"✓ Adapted {path}")
                except: pass
            
            aggregate_frames()
            btn_process.disabled = False
            status_text.value = f"Loaded {len(temp_dirs)} project(s)"
            page.update()
    def stop_zip_extraction(e):
        if current_extractor:
            add_log("STOP signal sent to extractor...")
            current_extractor.stop()
            btn_stop_zip.visible = False
            status_text.value = "Stopping..."
            page.update()

    def stop_reconstruction(e):
        if thread:
            add_log("STOP signal sent to reconstruction...")
            thread.stop()
            status_text.value = "Stopping reconstruction..."
            btn_stop_reconstruct.visible = False
            page.update()

    # File Pickers
    file_picker = ft.FilePicker(on_result=on_file_result)
    folder_picker = ft.FilePicker(on_result=on_folder_result)
    settings_folder_picker = ft.FilePicker(on_result=lambda e: (setattr(initial_dir_input, "value", e.path), page.update()) if e.path else None)

    format_dropdown_start = ft.Dropdown(
        label="Select Export Format",
        value=config_manager.get("export.format", "glb"),
        options=[
            ft.dropdown.Option("ply", "PLY (Point Cloud/Mesh)"),
            ft.dropdown.Option("obj", "OBJ (Standard Mesh)"),
            ft.dropdown.Option("glb", "GLB (Binary GLTF)"),
        ],
        width=300
    )

    def on_recon_frame(index, rgb_data=None):
        update_frame_preview(index, rgb_data)

    def confirm_start_reconstruction(e):
        page.close(reconstruct_format_dialog)
        
        config_manager.set("export.format", format_dropdown_start.value)
        
        if not temp_dirs:
            add_log("Error: No data loaded.")
            return
        
        btn_process.disabled = True
        btn_load_zip.disabled = True
        btn_load_folder.disabled = True
        btn_stop_reconstruct.visible = True
        frame_range_slider.disabled = True 
        status_text.value = f"Initializing ({format_dropdown_start.value.upper()})..."
        status_text.color = None
        progress_bar.visible = True
        progress_bar.value = None
        page.update()
        
        start_frame = int(frame_range_slider.start_value) if frame_range_slider.visible else 0
        end_frame = int(frame_range_slider.end_value) if frame_range_slider.visible else None
        
        nonlocal thread
        thread = ReconstructionThread(
            temp_dirs,
            config_manager,
            on_progress=on_reconstruct_progress,
            on_status=lambda msg: (setattr(status_text, "value", msg), page.update()),
            on_log=add_log,
            on_finished=on_reconstruct_finished,
            on_error=on_reconstruct_error,
            on_frame=on_recon_frame,
            start_frame=start_frame,
            end_frame=end_frame
        )
        thread.start()

    reconstruct_format_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Reconstruction Format"),
        content=ft.Column([
            ft.Text("Choose the output format for the 3D model:"),
            format_dropdown_start
        ], tight=True, height=100),
        actions=[
            ft.TextButton("Start", on_click=confirm_start_reconstruction),
            ft.TextButton("Cancel", on_click=lambda _: page.close(reconstruct_format_dialog)),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.overlay.extend([file_picker, folder_picker, settings_folder_picker, reconstruct_format_dialog])

    # Assign Handlers to buttons defined at top
    btn_load_zip.on_click = lambda _: file_picker.pick_files(
        dialog_title="Open Quest Capture ZIP(s)",
        allowed_extensions=["zip"],
        allow_multiple=True,
        initial_directory=config_manager.get("app_settings.initial_directory") if os.path.exists(config_manager.get("app_settings.initial_directory", "")) else None
    )
    btn_load_folder.on_click = lambda _: folder_picker.get_directory_path(
        dialog_title="Open Extracted Quest Data Folder(s)",
        initial_directory=config_manager.get("app_settings.initial_directory") if os.path.exists(config_manager.get("app_settings.initial_directory", "")) else None
    )
    btn_stop_zip.on_click = stop_zip_extraction
    btn_process.on_click = lambda e: page.open(reconstruct_format_dialog)
    btn_stop_reconstruct.on_click = stop_reconstruction

    
    # Placeholder for thread reference to allow cancellation from button
    thread = None

    def on_reconstruct_progress(val):
        progress_bar.value = val
        try:
            page.update()
        except: pass

    # viewer_3d already defined above

    def update_internal_viewer(glb_path):
        """Copies the GLB to assets and refreshes the internal 3D viewer."""
        try:
            if not glb_path or not os.path.exists(glb_path):
                return
            
            # Ensure assets directory exists
            assets_dir = Path("assets")
            assets_dir.mkdir(exist_ok=True)
            
            # Copy model to assets for serving
            target_path = assets_dir / "current_model.glb"
            shutil.copy2(glb_path, target_path)
            
            # Set URL with cache buster
            viewer_url = f"/viewer.html?model=current_model.glb&t={time.time()}"
            viewer_3d.url = viewer_url
            viewer_3d.visible = True
            
            # Switch view modes
            preview_img.visible = False
            viewer_3d.visible = True
            btn_toggle_view.visible = True
            btn_toggle_view.text = "Switch to 2D Preview"
            frame_range_slider.visible = False
            frame_range_label.visible = False
            
            add_log("🚀 3D Model loaded in internal viewer")
            try:
                page.update()
            except: pass
        except Exception as ex:
            add_log(f"Internal Viewer Error: {ex}")

    def on_reconstruct_finished(result):
        nonlocal current_mesh
        current_mesh = result.get('mesh')
        mesh = current_mesh
        
        # Get actual exported filename and path from result
        full_path = result.get('output_path')
        if full_path:
            filename = os.path.basename(full_path)
        else:
            fmt = config_manager.get("export.format", "obj")
            filename = f"reconstruction.{fmt}"
            # Use first temp_dir as default output base if full_path is missing
            base_dir = temp_dirs[0] if temp_dirs else "."
            full_path = os.path.join(base_dir, filename)
        
        status_text.value = "Reconstruction Complete! (3D Visualizer Enabled)"
        status_text.color = ft.Colors.GREEN_400
        btn_process.disabled = False
        
        # Make Visualizer button "glow"
        btn_visualize.disabled = False
        btn_visualize.bgcolor = ft.Colors.GREEN_700
        btn_visualize.color = ft.Colors.WHITE
        btn_visualize.scale = 1.05
        
        btn_load_zip.disabled = False
        btn_load_folder.disabled = False
        btn_stop_reconstruct.visible = False
        frame_range_slider.disabled = False # Re-enable slider
        
        add_log(f"✓ Reconstruction finished: {len(mesh.vertices)} vertices.")
        add_log("✨ 3D Visualizer is now available!")
        
        # Verify file and update title/logs
        if full_path and os.path.exists(full_path):
            add_log(f"✓ File saved: {filename}")
            add_log(f"  Path: {full_path}")
            page.title = f"QuestGear 3D Studio - {filename}"
            show_msg(f"Success! 3D Visualizer is ready.")
        else:
            add_log(f"⚠ Mesh extracted but file {filename} not found.")
            page.title = "QuestGear 3D Studio"
            
        progress_bar.visible = False
        
        # Check for thumbnail
        if temp_dirs:
            thumb_path = os.path.join(temp_dirs[0], "thumbnail.png")
            if os.path.exists(thumb_path):
                # Force reload by adding timestamp
                thumb_img.src = f"{thumb_path}?t={time.time()}" 
                thumb_img.visible = True
        
        # Load in Internal 3D Viewer if GLB is available
        if full_path and full_path.lower().endswith('.glb'):
            update_internal_viewer(full_path)
        
        try:
            page.update()
        except: pass

    def on_reconstruct_error(err):
        status_text.value = "Data Loaded" if temp_dirs else "Ready"
        btn_process.disabled = False
        btn_visualize.disabled = current_mesh is None
        btn_load_zip.disabled = False
        btn_load_folder.disabled = False
        btn_stop_reconstruct.visible = False
        frame_range_slider.disabled = False # Re-enable slider
        add_log(f"Reconstruction Info: {err}")
        progress_bar.visible = False
        try:
            page.update()
        except: pass

    def start_reconstruction(e):
        # This now just opens the format selection dialog
        page.open(reconstruct_format_dialog)

    btn_process.on_click = start_reconstruction

    def show_visualizer(e):
        # Reset "glow" when clicked
        btn_visualize.bgcolor = None
        btn_visualize.color = None
        btn_visualize.scale = 1.0
        btn_visualize.update()
        
        if not HAS_OPEN3D:
            show_msg("Visualizer not available (Open3D missing).")
            return
            
        if current_mesh and hasattr(current_mesh, 'vertices') and len(current_mesh.vertices) > 0:
            try:
                add_log("Opening 3D Visualizer...")
                vis = o3d.visualization.Visualizer()
                vis.create_window(window_name="QuestStream Result", width=1024, height=768)
                vis.add_geometry(current_mesh)
                
                # Setup render options for better visibility
                opt = vis.get_render_option()
                opt.background_color = np.asarray([0.1, 0.1, 0.1])
                opt.point_size = 2.0
                
                vis.run() # This blocks until window is closed
                vis.destroy_window()
                add_log("Visualizer closed.")
            except Exception as ex:
                add_log(f"Visualizer Error: {ex}")
                show_msg(f"Visualizer Error: {ex}")
        else:
            show_msg("No mesh to visualize.")

    btn_visualize.on_click = show_visualizer

    # Settings Dialog
    voxel_input = ft.TextField(label="Voxel Size (m)", value=str(config_manager.get("reconstruction.voxel_size", 0.02)))
    depth_max_input = ft.TextField(label="Max Depth (m)", value=str(config_manager.get("reconstruction.depth_max", 10.0)))
    frame_int_input = ft.TextField(label="Frame Interval", value=str(config_manager.get("reconstruction.frame_interval", 5)))
    camera_dropdown = ft.Dropdown(
        label="Camera",
        value=config_manager.get("reconstruction.camera", "left"),
        options=[
            ft.dropdown.Option("left", "Left Camera (Grayscale)"),
            ft.dropdown.Option("right", "Right Camera (Grayscale)"),
            ft.dropdown.Option("both", "Stereo (Both)"),
            ft.dropdown.Option("color", "RGB Camera (Color)"),
        ]
    )
    filter_check = ft.Checkbox(label="Filter Depth", value=config_manager.get("reconstruction.use_confidence_filtered_depth", True))
    
    enable_drift_check = ft.Checkbox(
        label="Enable Drift Correction (SLAM)", 
        value=config_manager.get("reconstruction.enable_drift_correction", True),
        tooltip="Corrects long-term tracking drift using GICP and Loop Closure. Recommended for large rooms."
    )
    
    refinement_method_dropdown = ft.Dropdown(
        label="Refinement Method",
        value=config_manager.get("reconstruction.refinement_method", "gicp"),
        options=[
            ft.dropdown.Option("icp", "Local ICP"),
            ft.dropdown.Option("gicp", "Generalized ICP (Accurate)"),
        ],
        width=250
    )
    
    enable_inpainting_check = ft.Checkbox(
        label="AI Depth Inpainting (Fill Holes)", 
        value=config_manager.get("reconstruction.enable_inpainting", False),
        tooltip="Uses MiDaS AI to fill holes in glossy surfaces. Note: Heavy on CPU/GPU."
    )
    
    acceleration_backend_dropdown = ft.Dropdown(
        label="Acceleration Backend",
        value=config_manager.get("reconstruction.acceleration_backend", "auto"),
        options=[
            ft.dropdown.Option("auto", "Auto Detection"),
            ft.dropdown.Option("cuda", "NVIDIA CUDA"),
            ft.dropdown.Option("directml", "DirectML (AMD/Intel)"),
            ft.dropdown.Option("cpu", "CPU Only (Safe)"),
        ],
        width=250
    )
    
    # Post-Processing & Export
    smoothing_input = ft.TextField(label="Smoothing Iterations", value=str(config_manager.get("post_processing.smoothing_iterations", 5)))
    decimation_input = ft.TextField(label="Target Triangles", value=str(config_manager.get("post_processing.decimation_target_triangles", 100000)))
    
    enable_poisson_check = ft.Checkbox(
        label="Poisson Surface Reconstruction (Solid)", 
        value=config_manager.get("post_processing.enable_poisson", False),
        tooltip="Creates a water-tight (solid) mesh. Best for 3D printing or closing large holes."
    )
    
    poisson_depth_slider = ft.Slider(
        min=5, max=12, divisions=7, 
        label="Poisson Detail: {value}",
        value=config_manager.get("post_processing.poisson_depth", 8)
    )
    export_fmt_dropdown = ft.Dropdown(
        label="Export Format",
        value=config_manager.get("export.format", "glb"),
        options=[
            ft.dropdown.Option("ply", "PLY (Standard)"),
            ft.dropdown.Option("obj", "OBJ (Universal)"),
            ft.dropdown.Option("glb", "GLB (Web/AR)"),
        ]
    )
    
    enable_texturing_check = ft.Checkbox(
        label="Advanced Texturing (UV Mapping)", 
        value=config_manager.get("export.enable_texturing", True),
        tooltip="Generate a texture atlas (.png) instead of vertex colors. Best for game engines."
    )
    
    texture_size_dropdown = ft.Dropdown(
        label="Texture Resolution",
        value=str(config_manager.get("export.texture_size", 2048)),
        options=[
            ft.dropdown.Option("1024", "1024 x 1024"),
            ft.dropdown.Option("2048", "2048 x 2048"),
            ft.dropdown.Option("4096", "4096 x 4096 (High Res)"),
        ],
        width=200
    )
    
    initial_dir_input = ft.TextField(
        label="Initial Scan Directory", 
        value=config_manager.get("app_settings.initial_directory", "D:\\METAQUEST"),
        hint_text="e.g. D:\\METAQUEST or C:\\Users\\Name\\Documents",
        expand=True
    )

    def save_settings(e):
        try:
            config_manager.set("reconstruction.voxel_size", float(voxel_input.value))
            config_manager.set("reconstruction.depth_max", float(depth_max_input.value))
            config_manager.set("reconstruction.frame_interval", int(frame_int_input.value))
            config_manager.set("reconstruction.camera", camera_dropdown.value)
            config_manager.set("reconstruction.use_confidence_filtered_depth", filter_check.value)
            config_manager.set("reconstruction.enable_drift_correction", enable_drift_check.value)
            config_manager.set("reconstruction.refinement_method", refinement_method_dropdown.value)
            config_manager.set("reconstruction.enable_inpainting", enable_inpainting_check.value)
            config_manager.set("reconstruction.acceleration_backend", acceleration_backend_dropdown.value)
            
            # Post-processing
            config_manager.set("post_processing.smoothing_iterations", int(smoothing_input.value))
            config_manager.set("post_processing.decimation_target_triangles", int(decimation_input.value))
            config_manager.set("post_processing.enable_poisson", enable_poisson_check.value)
            config_manager.set("post_processing.poisson_depth", int(poisson_depth_slider.value))
            config_manager.set("export.format", export_fmt_dropdown.value)
            config_manager.set("export.enable_texturing", enable_texturing_check.value)
            config_manager.set("export.texture_size", int(texture_size_dropdown.value))
            
            # App Settings
            config_manager.set("app_settings.initial_directory", initial_dir_input.value)
            
            # NerfStudio Settings
            if 'nerfstudio_ui' in locals() or 'nerfstudio_ui' in globals():
                config_manager.set("nerfstudio.max_iterations", int(nerfstudio_ui.iterations_input.value))
                config_manager.set("nerfstudio.method", nerfstudio_ui.method_dropdown.value)
                config_manager.set("nerfstudio.preset", nerfstudio_ui.preset_dropdown.value)
            
            show_msg("Settings saved")
        except ValueError:
            show_msg("Invalid numerical values")

    # ==== NerfStudio Integration ====
    from .nerfstudio_gui import NerfStudioUI
    from .help_gui import HelpUI
    
    nerfstudio_ui = NerfStudioUI(
        page=page,
        on_log=add_log,
        temp_dir_getter=lambda: temp_dirs[0] if temp_dirs else None,
        config_manager=config_manager
    )

    help_ui = HelpUI(page=page)

    # Settings Tab Content
    settings_tab_content = ft.Container(
        padding=20,
        content=ft.Column([
            ft.Text("Application Settings", size=24, weight="bold"),
            ft.Text("Configure global parameters for reconstruction and UI behavior."),
            ft.Divider(),
            ft.ResponsiveRow([
                ft.Column([
                    ft.Text("Reconstruction Engine", size=18, weight="bold"),
                    voxel_input,
                    depth_max_input,
                    frame_int_input,
                    camera_dropdown,
                    filter_check,
                    enable_drift_check,
                    refinement_method_dropdown,
                    enable_inpainting_check,
                    acceleration_backend_dropdown,
                ], col={"sm": 12, "md": 6}),
                ft.Column([
                    ft.Text("Post-Processing & Export", size=18, weight="bold"),
                    smoothing_input,
                    decimation_input,
                    enable_poisson_check,
                    ft.Text("Poisson Detail Level:"),
                    poisson_depth_slider,
                    export_fmt_dropdown,
                    enable_texturing_check,
                    texture_size_dropdown,
                    ft.Divider(),
                    ft.Text("Neural Rendering (NerfStudio)", size=18, weight="bold"),
                    nerfstudio_ui.method_dropdown,
                    nerfstudio_ui.preset_dropdown,
                    nerfstudio_ui.iterations_input,
                    ft.Divider(),
                    ft.Text("Application Paths", size=18, weight="bold"),
                    ft.Row([
                        initial_dir_input,
                        ft.IconButton(
                            icon=ft.Icons.FOLDER_OPEN,
                            tooltip="Browse Directory",
                            on_click=lambda _: settings_folder_picker.get_directory_path(
                                initial_directory=initial_dir_input.value if os.path.exists(initial_dir_input.value) else None
                            )
                        )
                    ])
                ], col={"sm": 12, "md": 6}),
            ]),
            ft.Row([
                ft.ElevatedButton("Save All Settings", 
                                icon=ft.Icons.SAVE, 
                                bgcolor=ft.Colors.BLUE_700,
                                color=ft.Colors.WHITE,
                                on_click=save_settings),
                ft.TextButton("Reset to Defaults", on_click=lambda _: show_msg("Reset not implemented yet"))
            ], alignment=ft.MainAxisAlignment.CENTER, height=80)
        ], scroll=ft.ScrollMode.AUTO)
    )

    # Layout - Now with Tabs
    # page.appbar removed as requested - all settings are in the Settings tab

    # TSDF Reconstruction Tab (existing functionality)
    tsdf_tab_content = ft.Container(
        content=ft.Column([
            ft.Row([
                btn_load_zip,
                btn_load_folder,
                btn_stop_zip,
                btn_process,
                btn_stop_reconstruct,
                btn_visualize,
                ft.Container(content=mem_text, padding=10)
            ]),
            video_container := ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("Visualizer & Frames:", weight="bold"),
                        ft.VerticalDivider(),
                        btn_toggle_view,
                        btn_open_browser,
                        btn_fix_webview
                    ]),
                    ft.Stack([
                        preview_img,
                        viewer_3d,
                    ], expand=True),
                    ft.Stack([
                        ft.TransparentPointer(current_frame_indicator),
                        frame_range_slider,
                    ], height=40),
                    frame_range_label
                ]),
                padding=10,
                bgcolor="#151515",
                border_radius=10,
                height=400,
                animate_size=300
            ),
            splitter,
            progress_bar,
            status_text,
            thumb_img,
            ft.Divider(),
            ft.Text("Process Logs:", size=16, weight="bold"),
            ft.Container(
                content=log_list,
                expand=True,
                bgcolor="#1e1e1e",
                border_radius=5,
                padding=10
            )
        ], expand=True),
        expand=True
    )

    # Tab navigation
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(
                text="TSDF Reconstruction",
                icon=ft.Icons.VIEW_IN_AR,
                content=tsdf_tab_content
            ),
            nerfstudio_ui.get_tab(),
            ft.Tab(
                text="Settings",
                icon=ft.Icons.SETTINGS,
                content=settings_tab_content
            ),
            help_ui.get_tab(),
        ],
        expand=True
    )

    # Branding Overlay (Placed in the top-right of the Tabs bar)
    branding_overlay = ft.Container(
        padding=ft.padding.only(right=25, top=2),
        content=ft.Row([
            ft.Image(src="logo.png", width=100, height=50, border_radius=10),
            ft.Text("QuestGear 3D Studio", size=32, weight="bold", color=ft.Colors.BLUE_400),
            ft.Text("v2.1", size=14, color=ft.Colors.GREY_700),
        ], spacing=15, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.END),
    )

    main_layout = ft.Stack([
        tabs,
        branding_overlay # This will float on top of the tabs row on the right
    ], expand=True)

    page.add(main_layout)
    
    def on_window_event(e):
        if e.data == "close":
            if thread and thread.is_alive():
                thread.stop()
            page.window_destroy()

    page.on_window_event = on_window_event
    page.update()
    
    # Start NerfStudio installation check after page is ready
    nerfstudio_ui.start_installation_check()

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
