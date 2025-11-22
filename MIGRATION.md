# Migration Guide: Old Scripts → Unified Clipper

Quick reference for migrating from old scripts to `clipper_unified.py`

## Quick Migration Table

| Old Command | New Command |
|-------------|-------------|
| `python3 clipper.py video.mp4` | `python3 clipper_unified.py video.mp4 --mode diarization` |
| `python3 clipper_simple.py video.mp4` | `python3 clipper_unified.py video.mp4 --mode scene` |
| `python3 clipper_ffmpeg.py video.mp4` | `python3 clipper_unified.py video.mp4 --mode scene` |
| `python3 clipper_mediapipe.py video.mp4` | `python3 clipper_unified.py video.mp4 --mode mediapipe` |
| `python3 clipper_advanced.py video.mp4` | `python3 clipper_unified.py video.mp4 --mode multimodal` |
| `python3 clipper_configurable.py video.mp4` | `python3 clipper_unified.py video.mp4` |

## Detailed Migrations

### clipper.py (Speaker Diarization)

**Before:**
```bash
python3 clipper.py standup_show.mp4 \
  --hf-token YOUR_TOKEN \
  --min-duration 180 \
  --keep-audio
```

**After:**
```bash
export HF_TOKEN=YOUR_TOKEN
python3 clipper_unified.py standup_show.mp4 \
  --mode diarization \
  --min-duration 180
```

**Config:**
```yaml
detection_mode: diarization
filtering:
  min_duration: 180.0
```

### clipper_simple.py / clipper_ffmpeg.py (Scene Detection)

**Before:**
```bash
python3 clipper_ffmpeg.py show.mp4 \
  --threshold 0.4 \
  --min-duration 60 \
  --max-gap 10
```

**After:**
```bash
python3 clipper_unified.py show.mp4 \
  --mode scene \
  --min-duration 60
```

**Config:**
```yaml
detection_mode: scene
scene_detection:
  threshold: 0.4
  max_gap: 10.0
filtering:
  min_duration: 60.0
```

### clipper_mediapipe.py (Pose Detection)

**Before:**
```bash
python3 clipper_mediapipe.py show.mp4 \
  --exit-threshold 0.15 \
  --min-duration 180 \
  --debug
```

**After:**
```bash
python3 clipper_unified.py show.mp4 \
  --mode mediapipe \
  --min-duration 180 \
  --debug
```

**Config:**
```yaml
detection_mode: mediapipe
position_detection:
  exit_threshold: 0.15
filtering:
  min_duration: 180.0
debug:
  export_frames: true
```

### clipper_advanced.py (Multi-modal)

**Before:**
```bash
python3 clipper_advanced.py show.mp4 \
  --exit-threshold 0.15 \
  --min-duration 180 \
  --debug
```

**After:**
```bash
python3 clipper_unified.py show.mp4 \
  --mode multimodal \
  --min-duration 180 \
  --debug
```

**Config:**
```yaml
detection_mode: multimodal
position_detection:
  exit_threshold: 0.15
filtering:
  min_duration: 180.0
debug:
  export_frames: true
```

### clipper_configurable.py (Rule-based)

**Before:**
```bash
python3 clipper_configurable.py test_vid.MOV \
  -c my_rules.yaml \
  -d
```

**After:**
```bash
python3 clipper_unified.py test_vid.MOV \
  -c my_rules.yaml \
  -d
```

This is the most direct migration - the unified script uses the same config format!

## Parameter Mapping

### Common Parameters

| Old Parameter | New Parameter | Notes |
|---------------|---------------|-------|
| `--hf-token` | `HF_TOKEN` env var | Now uses environment variable |
| `--min-duration` | `--min-duration` | Same |
| `--output` / `-o` | `--output` / `-o` | Same |
| `--debug` / `-d` | `--debug` / `-d` | Same |
| `--config` / `-c` | `--config` / `-c` | Same |

### Mode-Specific Parameters

| Old Script | Old Parameter | New Config Path |
|------------|---------------|-----------------|
| clipper_ffmpeg.py | `--threshold` | `scene_detection.threshold` |
| clipper_ffmpeg.py | `--max-gap` | `scene_detection.max_gap` |
| clipper_mediapipe.py | `--exit-threshold` | `position_detection.exit_threshold` |
| clipper.py | `--keep-audio` | N/A (temp files always cleaned) |

## Config File Migration

If you have custom config files, they should work as-is! Just add the mode selection:

```yaml
# Add this line at the top
detection_mode: multimodal

# Rest of your config remains the same
transition_detection:
  enabled: true
  rules:
    # your rules...

# etc...
```

## Environment Variables

### Before (clipper.py)
```bash
export HF_TOKEN=your_token
# OR
export HUGGING_FACE_TOKEN=your_token
```

### After (clipper_unified.py)
```bash
export HF_TOKEN=your_token
# OR
export HUGGING_FACE_TOKEN=your_token
```

Same! No change needed.

## Testing Your Migration

1. **Test with simple command:**
   ```bash
   python3 clipper_unified.py your_video.mp4
   ```

2. **Verify mode selection:**
   ```bash
   python3 clipper_unified.py your_video.mp4 --mode scene
   ```

3. **Test with your old config:**
   ```bash
   python3 clipper_unified.py your_video.mp4 -c your_old_config.yaml
   ```

4. **Enable debug to see what's happening:**
   ```bash
   python3 clipper_unified.py your_video.mp4 -d
   ```

## Common Migration Issues

### Issue: "MediaPipe not installed"
**Solution:** Install MediaPipe for visual modes
```bash
pip install mediapipe filterpy
```

### Issue: "HuggingFace token required"
**Solution:** Set environment variable
```bash
export HF_TOKEN=your_token
```

### Issue: "No segments detected"
**Solution:** Try different mode or lower min_duration
```bash
python3 clipper_unified.py video.mp4 --mode scene --min-duration 30
```

### Issue: Mode not detected from config
**Solution:** Explicitly specify mode
```bash
python3 clipper_unified.py video.mp4 --mode multimodal
```

## Rollback Plan

If you need to rollback to old scripts:

1. **Old scripts still work** - nothing was deleted
2. **Keep your old configs** - they still work with old scripts
3. **No data loss** - unified script creates new output folders

Simply continue using old scripts until ready to switch.

## Benefits Checklist

After migrating, you get:

- ✅ Single script to maintain
- ✅ Easy mode switching
- ✅ Consistent interface
- ✅ Better documentation
- ✅ More flexible configuration
- ✅ Shared improvements across all modes

## Need Help?

1. Read `README_UNIFIED.md` for detailed documentation
2. Check `CONSOLIDATION_SUMMARY.md` for technical details
3. Review `clipper_rules.yaml` for all configuration options
4. Try `python3 clipper_unified.py --help`

## Recommended Migration Path

1. **Week 1:** Try unified script alongside old scripts
2. **Week 2:** Update your workflows to use unified script
3. **Week 3:** Migrate any custom configs
4. **Week 4:** Fully switch to unified script
5. **Week 5+:** Consider deprecating old scripts

Take your time - there's no rush! Both systems work.
