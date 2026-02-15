# NerfStudio Integration Guide

## 📋 Overview
QuestGear 3D Studio now supports **NerfStudio training** directly from the GUI! This enables color-only 3D reconstruction using state-of-the-art neural rendering methods.

## 🚀 Quick Start

### 1. Install NerfStudio (One-time setup)

#### Option A: Separate Environment (Recommended)
NerfStudio has heavy dependencies (PyTorch, CUDA). Best to install in separate environment:

```powershell
# Create NerfStudio environment
conda create -n nerfstudio python=3.10
conda activate nerfstudio

# Install NerfStudio
pip install nerfstudio

# Verify installation
ns-train --help
```

Then in QuestGear3DStudio, configure the path to `ns-train` executable in settings.

#### Option B: Same Environment (Advanced)
If you want to use the same venv:

```powershell
# Activate QuestGear3DStudio venv
.\venv\Scripts\activate

# Install NerfStudio
pip install nerfstudio

# May require CUDA toolkit
# Download from: https://developer.nvidia.com/cuda-downloads
```

**⚠️ Warning:** This will install ~2GB of dependencies including PyTorch.

### 2. Configure QuestGear3DStudio

Edit `config.yml` and add:

```yaml
nerfstudio:
  executable_path: "ns-train"  # or full path: "C:/Users/.../ns-train.exe"
  default_method: "splatfacto"
  default_iterations: 30000
  viewer_port: 7007
```

### 3. Train from GUI

1. Load your scan in QuestGear3DStudio
2. Go to **NerfStudio Training** tab
3. Select method (Splatfacto recommended)
4. Click **Start Training**
5. Monitor progress in real-time
6. Click **Open Viewer** when done

## 📊 Training Methods

### Splatfacto (Gaussian Splatting) ⭐ Recommended
- **Speed:** Fast (5-10 min)
- **Quality:** Excellent
- **Output:** `.ply` file (point cloud with gaussians)
- **Best for:** Real-time viewing, high detail

### Nerfacto (NeRF)
- **Speed:** Medium (15-30 min)
- **Quality:** Very Good
- **Output:** Neural network weights
- **Best for:** Novel view synthesis, smooth surfaces

### Instant-NGP
- **Speed:** Very Fast (2-5 min)
- **Quality:** Good
- **Output:** Hash grid + tiny MLP
- **Best for:** Quick previews

### Depth-Nerfacto
- **Speed:** Medium (15-30 min)
- **Quality:** Excellent
- **Requires:** Valid depth maps
- **Best for:** Scans with accurate depth data

## 🎯 Workflow Examples

### Example 1: Quick Preview
```python
# In QuestGear3DStudio Python API
from modules.nerfstudio_trainer import NerfStudioTrainer

trainer = NerfStudioTrainer()
trainer.start_training(
    data_path="path/to/scan",
    method="instant-ngp",
    max_iterations=10000
)
```

### Example 2: High-Quality Export
```python
trainer.start_training(
    data_path="path/to/scan",
    method="splatfacto",
    max_iterations=30000,
    extra_args={
        'pipeline.model.cull-alpha-thresh': 0.05,
        'optimizers.xyz.lr': 0.00016
    }
)
```

## 🔧 Troubleshooting

### "NerfStudio not found"
- Check if `ns-train` is in PATH
- Verify installation: `ns-train --help`
- Specify full path in config.yml

### "CUDA out of memory"
- Reduce `--pipeline.datamanager.train-num-rays-per-batch` to 2048
- Close other GPU applications
- Use smaller resolution images

### Training is slow
- Check GPU usage (Task Manager)
- Ensure CUDA is properly installed
- Try `instant-ngp` for faster results

### Poor quality results
- Increase `max_iterations` to 50000+
- Ensure good camera coverage (360° scan)
- Check camera poses are accurate (validate transforms.json)

## 📖 Technical Details

### How it works
1. **Data Export:** QuestGear3DScan exports `transforms.json` (NerfStudio format)
2. **Process Launch:** GUI spawns `ns-train` subprocess
3. **Progress Parsing:** Real-time log parsing for step/loss/PSNR
4. **Output Import:** Final model (.ply or config.yml) imported back to GUI

### Integration Architecture
```
QuestGear3DStudio
├── modules/nerfstudio_trainer.py  (Backend - subprocess management)
├── modules/gui.py                  (Frontend - NerfStudio tab)
└── config.yml                      (Configuration)
```

### Output Structure
```
outputs/
└── splatfacto/
    └── scan_name/
        └── 2026-02-15_123456/
            ├── config.yml          (Training config)
            ├── dataparser_transforms.json
            ├── point_cloud.ply     (Final Gaussian Splatting model)
            └── nerfstudio_models/  (Checkpoints)
```

## 🌐 Resources

- **NerfStudio Docs:** https://docs.nerf.studio/
- **Gaussian Splatting Paper:** https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/
- **QuestGear3D GitHub:** (your repo URL)

## ❓ FAQ

**Q: Do I need depth maps?**
A: No! Splatfacto and Nerfacto work with color-only data.

**Q: How much GPU memory do I need?**
A: Minimum 4GB, recommended 8GB+ VRAM.

**Q: Can I train on CPU?**
A: Technically yes, but it will be 100x slower. Not recommended.

**Q: Where is the final model saved?**
A: `outputs/<method>/<scan_name>/<timestamp>/point_cloud.ply`

---
*Updated 2026-02-15 | QuestGear 3D Studio v2.0*
