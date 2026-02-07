# QuestStream 3D Processor

QuestStream is a Python-based tool for reconstructing 3D meshes from data captured by Meta Quest 3 headsets. It processes RGB images, depth maps, and camera pose data to generate high-quality 3D models using TSDF (Truncated Signed Distance Function) integration.

## Features

-   **Data Ingestion**: validaties and extracts Quest capture data (ZIP format).
-   **3D Reconstruction**: Uses Open3D's ScalableTSDFVolume for robust mesh generation.
-   **GUI**: User-friendly interface built with PyQt6.
-   **Visualization**: Built-in 3D visualizer for inspecting results.
-   **Configuration**: Customizable reconstruction parameters via YAML.

## Prerequisites

-   Windows 10/11
-   Python 3.11 or higher

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/QuestStream.git
    cd QuestStream
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Run the application:**
    ```bash
    python main.py
    ```

2.  **Load Data:**
    -   Click **File > Load ZIP**.
    -   Select a valid ZIP file containing the Quest capture data.
    -   **ZIP Structure Requirement**:
        -   `frames.json`: Metadata for each frame (timestamp, pose, intrinsics).
        -   `raw_images/`: Directory containing YUV/BIN image files.
        -   `depth_maps/`: Directory containing depth map files.

3.  **Start Reconstruction:**
    -   Once extraction is complete, click **Start Reconstruction**.
    -   Monitor progress via the progress bar and status label.

4.  **Visualize:**
    -   When reconstruction consists finishes, click **Visualizer (External)** to view the 3D mesh.

## Configuration

You can adjust reconstruction parameters in `config.yml` or via **File > Settings** in the GUI.

**Key Parameters:**
-   `reconstruction.voxel_size`: Size of valid voxels (smaller = higher detail, more RAM). Default: `0.01` (1cm).
-   `reconstruction.block_count`: Pre-allocated memory blocks.
-   `reconstruction.depth_max`: Maximum depth to integrate (in meters).
-   `reconstruction.use_confidence_filtered_depth`: Enable bilateral filtering for depth maps.

## Project Structure

-   `main.py`: Application entry point.
-   `modules/`:
    -   `gui.py`: Main window and UI logic.
    -   `reconstruction.py`: Open3D TSDF volume integration logic.
    -   `ingestion.py`: ZIP validation and extraction.
    -   `image_processing.py`: YUV to RGB conversion and depth filtering.
    -   `config_manager.py`: Configuration handling.

## License

[MIT License](LICENSE)
