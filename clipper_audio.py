#!/usr/bin/env python3
"""
Comedy Clipper - Audio-based speaker detection
Works with static camera by analyzing audio to detect speaker changes
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple
import subprocess


class AudioComedyClipper:
    """Clipper using audio analysis for speaker changes (works with static camera)"""

    def __init__(self):
        pass

    def extract_audio(self, video_path: str) -> str:
        """Extract audio from video."""
        audio_path = str(Path(video_path).with_suffix('.wav'))
        print(f"Extracting audio from {video_path}...")

        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-ac', '1',  # Mono
            '-ar', '16000',  # 16kHz sample rate
            audio_path
        ]

        subprocess.run(cmd, capture_output=True)
        return audio_path

    def detect_silence_segments(self, video_path: str, silence_threshold: float = -40.0,
                                silence_duration: float = 2.0) -> List[Tuple[float, float]]:
        """
        Detect segments of speech by finding silence gaps.

        Args:
            video_path: Path to video
            silence_threshold: dB threshold for silence (default -40dB)
            silence_duration: Minimum silence duration in seconds

        Returns:
            List of (start, end) tuples for speech segments
        """
        print(f"Detecting speech segments (silence threshold: {silence_threshold}dB)...")

        # Use ffmpeg silencedetect filter
        cmd = [
            'ffmpeg', '-i', video_path,
            '-af', f'silencedetect=noise={silence_threshold}dB:d={silence_duration}',
            '-f', 'null', '-'
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        # Parse silence periods
        silence_starts = []
        silence_ends = []

        for line in result.stdout.split('\n'):
            if 'silence_start:' in line:
                try:
                    time = float(line.split('silence_start:')[1].strip().split()[0])
                    silence_starts.append(time)
                except (IndexError, ValueError):
                    pass
            elif 'silence_end:' in line:
                try:
                    time = float(line.split('silence_end:')[1].strip().split()[0])
                    silence_ends.append(time)
                except (IndexError, ValueError):
                    pass

        # Convert silence periods to speech segments
        segments = []

        # First segment (if video doesn't start with silence)
        if silence_starts and (not silence_ends or silence_starts[0] > 0):
            segments.append((0.0, silence_starts[0]))

        # Segments between silences
        for i in range(len(silence_ends)):
            start = silence_ends[i]
            end = silence_starts[i + 1] if i + 1 < len(silence_starts) else None
            if end:
                segments.append((start, end))

        # Last segment (if video doesn't end with silence)
        if silence_ends and len(silence_ends) > len(silence_starts):
            # Video ends with speech
            pass  # We don't know the end time

        print(f"Found {len(segments)} speech segments")
        return segments

    def group_segments(self, segments: List[Tuple[float, float]],
                      min_duration: float = 30.0,
                      max_gap: float = 15.0) -> List[Tuple[float, float]]:
        """
        Group consecutive speech segments into comedian sets.

        Args:
            segments: List of speech (start, end) tuples
            min_duration: Minimum duration for a set
            max_gap: Maximum gap between segments to group together

        Returns:
            List of grouped (start, end) tuples
        """
        if not segments:
            return []

        grouped = []
        current_start = segments[0][0]
        current_end = segments[0][1]

        for i in range(1, len(segments)):
            start, end = segments[i]
            gap = start - current_end

            if gap <= max_gap:
                # Extend current group
                current_end = end
            else:
                # Save current group if long enough
                duration = current_end - current_start
                if duration >= min_duration:
                    grouped.append((current_start, current_end))

                # Start new group
                current_start = start
                current_end = end

        # Don't forget last group
        duration = current_end - current_start
        if duration >= min_duration:
            grouped.append((current_start, current_end))

        return grouped

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

    def clip_video(self, video_path: str, segments: List[Tuple[float, float]],
                   output_dir: str = None):
        """Clip video based on segments."""
        if output_dir is None:
            output_dir = Path(video_path).parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        video_name = Path(video_path).stem

        print(f"\nClipping {len(segments)} segments...")

        for i, (start, end) in enumerate(segments, 1):
            duration = end - start
            output_path = output_dir / f"{video_name}_set{i:02d}_{int(duration)}s.mp4"

            print(f"  [{i}/{len(segments)}] {start:.1f}s - {end:.1f}s ({duration:.1f}s) -> {output_path.name}")

            self.clip_video_ffmpeg(video_path, start, end, str(output_path))

        print(f"\nDone! Clips saved to: {output_dir}")

    def process_video(self, video_path: str, output_dir: str = None,
                     min_duration: float = 30.0, max_gap: float = 15.0,
                     silence_threshold: float = -40.0):
        """
        Complete pipeline: detect speech segments, group, and clip.

        Args:
            video_path: Path to input video
            output_dir: Directory to save clips
            min_duration: Minimum duration for a set
            max_gap: Maximum gap to group segments together
            silence_threshold: dB threshold for silence detection
        """
        # Detect speech segments
        segments = self.detect_silence_segments(video_path, silence_threshold)

        if not segments:
            print("No speech segments detected. Try adjusting --silence-threshold.")
            return

        # Group into sets
        grouped = self.group_segments(segments, min_duration, max_gap)

        if not grouped:
            print(f"\nNo segments found with minimum duration of {min_duration}s")
            print("Try lowering --min-duration or --max-gap")
            return

        print(f"\nGrouped into {len(grouped)} sets:")
        for i, (start, end) in enumerate(grouped, 1):
            print(f"  {i}. {start:.1f}s - {end:.1f}s ({end-start:.1f}s)")

        # Clip video
        self.clip_video(video_path, grouped, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Comedy clipper using audio-based speaker detection (works with static camera)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python3 clipper_audio.py standup_show.mp4

  # Custom output directory
  python3 clipper_audio.py show.mp4 -o clips/

  # Adjust sensitivity
  python3 clipper_audio.py show.mp4 -s -35  # More sensitive (picks up quieter speech)
  python3 clipper_audio.py show.mp4 -s -45  # Less sensitive (only loud speech)

  # Adjust minimum set duration
  python3 clipper_audio.py show.mp4 -m 60    # 60 second minimum sets
        """
    )

    parser.add_argument('video', help='Input video file')
    parser.add_argument('-o', '--output', help='Output directory for clips')
    parser.add_argument('-m', '--min-duration', type=float, default=30.0,
                       help='Minimum duration for a set in seconds (default: 30)')
    parser.add_argument('-g', '--max-gap', type=float, default=15.0,
                       help='Maximum gap to group segments together in seconds (default: 15)')
    parser.add_argument('-s', '--silence-threshold', type=float, default=-40.0,
                       help='Silence threshold in dB (default: -40, lower=more sensitive)')

    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"Error: Video file not found: {args.video}")
        sys.exit(1)

    try:
        clipper = AudioComedyClipper()
        clipper.process_video(
            args.video,
            output_dir=args.output,
            min_duration=args.min_duration,
            max_gap=args.max_gap,
            silence_threshold=args.silence_threshold
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
