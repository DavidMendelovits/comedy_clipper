"""
Scene Detector - FFmpeg-based scene change detection
Detects segments based on video scene changes
"""

from typing import List, Tuple, Optional
import subprocess


class SceneDetector:
    """FFmpeg-based scene change detector"""

    def __init__(self, config: any):
        """
        Initialize scene detector.

        Args:
            config: Configuration object
        """
        self.config = config
        self.threshold = config.get("scene_detection.threshold", 0.3)
        self.max_gap = config.get("scene_detection.max_gap", 5.0)
        self.min_duration = config.get("filtering.min_duration", 30.0)

        print(f"Scene detector initialized (threshold={self.threshold})")

    def detect_scenes(
        self,
        video_path: str
    ) -> List[Tuple[float, float]]:
        """
        Detect scene changes in video.

        Args:
            video_path: Path to video file

        Returns:
            List of (start_time, end_time) tuples for detected segments
        """
        print(f"Analyzing video for scene changes (threshold={self.threshold})...")

        # Run FFmpeg scene detection
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-filter:v', f"select='gt(scene,{self.threshold})',showinfo",
            '-f', 'null',
            '-'
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # Parse timestamps from output
        timestamps = [0.0]
        for line in result.stdout.split('\n'):
            if 'pts_time:' in line:
                try:
                    pts_time = line.split('pts_time:')[1].split()[0]
                    timestamps.append(float(pts_time))
                except (IndexError, ValueError):
                    continue

        timestamps.sort()
        print(f"Found {len(timestamps)} scene changes")

        # Group scenes into segments
        segments = self._group_scenes(timestamps)
        print(f"Detected {len(segments)} segments from scenes")

        return segments

    def _group_scenes(
        self,
        timestamps: List[float]
    ) -> List[Tuple[float, float]]:
        """
        Group scene timestamps into continuous segments.

        Args:
            timestamps: List of scene change timestamps

        Returns:
            List of (start, end) segment tuples
        """
        segments = []

        if len(timestamps) >= 2:
            current_start = timestamps[0]
            last_time = timestamps[0]

            for time in timestamps[1:]:
                gap = time - last_time

                # If gap is too large, end current segment and start new one
                if gap > self.max_gap:
                    duration = last_time - current_start
                    if duration >= self.min_duration:
                        segments.append((current_start, last_time))
                    current_start = time

                last_time = time

            # Add final segment
            duration = last_time - current_start
            if duration >= self.min_duration:
                segments.append((current_start, last_time))

        return segments
