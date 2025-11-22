# Script Consolidation Summary

## Overview

All comedy clipper scripts have been consolidated into a single, configurable tool: **`clipper_unified.py`**

## What Changed

### Before: 7 Separate Scripts
1. `clipper.py` - Speaker diarization
2. `clipper_simple.py` - Scene detection with MoviePy
3. `clipper_ffmpeg.py` - Pure FFmpeg scene detection
4. `clipper_mediapipe.py` - MediaPipe pose tracking
5. `clipper_advanced.py` - Face + pose multi-modal
6. `clipper_configurable.py` - Fully configurable with YAML
7. `config_loader.py` - Config loading utility

### After: 1 Unified Script
- **`clipper_unified.py`** - All detection methods in one script
- **`clipper_rules.yaml`** - Unified configuration file
- **`config_loader.py`** - Config loading utility (unchanged)

## New Features

### 1. Mode Selection
Choose detection method via command line or config:

```bash
# Command line
python3 clipper_unified.py video.mp4 --mode multimodal
python3 clipper_unified.py video.mp4 --mode scene
python3 clipper_unified.py video.mp4 --mode diarization

# Or in clipper_rules.yaml
detection_mode: multimodal
```

### 2. All Detection Methods in One Place
- **Multimodal**: Face + pose detection (best for standup)
- **Pose**: Pose-only tracking
- **Face**: Face-only detection
- **MediaPipe**: Enhanced pose tracking
- **Scene**: FFmpeg scene detection
- **Diarization**: Speaker-based segmentation

### 3. Unified Configuration
Single `clipper_rules.yaml` file controls all modes:

```yaml
detection_mode: multimodal

scene_detection:
  threshold: 0.3
  max_gap: 5.0

transition_detection:
  enabled: true
  person_count_method: max
  rules:
    - from: 2
      to: 1
      action: end_segment

blur_detection:
  enabled: true
  threshold: 100.0

filtering:
  min_duration: 5.0
  buffer_before_start: 2.0
  buffer_after_end: 2.0
```

### 4. Smart Defaults
The unified script auto-detects mode from config and uses sensible defaults for all parameters.

### 5. Optional Dependencies
Only imports what you need:
- Scene mode: No ML dependencies required
- Visual modes: Requires MediaPipe
- Diarization: Requires pyannote-audio

## Migration Guide

### Old Usage → New Usage

**Scene Detection:**
```bash
# Old
python3 clipper_ffmpeg.py video.mp4

# New
python3 clipper_unified.py video.mp4 --mode scene
```

**Pose Detection:**
```bash
# Old
python3 clipper_mediapipe.py video.mp4

# New
python3 clipper_unified.py video.mp4 --mode pose
```

**Multi-modal Detection:**
```bash
# Old
python3 clipper_advanced.py video.mp4 -d

# New
python3 clipper_unified.py video.mp4 --mode multimodal -d
```

**Configurable Detection:**
```bash
# Old
python3 clipper_configurable.py video.mp4 -c my_rules.yaml

# New
python3 clipper_unified.py video.mp4 -c my_rules.yaml
```

**Speaker Diarization:**
```bash
# Old
python3 clipper.py video.mp4 --hf-token TOKEN

# New (uses environment variable)
export HF_TOKEN=your_token
python3 clipper_unified.py video.mp4 --mode diarization
```

## Benefits

### 1. Easier to Use
- One script to learn instead of 7
- Consistent command-line interface
- Easy mode switching without changing scripts

### 2. Easier to Maintain
- All code in one place
- Shared utilities and functions
- Single configuration system

### 3. More Flexible
- Mix and match detection modes
- Override config via command line
- Easy experimentation

### 4. Better Documentation
- Single comprehensive README
- All examples in one place
- Clearer mode comparisons

## File Structure

```
comedy_clipper/
├── clipper_unified.py          # ← NEW: Unified script
├── clipper_rules.yaml          # ← UPDATED: Unified config
├── config_loader.py            # Unchanged
├── README_UNIFIED.md           # ← NEW: Comprehensive docs
│
├── clipper.py                  # OLD: Can be deprecated
├── clipper_simple.py           # OLD: Can be deprecated
├── clipper_ffmpeg.py           # OLD: Can be deprecated
├── clipper_mediapipe.py        # OLD: Can be deprecated
├── clipper_advanced.py         # OLD: Can be deprecated
└── clipper_configurable.py     # OLD: Can be deprecated
```

## Backwards Compatibility

All old scripts still work! The unified script is an addition, not a replacement (yet).

You can continue using old scripts if needed, or gradually migrate to `clipper_unified.py`.

## Recommended Next Steps

1. **Try the unified script:**
   ```bash
   python3 clipper_unified.py test_video.mp4
   ```

2. **Read the documentation:**
   ```bash
   cat README_UNIFIED.md
   ```

3. **Experiment with modes:**
   ```bash
   python3 clipper_unified.py video.mp4 --mode scene
   python3 clipper_unified.py video.mp4 --mode multimodal -d
   ```

4. **Customize configuration:**
   Edit `clipper_rules.yaml` to tune detection parameters

5. **Deprecate old scripts:**
   Once comfortable with unified script, consider removing old scripts

## Technical Details

### Architecture

The unified script uses a class-based design:

```python
class UnifiedComedyClipper:
    def __init__(self, config, mode, debug):
        # Initialize based on mode
        self._init_detectors()

    def detect_segments(self, video_path):
        # Route to appropriate detection method
        if self.mode == "scene":
            return self._detect_scenes_ffmpeg()
        elif self.mode == "diarization":
            return self._detect_diarization()
        else:
            return self._detect_visual()

    def process_video(self, video_path, output_dir):
        # Unified pipeline
        segments = self.detect_segments(video_path)
        filtered = self.filter_segments(segments)
        self.clip_video(video_path, filtered, output_dir)
```

### Configuration System

The config loader (`config_loader.py`) handles:
- YAML file parsing
- Transition rule matching
- Dot-notation path access
- Default values

### Detection Routing

The script intelligently routes to the appropriate detection method:

1. **Scene mode**: Pure FFmpeg subprocess
2. **Diarization mode**: Audio extraction + pyannote pipeline
3. **Visual modes**: OpenCV + MediaPipe processing

### Shared Components

All modes share:
- Segment filtering logic
- FFmpeg clipping
- Debug frame export
- Blur detection (visual modes)
- Kalman filtering (visual modes)

## Performance Comparison

| Mode | Speed | Accuracy | Dependencies |
|------|-------|----------|--------------|
| Scene | ★★★★★ | ★★★ | FFmpeg only |
| Pose | ★★★ | ★★★★ | MediaPipe |
| Face | ★★★ | ★★★ | MediaPipe |
| Multimodal | ★★ | ★★★★★ | MediaPipe |
| Diarization | ★ | ★★★★★ | pyannote-audio |

## Known Limitations

1. **MediaPipe Pose** only tracks one person at a time (use face detection for multiple)
2. **Diarization** requires GPU for reasonable speed
3. **Scene detection** doesn't work well for static camera shows
4. **Blur detection** adds overhead but improves clip quality

## Future Enhancements

Potential additions:
- Audio-based segmentation (applause/laughter detection)
- Motion-based segmentation
- Multi-person pose tracking
- Hybrid detection (combine multiple modes)
- Real-time processing
- GUI interface

## Support

For issues or questions:
1. Check `README_UNIFIED.md` for detailed documentation
2. Review `clipper_rules.yaml` for configuration options
3. Try different detection modes
4. Enable debug mode (`-d`) to see what's detected

## Conclusion

The unified clipper provides:
- ✅ All detection methods in one script
- ✅ Consistent interface
- ✅ Flexible configuration
- ✅ Comprehensive documentation
- ✅ Easier maintenance
- ✅ Better user experience

Old scripts remain functional but the unified script is now the recommended approach.
