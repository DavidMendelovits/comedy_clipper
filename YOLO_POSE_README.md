# YOLO11/12 Pose Detection & Video Overlay Player

This guide covers the new YOLO11/12 pose detection clipper and interactive video overlay player.

## New Features

### 1. YOLO Pose Detection Clipper (`clipper_yolo_pose.py`)

A specialized clipper using YOLO11/12 for pose detection instead of MediaPipe. Provides:

- **Superior Performance**: YOLO11/12 offers better accuracy and speed
- **Advanced Pose Tracking**: 17 COCO keypoints per person
- **Real-time Visualization**: Debug mode exports frames with pose overlays
- **Multiple Model Sizes**: From nano (fast) to extra-large (accurate)

#### Usage

```bash
# Basic usage with default model (yolo11n-pose)
python3 clipper_yolo_pose.py video.mp4

# Use medium model for better accuracy
python3 clipper_yolo_pose.py video.mp4 --model yolo11m-pose.pt

# Enable debug visualization with pose overlays
python3 clipper_yolo_pose.py video.mp4 -d

# Use custom config file
python3 clipper_yolo_pose.py video.mp4 -c my_config.yaml

# Override minimum duration
python3 clipper_yolo_pose.py video.mp4 --min-duration 120
```

#### Available YOLO Models

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| `yolo11n-pose.pt` | Nano | Fastest | Good | Quick testing, real-time |
| `yolo11s-pose.pt` | Small | Fast | Better | General use |
| `yolo11m-pose.pt` | Medium | Moderate | Great | **Recommended** |
| `yolo11l-pose.pt` | Large | Slower | Excellent | High accuracy needed |
| `yolo11x-pose.pt` | XLarge | Slowest | Best | Maximum accuracy |

Models will be auto-downloaded on first use.

#### Debug Output

When using `-d` flag, the script exports:

- **Timeline frames**: Frames every 30 seconds with pose skeleton overlays
- **Segment boundaries**: Start/end frames for each detected segment
- **Pose visualization**:
  - Green keypoints for joint locations
  - Blue skeleton lines connecting joints
  - Confidence-based sizing

### 2. Interactive Video Overlay Player (`video_overlay_player.py`)

A real-time video player that shows detection overlays as the video plays. Perfect for:

- **Visualizing detection quality**: See what the AI sees
- **Testing configurations**: Try different models and see results immediately
- **Understanding failures**: Debug why segments weren't detected

#### Usage

```bash
# Play with YOLO pose detection
python3 video_overlay_player.py video.mp4

# Play with all detection types
python3 video_overlay_player.py video.mp4 --detections yolo_pose mediapipe_pose mediapipe_face

# Use a more accurate YOLO model
python3 video_overlay_player.py video.mp4 --yolo-model yolo11m-pose.pt
```

#### Interactive Controls

| Key | Action |
|-----|--------|
| **SPACE** | Play/Pause |
| **Y** | Toggle YOLO Pose overlay |
| **P** | Toggle MediaPipe Pose overlay |
| **F** | Toggle Face Detection overlay |
| **B** | Toggle Stage Boundary |
| **I** | Toggle Info overlay |
| **+/-** | Adjust playback speed (0.25x - 4.0x) |
| **LEFT/RIGHT** | Seek backward/forward 5 seconds |
| **Q** | Quit |

#### Overlay Features

1. **YOLO Pose Overlay** (Yellow/Green):
   - Skeleton with 17 keypoints
   - Confidence-based keypoint sizing
   - Real-time tracking

2. **MediaPipe Pose Overlay** (Colored):
   - Full body landmarks
   - Smooth tracking
   - Good for comparison

3. **Face Detection Overlay** (Green boxes):
   - Bounding boxes around detected faces
   - Confidence scores

4. **Stage Boundary** (Blue):
   - Visual representation of stage area
   - Corner markers
   - Helps understand exit detection

5. **Info Display**:
   - Current time / total duration
   - Progress bar
   - Playback speed
   - Active overlays
   - Play/pause status

## Comparison: YOLO vs MediaPipe Pose

| Feature | YOLO11 Pose | MediaPipe Pose |
|---------|-------------|----------------|
| **Speed** | Very Fast | Fast |
| **Accuracy** | Excellent | Good |
| **Multi-person** | Yes | Single person |
| **Keypoints** | 17 (COCO) | 33 (BlazePose) |
| **Tracking** | Built-in | Built-in |
| **GPU Support** | Yes | Limited |
| **Model Size** | Configurable | Fixed |

**When to use YOLO11**:
- Multiple people on stage
- Need consistent tracking
- GPU available
- Want best accuracy

**When to use MediaPipe**:
- Single person focus
- CPU-only environment
- Need more detailed keypoints (33 vs 17)

## Integration with Existing UI

The new scripts work standalone, but you can integrate them into the Electron app:

### Adding YOLO Pose Clipper to UI

In `electron/main.ts`, add a new clipper type:

```typescript
case 'yolo_pose':
  pythonScript = 'clipper_yolo_pose.py';
  args = [
    videoPath,
    '--model', options.yoloModel || 'yolo11n-pose.pt',
    '--json'
  ];
  break;
```

### Adding Overlay Player as Preview

You could integrate the overlay player as a preview mode before processing:

```typescript
// In main.ts
ipcMain.handle('preview-with-overlays', async (event, videoPath) => {
  const python = spawn('python3', [
    'video_overlay_player.py',
    videoPath,
    '--detections', 'yolo_pose'
  ]);
  // Handle output...
});
```

## Performance Tips

### For Clipper

1. **Model Selection**:
   - Use `yolo11n-pose.pt` for fast processing
   - Use `yolo11m-pose.pt` for balanced quality
   - Use `yolo11x-pose.pt` only when accuracy is critical

2. **Sample Rate**:
   - Increase sample rate (e.g., 60) to skip more frames and speed up processing
   - Decrease (e.g., 15) for better accuracy

3. **GPU Acceleration**:
   - YOLO automatically uses GPU if CUDA is available
   - Install: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`

### For Overlay Player

1. **Playback Speed**:
   - Use lower speeds (0.5x, 0.25x) when analyzing specific moments
   - Use higher speeds (2x, 4x) for quick review

2. **Toggle Overlays**:
   - Disable unused overlays to improve performance
   - YOLO is fastest, MediaPipe face is slowest

3. **Window Size**:
   - Smaller window = faster rendering
   - Resize window with mouse if needed

## Troubleshooting

### "YOLO not available" Error

```bash
pip install ultralytics
```

### Models downloading slowly

First run downloads models (~20MB each). Subsequent runs use cached models.

### Overlay player laggy

1. Try a smaller YOLO model (nano instead of large)
2. Disable some overlays
3. Reduce playback speed
4. Close other applications

### No poses detected

1. Check if people are clearly visible in frame
2. Try a larger model (medium or large)
3. Adjust confidence threshold in config
4. Use overlay player to debug

## Configuration

Both scripts use the same `clipper_rules.yaml` config file. Key settings:

```yaml
# YOLO Pose Detection
yolo_detection:
  enabled: true
  model: "yolo11n-pose.pt"
  confidence: 0.5

# Position-based exit detection
position_detection:
  enabled: true
  exit_threshold: 0.15  # Distance from edge (0.0-0.5)
  exit_stability_frames: 2  # Frames at edge before exit

# Debug visualization
debug:
  export_frames: true
  overlays:
    draw_pose_landmarks: true
    draw_stage_boundaries: true
```

## Next Steps

1. Try the overlay player first to see how detection works
2. Experiment with different YOLO models
3. Run the YOLO clipper with debug mode
4. Compare results with MediaPipe clipper
5. Choose the best model/config for your use case

## Examples

### Quick Test
```bash
# See what the detector sees
python3 video_overlay_player.py casablanca.mp4

# Process with YOLO
python3 clipper_yolo_pose.py casablanca.mp4 -d
```

### Production Use
```bash
# High-quality clipping
python3 clipper_yolo_pose.py casablanca.mp4 \
  --model yolo11m-pose.pt \
  --min-duration 180 \
  -c clipper_rules.yaml
```

### Debugging
```bash
# Visual debugging
python3 video_overlay_player.py casablanca.mp4 \
  --detections yolo_pose mediapipe_pose \
  --yolo-model yolo11m-pose.pt
```
