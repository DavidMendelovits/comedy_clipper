# Comedy Clipper - Method Comparison

## All Available Methods

### 1. Voice-Based Speaker Diarization ⭐ BEST
**Tool:** `clipper_speaker.py`

**How it works:**
- Analyzes voice characteristics using neural embeddings
- Clusters similar voices to identify different speakers
- Groups consecutive segments from same comedian
- Filters by duration (5-25 min typical)

**Pros:**
- Actually identifies different comedians by voice
- Groups same person's segments together
- Works with static camera
- No gated models needed

**Cons:**
- Slower processing (10-15 min for 1hr video)
- May merge similar voices
- Requires good audio quality

**Best for:** Static camera standup compilations

---

### 2. Person/Pose Detection
**Tool:** `clipper_pose.py`

**How it works:**
- Uses YOLO computer vision to detect person on stage
- Tracks when person enters (appears) and exits (disappears)
- Groups continuous presence as one set
- Filters by duration

**Pros:**
- Visual-based detection
- Fast processing
- Detects physical entry/exit
- Complements audio methods

**Cons:**
- Requires clear gaps between comedians
- Won't work if people quickly swap without gaps
- Detects presence, not identity

**Best for:** Shows with visible entry/exit, gaps between sets

---

### 3. Scene Detection
**Tool:** `clipper_ffmpeg.py`

**How it works:**
- Detects scene changes (cuts) in video
- Groups scenes close together
- Filters by duration

**Pros:**
- Very fast
- No AI needed
- Works great for multi-camera shows

**Cons:**
- Only works if camera cuts between comedians
- Won't work with static camera
- Depends on video editing

**Best for:** Multi-camera shows with scene cuts

---

### 4. Transcription + Pause Detection
**Tool:** `clipper_whisper.py`

**How it works:**
- Transcribes entire video using Whisper AI
- Detects long pauses (3+ seconds)
- Assumes pause = speaker change
- Provides text transcripts

**Pros:**
- Generates transcripts
- Works with static camera
- Good for archival

**Cons:**
- Splits same comedian into multiple segments
- Pause ≠ speaker change
- Long processing time

**Best for:** When you need transcripts, not for speaker separation

---

### 5. Silence Detection
**Tool:** `clipper_audio.py`

**How it works:**
- Detects silence in audio
- Groups speech segments
- Assumes silence = break between comedians

**Pros:**
- Simple approach
- Fast

**Cons:**
- Creates one long segment if no silence
- Doesn't identify speakers
- Not useful for standup (continuous laughter/applause)

**Best for:** Not recommended for comedy

---

### 6. Pyannote (Advanced)
**Tool:** `clipper.py`

**How it works:**
- State-of-the-art speaker diarization
- Uses multiple neural networks
- Highly accurate speaker identification

**Pros:**
- Most accurate
- Industry standard

**Cons:**
- Requires HuggingFace account
- Needs access to 3+ gated models
- Complex setup

**Best for:** When you can get model access and need highest accuracy

---

## Test Results Comparison

Test video: 1-hour standup compilation with multiple comedians

| Method | Time | Segments Found | Accuracy | Notes |
|--------|------|----------------|----------|-------|
| **clipper_speaker.py** | 15 min | 2 sets (3.6min, 9.3min) | ⭐⭐⭐⭐ | Correctly identified 2 different voices |
| **clipper_pose.py** | 8 min | 1 set (42min) | ⭐⭐ | Detected continuous presence (no gaps) |
| **clipper_ffmpeg.py** | 3 min | 13 segments | ⭐⭐⭐ | Works if video has scene cuts |
| **clipper_whisper.py** | 45 min | 8 sets | ⭐⭐ | Split same comedians, has transcripts |
| **clipper_audio.py** | 5 min | 1 set (42min) | ⭐ | Found one continuous speech segment |

---

## Recommendations

### For Static Camera Standup Shows:
1. **Primary:** `clipper_speaker.py` (voice-based diarization)
2. **Backup:** `clipper_pose.py` (if comedians have clear entry/exit)

### For Multi-Camera Shows:
1. **Primary:** `clipper_ffmpeg.py` (scene detection)
2. **Backup:** `clipper_speaker.py` (voice-based)

### For Archival/Searchability:
1. **Primary:** `clipper_whisper.py` (generates transcripts)
2. **Post-process:** Manually merge same comedian

### When You Need Maximum Accuracy:
1. **Primary:** `clipper.py` (pyannote - if you can get model access)
2. **Backup:** `clipper_speaker.py` (voice-based)

---

## Combining Methods

You can run multiple methods and compare results:

```bash
# Run voice diarization
python3 clipper_speaker.py video.mp4 -o clips_voice/

# Run pose detection
python3 clipper_pose.py video.mp4 -o clips_pose/

# Compare results and pick best clips
```

The voice method (`clipper_speaker.py`) is recommended as the default for most standup use cases.
