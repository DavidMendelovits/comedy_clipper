# Unified Comedy Clipper

A single, configurable script that consolidates all comedy clipping detection methods into one easy-to-use tool.

## Overview

The unified clipper combines all previously separate scripts into a single configurable tool:

- **Speaker Diarization** (from `clipper.py`)
- **Scene Detection** (from `clipper_simple.py` and `clipper_ffmpeg.py`)
- **Pose Detection** (from `clipper_mediapipe.py`)
- **Face Detection** (new)
- **Multi-modal Detection** (from `clipper_advanced.py` and `clipper_configurable.py`)

## Quick Start

```bash
# Use default settings (multimodal detection)
python3 clipper_unified.py video.mp4

# Use scene detection mode
python3 clipper_unified.py video.mp4 --mode scene

# Use speaker diarization
python3 clipper_unified.py video.mp4 --mode diarization

# Enable debug output
python3 clipper_unified.py video.mp4 -d

# Override minimum duration
python3 clipper_unified.py video.mp4 --min-duration 120
```

## Detection Modes

### 1. Multimodal (Default)
**Best for: Standup shows with host introductions**

Combines face and pose detection to count people on stage. Detects transitions when person count changes (e.g., host + comedian → host only).

```bash
python3 clipper_unified.py video.mp4 --mode multimodal
```

Features:
- Face detection using MediaPipe
- Pose detection using MediaPipe
- Kalman filtering for smooth tracking
- Blur detection to avoid cutting on blurry frames
- Configurable transition rules

### 2. Scene Detection
**Best for: Videos with camera cuts between comedians**

Uses FFmpeg's built-in scene detection to identify video cuts.

```bash
python3 clipper_unified.py video.mp4 --mode scene
```

Features:
- Fast and reliable
- No ML dependencies required
- Works well for edited videos
- Configurable sensitivity

### 3. Pose Detection
**Best for: Single comedian tracking stage entry/exit**

Tracks body pose to detect when comedian enters or exits stage.

```bash
python3 clipper_unified.py video.mp4 --mode pose
```

Features:
- Accurate body position tracking
- Entry/exit detection at stage edges
- Stable torso tracking

### 4. Face Detection
**Best for: Close-up shots**

Detects faces to count people on stage.

```bash
python3 clipper_unified.py video.mp4 --mode face
```

### 5. MediaPipe
**Best for: Stage entry/exit with pose landmarks**

Similar to pose mode but with enhanced MediaPipe features.

```bash
python3 clipper_unified.py video.mp4 --mode mediapipe
```

### 6. Diarization
**Best for: Audio-based segmentation by speaker**

Uses AI speaker diarization to identify different speakers.

```bash
# Requires HF_TOKEN environment variable
export HF_TOKEN=your_huggingface_token
python3 clipper_unified.py video.mp4 --mode diarization
```

Requirements:
- HuggingFace account and token
- Accept pyannote terms at https://huggingface.co/pyannote/speaker-diarization-3.1
- Set `HF_TOKEN` environment variable

## Configuration

All detection parameters can be customized via `clipper_rules.yaml`:

```yaml
# Choose detection mode
detection_mode: multimodal  # or: scene, pose, face, mediapipe, diarization

# Scene detection settings
scene_detection:
  threshold: 0.3
  max_gap: 5.0

# Transition rules for multimodal/pose/face modes
transition_detection:
  enabled: true
  rules:
    - from: 2
      to: 1
      action: end_segment
      description: "Comedian exits, host remains"

# Filtering
filtering:
  min_duration: 5.0  # seconds
  max_duration: 0    # 0 = no limit
  merge_close_segments: true
  buffer_before_start: 2.0
  buffer_after_end: 2.0

# Blur detection (for visual modes)
blur_detection:
  enabled: true
  threshold: 100.0

# Output settings
output:
  ffmpeg:
    video_codec: libx264
    audio_codec: aac
    preset: fast
    crf: 23
```

## Command Line Options

```
usage: clipper_unified.py [-h] [--mode {multimodal,pose,face,mediapipe,scene,diarization}]
                          [-c CONFIG] [-o OUTPUT] [-d] [--min-duration MIN_DURATION]
                          video

positional arguments:
  video                 Input video file

optional arguments:
  -h, --help            show this help message and exit
  --mode {multimodal,pose,face,mediapipe,scene,diarization}
                        Detection mode (default: from config or multimodal)
  -c CONFIG, --config CONFIG
                        Config file (default: clipper_rules.yaml)
  -o OUTPUT, --output OUTPUT
                        Output directory for clips
  -d, --debug           Enable debug mode
  --min-duration MIN_DURATION
                        Override minimum duration (seconds)
```

## Installation

### Basic Installation (Scene Detection)

```bash
pip install -r requirements.txt
```

### Visual Detection (Multimodal, Pose, Face)

```bash
pip install mediapipe filterpy opencv-python numpy
```

### Speaker Diarization

```bash
pip install pyannote-audio torch python-dotenv
```

### Complete Installation (All Modes)

```bash
pip install mediapipe filterpy opencv-python numpy pyannote-audio torch python-dotenv
```

## Examples

### Example 1: Standup Show with Host
```bash
# Use multimodal detection to identify when comedian enters/exits with host
python3 clipper_unified.py standup_show.mp4 --mode multimodal -d

# Customize transition rules in clipper_rules.yaml:
# - from: 1, to: 2, action: start_segment  # Host → Host + Comedian
# - from: 2, to: 1, action: end_segment    # Host + Comedian → Host
```

### Example 2: Edited Comedy Special
```bash
# Use scene detection to find camera cuts
python3 clipper_unified.py special.mp4 --mode scene

# Adjust sensitivity in clipper_rules.yaml:
# scene_detection:
#   threshold: 0.4  # Higher = less sensitive
```

### Example 3: Podcast/Interview
```bash
# Use speaker diarization to segment by speaker
export HF_TOKEN=your_token
python3 clipper_unified.py podcast.mp4 --mode diarization --min-duration 60
```

### Example 4: Single Comedian
```bash
# Use pose detection to track stage entry/exit
python3 clipper_unified.py set.mp4 --mode pose
```

## Output

The clipper creates timestamped folders with your clips:

```
video_clips_20231120_143022/
├── video_clip01_5m23s.mp4
├── video_clip02_7m45s.mp4
└── video_clip03_6m12s.mp4
```

With debug mode enabled (`-d`), you also get debug frames:

```
video_debug_20231120_143022/
├── seg01_first_f1234_blur156.jpg
├── seg01_last_f5678_blur142.jpg
├── seg02_first_f6789_blur168.jpg
└── seg02_last_f9012_blur151.jpg
```

Debug frames show:
- Detected faces (bounding boxes)
- Detected poses (skeleton overlay)
- Stage boundaries (red lines)
- Person position (green/red indicator)
- Frame info (face count, pose count, person count)
- Blur score and sharpness

## Configuration Guide

### Transition Rules

Transition rules define how person count changes trigger segment boundaries:

```yaml
transition_detection:
  rules:
    # Format: from → to → action
    - from: 2      # From 2 people
      to: 1        # To 1 person
      action: end_segment
      description: "Comedian exits"
```

Special values:
- `from: any` - Matches any count
- `to: 2+` - Matches 2 or more
- `to: 1-` - Matches 1 or fewer

### Person Count Method

When using multimodal detection, you can choose how to combine face and pose counts:

```yaml
transition_detection:
  person_count_method: max  # Options: min, max, average
```

- `min`: Conservative (both must agree) - good for reducing false positives
- `max`: Liberal (either is enough) - good when MediaPipe Pose only tracks 1 person
- `average`: Middle ground

### Blur Detection

Prevent cutting on blurry/out-of-focus frames:

```yaml
blur_detection:
  enabled: true
  threshold: 100.0  # Lower = more strict
  boundary_shift_max_frames: 30  # Max frames to search for sharp boundary
  boundary_sharpness_min: 150.0  # Minimum sharpness for boundaries
```

The clipper will shift segment boundaries to the nearest sharp frame within the search window.

### Kalman Filter

Smooth out noisy position tracking:

```yaml
kalman_filter:
  enabled: true
  process_noise: 1.0       # Lower = smoother but slower to adapt
  measurement_noise: 5.0   # Lower = trust measurements more
```

### Filtering

Control which segments are kept:

```yaml
filtering:
  min_duration: 5.0        # Minimum segment length (seconds)
  max_duration: 0          # Maximum segment length (0 = no limit)
  min_gap: 5.0             # Merge segments closer than this
  merge_close_segments: true
  buffer_before_start: 2.0 # Add 2s before detected start
  buffer_after_end: 2.0    # Add 2s after detected end
```

## Comparison with Previous Scripts

| Old Script | Unified Equivalent |
|------------|-------------------|
| `clipper.py` | `--mode diarization` |
| `clipper_simple.py` | `--mode scene` |
| `clipper_ffmpeg.py` | `--mode scene` |
| `clipper_mediapipe.py` | `--mode mediapipe` or `--mode pose` |
| `clipper_advanced.py` | `--mode multimodal` |
| `clipper_configurable.py` | Default (with config file) |

## Troubleshooting

### "MediaPipe not installed"
```bash
pip install mediapipe
```

### "filterpy not installed"
```bash
pip install filterpy
```

### "HuggingFace token required" (diarization mode)
```bash
# 1. Get token from https://huggingface.co/settings/tokens
# 2. Accept terms at https://huggingface.co/pyannote/speaker-diarization-3.1
# 3. Set environment variable
export HF_TOKEN=hf_your_token_here
```

### No segments detected
- Try lowering `min_duration` in config or with `--min-duration 30`
- Try different detection mode
- Enable debug mode (`-d`) to see what's being detected
- Adjust transition rules for your specific video format

### Too many false positives
- Increase `transition_stability_frames` in config
- Use `person_count_method: min` for more conservative detection
- Increase `min_duration` to filter out short segments

### Clips cut too close to transitions
- Increase `buffer_before_start` and `buffer_after_end` in config
- Default is 2 seconds before/after

## Performance Tips

1. **Faster processing**: Lower `processing.sample_rate` (check every Nth frame)
2. **Better accuracy**: Lower `processing.sample_rate` (check more frames)
3. **Scene mode**: Fastest, no ML required
4. **Diarization mode**: Slowest but most accurate for audio-based segmentation
5. **GPU acceleration**: Diarization mode will use GPU if available (CUDA)

## License

Same as parent project.

## Credits

Consolidates functionality from:
- `clipper.py` - Speaker diarization
- `clipper_simple.py` - Scene detection
- `clipper_ffmpeg.py` - FFmpeg scene detection
- `clipper_mediapipe.py` - Pose tracking
- `clipper_advanced.py` - Multi-modal detection
- `clipper_configurable.py` - Configurable rules engine
