"""Unit tests for segment filtering functionality"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from python_backend.filters.segment_filter import (
    SegmentFilter,
    FilterConfig,
    filter_segments,
    format_segment
)


class TestFilterConfig(unittest.TestCase):
    """Test FilterConfig dataclass"""

    def test_default_config(self):
        """Test default configuration values"""
        config = FilterConfig()
        self.assertEqual(config.min_duration, 180.0)
        self.assertEqual(config.max_duration, 1800.0)
        self.assertTrue(config.merge_close_segments)
        self.assertEqual(config.merge_threshold, 10.0)
        self.assertEqual(config.buffer_before_start, 10.0)
        self.assertEqual(config.buffer_after_end, 10.0)

    def test_custom_config(self):
        """Test custom configuration values"""
        config = FilterConfig(
            min_duration=120.0,
            max_duration=900.0,
            merge_threshold=5.0
        )
        self.assertEqual(config.min_duration, 120.0)
        self.assertEqual(config.max_duration, 900.0)
        self.assertEqual(config.merge_threshold, 5.0)

    def test_from_dict(self):
        """Test creating config from dictionary"""
        config_dict = {
            'min_duration': 60.0,
            'max_duration': 600.0,
            'merge_threshold': 3.0
        }
        config = FilterConfig.from_dict(config_dict)
        self.assertEqual(config.min_duration, 60.0)
        self.assertEqual(config.max_duration, 600.0)
        self.assertEqual(config.merge_threshold, 3.0)


class TestSegmentFilter(unittest.TestCase):
    """Test SegmentFilter class"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = FilterConfig(
            min_duration=60.0,  # 1 minute
            max_duration=600.0,  # 10 minutes
            merge_threshold=5.0,  # 5 seconds
            buffer_before_start=2.0,
            buffer_after_end=2.0
        )
        self.filter = SegmentFilter(self.config)

    def test_filter_short_segments(self):
        """Test filtering out segments that are too short"""
        segments = [
            (0.0, 30.0),    # 30s - too short
            (40.0, 150.0),  # 110s - long enough
            (160.0, 180.0), # 20s - too short
        ]
        filtered = self.filter.filter(segments)

        # Only the middle segment should pass
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0][0], 40.0 - 2.0)  # With buffer before
        self.assertEqual(filtered[0][1], 150.0 + 2.0)  # With buffer after

    def test_filter_long_segments(self):
        """Test filtering out segments that are too long"""
        segments = [
            (0.0, 100.0),   # 100s - ok
            (200.0, 900.0), # 700s - too long
            (1000.0, 1300.0), # 300s - ok
        ]
        filtered = self.filter.filter(segments)

        # First and third segments should pass
        self.assertEqual(len(filtered), 2)

    def test_merge_close_segments(self):
        """Test merging segments that are close together"""
        segments = [
            (0.0, 100.0),   # 100s
            (103.0, 200.0), # 97s, gap = 3s < 5s threshold
            (210.0, 300.0), # 90s, gap = 10s > 5s threshold
        ]
        filtered = self.filter.filter(segments)

        # First two should be merged, third separate
        self.assertEqual(len(filtered), 2)
        # First merged segment (clamped to 0 at start)
        self.assertEqual(filtered[0][0], 0.0)  # Clamped to 0 (can't be negative)
        self.assertAlmostEqual(filtered[0][1], 200.0 + 2.0)  # Merged end + buffer

    def test_apply_buffers(self):
        """Test that buffers are applied correctly"""
        segments = [(100.0, 200.0)]
        filtered = self.filter.filter(segments)

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0][0], 98.0)  # 100 - 2 (buffer_before)
        self.assertEqual(filtered[0][1], 202.0)  # 200 + 2 (buffer_after)

    def test_clamp_to_video_duration(self):
        """Test that buffers are clamped to video duration"""
        segments = [(0.0, 100.0), (500.0, 599.0)]
        video_duration = 600.0

        filtered = self.filter.filter(segments, video_duration)

        # First segment: buffer_before should be clamped to 0
        self.assertEqual(filtered[0][0], 0.0)  # Can't go below 0

        # Second segment: buffer_after (599 + 2 = 601) should be clamped to duration
        self.assertEqual(filtered[1][1], 600.0)  # Can't exceed duration

    def test_get_stats(self):
        """Test segment statistics calculation"""
        segments = [
            (0.0, 100.0),   # 100s
            (200.0, 350.0), # 150s
            (400.0, 600.0), # 200s
        ]

        stats = self.filter.get_stats(segments)

        self.assertEqual(stats['count'], 3)
        self.assertEqual(stats['total_duration'], 450.0)
        self.assertEqual(stats['avg_duration'], 150.0)
        self.assertEqual(stats['min_duration'], 100.0)
        self.assertEqual(stats['max_duration'], 200.0)
        self.assertEqual(stats['durations'], [100.0, 150.0, 200.0])

    def test_get_stats_empty(self):
        """Test statistics for empty segment list"""
        stats = self.filter.get_stats([])

        self.assertEqual(stats['count'], 0)
        self.assertEqual(stats['total_duration'], 0.0)


class TestFilterSegmentsFunction(unittest.TestCase):
    """Test convenience filter_segments function"""

    def test_filter_segments_function(self):
        """Test the convenience function"""
        segments = [
            (0.0, 30.0),    # Too short (< 60s)
            (40.0, 150.0),  # Long enough
        ]

        filtered = filter_segments(
            segments,
            min_duration=60.0,
            max_duration=600.0,
            merge_threshold=5.0,
            buffer_before=2.0,
            buffer_after=2.0
        )

        self.assertEqual(len(filtered), 1)
        self.assertAlmostEqual(filtered[0][0], 38.0)  # 40 - 2
        self.assertAlmostEqual(filtered[0][1], 152.0)  # 150 + 2


class TestFormatSegment(unittest.TestCase):
    """Test segment formatting function"""

    def test_format_segment(self):
        """Test formatting a segment as human-readable string"""
        result = format_segment(0.0, 185.0)  # 3m 5s
        self.assertIn("0:00:00", result)  # Start time
        self.assertIn("0:03:05", result)  # End time
        self.assertIn("3m", result)  # Duration minutes
        self.assertIn("5s", result)  # Duration seconds

    def test_format_segment_hours(self):
        """Test formatting with hours"""
        result = format_segment(0.0, 3725.0)  # 1h 2m 5s
        self.assertIn("1:02:05", result)  # End time with hour
        self.assertIn("1h", result)  # Duration hours

    def test_format_segment_zero_duration(self):
        """Test formatting segment with zero duration"""
        result = format_segment(100.0, 100.0)
        self.assertIn("0s", result)  # Should still show 0s


if __name__ == '__main__':
    unittest.main()
