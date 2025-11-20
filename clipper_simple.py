#!/usr/bin/env python3
"""
Comedy Clipper - Simple version using scene detection
Automatically clips videos at scene changes (cuts between comedians)
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple
import subprocess
import json

from moviepy import VideoFileClip


class SimpleComedyClipper:
    """Simple clipper using ffmpeg scene detection"""

    def __init__(self, scene_threshold: float = 0.3):
        """
        Initialize clipper.

        Args:
            scene_threshold: Sensitivity for scene detection (0-1, lower = more sensitive)
        """
        self.scene_threshold = scene_threshold

    def detect_scenes(self, video_path: str) -> List[float]:
        """
        Detect scene changes using ffmpeg.

        Returns:
            List of timestamps where scenes change
        """
        print(f"Detecting scene changes in {video_path}...")

        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-filter:v', f"select='gt(scene,{self.scene_threshold})',showinfo",
            '-f', 'null',
            '-'
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # Parse scene change timestamps from ffmpeg output
        timestamps = [0.0]  # Always start from beginning
        for line in result.stdout.split('\n'):
            if 'pts_time:' in line:
                try:
                    # Extract timestamp
                    pts_time = line.split('pts_time:')[1].split()[0]
                    timestamps.append(float(pts_time))
                except (IndexError, ValueError):
                    continue

        timestamps.sort()
        print(f"Found {len(timestamps)} scene changes")
        return timestamps

    def group_scenes(self, timestamps: List[float], min_duration: float = 30.0,
                    max_gap: float = 5.0) -> List[Tuple[float, float]]:
        """
        Group consecutive scenes into segments (comedian sets).

        Args:
            timestamps: List of scene change times
            min_duration: Minimum duration for a segment (seconds)
            max_gap: Maximum gap to consider scenes part of same set (seconds)

        Returns:
            List of (start, end) tuples for each segment
        """
        if len(timestamps) < 2:
            return []

        segments = []
        current_start = timestamps[0]
        last_time = timestamps[0]

        for i in range(1, len(timestamps)):
            time = timestamps[i]
            gap = time - last_time

            # If gap is too large, consider it a new segment
            if gap > max_gap:
                duration = last_time - current_start
                if duration >= min_duration:
                    segments.append((current_start, last_time))
                current_start = time

            last_time = time

        # Don't forget the last segment
        duration = last_time - current_start
        if duration >= min_duration:
            segments.append((current_start, last_time))

        return segments

    def clip_video(self, video_path: str, segments: List[Tuple[float, float]],
                   output_dir: str = None):
        """
        Clip video based on segments.

        Args:
            video_path: Path to input video
            segments: List of (start, end) tuples
            output_dir: Directory to save clips
        """
        if output_dir is None:
            output_dir = Path(video_path).parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        video_name = Path(video_path).stem

        print(f"\nClipping {len(segments)} segments...")
        video = VideoFileClip(video_path)

        for i, (start, end) in enumerate(segments, 1):
            duration = end - start
            output_path = output_dir / f"{video_name}_segment{i:02d}_{int(duration)}s.mp4"

            print(f"  [{i}/{len(segments)}] {start:.1f}s - {end:.1f}s ({duration:.1f}s) -> {output_path.name}")

            clip = video.subclipped(start, end)
            clip.write_videofile(
                str(output_path),
                codec='libx264',
                audio_codec='aac'
            )
            clip.close()

        video.close()
        print(f"\nDone! Clips saved to: {output_dir}")

    def process_video(self, video_path: str, output_dir: str = None,
                     min_duration: float = 30.0, max_gap: float = 5.0):
        """
        Complete pipeline: detect scenes, group, and clip.

        Args:
            video_path: Path to input video
            output_dir: Directory to save clips
            min_duration: Minimum duration for a segment
            max_gap: Maximum gap to group scenes together
        """
        # Detect scenes
        timestamps = self.detect_scenes(video_path)

        if len(timestamps) < 2:
            print("Not enough scene changes detected. Try adjusting --threshold.")
            return

        # Group into segments
        segments = self.group_scenes(timestamps, min_duration, max_gap)

        if not segments:
            print(f"\nNo segments found with minimum duration of {min_duration}s")
            print("Try lowering --min-duration or --max-gap")
            return

        print(f"\nGrouped into {len(segments)} segments:")
        for i, (start, end) in enumerate(segments, 1):
            print(f"  {i}. {start:.1f}s - {end:.1f}s ({end-start:.1f}s)")

        # Clip video
        self.clip_video(video_path, segments, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Simple comedy clipper using scene detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python clipper_simple.py standup_show.mp4

  # Custom sensitivity
  python clipper_simple.py show.mp4 --threshold 0.4

  # Custom output directory
  python clipper_simple.py show.mp4 -o clips/

  # Adjust minimum duration
  python clipper_simple.py show.mp4 -m 60
        """
    )

    parser.add_argument('video', help='Input video file')
    parser.add_argument('-o', '--output', help='Output directory for clips')
    parser.add_argument('-m', '--min-duration', type=float, default=30.0,
                       help='Minimum duration for a segment in seconds (default: 30)')
    parser.add_argument('-g', '--max-gap', type=float, default=5.0,
                       help='Maximum gap to group scenes together in seconds (default: 5)')
    parser.add_argument('-t', '--threshold', type=float, default=0.3,
                       help='Scene detection threshold 0-1, lower=more sensitive (default: 0.3)')

    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"Error: Video file not found: {args.video}")
        sys.exit(1)

    try:
        clipper = SimpleComedyClipper(scene_threshold=args.threshold)
        clipper.process_video(
            args.video,
            output_dir=args.output,
            min_duration=args.min_duration,
            max_gap=args.max_gap
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
