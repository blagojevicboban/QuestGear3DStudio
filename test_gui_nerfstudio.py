#!/usr/bin/env python3
"""
Quick test for GUI with NerfStudio integration.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*60)
print("Testing QuestGear3DStudio GUI with NerfStudio Tab")
print("="*60)

print("\n[1] Importing modules...")
try:
    from modules.nerfstudio_gui import NerfStudioUI
    print("    ✅ nerfstudio_gui imported")
except Exception as e:
    print(f"    ❌ Failed to import nerfstudio_gui: {e}")
    sys.exit(1)

try:
    from modules.nerfstudio_trainer import NerfStudioTrainer
    print("    ✅ nerfstudio_trainer imported")
except Exception as e:
    print(f"    ❌ Failed to import nerfstudio_trainer: {e}")
    sys.exit(1)

try:
    import flet as ft
    print("    ✅ flet imported")
except Exception as e:
    print(f"    ❌ Failed to import flet: {e}")
    sys.exit(1)

print("\n[2] Testing NerfStudioTrainer methods...")
methods = NerfStudioTrainer.METHODS
print(f"    Available methods: {len(methods)}")
for method_id, info in methods.items():
    print(f"      - {method_id}: {info['name']}")

print("\n[3] Checking NerfStudio installation...")
is_installed = NerfStudioTrainer.check_installation()
if is_installed:
    print("    ✅ NerfStudio is installed")
else:
    print("    ⚠️  NerfStudio not installed (expected, optional)")

print("\n[4] Testing GUI initialization (dry run)...")
print("    Creating mock page and UI...")

class MockPage:
    def __init__(self):
        self.snack_bar = None
        self.tasks = []
    
    def update(self):
        pass
    
    def run_task(self, task):
        self.tasks.append(task)

mock_page = MockPage()
mock_log = lambda msg: print(f"    [LOG] {msg}")
mock_temp_dir = lambda: "C:\\Users\\Mejkerslab\\Desktop\\Scan_20260215_221412"

try:
    ui = NerfStudioUI(
        page=mock_page,
        on_log=mock_log,
        temp_dir_getter=mock_temp_dir
    )
    print("    ✅ NerfStudioUI initialized successfully")
    print(f"    Installation status: {ui.is_installed}")
except Exception as e:
    print(f"    ❌ Failed to initialize UI: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[5] Testing tab generation...")
try:
    tab = ui.get_tab()
    print(f"    ✅ Tab created: {tab.text}")
except Exception as e:
    print(f"    ❌ Failed to create tab: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✅ All tests passed!")
print("="*60)
print("\nTo launch the full GUI, run:")
print("  python main.py")
print("\nOr test individually:")
print("  python modules/gui.py")
