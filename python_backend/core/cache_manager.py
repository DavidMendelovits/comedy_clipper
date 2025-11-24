"""
Detection Cache Manager
Caches pose/face detection results to speed up parameter tuning
"""

import hashlib
import json
import os
import pickle
import shutil
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np


@dataclass
class DetectionFrame:
    """Single frame detection data"""
    frame_num: int
    timestamp: float
    face_count: int
    pose_count: int
    yolo_count: int
    person_count: int
    positions: List[float]  # List of x positions for detected persons
    blur_score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DetectionFrame':
        return cls(**data)


@dataclass
class DetectionCache:
    """Complete detection data for a video"""
    video_path: str
    video_hash: str
    config_hash: str
    fps: float
    frame_count: int
    duration: float
    width: int
    height: int
    detection_method: str
    model_version: str
    created_at: float
    frames: List[DetectionFrame] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'video_path': self.video_path,
            'video_hash': self.video_hash,
            'config_hash': self.config_hash,
            'fps': self.fps,
            'frame_count': self.frame_count,
            'duration': self.duration,
            'width': self.width,
            'height': self.height,
            'detection_method': self.detection_method,
            'model_version': self.model_version,
            'created_at': self.created_at,
            'frames': [f.to_dict() for f in self.frames],
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DetectionCache':
        frames = [DetectionFrame.from_dict(f) for f in data.pop('frames', [])]
        return cls(**data, frames=frames)


class CacheManager:
    """Manages detection result caching"""

    CACHE_VERSION = "1.0"
    MAX_CACHE_SIZE_GB = 10.0

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize cache manager

        Args:
            cache_dir: Custom cache directory. Defaults to ~/.comedy_clipper/cache
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".comedy_clipper" / "cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Metadata file tracks all cached items
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load cache metadata: {e}")
                return {'version': self.CACHE_VERSION, 'entries': {}}
        return {'version': self.CACHE_VERSION, 'entries': {}}

    def _save_metadata(self):
        """Save cache metadata"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save cache metadata: {e}")

    def _compute_video_hash(self, video_path: str) -> str:
        """
        Compute hash of video file
        Uses file size + first/last 64KB to avoid reading entire file
        """
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        hasher = hashlib.sha256()

        # Add file size
        file_size = path.stat().st_size
        hasher.update(str(file_size).encode())

        # Add modification time
        mtime = path.stat().st_mtime
        hasher.update(str(mtime).encode())

        # Add first 64KB
        with open(video_path, 'rb') as f:
            hasher.update(f.read(65536))

            # Add last 64KB if file is large enough
            if file_size > 131072:
                f.seek(-65536, 2)
                hasher.update(f.read(65536))

        return hasher.hexdigest()

    def _compute_config_hash(self, config: Dict[str, Any]) -> str:
        """
        Compute hash of detection configuration
        Only includes parameters that affect detection results
        """
        # Extract only detection-relevant parameters
        detection_params = {
            'detection_mode': config.get('detection_mode'),
            'yolo_model': config.get('yolo_detection', {}).get('model'),
            'yolo_confidence': config.get('yolo_detection', {}).get('confidence'),
            'face_confidence': config.get('mediapipe_detection', {}).get('face_confidence'),
            'pose_model_complexity': config.get('mediapipe_detection', {}).get('model_complexity'),
            'sample_rate': config.get('sample_rate'),
            'zone_boundaries': config.get('zone_crossing', {}).get('boundaries'),
        }

        # Sort keys for consistent hashing
        config_str = json.dumps(detection_params, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]

    def get_cache_key(self, video_path: str, config: Dict[str, Any]) -> str:
        """Generate cache key from video and config"""
        video_hash = self._compute_video_hash(video_path)
        config_hash = self._compute_config_hash(config)
        return f"{video_hash}_{config_hash}"

    def has_cache(self, video_path: str, config: Dict[str, Any]) -> bool:
        """Check if cache exists for video + config"""
        cache_key = self.get_cache_key(video_path, config)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        return cache_file.exists()

    def save_cache(self, detection_data: DetectionCache) -> bool:
        """
        Save detection data to cache

        Args:
            detection_data: DetectionCache object to save

        Returns:
            True if saved successfully
        """
        try:
            cache_key = f"{detection_data.video_hash}_{detection_data.config_hash}"
            cache_file = self.cache_dir / f"{cache_key}.pkl"

            # Save detection data as pickle (faster than JSON for numpy arrays)
            with open(cache_file, 'wb') as f:
                pickle.dump(detection_data, f, protocol=pickle.HIGHEST_PROTOCOL)

            # Update metadata
            self.metadata['entries'][cache_key] = {
                'video_path': detection_data.video_path,
                'video_hash': detection_data.video_hash,
                'config_hash': detection_data.config_hash,
                'created_at': detection_data.created_at,
                'last_accessed': time.time(),
                'file_size': cache_file.stat().st_size,
                'detection_method': detection_data.detection_method,
                'frame_count': detection_data.frame_count,
            }
            self._save_metadata()

            # Check cache size and cleanup if needed
            self._cleanup_if_needed()

            print(f"[CACHE] Saved detection data: {cache_key}")
            return True

        except Exception as e:
            print(f"[CACHE] Error saving cache: {e}")
            return False

    def load_cache(self, video_path: str, config: Dict[str, Any]) -> Optional[DetectionCache]:
        """
        Load cached detection data

        Args:
            video_path: Path to video file
            config: Detection configuration

        Returns:
            DetectionCache object or None if not found
        """
        try:
            cache_key = self.get_cache_key(video_path, config)
            cache_file = self.cache_dir / f"{cache_key}.pkl"

            if not cache_file.exists():
                print(f"[CACHE] No cache found for: {cache_key}")
                return None

            # Load detection data
            with open(cache_file, 'rb') as f:
                detection_data = pickle.load(f)

            # Update last accessed time
            if cache_key in self.metadata['entries']:
                self.metadata['entries'][cache_key]['last_accessed'] = time.time()
                self._save_metadata()

            print(f"[CACHE] Loaded detection data: {cache_key} ({len(detection_data.frames)} frames)")
            return detection_data

        except Exception as e:
            print(f"[CACHE] Error loading cache: {e}")
            return None

    def delete_cache(self, cache_key: str) -> bool:
        """Delete a specific cache entry"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            if cache_file.exists():
                cache_file.unlink()

            if cache_key in self.metadata['entries']:
                del self.metadata['entries'][cache_key]
                self._save_metadata()

            print(f"[CACHE] Deleted: {cache_key}")
            return True

        except Exception as e:
            print(f"[CACHE] Error deleting cache: {e}")
            return False

    def clear_all(self) -> bool:
        """Clear all cached data"""
        try:
            # Remove all .pkl files
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()

            # Reset metadata
            self.metadata = {'version': self.CACHE_VERSION, 'entries': {}}
            self._save_metadata()

            print("[CACHE] Cleared all cache data")
            return True

        except Exception as e:
            print(f"[CACHE] Error clearing cache: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_size = 0
        entry_count = len(self.metadata['entries'])

        for cache_file in self.cache_dir.glob("*.pkl"):
            total_size += cache_file.stat().st_size

        total_size_mb = total_size / (1024 * 1024)
        total_size_gb = total_size / (1024 * 1024 * 1024)

        return {
            'entry_count': entry_count,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size_mb, 2),
            'total_size_gb': round(total_size_gb, 3),
            'cache_dir': str(self.cache_dir),
            'entries': self.metadata['entries']
        }

    def _cleanup_if_needed(self):
        """Remove oldest entries if cache exceeds size limit"""
        stats = self.get_cache_stats()

        if stats['total_size_gb'] > self.MAX_CACHE_SIZE_GB:
            print(f"[CACHE] Cache size ({stats['total_size_gb']:.2f}GB) exceeds limit ({self.MAX_CACHE_SIZE_GB}GB)")

            # Sort entries by last accessed time
            entries = sorted(
                self.metadata['entries'].items(),
                key=lambda x: x[1].get('last_accessed', 0)
            )

            # Remove oldest 25% of entries
            remove_count = max(1, len(entries) // 4)
            for cache_key, _ in entries[:remove_count]:
                self.delete_cache(cache_key)

            print(f"[CACHE] Removed {remove_count} oldest entries")

    def get_cached_videos(self) -> List[Dict[str, Any]]:
        """Get list of all cached videos"""
        videos = []
        for cache_key, entry in self.metadata['entries'].items():
            videos.append({
                'cache_key': cache_key,
                'video_path': entry['video_path'],
                'detection_method': entry.get('detection_method', 'unknown'),
                'frame_count': entry.get('frame_count', 0),
                'created_at': entry['created_at'],
                'last_accessed': entry.get('last_accessed', entry['created_at']),
                'file_size_mb': round(entry.get('file_size', 0) / (1024 * 1024), 2),
            })

        # Sort by last accessed (most recent first)
        videos.sort(key=lambda x: x['last_accessed'], reverse=True)
        return videos


def create_detection_cache(
    video_path: str,
    config: Dict[str, Any],
    fps: float,
    frame_count: int,
    duration: float,
    width: int,
    height: int,
    detection_method: str,
    model_version: str = "1.0"
) -> DetectionCache:
    """Helper function to create a new DetectionCache object"""
    cache_manager = CacheManager()
    video_hash = cache_manager._compute_video_hash(video_path)
    config_hash = cache_manager._compute_config_hash(config)

    return DetectionCache(
        video_path=video_path,
        video_hash=video_hash,
        config_hash=config_hash,
        fps=fps,
        frame_count=frame_count,
        duration=duration,
        width=width,
        height=height,
        detection_method=detection_method,
        model_version=model_version,
        created_at=time.time(),
        frames=[],
        metadata={}
    )
