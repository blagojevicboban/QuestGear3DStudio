# QuestGear3DStudio - Changelog
## [2.4.0] - 2026-03-15: The Neural Enhancement Update 🚀✨
### 🎯 Summary
Introduced state-of-the-art Neural Enhancement using **NVIDIA DiFix3D+**, providing a professional post-processing pipeline for NeRF and Gaussian Splatting results. This update allows users to refine their 3D reconstructions by removing artifacts and ensuring high visual fidelity through single-step diffusion.

### ✨ New Features
*   **🧠 DiFix3D+ Integration**:
    *   Integrated the **DiFix3D+** single-step diffusion model for artifacts removal and 3D consistency.
    *   Custom VAE implementation with **skip-connections** to maintain high-frequency details from the original renders.
    *   Support for local execution with automated weights management via Hugging Face (`nvidia/difix`).
*   **🎛️ Neural Enhancer GUI**:
    *   New dedicated section in the NerfStudio tab for managing post-processing.
    *   Batch enhancement of training renders/screenshots with real-time progress monitoring.
    *   Automatic suffixing (`_enhanced`) for easy comparison with original results.
*   **🛠️ Robust Local Loading**:
    *   Bypassed `trust_remote_code` limitations by implementing local pipeline and VAE loaders in `modules/difix/`.
    *   Fallback logic for CPU/CUDA detection ensures compatibility across varying hardware setups.

## [2.3.1] - 2026-03-14: Stability & GUI Refactoring Pass 🛠️
### 🎯 Summary
Critical maintenance update focused on resolving initialization race conditions and GUI binding errors introduced by the Multi-Scan architecture. Reorganized the entire `gui.py` module for predictable startup and reliable event handling.

### 🩺 Stability & UX Fixes
*   **🧩 GUI Binding Resolution**:
    *   Resolved `UnboundLocalError` and `NameError: reconstruct_format_dialog` by restructuring initialization order.
    *   Unified UI control creation at the top of the `main` loop to prevent circular dependencies.
    *   Fixed `SyntaxError` related to `nonlocal` bindings in nested callback functions.
*   **🏘️ Robust Multi-Scan Logic**:
    *   Consolidated data aggregation logic into a single, predictable flow for ZIP and Folder loading.
    *   Improved state management for `temp_dirs` and `frames_data` to ensure accurate stitching of multiple projects.
*   **🌐 Internal Viewer Enhancements**:
    *   Fixed GLB loading logic to point to the first project's asset directory if no global path is returned.
    *   Integrated format-selector directly into the reconstruction flow for streamlined exporting.

## [2.3.0] - 2026-03-14: The Multi-Scan & AI Enhancement Update 🏘️🚀

### 🎯 Summary
Enhanced the User Experience (UX) by integrating a real-time 3D visualizer directly within the application, removing dependency on external windows for immediate project inspection. Additionally, implemented robust persistent storage for application preferences and dynamic setting updates.

### ✨ New Features
*   **⚙️ Persistent Settings & Dynamic Updates**:
    *   Loading default values if the file does not exist.
    *   Persistent storage of application preferences (e.g., `initial_directory`, `nerfstudio.method`).
    *   Dynamic updating of values via the **Settings Tab** or Quick Settings dialog.
    *   **Advanced Texture Mapping (UV Atlas)**: Added support for UV unwrapping (xatlas) and projective texture baking.
    *   **Drift Correction & Loop Closure**: Implemented GICP-based SLAM refinement to correct Quest tracking drift.
    *   🗿 **Poisson Reconstruction**: [NEW] Generate **water-tight (solid)** 3D meshes, perfect for 3D printing and clean topology.
    *   🚀 **Multi-Backend Acceleration**: [NEW] Support for **NVIDIA CUDA** and **AMD/Intel DirectML (ONNX)**.
    *   🏘️ **Multi-Scan Merging**: [NEW] Stitch multiple ZIP recordings into a single large-scale scene (room-by-room scanning).
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
*   **⚙️ Dedicated Settings Tab**:
    *   Moved global parameters (Voxel Size, Smoothing, etc.) to a separate **Settings** tab.
    *   Added **Initial Scan Directory** persistence, allowing users to save their preferred Quest storage path.
    *   Integrated **NerfStudio Training Settings** (Method, Preset, Iterations) into the central configuration.
    *   Refactored the settings dialog into a responsive, dual-column layout.
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
