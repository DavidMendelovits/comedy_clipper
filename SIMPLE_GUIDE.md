# Simple Guide - Comedy Clipper

## What Do You Want To Do?

### 1. Clip When Comedians Exit Stage (Most Common)

**This detects when a person walks off stage and creates clips of their entire set.**

```bash
# Run this command:
venv_mediapipe/bin/python clipper_unified.py your_video.mp4 --mode mediapipe
```

**What it does:**
- Tracks when people enter and exit the stage (stage left/right)
- Creates a clip for each comedian's full set
- Adds 2 second buffer before/after (configurable)

**To change the buffer time:**

Edit `clipper_rules.yaml` and change these lines:
```yaml
filtering:
  buffer_before_start: 2.0  # Change to 10.0 for 10 seconds before
  buffer_after_end: 2.0     # Change to 10.0 for 10 seconds after
```

Then run:
```bash
venv_mediapipe/bin/python clipper_unified.py your_video.mp4 --mode mediapipe
```

---

### 2. Clip When Person Count Changes (For Shows With Host)

**This detects when the number of people on stage changes (e.g., host + comedian → host only).**

```bash
venv_mediapipe/bin/python clipper_unified.py your_video.mp4 --mode multimodal
```

**What it does:**
- Detects faces and body poses
- Counts how many people are on stage
- Creates clips when count changes (2 people → 1 person = comedian left)

---

### 3. Clip On Camera Cuts (Fastest)

**For edited videos with cuts between comedians.**

```bash
venv_mediapipe/bin/python clipper_unified.py your_video.mp4 --mode scene
```

**What it does:**
- Detects when the camera cuts/changes
- Groups cuts into segments
- Very fast, no AI needed

---

## Quick Setup for Stage Exit Mode (10 Second Buffer)

### Step 1: Edit the config file

Open `clipper_rules.yaml` and find this section (around line 160):

```yaml
filtering:
  min_duration: 5.0  # Minimum clip length in seconds

  # Time buffer (seconds) to add before/after detected transitions
  buffer_before_start: 2.0  # ← Change this to 10.0
  buffer_after_end: 2.0     # ← Change this to 10.0
```

Change it to:
```yaml
filtering:
  min_duration: 5.0

  # Time buffer (seconds) to add before/after detected transitions
  buffer_before_start: 10.0  # Start clip 10s before comedian exits
  buffer_after_end: 10.0     # End clip 10s after comedian exits
```

### Step 2: Run the clipper

```bash
venv_mediapipe/bin/python clipper_unified.py your_video.mp4 --mode mediapipe
```

### Step 3: Find your clips

Look for a folder named:
```
your_video_clips_mediapipe_TIMESTAMP/
```

Inside you'll find:
```
your_video_clip01_5m23s.mp4
your_video_clip02_7m45s.mp4
your_video_clip03_6m12s.mp4
```

---

## Common Options

### Set Minimum Clip Length

Only keep clips longer than X seconds:
```bash
venv_mediapipe/bin/python clipper_unified.py video.mp4 --mode mediapipe --min-duration 60
```

### Save to Specific Folder

```bash
venv_mediapipe/bin/python clipper_unified.py video.mp4 --mode mediapipe -o /path/to/output
```

### Enable Debug Mode (See What's Detected)

```bash
venv_mediapipe/bin/python clipper_unified.py video.mp4 --mode mediapipe -d
```

This creates a debug folder with images showing:
- Where people are detected
- Stage boundaries (red lines)
- Whether person is at edge or center

---

## Mode Quick Reference

| Mode | When To Use | Speed | Accuracy |
|------|-------------|-------|----------|
| **mediapipe** | **Single comedian exits stage** | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **multimodal** | **Show with host + comedians** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **scene** | **Edited videos with cuts** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

---

## Troubleshooting

### No clips created?

1. **Lower the minimum duration:**
   ```bash
   venv_mediapipe/bin/python clipper_unified.py video.mp4 --mode mediapipe --min-duration 10
   ```

2. **Enable debug to see what's happening:**
   ```bash
   venv_mediapipe/bin/python clipper_unified.py video.mp4 --mode mediapipe -d
   ```

3. **Try a different mode:**
   ```bash
   venv_mediapipe/bin/python clipper_unified.py video.mp4 --mode scene
   ```

### Clips cut off too early/late?

Adjust the buffer in `clipper_rules.yaml`:
```yaml
filtering:
  buffer_before_start: 10.0  # Add more time before
  buffer_after_end: 10.0     # Add more time after
```

### Too many short clips?

Increase minimum duration:
```bash
venv_mediapipe/bin/python clipper_unified.py video.mp4 --mode mediapipe --min-duration 120
```

Or edit `clipper_rules.yaml`:
```yaml
filtering:
  min_duration: 120.0  # Only keep clips 2+ minutes
```

---

## Complete Example: Stage Exit with 10 Second Buffer

1. **Edit `clipper_rules.yaml`:**
   ```yaml
   filtering:
     min_duration: 30.0          # Keep clips 30+ seconds
     buffer_before_start: 10.0   # Add 10s before exit
     buffer_after_end: 10.0      # Add 10s after exit
   ```

2. **Run the clipper:**
   ```bash
   venv_mediapipe/bin/python clipper_unified.py standup_show.mp4 --mode mediapipe -d
   ```

3. **Check the output:**
   - Clips in `standup_show_clips_mediapipe_TIMESTAMP/`
   - Debug images in `standup_show_debug_mediapipe_TIMESTAMP/`

4. **Review and adjust:**
   - If clips are too long/short, adjust `buffer_before_start` and `buffer_after_end`
   - If too many/few clips, adjust `min_duration`
   - Rerun with new settings

Done! 🎉
