"""
NerfStudio GUI Module
Provides Flet UI components for NerfStudio integration including:
- Installation/Update manager
- Training configuration
- Progress monitoring
- Results viewer
"""

import flet as ft
import subprocess
import threading
import os
from pathlib import Path
from typing import Callable, Optional
from .nerfstudio_trainer import NerfStudioTrainer


class NerfStudioUI:
    """Manages NerfStudio UI components and state."""
    
    def __init__(self, page: ft.Page, on_log: Callable[[str], None], temp_dir_getter: Callable[[], str]):
        self.page = page
        self.on_log = on_log
        self.temp_dir_getter = temp_dir_getter  # Function to get current scan path
        self.trainer = NerfStudioTrainer()
        self.is_installed = False
        self.installation_thread = None
        
        # Batch Processing
        self.batch_queue = []
        self.is_batch_processing = False
        self.current_batch_index = -1

        # UI Components
        self.setup_ui()
        
        # DON'T check installation immediately - will be called after page is ready
        # Use start_installation_check() method from GUI after initialization
    
    def start_installation_check(self):
        """Start background installation check. Call this after page is fully loaded."""
        threading.Thread(target=self._check_installation_async, daemon=True).start()
    
    def _get_nerfstudio_python(self) -> str:
        """Get path to the dedicated NerfStudio python executable."""
        # Use a separate venv for NerfStudio to avoid conflicts
        venv_name = "nerfstudio_venv"
        return os.path.abspath(os.path.join(os.getcwd(), venv_name, "Scripts", "python.exe"))

    def _check_installation_async(self):
        """Check if NerfStudio is installed (in background)."""
        import time
        time.sleep(0.5)  # Small delay to ensure page is ready
        
        ns_python = self._get_nerfstudio_python()
        
        # Check if python exists in separate env
        if not os.path.exists(ns_python):
            self.is_installed = False
        else:
            # Check if nerfstudio is importable in that env
            try:
                cmd = [ns_python, "-c", "import nerfstudio; print('ok')"]
                # Use subprocess to check without raising exception if module missing
                result = subprocess.run(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                    check=False  # Don't raise CalledProcessError
                )
                self.is_installed = (result.returncode == 0)
            except Exception:
                self.is_installed = False
        
        # Update UI on main thread (safely)
        try:
            self._update_installation_status()
        except:
            # If page not ready, try with run_task
            try:
                self.page.run_task(self._update_installation_status)
            except:
                pass  # Silently fail if page still not ready

    def _update_installation_status(self):
        """Update UI based on installation status."""
        if self.is_installed:
            self.install_status_text.value = "✅ NerfStudio Installed (Dedicated Env)"
            self.install_status_text.color = ft.Colors.GREEN
            self.btn_install.text = "Update NerfStudio"
            self.btn_install.icon = ft.Icons.SYSTEM_UPDATE
            self.btn_uninstall.visible = True  # Show uninstall when installed
            self.btn_uninstall.visible = True  # Show uninstall when installed
            self.training_container.disabled = False
            self.batch_container.disabled = False
            self.history_container.disabled = False
            self.btn_train.disabled = False  # Enable button - validation happens on click
        else:
            self.install_status_text.value = "❌ NerfStudio Not Found"
            self.install_status_text.color = ft.Colors.RED
            self.btn_install.text = "Install NerfStudio (Safe Mode)"
            self.btn_install.icon = ft.Icons.DOWNLOAD
            self.btn_uninstall.visible = False  # Hide uninstall when not installed
            self.training_container.disabled = True
            self.batch_container.disabled = True
            self.history_container.disabled = True
            self.btn_train.disabled = True
        
        self.page.update()
    
    def setup_ui(self):
        """Create all UI components."""
        
        # ====== Installation Section ======
        self.install_status_text = ft.Text("Checking...", color=ft.Colors.GREY)
        self.btn_install = ft.ElevatedButton(
            "Install NerfStudio",
            icon=ft.Icons.DOWNLOAD,
            on_click=self._on_install_click
        )
        self.btn_uninstall = ft.ElevatedButton(
            "Uninstall",
            icon=ft.Icons.DELETE_FOREVER,
            on_click=self._on_uninstall_click,
            visible=False,
            bgcolor=ft.Colors.RED_700,
            color=ft.Colors.WHITE
        )
        self.install_progress = ft.ProgressBar(visible=False)
        
        # Use ListView for install log to enable scrolling
        self.install_log = ft.ListView(
            expand=True,
            spacing=2,
            padding=5,
            auto_scroll=True,
            height=150
        )
        self.install_log_container = ft.Container(
            content=self.install_log,
            bgcolor="#1e1e1e",
            border=ft.border.all(1, ft.Colors.GREY_800),
            border_radius=5,
            padding=5,
            height=150,
            visible=False # Hidden initially
        )
        
        # ====== Training Configuration ======
        self.method_dropdown = ft.Dropdown(
            label="Training Method",
            value="splatfacto",
            options=[
                ft.dropdown.Option("splatfacto", "⚡ Splatfacto (Gaussian Splatting) - Fast, Excellent"),
                ft.dropdown.Option("nerfacto", "🎯 Nerfacto (NeRF) - Balanced"),
                ft.dropdown.Option("instant-ngp", "🚀 Instant-NGP - Ultra Fast"),
                ft.dropdown.Option("depth-nerfacto", "📊 Depth-Nerfacto - Requires Depth"),
            ],
            width=400,
            on_change=self._on_method_change
        )
        
        self.method_description = ft.Text(
            NerfStudioTrainer.METHODS['splatfacto']['description'],
            size=11,
            color=ft.Colors.GREY_400
        )

        self.preset_dropdown = ft.Dropdown(
            label="Quality Preset",
            value="Balanced",
            options=[
                ft.dropdown.Option("Fast", NerfStudioTrainer.PRESETS['Fast']['description']),
                ft.dropdown.Option("Balanced", NerfStudioTrainer.PRESETS['Balanced']['description']),
                ft.dropdown.Option("Quality", NerfStudioTrainer.PRESETS['Quality']['description']),
            ],
            width=300,
            on_change=self._on_preset_change
        )
        
        self.iterations_input = ft.TextField(
            label="Max Iterations",
            value="30000",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        self.btn_train = ft.ElevatedButton(
            "Start Training",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self._on_train_click,
            disabled=True
        )
        
        self.btn_stop = ft.ElevatedButton(
            "Stop Training",
            icon=ft.Icons.STOP,
            on_click=self._on_stop_click,
            visible=False,
            bgcolor=ft.Colors.RED_700,
            color=ft.Colors.WHITE
        )
        
        # ====== Progress Monitor ======
        self.training_progress = ft.ProgressBar(value=0, visible=False)
        self.progress_text = ft.Text("", size=12)
        self.eta_text = ft.Text("", size=11, color=ft.Colors.GREY_400)
        self.loss_text = ft.Text("", size=11, color=ft.Colors.BLUE_400)
        self.psnr_text = ft.Text("", size=11, color=ft.Colors.GREEN_400)
        
        # ====== Results ======
        # ====== Results ======
        self.btn_open_viewer = ft.ElevatedButton(
            "Open Viewer",
            icon=ft.Icons.VISIBILITY,
            on_click=self._on_open_viewer,
            visible=False
        )
        self.output_path_text = ft.Text("", size=11, selectable=True)
        
        # ====== Training Logs ======
        self.training_log = ft.ListView(
            expand=True,
            spacing=2,
            padding=5,
            auto_scroll=True,
            height=200
        )
        self.training_log_container = ft.Container(
            content=self.training_log,
            bgcolor="#1e1e1e",
            border=ft.border.all(1, ft.Colors.GREY_800),
            border_radius=5,
            padding=5,
            height=200,
            visible=True # Always visible to ensure user sees logs
        )
        # Thread safety lock for logs
        self.log_lock = threading.Lock()
        self.log_buffer = []
        self.is_log_updater_running = False
        
        self.training_container = ft.Container(
            content=ft.Column([
                ft.Text("Training Configuration", weight="bold", size=16),
                self.method_dropdown,
                self.method_description,
                self.preset_dropdown, # Added preset dropdown
                self.iterations_input,
                ft.Divider(),
                ft.Row([self.btn_train, self.btn_stop]),
                ft.Container(height=10),
                ft.Row([
                    ft.ElevatedButton(
                        "Generate Monocular Depth",
                        icon=ft.Icons.AUTO_GRAPH,
                        on_click=self._on_generate_mono_depth_click,
                        tooltip="Use MiDaS to estimate depth from color images (fallback)"
                    ),
                    self.eta_text, # Reusing for depth gen ETA too 
                ]),
                self.training_progress,
                self.progress_text,
                self.eta_text,
                ft.Row([self.loss_text, self.psnr_text]),
                ft.Divider(),
                self.training_log_container, # Add log container here
                self.btn_open_viewer,
                self.output_path_text,
            ]),
            padding=15,
            disabled=True
        )

        # ====== Batch Processing ======
        self.batch_list = ft.ListView(height=100, spacing=2, auto_scroll=True)
        self.btn_add_batch = ft.ElevatedButton("Add to Queue", icon=ft.Icons.QUEUE, on_click=self._on_add_batch)
        self.btn_clear_batch = ft.ElevatedButton("Clear", icon=ft.Icons.CLEAR_ALL, on_click=self._on_clear_batch)
        self.btn_start_batch = ft.ElevatedButton("Start Batch", icon=ft.Icons.PLAY_CIRCLE, on_click=self._on_start_batch, disabled=True)
        
        self.batch_container = ft.Container(
            content=ft.Column([
                ft.Text("Batch Queue", weight="bold", size=16),
                ft.Container(
                    content=self.batch_list,
                    bgcolor="#1e1e1e",
                    border=ft.border.all(1, ft.Colors.GREY_800),
                    border_radius=5,
                    padding=5,
                    height=100
                ),
                ft.Row([self.btn_add_batch, self.btn_clear_batch, self.btn_start_batch]),
            ]),
            padding=15,
            bgcolor="#2a2a2a",
            border_radius=10,
            margin=10,
            disabled=True # Enabled when installed
        )

        # ====== Export Section ======
        self.export_format = ft.Dropdown(
            label="Format",
            value="ply",
            options=[
                ft.dropdown.Option("ply", "PLY (PointCloud/Splat)"),
                ft.dropdown.Option("obj", "OBJ (Mesh)"),
                ft.dropdown.Option("glb", "GLB (Mesh/Scene)"),
            ],
            width=150
        )
        self.btn_export = ft.ElevatedButton("Export Model", icon=ft.Icons.FILE_UPLOAD, on_click=self._on_export_click)
        self.export_status = ft.Text("", size=12)
        
        self.export_container = ft.Container(
            content=ft.Column([
                ft.Text("Export Results", weight="bold", size=16),
                ft.Row([self.export_format, self.btn_export]),
                self.export_status
            ]),
            padding=15,
            bgcolor="#2a2a2a",
            border_radius=10,
            margin=10,
            visible=False 
        )

        # ====== History ======
        self.history_list = ft.ListView(height=150, spacing=2, auto_scroll=False)
        self.btn_refresh_history = ft.ElevatedButton("Refresh History", icon=ft.Icons.REFRESH, on_click=self._refresh_history)
        
        self.history_container = ft.Container(
            content=ft.Column([
                ft.Text("Model History", weight="bold", size=16),
                ft.Container(
                    content=self.history_list,
                    bgcolor="#1e1e1e",
                    border=ft.border.all(1, ft.Colors.GREY_800),
                    border_radius=5,
                    padding=5,
                    height=150
                ),
                self.btn_refresh_history
            ]),
            padding=15,
            bgcolor="#2a2a2a",
            border_radius=10,
            margin=10,
            disabled=True # Enabled when installed
        )
    
    def get_tab(self) -> ft.Tab:
        """Return the NerfStudio tab for main GUI."""
        return ft.Tab(
            text="NerfStudio",
            icon=ft.Icons.AUTO_AWESOME,  # Star/sparkle icon for neural rendering
            content=ft.Container(
                content=ft.ListView([
                    ft.Container(
                        content=ft.Column([
                            ft.Text("🌟 NerfStudio Integration", size=20, weight="bold"),
                            ft.Text(
                                "Train Gaussian Splatting and NeRF models directly from your scans. "
                                "No depth required for color-only reconstruction!",
                                size=12,
                                color=ft.Colors.GREY_400
                            ),
                        ]),
                        padding=15,
                        bgcolor=ft.Colors.BLUE_900,
                        border_radius=10,
                        margin=10
                    ),
                    
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Installation Status", weight="bold", size=16),
                            self.install_status_text,
                            ft.Row([self.btn_install, self.btn_uninstall]),
                            self.install_progress,
                            self.install_log_container,
                        ]),
                        padding=15,
                        bgcolor="#2a2a2a",
                        border_radius=10,
                        margin=10
                    ),
                    
                    ft.Container(
                        content=self.training_container,
                        bgcolor="#2a2a2a",
                        border_radius=10,
                        margin=10
                    ),
                    self.batch_container,
                    self.export_container,
                    self.history_container,
                ], padding=10),
                expand=True
            )
        )
    
    def _on_method_change(self, e):
        """Update description when method changes."""
        method = e.control.value
        if method in NerfStudioTrainer.METHODS:
            info = NerfStudioTrainer.METHODS[method]
            self.method_description.value = f"{info['description']} | Speed: {info['speed']}, Quality: {info['quality']}"
            self.page.update()
    
    def _on_preset_change(self, e):
        """Update training parameters based on preset."""
        preset = e.control.value
        if preset in NerfStudioTrainer.PRESETS:
            config = NerfStudioTrainer.PRESETS[preset]
            self.iterations_input.value = str(config['max_iterations'])
            self.page.update()
    
    def _on_install_click(self, e):
        """Handle install/update button click."""
        if self.installation_thread and self.installation_thread.is_alive():
            self._show_message("Installation already in progress")
            return
        
        self.btn_install.disabled = True
        self.install_progress.visible = True
        self.install_log.value = "Starting installation..."
        self.page.update()
        
        self.installation_thread = threading.Thread(
            target=self._install_nerfstudio,
            daemon=True
        )
        self.installation_thread.start()
    
    def _on_uninstall_click(self, e):
        """Show confirmation dialog for uninstallation."""
        def close_dlg(e):
            dlg.open = False
            self.page.update()
            
        def confirm_uninstall(e):
            dlg.open = False
            self.page.update()
            self._do_uninstall()

        dlg = ft.AlertDialog(
            title=ft.Text("Uninstall NerfStudio?"),
            content=ft.Text("This will remove NerfStudio and all its dependencies from the virtual environment. This cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.TextButton("Yes, Uninstall", on_click=confirm_uninstall, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        dlg.open = True
        self.page.overlay.append(dlg)
        self.page.update()

    def _do_uninstall(self):
        """Start the uninstallation thread."""
        if self.installation_thread and self.installation_thread.is_alive():
            self._show_message("A process is already in progress")
            return
            
        self.btn_install.disabled = True
        self.btn_uninstall.disabled = True
        self.install_progress.visible = True
        self.install_log.value = "Starting uninstallation..."
        self.page.update()
        
        self.installation_thread = threading.Thread(
            target=self._uninstall_nerfstudio,
            daemon=True
        )
        self.installation_thread.start()

    def _uninstall_nerfstudio(self):
        """Uninstall NerfStudio using pip."""
        import sys
        
        try:
            self._update_install_log("Uninstalling NerfStudio...")
            
            uninstall_cmd = [
                sys.executable,
                '-m', 'pip',
                'uninstall',
                '-y',  # Auto-confirm
                'nerfstudio'
            ]
            
            process = subprocess.Popen(
                uninstall_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            for line in process.stdout:
                line = line.strip()
                if line:
                    self._update_install_log(line)
            
            if process.wait() == 0:
                self._update_install_log("✅ Uninstallation successful!")
                self.on_log("NerfStudio uninstalled")
            else:
                self._update_install_log("❌ Uninstallation failed")
                self.on_log("NerfStudio uninstallation failed")
                
            # Re-check status
            threading.Thread(target=self._check_installation_async, daemon=True).start()
            
        except Exception as ex:
            self._update_install_log(f"❌ Error: {ex}")
            self.on_log(f"NerfStudio uninstall error: {ex}")
        
        finally:
            self.btn_install.disabled = False
            self.btn_uninstall.disabled = False
            self.btn_uninstall.visible = False # It's gone now
            self.install_progress.visible = False
            self.page.update()
    
    def _install_nerfstudio(self):
        """Install/update NerfStudio in dedicated env."""
        import sys
        
        target_python = self._get_nerfstudio_python()
        venv_dir = os.path.dirname(os.path.dirname(target_python)) # .../nerfstudio_venv
        
        try:
            self._update_install_log(f"Creating dedicated environment in: {venv_dir}...")
            
            # 1. Create venv if not exists
            if not os.path.exists(target_python):
                import venv
                self._update_install_log("Initializing new virtual environment...")
                venv.create(venv_dir, with_pip=True)
                self._update_install_log("✅ Environment created.")

            # 2. Upgrade pip
            self._update_install_log("Upgrading pip...")
            subprocess.run([target_python, "-m", "pip", "install", "--upgrade", "pip"], 
                           creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)

            # 3. Install PyTorch with CUDA (Critical Step!)
            # Updated to CUDA 11.8 for broader compatibility (Quadro P600, etc.)
            self._update_install_log("Step 1/3: Installing PyTorch (cuda 11.8)...")
            torch_cmd = [
                target_python, "-m", "pip", "install", 
                "torch==2.1.2+cu118", "torchvision==0.16.2+cu118", "torchaudio==2.1.2+cu118",
                "--index-url", "https://download.pytorch.org/whl/cu118",
                "--no-cache-dir",
                "--force-reinstall"
            ]
            
            proc = subprocess.Popen(
                torch_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            ) 
            for line in proc.stdout:
                if line.strip(): self._update_install_log(line.strip())
            proc.wait()

            # 4. Install NerfStudio & Dependencies
            self._update_install_log("Step 2/3: Installing NerfStudio & core libs...")
            self._update_install_log("  → Ensuring numpy compatibility (<2.0)...")
            subprocess.run([target_python, "-m", "pip", "install", "numpy<2.0.0"], 
                           creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            # gsplat needs special handling - install from official wheel repo with CUDA binaries
            # Pinned to 1.4.0 for stability with older GPUs
            self._update_install_log("  → Installing gsplat 1.4.0 with CUDA support...")
            gsplat_cmd = [
                target_python, "-m", "pip", "install", 
                "gsplat==1.4.0",
                "--find-links", "https://docs.gsplat.studio/whl/",
                "--no-cache-dir",
                "--no-deps",
                "--force-reinstall"
            ]
            proc_gsplat = subprocess.Popen(
                gsplat_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            for line in proc_gsplat.stdout:
                 if line.strip() and ('ERROR' in line or 'Successfully' in line): 
                     self._update_install_log(f"    {line.strip()}")
            proc_gsplat.wait()
            
            # Install remaining components
            self._update_install_log("  → Installing nerfstudio and dependencies...")
            ns_cmd = [
                target_python, "-m", "pip", "install", 
                "nerfstudio==1.1.5", "nerfacc", "viser", "tensorboard",
                "--no-warn-script-location"
            ]
            
            proc = subprocess.Popen(
                ns_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            for line in proc.stdout:
                 if line.strip(): self._update_install_log(line.strip())
            
            if proc.wait() == 0:
                # Verify gsplat installation (silently)
                try:
                    verify_cmd = [target_python, "-c", "from gsplat import csrc; print('OK')"]
                    verify_result = subprocess.run(
                        verify_cmd, 
                        capture_output=True, 
                        text=True,
                        stderr=subprocess.DEVNULL,  # Suppress error output to avoid debugger breaks
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                        timeout=10  # Prevent hanging
                    )
                    gsplat_ok = (verify_result.returncode == 0)
                except Exception:
                    gsplat_ok = False
                
                if not gsplat_ok:
                    self._update_install_log("⚠️  gsplat installation incomplete (missing CUDA binaries)")
                    self._update_install_log("ℹ️  This is a known issue on Windows.")
                    self._update_install_log("📌 SOLUTION: Use 'nerfacto' method instead of 'splatfacto'")
                    self._update_install_log("   OR install Visual Studio Build Tools:")
                    self._update_install_log("   https://visualstudio.microsoft.com/downloads/")
                    self._update_install_log("")
                    self._update_install_log("✅ NerfStudio installed (nerfacto method available)")
                    self.is_installed = True
                    self.on_log("NerfStudio installed (nerfacto only - gsplat build failed)")
                else:
                    self._update_install_log("✅ Installation successful (all methods available)!")
                    self.is_installed = True
                    self.on_log("NerfStudio installed in dedicated env")
            else:
                self._update_install_log("❌ Installation failed.")
            
            # Refresh status
            self._check_installation_async()
            
        except Exception as ex:
            self._update_install_log(f"❌ Error: {ex}")
            import traceback
            self._update_install_log(traceback.format_exc())
        
        finally:
            self.btn_install.disabled = False
            self.install_progress.visible = False
            self.page.update()
            self._installation_complete()
    
    def _installation_complete(self):
        """Called when installation finishes."""
        self.btn_install.disabled = False
        self.install_progress.visible = False
        self.page.update()
    
    def _update_install_log(self, text: str):
        """Append text to install log."""
        self.install_log.controls.append(ft.Text(text, size=11, font_family="Consolas"))
        if len(self.install_log.controls) > 1000:
            self.install_log.controls.pop(0)

        # Ensure log container is visible
        if hasattr(self, 'install_log_container'):
            self.install_log_container.visible = True

        self.page.update()

    
    def _on_train_click(self, e):
        """Start training."""
        temp_dir = self.temp_dir_getter()
        if not temp_dir:
            self._show_message("Please load a scan first")
            return
        
        if self.trainer.is_running:
            self._show_message("Training already in progress")
            return
        
        # Validate iterations
        try:
            max_iters = int(self.iterations_input.value)
            if max_iters < 1000:
                self._show_message("Iterations must be at least 1000")
                return
        except ValueError:
            self._show_message("Invalid iterations value")
            return
        
        method = self.method_dropdown.value
        
        self.on_log(f"Starting NerfStudio training: {method}")
        self.btn_train.disabled = True
        self.btn_stop.visible = True
        self.training_progress.visible = True
        self.training_progress.value = 0
        self.progress_text.value = "Initializing..."
        self.output_path_text.value = "" # Clear previous path
        self.page.update()
        
        success = self.trainer.start_training(
            data_path=temp_dir,
            method=method,
            max_iterations=max_iters,
            progress_callback=self._on_training_progress,
            completion_callback=self._on_training_complete,
            log_callback=self._on_training_log
        )
        
        if success:
            self.training_log.controls.clear()
            self.training_log_container.visible = True
            
            # Show viewer button during training
            self.btn_open_viewer.visible = True
            
            self.page.update()
        else:
            self.btn_train.disabled = False
            self.btn_stop.visible = False
            self.training_progress.visible = False
            self._show_message("Failed to start training")
            self.page.update()
    
    def _on_training_log(self, line: str):
        """Handle raw log output from training - Thread Safe & Buffered."""
        should_start = False
        
        # Handle carriage returns and newlines (prevent excessive empty lines)
        if '\r' in line:
            line = line.replace('\r', '\n')
        
        # Filter out empty lines or just whitespace
        segments = [s.rstrip() for s in line.split('\n') if s.strip()]
        
        if not segments:
            return

        with self.log_lock:
            self.log_buffer.extend(segments)
            if not self.is_log_updater_running:
                self.is_log_updater_running = True
                should_start = True
        
        if should_start:
            threading.Thread(target=self._log_updater_loop, daemon=True).start()
    
    def _log_updater_loop(self):
        """Accumulate logs and update UI periodically."""
        import time
        while self.log_buffer or self.trainer.is_running:
            # If buffer empty, wait a bit
            if not self.log_buffer:
                time.sleep(0.5)
                continue
                
            # Grab all pending logs
            with self.log_lock:
                lines = self.log_buffer[:]
                self.log_buffer.clear()
            
            if not lines:
                continue

            # Performance: If we have too many logs pending (lag), just show the latest ones
            # to prevent freezing the UI with thousands of updates.
            if len(lines) > 50:
                lines = lines[-50:]
                lines.insert(0, "... [skipped info logs due to high volume] ...")

            # Update UI
            # We use a copy of the list to avoid locking during UI update
            new_controls = []
            for line in lines:
                new_controls.append(
                    ft.Text(line.rstrip(), size=10, font_family="Consolas", color=ft.Colors.GREEN_400)
                )
            
            self.training_log.controls.extend(new_controls)
            
            # Prune if too long
            if len(self.training_log.controls) > 500:
                del self.training_log.controls[:len(self.training_log.controls) - 500]
            
            try:
                self.page.update()
            except Exception:
                pass # Page might be closed or busy
            
            time.sleep(0.5) # Max 2 updates per second to prevent freezing
        
        with self.log_lock:
            self.is_log_updater_running = False

    def _on_stop_click(self, e):
        """Stop training."""
        self.btn_stop.disabled = True
        self.btn_stop.text = "Stopping..."
        self.page.update()
        
        # Run stop in a thread to not block UI
        threading.Thread(target=self.trainer.stop_training, daemon=True).start()
    
    def _on_training_progress(self, info: dict):
        """Handle training progress updates."""
        step = info.get('step', 0)
        total = info.get('total_steps', 30000)
        loss = info.get('loss')
        psnr = info.get('psnr')
        eta = info.get('eta_seconds')
        
        # Update progress bar
        if total > 0:
            self.training_progress.value = step / total
        
        # Update text
        self.progress_text.value = f"Step {step:,} / {total:,}"
        
        if eta is not None:
            minutes = eta // 60
            seconds = eta % 60
            self.eta_text.value = f"ETA: {minutes}m {seconds}s"
        
        if loss is not None:
            self.loss_text.value = f"Loss: {loss:.5f}"
        
        if psnr is not None:
            self.psnr_text.value = f"PSNR: {psnr:.2f} dB"
        
        self.page.update()
    
    def _on_training_complete(self, success: bool, output_path: str):
        """Handle training completion."""
        self.btn_train.disabled = False
        self.btn_stop.visible = False
        self.training_progress.visible = False
        
        if success:
            self.on_log(f"✅ Training completed! Output: {output_path}")
            self.output_path_text.value = f"{output_path}" # Modified to just path for cleaner usage
            self.btn_open_viewer.visible = True
            self.export_container.visible = True # Show export
            self._show_message("Training completed successfully!")
            
            if self.is_batch_processing:
                current_job = self.batch_queue[self.current_batch_index]
                current_job['status'] = 'Done'
                self._update_batch_list()
                self._start_next_batch_job()
                
        else:
            self.on_log("❌ Training failed or was cancelled")
            self._show_message("Training failed or was cancelled")
            
            # Hide viewer button on failure
            self.btn_open_viewer.visible = False
            
            if self.is_batch_processing:
                current_job = self.batch_queue[self.current_batch_index]
                current_job['status'] = 'Failed'
                self._update_batch_list()
                self._start_next_batch_job()
        
        self.page.update()
    
    def _on_open_viewer(self, e):
        """Open NerfStudio viewer."""
        viewer_url = self.trainer.get_viewer_url("")
        self.on_log(f"Opening viewer: {viewer_url}")
        
        # Open in default browser
        import webbrowser
        webbrowser.open(viewer_url)
        
        self._show_message(f"Opening viewer at {viewer_url}")
    
    def _show_message(self, text: str):
        """Show snackbar message."""
        self.page.snack_bar = ft.SnackBar(content=ft.Text(text))
        self.page.snack_bar.open = True
        self.page.update()

    def _on_add_batch(self, e):
        """Add current configuration to batch queue."""
        path = self.temp_dir_getter()
        if not path:
             self._show_message("Please load a scan first")
             return
        
        # Add to queue with current settings
        job = {
            'path': path,
            'method': self.method_dropdown.value,
            'iterations': int(self.iterations_input.value),
            'status': 'Pending'
        }
        self.batch_queue.append(job)
        self._update_batch_list()
        self._show_message("Added to batch queue")
        
    def _on_clear_batch(self, e):
        """Clear the batch queue."""
        self.batch_queue = []
        self._update_batch_list()
        
    def _update_batch_list(self):
        """Update batch list UI."""
        self.batch_list.controls.clear()
        for i, job in enumerate(self.batch_queue):
            status_symbol = "⏳"
            if job['status'] == 'Running': status_symbol = "🔄"
            elif job['status'] == 'Done': status_symbol = "✅"
            elif job['status'] == 'Failed': status_symbol = "❌"
            
            self.batch_list.controls.append(
                ft.Text(f"{i+1}. {status_symbol} {os.path.basename(job['path'])} ({job['method']}, {job['iterations']} iters)")
            )
        
        self.btn_start_batch.disabled = len(self.batch_queue) == 0 or self.is_batch_processing
        self.page.update()

    def _on_start_batch(self, e):
        """Start batch processing."""
        if not self.batch_queue:
            return
            
        self.is_batch_processing = True
        self.current_batch_index = -1
        self.btn_start_batch.disabled = True
        self.btn_add_batch.disabled = True
        self.btn_clear_batch.disabled = True
        self.page.update()
        
        self.on_log("Starting batch processing...")
        self._start_next_batch_job()
        
    def _start_next_batch_job(self):
        """Start the next job in the queue."""
        self.current_batch_index += 1
        
        if self.current_batch_index >= len(self.batch_queue):
            # All done
            self.is_batch_processing = False
            self.current_batch_index = -1
            self.on_log("Batch processing complete!")
            self._show_message("Batch processing complete!")
            self.btn_add_batch.disabled = False
            self.btn_clear_batch.disabled = False
            # self.btn_start_batch.disabled = False # Don't re-enable immediately to avoid confusion
            self._update_batch_list()
            return

        job = self.batch_queue[self.current_batch_index]
        job['status'] = 'Running'
        self._update_batch_list()
        
        # Override temp_dir via getter (trickier) or pass directly to trainer
        # Trainer takes data_path directly, so we are good.
        
        self.on_log(f"Batch Job {self.current_batch_index+1}/{len(self.batch_queue)}: {os.path.basename(job['path'])}")
        
        # Update UI to reflect current job
        self.method_dropdown.value = job['method']
        self.iterations_input.value = str(job['iterations'])
        self.page.update()
        
        # Start training
        success = self.trainer.start_training(
            data_path=job['path'],
            method=job['method'],
            max_iterations=job['iterations'],
            progress_callback=self._on_training_progress,
            completion_callback=self._on_training_complete,
            log_callback=self._on_training_log
        )
        
        if not success:
            job['status'] = 'Failed'
            self._update_batch_list()
            # Continue to next job? YES.
            self._start_next_batch_job()

    def _on_export_click(self, e):
        """Handle export button click."""
        output_path = self.output_path_text.value.replace("Model saved: ", "")
        if not output_path or not os.path.exists(output_path):
            self._show_message("No trained model found to export")
            return
            
        fmt = self.export_format.value
        self.btn_export.disabled = True
        self.export_status.value = "Exporting..."
        self.page.update()
        
        threading.Thread(
            target=self._do_export,
            args=(output_path, fmt),
            daemon=True
        ).start()
        
    def _do_export(self, config_path, fmt):
        """Run ns-export command."""
        try:
            # config_path is the directory usually in my implementation logic?
            # self.output_path_text is set in _on_training_complete
            # Wait, NerfStudio outputs a directory. The config file is inside it.
            
            config_file = os.path.join(config_path, "config.yml")
            if not os.path.exists(config_file):
                self.export_status.value = "Error: config.yml not found"
                self.page.update()
                self.btn_export.disabled = False
                return

            output_dir = os.path.join(config_path, f"export_{fmt}")
            
            # Determine export type
            export_type = "gaussian-splat" # default for splatfacto
            if "nerfacto" in config_path and "splat" not in config_path:
                export_type = "pointcloud" # Default to PC for NeRF, maybe mesh?
                if fmt in ['obj', 'glb']:
                    # For meshes from NeRF (marching cubes or poisson)
                    # This is complex as it requires normal estimation or specific method
                    # Let's try 'tsdf' or 'poisson' if supported, or 'marching-cubes'
                    export_type = "marching-cubes" # Standard for density fields

            # Override for splatfacto
            with open(config_file, 'r') as f:
                if "splatfacto" in f.read():
                     export_type = "gaussian-splat"
                     if fmt == "obj":
                         # Splat to mesh is hard. Warning?
                         pass 

            cmd = [
                self._get_nerfstudio_python(),
                "ns-export",
                export_type,
                "--load-config", config_file,
                "--output-dir", output_dir
            ]
            
            # Add format flag if applicable
            if export_type == "gaussian-splat":
                if fmt == "ply":
                    cmd.extend(["--output-format", "ply"])
                # splat to obj/glb is not directly supported by ns-export for gaussian-splat usually
            
            self.on_log(f"Exporting: {' '.join(cmd)}")
            
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if proc.returncode == 0:
                self.export_status.value = f"✅ Exported to {output_dir}"
                self.on_log(f"Export successful: {output_dir}")
                # Open folder
                os.startfile(output_dir)
            else:
                 self.export_status.value = f"❌ Export failed"
                 self.on_log(f"Export failed: {proc.stderr}")

        except Exception as ex:
            self.export_status.value = f"Error: {ex}"
        finally:
             self.btn_export.disabled = False
             self.page.update()

    def _refresh_history(self, e):
        """Refresh model history list."""
        self.history_list.controls.clear()
        
        try:
            history = self.trainer.get_history()
            
            if not history:
                self.history_list.controls.append(ft.Text("No trained models found.", color=ft.Colors.GREY))
            
            for item in history:
                # Create row for each item
                row = ft.Row([
                    ft.Column([
                        ft.Text(f"{item['name']}", weight="bold", size=12),
                        ft.Text(f"{item['method']} | {item['date']}", size=10, color=ft.Colors.GREY_400),
                    ], expand=True),
                    
                    ft.IconButton(
                        icon=ft.Icons.VISIBILITY, 
                        tooltip="View Model",
                        on_click=lambda e, path=item['path']: self._on_view_history(path)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.FILE_UPLOAD, 
                        tooltip="Export",
                        on_click=lambda e, path=item['path']: self._on_export_history(path)
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                
                self.history_list.controls.append(ft.Container(
                    content=row,
                    padding=5,
                    bgcolor="#333333",
                    border_radius=5,
                    margin=ft.margin.only(bottom=2)
                ))
                
        except Exception as ex:
             self.history_list.controls.append(ft.Text(f"Error loading history: {ex}", color=ft.Colors.RED))
             
        self.page.update()

    def _on_view_history(self, path):
        """View a historical model."""
        url = self.trainer.get_viewer_url(path)
        
        # We need to launch the viewer process for this specific config if not running
        # Usually viewer is launched via ns-viewer --load-config ...
        # But for now let's just assume we can open the viewer if running, or launch it.
        # Actually NerfStudioTrainer.get_viewer_url just returns localhost:7007
        # We need to run ns-viewer.
        
        self.on_log(f"Launching viewer for: {path}")
        self._show_message("Launching viewer...")
        
        threading.Thread(target=self._launch_viewer_process, args=(path,), daemon=True).start()

    def _on_export_history(self, path):
        """Prepare export for historical model."""
        self.output_path_text.value = path
        self.export_container.visible = True
        self.export_status.value = f"Selected: {os.path.basename(path)}"
        self.page.update()
        self._show_message("Ready to export. Select format and click Export.")

    def _launch_viewer_process(self, path):
        """Launch ns-viewer in background."""
        import subprocess
        import webbrowser
        import time

        config_path = os.path.join(path, "config.yml")
        if not os.path.exists(config_path):
            self.on_log(f"Error: Config not found at {config_path}")
            return

        cmd = [
            self._get_nerfstudio_python(),
            "ns-viewer",
            "--load-config", config_path
        ]
        
        self.on_log(f"Starting viewer: {' '.join(cmd)}")
        
        # Kill existing viewers? Maybe not needed if port 7007 is free or it picks another?
        # Usually it tries 7007.
        
        try:
            subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # Give it a moment to start
            time.sleep(3)
            webbrowser.open("http://localhost:7007")
            
        except Exception as ex:
            self.on_log(f"Failed to launch viewer: {ex}")
    def _on_generate_mono_depth_click(self, e):
        """Handle Monocular Depth generation request."""
        temp_dir = self.temp_dir_getter()
        if not temp_dir:
            self._show_message("Please load a scan first")
            return
            
        self.btn_train.disabled = True
        self.training_progress.visible = True
        self.training_progress.value = 0
        self.progress_text.value = "Initializing Monocular Depth Estimation..."
        self.training_log.controls.clear()
        self.training_log_container.visible = True
        self.page.update()
        
        threading.Thread(target=self._run_monocular_depth_async, args=(temp_dir,), daemon=True).start()

    def _run_monocular_depth_async(self, scan_folder):
        """Run monocular depth generation in a background thread."""
        try:
            # Import generator here to avoid early dependency errors if MiDaS not installed
            from generate_monocular_depth import generate_depth_for_scan
            
            self._on_training_log(f"Starting Monocular Depth Generation for: {scan_folder}")
            
            # Run the generator
            generate_depth_for_scan(scan_folder)
            
            self.progress_text.value = "✅ Monocular Depth Generated successfully!"
            self.on_log("Monocular depth generation complete")
            
        except Exception as ex:
            self._on_training_log(f"❌ Error during depth generation: {ex}")
            self.progress_text.value = "❌ Depth Generation Failed"
        
        finally:
            self.btn_train.disabled = False
            self.training_progress.visible = False
            self.page.update()

    def _show_message(self, message: str):
        """Show a snackbar message."""
        self.page.snack_bar = ft.SnackBar(ft.Text(message))
        self.page.snack_bar.open = True
        self.page.update()
