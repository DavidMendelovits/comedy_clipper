"""Core utilities for the Comedy Clipper backend."""

from .cache_manager import CacheManager, DetectionCache, DetectionFrame
from .video_io import VideoInfo, get_video_info, load_video_opencv, probe_video_ffmpeg, format_duration
from .ffmpeg_utils import clip_video, clip_video_batch, extract_audio, concat_videos, FFmpegError
from .progress import ProgressReporter, SilentProgressReporter

__all__ = [
    # Cache management
    'CacheManager',
    'DetectionCache',
    'DetectionFrame',
    # Video I/O
    'VideoInfo',
    'get_video_info',
    'load_video_opencv',
    'probe_video_ffmpeg',
    'format_duration',
    # FFmpeg operations
    'clip_video',
    'clip_video_batch',
    'extract_audio',
    'concat_videos',
    'FFmpegError',
    # Progress reporting
    'ProgressReporter',
    'SilentProgressReporter',
]
