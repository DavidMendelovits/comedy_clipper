# YOLOv8 Person Detection Implementation Analysis

## Overview

The Comedy Clipper codebase integrates YOLOv8 person detection to reliably track performers on stage and distinguish them from audience members. This document provides a comprehensive analysis of the configuration, parameters, and spatial filtering logic.

---

## 1. Configuration & Initialization

### Configuration Location
- **Primary Config File**: `clipper_rules.yaml`
- **YOLO Settings**: Lines 129-142

### YOLO Detection Configuration

```yaml
yolo_detection:
  # Enable YOLO detector (requires ultralytics package)
  enabled: true

  # YOLO model to use
  # Options: yolov8n.pt (nano, fastest), yolov8s.pt (small), yolov8m.pt (medium)
  model: "yolov8n.pt"

  # Detection confidence threshold (0.0-1.0)
  confidence: 0.5

  # Maximum frames an object can disappear before deregistration
  # Higher = more persistent tracking across occlusions
  max_disappeared_frames: 30
```

### Key Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `enabled` | `true` | Enables YOLO-based person detection |
| `model` | `yolov8n.pt` | Nano model: fastest inference, sufficient accuracy for comedy shows |
| `confidence` | `0.5` | Detection threshold - 50% confidence needed for person detection |
| `max_disappeared_frames` | `30` | Frames person can vanish before being "forgotten" (~1 second at 30fps) |

---

## 2. Implementation in Code

### Primary Implementation Files

#### **clipper_unified.py** (Lines 189-208)
Complete integrated implementation with YOLO support.

```python
# Initialize YOLO detector if enabled
yolo_enabled = self.config.get("yolo_detection.enabled", False)
if yolo_enabled and self.mode in ["multimodal", "yolo_zone"]:
    if not YOLO_AVAILABLE:
        raise ImportError("Ultralytics not installed")
    
    print("Initializing YOLO detector...")
    model_name = self.config.get("yolo_detection.model", "yolov8n.pt")
    self.yolo = YOLO(model_name)
    
    # Initialize centroid tracker
    max_disappeared = self.config.get("yolo_detection.max_disappeared_frames", 30)
    self.person_tracker = CentroidTracker(max_disappeared=max_disappeared)
```

#### **clipper_pose.py** (Lines 17-32)
Dedicated YOLO-only implementation for simple stage entry/exit detection.

```python
from ultralytics import YOLO

class PoseDetectionClipper:
    def __init__(self, model_size: str = "n", debug: bool = False):
        print(f"Loading YOLO{model_size} model for person detection...")
        self.model = YOLO(f'yolov8{model_size}.pt')
```

---

## 3. Detection & Sensitivity Parameters

### Detection Sensitivity Control

#### **Confidence Threshold** (clipper_unified.py, lines 554-555)

```python
yolo_confidence = self.config.get("yolo_detection.confidence", 0.5)
results = self.yolo(frame, classes=[0], conf=yolo_confidence, verbose=False)
```

- **Range**: 0.0 to 1.0
- **Current Setting**: 0.5 (50% confidence)
- **Effect**: 
  - Lower values = MORE detections (higher false positives)
  - Higher values = FEWER detections (higher false negatives)
  - 0.5 is reasonable balance for standup comedy (clear, well-lit performers)

#### **Class Filtering**

```python
results = self.yolo(frame, classes=[0], conf=yolo_confidence, verbose=False)
```

- Only detects class 0 from COCO dataset = **PERSON class only**
- Other classes (chairs, microphones, etc.) are ignored

#### **Tracking Persistence** (max_disappeared_frames)

```python
max_disappeared = self.config.get("yolo_detection.max_disappeared_frames", 30)
self.person_tracker = CentroidTracker(max_disappeared=max_disappeared)
```

- **Current Setting**: 30 frames
- **Effect**: A person can be absent from YOLO detections for up to 30 frames before being "forgotten"
- **Use Case**: Handles occlusions, false negatives, and brief disappearances
- **At 30fps**: 30 frames = ~1 second of persistence

---

## 4. Stage Boundary & Zone Crossing Detection

### Zone Crossing Configuration

```yaml
zone_crossing:
  # Enable zone crossing detection
  enabled: true  # ENABLED to exclude audience in foreground

  # Stage boundary definition
  stage_boundary:
    # Type: "polygon" or "rectangle"
    type: "rectangle"

    # For rectangle: specify bounds (in pixels or as fraction of frame if < 1.0)
    # These values define the stage area
    # ADJUSTED FOR FOREGROUND AUDIENCE: excludes bottom 15% where audience heads appear
    left: 0.05   # 5% from left edge (wide to include full stage)
    right: 0.95  # 95% from left edge (5% from right)
    top: 0.0     # Start from very top
    bottom: 0.85 # Stop at 85% down (excludes bottom 15% where audience is)

  # Buffer zone (pixels) to prevent double-counting from position wobbling
  buffer_zone: 50

  # Minimum frames person must be inside/outside before counting as stable
  min_frames_inside: 3
```

### How It Works

#### **Zone Checker Creation** (clipper_unified.py, lines 235-306)

```python
def _create_zone_checker(self, frame_width, frame_height):
    """Create a zone checker function based on configuration."""
    
    if boundary_type == "rectangle":
        # Convert fractions to pixels if needed (values < 1.0 are fractions)
        if left < 1.0:
            left = int(left * frame_width)
        if right < 1.0:
            right = int(right * frame_width)
        if top < 1.0:
            top = int(top * frame_height)
        if bottom < 1.0:
            bottom = int(bottom * frame_height)
        
        def check_zone(centroid):
            """Check if centroid is inside rectangle"""
            x, y = centroid
            inside = left <= x <= right and top <= y <= bottom
            return "inside" if inside else "outside"
```

#### **Zone Boundary Coordinates (for typical 1920x1080 video)**

| Boundary | Value | Pixels | Purpose |
|----------|-------|--------|---------|
| left | 0.05 | 96px | Includes performers near stage left edge |
| right | 0.95 | 1824px | Includes performers near stage right edge |
| top | 0.0 | 0px | Full height from top |
| bottom | 0.85 | 918px | STOPS at 85% - excludes audience sitting in front (bottom 15%) |

**Key Insight**: The bottom boundary stops at 85% to **exclude audience members' heads that appear in the foreground**, ensuring only stage performers are counted.

---

## 5. Distinguishing Comedians vs Audience

### Multi-Layered Approach

#### **Spatial Filtering (Primary Method)**

The zone boundary configuration is the PRIMARY mechanism for audience exclusion:

```
┌─────────────────────────────────────┐
│  STAGE AREA (zone_crossing enabled) │
│  left=5%, right=95%, top=0%         │
│  ────────────────────────────────   │ bottom=85%
│  AUDIENCE AREA (excluded)           │
│  bottom=85-100% (sitting area)      │
└─────────────────────────────────────┘
```

**Result**: 
- Comedians performing on stage (upper 85% of frame) = INSIDE zone
- Audience members sitting in foreground (bottom 15%) = OUTSIDE zone

#### **Person Count Methods** (clipper_unified.py, lines 586-606)

The `person_count_method` configuration determines how to count people:

```python
person_count_method = self.config.get("transition_detection.person_count_method", "min")

if person_count_method == "yolo":
    # Use YOLO count (all detected people)
    person_count = num_yolo_persons
    
elif person_count_method == "yolo_zone":
    # Use YOLO count inside zone only (CURRENT SETTING)
    person_count = yolo_person_count_inside
    
elif person_count_method == "hybrid":
    # Prefer YOLO if available, fallback to max(faces, poses)
    if num_yolo_persons > 0:
        person_count = num_yolo_persons
    else:
        person_count = max(num_faces, num_poses)
```

**Current Config Setting**:
```yaml
person_count_method: yolo_zone  # Changed from yolo to exclude audience
```

This means:
- YOLO detects ALL people in the frame
- CentroidTracker categorizes them as "inside" or "outside" zone
- Only people **inside the stage boundary** are counted
- Audience members outside the boundary are ignored

#### **Centroid Tracking** (person_tracker.py, lines 159-165)

```python
def get_count_inside_zone(self):
    """Get count of objects currently inside the zone."""
    return sum(1 for state in self.zone_states.values() if state == "inside")

def get_count_outside_zone(self):
    """Get count of objects currently outside the zone."""
    return sum(1 for state in self.zone_states.values() if state == "outside")
```

Each detected person is assigned a "zone_state":
- "inside" = stage performer
- "outside" = audience member
- "unknown" = newly detected, not yet classified

---

## 6. Detection & Filtering Logic

### Frame Processing Pipeline

```
Frame Input
    ↓
[Blur Detection] (optional)
    ↓
[YOLO Person Detection] (class 0 only)
    ↓ Extract bounding boxes from detections
    ↓
[Centroid Tracker] Update tracked objects
    ↓ Calculate centroids from bounding boxes
    ↓
[Zone Checker] Classify inside/outside
    ↓
[Count Extraction] Get inside/outside counts
    ↓
[Person Count Selection] Use yolo_zone method
    ↓
[Kalman Smoothing] Optional position filtering
    ↓
[Median Smoothing] Reduce count noise
    ↓
[Transition Analysis] Detect 0→1, 1→2 changes
```

### YOLO Bounding Box Processing (clipper_unified.py, lines 557-566)

```python
if len(results) > 0 and len(results[0].boxes) > 0:
    # Extract bounding boxes [x1, y1, x2, y2]
    boxes = results[0].boxes.xyxy.cpu().numpy()
    
    for box in boxes:
        x1, y1, x2, y2 = box
        w = x2 - x1
        h = y2 - y1
        yolo_detections.append((x1, y1, w, h))
        num_yolo_persons += 1
```

Box format conversion:
- YOLO returns: [x1, y1, x2, y2] (top-left and bottom-right corners)
- Converted to: [x1, y1, w, h] (top-left corner and dimensions)
- CentroidTracker converts to: (cx, cy) centroid for tracking

---

## 7. Smoothing & Stability

### Person Count Smoothing (clipper_unified.py, lines 658-688)

```yaml
person_count_smoothing: true
smoothing_window: 5  # Median filter window size (number of frames)
```

**Implementation**:
```python
# Extract person counts
person_counts = [d[3] for d in detection_history]

# Apply median filter
for i in range(len(person_counts)):
    start = max(0, i - window_size // 2)
    end = min(len(person_counts), i + window_size // 2 + 1)
    window = person_counts[start:end]
    
    # Calculate median
    sorted_window = sorted(window)
    median = sorted_window[len(sorted_window) // 2]
    smoothed_counts.append(median)
```

**Effect**:
- Window size 5 = uses 5-frame sliding window
- Median filter = robust to noise and outliers
- Example: [1, 2, 1, 1, 2, 1, 2] with window=5 → smooths to [1, 1, 1, 1, 1, 1, 1]
- Prevents false transitions from detection noise

### Kalman Filter for Position (optional)

```yaml
kalman_filter:
  enabled: true
  process_noise: 1.0      # How much we trust the model
  measurement_noise: 5.0  # How much we trust measurements
  initial_covariance: 10.0
```

Smooths X position of detected person across frames, but does NOT affect count.

---

## 8. Transition Detection Rules

### Configured Transition Rules (clipper_rules.yaml, lines 43-80)

```yaml
transition_detection:
  rules:
    # Host + Comedian → Comedian only (host exits)
    - from: 2
      to: 1
      action: start_segment
      
    # Comedian only → Host + Comedian (host enters)
    - from: 1
      to: 2
      action: end_segment
      
    # Empty stage → Person appears
    - from: 0
      to: 1
      action: start_segment
      
    # Person on stage → Empty stage
    - from: 1
      to: 0
      action: end_segment
      
    # Multiple people on stage
    - from: any
      to: 2+
      action: start_segment
      
    # People exit
    - from: 2+
      to: 1-
      action: end_segment
```

**Transition Stability** (prevents flicker):
```yaml
transition_stability_frames: 2  # Need stable count for 2 frames before triggering
```

At 1 frame/sec sampling = 2 seconds of stable count before transition triggers.

---

## 9. Fallback Detection (Position-Based)

If NO transitions detected, falls back to position-based detection:

```yaml
position_detection:
  enabled: true
  
  # Stage boundary thresholds (0.0 to 0.5)
  # 0.15 = person is within 15% of frame edge
  exit_threshold: 0.15
  
  # Position must be stable for N frames before triggering exit
  exit_stability_frames: 2
  
  # Track position of:
  tracking_point: torso  # or "center" (bounding box center)
```

**How it Works**:
1. Tracks X position of detected person
2. If position goes outside edge zones (< 15% or > 85% from edges), triggers end
3. Fallback ensures clips are found even without clear transitions

---

## 10. Sample Configurations for Different Scenarios

### Strict Audience Exclusion (Current)
```yaml
zone_crossing:
  enabled: true
  stage_boundary:
    type: rectangle
    left: 0.05
    right: 0.95
    top: 0.0
    bottom: 0.85  # Excludes bottom 15% (audience)
person_count_method: yolo_zone
```

### Full Frame Detection (All People)
```yaml
person_count_method: yolo  # Count all detected people
# zone_crossing can be disabled
```

### Hybrid (Fallback to MediaPipe)
```yaml
person_count_method: hybrid
# Uses YOLO if available, falls back to max(faces, poses)
```

### Conservative (MediaPipe Only)
```yaml
yolo_detection:
  enabled: false
person_count_method: min  # min(faces, poses)
```

---

## 11. Performance & Accuracy Trade-offs

| Setting | Detection | Audience | Speed | Accuracy |
|---------|-----------|----------|-------|----------|
| YOLO nano + zone | Best | Excellent | Fast | High |
| YOLO small + zone | Better | Excellent | Medium | Higher |
| MediaPipe + min | Good | Fair | Fast | Medium |
| Position-based | Fair | Good | Very Fast | Low |

**Recommendation**: Current config (YOLO nano + zone) provides best balance.

---

## 12. Key Files Summary

| File | Purpose | Key Lines |
|------|---------|-----------|
| `clipper_rules.yaml` | Configuration | 129-170 (YOLO & zone config) |
| `clipper_unified.py` | Main implementation | 189-606 (YOLO detection & tracking) |
| `clipper_pose.py` | YOLO-only variant | 17-250 (Simple entry/exit detection) |
| `person_tracker.py` | Centroid tracking | 55-157 (Zone state tracking) |
| `config_loader.py` | Config validation | 62-93 (Config access methods) |

---

## 13. Example Detection Flow

### Scenario: Two comedians with host

**Frame 1**: Host on stage
```
YOLO detects: 1 person
Zone check: Inside stage area
person_count = 1
```

**Frame 2**: Comedian joins host
```
YOLO detects: 2 people
Zone check: Both inside stage area
person_count = 2 (stable for 2 frames)
Transition: 1→2 triggers END_SEGMENT
```

**Frame 3-10**: Comedian performs alone
```
YOLO detects: 1-2 people (maybe some audience members)
Zone check: Only 1 inside, others outside
person_count = 1 (inside zone)
```

**Frame 11**: Host returns
```
YOLO detects: 2 people in upper area
Zone check: Both inside
person_count = 2 (stable)
```

---

## Conclusion

The YOLOv8 implementation uses:
1. **YOLO Detection** for reliable multi-person detection
2. **Centroid Tracking** to maintain object identities
3. **Zone Boundaries** to filter audience members (spatial filtering)
4. **Transition Rules** to detect performer changes
5. **Smoothing** (median + Kalman) to reduce false positives

The current configuration prioritizes **audience exclusion** via the `yolo_zone` method, which only counts people **inside the defined stage boundary**, ensuring accurate detection of stage performers only.

