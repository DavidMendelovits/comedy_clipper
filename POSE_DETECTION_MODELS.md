# Pose Detection Model Testing Suite

A comprehensive collection of scripts to test and compare different pose detection models on video files. Each model outputs a video with pose overlay visualization for easy comparison.

## Available Models

### 1. MediaPipe Pose (`pose_mediapipe.py`)
- **Provider**: Google
- **Pros**: Fast, lightweight, good accuracy, easy to install
- **Cons**: Single-person detection only
- **Best for**: Real-time applications, single-person videos
- **Models**: 3 complexity levels (0=lite, 1=full, 2=heavy)

### 2. MoveNet (`pose_movenet.py`)
- **Provider**: TensorFlow/Google
- **Pros**: Very fast, optimized for edge devices
- **Cons**: Single-person detection, moderate accuracy
- **Best for**: Speed-critical applications, mobile deployment
- **Models**:
  - Lightning (192x192) - fastest
  - Thunder (256x256) - more accurate

### 3. OpenPose (`pose_openpose.py`)
- **Provider**: CMU (via OpenCV DNN)
- **Pros**: Multi-person detection, well-established
- **Cons**: Slower, requires manual model download
- **Best for**: Multi-person scenarios, academic research
- **Models**:
  - COCO (18 keypoints)
  - MPI (15 keypoints)

### 4. MMPose (`pose_mmpose.py`)
- **Provider**: OpenMMLab
- **Pros**: State-of-the-art accuracy, many model options
- **Cons**: Heavy dependencies, slower
- **Best for**: Highest accuracy requirements
- **Models**:
  - RTMPose-M (fast and accurate)
  - RTMPose-L (more accurate)
  - HRNet-W32 (very accurate)
  - HRNet-W48 (highest accuracy)

### 5. YOLO Pose (`clipper_yolo_pose.py`)
- **Provider**: Ultralytics
- **Pros**: Fast, accurate, multi-person detection
- **Cons**: Larger model size
- **Best for**: General purpose, multi-person detection
- **Models**: YOLOv8/v11 Pose variants

## Installation

### Quick Start (MediaPipe only)
```bash
pip install -r requirements_mediapipe.txt
```

### Install All Models
```bash
pip install -r requirements_pose_all.txt
```

### Individual Model Installation

**MediaPipe:**
```bash
pip install -r requirements_mediapipe.txt
```

**MoveNet:**
```bash
pip install -r requirements_movenet.txt
```

**OpenPose:**
```bash
pip install -r requirements_openpose.txt

# Download models manually from:
# https://github.com/CMU-Perceptual-Computing-Lab/openpose/tree/master/models
```

**MMPose:**
```bash
pip install -r requirements_mmpose.txt
```

## Usage

### Individual Model Scripts

#### MediaPipe Pose
```bash
# Basic usage
python pose_mediapipe.py input_video.mp4

# Specify output and complexity
python pose_mediapipe.py input_video.mp4 -o output.mp4 -c 2

# Options:
#   -c, --complexity: 0 (lite), 1 (full), 2 (heavy) - default: 2
#   --min-detection: Minimum detection confidence (default: 0.5)
#   --min-tracking: Minimum tracking confidence (default: 0.5)
```

#### MoveNet
```bash
# Thunder model (more accurate)
python pose_movenet.py input_video.mp4

# Lightning model (faster)
python pose_movenet.py input_video.mp4 -m lightning

# Options:
#   -m, --model: lightning or thunder (default: thunder)
#   -c, --confidence: Minimum confidence threshold (default: 0.3)
```

#### OpenPose
```bash
# COCO model (18 keypoints)
python pose_openpose.py input_video.mp4 -m /path/to/openpose/models

# MPI model (15 keypoints)
python pose_openpose.py input_video.mp4 -m /path/to/openpose/models -t MPI

# Options:
#   -m, --model-dir: Directory containing OpenPose models (required)
#   -t, --type: COCO or MPI (default: COCO)
#   -c, --confidence: Minimum confidence threshold (default: 0.1)
```

#### MMPose
```bash
# RTMPose-M (balanced)
python pose_mmpose.py input_video.mp4

# RTMPose-L (more accurate)
python pose_mmpose.py input_video.mp4 -m rtmpose-l

# HRNet-W48 (highest accuracy)
python pose_mmpose.py input_video.mp4 -m hrnet-w48

# With GPU
python pose_mmpose.py input_video.mp4 -d cuda:0

# Options:
#   -m, --model: rtmpose-m, rtmpose-l, hrnet-w32, hrnet-w48
#   -d, --device: cpu or cuda:0 (default: cpu)
#   -c, --confidence: Minimum confidence threshold (default: 0.3)
```

### Comparison Script

Run multiple models on the same video and generate a comparison report:

```bash
# Run all available models
python compare_pose_models.py input_video.mp4

# Run specific models
python compare_pose_models.py input_video.mp4 --models mediapipe movenet-thunder yolo

# Include OpenPose
python compare_pose_models.py input_video.mp4 \
  --models mediapipe movenet-thunder openpose-coco \
  --openpose-dir /path/to/openpose/models

# Include MMPose with GPU
python compare_pose_models.py input_video.mp4 \
  --models mediapipe mmpose-rtmpose-m mmpose-hrnet-w48 \
  --device cuda:0

# Specify output directory
python compare_pose_models.py input_video.mp4 -o results/

# Available model options:
#   - mediapipe
#   - movenet-lightning
#   - movenet-thunder
#   - openpose-coco
#   - openpose-mpi
#   - mmpose-rtmpose-m
#   - mmpose-rtmpose-l
#   - mmpose-hrnet-w32
#   - mmpose-hrnet-w48
#   - yolo
```

The comparison script will:
1. Run each selected model on the input video
2. Generate overlay videos for each model
3. Collect performance statistics (FPS, detection rate, processing time)
4. Create a detailed comparison report (`comparison_report.txt`)
5. Save results as JSON (`comparison_report.json`)

## Output Format

All scripts generate:
- **Video file**: Original video with pose overlay
  - Green skeleton when pose detected
  - Red "NO POSE" indicator when not detected
  - Real-time FPS display
  - Frame counter
  - Model name indicator

- **Console statistics**:
  - Total frames processed
  - Frames with pose detected
  - Detection rate (%)
  - Average processing time per frame (ms)
  - Average FPS

## Performance Comparison Guide

When comparing models, consider:

### Speed
- **Fastest**: MoveNet Lightning, MediaPipe Lite (Complexity 0)
- **Fast**: MediaPipe Full, MoveNet Thunder, RTMPose-M
- **Moderate**: YOLO Pose, OpenPose
- **Slow**: HRNet models

### Accuracy
- **Highest**: HRNet-W48, HRNet-W32
- **High**: RTMPose-L, MediaPipe Heavy
- **Good**: YOLO Pose, RTMPose-M, MoveNet Thunder
- **Moderate**: MoveNet Lightning, MediaPipe Lite

### Multi-person Support
- **Yes**: OpenPose, YOLO Pose, MMPose (with detector)
- **No**: MediaPipe, MoveNet

### Resource Usage
- **Low**: MediaPipe, MoveNet
- **Moderate**: RTMPose, YOLO
- **High**: HRNet, OpenPose (CPU)

## Troubleshooting

### MediaPipe Issues
- If you get import errors, ensure you have a recent version of Python (3.8+)
- On Mac M1/M2, you might need: `pip install mediapipe --user`

### MoveNet Issues
- Large model downloads on first run (may take several minutes)
- TensorFlow requires Python 3.8-3.11 (not 3.12+)

### OpenPose Issues
- **Model not found**: Download models from the OpenPose GitHub repository
- **Slow performance**: Consider using GPU version of OpenCV or switching to another model

### MMPose Issues
- **Import errors**: Install in order: `torch` → `mmcv` → `mmengine` → `mmdet` → `mmpose`
- **CUDA errors**: Ensure PyTorch CUDA version matches your CUDA installation
- **Model download**: First run downloads models automatically (may be slow)

### General Issues
- **Out of memory**: Reduce video resolution or use a lighter model
- **Slow processing**: Use GPU acceleration or switch to faster model
- **Low detection rate**: Adjust confidence thresholds or try different models

## Model Download Links

### OpenPose Models
- **COCO (18 keypoints)**:
  - `pose_deploy_linevec.prototxt`
  - `pose_iter_440000.caffemodel`
- **MPI (15 keypoints)**:
  - `pose_deploy_linevec_faster_4_stages.prototxt`
  - `pose_iter_160000.caffemodel`
- **Download**: https://github.com/CMU-Perceptual-Computing-Lab/openpose/tree/master/models

### YOLO Models
```bash
# YOLOv11 Pose models auto-download, or manual download:
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolo11n-pose.pt
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolo11l-pose.pt
```

## Example Workflows

### Quick Test (Single Model)
```bash
# Test with MediaPipe (fastest setup)
pip install -r requirements_mediapipe.txt
python pose_mediapipe.py my_video.mp4
```

### Full Comparison (All Models)
```bash
# Install all dependencies
pip install -r requirements_pose_all.txt

# Download OpenPose models to ./openpose_models/
# ... (download from GitHub)

# Run comparison
python compare_pose_models.py my_video.mp4 \
  --models mediapipe movenet-thunder openpose-coco mmpose-rtmpose-m yolo \
  --openpose-dir ./openpose_models/ \
  -o comparison_results/
```

### Best Accuracy Test
```bash
pip install -r requirements_mmpose.txt
python pose_mmpose.py my_video.mp4 -m hrnet-w48 -d cuda:0
```

### Best Speed Test
```bash
pip install -r requirements_movenet.txt
python pose_movenet.py my_video.mp4 -m lightning
```

## Integration with Comedy Clipper

These pose detection scripts can be integrated with the Comedy Clipper project:

1. **Test pose detection quality** on comedy videos
2. **Compare models** to find best balance of speed/accuracy
3. **Use pose data** for comedian detection and tracking
4. **Analyze body language** for comedy timing analysis

## References

- **MediaPipe**: https://google.github.io/mediapipe/solutions/pose
- **MoveNet**: https://www.tensorflow.org/hub/tutorials/movenet
- **OpenPose**: https://github.com/CMU-Perceptual-Computing-Lab/openpose
- **MMPose**: https://github.com/open-mmlab/mmpose
- **YOLO**: https://docs.ultralytics.com/tasks/pose/

## License

These scripts are provided as-is for testing and research purposes. Each model library has its own license - please refer to the respective project repositories for license details.
