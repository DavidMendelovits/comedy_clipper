# Video Export Mode with Frame Overlays

The `video_overlay_player.py` script now supports exporting the entire video (or segments) with frame overlays rendered directly into the output video.

## Features

- **Export entire video or time ranges** with overlays rendered into the output
- **Choose which overlays to include**:
  - YOLO pose detection (skeleton and keypoints)
  - MediaPipe pose tracking
  - MediaPipe face detection
  - Stage boundary markers
  - Info overlay (time, progress)
- **Automatic H.264 encoding** for maximum compatibility
- **Progress tracking** during export
- **Customizable output path**

## Usage

### Basic Export

Export entire video with default YOLO pose overlays:

```bash
python3 video_overlay_player.py video.mp4 --export
```

Output will be saved as `video_overlays_YYYYMMDD_HHMMSS_h264.mp4` in the same directory.

### Export with Custom Output Path

```bash
python3 video_overlay_player.py video.mp4 --export -o my_analysis.mp4
```

### Export Specific Time Range

Export only frames from 30 seconds to 90 seconds:

```bash
python3 video_overlay_player.py video.mp4 --export --start-time 30 --end-time 90
```

### Export with All Detection Overlays

```bash
python3 video_overlay_player.py video.mp4 --export \
  --detections yolo_pose mediapipe_pose mediapipe_face
```

### Export with Selective Overlays

Export with only stage boundary and info (disable all detection overlays):

```bash
python3 video_overlay_player.py video.mp4 --export \
  --no-yolo --no-mediapipe-pose --no-mediapipe-face
```

Export with only YOLO pose and no info overlay:

```bash
python3 video_overlay_player.py video.mp4 --export --no-info
```

### Use Different YOLO Model

For better accuracy, use a larger YOLO model:

```bash
python3 video_overlay_player.py video.mp4 --export \
  --yolo-model yolo11m-pose.pt
```

## Available Command-Line Options

### Export Mode Options

- `--export` - Enable export mode (instead of interactive playback)
- `-o, --output PATH` - Output video file path
- `--start-time SECONDS` - Start time for export (default: beginning)
- `--end-time SECONDS` - End time for export (default: end)

### Overlay Control Options

- `--no-yolo` - Disable YOLO pose overlay
- `--no-mediapipe-pose` - Disable MediaPipe pose overlay
- `--no-mediapipe-face` - Disable MediaPipe face detection overlay
- `--no-stage-boundary` - Disable stage boundary overlay
- `--no-info` - Disable info overlay (time, progress bar)

### Detection Options

- `--detections [yolo_pose] [mediapipe_pose] [mediapipe_face]` - Detection modes to enable
- `--yolo-model MODEL` - YOLO model to use (default: yolo11n-pose.pt)

## Output Format

The export process creates two videos:

1. **Temporary video** - Initial output with mp4v codec
2. **Final video** - Re-encoded with H.264 for maximum compatibility
   - Codec: libx264
   - Preset: medium
   - CRF: 23 (good quality)
   - Pixel format: yuv420p
   - Includes faststart flag for web streaming

The temporary file is automatically deleted after successful re-encoding.

## Examples

### Example 1: Comedy Performance Analysis

Export a comedy set with YOLO pose detection to analyze stage movement:

```bash
python3 video_overlay_player.py comedy_set.mp4 --export \
  --yolo-model yolo11m-pose.pt \
  --no-info
```

### Example 2: Quick Preview of First Minute

Export just the first 60 seconds with all overlays:

```bash
python3 video_overlay_player.py video.mp4 --export \
  --end-time 60 \
  --detections yolo_pose mediapipe_pose mediapipe_face
```

### Example 3: Stage Boundary Visualization Only

Export video showing only where the stage boundaries are detected:

```bash
python3 video_overlay_player.py video.mp4 --export \
  --no-yolo \
  --no-mediapipe-pose \
  --no-mediapipe-face \
  --no-info
```

## Performance Notes

- **Processing time**: Expect real-time or slower depending on:
  - Video resolution
  - Number of detection overlays enabled
  - YOLO model size (larger = slower but more accurate)
  - CPU/GPU performance

- **For faster exports**:
  - Use smaller YOLO models (yolo11n-pose.pt)
  - Disable unused overlays with `--no-*` flags
  - Export only the needed time range with `--start-time` and `--end-time`

## Requirements

- Python 3.8+
- OpenCV (opencv-python)
- Ultralytics YOLO (for pose detection)
- MediaPipe (optional, for additional pose/face detection)
- FFmpeg (for H.264 re-encoding)

Install dependencies:

```bash
pip install opencv-python ultralytics mediapipe
```

## Troubleshooting

### FFmpeg Not Found

If you see "Warning: FFmpeg not found", the export will still work but may have compatibility issues. Install FFmpeg:

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

### Out of Memory

For very long videos or high resolutions, you may run out of memory. Solutions:
- Export in smaller time segments using `--start-time` and `--end-time`
- Close other applications
- Use a smaller YOLO model

### Slow Processing

If export is too slow:
- Use `yolo11n-pose.pt` instead of larger models
- Disable unused overlays
- Consider exporting at a lower frame rate (requires code modification)
