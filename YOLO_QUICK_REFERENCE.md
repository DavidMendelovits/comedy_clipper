# YOLOv8 Person Detection - Quick Reference

## Configuration Quick Lookup

### Enable/Disable YOLO
```yaml
yolo_detection:
  enabled: true  # Set to false to disable
```

### Detection Sensitivity (0.0-1.0)
```yaml
yolo_detection:
  confidence: 0.5  # Lower = more detections, Higher = fewer detections
```

### Audience Exclusion Method
```yaml
# In config file, look for person_count_method:
person_count_method: yolo_zone  # Only counts people inside stage boundary

# Alternative values:
#   yolo      = count all detected people (includes audience)
#   yolo_zone = count only people in stage area (audience excluded)
#   hybrid    = prefer YOLO if available, fallback to MediaPipe
#   min/max/average = use MediaPipe face+pose methods
```

### Stage Boundary Definition
```yaml
zone_crossing:
  enabled: true
  stage_boundary:
    type: "rectangle"
    left: 0.05     # 5% from left edge
    right: 0.95    # 95% from left edge (5% from right)
    top: 0.0       # Start from top
    bottom: 0.85   # STOP at 85% down (excludes audience in bottom 15%)
```

---

## Key Parameters & Their Effects

### Confidence Threshold
| Value | Effect |
|-------|--------|
| 0.3 | Very sensitive, many false positives |
| 0.5 | **DEFAULT** - Good balance |
| 0.7 | Conservative, may miss some detections |
| 0.9 | Very strict, only obvious people |

### Max Disappeared Frames
| Value | Persistence | Use Case |
|-------|-------------|----------|
| 10 | 0.3s @ 30fps | Quick reactions |
| 30 | **DEFAULT** 1s @ 30fps | Standard tracking |
| 60 | 2s @ 30fps | Occluded performers |

### Person Count Method
| Method | Includes Audience | Best For |
|--------|------------------|----------|
| `yolo` | YES - all detected people | Audience interaction |
| `yolo_zone` | **NO** - stage only | **Recommended - pure performance** |
| `hybrid` | Fallback capability | Unreliable lighting |
| `min/max` | Depends on faces/poses | Low-light situations |

---

## Visual: Stage Boundary (Rectangle Mode)

```
Top (0%)    ┌─────────────────────────────────┐
            │       STAGE AREA                 │
            │    (zone = "inside")             │
            │                                  │
            │ Left 5%             Right 95%   │
            │ ▼                    ▼           │
            │ ┌──────────────────────────┐    │
            │ │                          │    │
            │ │    PERFORMERS HERE       │    │
            │ │                          │    │
            │ └──────────────────────────┘    │
            │                                  │
Bottom 85%  ├─────────────────────────────────┤  ← Boundary Cut-off
            │   AUDIENCE AREA                  │
            │ (zone = "outside" - ignored)    │
            │                                  │
Bottom 100%└─────────────────────────────────┘
```

**For 1920x1080 video:**
- Left boundary: 96px (1920 * 0.05)
- Right boundary: 1824px (1920 * 0.95)
- Top boundary: 0px
- Bottom boundary: 918px (1080 * 0.85)

---

## Detection Pipeline

```
Video Frame
    │
    ▼ [YOLO Detection] - Detects all people (class 0)
    │ Output: All bounding boxes in frame
    │
    ▼ [Centroid Tracker] - Tracks identity across frames
    │ Output: {person_id → (cx, cy)}
    │
    ▼ [Zone Checker] - Is centroid inside/outside boundary?
    │ Output: {person_id → "inside"/"outside"}
    │
    ▼ [Count Selection] - Count only "inside" (yolo_zone method)
    │ Output: person_count = count of "inside"
    │
    ▼ [Smoothing] - Median filter to reduce noise
    │ Output: smoothed_person_count
    │
    ▼ [Transition Detection] - Does person_count match a rule?
    │ Output: Segment boundaries
    │
    ▼ Video Clips
```

---

## Troubleshooting

### Problem: Too many false positives (detecting audience)
**Solution**: Lower the bottom boundary value
```yaml
bottom: 0.75  # Instead of 0.85 - cuts off more audience area
```

### Problem: Missing stage performers (too few detections)
**Solution**: Lower confidence threshold
```yaml
confidence: 0.4  # Instead of 0.5 - more sensitive
```

### Problem: Detecting audience members as stage performers
**Solution**: Use yolo_zone instead of yolo
```yaml
person_count_method: yolo_zone  # Only count inside boundary
```

### Problem: Jittery detection / false transitions
**Solution**: Increase stability window
```yaml
person_count_smoothing: true
smoothing_window: 7  # Was 5 - use larger window
```

### Problem: Missing transitions (comedian performances not detected)
**Solution**: Lower stability frames requirement
```yaml
transition_stability_frames: 1  # Was 2 - trigger faster
```

---

## Comparison: Audience Exclusion Methods

### Method 1: Spatial Filtering (CURRENT - RECOMMENDED)
```yaml
person_count_method: yolo_zone
zone_crossing:
  enabled: true
  stage_boundary:
    bottom: 0.85  # Exclude bottom 15%
```
**Pros**: Simple, reliable, fast  
**Cons**: Fixed boundary may not work for all venues  
**Best for**: Standard comedy club layout

### Method 2: Object Detection Only
```yaml
person_count_method: yolo
zone_crossing:
  enabled: false
```
**Pros**: Counts all people (useful for audience interaction)  
**Cons**: Cannot distinguish comedians from audience  
**Best for**: Audience participation tracking

### Method 3: Hybrid with Face Detection
```yaml
person_count_method: hybrid
yolo_detection:
  enabled: true
confidence:
  face_detection:
    model_selection: 1  # Full range (vs 0 for short range)
```
**Pros**: Falls back if YOLO fails  
**Cons**: Slower (runs multiple detectors)  
**Best for**: Unreliable conditions

---

## Performance Impact

### YOLO Model Sizes
| Model | Speed | Accuracy | RAM |
|-------|-------|----------|-----|
| yolov8n (nano) | ⚡⚡⚡ Fastest | ⭐⭐⭐⭐ | Low |
| yolov8s (small) | ⚡⚡ Fast | ⭐⭐⭐⭐⭐ | Medium |
| yolov8m (medium) | ⚡ Medium | ⭐⭐⭐⭐⭐⭐ | High |
| yolov8l (large) | 🐢 Slow | Perfect | Very High |

**Default (nano)**: Best balance for most cases

---

## Code References

### Enable YOLO in Python
```python
from ultralytics import YOLO

# Load model
model = YOLO('yolov8n.pt')  # nano

# Run detection
results = model(frame, classes=[0], conf=0.5, verbose=False)

# Extract boxes [x1, y1, x2, y2]
for result in results:
    for box in result.boxes:
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
```

### Zone Checking in Python
```python
def check_zone(centroid, left, right, top, bottom):
    x, y = centroid
    inside = left <= x <= right and top <= y <= bottom
    return "inside" if inside else "outside"
```

### Count People Inside Zone
```python
person_tracker.update(yolo_detections, zone_checker=zone_checker)
inside_count = person_tracker.get_count_inside_zone()
outside_count = person_tracker.get_count_outside_zone()
```

---

## File Paths

| Feature | Config File | Code File | Lines |
|---------|-------------|-----------|-------|
| YOLO settings | `clipper_rules.yaml` | - | 129-142 |
| Zone boundary | `clipper_rules.yaml` | - | 150-175 |
| Person count method | `clipper_rules.yaml` | - | 96 |
| Detection logic | - | `clipper_unified.py` | 552-584 |
| Zone checking | - | `clipper_unified.py` | 235-306 |
| Centroid tracking | - | `person_tracker.py` | 55-157 |

---

## Common Configuration Templates

### Template 1: Strict Comedy Club
```yaml
yolo_detection:
  enabled: true
  model: yolov8n.pt
  confidence: 0.5
  max_disappeared_frames: 30

zone_crossing:
  enabled: true
  stage_boundary:
    type: rectangle
    left: 0.05
    right: 0.95
    top: 0.0
    bottom: 0.85

person_count_method: yolo_zone
```

### Template 2: Small Venue (More Audience in Frame)
```yaml
yolo_detection:
  enabled: true
  model: yolov8s.pt  # Better accuracy
  confidence: 0.6    # More conservative
  max_disappeared_frames: 20  # Less persistence

zone_crossing:
  enabled: true
  stage_boundary:
    type: rectangle
    left: 0.1
    right: 0.9
    top: 0.05
    bottom: 0.7  # Even tighter boundary

person_count_method: yolo_zone
```

### Template 3: Large Theater (Distant Performers)
```yaml
yolo_detection:
  enabled: true
  model: yolov8m.pt  # Higher accuracy
  confidence: 0.4    # More sensitive
  max_disappeared_frames: 60  # More persistence

zone_crossing:
  enabled: true
  stage_boundary:
    type: rectangle
    left: 0.0
    right: 1.0
    top: 0.0
    bottom: 1.0  # Use entire frame

person_count_method: yolo
```

---

## Tuning Steps

1. **Enable debug mode** to see detections
   ```bash
   python3 clipper_unified.py video.mov -d
   ```

2. **Check debug frames** to see who was detected
   ```
   video_debug_20251121_120000/
   ├── seg01_first_frame...jpg
   ├── seg01_last_frame...jpg
   ...
   ```

3. **Adjust confidence if needed**
   - Too few detections → lower confidence (0.4)
   - Too many false detections → raise confidence (0.6)

4. **Adjust zone boundary if needed**
   - Audience appearing in stage count → lower bottom value (0.75)
   - Missing stage performers → raise bottom value (0.95)

5. **Test and iterate**
   ```bash
   # Try new config
   python3 clipper_unified.py video.mov -c new_config.yaml
   
   # Check results in clips folder
   ```

