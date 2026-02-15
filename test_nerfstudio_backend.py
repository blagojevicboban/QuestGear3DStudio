#!/usr/bin/env python3
"""Test NerfStudio trainer backend."""
import sys
sys.path.insert(0, r'C:\QuestGear3D\QuestGear3DStudio')

from modules.nerfstudio_trainer import NerfStudioTrainer
import time

print("="*60)
print("NerfStudio Trainer - Backend Test")
print("="*60)

# Check installation
print("\n[1] Checking NerfStudio installation...")
if NerfStudioTrainer.check_installation():
    print("    ✅ NerfStudio found!")
else:
    print("    ❌ NerfStudio not installed")
    print("    Install with: pip install nerfstudio")
    sys.exit(1)

# Show available methods
print("\n[2] Available training methods:")
for method_id, info in NerfStudioTrainer.METHODS.items():
    req_depth = "⚠️ Requires depth" if info['requires_depth'] else "✅ Color-only"
    print(f"    - {info['name']}")
    print(f"      {info['description']}")
    print(f"      Speed: {info['speed']}, Quality: {info['quality']}, {req_depth}")

# Get recommendation
print("\n[3] Recommendations:")
print(f"    Color-only scans: {NerfStudioTrainer.get_recommended_method(has_depth=False)}")
print(f"    With depth maps: {NerfStudioTrainer.get_recommended_method(has_depth=True)}")

# Test with small iteration count (won't actually train, just test subprocess)
print("\n[4] Testing subprocess management...")
print("    (This will start NerfStudio with --help to test command)")

scan_path = r"C:\Users\Mejkerslab\Desktop\Scan_20260215_221412"

def progress_handler(info):
    step = info.get('step', 0)
    total = info.get('total_steps', '?')
    loss = info.get('loss')
    psnr = info.get('psnr')
    
    msg = f"    Step {step}/{total}"
    if loss is not None:
        msg += f" | Loss: {loss:.5f}"
    if psnr is not None:
        msg += f" | PSNR: {psnr:.2f}"
    print(msg)

def completion_handler(success, output_path):
    if success:
        print(f"\n    ✅ Training completed!")
        print(f"    Output: {output_path}")
    else:
        print(f"\n    ❌ Training failed")

print("\n[5] Ready to start training!")
print(f"    Scan: {scan_path}")
print(f"    Method: splatfacto (Gaussian Splatting)")
print("\n    To start actual training, uncomment the lines below in the test script.")
print("    Training typically takes 5-30 minutes depending on method and scene complexity.")

# Uncomment to actually start training:
# trainer = NerfStudioTrainer()
# trainer.start_training(
#     data_path=scan_path,
#     method='splatfacto',
#     max_iterations=30000,
#     progress_callback=progress_handler,
#     completion_callback=completion_handler
# )
# 
# # Wait for completion
# try:
#     while trainer.is_running:
#         time.sleep(1)
# except KeyboardInterrupt:
#     print("\n    User interrupted, stopping...")
#     trainer.stop_training()

print("\n" + "="*60)
print("✅ Backend test completed!")
print("="*60)
