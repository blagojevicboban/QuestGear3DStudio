# 🎨 NerfStudio GUI - Quick Start Guide

## Overview
QuestGear 3D Studio now features a **complete GUI** for NerfStudio training, making it easy to create photorealistic 3D reconstructions without  using the command line!

---

## 🚀 Getting Started

### Step 1: Launch the Application
```bash
cd C:\QuestGear3D\QuestGear3DStudio
.\venv\Scripts\activate
python main.py
```

### Step 2: Navigate to NerfStudio Tab
- Click on the **"NerfStudio" tab** (with sparkle ✨ icon)
- You'll see two sections:
  - **Installation Status**
  - **Training Configuration**

---

## 📥 Installing NerfStudio

### First-Time Setup

1. **Check Installation Status:**
   - Look for "✅ NerfStudio Installed" or "❌ NerfStudio Not Found"

2. **Click "Install NerfStudio":**
   - Progress bar will appear
   - Installation takes **5-10 minutes**
   - Live log shows download/installation progress

3. **Wait for Completion:**
   - Status will update to "✅ NerfStudio Installed"
   - Training section will become enabled

### Updating NerfStudio

- If already installed, button shows **"Update NerfStudio"**
- Click to upgrade to the latest version
- Same process as installation

---

## 🎬 Training a Model

### Prerequisites
- ✅ Scan data loaded (use "Load Folder" or "Load ZIP" in TSDF tab)
- ✅ NerfStudio installed
- ✅ GPU with CUDA support (recommended)

### Training Steps

1. **Select Training Method:**
   - **Splatfacto** ⚡ (Recommended) - Gaussian Splatting, fast & excellent quality
   - **Nerfacto** 🎯 - Standard NeRF, balanced quality/speed
   - **Instant-NGP** 🚀 - Ultra-fast, good quality
   - **Depth-Nerfacto** 📊 - Requires valid depth maps

2. **Set Max Iterations:**
   - Default: **30,000**
   - Quick preview: 10,000
   - High quality: 50,000+

3. **Click "Start Training":**
   - Progress bar appears
   - Real-time metrics displayed:
     - **Step**: Current/Total iterations
     - **ETA**: Estimated time remaining
     - **Loss**: Training loss (lower is better)
     - **PSNR**: Image quality metric (higher is better, > 25 is good)

4. **Monitor Progress:**
   - Watch the progress bar
   - Check console logs for detailed output
   - Training typically takes **5-30 minutes** depending on method

5. **Training Complete:**
   - Status: "✅ Training completed!"
   - Output path displayed (e.g., `outputs/splatfacto/scan_name/...`)
   - **"Open Viewer"** button appears

---

## 👁️ Viewing Results

### Option 1: NerfStudio Viewer
1. Click **"Open Viewer"** button
2. Browser opens to `http://localhost:7007`
3. Interactive 3D viewer with:
   - Real-time navigation
   - Rendering controls
   - Camera path playback

### Option 2: Export Model
- Navigate to output folder (shown in GUI)
- Find `point_cloud.ply` (for Splatfacto)
- Open in MeshLab, CloudCompare, or Blender

---

## ⚙️ Advanced Options

### Custom Arguments (Future)
Currently, training uses default parameters. Future updates will add:
- Learning rate control
- Batch size adjustment
- Custom output directory
- Hyperparameter presets

### For Now (CLI)
For advanced control, use command line:
```bash
ns-train splatfacto --data "path/to/scan" `
  --pipeline.model.cull-alpha-thresh 0.05 `
  --optimizers.xyz.lr 0.00016 `
  --max-num-iterations 50000
```

---

## 🔧 Troubleshooting

### "NerfStudio Not Found" After Install
- **Solution:** Restart the application
- If persists, check PATH or reinstall

### Training Crashes / CUDA Errors
- **Cause:** Insufficient GPU memory
- **Solution:**
  1. Close other GPU applications
  2. Use smaller resolution images
  3. Try **Instant-NGP** (lighter on memory)

### Poor Quality Results
- **Check:**
  - Camera poses are accurate (test with viewer)
  - Sufficient camera coverage (360° scan recommended)
  - Enough iterations (try 50k+)

### Viewer Won't Open
- **Manual:** Open browser to `http://localhost:7007`
- **Check:** NerfStudio viewer process is running (check terminal)

---

## 📊 Method Comparison

| Method | Speed | Quality | GPU Memory | Best For |
|--------|-------|---------|------------|----------|
| **Splatfacto** | ⚡⚡⚡ Fast (5-10 min) | 🌟🌟🌟🌟🌟 Excellent | High (6-8GB) | Photorealistic scenes, real-time viewer |
| **Nerfacto** | ⚡⚡ Medium (15-30 min) | 🌟🌟🌟🌟 Very Good | Medium (4-6GB) | General purpose, smooth surfaces |
| **Instant-NGP** | ⚡⚡⚡⚡ Ultra Fast (2-5 min) | 🌟🌟🌟 Good | Low (2-4GB) | Quick previews, testing |
| **Depth-Nerfacto** | ⚡⚡ Medium (15-30 min) | 🌟🌟🌟🌟🌟 Excellent | Medium (4-6GB) | When depth is valid |

---

## 💡 Tips & Tricks

### Best Practices
1. **Start with Splatfacto** - Best quality/speed balance
2. **Use 30k iterations** for most scenes
3. **Check depth validity first** - If depth is uniform, don't use Depth-Nerfacto
4. **Monitor PSNR** - Should increase over time (target: >25 dB)
5. **Save viewer URL** - Bookmark for easy access

### Performance Optimization
- **Reduce iterations for testing** (10k preview, then full 30k)
- **Close browser tabs** during training (saves RAM)
- **Use SSD** for scan data (faster loading)

### Quality Improvements
- **Increase iterations** to 50,000+
- **Ensure good lighting** during capture
- **360° coverage** for best results
- **Minimize motion blur** (slow, steady movements)

---

## 🎓 Learning Resources

### NerfStudio Documentation
- **Official Docs:** https://docs.nerf.studio/
- **Tutorials:** https://docs.nerf.studio/tutorials/
- **Discord Community:** https://discord.gg/nerfstudio

### Gaussian Splatting
- **Paper:** https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/
- **Interactive Demo:** https://huggingface.co/spaces/cakewalk/splat

---

## 📞 Support

### Issues?
1. Check logs in **Console/Terminal**
2. Review this guide's **Troubleshooting** section
3. Check `NERFSTUDIO_GUIDE.md` for detailed setup info
4. Report bugs with error logs attached

---

**Happy Training! 🎉**

*Last Updated: 2026-02-15*
