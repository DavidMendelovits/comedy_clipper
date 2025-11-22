# Quick Start Guide - Unified Comedy Clipper

## Installation

### Option 1: Scene Detection Only (No ML Required)
```bash
# No special dependencies needed, just Python 3 and FFmpeg
python3 clipper_unified.py video.mp4 --mode scene
```

### Option 2: Full Installation (All Modes)
```bash
# Activate the virtual environment (if available)
source venv_mediapipe/bin/activate

# Or install globally
pip install mediapipe opencv-python numpy filterpy pyyaml

# For speaker diarization, also install:
pip install pyannote-audio torch python-dotenv
```

## Basic Usage

### 1. Process with Default Settings
```bash
python3 clipper_unified.py your_video.mp4
```

This will:
- Use multimodal detection (face + pose)
- Detect comedian sets based on person count changes
- Create clips in a timestamped folder
- Use settings from `clipper_rules.yaml`

### 2. Choose a Detection Mode

**Scene Detection** (fastest, no ML):
```bash
python3 clipper_unified.py video.mp4 --mode scene
```

**Multimodal** (best for standup shows):
```bash
python3 clipper_unified.py video.mp4 --mode multimodal
```

**Pose Tracking** (track stage entry/exit):
```bash
python3 clipper_unified.py video.mp4 --mode pose
```

**Speaker Diarization** (audio-based):
```bash
export HF_TOKEN=your_huggingface_token
python3 clipper_unified.py video.mp4 --mode diarization
```

### 3. Common Options

**Set minimum duration** (in seconds):
```bash
python3 clipper_unified.py video.mp4 --min-duration 120
```

**Enable debug output**:
```bash
python3 clipper_unified.py video.mp4 -d
```

**Custom output directory**:
```bash
python3 clipper_unified.py video.mp4 -o /path/to/output
```

**Use custom config**:
```bash
python3 clipper_unified.py video.mp4 -c my_config.yaml
```

## Output

The script creates timestamped folders:

```
your_video_clips_20231120_143022/
├── your_video_clip01_5m23s.mp4
├── your_video_clip02_7m45s.mp4
└── your_video_clip03_6m12s.mp4
```

With debug mode (`-d`):
```
your_video_debug_20231120_143022/
├── seg01_first_f1234_blur156.jpg
├── seg01_last_f5678_blur142.jpg
└── ...
```

## Which Mode Should I Use?

| Your Video Type | Recommended Mode | Why |
|----------------|------------------|-----|
| Standup show with host | `multimodal` | Detects person count changes |
| Edited comedy special | `scene` | Detects camera cuts |
| Single comedian | `pose` or `mediapipe` | Tracks stage entry/exit |
| Podcast/interview | `diarization` | Segments by speaker |
| Static camera, no host | `pose` | Tracks comedian position |

## Quick Troubleshooting

**No segments detected:**
```bash
# Try lowering minimum duration
python3 clipper_unified.py video.mp4 --min-duration 30

# Or try a different mode
python3 clipper_unified.py video.mp4 --mode scene
```

**Dependencies missing:**
```bash
# For visual modes
pip install mediapipe opencv-python numpy filterpy

# For diarization
pip install pyannote-audio torch
```

**Too many/few clips:**
Edit `clipper_rules.yaml`:
```yaml
filtering:
  min_duration: 120.0  # Increase for fewer clips
  merge_close_segments: true  # Merge nearby clips
```

## Examples

### Example 1: Quick Test
```bash
# Fast scene detection, 30 second minimum
python3 clipper_unified.py test.mp4 --mode scene --min-duration 30
```

### Example 2: High Quality Standup
```bash
# Multimodal with debug output
python3 clipper_unified.py show.mp4 --mode multimodal -d
```

### Example 3: Batch Process
```bash
# Process multiple videos
for video in *.mp4; do
    python3 clipper_unified.py "$video" --mode scene
done
```

## Configuration

Edit `clipper_rules.yaml` to customize:

```yaml
# Set default mode
detection_mode: multimodal

# Adjust minimum duration
filtering:
  min_duration: 120.0

# Fine-tune detection
transition_detection:
  person_count_method: max  # max, min, or average

# Adjust blur detection
blur_detection:
  enabled: true
  threshold: 100.0
```

## Next Steps

- Read `README_UNIFIED.md` for detailed documentation
- Check `MIGRATION.md` if upgrading from old scripts
- Review `clipper_rules.yaml` for all configuration options
- Try different modes to find what works best for your videos

## Getting Help

```bash
# Show help
python3 clipper_unified.py --help

# Show config options
cat clipper_rules.yaml

# Test with debug mode
python3 clipper_unified.py video.mp4 -d
```

## Common Workflows

### Workflow 1: Fast Preview
```bash
# Quick scene detection to see what you get
python3 clipper_unified.py video.mp4 --mode scene --min-duration 30
```

### Workflow 2: High Quality
```bash
# Multimodal with debug, review results, tune config, reprocess
python3 clipper_unified.py video.mp4 --mode multimodal -d
# Review debug frames and clips
# Edit clipper_rules.yaml based on results
python3 clipper_unified.py video.mp4 --mode multimodal
```

### Workflow 3: Production
```bash
# Once you find settings that work, batch process
for video in videos/*.mp4; do
    python3 clipper_unified.py "$video" -c production_config.yaml
done
```

That's it! You're ready to start clipping comedy videos.
