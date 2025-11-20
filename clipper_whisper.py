#!/usr/bin/env python3
"""
Comedy Clipper - Whisper-based speaker detection
Uses Whisper transcription timestamps to identify speaker segments
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple
import subprocess
from faster_whisper import WhisperModel


class WhisperComedyClipper:
    """Clipper using Whisper transcription for speaker segmentation"""

    def __init__(self, model_size: str = "base"):
        """
        Initialize clipper.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
        """
        print(f"Loading Whisper {model_size} model...")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        print("Model loaded!")

    def transcribe_and_segment(self, video_path: str, pause_threshold: float = 3.0) -> List[Tuple[float, float, str]]:
        """
        Transcribe video and detect speaker segments based on pauses.

        Args:
            video_path: Path to video
            pause_threshold: Pause duration to consider as speaker change (seconds)

        Returns:
            List of (start, end, text) tuples for each speech segment
        """
        print(f"Transcribing {video_path}...")

        segments, info = self.model.transcribe(
            video_path,
            beam_size=5,
            word_timestamps=True
        )

        print(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")

        # Collect all segments with timestamps
        speech_segments = []
        for segment in segments:
            speech_segments.append((segment.start, segment.end, segment.text.strip()))

        print(f"Found {len(speech_segments)} speech segments")
        return speech_segments

    def group_by_speaker(self, segments: List[Tuple[float, float, str]],
                         pause_threshold: float = 3.0,
                         min_duration: float = 30.0) -> List[Tuple[float, float, List[str]]]:
        """
        Group segments into speaker sets based on pause length.

        Args:
            segments: List of (start, end, text) tuples
            pause_threshold: Minimum pause to consider new speaker
            min_duration: Minimum duration for a set

        Returns:
            List of (start, end, texts) tuples for each speaker set
        """
        if not segments:
            return []

        speaker_sets = []
        current_start = segments[0][0]
        current_end = segments[0][1]
        current_texts = [segments[0][2]]

        for i in range(1, len(segments)):
            start, end, text = segments[i]
            pause = start - current_end

            if pause >= pause_threshold:
                # Long pause - likely new speaker
                duration = current_end - current_start
                if duration >= min_duration:
                    speaker_sets.append((current_start, current_end, current_texts))

                # Start new set
                current_start = start
                current_end = end
                current_texts = [text]
            else:
                # Same speaker continues
                current_end = end
                current_texts.append(text)

        # Don't forget last set
        duration = current_end - current_start
        if duration >= min_duration:
            speaker_sets.append((current_start, current_end, current_texts))

        return speaker_sets

    def clip_video_ffmpeg(self, video_path: str, start: float, end: float, output_path: str):
        """Clip video using ffmpeg."""
        duration = end - start

        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start),
            '-i', video_path,
            '-t', str(duration),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-preset', 'fast',
            output_path
        ]

        subprocess.run(cmd, capture_output=True)

    def clip_video(self, video_path: str, speaker_sets: List[Tuple[float, float, List[str]]],
                   output_dir: str = None):
        """Clip video based on speaker sets."""
        if output_dir is None:
            output_dir = Path(video_path).parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        video_name = Path(video_path).stem

        print(f"\nClipping {len(speaker_sets)} sets...")

        for i, (start, end, texts) in enumerate(speaker_sets, 1):
            duration = end - start
            output_path = output_dir / f"{video_name}_speaker{i:02d}_{int(duration)}s.mp4"

            # Save transcript snippet
            transcript_path = output_dir / f"{video_name}_speaker{i:02d}_transcript.txt"
            with open(transcript_path, 'w') as f:
                f.write(' '.join(texts))

            print(f"  [{i}/{len(speaker_sets)}] {start:.1f}s - {end:.1f}s ({duration:.1f}s) -> {output_path.name}")
            print(f"      Preview: {' '.join(texts)[:100]}...")

            self.clip_video_ffmpeg(video_path, start, end, str(output_path))

        print(f"\nDone! Clips and transcripts saved to: {output_dir}")

    def process_video(self, video_path: str, output_dir: str = None,
                     min_duration: float = 30.0, pause_threshold: float = 3.0):
        """
        Complete pipeline: transcribe, detect speakers, and clip.

        Args:
            video_path: Path to input video
            output_dir: Directory to save clips
            min_duration: Minimum duration for a set
            pause_threshold: Pause duration to detect speaker change
        """
        # Transcribe and get segments
        segments = self.transcribe_and_segment(video_path, pause_threshold)

        if not segments:
            print("No speech detected in video")
            return

        # Group into speaker sets
        speaker_sets = self.group_by_speaker(segments, pause_threshold, min_duration)

        if not speaker_sets:
            print(f"\nNo speaker sets found with minimum duration of {min_duration}s")
            print("Try lowering --min-duration or --pause-threshold")
            return

        print(f"\nDetected {len(speaker_sets)} speaker sets:")
        for i, (start, end, texts) in enumerate(speaker_sets, 1):
            preview = ' '.join(texts)[:80]
            print(f"  {i}. {start:.1f}s - {end:.1f}s ({end-start:.1f}s): {preview}...")

        # Clip video
        self.clip_video(video_path, speaker_sets, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Comedy clipper using Whisper transcription for speaker detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (uses base model)
  python3 clipper_whisper.py standup_show.mp4

  # Use larger model for better accuracy
  python3 clipper_whisper.py show.mp4 --model medium

  # Adjust speaker detection sensitivity
  python3 clipper_whisper.py show.mp4 -p 5  # 5 second pause = new speaker

  # Save to specific directory
  python3 clipper_whisper.py show.mp4 -o clips/

Models:
  tiny   - Fastest, least accurate (~75MB)
  base   - Good balance (~150MB) [default]
  small  - Better accuracy (~500MB)
  medium - Very good (~1.5GB)
  large  - Best accuracy (~3GB)
        """
    )

    parser.add_argument('video', help='Input video file')
    parser.add_argument('-o', '--output', help='Output directory for clips')
    parser.add_argument('-m', '--min-duration', type=float, default=30.0,
                       help='Minimum duration for a set in seconds (default: 30)')
    parser.add_argument('-p', '--pause-threshold', type=float, default=3.0,
                       help='Pause duration to detect speaker change in seconds (default: 3)')
    parser.add_argument('--model', default='base',
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Whisper model size (default: base)')

    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"Error: Video file not found: {args.video}")
        sys.exit(1)

    try:
        clipper = WhisperComedyClipper(model_size=args.model)
        clipper.process_video(
            args.video,
            output_dir=args.output,
            min_duration=args.min_duration,
            pause_threshold=args.pause_threshold
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
