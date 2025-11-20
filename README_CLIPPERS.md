# Comedy Clipper - Implementation Comparison

Three different approaches for automatically clipping comedy sets from standup show recordings.

## 🎯 Quick Comparison

| Feature | YOLO (clipper_pose.py) | MediaPipe (clipper_mediapipe.py) | Advanced (clipper_advanced.py) |
|---------|----------------------|--------------------------------|------------------------------|
| **Detection Method** | Bounding box | Body landmarks | Face + Pose + Kalman |
| **Accuracy** | Good | Better | Best |
| **Speed** | Fast | Medium | Slower |
| **Python Version** | Any | 3.8-3.12 | 3.8-3.12 |
| **Best For** | Simple exits | Single performer | Multi-person shows |
| **Kalman Filter** | ❌ | ❌ | ✅ |
| **Multi-Modal** | ❌ | ❌ | ✅ Face + Pose |

---

## 1️⃣ YOLO Pose Clipper (clipper_pose.py)

**Best for:** Simple, fast processing with YOLO models

### How It Works
- Uses YOLO to detect person bounding boxes
- Tracks horizontal position of bounding box center
- Clips when person exits stage left/right (within 15% of frame edge)
- Simple interpolation for missing frames

### Usage
```bash
# Basic usage
python3 clipper_pose.py test_vid.MOV -d -m 180

# Options
-d              # Debug mode (export first/last frames with overlays)
-m 180          # Minimum duration in seconds (default: 180 = 3 min)
-e 0.15         # Exit threshold (default: 0.15 = 15% from edge)
-c 0.5          # Confidence threshold (default: 0.5)
-s n            # Model size: n=nano, s=small, m=medium, l=large
```

### Requirements
```bash
pip install opencv-python ultralytics numpy
```

### Output
- Clips: `<video>_clips_<timestamp>/`
- Debug: `<video>_debug_<timestamp>/`

---

## 2️⃣ MediaPipe Clipper (clipper_mediapipe.py)

**Best for:** Accurate single-performer tracking

### How It Works
- Uses MediaPipe Pose to track 33 body landmarks
- Tracks torso center (average of shoulders + hips) - more stable than bounding box
- Detects stage exits based on torso position
- Shows full skeleton overlay in debug frames

### Usage
```bash
# Requires Python 3.8-3.12
source venv_mediapipe/bin/activate

# Basic usage
python3 clipper_mediapipe.py test_vid.MOV -d -m 180

# Options
-d              # Debug mode (skeleton overlays)
-m 180          # Minimum duration in seconds
-e 0.15         # Exit threshold
```

### Requirements
```bash
pip install -r requirements_mediapipe.txt
```

### Advantages
- More accurate position tracking (torso vs bounding box)
- 33 landmark points for full body understanding
- Built-in landmark smoothing
- Better handles pose variations

---

## 3️⃣ Advanced Multi-Modal Clipper (clipper_advanced.py) ⭐

**Best for:** Professional results with host + comedian format

### How It Works
1. **Face Detection**: Counts faces using MediaPipe Face Detection
2. **Pose Detection**: Counts people using MediaPipe Pose
3. **Kalman Filtering**: Smooth, robust position tracking even with missing frames
4. **Transition Detection**: Primary mode
   - Detects 2→1 transitions (comedian exits, host remains)
   - Detects 1→2 transitions (comedian enters with host)
5. **Fallback Mode**: Position-based detection if no transitions found

### Usage
```bash
# Requires Python 3.8-3.12
source venv_mediapipe/bin/activate

# Basic usage
python3 clipper_advanced.py test_vid.MOV -d -m 180

# Options
-d              # Debug mode (face + pose overlays)
-m 180          # Minimum duration in seconds
-e 0.15         # Stage boundary threshold
```

### Requirements
```bash
pip install -r requirements_advanced.txt
```

### Features
✅ **Dual Detection**: Face + Pose for higher confidence
✅ **Kalman Filter**: Eliminates flaky detection
✅ **Multi-Mode**: Handles both host+comedian and single performer
✅ **Rich Debug**: Shows both face bounding boxes and skeleton overlays
✅ **Confidence Scoring**: min(faces, poses) for conservative estimates

### Debug Frame Overlays
- **Green skeleton**: Pose landmarks
- **Blue boxes**: Face detections
- **Red lines**: Stage boundaries (15% from edges)
- **Text info**: Frame number, face count, pose count, confidence

---

## 🚀 Test Results (test_vid.MOV)

### YOLO Clipper
```
3 segments detected
- Comedian 1: 2m 0s
- Comedian 2: 7m 14s
- Comedian 3: 5m 41s
```

### Advanced Clipper
```
4 segments detected (using position-based fallback)
- Comedian 1: 6m 10s
- Comedian 2: 3m 3s
- Comedian 3: 2m 43s
- Comedian 4: 2m 49s
```

---

## 📊 When to Use Each

### Use YOLO if:
- You need maximum speed
- You're okay with bounding box approximations
- You don't need Python 3.8-3.12 specifically
- Simple single-performer videos

### Use MediaPipe if:
- You want accurate pose tracking
- You need torso-specific positioning
- Single performer videos
- You can use Python 3.8-3.12

### Use Advanced if:
- **You have host + comedian format** ⭐
- You need maximum accuracy
- You want robust tracking (Kalman filter)
- You need confidence scores
- Professional production quality
- You can use Python 3.8-3.12

---

## 🔧 Environment Setup

### For YOLO (Any Python version)
```bash
python3 -m venv venv
source venv/bin/activate
pip install opencv-python ultralytics numpy
```

### For MediaPipe/Advanced (Python 3.8-3.12)
```bash
# Install Python 3.11 with pyenv
pyenv install 3.11.10

# Create venv with Python 3.11
/Users/davidmendelovits/.pyenv/versions/3.11.10/bin/python3 -m venv venv_mediapipe
source venv_mediapipe/bin/activate

# Install dependencies
pip install -r requirements_advanced.txt
```

---

## 📁 Output Structure

All clippers create timestamped folders:

```
video_name_clips_<timestamp>/
├── video_name_comedian01_6m10s.mp4
├── video_name_comedian02_3m3s.mp4
└── ...

video_name_debug_<timestamp>/          # YOLO
video_name_debug_mediapipe_<timestamp>/ # MediaPipe
video_name_debug_advanced_<timestamp>/  # Advanced
├── segment01_first_frame0.jpg
├── segment01_last_frame11102.jpg
└── ...
```

---

## 🎬 Production Recommendation

For **best results** with standup comedy shows:

1. **Try Advanced first** (handles multiple scenarios)
2. **Fall back to MediaPipe** (if single performer)
3. **Use YOLO** (for quick processing or Python 3.13+)

The Advanced clipper automatically falls back to position-based detection, so it works for both multi-person and single-performer videos!
