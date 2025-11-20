# Comedy Clipper - Rules Configuration Guide

Complete guide to configuring detection rules for the comedy clipper.

## Quick Start

The configurable clipper uses `clipper_rules.yaml` to define all detection behavior:

```bash
# Run with default rules
python3 clipper_configurable.py test_vid.MOV -d

# Run with custom rules
python3 clipper_configurable.py test_vid.MOV -c my_custom_rules.yaml -d
```

---

## 🎯 Understanding the Rule System

The clipper uses a **multi-tier detection system**:

1. **Transition-Based Detection** (Primary) - Detects when person count changes
2. **Position-Based Detection** (Fallback) - Detects when person exits stage edges
3. **Kalman Filtering** - Smooths tracking to prevent flaky detection
4. **Segment Filtering** - Post-processes segments by duration, gaps, etc.

---

## 📋 Rule Types

### 1. Transition Rules

Transition rules detect segments based on changes in person count.

**Format:**
```yaml
transition_detection:
  rules:
    - from: <count>
      to: <count>
      action: <start_segment|end_segment>
      description: "What this rule does"
```

**Count Values:**
- `0` - Nobody on stage
- `1` - One person on stage
- `2` - Two people on stage
- `2+` - Two or more people (any count >= 2)
- `1-` - One or fewer people (any count <= 1)
- `any` - Any count (wildcard)

**Actions:**
- `start_segment` - Begin a new comedian set
- `end_segment` - End the current set

**Example Rules:**

```yaml
# Host + comedian → host only (comedian exits)
- from: 2
  to: 1
  action: end_segment
  description: "Comedian exits, host remains"

# Empty stage → person appears (comedian enters alone)
- from: 0
  to: 1
  action: start_segment
  description: "Comedian enters empty stage"

# Person on stage → empty stage (comedian exits completely)
- from: 1
  to: 0
  action: end_segment
  description: "Comedian exits, stage empty"

# Any count → 2+ people (flexible start)
- from: any
  to: 2+
  action: start_segment
  description: "Multiple people appear"
```

### 2. Person Count Method

How to combine face and pose detections into a person count:

```yaml
transition_detection:
  person_count_method: max  # or "min" or "average"
```

**IMPORTANT**: MediaPipe Pose only tracks **1 person at a time**, so `num_poses` will be 0 or 1, never 2+.

- **`max`** (recommended) - Trusts face detection for multi-person scenarios
  - Example: 2 faces + 1 pose = 2 person count ✓ (Correct for 2 people on stage)
  - Use when detecting 2→1 or 1→2 transitions
- **`min`** - Conservative, requires both detectors to agree
  - Example: 2 faces + 1 pose = 1 person count ❌ (Fails to detect 2 people!)
  - Only use for single-person scenarios (0→1, 1→0)
- **`average`** - Middle ground
  - Example: 2 faces + 1 pose = 1.5 → 1 person count ❌ (Also fails!)

### 3. Transition Stability

Prevents flickering by requiring count to be stable for N frames:

```yaml
transition_detection:
  transition_stability_frames: 3  # Require 3 consecutive frames
```

Higher = more stable, but slower to detect transitions.

---

## 🎯 Common Use Cases

### Use Case 1: Host + Comedian Format

**Scenario:** Show has a host who introduces each comedian. Comedian enters (2 people), performs, then exits (1 person remains).

**Rules:**
```yaml
transition_detection:
  enabled: true
  rules:
    - from: 1
      to: 2
      action: start_segment
      description: "Comedian joins host"

    - from: 2
      to: 1
      action: end_segment
      description: "Comedian exits, host remains"

  person_count_method: min
  transition_stability_frames: 3
```

### Use Case 2: Solo Performers

**Scenario:** No host. Comedians walk on stage alone, perform, and exit.

**Rules:**
```yaml
transition_detection:
  enabled: true
  rules:
    - from: 0
      to: 1
      action: start_segment
      description: "Comedian enters empty stage"

    - from: 1
      to: 0
      action: end_segment
      description: "Comedian exits, stage empty"

  person_count_method: min
  transition_stability_frames: 3
```

### Use Case 3: Position-Based Only

**Scenario:** Ignore person count, only detect when someone exits stage left/right.

**Rules:**
```yaml
transition_detection:
  enabled: false  # Disable transition detection

position_detection:
  enabled: true
  exit_threshold: 0.15  # Person within 15% of frame edge = exiting
  exit_stability_frames: 2
  tracking_point: torso  # or "center"
```

### Use Case 4: Hybrid Approach

**Scenario:** Try transitions first, fall back to position if nothing found.

**Rules:**
```yaml
transition_detection:
  enabled: true
  rules: [... your transition rules ...]

position_detection:
  enabled: true  # Will activate if no transitions found
  exit_threshold: 0.15
```

---

## 🔧 Fine-Tuning Parameters

### Kalman Filter (Smoothing)

Eliminates jittery tracking and fills in missing detections:

```yaml
kalman_filter:
  enabled: true

  # Lower = smoother, slower to adapt
  process_noise: 1.0

  # Lower = trust measurements more
  measurement_noise: 5.0

  # Initial uncertainty
  initial_covariance: 10.0
```

**When to adjust:**
- Camera shake → Increase `measurement_noise`
- Fast movement → Increase `process_noise`
- Too smooth/laggy → Decrease both

### Detection Confidence

Control how sensitive the detectors are:

```yaml
confidence:
  face_detection:
    min_detection_confidence: 0.5  # 0.0 (liberal) to 1.0 (strict)
    model_selection: 1  # 0=short range (<2m), 1=full range (>2m)

  pose_detection:
    min_detection_confidence: 0.5
    min_tracking_confidence: 0.5
    model_complexity: 1  # 0=lite, 1=full, 2=heavy
    smooth_landmarks: true
```

**When to adjust:**
- Too many false positives → Increase confidence thresholds
- Missing detections → Decrease confidence thresholds
- Slow performance → Use lower `model_complexity`

### Segment Filtering

Post-process detected segments:

```yaml
filtering:
  # Only keep segments longer than this
  min_duration: 180.0  # seconds (3 minutes)

  # Reject segments longer than this (0 = no limit)
  max_duration: 0

  # Merge segments with gaps smaller than this
  min_gap: 5.0  # seconds

  # Auto-merge close segments
  merge_close_segments: true
```

**Examples:**
- Comedy sets typically 3-10 minutes → `min_duration: 180`, `max_duration: 600`
- Quick transitions → `min_gap: 3.0`
- Long applause breaks → `min_gap: 10.0`

### Processing Speed

Control frame sampling rate:

```yaml
processing:
  # Process 1 frame every N frames
  # Higher = faster, but less accurate
  sample_rate: 30  # At 30fps, this = 1 frame per second

  # Slow down during transitions for accuracy
  adaptive_sampling: true
  adaptive_rate_on_change: 15  # 2 frames per second during changes
```

**Recommendations:**
- `sample_rate: 30` (1 fps) - Good balance
- `sample_rate: 15` (2 fps) - More accurate, slower
- `sample_rate: 60` (0.5 fps) - Fast preview

---

## 🎨 Debug Visualization

Control what appears in debug frame overlays:

```yaml
debug:
  export_frames: true
  export_first_frame: true
  export_last_frame: true
  export_transition_frames: false  # Export frames where count changes

  overlays:
    draw_pose_landmarks: true    # Green skeleton
    draw_face_boxes: true        # Blue bounding boxes
    draw_stage_boundaries: true  # Red edge lines
    draw_position_indicator: true # Vertical line at person position
    draw_text_info: true         # Text overlay

  text_info:
    - frame_number
    - num_faces
    - num_poses
    - person_count
    - confidence_score
    - position
    - status
```

---

## 🎬 Output Configuration

Customize output folders and video encoding:

```yaml
output:
  use_timestamps: true
  clips_folder_suffix: "clips"       # video_clips_20251119_123456
  debug_folder_suffix: "debug"       # video_debug_20251119_123456

  ffmpeg:
    video_codec: libx264
    audio_codec: aac
    preset: fast  # ultrafast, fast, medium, slow, veryslow
    crf: 23       # Quality: 18 (best) to 28 (worst)
```

**Preset trade-offs:**
- `ultrafast` - Fastest, largest files
- `fast` - Good balance (recommended)
- `slow` - Better compression, slower
- `veryslow` - Best compression, very slow

**CRF (Constant Rate Factor):**
- `18` - Visually lossless, large files
- `23` - Good quality (recommended)
- `28` - Lower quality, smaller files

---

## 📊 Real-World Examples

### Example 1: Netflix Comedy Special

```yaml
transition_detection:
  enabled: false  # Usually single performer

position_detection:
  enabled: true
  exit_threshold: 0.12  # Tight framing
  tracking_point: torso

filtering:
  min_duration: 300.0  # 5 min minimum
  max_duration: 1200.0  # 20 min maximum
  merge_close_segments: false  # Don't merge different bits

processing:
  sample_rate: 15  # Higher accuracy for professional content
```

### Example 2: Open Mic Night

```yaml
transition_detection:
  enabled: true
  rules:
    - {from: 1, to: 2, action: start_segment}
    - {from: 2, to: 1, action: end_segment}
    - {from: 0, to: 1, action: start_segment}  # Sometimes host leaves
    - {from: 1, to: 0, action: end_segment}

filtering:
  min_duration: 120.0  # 2 min (shorter sets)
  max_duration: 420.0  # 7 min (open mic limit)
  merge_close_segments: true
  min_gap: 8.0  # Allow for applause

processing:
  sample_rate: 30  # Faster processing for long shows
```

### Example 3: Late Night Show

```yaml
transition_detection:
  enabled: true
  rules:
    - {from: 1, to: 2, action: start_segment, description: "Guest joins host"}
    - {from: 2, to: 1, action: end_segment, description: "Guest exits"}
    - {from: 2, to: any, action: end_segment, description: "Scene change"}

filtering:
  min_duration: 180.0
  max_duration: 900.0  # 15 min interview limit
  merge_close_segments: false  # Keep segments separate

confidence:
  face_detection:
    min_detection_confidence: 0.6  # Higher for TV quality
  pose_detection:
    min_detection_confidence: 0.6
```

---

## 🚀 Testing Your Rules

1. **Start with defaults**: Run with `clipper_rules.yaml`
2. **Enable debug**: Use `-d` flag to see what's detected
3. **Review debug frames**: Check first/last frames of each segment
4. **Adjust incrementally**: Change one parameter at a time
5. **Test on subset**: Use short test clips first

**Iteration process:**
```bash
# Test with debug
python3 clipper_configurable.py test.mp4 -d

# Review debug frames in test_debug_<timestamp>/
# Adjust rules in clipper_rules.yaml
# Test again
```

---

## 📚 Configuration Reference

Complete parameter listing with defaults:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `transition_detection.enabled` | bool | true | Enable transition-based detection |
| `transition_detection.transition_stability_frames` | int | 3 | Frames before triggering |
| `transition_detection.person_count_method` | string | "min" | How to count people |
| `position_detection.enabled` | bool | true | Enable position fallback |
| `position_detection.exit_threshold` | float | 0.15 | Edge zone size (0-0.5) |
| `kalman_filter.enabled` | bool | true | Enable smoothing |
| `filtering.min_duration` | float | 180.0 | Min segment length (sec) |
| `filtering.merge_close_segments` | bool | true | Auto-merge close segments |
| `processing.sample_rate` | int | 30 | Frame sampling interval |
| `debug.export_frames` | bool | true | Export debug images |

---

## 🎓 Tips & Best Practices

1. **Start conservative**: Use `person_count_method: min` and higher confidence thresholds
2. **Use stability**: Set `transition_stability_frames: 3` to avoid flicker
3. **Test on variety**: Try different lighting, camera angles, stage setups
4. **Monitor logs**: Watch console output for transition events
5. **Check debug frames**: Visual confirmation is crucial
6. **Version your configs**: Save different configs for different show types
7. **Document changes**: Add descriptions to your rules

---

## ❓ Troubleshooting

**Problem:** No segments detected
- Solution: Lower `min_duration`, check `transition_stability_frames`
- Enable position fallback if disabled

**Problem:** Too many short segments
- Solution: Increase `min_duration` and `min_gap`
- Enable `merge_close_segments`

**Problem:** Missing transitions
- Solution: Lower confidence thresholds
- Decrease `transition_stability_frames`
- Check `person_count_method` (try "max" instead of "min")

**Problem:** False transitions during applause
- Solution: Increase `transition_stability_frames`
- Use higher confidence thresholds

**Problem:** Slow processing
- Solution: Increase `sample_rate`
- Use lower `model_complexity`
- Disable Kalman filter for testing

---

## 🔬 Experimental Features

```yaml
experimental:
  motion_based_segmentation: false  # Not yet implemented
  audio_based_segmentation: false   # Not yet implemented
  multi_person_tracking: false      # Requires different pose model
```

These features are placeholders for future development.

---

## 📞 Support

For issues or questions:
- Check debug frames first
- Review console logs for transition events
- Try default config as baseline
- Adjust one parameter at a time

Happy clipping! 🎭
