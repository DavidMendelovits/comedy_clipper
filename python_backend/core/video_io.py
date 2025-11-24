"""
Video I/O Utilities
Common video reading, probing, and metadata extraction functions
"""

import subprocess
import json
from typing import Tuple, Optional
import cv2


class VideoInfo:
    """Video metadata container"""

    def __init__(self, path: str, fps: float, frame_count: int, duration: float,
                 width: int, height: int):
        self.path = path
        self.fps = fps
        self.frame_count = frame_count
        self.duration = duration
        self.width = width
        self.height = height

    def __repr__(self):
        return (f"VideoInfo(path={self.path}, fps={self.fps:.2f}, "
                f"frames={self.frame_count}, duration={self.duration:.1f}s, "
                f"{self.width}x{self.height})")


def probe_video_ffmpeg(video_path: str) -> Optional[VideoInfo]:
    """
    Probe video file using FFmpeg to get accurate metadata

    Args:
        video_path: Path to video file

    Returns:
        VideoInfo object or None if probe fails
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        # Find video stream
        video_stream = None
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                video_stream = stream
                break

        if not video_stream:
            return None

        # Extract metadata
        fps_str = video_stream.get('r_frame_rate', '30/1')
        if '/' in fps_str:
            num, den = map(int, fps_str.split('/'))
            fps = num / den if den != 0 else 30.0
        else:
            fps = float(fps_str)

        duration = float(data.get('format', {}).get('duration', 0))
        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
        frame_count = int(video_stream.get('nb_frames', 0))

        # Calculate frame count from duration if not available
        if frame_count == 0 and duration > 0:
            frame_count = int(duration * fps)

        return VideoInfo(video_path, fps, frame_count, duration, width, height)

    except Exception as e:
        print(f"Error probing video with FFmpeg: {e}")
        return None


def load_video_opencv(video_path: str) -> Tuple[Optional[cv2.VideoCapture], Optional[VideoInfo]]:
    """
    Load video using OpenCV and extract metadata

    Args:
        video_path: Path to video file

    Returns:
        Tuple of (VideoCapture, VideoInfo) or (None, None) on error
    """
    try:
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            return None, None

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0

        info = VideoInfo(video_path, fps, frame_count, duration, width, height)

        return cap, info

    except Exception as e:
        print(f"Error loading video with OpenCV: {e}")
        return None, None


def get_video_info(video_path: str, prefer_ffmpeg: bool = True) -> Optional[VideoInfo]:
    """
    Get video information, trying FFmpeg first (more accurate) then OpenCV

    Args:
        video_path: Path to video file
        prefer_ffmpeg: Try FFmpeg first (recommended for accuracy)

    Returns:
        VideoInfo object or None if both methods fail
    """
    if prefer_ffmpeg:
        info = probe_video_ffmpeg(video_path)
        if info:
            return info

        # Fallback to OpenCV
        print("FFmpeg probe failed, trying OpenCV...")
        cap, info = load_video_opencv(video_path)
        if cap:
            cap.release()
        return info
    else:
        cap, info = load_video_opencv(video_path)
        if cap:
            cap.release()
        return info


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "1h 23m 45s" or "3m 30s"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)
