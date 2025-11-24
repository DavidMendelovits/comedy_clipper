"""
Segment Filtering
Common segment filtering logic extracted from multiple clippers
"""

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class FilterConfig:
    """Segment filtering configuration"""
    min_duration: float = 180.0  # 3 minutes
    max_duration: float = 1800.0  # 30 minutes
    merge_close_segments: bool = True
    merge_threshold: float = 10.0  # seconds
    buffer_before_start: float = 10.0  # seconds
    buffer_after_end: float = 10.0  # seconds

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'FilterConfig':
        """Create from configuration dictionary"""
        return cls(
            min_duration=config.get('min_duration', 180.0),
            max_duration=config.get('max_duration', 1800.0),
            merge_close_segments=config.get('merge_close_segments', True),
            merge_threshold=config.get('merge_threshold', 10.0),
            buffer_before_start=config.get('buffer_before_start', 10.0),
            buffer_after_end=config.get('buffer_after_end', 10.0),
        )


class SegmentFilter:
    """Filters video segments based on duration and merging rules"""

    def __init__(self, config: FilterConfig):
        """
        Initialize segment filter

        Args:
            config: Filter configuration
        """
        self.config = config

    def filter(
        self,
        segments: List[Tuple[float, float]],
        video_duration: Optional[float] = None
    ) -> List[Tuple[float, float]]:
        """
        Filter segments based on configuration

        Args:
            segments: List of (start, end) tuples in seconds
            video_duration: Total video duration (for clamping buffers)

        Returns:
            Filtered list of (start, end) tuples
        """
        if not segments:
            return []

        filtered = []

        for start, end in segments:
            duration = end - start

            # Skip segments that are too short or too long
            if duration < self.config.min_duration:
                continue
            if duration > self.config.max_duration:
                continue

            # Merge with previous segment if gap is small
            if filtered and self.config.merge_close_segments:
                prev_end = filtered[-1][1]
                gap = start - prev_end

                if gap < self.config.merge_threshold:
                    # Extend previous segment instead of adding new one
                    filtered[-1] = (filtered[-1][0], end)
                    continue

            # Add segment
            filtered.append((start, end))

        # Apply buffers to all segments
        buffered = []
        for start, end in filtered:
            buffered_start = max(0, start - self.config.buffer_before_start)
            buffered_end = end + self.config.buffer_after_end

            if video_duration is not None:
                buffered_end = min(video_duration, buffered_end)

            buffered.append((buffered_start, buffered_end))

        return buffered

    def get_stats(self, segments: List[Tuple[float, float]]) -> Dict[str, Any]:
        """
        Get statistics about segments

        Args:
            segments: List of (start, end) tuples

        Returns:
            Dictionary with segment statistics
        """
        if not segments:
            return {
                'count': 0,
                'total_duration': 0.0,
                'avg_duration': 0.0,
                'min_duration': 0.0,
                'max_duration': 0.0,
            }

        durations = [end - start for start, end in segments]
        total = sum(durations)

        return {
            'count': len(segments),
            'total_duration': total,
            'avg_duration': total / len(segments),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'durations': durations,
        }


def filter_segments(
    segments: List[Tuple[float, float]],
    min_duration: float = 180.0,
    max_duration: float = 1800.0,
    merge_threshold: float = 10.0,
    buffer_before: float = 10.0,
    buffer_after: float = 10.0,
    video_duration: Optional[float] = None
) -> List[Tuple[float, float]]:
    """
    Filter segments (convenience function)

    Args:
        segments: List of (start, end) tuples in seconds
        min_duration: Minimum segment duration
        max_duration: Maximum segment duration
        merge_threshold: Maximum gap to merge segments
        buffer_before: Seconds to add before segment start
        buffer_after: Seconds to add after segment end
        video_duration: Total video duration for clamping

    Returns:
        Filtered segments
    """
    config = FilterConfig(
        min_duration=min_duration,
        max_duration=max_duration,
        merge_close_segments=True,
        merge_threshold=merge_threshold,
        buffer_before_start=buffer_before,
        buffer_after_end=buffer_after
    )

    filter = SegmentFilter(config)
    return filter.filter(segments, video_duration)


def format_segment(start: float, end: float) -> str:
    """
    Format segment as human-readable string

    Args:
        start: Start time in seconds
        end: End time in seconds

    Returns:
        Formatted string like "1:23:45 - 2:34:56 (1h 11m 11s)"
    """
    def format_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}:{minutes:02d}:{secs:02d}"

    duration = end - start
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    secs = int(duration % 60)

    duration_str = []
    if hours > 0:
        duration_str.append(f"{hours}h")
    if minutes > 0:
        duration_str.append(f"{minutes}m")
    if secs > 0 or not duration_str:
        duration_str.append(f"{secs}s")

    return f"{format_time(start)} - {format_time(end)} ({' '.join(duration_str)})"
