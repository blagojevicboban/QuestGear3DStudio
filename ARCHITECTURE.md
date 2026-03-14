# QuestGear 3D Ecosystem - Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         QUEST 3 HEADSET                                  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  QuestGear3DScan (Unity App)                                    │    │
│  │                                                                  │    │
│  │  • Captures Camera 1 (tracking) → 1280x720 JPG                 │    │
│  │  • Reads Environment Depth API → 320x320 PNG (16-bit)          │    │
│  │  • [NEW] Scene Model Integration → scene_data.json             │    │
│  │  • Tracks HMD pose (6DOF) → Position + Rotation                │    │
│  │  • Exports transforms.json (NerfStudio format)                 │    │
│  │                                                                  │    │
│  │  Output: Scan_YYYYMMDD_HHMMSS/                                 │    │
│  │    ├── color/frame_*.jpg                                        │    │
│  │    ├── depth/frame_*.png                                        │    │
│  │    ├── scan_data.json                                           │    │
│  │    ├── scene_data.json  [NEW]                                   │    │
│  │    └── transforms.json                                          │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────│──────────────────────────────┘
                                          │
                    USB Transfer / ADB    │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         WINDOWS PC                                       │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  QuestGear3DStudio (Python/Flet GUI)                            │    │
│  │                                                                  │    │
│  │  ┌─────────────────────────────────────────────────────────┐   │    │
│  │  │  Data Adapter (quest_adapter.py)                         │   │    │
│  │  │  • Auto-detects formats & adapts poses                   │   │    │
│  │  │  • [NEW] Mono-Depth Folder Priority                      │   │    │
│  │  └─────────────────────────────────────────────────────────┘   │    │
│  │                           ▼                                      │    │
│  │  ┌─────────────────────────────────────────────────────────┐   │    │
│  │  │  Image Processor (quest_image_processor.py)              │   │    │
│  │  │  • Multi-format loader (JPG, PNG, YUV)                   │   │    │
│  │  │  • Validates depth quality                               │   │    │
│  │  └─────────────────────────────────────────────────────────┘   │    │
│  │                           ▼                                      │    │
│  │         ╔═══════════════════════════════════════╗                │    │
│  │         ║  RECONSTRUCTION PATH SELECTOR         ║                │    │
│  │         ╚═══════════════════════════════════════╝                │    │
│  │                  /           |            \                      │    │
│  │          Valid Depth?   No Depth ──► Generate Mono Depth         │    │
│  │                /             |                \                  │    │
│  │               ▼              ▼                 ▼                 │    │
│  │  ┌──────────────────────────┐   ┌────────────────────────────┐ │    │
│  │  │ TSDF Reconstruction      │   │ NerfStudio Training        │ │    │
│  │  │ (reconstruction.py)      │   │ (nerfstudio_trainer.py)    │ │    │
│  │  │                          │   │                            │ │    │
│  │  │ • VoxelBlockGrid (CUDA)  │   │ • Subprocess: ns-train     │ │    │
│  │  │ • Depth fusion           │   │ • Methods:                 │ │    │
│  │  │ • Mesh extraction        │   │   - Splatfacto ⭐         │ │    │
│  │  │                          │   │   - Depth-Nerfacto 🧠      │ │    │
│  │  │ Output: .ply mesh        │   │   - Nerfacto / Instant-NGP │ │    │
│  │  └──────────────────────────┘   └────────────────────────────┘ │    │
│  │                  │                              │                │    │
│  │                  └──────────┬───────────────────┘                │    │
│  │                            ▼                                     │    │
│  │  ┌─────────────────────────────────────────────────────────┐   │    │
│  │  │  3D Viewer / Export                                      │   │    │
│  │  │  • Open3D visualization                                  │   │    │
│  │  │  • Export to OBJ, PLY, GLB                              │   │    │
│  │  └─────────────────────────────────────────────────────────┘   │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow (Updated Phase 2)

### 📸 Capture (Quest 3)
- **Object Mode**: Continuous RGB-D stream.
- **Space Mode**: Room geometry capture via `OVRSceneManager` → `scene_data.json`.
- **External Sensors**: Optional support via `IDepthProvider` interface.

### 🧠 Monocular Depth Path
When hardware depth is unavailable or poor quality:
1. User clicks **"Generate Monocular Depth"** in Studio GUI.
2. `monocular_depth.py` runs **MiDaS** inference on color frames.
3. 16-bit depth PNGs are saved to `depth_monocular/`.
### 🏘️ Multi-Scan Merging Architecture
Introduced in v2.3.0 to support scanning large environments (e.g., entire apartments) room-by-room:
1. **Selection**: User selects multiple ZIP captures or extracted folders.
2. **Aggregation**: `gui.py` maintains a `temp_dirs` list and triggers `aggregate_frames()`.
3. **Data Loading**: `QuestDataAdapter` processes each folder independently to ensure they have the standard `frames.json` manifest.
4. **Pose Integration**: `QuestReconstructor` iterates through all aggregated frames. Poses remain in Quest's global coordinate system (HMD Tracking Space). 
   - *Note*: Large-scale alignment depends on the Quest's internal SLAM remaining continuous between scans (walking from room to room).
5. **Unified Reconstruction**: A single `VoxelBlockGrid` is initialized to encompass all frames, producing one master 3D model.

... [rest of architecture doc follows]
