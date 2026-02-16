"""
NerfStudio Training Module
Manages NerfStudio training processes via subprocess with real-time progress tracking.
"""

import subprocess
import threading
import time
import re
from pathlib import Path
from typing import Callable, Optional, Dict, Any
import json


class NerfStudioTrainer:
    """Manages NerfStudio training processes."""
    
    # Available training methods
    METHODS = {
        'splatfacto': {
            'name': 'Splatfacto (Gaussian Splatting)',
            'description': 'Fast, high-quality 3D Gaussian Splatting',
            'requires_depth': False,
            'speed': 'Fast (5-10 min)',
            'quality': 'Excellent'
        },
        'nerfacto': {
            'name': 'Nerfacto (NeRF)',
            'description': 'Standard NeRF with good quality/speed balance',
            'requires_depth': False,
            'speed': 'Medium (15-30 min)',
            'quality': 'Very Good'
        },
        'instant-ngp': {
            'name': 'Instant-NGP',
            'description': 'Ultra-fast neural graphics primitives',
            'requires_depth': False,
            'speed': 'Very Fast (2-5 min)',
            'quality': 'Good'
        },
        'depth-nerfacto': {
            'name': 'Depth-Nerfacto',
            'description': 'NeRF with depth supervision (requires depth maps)',
            'requires_depth': True,
            'speed': 'Medium (15-30 min)',
            'quality': 'Excellent'
        }
    }
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.completion_callback: Optional[Callable[[bool, str], None]] = None
        self._monitor_thread: Optional[threading.Thread] = None
        
    def start_training(
        self,
        data_path: str,
        method: str = 'splatfacto',
        output_dir: Optional[str] = None,
        max_iterations: int = 30000,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        completion_callback: Optional[Callable[[bool, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,  # New callback
        extra_args: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Start NerfStudio training process.
        
        Args:
            data_path: Path to scan data folder (with transforms.json)
            method: Training method ('splatfacto', 'nerfacto', etc.)
            output_dir: Optional custom output directory
            max_iterations: Maximum training iterations
            progress_callback: Called with progress updates {step, total, loss, eta}
            completion_callback: Called when done (success: bool, output_path: str)
            log_callback: Called with raw output lines
            extra_args: Additional command-line arguments
            
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running:
            print("[NerfStudio] Training already in progress")
            return False
        
        if method not in self.METHODS:
            print(f"[NerfStudio] Unknown method: {method}")
            return False
        
        # Check if data path exists
        data_path_obj = Path(data_path)
        if not data_path_obj.exists():
            print(f"[NerfStudio] Data path not found: {data_path}")
            return False
        
        # Check for transforms.json
        transforms_file = data_path_obj / "transforms.json"
        if not transforms_file.exists():
            print(f"[NerfStudio] transforms.json not found in {data_path}")
            return False
        
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.log_callback = log_callback
        
        # Build command using the python launcher script with SSL patches
        import sys
        import os
        
        # Use our custom launcher script that includes SSL monkey patches
        launcher_script = os.path.join(os.getcwd(), 'run_nerfstudio.py')
        
        if not os.path.exists(launcher_script):
            print(f"[NerfStudio] ERROR: Launcher script not found: {launcher_script}")
            return False
            
        cmd = [
            self._get_python_path(),  # Run with current python or dedicated venv python
            launcher_script, # The script that patches SSL and calls ns-train entrypoint
            method,
            '--data', str(data_path_obj),
            '--max-num-iterations', str(max_iterations),
        ]
        
        # Add output dir if specified
        if output_dir:
            cmd.extend(['--output-dir', output_dir])
        
        # Add extra args
        if extra_args:
            for key, value in extra_args.items():
                cmd.append(f'--{key}')
                if value is not True:  # Skip value for boolean flags
                    cmd.append(str(value))
        
        # Prepare environment with unbuffered output
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['COLUMNS'] = '150' # Force wide output to prevent weird wrapping

        print(f"[NerfStudio] Starting via launcher: {' '.join(cmd)}")
        
        try:
            # Start process with pipes for output
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,              # Unbuffered
                universal_newlines=True,
                encoding='utf-8',       # Explicitly use UTF-8
                errors='replace',       # Replace un-decodable bytes instead of crashing
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                env=env
            )
            
            self.is_running = True
            
            # Start monitoring thread
            self._monitor_thread = threading.Thread(
                target=self._monitor_training,
                daemon=True
            )
            self._monitor_thread.start()
            
            return True
            
        except FileNotFoundError:
            print("[NerfStudio] ERROR: Launcher command failed!")
            return False
        except Exception as e:
            print(f"[NerfStudio] Failed to start: {e}")
            return False
    
    def _strip_ansi(self, text: str) -> str:
        """Strip ANSI escape codes from string."""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def _monitor_training(self):
        """Monitor training process output and parse progress."""
        if not self.process:
            return
        
        try:
            buffer = []
            while True:
                # Read character by character to catch \r (progress bars)
                # and prevent blocking until \n
                char = self.process.stdout.read(1)
                
                if not char:
                    # End of stream
                     if buffer:
                         self._process_line("".join(buffer))
                     break
                
                if char == '\n' or char == '\r':
                    if buffer:
                        self._process_line("".join(buffer))
                        buffer = []
                else:
                    buffer.append(char)

            # Wait for process to complete
            return_code = self.process.wait()
            
            self.is_running = False
            
            # Determine output path
            output_path = self._find_output_path()
            
            success = (return_code == 0)
            
            if self.completion_callback:
                self.completion_callback(success, output_path)
            
            if success:
                print(f"[NerfStudio] Training completed! Output: {output_path}")
            else:
                print(f"[NerfStudio] Training failed with code {return_code}")
                
        except Exception as e:
            print(f"[NerfStudio] Monitoring error: {e}")
            self.is_running = False

    def _process_line(self, line: str):
        """Process a single line of output."""
         # Handle control characters that might not be stripped by line buffering
        line = line.replace('\x00', '') # Null bytes
        
        # Check for "clear screen" or "move cursor" confusion
        clean_line = self._strip_ansi(line).strip()
        
        if not clean_line:
            return
        
        # Send raw log first (cleaned)
        if hasattr(self, 'log_callback') and self.log_callback:
            self.log_callback(clean_line)

        # Parse progress from NerfStudio output
        progress_info = self._parse_progress_line(clean_line)
        
        if progress_info and self.progress_callback:
            self.progress_callback(progress_info)

    def _get_python_path(self) -> str:
        """Get path to python executable in dedicated venv."""
        import sys
        import os
        
        # Check for dedicated venv path
        venv_path = os.path.abspath(os.path.join(os.getcwd(), "nerfstudio_venv", "Scripts", "python.exe"))
        if os.path.exists(venv_path):
            return venv_path
            
        return sys.executable

    def _parse_progress_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse progress information from NerfStudio output line - ROBUST VERSION.
        Handles various tabular formats and extracts ETA.
        """
        line = line.strip()
        
        try:
            # Method 1: Look for "Step (Pct%)" pattern common in newer NerfStudio
            # Matches: "9580 (31.93%) ..."
            match_pct = re.search(r'(\d+)\s*\(\s*([0-9.]+)%\s*\)', line)
            if match_pct:
                step = int(match_pct.group(1))
                percentage = float(match_pct.group(2))
                
                eta_seconds = None
                
                # ETA Heuristic: Find the longest time duration in the line
                # Iteration time is usually small (ms or s), ETA is usually larger (m, h)
                
                # Split by multiple spaces to separate columns
                parts = re.split(r'\s{2,}', line)
                
                max_seconds = -1.0
                
                # Analyze potential time columns
                for part in parts:
                    # Skip the step column itself
                    if match_pct.group(0) in part:
                        continue
                        
                    # Calculate seconds for this part
                    # part example: "10 h, 33 m, 17 s" or "1 s, 860 ms"
                    part_seconds = 0.0
                    has_time = False
                    
                    # Find all number+unit pairs
                    # Note: We prioritize h/m/s. 'ms' usually indicates iteration time
                    pairs = re.findall(r'(\d+)\s*([hms]|ms)', part)
                    for val, unit in pairs:
                        val = int(val)
                        if unit == 'h': part_seconds += val * 3600
                        elif unit == 'm': part_seconds += val * 60
                        elif unit == 's': part_seconds += val
                        elif unit == 'ms': part_seconds += val / 1000.0
                        has_time = True
                    
                    if has_time:
                        if part_seconds > max_seconds:
                            max_seconds = part_seconds
                
                # If we found a valid time, assume the largest one is ETA
                # (unless it's tiny and only ms, then maybe we have no ETA yet)
                if max_seconds >= 0:
                    eta_seconds = int(max_seconds)

                # Calculate total steps
                if percentage > 0:
                   total_steps = int(step * 100.0 / percentage)
                else:
                   total_steps = 30000
                
                return {
                   'step': step,
                   'total_steps': total_steps,
                   'loss': None, # Not always available in table
                   'psnr': None,
                   'eta_seconds': eta_seconds
                }

            # Method 2: Old Format Fallback (Step 100/30000 ...)
            step_match = re.search(r'Step\s+(\d+)', line, re.IGNORECASE)
            if step_match:
                total_match = re.search(r'/\s*(\d+)', line)
                loss_match = re.search(r'loss[:\s=]+([0-9.]+)', line, re.IGNORECASE)
                psnr_match = re.search(r'psnr[:\s=]+([0-9.]+)', line, re.IGNORECASE)
                
                return {
                    'step': int(step_match.group(1)),
                    'total_steps': int(total_match.group(1)) if total_match else None,
                    'loss': float(loss_match.group(1)) if loss_match else None,
                    'psnr': float(psnr_match.group(1)) if psnr_match else None,
                    'eta_seconds': None
                }
                
        except Exception:
            pass # Fail gracefully
            
        return None
    
    def _find_output_path(self) -> str:
        """
        Find the output path where trained model was saved.
        NerfStudio typically saves to: outputs/<method>/<data_name>/<timestamp>/
        """
        # Default NerfStudio output location
        outputs_dir = Path('outputs')
        if not outputs_dir.exists():
            return ""
        
        # Find most recent output directory
        try:
            subdirs = [d for d in outputs_dir.rglob('*') if d.is_dir() and (d / 'config.yml').exists()]
            if subdirs:
                latest = max(subdirs, key=lambda d: d.stat().st_mtime)
                return str(latest)
        except:
            pass
        
        return str(outputs_dir)
    
    def stop_training(self):
        """Stop the training process."""
        if self.process and self.is_running:
            print("[NerfStudio] Stopping training...")
            self.process.terminate()
            self.process.wait(timeout=5)
            self.is_running = False
            print("[NerfStudio] Stopped")
    
    def get_viewer_url(self, output_path: str) -> str:
        """
        Get the viewer URL for a trained model.
        
        Args:
            output_path: Path to training output directory
            
        Returns:
            URL to open viewer (e.g., "http://localhost:7007")
        """
        # NerfStudio viewer typically runs on port 7007
        return "http://localhost:7007"
    
    @staticmethod
    def check_installation() -> bool:
        """Check if NerfStudio is installed and accessible."""
        import sys
        import os
        
        # Try multiple methods to detect NerfStudio
        
        # Method 1: Try importing nerfstudio module
        try:
            import nerfstudio
            return True
        except ImportError:
            pass
        
        # Method 2: Try running ns-train from venv Scripts folder
        try:
            venv_path = os.path.dirname(sys.executable)
            ns_train_exe = os.path.join(venv_path, 'ns-train.exe')
            
            if os.path.exists(ns_train_exe):
                result = subprocess.run(
                    [ns_train_exe, '--help'],
                    capture_output=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                return result.returncode == 0
        except:
            pass
        
        # Method 3: Try ns-train command directly (if in PATH)
        try:
            result = subprocess.run(
                ['ns-train', '--help'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            pass
        
        return False
    
    @staticmethod
    def get_recommended_method(has_depth: bool) -> str:
        """
        Get recommended training method based on available data.
        
        Args:
            has_depth: Whether scan has valid depth maps
            
        Returns:
            Recommended method name
        """
        if has_depth:
            return 'depth-nerfacto'
        else:
            return 'splatfacto'  # Fastest and best quality for color-only


# Example usage
if __name__ == "__main__":
    
    def on_progress(info):
        step = info['step']
        total = info.get('total_steps', '?')
        loss = info.get('loss', 0)
        print(f"Progress: {step}/{total} | Loss: {loss:.5f}")
    
    def on_complete(success, output_path):
        if success:
            print(f"✅ Training completed! Output: {output_path}")
        else:
            print("❌ Training failed!")
    
    # Check if installed
    if not NerfStudioTrainer.check_installation():
        print("NerfStudio not found. Install with: pip install nerfstudio")
        exit(1)
    
    # Start training
    trainer = NerfStudioTrainer()
    data_path = r"C:\Users\Mejkerslab\Desktop\Scan_20260215_221412"
    
    trainer.start_training(
        data_path=data_path,
        method='splatfacto',
        max_iterations=30000,
        progress_callback=on_progress,
        completion_callback=on_complete
    )
    
    # Wait for completion
    try:
        while trainer.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        trainer.stop_training()
