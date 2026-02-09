# QuestGear 3D Studio - Architecture

This document describes the technical design and data flow within the application.

## 1. Component Overview

The application is divided into a UI layer and a logic layer (backend) that communicate via callback functions within parallel threads (threading).

### UI Layer (`modules/gui.py`)
- Uses **Flet** for interface rendering.
- Manages application state (paths to temporary folders, loaded meshes).
- Launches asynchronous processes in background threads to keep the UI responsive.
- **Splitter Control**: Implements a custom `GestureDetector` to allow resizing of the video preview pane.
- Contains the `add_log` function which centralizes the output of operations.

### Ingestion Layer (`modules/ingestion.py`)
- **ZipValidator**: Checks if the ZIP file has a correct structure (presence of `frames.json` and required folders).
- **AsyncExtractor**: Inherits from `threading.Thread`. Extracts the ZIP into a system temporary folder (`tempfile`).

### Processing Layer (`modules/quest_image_processor.py`, `modules/quest_reconstruction_utils.py`)
- **YUV to RGB**: Conversion from NV12/NV21 format to RGB.
- **Transforms**: `Classes` and `Enums` for converting **Unity (LH, Y-up)** poses to **Open3D (RH, Y-down)**.
- **Depth**: Safe `convert_depth_to_linear` with localized clamping and NaN handling.
- **Intrinsics**: Dynamic calculation of focal length and principal point from FOV angles.

### Reconstruction Layer (`modules/reconstruction.py`)
- **QuestReconstructor**: Initializes `VoxelBlockGrid`. Supports both CPU and GPU (CUDA).
- **Integration**: Converts numerical arrays (RGB, Linear Depth) into Open3D Tensors and integrates safe, verified data.

## 2. Data Flow

1. **User selects ZIP** -> `FilePicker` in the GUI.
2. **Validation** -> `ZipValidator` checks CRC and structure.
3. **Extraction** -> `AsyncExtractor` extracts files to `_extracted` folder next to the zip (or system tmp previously).
4. **Launch Reconstruction**:
    - `ReconstructionThread` reads `frames.json`.
    - For each frame:
        - Read BIN/YUV file -> `yuv_to_rgb`.
        - Read Depth file -> `filter_depth` (if configured).
        - Frame is integrated into the `Volume`.
        - **Stereo Mode**: If enabled, both Left and Right camera frames are integrated. The system calculates the world pose for each camera using the Head Pose and known Extrinsics (IPD offset).
5. **Finalization**: 
    - `extract_mesh()` generates a mesh.
    - **Post-Processing**: Smoothing and decimation are applied.
    - **Export**: Mesh is saved as .obj/.glb.
    - **Thumbnail**: A preview image is captured using an off-screen visualizer.

## 3. Configuration Management

All parameters are stored in `config.yml`. `ConfigManager` enables:
- Loading default values if the file does not exist.
- Dynamic updating of values via the Settings dialog without restarting the application.

## 4. Error Handling

The application uses `try-except` blocks in all critical threads. Errors are sent back to the GUI via the `on_error` callback and are printed in the logs (or SnackBar notifications).
