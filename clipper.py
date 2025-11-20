#!/usr/bin/env python3
"""
Comedy Clipper - Automatically clip standup comedy videos by speaker using diarization
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple
import argparse

from dotenv import load_dotenv
from pyannote.audio import Pipeline
from moviepy import VideoFileClip
import torch

# Load environment variables from .env file
load_dotenv()


class ComedyClipper:
    def __init__(self, hf_token: str = None):
        """
        Initialize the Comedy Clipper with speaker diarization.

        Args:
            hf_token: HuggingFace token for pyannote models (required for first use)
        """
        self.hf_token = hf_token or os.getenv('HF_TOKEN') or os.getenv('HUGGING_FACE_TOKEN')
        if not self.hf_token:
            raise ValueError(
                "HuggingFace token required. Set HF_TOKEN or HUGGING_FACE_TOKEN environment variable or pass hf_token parameter.\n"
                "Get your token at: https://huggingface.co/settings/tokens\n"
                "Accept pyannote terms at: https://huggingface.co/pyannote/speaker-diarization-3.1"
            )

        print("Loading speaker diarization model...")
        self.pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=self.hf_token
        )

        # Use GPU if available
        if torch.cuda.is_available():
            self.pipeline = self.pipeline.to(torch.device("cuda"))
            print("Using GPU acceleration")
        else:
            print("Using CPU (this will be slower)")

    def extract_audio(self, video_path: str, output_audio_path: str = None) -> str:
        """Extract audio from video file."""
        if output_audio_path is None:
            output_audio_path = str(Path(video_path).with_suffix('.wav'))

        print(f"Extracting audio from {video_path}...")
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(output_audio_path, codec='pcm_s16le', verbose=False, logger=None)
        video.close()

        return output_audio_path

    def diarize_audio(self, audio_path: str) -> List[Tuple[float, float, str]]:
        """
        Perform speaker diarization on audio file.

        Returns:
            List of (start_time, end_time, speaker_label) tuples
        """
        print(f"Running speaker diarization on {audio_path}...")
        diarization = self.pipeline(audio_path)

        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append((turn.start, turn.end, speaker))

        print(f"Found {len(set(s[2] for s in segments))} unique speakers")
        print(f"Total segments: {len(segments)}")

        return segments

    def group_segments_by_speaker(self, segments: List[Tuple[float, float, str]],
                                   min_duration: float = 30.0) -> List[Tuple[float, float, str]]:
        """
        Group consecutive segments by the same speaker and filter by minimum duration.

        Args:
            segments: List of (start, end, speaker) tuples
            min_duration: Minimum duration in seconds for a set (default 30s)

        Returns:
            List of grouped (start, end, speaker) tuples
        """
        if not segments:
            return []

        grouped = []
        current_speaker = segments[0][2]
        current_start = segments[0][0]
        current_end = segments[0][1]

        for start, end, speaker in segments[1:]:
            if speaker == current_speaker:
                # Extend current segment
                current_end = end
            else:
                # Save previous segment if it meets minimum duration
                duration = current_end - current_start
                if duration >= min_duration:
                    grouped.append((current_start, current_end, current_speaker))

                # Start new segment
                current_speaker = speaker
                current_start = start
                current_end = end

        # Don't forget the last segment
        duration = current_end - current_start
        if duration >= min_duration:
            grouped.append((current_start, current_end, current_speaker))

        return grouped

    def clip_video(self, video_path: str, segments: List[Tuple[float, float, str]],
                   output_dir: str = None):
        """
        Clip video based on speaker segments.

        Args:
            video_path: Path to input video
            segments: List of (start, end, speaker) tuples
            output_dir: Directory to save clips (default: same as input video)
        """
        if output_dir is None:
            output_dir = Path(video_path).parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        video_name = Path(video_path).stem

        print(f"\nClipping {len(segments)} segments...")
        video = VideoFileClip(video_path)

        for i, (start, end, speaker) in enumerate(segments, 1):
            duration = end - start
            output_path = output_dir / f"{video_name}_{speaker}_set{i:02d}_{int(duration)}s.mp4"

            print(f"  [{i}/{len(segments)}] {speaker}: {start:.1f}s - {end:.1f}s ({duration:.1f}s) -> {output_path.name}")

            clip = video.subclip(start, end)
            clip.write_videofile(
                str(output_path),
                codec='libx264',
                audio_codec='aac',
                verbose=False,
                logger=None
            )
            clip.close()

        video.close()
        print(f"\nDone! Clips saved to: {output_dir}")

    def process_video(self, video_path: str, output_dir: str = None,
                     min_duration: float = 30.0, keep_audio: bool = False):
        """
        Complete pipeline: extract audio, diarize, group, and clip.

        Args:
            video_path: Path to input video
            output_dir: Directory to save clips
            min_duration: Minimum duration for a set in seconds
            keep_audio: Keep extracted audio file
        """
        # Extract audio
        audio_path = self.extract_audio(video_path)

        try:
            # Diarize
            segments = self.diarize_audio(audio_path)

            # Group by speaker
            grouped_segments = self.group_segments_by_speaker(segments, min_duration)

            if not grouped_segments:
                print(f"\nNo segments found with minimum duration of {min_duration}s")
                return

            print(f"\nGrouped into {len(grouped_segments)} sets:")
            for i, (start, end, speaker) in enumerate(grouped_segments, 1):
                print(f"  {i}. {speaker}: {start:.1f}s - {end:.1f}s ({end-start:.1f}s)")

            # Clip video
            self.clip_video(video_path, grouped_segments, output_dir)

        finally:
            # Cleanup
            if not keep_audio and os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"Cleaned up temporary audio file: {audio_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Automatically clip standup comedy videos by speaker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python clipper.py standup_show.mp4

  # Specify output directory
  python clipper.py standup_show.mp4 -o clips/

  # Change minimum set duration to 60 seconds
  python clipper.py standup_show.mp4 -m 60

  # Keep extracted audio file
  python clipper.py standup_show.mp4 --keep-audio

Environment Variables:
  HF_TOKEN    HuggingFace token (required for first use)
              Get at: https://huggingface.co/settings/tokens
        """
    )

    parser.add_argument('video', help='Input video file')
    parser.add_argument('-o', '--output', help='Output directory for clips (default: same as input)')
    parser.add_argument('-m', '--min-duration', type=float, default=30.0,
                       help='Minimum duration for a set in seconds (default: 30)')
    parser.add_argument('--keep-audio', action='store_true',
                       help='Keep extracted audio file')
    parser.add_argument('--hf-token', help='HuggingFace token (or set HF_TOKEN env var)')

    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"Error: Video file not found: {args.video}")
        sys.exit(1)

    try:
        clipper = ComedyClipper(hf_token=args.hf_token)
        clipper.process_video(
            args.video,
            output_dir=args.output,
            min_duration=args.min_duration,
            keep_audio=args.keep_audio
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
