# 🎨 NerfStudio GUI - Quick Start Guide

## Overview
QuestGear 3D Studio now features a **complete GUI** for NerfStudio training, making it easy to create photorealistic 3D reconstructions without using the command line!

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
   - Progress bar will appear (5-10 minutes)
3. **Wait for Completion:**
   - Status will update to "✅ NerfStudio Installed"

---

## 🎬 Training a Model

### Prerequisites
- ✅ Scan data loaded
- ✅ NerfStudio installed
- ✅ GPU with CUDA support (recommended)

### Training Steps

1. **Select Training Method:**
   - **Splatfacto** ⚡ (Recommended) - Gaussian Splatting
   - **Nerfacto** 🎯 - Standard NeRF
   - **Depth-Nerfacto** 📊 - Use if valid depth exists.

2. **[NEW] Monocular Depth Fallback:**
   - If your hardware depth is uniform (incorrect) or missing, click **"Generate Monocular Depth"**.
   - This uses AI to estimate depth from color frames, enabling high-quality **Depth-Nerfacto** training.

3. **Choose Quality Preset:**
   - **Fast** ⚡ (15k iters) | **Balanced** ⚖️ (30k iters) | **Quality** 💎 (50k iters)

4. **Click "Start Training"**

... [rest of guide follows]
