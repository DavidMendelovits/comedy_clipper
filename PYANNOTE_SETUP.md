# How to Enable Speaker Diarization with Pyannote

The `clipper.py` script uses speaker diarization to identify different comedians by voice. However, pyannote.audio requires accepting terms for multiple gated models.

## Required Model Access

You need to accept terms for these HuggingFace models:

1. **Main diarization pipeline:**
   https://huggingface.co/pyannote/speaker-diarization-3.1

2. **Segmentation model:**
   https://huggingface.co/pyannote/segmentation-3.0

3. **Embedding model:**
   https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM

## Setup Steps

1. **Create HuggingFace account** (if you don't have one):
   - https://huggingface.co/join

2. **Get your access token**:
   - Go to: https://huggingface.co/settings/tokens
   - Click "New token"
   - Name it "comedy-clipper"
   - Copy the token

3. **Accept ALL model terms** (visit each link and click "Agree"):
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - https://huggingface.co/pyannote/segmentation-3.0
   - https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM

4. **Add token to .env file:**
   ```bash
   echo "HUGGING_FACE_TOKEN=your_token_here" >> .env
   ```

5. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

6. **Run the clipper:**
   ```bash
   source venv/bin/activate
   python clipper.py your_video.mp4 -m 30 -o clips/
   ```

## How It Works

- Extracts audio from video
- Runs pyannote speaker diarization to identify different speakers
- Groups consecutive segments by the same speaker
- Labels speakers as SPEAKER_00, SPEAKER_01, etc.
- Clips video for each comedian's set

## Advantages

- Actually identifies different speakers by voice
- Works with static camera (no scene changes needed)
- More accurate than silence detection for multi-comedian shows

## Disadvantages

- Requires HuggingFace account and model access
- First run downloads ~500MB of models
- Slower processing (10-20x real-time on CPU)
- Requires accepting terms for gated models
