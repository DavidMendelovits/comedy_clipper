# Comedy Clipper - One Page Cheat Sheet

## 🎯 MOST COMMON USE: Clip When People Exit Stage

```bash
venv_mediapipe/bin/python clipper_unified.py your_video.mp4 --mode mediapipe
```

**Default settings:** 10 second buffer before/after, 5 second minimum clip length

---

## 📋 All Detection Modes

| Command | What It Does |
|---------|--------------|
| `--mode mediapipe` | Clips when people exit/enter stage (position-based) |
| `--mode multimodal` | Clips when person count changes (e.g., 2→1 people) |
| `--mode scene` | Clips on camera cuts (fastest, no AI) |

---

## ⚙️ Common Options

```bash
# Set minimum clip length (seconds)
--min-duration 60

# Enable debug mode (see detection frames)
-d

# Custom output folder
-o /path/to/output

# Use custom config
-c my_config.yaml
```

---

## 📝 Config File Quick Edits

**File:** `clipper_rules.yaml`

### Change Buffer Time
```yaml
filtering:
  buffer_before_start: 10.0  # Seconds before exit
  buffer_after_end: 10.0     # Seconds after exit
```

### Change Minimum Clip Length
```yaml
filtering:
  min_duration: 30.0  # Only keep clips 30+ seconds
```

### Change Default Mode
```yaml
detection_mode: mediapipe  # or: multimodal, scene
```

---

## 🚀 Complete Examples

### Basic: Stage exit detection
```bash
venv_mediapipe/bin/python clipper_unified.py show.mp4 --mode mediapipe
```

### With 2-minute minimum
```bash
venv_mediapipe/bin/python clipper_unified.py show.mp4 --mode mediapipe --min-duration 120
```

### With debug output
```bash
venv_mediapipe/bin/python clipper_unified.py show.mp4 --mode mediapipe -d
```

### Scene detection (fastest)
```bash
venv_mediapipe/bin/python clipper_unified.py show.mp4 --mode scene --min-duration 30
```

---

## 📂 Output

Creates timestamped folders:

```
your_video_clips_mediapipe_20231120_143022/
├── your_video_clip01_5m23s.mp4
├── your_video_clip02_7m45s.mp4
└── your_video_clip03_6m12s.mp4
```

With `-d` flag, also creates debug folder with detection images.

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| No clips created | Try `--min-duration 10` or `--mode scene` |
| Too many clips | Increase `--min-duration 120` |
| Clips too short | Edit `buffer_before_start` and `buffer_after_end` in config |
| Clips cut off early | Increase buffer times in config |

---

## 📚 More Help

- **Simple guide:** `SIMPLE_GUIDE.md`
- **Full documentation:** `README_UNIFIED.md`
- **Migration from old scripts:** `MIGRATION.md`
- **Quick start:** `QUICKSTART.md`

---

## 💡 Pro Tips

1. **Start with debug mode** (`-d`) to see what's detected
2. **Use scene mode** for quick tests on edited videos
3. **Adjust buffer times** in config if clips are cut off
4. **Lower min_duration** to see all detected segments first
5. **Check debug images** to understand why clips were/weren't created
