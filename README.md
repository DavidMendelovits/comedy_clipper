# Comedy Clipper

Automatically clip standup comedy videos into individual comedian sets.

## 🎯 New Features

### YOLO11/12 Pose Detection + Interactive Video Overlay Player

Two powerful new tools for better visualization and detection:

1. **`clipper_yolo_pose.py`** - YOLO11/12 pose detection clipper
   - Superior accuracy and speed vs MediaPipe
   - Multiple model sizes (nano to extra-large)
   - Real-time pose skeleton visualization

2. **`video_overlay_player.py`** - Interactive video player
   - See detection overlays in real-time
   - Toggle YOLO/MediaPipe/Face detection on the fly
   - Adjust playback speed, seek through video
   - Perfect for debugging and testing

📖 **[See Full Documentation](YOLO_POSE_README.md)**

**Quick start:**
```bash
# Try the interactive player first
python3 video_overlay_player.py video.mp4

# Process with YOLO pose detection
python3 clipper_yolo_pose.py video.mp4 --model yolo11m-pose.pt -d
```

## Available Clippers

### 1. **clipper_speaker.py** ⭐ RECOMMENDED for Static Camera
Uses voice embeddings for TRUE speaker diarization (identifies comedians by voice, not pauses).

**Best for:** Static camera standup shows, showcases with multiple comedians
**Pros:**
- Identifies different speakers by voice characteristics
- Correctly groups same comedian's segments together
- Filters to 5-25 minute sets (typical comedian length)
- No HuggingFace gated models required
- Most accurate for standup compilations

**Usage:**
```bash
# 5-minute minimum sets (default)
python3 clipper_speaker.py your_show.mp4 -m 300

# 3-minute minimum (catch shorter sets)
python3 clipper_speaker.py your_show.mp4 -m 180
```

### 2. **clipper_pose.py** - Person Detection (Static Camera)
Uses YOLO computer vision to detect when a person enters/exits the stage.

**Best for:** Static camera shows with clear entry/exit, gaps between comedians
**Pros:**
- Detects physical presence on stage
- Works when comedians walk on/off with breaks
- Fast processing
- Visual-based (complements voice detection)

**Usage:**
```bash
# 3-minute minimum (default)
python3 clipper_pose.py your_show.mp4 -m 180

# More sensitive detection
python3 clipper_pose.py your_show.mp4 -c 0.3
```

### 3. **clipper_ffmpeg.py** (For Multi-Camera Shows)
Uses FFmpeg scene detection to find cuts between cameras/comedians.

**Best for:** Multi-camera shows, videos with visible scene changes
**Pros:**
- Very fast
- No AI dependencies
- Works great when camera switches between comedians

**Usage:**
```bash
python3 clipper_ffmpeg.py your_video.mp4 -o clips/
```

### 4. **clipper_whisper.py** (With Transcripts)
Uses Whisper AI transcription - detects speaker changes by pauses (not voice).

**Best for:** When you need transcripts of each segment
**Pros:**
- Provides text transcripts
- Works without scene changes
**Cons:**
- May split same comedian into multiple segments (uses pauses, not voice)

**Usage:**
```bash
python3 clipper_whisper.py your_video.mp4 -o clips/
```

### 5. **clipper.py** (Advanced - Pyannote)
Uses pyannote.audio for speaker diarization.

**Best for:** When you need the most accurate speaker identification
**Requires:** HuggingFace tokens and model access (see PYANNOTE_SETUP.md)

## Quick Start

### For Static Camera Standup Shows (RECOMMENDED):
```bash
# Install dependencies
source venv/bin/activate  # Or create: python3 -m venv venv
pip install -r requirements.txt

# Run speaker diarization clipper (5-min minimum sets)
python3 clipper_speaker.py your_show.mp4 -m 300 -o clips/

# Or 3-min minimum to catch shorter sets
python3 clipper_speaker.py your_show.mp4 -m 180 -o clips/
```

### For Multi-Camera Shows:
```bash
python3 clipper_ffmpeg.py your_show.mp4 -o clips/
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get HuggingFace Token

The pyannote.audio model requires a free HuggingFace account:

1. Create account at https://huggingface.co/join
2. Get your token at https://huggingface.co/settings/tokens
3. Accept the terms for the model at https://huggingface.co/pyannote/speaker-diarization-3.1

### 3. Set Your Token

```bash
export HF_TOKEN='your_token_here'
```

Or pass it directly with `--hf-token` flag.

## Usage

### Basic Usage

```bash
python clipper.py standup_show.mp4
```

This will:
- Extract audio from the video
- Identify all speakers
- Create clips for each comedian (minimum 30s sets)
- Save clips in the same directory as the input

### Advanced Options

```bash
# Specify output directory
python clipper.py show.mp4 -o clips/

# Change minimum set duration to 60 seconds (filters out short segments)
python clipper.py show.mp4 -m 60

# Keep the extracted audio file (for debugging)
python clipper.py show.mp4 --keep-audio

# Pass HuggingFace token directly
python clipper.py show.mp4 --hf-token 'your_token_here'
```

### Full Options

```
usage: clipper.py [-h] [-o OUTPUT] [-m MIN_DURATION] [--keep-audio] [--hf-token HF_TOKEN] video

Arguments:
  video                 Input video file

Options:
  -h, --help            Show this help message
  -o, --output          Output directory for clips (default: same as input)
  -m, --min-duration    Minimum duration for a set in seconds (default: 30)
  --keep-audio          Keep extracted audio file
  --hf-token            HuggingFace token (or set HF_TOKEN env var)
```

## Output

Clips are named using this format:
```
{original_name}_{speaker_label}_set{number}_{duration}s.mp4
```

Example output:
```
show_SPEAKER_00_set01_245s.mp4  # First comedian, 245 seconds
show_SPEAKER_00_set02_180s.mp4  # Same comedian, second set
show_SPEAKER_01_set01_312s.mp4  # Second comedian
show_SPEAKER_02_set01_156s.mp4  # Third comedian
```

## How Speaker Labels Work

The model assigns generic labels (SPEAKER_00, SPEAKER_01, etc.) to different voices it detects. These labels are:
- **Consistent within the same video** - SPEAKER_00 is always the same person
- **Not consistent across videos** - SPEAKER_00 in one video may be SPEAKER_01 in another
- **Assigned in order of appearance** - Usually the first speaker becomes SPEAKER_00

You can rename the files afterward if you know which comedian is which.

## Tips for Best Results

1. **Minimum Duration**: Use `-m` to filter out short segments (announcements, introductions, etc.)
   - For full sets: `-m 60` (1 minute minimum)
   - For clips: `-m 15` (15 seconds minimum)

2. **Audio Quality**: Better audio = better diarization
   - Clean audio with minimal background noise works best
   - Multiple speakers talking over each other may confuse the model

3. **Processing Time**:
   - CPU: About 10-20x real-time (1 hour video = 10-20 hours processing)
   - GPU: About 2-5x real-time (1 hour video = 2-5 hours processing)
   - First run downloads ~500MB of models

4. **Memory**:
   - Requires ~2GB RAM for audio processing
   - GPU version needs ~4GB VRAM

## Troubleshooting

**"HuggingFace token required"**
- Set `HF_TOKEN` environment variable or use `--hf-token` flag
- Make sure you accepted the terms at https://huggingface.co/pyannote/speaker-diarization-3.1

**"No segments found"**
- Try lowering `--min-duration`
- Check if audio extraction worked (use `--keep-audio` to inspect)

**Too many segments / wrong splits**
- Increase `--min-duration` to filter out short segments
- Speaker diarization isn't perfect - some manual editing may be needed

**Out of memory**
- Close other applications
- Process shorter videos
- Use CPU instead of GPU (it's slower but uses less memory)

## Technical Details

- **Diarization**: pyannote.audio 3.1 (state-of-the-art speaker diarization)
- **Video Processing**: moviepy + ffmpeg
- **GPU Acceleration**: Automatic if CUDA available

## Limitations

- Generic speaker labels (SPEAKER_00, etc.) - doesn't identify actual names
- May split single comedian if voice changes significantly
- May merge different comedians if voices are very similar
- Background noise, music, or audience can affect accuracy
- Requires manual review for best results

## License

MIT
