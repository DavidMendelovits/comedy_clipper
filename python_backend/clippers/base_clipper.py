"""
Base Clipper Class
Abstract base class for all comedy clippers with common functionality
"""

import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from python_backend.core import (
    CacheManager,
    DetectionCache,
    create_detection_cache,
    VideoInfo,
    get_video_info,
    clip_video,
    clip_video_batch,
    ProgressReporter,
    format_duration
)
from python_backend.filters.segment_filter import SegmentFilter, FilterConfig


class BaseClipper(ABC):
    """
    Abstract base class for all comedy clippers.
    Handles common operations like caching, filtering, clipping, and progress reporting.
    """

    def __init__(
        self,
        config: Any,
        mode: str = None,
        debug: bool = False,
        use_cache: bool = True
    ):
        """
        Initialize base clipper.

        Args:
            config: Loaded configuration object
            mode: Detection mode (implementation-specific)
            debug: Whether to export debug frames
            use_cache: Whether to use cached detection data
        """
        self.config = config
        self.mode = mode or config.get("detection_mode", "multimodal")
        self.debug = debug or config.get("debug.export_frames", False)
        self.use_cache = use_cache

        # Initialize cache manager
        self.cache_manager = CacheManager() if use_cache else None

        # Progress reporter
        self.progress = ProgressReporter()

        # Debug output directory (set when debug frames are exported)
        self.debug_dir = None

        # Initialize detectors (subclass responsibility)
        self._init_detectors()

        print(f"Initialized {self.__class__.__name__} in '{self.mode}' mode"
              f"{' (caching enabled)' if use_cache else ''}")

    @abstractmethod
    def _init_detectors(self):
        """Initialize detection models/pipelines (implemented by subclasses)"""
        pass

    @abstractmethod
    def detect_segments(
        self,
        video_path: str,
        json_output: bool = False
    ) -> List[Tuple[float, float]]:
        """
        Detect segments using the clipper's detection method.

        Args:
            video_path: Path to video file
            json_output: Whether to suppress print output

        Returns:
            List of (start_time, end_time) tuples in seconds
        """
        pass

    def load_video_info(self, video_path: str) -> VideoInfo:
        """
        Load video metadata using core utilities.

        Args:
            video_path: Path to video file

        Returns:
            VideoInfo object with video metadata
        """
        return get_video_info(video_path)

    def load_from_cache(
        self,
        video_path: str,
        config_dict: Dict[str, Any]
    ) -> Optional[DetectionCache]:
        """
        Try to load detection data from cache.

        Args:
            video_path: Path to video file
            config_dict: Configuration dictionary for cache key

        Returns:
            DetectionCache if found, None otherwise
        """
        if not self.use_cache or not self.cache_manager:
            return None

        self.progress.log("Checking for cached detection data...")
        detection_cache = self.cache_manager.load_cache(video_path, config_dict)

        if detection_cache:
            self.progress.log(
                f"✓ Found cached data with {len(detection_cache.frames)} frames"
            )
            self.progress.log(
                f"Cache created: {datetime.fromtimestamp(detection_cache.created_at).strftime('%Y-%m-%d %H:%M:%S')}"
            )
            self.progress.log(f"Detection method: {detection_cache.detection_method}")
        else:
            self.progress.log("No cache found, will process video and cache results")

        return detection_cache

    def save_to_cache(
        self,
        detection_cache: DetectionCache
    ) -> bool:
        """
        Save detection data to cache.

        Args:
            detection_cache: Detection data to cache

        Returns:
            True if saved successfully, False otherwise
        """
        if not self.use_cache or not self.cache_manager:
            return False

        self.progress.log("Saving detection data to cache...")
        success = self.cache_manager.save_cache(detection_cache)

        if success:
            self.progress.log(f"✓ Saved {len(detection_cache.frames)} frames to cache")
        else:
            self.progress.log("✗ Failed to save cache")

        return success

    def filter_segments(
        self,
        segments: List[Tuple[float, float]],
        video_duration: Optional[float] = None,
        json_output: bool = False
    ) -> List[Tuple[float, float]]:
        """
        Filter segments using configuration rules.

        Args:
            segments: List of (start, end) tuples
            video_duration: Total video duration for clamping buffers
            json_output: Whether to suppress print output

        Returns:
            Filtered list of (start, end) tuples
        """
        if not json_output:
            self.progress.log(f"Filtering segments (found {len(segments)} raw segments)")

        # Create filter config from clipper config
        filter_config = FilterConfig(
            min_duration=self.config.get("filtering.min_duration", 180.0),
            max_duration=self.config.get("filtering.max_duration", 1800.0),
            merge_close_segments=self.config.get("filtering.merge_close_segments", True),
            merge_threshold=self.config.get("filtering.min_gap", 10.0),
            buffer_before_start=self.config.get("filtering.buffer_before_start", 10.0),
            buffer_after_end=self.config.get("filtering.buffer_after_end", 10.0),
        )

        # Create segment filter and apply
        segment_filter = SegmentFilter(filter_config)
        filtered = segment_filter.filter(segments, video_duration)

        if not json_output and filtered:
            self.progress.log(f"Filtered to {len(filtered)} segments:")
            for i, (start, end) in enumerate(filtered, 1):
                duration_str = format_duration(end - start)
                self.progress.log(
                    f"  {i}. {format_duration(start)} - {format_duration(end)} ({duration_str})"
                )

        return filtered

    def clip_video(
        self,
        video_path: str,
        segments: List[Tuple[float, float]],
        output_dir: str = None,
        json_output: bool = False
    ) -> List[str]:
        """
        Clip video using FFmpeg.

        Args:
            video_path: Path to input video
            segments: List of (start, end) tuples to clip
            output_dir: Output directory (default: video directory)
            json_output: Whether to suppress print output

        Returns:
            List of paths to created clip files
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_name = Path(video_path).stem

        if output_dir is None:
            base_dir = Path(video_path).parent
        else:
            base_dir = Path(output_dir)

        clips_suffix = self.config.get("output.clips_folder_suffix", "clips")
        output_dir = base_dir / f"{video_name}_{clips_suffix}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        if not json_output:
            self.progress.log(f"Creating {len(segments)} video clips in {output_dir}")

        # Get FFmpeg settings from config
        preset = self.config.get("output.ffmpeg.preset", "fast")
        crf = self.config.get("output.ffmpeg.crf", 23)
        audio_bitrate = self.config.get("output.ffmpeg.audio_bitrate", "128k")

        clip_files = []

        for i, (start, end) in enumerate(segments, 1):
            duration = end - start
            minutes = int(duration / 60)
            seconds = int(duration % 60)

            output_path = output_dir / f"{video_name}_clip{i:02d}_{minutes}m{seconds}s.mp4"

            # Emit progress
            progress_pct = int((i / len(segments)) * 100)
            self.progress.emit(
                "clipping",
                progress_pct,
                current=i,
                total=len(segments),
                message=f"Creating clip {i}/{len(segments)}"
            )

            if not json_output:
                duration_str = format_duration(duration)
                self.progress.log(
                    f"  [{i}/{len(segments)}] {format_duration(start)} - {format_duration(end)} ({duration_str})"
                )

            # Use core clip_video utility
            try:
                clip_video(
                    input_path=video_path,
                    output_path=str(output_path),
                    start_time=start,
                    end_time=end,
                    preset=preset,
                    crf=crf,
                    audio_bitrate=audio_bitrate
                )
                clip_files.append(str(output_path))
            except Exception as e:
                if not json_output:
                    self.progress.error(f"Failed to create clip {i}: {e}")

        if not json_output:
            self.progress.log(f"Done! {len(clip_files)} clips saved to: {output_dir}")

        return clip_files

    def process_video(
        self,
        video_path: str,
        output_dir: str = None,
        json_output: bool = False
    ) -> dict:
        """
        Complete pipeline: detect segments, filter, and clip.

        Args:
            video_path: Path to input video
            output_dir: Output directory for clips
            json_output: Whether to suppress print output

        Returns:
            Dictionary with processing results:
                - success: bool
                - segments_detected: list of (start, end) tuples
                - segments_filtered: list of (start, end) tuples
                - clips: list of clip file paths
                - output_dir: path to output directory
                - debug_dir: path to debug directory (if debug enabled)
                - error: error message if failed
        """
        if not json_output:
            self.progress.log("Starting video processing")

        result = {
            'success': False,
            'segments_detected': [],
            'segments_filtered': [],
            'clips': [],
            'output_dir': None,
            'debug_dir': None,
            'error': None
        }

        try:
            # Phase 1: Detection
            self.progress.emit("detection", 0, message="Starting detection")
            segments = self.detect_segments(video_path, json_output)

            # Convert to simple tuples (in case subclass returns 4-tuples)
            result['segments_detected'] = [
                (float(seg[0]), float(seg[1])) for seg in segments
            ]

            if not segments:
                if not json_output:
                    self.progress.log("No segments detected")
                result['error'] = 'No segments detected'
                return result

            # Phase 2: Filtering
            self.progress.emit("filtering", 0, message="Filtering segments")
            video_info = self.load_video_info(video_path)
            filtered = self.filter_segments(
                result['segments_detected'],
                video_duration=video_info.duration,
                json_output=json_output
            )
            result['segments_filtered'] = filtered

            if not filtered:
                min_dur = self.config.get("filtering.min_duration", 180.0)
                if not json_output:
                    self.progress.log(
                        f"No segments passed filtering (min duration: {format_duration(min_dur)})"
                    )
                    self.progress.log(f"Detected {len(segments)} segments before filtering:")
                    for i, (start, end) in enumerate(result['segments_detected'], 1):
                        duration_str = format_duration(end - start)
                        self.progress.log(f"  {i}. {format_duration(start)} - {format_duration(end)} ({duration_str})")

                result['error'] = f'No segments passed filtering (min duration: {min_dur}s)'
                result['success'] = True  # Processing completed, just no clips
                return result

            # Phase 3: Clipping
            self.progress.emit("clipping", 0, message="Creating clips")
            clips = self.clip_video(video_path, filtered, output_dir, json_output)
            result['clips'] = clips
            result['output_dir'] = str(Path(clips[0]).parent) if clips else None
            result['debug_dir'] = self.debug_dir
            result['success'] = True

            if not json_output:
                self.progress.complete(f"Processing complete - {len(clips)} clips created")

            return result

        except Exception as e:
            result['error'] = str(e)
            if not json_output:
                self.progress.error(f"Processing failed: {e}")
                import traceback
                traceback.print_exc()
            return result
