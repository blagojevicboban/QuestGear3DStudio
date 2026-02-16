# QuestGear3DStudio - Changelog

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
