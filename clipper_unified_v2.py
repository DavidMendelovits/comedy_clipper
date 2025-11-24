#!/usr/bin/env python3
"""
Unified Comedy Clipper - Refactored using BaseClipper architecture
Supports: speaker diarization, scene detection, pose detection, face+pose multi-modal

This version demonstrates the new modular architecture with:
- BaseClipper for common operations (caching, filtering, clipping, progress)
- Specialized detector modules (VisualDetector, YOLODetector, SceneDetector, DiarizationDetector)
- Dramatically reduced code duplication (~60% reduction from 1764 to ~700 lines)
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
from config_loader import load_config, ClipperConfig

# Add paths for new module imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "python_backend"))

from python_backend.clippers.base_clipper import BaseClipper
from python_backend.detectors import VisualDetector, YOLODetector, SceneDetector, DiarizationDetector
from python_backend.core import (
    CacheManager,
    DetectionCache,
    DetectionFrame,
    create_detection_cache,
    VideoInfo,
    get_video_info
)

# Optional imports
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

try:
    from filterpy.kalman import KalmanFilter
    KALMAN_AVAILABLE = True
except ImportError:
    KALMAN_AVAILABLE = False
    KalmanFilter = None


class KalmanPositionTracker:
    """Kalman filter for tracking person position over time"""

    def __init__(self, config: ClipperConfig):
        """Initialize Kalman filter from config"""
        if not KALMAN_AVAILABLE:
            raise ImportError("filterpy not installed. Run: pip install filterpy")

        self.kf = KalmanFilter(dim_x=2, dim_z=1)
        self.kf.F = np.array([[1., 1.], [0., 1.]])
        self.kf.H = np.array([[1., 0.]])

        measurement_noise = config.get("kalman_filter.measurement_noise", 5.0)
        self.kf.R = np.array([[measurement_noise]])

        process_noise = config.get("kalman_filter.process_noise", 1.0)
        self.kf.Q = np.array([[process_noise, 0.], [0., process_noise]])

        initial_cov = config.get("kalman_filter.initial_covariance", 10.0)
        self.kf.P *= initial_cov

        self.initialized = False

    def update(self, measurement: Optional[float]) -> float:
        """Update filter with new measurement"""
        if measurement is not None:
            if not self.initialized:
                self.kf.x = np.array([[measurement], [0.]])
                self.initialized = True
            else:
                self.kf.update(measurement)

        self.kf.predict()
        return float(self.kf.x[0])


class UnifiedClipper(BaseClipper):
    """
    Unified clipper supporting multiple detection methods.
    Refactored to use BaseClipper architecture with specialized detector modules.
    """

    def _init_detectors(self):
        """Initialize required detectors based on mode"""
        # Route to appropriate detector based on mode
        if self.mode == "scene":
            self.scene_detector = SceneDetector(self.config)
            print(f"Initialized SceneDetector")

        elif self.mode == "diarization":
            self.diarization_detector = DiarizationDetector(self.config)
            print(f"Initialized DiarizationDetector")

        elif self.mode in ["multimodal", "face", "pose", "mediapipe"]:
            # Initialize visual detector (MediaPipe)
            self.visual_detector = VisualDetector(self.config, self.mode)
            print(f"Initialized VisualDetector in {self.mode} mode")

            # Optionally initialize YOLO detector if enabled
            yolo_enabled = self.config.get("yolo_detection.enabled", False)
            if yolo_enabled:
                self.yolo_detector = YOLODetector(self.config)
                print(f"Initialized YOLODetector")
            else:
                self.yolo_detector = None

        else:
            raise ValueError(f"Unknown detection mode: {self.mode}")

    def detect_segments(
        self,
        video_path: str,
        json_output: bool = False
    ) -> List[Tuple[float, float]]:
        """
        Detect segments using configured detection mode.
        Routes to appropriate detector and returns list of (start, end) tuples.
        """
        if not json_output:
            self.progress.log(f"Detecting segments using {self.mode} mode")

        # Route to appropriate detection method
        if self.mode == "scene":
            return self.scene_detector.detect_scenes(video_path)

        elif self.mode == "diarization":
            return self.diarization_detector.detect_speakers(video_path)

        elif self.mode in ["multimodal", "face", "pose", "mediapipe"]:
            return self._detect_visual(video_path, json_output)

        else:
            raise ValueError(f"Unknown detection mode: {self.mode}")

    def _detect_visual(
        self,
        video_path: str,
        json_output: bool = False
    ) -> List[Tuple[float, float]]:
        """
        Visual detection using MediaPipe face/pose and optional YOLO tracking.
        Handles frame-level detection, analysis, and caching.
        """
        if not CV2_AVAILABLE:
            raise ImportError("OpenCV (cv2) not installed. Run: pip install opencv-python")

        if not json_output:
            self.progress.log(f"Loading video for {self.mode} detection")

        self.progress.emit("loading", 0, 0, 1, "Loading video file")

        # Load video info
        video_info = self.load_video_info(video_path)
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video: {video_path}")

        fps = video_info.fps
        total_frames = video_info.frame_count
        duration = video_info.duration
        frame_width = video_info.width
        frame_height = video_info.height

        print(f"Video: {duration:.1f}s, {fps:.1f} fps, {total_frames} frames, {frame_width}x{frame_height}px")

        sample_rate = self.config.get("processing.sample_rate", 30)
        sample_interval = int(sample_rate)

        # Try to load from cache
        detection_history = []
        cached_detection_loaded = False

        config_dict = self.config.to_dict() if hasattr(self.config, 'to_dict') else dict(self.config._config)
        detection_cache = self.load_from_cache(video_path, config_dict)

        if detection_cache:
            # Convert cached frames to detection_history format
            detection_history = [
                (
                    frame.frame_num,
                    frame.face_count,
                    frame.pose_count,
                    frame.person_count,
                    frame.positions[0] if frame.positions else None,  # avg_position
                    frame.blur_score,
                    frame.blur_score < self.config.get("blur_detection.threshold", 100.0)  # is_blurry
                )
                for frame in detection_cache.frames
            ]
            cached_detection_loaded = True
            self.progress.emit("detection", 100, total_frames, total_frames, "Loaded from cache")
            cap.release()

        # Only process frames if we don't have cached data
        if not cached_detection_loaded:
            # Initialize Kalman filter
            use_kalman = self.config.get("kalman_filter.enabled", True) and KALMAN_AVAILABLE
            kalman_tracker = KalmanPositionTracker(self.config) if use_kalman else None

            # Blur detection
            use_blur_detection = self.config.get("blur_detection.enabled", True)
            blur_count = 0

            # Edge zones for exit detection
            exit_threshold = self.config.get("position_detection.exit_threshold", 0.15)
            left_edge = frame_width * exit_threshold
            right_edge = frame_width * (1 - exit_threshold)

            # Zone checker for YOLO
            zone_checker = self._create_zone_checker(frame_width, frame_height) if self.yolo_detector else None
            if zone_checker and self.yolo_detector:
                print("Zone crossing detection enabled")

            frame_num = 0
            checked_frames = 0

            if not json_output:
                self.progress.log("Processing video frames")

            # Frame processing loop
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_num % sample_interval == 0:
                    # Blur detection
                    blur_score = 0.0
                    is_blurry = False
                    if use_blur_detection:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
                        blur_score = float(laplacian.var())
                        threshold = self.config.get("blur_detection.threshold", 100.0)
                        is_blurry = blur_score < threshold
                        if is_blurry:
                            blur_count += 1

                    # Visual detection (MediaPipe)
                    num_faces, num_poses, face_positions, pose_positions, _, _ = self.visual_detector.detect_frame(
                        frame, frame_width, frame_height
                    )

                    # YOLO detection (if enabled)
                    num_yolo_persons = 0
                    yolo_person_count_inside = 0
                    if self.yolo_detector:
                        num_yolo_persons, detections, yolo_person_count_inside, _, zone_crossings = \
                            self.yolo_detector.detect_frame(frame, zone_checker, frame_width, frame_height)

                    # Calculate person count based on configured method
                    person_count = self._calculate_person_count(
                        num_faces, num_poses, num_yolo_persons, yolo_person_count_inside
                    )

                    # Calculate average position
                    all_positions = face_positions + pose_positions
                    avg_position = sum(all_positions) / len(all_positions) if all_positions else None

                    # Apply Kalman filter
                    if use_kalman and kalman_tracker:
                        filtered_position = kalman_tracker.update(avg_position)
                    else:
                        filtered_position = avg_position

                    # Store detection data
                    detection_history.append((
                        frame_num, num_faces, num_poses, person_count, filtered_position, blur_score, is_blurry
                    ))

                    # Debug output for first few frames
                    if checked_frames < 5 and not json_output:
                        self.progress.log(
                            f"  Frame {frame_num}: faces={num_faces}, poses={num_poses}, "
                            f"person_count={person_count}, position={filtered_position}"
                        )

                    checked_frames += 1

                    # Progress reporting
                    if checked_frames % 30 == 0:
                        progress = int((frame_num / total_frames) * 100)
                        self.progress.emit("detection", progress, frame_num, total_frames, "Processing frames")
                        if not json_output:
                            self.progress.log(f"  Progress: {progress}% ({frame_num}/{total_frames} frames)")

                frame_num += 1

            cap.release()

            # Save detection data to cache
            if self.use_cache and self.cache_manager:
                detection_cache = create_detection_cache(
                    video_path=video_path,
                    config=config_dict,
                    fps=fps,
                    frame_count=total_frames,
                    duration=duration,
                    width=frame_width,
                    height=frame_height,
                    detection_method=self.mode,
                    model_version="2.0"
                )

                # Add all detection frames to cache
                for frame_num, num_faces, num_poses, person_count, position, blur_score, is_blurry in detection_history:
                    detection_frame = DetectionFrame(
                        frame_num=frame_num,
                        timestamp=frame_num / fps,
                        face_count=num_faces,
                        pose_count=num_poses,
                        yolo_count=0,  # Not directly stored in history
                        person_count=person_count,
                        positions=[position] if position is not None else [],
                        blur_score=blur_score
                    )
                    detection_cache.frames.append(detection_frame)

                self.save_to_cache(detection_cache)

            self.progress.emit("detection", 100, total_frames, total_frames, "Frame processing complete")
        else:
            # When loaded from cache, set checked_frames
            checked_frames = len(detection_history)
            left_edge = frame_width * self.config.get("position_detection.exit_threshold", 0.15)
            right_edge = frame_width * (1 - self.config.get("position_detection.exit_threshold", 0.15))

        # Calculate detection statistics
        total_with_faces = sum(1 for d in detection_history if d[1] > 0)
        total_with_poses = sum(1 for d in detection_history if d[2] > 0)
        total_with_people = sum(1 for d in detection_history if d[3] > 0)

        print(f"Analyzed {checked_frames} frames")
        print(f"  Frames with faces detected: {total_with_faces}/{checked_frames} ({100*total_with_faces/checked_frames:.1f}%)")
        print(f"  Frames with poses detected: {total_with_poses}/{checked_frames} ({100*total_with_poses/checked_frames:.1f}%)")
        print(f"  Frames with people detected: {total_with_people}/{checked_frames} ({100*total_with_people/checked_frames:.1f}%)")

        # Apply median filtering to smooth person counts
        detection_history = self._apply_person_count_smoothing(detection_history)

        # Analyze transitions
        self.progress.emit("analysis", 0, 0, 1, "Analyzing transitions")
        segments = self._analyze_transitions(detection_history, fps, left_edge, right_edge)
        self.progress.emit("analysis", 100, 1, 1, "Analysis complete")

        return segments

    def _calculate_person_count(
        self,
        num_faces: int,
        num_poses: int,
        num_yolo_persons: int,
        yolo_person_count_inside: int
    ) -> int:
        """Calculate person count based on configured method"""
        person_count_method = self.config.get("transition_detection.person_count_method", "min")

        if person_count_method == "yolo":
            person_count = num_yolo_persons
        elif person_count_method == "yolo_zone":
            person_count = yolo_person_count_inside
        elif person_count_method == "min":
            person_count = min(num_faces, num_poses) if self.mode == "multimodal" else (num_faces or num_poses)
        elif person_count_method == "max":
            person_count = max(num_faces, num_poses)
        elif person_count_method == "average":
            person_count = int((num_faces + num_poses) / 2)
        elif person_count_method == "hybrid":
            person_count = num_yolo_persons if num_yolo_persons > 0 else max(num_faces, num_poses)
        else:
            person_count = num_faces or num_poses

        # Cap at 2 to avoid noise from audience/false positives
        return min(person_count, 2)

    def _create_zone_checker(self, frame_width: int, frame_height: int):
        """Create zone checker function for zone crossing detection"""
        zone_config = self.config.get("zone_crossing", {})
        if not zone_config.get("enabled", False):
            return None

        stage_boundary = zone_config.get("stage_boundary", {})
        boundary_type = stage_boundary.get("type", "rectangle")

        if boundary_type == "rectangle":
            left = stage_boundary.get("left", 0.2)
            right = stage_boundary.get("right", 0.8)
            top = stage_boundary.get("top", 0.2)
            bottom = stage_boundary.get("bottom", 0.8)

            # Convert fractions to pixels
            if left <= 1.0:
                left = int(left * frame_width)
            if right <= 1.0:
                right = int(right * frame_width)
            if top <= 1.0:
                top = int(top * frame_height)
            if bottom <= 1.0:
                bottom = int(bottom * frame_height)

            def check_zone(centroid):
                x, y = centroid
                inside = left <= x <= right and top <= y <= bottom
                return "inside" if inside else "outside"

            return check_zone

        return None

    def _apply_person_count_smoothing(
        self,
        detection_history: List[Tuple]
    ) -> List[Tuple]:
        """Apply median filtering to smooth person counts"""
        person_count_smoothing = self.config.get("transition_detection.person_count_smoothing", True)

        if not person_count_smoothing or len(detection_history) == 0:
            return detection_history

        window_size = self.config.get("transition_detection.smoothing_window", 5)
        print(f"\nApplying median filtering (window={window_size}) to smooth person counts...")

        # Extract person counts
        person_counts = [d[3] for d in detection_history]

        # Apply median filter
        smoothed_counts = []
        for i in range(len(person_counts)):
            start = max(0, i - window_size // 2)
            end = min(len(person_counts), i + window_size // 2 + 1)
            window = person_counts[start:end]
            median = sorted(window)[len(window) // 2]
            smoothed_counts.append(median)

        # Update detection_history with smoothed counts
        detection_history = [
            (d[0], d[1], d[2], smoothed_counts[i], d[4], d[5], d[6])
            for i, d in enumerate(detection_history)
        ]

        # Report smoothing effect
        changes = sum(1 for i in range(len(person_counts)) if person_counts[i] != smoothed_counts[i])
        if changes > 0:
            print(f"  Smoothed {changes}/{len(person_counts)} frames ({100*changes/len(person_counts):.1f}%)")

        return detection_history

    def _analyze_transitions(
        self,
        detection_history: List[Tuple],
        fps: float,
        left_edge: float,
        right_edge: float
    ) -> List[Tuple[float, float]]:
        """Analyze transitions and detect segments"""
        transition_enabled = self.config.get("transition_detection.enabled", False)

        # For mediapipe mode OR if transition detection disabled, use position-based only
        if self.mode == "mediapipe" or not transition_enabled:
            print("\nUsing position-based detection (stage entry/exit)...")
            return self._position_based_detection(detection_history, fps, left_edge, right_edge)

        print("\nAnalyzing transitions...")

        segments = []
        current_start = None
        prev_count = 0

        stability_frames = self.config.get("transition_detection.transition_stability_frames", 3)
        stable_count = 0
        stable_value = 0

        for i, detection_data in enumerate(detection_history):
            frame_num, num_faces, num_poses, person_count, position = detection_data[:5]
            time = frame_num / fps

            # Check for stable count
            if person_count == stable_value:
                stable_count += 1
            else:
                stable_value = person_count
                stable_count = 1

            # Only process transitions when count is stable
            if stable_count >= stability_frames and person_count != prev_count:
                if self.config.should_start_segment(prev_count, person_count):
                    if current_start is None:
                        current_start = (time, i)
                        print(f"  Segment start at {time:.1f}s: {prev_count}→{person_count} people")

                elif self.config.should_end_segment(prev_count, person_count):
                    if current_start is not None:
                        segments.append((current_start[0], time, current_start[1], i))
                        print(f"  Segment end at {time:.1f}s: {prev_count}→{person_count} people")
                        current_start = None

                prev_count = person_count

        # Final segment
        if current_start is not None:
            final_time = detection_history[-1][0] / fps
            segments.append((current_start[0], final_time, current_start[1], len(detection_history) - 1))

        print(f"Detected {len(segments)} segments from transitions")

        # Fallback to position-based if no segments
        if len(segments) == 0 and self.config.get("position_detection.enabled", True):
            print("No transitions found. Using position-based fallback...")
            segments = self._position_based_detection(detection_history, fps, left_edge, right_edge)

        return segments

    def _position_based_detection(
        self,
        detection_history: List[Tuple],
        fps: float,
        left_edge: float,
        right_edge: float
    ) -> List[Tuple[float, float]]:
        """Position-based detection - clips when someone walks off frame"""
        segments = []
        current_start = None
        exit_stability_frames = self.config.get("position_detection.exit_stability_frames", 2)
        at_edge_count = 0

        print(f"\nPosition-based detection parameters:")
        print(f"  Left edge threshold: {left_edge:.1f} pixels")
        print(f"  Right edge threshold: {right_edge:.1f} pixels")
        print(f"  Exit stability frames: {exit_stability_frames}")

        for i, detection_data in enumerate(detection_history):
            frame_num, num_faces, num_poses, person_count, position = detection_data[:5]
            time = frame_num / fps

            has_detection = (num_faces > 0 or num_poses > 0)

            if position is not None and has_detection:
                is_at_edge = position < left_edge or position > right_edge

                if is_at_edge:
                    at_edge_count += 1
                else:
                    at_edge_count = 0

                # Start segment when person is NOT at edge
                if not is_at_edge:
                    if current_start is None:
                        current_start = (time, i)
                        print(f"  ✓ Segment start at {time:.1f}s (frame {int(frame_num)}, position: {position:.1f}px)")

                # End segment when person has been at edge for stability period
                elif at_edge_count >= exit_stability_frames and current_start is not None:
                    segments.append((current_start[0], time, current_start[1], i))
                    print(f"  ✗ Segment end at {time:.1f}s (frame {int(frame_num)}): person at edge")
                    current_start = None
                    at_edge_count = 0

            # No detection - also end segment
            elif not has_detection and current_start is not None:
                segments.append((current_start[0], time, current_start[1], i))
                print(f"  ✗ Segment end at {time:.1f}s (frame {int(frame_num)}): person disappeared")
                current_start = None
                at_edge_count = 0

        # Close any open segment at end of video
        if current_start is not None:
            final_time = detection_history[-1][0] / fps
            segments.append((current_start[0], final_time, current_start[1], len(detection_history) - 1))
            print(f"  ✗ Segment end at {final_time:.1f}s: end of video")

        print(f"\n📊 Detected {len(segments)} segments from position-based detection")
        return segments


def main():
    """Main entry point with argument parsing and execution"""
    parser = argparse.ArgumentParser(
        description="Unified comedy clipper (refactored with BaseClipper architecture)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Detection Modes:
  multimodal   - Face + pose detection (default, best for standup)
  pose         - Pose detection only
  face         - Face detection only
  mediapipe    - MediaPipe pose tracking
  scene        - FFmpeg scene detection
  diarization  - Speaker diarization (requires HF_TOKEN)

Examples:
  # Use default config and mode
  python3 clipper_unified_v2.py video.mp4

  # Specify detection mode
  python3 clipper_unified_v2.py video.mp4 --mode scene

  # Use custom config
  python3 clipper_unified_v2.py video.mp4 -c my_config.yaml

  # Enable debug output
  python3 clipper_unified_v2.py video.mp4 -d

Configuration:
  Edit clipper_rules.yaml to customize all detection parameters
        """
    )

    parser.add_argument('video', help='Input video file')
    parser.add_argument('--mode', choices=['multimodal', 'pose', 'face', 'mediapipe', 'scene', 'diarization'],
                       help='Detection mode (default: from config or multimodal)')
    parser.add_argument('-c', '--config', help='Config file (default: clipper_rules.yaml)')
    parser.add_argument('-o', '--output', help='Output directory for clips')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--min-duration', type=float, help='Override minimum duration (seconds)')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--no-cache', action='store_true', help='Disable detection data caching')

    args = parser.parse_args()

    # Load configuration
    config_path = args.config or 'clipper_rules.yaml'
    config = load_config(config_path)

    # Override config from command line args
    if args.min_duration is not None:
        config.set("filtering.min_duration", args.min_duration)

    # Create clipper
    mode = args.mode or config.get("detection_mode", "multimodal")
    use_cache = not args.no_cache

    clipper = UnifiedClipper(
        config=config,
        mode=mode,
        debug=args.debug,
        use_cache=use_cache
    )

    # Process video
    result = clipper.process_video(args.video, args.output, args.json)

    # Output results
    if args.json:
        import json
        print(json.dumps(result, indent=2))
    else:
        if result['success']:
            print(f"\n✅ Success! Created {len(result['clips'])} clips")
            print(f"📁 Output directory: {result['output_dir']}")
        else:
            print(f"\n❌ Error: {result['error']}")
            sys.exit(1)


if __name__ == "__main__":
    main()
