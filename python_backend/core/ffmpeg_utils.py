"""
FFmpeg Utilities
Common FFmpeg operations for video clipping and encoding
"""

import subprocess
import os
from pathlib import Path
from typing import List, Tuple, Optional


class FFmpegError(Exception):
    """FFmpeg operation error"""
    pass


def clip_video(
    input_path: str,
    output_path: str,
    start_time: float,
    end_time: float,
    preset: str = "fast",
    crf: int = 23,
    audio_bitrate: str = "128k",
    verbose: bool = False
) -> bool:
    """
    Clip video segment using FFmpeg

    Args:
        input_path: Input video path
        output_path: Output video path
        start_time: Start time in seconds
        end_time: End time in seconds
        preset: FFmpeg encoding preset (ultrafast, fast, medium, slow, veryslow)
        crf: Constant Rate Factor (18-28, lower = better quality)
        audio_bitrate: Audio bitrate (e.g., "128k", "192k")
        verbose: Show FFmpeg output

    Returns:
        True if successful, False otherwise
    """
    try:
        duration = end_time - start_time

        if duration <= 0:
            print(f"Invalid duration: {duration}s (start={start_time}, end={end_time})")
            return False

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-ss', str(start_time),  # Seek to start time
            '-i', input_path,
            '-t', str(duration),  # Duration
            '-c:v', 'libx264',  # Video codec
            '-preset', preset,
            '-crf', str(crf),
            '-c:a', 'aac',  # Audio codec
            '-b:a', audio_bitrate,
            '-movflags', '+faststart',  # Enable streaming
            output_path
        ]

        if verbose:
            print(f"FFmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True)
        else:
            result = subprocess.run(cmd, capture_output=True, check=True)

        return result.returncode == 0

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error clipping video: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"FFmpeg stderr: {e.stderr.decode()}")
        return False
    except Exception as e:
        print(f"Error clipping video: {e}")
        return False


def clip_video_batch(
    input_path: str,
    segments: List[Tuple[float, float]],
    output_dir: str,
    base_name: Optional[str] = None,
    **kwargs
) -> List[str]:
    """
    Clip multiple segments from a video

    Args:
        input_path: Input video path
        segments: List of (start, end) tuples in seconds
        output_dir: Output directory for clips
        base_name: Base name for output files (default: input filename)
        **kwargs: Additional arguments passed to clip_video()

    Returns:
        List of successfully created clip paths
    """
    os.makedirs(output_dir, exist_ok=True)

    if base_name is None:
        base_name = Path(input_path).stem

    created_clips = []

    for i, (start, end) in enumerate(segments, 1):
        output_path = os.path.join(output_dir, f"{base_name}_clip_{i:02d}.mp4")

        print(f"Creating clip {i}/{len(segments)}: {start:.1f}s - {end:.1f}s")

        success = clip_video(input_path, output_path, start, end, **kwargs)

        if success:
            created_clips.append(output_path)
            print(f"  ✓ Created: {output_path}")
        else:
            print(f"  ✗ Failed to create clip {i}")

    return created_clips


def extract_audio(
    video_path: str,
    output_path: str,
    format: str = "wav",
    sample_rate: int = 16000,
    channels: int = 1
) -> bool:
    """
    Extract audio from video

    Args:
        video_path: Input video path
        output_path: Output audio path
        format: Audio format (wav, mp3, aac)
        sample_rate: Sample rate in Hz
        channels: Number of audio channels (1=mono, 2=stereo)

    Returns:
        True if successful
    """
    try:
        cmd = [
            'ffmpeg',
            '-y',
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le' if format == 'wav' else format,
            '-ar', str(sample_rate),
            '-ac', str(channels),
            output_path
        ]

        subprocess.run(cmd, capture_output=True, check=True)
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e}")
        return False


def concat_videos(
    input_paths: List[str],
    output_path: str,
    verbose: bool = False
) -> bool:
    """
    Concatenate multiple video files

    Args:
        input_paths: List of input video paths
        output_path: Output video path
        verbose: Show FFmpeg output

    Returns:
        True if successful
    """
    if not input_paths:
        return False

    try:
        # Create concat file
        concat_file = Path(output_path).parent / "concat_list.txt"

        with open(concat_file, 'w') as f:
            for path in input_paths:
                # FFmpeg concat requires absolute paths
                abs_path = os.path.abspath(path)
                f.write(f"file '{abs_path}'\n")

        cmd = [
            'ffmpeg',
            '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_file),
            '-c', 'copy',
            output_path
        ]

        if verbose:
            subprocess.run(cmd, check=True)
        else:
            subprocess.run(cmd, capture_output=True, check=True)

        # Cleanup concat file
        concat_file.unlink()

        return True

    except Exception as e:
        print(f"Error concatenating videos: {e}")
        return False


def get_video_duration_ffmpeg(video_path: str) -> Optional[float]:
    """
    Get video duration using FFmpeg

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds or None if failed
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())

    except Exception:
        return None
