# YOLO Pose Detection - Quick Start Guide

## 🚀 Installation (5 minutes)

```bash
# 1. Install Python dependencies
pip install -r requirements_yolo.txt

# 2. Verify installation
python3 -c "from ultralytics import YOLO; print('✓ YOLO installed')"
python3 -c "import cv2; print('✓ OpenCV installed')"
```

That's it! Models download automatically on first use.

---

## 🎮 Try It Out

### Option 1: Interactive Player (See Detection in Real-Time)

```bash
# Launch the overlay player
python3 video_overlay_player.py your_video.mp4

# Controls:
# SPACE - Play/Pause
# Y     - Toggle YOLO pose overlay
# Q     - Quit
```

**Perfect for:** Understanding what the AI sees before processing.

### Option 2: Process Video (Create Clips)

```bash
# Basic processing
python3 clipper_yolo_pose.py your_video.mp4

# With debug visualization
python3 clipper_yolo_pose.py your_video.mp4 -d

# With better model
python3 clipper_yolo_pose.py your_video.mp4 --model yolo11m-pose.pt -d
```

**Creates:** Video clips + debug frames with pose skeletons.

---

## 💻 Using the UI

### Step 1: Select Video
Click the file picker or drag & drop your video

### Step 2: Choose Detection Method
**Detection Method** → Select **"YOLO Pose (Recommended)"**

### Step 3: Select Model (Optional)
**YOLO Model** → Choose model size:
- **Nano** - Fastest (testing)
- **Medium** - ⭐ Recommended (balanced)
- **Large** - Best accuracy

### Step 4: Adjust Settings
- **Min Duration**: 30 seconds (how short clips can be)
- **Max Duration**: 600 seconds (how long clips can be)
- **Exit Sensitivity**: 0.12 (lower = more sensitive)
- **Debug**: ✓ Check to export pose visualization

### Step 5: Process
Click **"Start Processing"** and wait!

---

## 📊 Model Comparison

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| **Nano** | ~10MB | ⚡⚡⚡ | ★★★ | Quick testing |
| **Small** | ~20MB | ⚡⚡ | ★★★★ | Fast processing |
| **Medium** | ~40MB | ⚡ | ★★★★★ | ⭐ **Recommended** |
| **Large** | ~80MB | 🐌 | ★★★★★ | High accuracy needs |
| **XLarge** | ~150MB | 🐌🐌 | ★★★★★ | Maximum quality |

**Start with Medium** - best balance of speed and accuracy.

---

## ⏱️ Processing Times

**60-minute video:**
- Nano model: ~30 minutes
- Medium model: ~60 minutes
- Large model: ~90 minutes

**First run adds:** ~5 minutes (model download)

---

## 📁 What You Get

### Output Folder Structure

```
video_name_clips_20250123_143022/
├── video_clip01_3m45s.mp4
├── video_clip02_5m12s.mp4
└── video_clip03_4m30s.mp4

video_name_yolo_pose_debug_20250123_143022/  (if debug enabled)
├── timeline/              # Frames every 30 seconds
│   ├── frame_0000s.jpg
│   ├── frame_0030s.jpg
│   └── frame_0060s.jpg
└── segments/              # Segment boundaries
    ├── seg01_start_45.2s.jpg
    ├── seg01_end_270.5s.jpg
    └── ...
```

---

## 🔍 Troubleshooting

### "Module not found" errors

```bash
pip install -r requirements_yolo.txt
```

### No clips created?

**Try the overlay player first:**
```bash
python3 video_overlay_player.py your_video.mp4
```

Watch the video and see if people are detected. If not:
- Try a larger model (Medium or Large)
- Check if people are clearly visible in frame
- Lower the minimum duration setting

### Models downloading during processing?

**Normal on first run!** Models are cached after download.

To pre-download:
```bash
python3 -c "from ultralytics import YOLO; YOLO('yolo11m-pose.pt')"
```

### Too slow?

- Use Nano or Small model
- Disable debug mode
- Process shorter videos first

---

## 🎯 Best Practices

### 1. Start with the Overlay Player
**Always** test new videos with the overlay player first:
```bash
python3 video_overlay_player.py video.mp4
```

This shows you:
- Is detection working?
- Are people being tracked?
- Where are the stage boundaries?

### 2. Enable Debug on First Run
Process with `-d` flag to get visualization:
```bash
python3 clipper_yolo_pose.py video.mp4 -d
```

Review debug frames to verify detection quality.

### 3. Choose the Right Model

**Quick test?** → Nano
**Production use?** → Medium ⭐
**Critical accuracy?** → Large

### 4. Tune Settings

If you get:
- **Too many clips** → Increase minimum duration
- **Too few clips** → Lower exit sensitivity, try larger model
- **Wrong boundaries** → Review debug frames, adjust exit threshold

---

## 📚 Full Documentation

- **Complete Guide**: [YOLO_POSE_README.md](YOLO_POSE_README.md)
- **Installation Help**: [INSTALL_YOLO.md](INSTALL_YOLO.md)
- **UI Integration**: [UI_INTEGRATION_COMPLETE.md](UI_INTEGRATION_COMPLETE.md)
- **What's New**: [WHATS_NEW.md](WHATS_NEW.md)

---

## 💡 Quick Tips

1. **First time?** Start with overlay player
2. **Not working?** Check debug frames
3. **Too slow?** Use smaller model
4. **Need accuracy?** Use Medium or Large
5. **Strange results?** Review stage boundary in debug output

---

## 🎬 Example Workflow

```bash
# 1. See what detection looks like
python3 video_overlay_player.py standup_show.mp4

# 2. Process with debug
python3 clipper_yolo_pose.py standup_show.mp4 --model yolo11m-pose.pt -d

# 3. Review debug frames in output folder

# 4. Re-process with adjusted settings if needed
python3 clipper_yolo_pose.py standup_show.mp4 --model yolo11m-pose.pt --min-duration 20 -d
```

---

## ✅ Success Checklist

- [ ] Dependencies installed (`requirements_yolo.txt`)
- [ ] Tested overlay player
- [ ] Processed test video with debug
- [ ] Reviewed debug frames
- [ ] Adjusted settings as needed
- [ ] Ready for production use!

---

**Need help?** Check the full documentation or create an issue.

**Ready to start?** Run the overlay player! 🎉
