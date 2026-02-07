# QuestStream 3D Processor - Documentation

This tool enables 3D reconstruction of scenes captured using **Meta Quest 3** devices (using OpenQuestCapture or similar tools). The pipeline converts raw images and depth maps into a textured 3D model.

## 🚀 Quick Start

1. **Loading Data**:
   - Click **"Load Folder"** and select the extracted folder containing Quest data.
   - The program will automatically detect the Quest format and create `frames.json` (if it doesn't already exist).
2. **Settings**:
   - Click the gear icon (top right).
   - **Voxel Size**: Set to `0.02` for a good balance, or `0.01` for high quality.
   - **Frame Interval**: Set to `1` to process every frame, or `5` for a quick preview.
3. **Reconstruction**:
   - Click **"Start Reconstruction"**.
   - Monitor progress in the logs. Once finished, you will see the number of generated vertices.
4. **Visualization**:
   - Click **"Visualizer (External)"** to open the 3D preview.

---

## 🛠️ Technical Pipeline

### 1. Image Data Preprocessing
- **YUV to RGB**: Quest captures images in `YUV_420_888` format. Our processor converts this to the standard RGB format using OpenCV.
- **Raw Depth**: Depth maps are loaded as `float32` values from `.raw` files. Since Quest 3 generates depth in meters, we perform scaling and cleanup of invalid values (Infinity/NaN).

### 2. Geometric Integration (TSDF)
We use **Scalable TSDF Volume** (from the Open3D library) which works as follows:
- Each RGB-D frame is projected into 3D space using **intrinsics** parameters (focal length, principal point) and **pose** (headset position and rotation).
- Data is accumulated into a volumetric grid (voxels).
- Finally, the **Marching Cubes** algorithm is used to extract the final triangle mesh.

---

## 📂 Data Structure (Meta Quest format)

The program expects the following files in the folder:
- `frames.json`: Main index with poses and paths.
- `left_camera_raw/`: Contains `.yuv` images.
- `left_depth/`: Contains `.raw` depth maps.
- `left_camera_image_format.json`: Information about image resolution.
- `left_depth_descriptors.csv`: Information about depth resolution and range.

---

## 💡 Tips for Best Results

- **Lighting**: Capture spaces with good, diffused lighting so YUV images are clear.
- **Movement Speed**: Move slowly while recording. Fast movements cause motion blur, which ruins 3D reconstruction.
- **Overlap**: Ensure frames overlap (circle around objects) so the TSDF volume can merge scene parts.
- **Voxel Size**: If you get 0 vertices at the end, check if the `Voxel Size` is too small for the noise level in the depth map. `0.02` is usually a safe value.

## 📦 Dependencies
The application uses:
- **Flet**: For a modern user interface.
- **Open3D**: For powerful 3D processing and visualization.
- **OpenCV & NumPy**: For fast pixel and array processing.
