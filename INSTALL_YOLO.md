# Installation Guide for YOLO Pose Detection Features

This guide will help you set up the YOLO11/12 pose detection clipper and interactive overlay player.

## Prerequisites

- Python 3.8 - 3.12 (Python 3.11 recommended)
- FFmpeg (for video processing)
- At least 4GB RAM
- Optional: NVIDIA GPU for faster processing

## Quick Install

### 1. Install Python Dependencies

```bash
# Install YOLO pose detection dependencies
pip install -r requirements_yolo.txt
```

This will install:
- `ultralytics` (YOLO11/12)
- `opencv-python` (video processing)
- `pyyaml` (config files)
- `numpy` (numerical operations)
- `mediapipe` (optional, for comparison)

### 2. Verify Installation

```bash
# Check YOLO installation
python3 -c "from ultralytics import YOLO; print('YOLO installed successfully')"

# Check OpenCV
python3 -c "import cv2; print('OpenCV version:', cv2.__version__)"

# Check if config loader works
python3 -c "from config_loader import load_config; print('Config loader OK')"
```

### 3. Test the Scripts

```bash
# Test YOLO pose clipper help
python3 clipper_yolo_pose.py --help

# Test overlay player help
python3 video_overlay_player.py --help
```

## Detailed Installation Steps

### Option A: Using Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv_yolo

# Activate it
source venv_yolo/bin/activate  # On macOS/Linux
# or
venv_yolo\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements_yolo.txt

# Test installation
python3 clipper_yolo_pose.py --help
```

### Option B: System-Wide Installation

```bash
# Install dependencies globally
pip install -r requirements_yolo.txt
```

### Option C: Using existing virtualenv

If you already have a virtualenv for the comedy clipper:

```bash
# Activate your existing virtualenv
source venv/bin/activate

# Install additional dependencies
pip install ultralytics opencv-python pyyaml numpy mediapipe
```

## GPU Acceleration (Optional)

### For NVIDIA GPUs (CUDA)

```bash
# Install PyTorch with CUDA support
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Verify GPU is detected
python3 -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

### For Apple Silicon (M1/M2/M3)

PyTorch with MPS (Metal Performance Shaders) acceleration is installed automatically. YOLO will use it if available:

```bash
# Verify MPS is available
python3 -c "import torch; print('MPS available:', torch.backends.mps.is_available())"
```

## First Run

On first run, YOLO will download model weights (~20-50MB depending on model):

```bash
# This will download yolo11n-pose.pt on first run
python3 clipper_yolo_pose.py test_video.mp4 --help
```

Models are cached in `~/.cache/ultralytics/` and reused for subsequent runs.

## Troubleshooting

### "No module named 'yaml'"

```bash
pip install pyyaml
```

### "No module named 'ultralytics'"

```bash
pip install ultralytics
```

### "cv2 not found" or "OpenCV error"

```bash
pip install opencv-python
```

### Models downloading slowly

First run downloads models from GitHub. If it's slow:

1. Wait it out (it only happens once)
2. Or download manually:
   ```bash
   wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n-pose.pt
   mv yolo11n-pose.pt ~/.cache/ultralytics/
   ```

### "ffmpeg not found"

Install FFmpeg:

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

### Overlay player shows black screen

This usually means OpenCV can't read the video file:

1. Try a different video file
2. Convert video to MP4 H.264:
   ```bash
   ffmpeg -i input.mov -c:v libx264 -c:a aac output.mp4
   ```

### "GPU out of memory"

1. Use a smaller model: `--model yolo11n-pose.pt` (nano)
2. Or disable GPU and use CPU:
   ```bash
   export CUDA_VISIBLE_DEVICES=""
   python3 clipper_yolo_pose.py video.mp4
   ```

## Verifying Everything Works

Run this test script:

```bash
cat > test_yolo.py << 'EOF'
#!/usr/bin/env python3
"""Test YOLO installation"""

import sys

print("Testing YOLO pose detection installation...\n")

# Test imports
try:
    import cv2
    print("✓ OpenCV installed:", cv2.__version__)
except ImportError as e:
    print("✗ OpenCV not found:", e)
    sys.exit(1)

try:
    import numpy as np
    print("✓ NumPy installed:", np.__version__)
except ImportError as e:
    print("✗ NumPy not found:", e)
    sys.exit(1)

try:
    import yaml
    print("✓ PyYAML installed")
except ImportError as e:
    print("✗ PyYAML not found:", e)
    sys.exit(1)

try:
    from ultralytics import YOLO
    print("✓ Ultralytics YOLO installed")

    # Test loading a model
    print("\nTesting YOLO model loading...")
    model = YOLO('yolo11n-pose.pt')
    print("✓ YOLO model loaded successfully")

except ImportError as e:
    print("✗ Ultralytics not found:", e)
    sys.exit(1)
except Exception as e:
    print("✗ Error loading YOLO model:", e)
    sys.exit(1)

try:
    import mediapipe as mp
    print("✓ MediaPipe installed (optional)")
except ImportError:
    print("⚠ MediaPipe not installed (optional, for comparison)")

print("\n✓ All core dependencies installed successfully!")
print("\nYou can now run:")
print("  python3 clipper_yolo_pose.py your_video.mp4")
print("  python3 video_overlay_player.py your_video.mp4")
EOF

chmod +x test_yolo.py
python3 test_yolo.py
```

If this test passes, you're all set!

## Next Steps

1. **Try the interactive player first:**
   ```bash
   python3 video_overlay_player.py your_video.mp4
   ```

2. **Run the YOLO clipper with debug visualization:**
   ```bash
   python3 clipper_yolo_pose.py your_video.mp4 -d
   ```

3. **Compare with MediaPipe:**
   ```bash
   # Run both and compare results
   python3 clipper_unified.py your_video.mp4 --mode pose -d
   python3 clipper_yolo_pose.py your_video.mp4 -d
   ```

## Performance Tips

- **Nano model** (`yolo11n-pose.pt`): Fastest, good accuracy
- **Medium model** (`yolo11m-pose.pt`): Balanced (recommended)
- **XLarge model** (`yolo11x-pose.pt`): Slowest, best accuracy

Start with nano for testing, use medium for production.

## Support

If you encounter issues:

1. Check that all dependencies are installed: `pip list`
2. Verify Python version: `python3 --version` (should be 3.8-3.12)
3. Try the test script above
4. Check the [YOLO_POSE_README.md](YOLO_POSE_README.md) for usage examples
