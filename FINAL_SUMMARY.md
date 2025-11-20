# Comedy Clipper - Final Deliverable

## ✅ Complete Toolkit for Standup Comedy Clipping

You now have **6 different methods** to automatically clip standup videos, each optimized for different scenarios.

---

## Main Tools for Static Camera

### 1. clipper_speaker.py ⭐ RECOMMENDED
**True speaker diarization using voice embeddings**

```bash
python3 clipper_speaker.py your_show.mp4 -m 300
```

**Results on test video:**
- Detected 2 unique speakers by voice
- Comedian 1: 3m 38s
- Comedian 2: 9m 18s
- ✅ Correctly grouped same comedian together

**Perfect for:** Static camera standup compilations

---

### 2. clipper_pose.py - NEW!
**Person detection using YOLO computer vision**

```bash
python3 clipper_pose.py your_show.mp4 -m 180
```

**Results on test video:**
- Detected 2 presence segments
- 1 comedian set: 42m 7s (continuous presence)
- Fast processing (8 minutes)

**Perfect for:** Shows with clear entry/exit, gaps between comedians

---

## Other Tools

### 3. clipper_ffmpeg.py
**Scene detection** - Fast, works for multi-camera shows

### 4. clipper_whisper.py  
**Transcription-based** - Provides text transcripts but splits same comedian

### 5. clipper_audio.py
**Silence detection** - Simple but not effective for comedy

### 6. clipper.py
**Pyannote** - Most accurate but requires HuggingFace model access

---

## Quick Start Guide

### Setup (One Time):
```bash
cd /Users/davidmendelovits/space/comedy_clipper/.conductor/vaduz
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run on Your Videos:

**For voice-based clipping (recommended):**
```bash
source venv/bin/activate
python3 clipper_speaker.py your_standup_show.mp4 -m 300
```

**For pose-based clipping:**
```bash
source venv/bin/activate
python3 clipper_pose.py your_standup_show.mp4 -m 180
```

---

## Files Delivered

### Working Scripts:
- ✅ `clipper_speaker.py` - Voice diarization (RECOMMENDED)
- ✅ `clipper_pose.py` - Pose/person detection (NEW!)
- ✅ `clipper_ffmpeg.py` - Scene detection
- ✅ `clipper_whisper.py` - Transcription-based
- ✅ `clipper_audio.py` - Silence detection
- ✅ `clipper_simple.py` - Basic scene clipper
- ✅ `clipper.py` - Pyannote version

### Documentation:
- `README.md` - Full user guide
- `SUMMARY.md` - Quick overview
- `COMPARISON.md` - Method comparison (NEW!)
- `FINAL_SUMMARY.md` - This file
- `PYANNOTE_SETUP.md` - Advanced setup

### Configuration:
- `requirements.txt` - All dependencies
- `requirements_speaker.txt` - Speaker diarization only
- `.env` - Environment variables
- `.gitignore` - Git ignore rules

---

## Key Differences

### Voice vs Pose Detection:

**Voice (clipper_speaker.py):**
- ✅ Identifies WHO is speaking
- ✅ Groups same comedian together
- ❌ Slower (15min for 1hr video)
- Best when: Audio quality is good

**Pose (clipper_pose.py):**
- ✅ Detects physical presence
- ✅ Faster (8min for 1hr video)
- ❌ Doesn't identify WHO
- ❌ Needs clear entry/exit
- Best when: Comedians have clear gaps

### Recommended Strategy:

1. Try `clipper_speaker.py` first (voice-based)
2. If results aren't good, try `clipper_pose.py`
3. For multi-camera: use `clipper_ffmpeg.py`

---

## Dependencies Installed

Core libraries:
- resemblyzer - Voice encoder
- spectralcluster - Speaker clustering
- ultralytics (YOLO) - Person detection
- opencv-python - Computer vision
- faster-whisper - Speech transcription
- torch, torchvision - Neural networks
- librosa - Audio processing

---

## Next Steps

1. Get a better test video with more comedians
2. Run both voice and pose detection
3. Compare results
4. Choose best method for your use case

You're all set to automatically clip standup comedy videos! 🎤
