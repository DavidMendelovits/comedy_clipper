# 👋 Start Here - Comedy Clipper

## What You Want: Clip When Comedians Exit Stage (10 Second Buffer)

### Quick Start (30 Seconds)

```bash
venv_mediapipe/bin/python clipper_unified.py your_video.mp4 --mode mediapipe
```

That's it! Your clips will be in a new folder: `your_video_clips_mediapipe_TIMESTAMP/`

**Default settings:**
- ✅ 10 second buffer before exit
- ✅ 10 second buffer after exit
- ✅ 5 second minimum clip length
- ✅ Detects when people walk off stage

---

## Want to Change Settings?

### Change Buffer Time

Edit `clipper_rules.yaml` (line 188-189):
```yaml
buffer_before_start: 10.0  # Change this number
buffer_after_end: 10.0     # Change this number
```

### Change Minimum Clip Length

```bash
venv_mediapipe/bin/python clipper_unified.py video.mp4 --mode mediapipe --min-duration 60
```

### See What's Being Detected

```bash
venv_mediapipe/bin/python clipper_unified.py video.mp4 --mode mediapipe -d
```

This creates debug images showing where people are detected.

---

## Documentation

Pick your learning style:

- **`CHEATSHEET.md`** - One page with all commands (1 min read)
- **`SIMPLE_GUIDE.md`** - Step-by-step guide with examples (5 min read)
- **`QUICKSTART.md`** - Quick start for all modes (10 min read)
- **`README_UNIFIED.md`** - Complete documentation (30 min read)

---

## Different Video Types?

| Your Video | Use This Mode |
|------------|---------------|
| Single comedian exits stage | `--mode mediapipe` ⭐ |
| Show with host + comedians | `--mode multimodal` |
| Edited video with cuts | `--mode scene` |

---

## Need Help?

1. Read `CHEATSHEET.md` for quick commands
2. Read `SIMPLE_GUIDE.md` for step-by-step help
3. Enable debug mode (`-d`) to see what's detected
4. Try `--mode scene` as a quick test

---

## Example: Full Workflow

```bash
# 1. Test with debug to see what's detected
venv_mediapipe/bin/python clipper_unified.py show.mp4 --mode mediapipe -d --min-duration 10

# 2. Check the debug images in show_debug_mediapipe_TIMESTAMP/

# 3. Adjust settings if needed in clipper_rules.yaml

# 4. Run final version
venv_mediapipe/bin/python clipper_unified.py show.mp4 --mode mediapipe
```

Done! 🎉
