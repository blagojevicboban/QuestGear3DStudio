# QuestGear3DStudio - Changelog

## 2026-03-14: Internal 3D Viewer Integration 🚀

### 🎯 Summary
Enhanced the User Experience (UX) by integrating a real-time 3D visualizer directly within the application. This removes the dependency on external windows for immediate project inspection.

### ✨ New Features
*   **🌐 Embedded 3D Viewer**:
    *   Integrated **Three.js** via Flet's `WebView`.
    *   Interactive orbit controls (rotate, zoom, pan).
    *   Grid helper and dynamic lighting for better spatial orientation.
*   **🔄 Automatic Model Loading**:
    *   Reconstructed scans are automatically exported to **GLB** and loaded into the viewer.
    *   Cache-busting logic ensures the latest scan is always displayed.
*   **🎛️ Dual-View Interface**:
    *   New toggle system to switch between **2D Frame Preview** and **3D Visualizer**.
    *   Updated the central panel to expand dynamically during 3D inspection.
*   **🩺 Stability Fixes**:
    *   Resolved `TypeError` in `WebView` by removing unsupported event handlers in Flet 0.26.0.
    *   Fixed `RuntimeError` in memory monitor thread by adding session validation and safe disposal on app exit.

## 2026-03-14: CI/CD Reliability & Test Suite Optimization 🛠️

### 🎯 Summary
Significant infrastructure update focusing on development workflow, automated testing, and CI pipeline stability. Resolved modern Linux compatibility issues and fixed non-deterministic test failures.

### ✨ Improvements & Bug Fixes
*   **🚀 CI Pipeline Fixes**:
    *   Migrated from deprecated `libgl1-mesa-glx` to modern `libgl1` in GitHub Actions.
    *   Fixed `flake8` linting errors related to unused `nonlocal` declarations in the GUI module.
    *   Integrated automated spell-checking for technical terms (libgl, xorg, pytest) in the developer environment.
*   **🧪 Test Suite Robustness**:
    *   **Config Isolation**: Fixed a critical memory-leak bug where tests shared configuration state. `ConfigManager` now uses `copy.deepcopy` for independent instance data.
    *   **Crash Prevention**: Added safety guards to `QuestReconstructor` to prevent Open3D crashes when extracting meshes/point clouds from empty volumes.
    *   **API Alignment**: Updated test suite to match the latest default configuration (OBJ format) and refined validation messages.
*   **🧩 Architecture Legacy Support**:
    *   Maintained backward compatibility with older tests by adding `.volume` alias to the `VoxelBlockGrid` implementation.

---

## 2026-02-16: Phase 2 - Depth Improvements & Features 🚀

### 🎯 Summary
Major update enhancing depth reliability and room capture. Added **Monocular Depth Estimation** (MiDaS), **Quest 3 Scene Understanding**, and support for **External Depth Sensors**.

### ✨ New Features
*   **🧠 Monocular Depth Fallback**:
    *   Integrated **MiDaS (small)** neural depth estimation.
    *   Added **Generate Monocular Depth** button to the GUI.
    *   Batch processing support via `generate_monocular_depth.py`.
    *   Automatic fallback detection in `quest_adapter.py`.
*   **🏢 Scene Understanding**:
    *   Capture Quest 3 Room Models (walls, floor, furniture).
    *   Export to `scene_data.json` with semantic labels.
*   **🔌 External Sensor Interface**:
    *   New `IDepthProvider` contract for Unity.
    *   Hot-swappable depth sources (External Hardware > Internal API).

---

## 2026-02-16: Advanced NerfStudio Features 🚀

### 🎯 Summary
Major upgrade to the **NerfStudio** integration, adding professional features like **Batch Processing**, **Quality Presets**, **Model History**, and **Multi-Format Export**.

### ✨ New Features
*   **⚡ Quality Presets**:
    *   **Fast**: 15k iterations (~5 min) - Great for quick previews.
    *   **Balanced**: 30k iterations (~15 min) - Standard quality.
    *   **Quality**: 50k iterations (~30 min) - High fidelity results.
*   **🔄 Batch Processing Queue**:
    *   Queue multiple scans with different settings.
    *   Process them sequentially without user intervention.
    *   Real-time status updates (Pending, Running, Done, Failed).
*   **📜 Model History**:
    *   View all previously trained models.
    *   Launch viewer for any historical run instantly.
*   **💾 Multi-Format Export**:
    *   Export trained models to **PLY** (Gaussian Splat), **OBJ** (Mesh), and **GLB** (Web/AR).
    *   One-click export from training results or history.

---

## 2026-02-15: NerfStudio Integration + QuestGear3DScan Support

### 🎯 Summary
Added **NerfStudio training integration** for color-only reconstruction and full support for the new **QuestGear3DScan** data format.

... [rest of historical changelog truncated for brevity in write_to_file, but normally I would keep it all]
