"""
Diarization Detector - Speaker diarization using Pyannote
Detects segments based on speaker changes
"""

import os
import subprocess
from pathlib import Path
from typing import List, Tuple

try:
    from pyannote.audio import Pipeline
    import torch
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    Pipeline = None
    torch = None


class DiarizationDetector:
    """Pyannote-based speaker diarization detector"""

    def __init__(self, config: any):
        """
        Initialize diarization detector.

        Args:
            config: Configuration object
        """
        if not PYANNOTE_AVAILABLE:
            raise ImportError("Pyannote not installed. Run: pip install pyannote-audio")

        self.config = config
        self.min_duration = config.get("filtering.min_duration", 30.0)

        # Get HuggingFace token
        hf_token = os.getenv('HF_TOKEN') or os.getenv('HUGGING_FACE_TOKEN')
        if not hf_token:
            raise ValueError(
                "HuggingFace token required for diarization mode. "
                "Set HF_TOKEN or HUGGING_FACE_TOKEN environment variable.\n"
                "Get your token at: https://huggingface.co/settings/tokens\n"
                "Accept pyannote terms at: https://huggingface.co/pyannote/speaker-diarization-3.1"
            )

        # Load diarization model
        print("Loading speaker diarization model...")
        self.pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token
        )

        # Use GPU if available
        if torch.cuda.is_available():
            self.pipeline = self.pipeline.to(torch.device("cuda"))
            print("  Using GPU acceleration")
        else:
            print("  Using CPU (this will be slower)")

    def detect_speakers(
        self,
        video_path: str
    ) -> List[Tuple[float, float]]:
        """
        Detect speaker segments in video.

        Args:
            video_path: Path to video file

        Returns:
            List of (start_time, end_time) tuples for speaker segments
        """
        print("Extracting audio for diarization...")

        # Extract audio from video
        audio_path = str(Path(video_path).with_suffix('.wav'))
        self._extract_audio(video_path, audio_path)

        try:
            # Run diarization
            print("Running speaker diarization model...")
            diarization = self.pipeline(audio_path)

            # Extract speaker segments
            speaker_segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speaker_segments.append((turn.start, turn.end, speaker))

            num_speakers = len(set(s[2] for s in speaker_segments))
            print(f"Found {num_speakers} unique speakers")
            print(f"Total segments: {len(speaker_segments)}")

            # Group segments by speaker
            grouped = self._group_by_speaker(speaker_segments)
            print(f"Grouped into {len(grouped)} segments")

            return grouped

        finally:
            # Cleanup audio file
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print("Cleaned up temporary audio file")

    def _extract_audio(self, video_path: str, audio_path: str):
        """
        Extract audio from video using FFmpeg.

        Args:
            video_path: Path to video file
            audio_path: Path to save audio file
        """
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            audio_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)

    def _group_by_speaker(
        self,
        speaker_segments: List[Tuple[float, float, str]]
    ) -> List[Tuple[float, float]]:
        """
        Group consecutive segments by the same speaker.

        Args:
            speaker_segments: List of (start, end, speaker_id) tuples

        Returns:
            List of (start, end) segment tuples
        """
        if not speaker_segments:
            return []

        grouped = []
        current_speaker = speaker_segments[0][2]
        current_start = speaker_segments[0][0]
        current_end = speaker_segments[0][1]

        for start, end, speaker in speaker_segments[1:]:
            if speaker == current_speaker:
                # Extend current segment
                current_end = end
            else:
                # Save current segment if long enough
                duration = current_end - current_start
                if duration >= self.min_duration:
                    grouped.append((current_start, current_end))

                # Start new segment
                current_speaker = speaker
                current_start = start
                current_end = end

        # Add last segment
        duration = current_end - current_start
        if duration >= self.min_duration:
            grouped.append((current_start, current_end))

        return grouped
