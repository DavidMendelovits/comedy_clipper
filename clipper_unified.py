#!/usr/bin/env python3
"""
Unified Comedy Clipper - All detection methods in one configurable script
Supports: speaker diarization, scene detection, pose detection, face+pose multi-modal
Configure via YAML or command line arguments
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import subprocess
from datetime import datetime
from config_loader import load_config, ClipperConfig

# Optional imports based on detection mode
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None

try:
    from filterpy.kalman import KalmanFilter
    KALMAN_AVAILABLE = True
except ImportError:
    KALMAN_AVAILABLE = False
    KalmanFilter = None

try:
    from pyannote.audio import Pipeline
    import torch
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    Pipeline = None
    torch = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    YOLO = None

try:
    from enhanced_person_tracker import EnhancedPersonTracker
    TRACKER_AVAILABLE = True
except ImportError:
    try:
        # Fallback to original tracker if enhanced not available
        from person_tracker import CentroidTracker as EnhancedPersonTracker
        TRACKER_AVAILABLE = True
    except ImportError:
        TRACKER_AVAILABLE = False
        EnhancedPersonTracker = None


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


class UnifiedComedyClipper:
    """Unified clipper supporting multiple detection methods"""

    def __init__(self, config: ClipperConfig, mode: str = None, debug: bool = False):
        """
        Initialize clipper with specified detection mode.

        Args:
            config: Loaded configuration
            mode: Detection mode (auto-detect if None)
            debug: Whether to export debug frames
        """
        self.config = config
        self.debug = debug or config.get("debug.export_frames", False)
        self.debug_dir = None  # Will be set if debug frames are exported
        self.stage_polygon = None  # Will be set if zone crossing is enabled

        # Auto-detect mode from config if not specified
        if mode is None:
            mode = config.get("detection_mode", "multimodal")

        self.mode = mode

        # Initialize detectors based on mode
        self._init_detectors()

        print(f"Initialized in '{self.mode}' mode")

    def _emit_progress(self, phase: str, percent: int, current: int = None, total: int = None, message: str = None):
        """Emit structured progress JSON for UI consumption"""
        import json
        progress_data = {
            "type": "progress",
            "phase": phase,
            "percent": percent
        }
        if current is not None:
            progress_data["current"] = current
        if total is not None:
            progress_data["total"] = total
        if message:
            progress_data["message"] = message

        # Print as single-line JSON for easy parsing
        print(f"[PROGRESS] {json.dumps(progress_data)}")
        sys.stdout.flush()

    def _init_detectors(self):
        """Initialize required detectors based on mode"""
        if self.mode in ["multimodal", "face", "pose", "mediapipe"]:
            if not MEDIAPIPE_AVAILABLE:
                raise ImportError("MediaPipe not installed. Run: pip install mediapipe")

            print("Initializing MediaPipe detectors...")

            if self.mode in ["multimodal", "face"]:
                self.mp_face = mp.solutions.face_detection
                face_conf = self.config.get("confidence.face_detection.min_detection_confidence", 0.5)
                face_model = self.config.get("confidence.face_detection.model_selection", 1)
                self.face_detection = self.mp_face.FaceDetection(
                    model_selection=face_model,
                    min_detection_confidence=face_conf
                )

            if self.mode in ["multimodal", "pose", "mediapipe"]:
                self.mp_pose = mp.solutions.pose
                pose_det_conf = self.config.get("confidence.pose_detection.min_detection_confidence", 0.5)
                pose_track_conf = self.config.get("confidence.pose_detection.min_tracking_confidence", 0.5)
                pose_complexity = self.config.get("confidence.pose_detection.model_complexity", 1)
                pose_smooth = self.config.get("confidence.pose_detection.smooth_landmarks", True)

                self.pose = self.mp_pose.Pose(
                    static_image_mode=False,
                    model_complexity=pose_complexity,
                    smooth_landmarks=pose_smooth,
                    min_detection_confidence=pose_det_conf,
                    min_tracking_confidence=pose_track_conf
                )

            self.mp_drawing = mp.solutions.drawing_utils
            self.mp_drawing_styles = mp.solutions.drawing_styles

        # Initialize YOLO detector if enabled (can be used alongside other detectors)
        yolo_enabled = self.config.get("yolo_detection.enabled", False)
        if yolo_enabled and self.mode in ["multimodal", "yolo_zone"]:
            if not YOLO_AVAILABLE:
                raise ImportError("Ultralytics not installed. Run: pip install ultralytics")
            if not TRACKER_AVAILABLE:
                raise ImportError("Person tracker not found. Ensure person_tracker.py exists")

            print("Initializing YOLO detector...")
            model_name = self.config.get("yolo_detection.model", "yolov8n.pt")
            self.yolo = YOLO(model_name)

            # Initialize enhanced person tracker with velocity detection
            max_disappeared = self.config.get("yolo_detection.max_disappeared_frames", 30)
            velocity_window = self.config.get("yolo_detection.velocity_window", 5)
            exit_velocity_threshold = self.config.get("yolo_detection.exit_velocity_threshold", 20.0)
            self.person_tracker = EnhancedPersonTracker(
                max_disappeared=max_disappeared,
                velocity_window=velocity_window,
                exit_velocity_threshold=exit_velocity_threshold
            )
            print(f"  Model: {model_name}")
            print(f"  Tracker initialized (max_disappeared={max_disappeared})")
        else:
            self.yolo = None
            self.person_tracker = None

        if self.mode == "diarization":
            if not PYANNOTE_AVAILABLE:
                raise ImportError("Pyannote not installed. Run: pip install pyannote-audio")

            hf_token = os.getenv('HF_TOKEN') or os.getenv('HUGGING_FACE_TOKEN')
            if not hf_token:
                raise ValueError(
                    "HuggingFace token required for diarization mode. "
                    "Set HF_TOKEN or HUGGING_FACE_TOKEN environment variable.\n"
                    "Get your token at: https://huggingface.co/settings/tokens\n"
                    "Accept pyannote terms at: https://huggingface.co/pyannote/speaker-diarization-3.1"
                )

            print("Loading speaker diarization model...")
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=hf_token
            )

            if torch.cuda.is_available():
                self.pipeline = self.pipeline.to(torch.device("cuda"))
                print("Using GPU acceleration")
            else:
                print("Using CPU (this will be slower)")

    def _create_zone_checker(self, frame_width, frame_height):
        """
        Create a zone checker function based on configuration.

        Returns a function that takes (x, y) and returns "inside" or "outside"
        """
        zone_config = self.config.get("zone_crossing", {})
        if not zone_config.get("enabled", False):
            return None

        stage_boundary = zone_config.get("stage_boundary", {})
        boundary_type = stage_boundary.get("type", "rectangle")

        if boundary_type == "polygon":
            # Get polygon points from config
            points = stage_boundary.get("points", [])
            if not points:
                # Default to center 60% of frame
                margin = 0.2
                points = [
                    [frame_width * margin, frame_height * margin],
                    [frame_width * (1 - margin), frame_height * margin],
                    [frame_width * (1 - margin), frame_height * (1 - margin)],
                    [frame_width * margin, frame_height * (1 - margin)]
                ]

            # Convert to numpy array for cv2.pointPolygonTest
            polygon = np.array(points, dtype=np.int32)

            def check_zone(centroid):
                """Check if centroid is inside polygon"""
                x, y = centroid
                result = cv2.pointPolygonTest(polygon, (float(x), float(y)), False)
                return "inside" if result >= 0 else "outside"

            # Store polygon for debug visualization
            self.stage_polygon = polygon
            return check_zone

        elif boundary_type == "rectangle":
            # Get rectangle bounds from config or use defaults
            left = stage_boundary.get("left", 0.2)
            right = stage_boundary.get("right", 0.8)
            top = stage_boundary.get("top", 0.2)
            bottom = stage_boundary.get("bottom", 0.8)

            # Convert fractions to pixels if needed (values < 1.0 are fractions)
            if left < 1.0:
                left = int(left * frame_width)
            if right < 1.0:
                right = int(right * frame_width)
            if top < 1.0:
                top = int(top * frame_height)
            if bottom < 1.0:
                bottom = int(bottom * frame_height)

            def check_zone(centroid):
                """Check if centroid is inside rectangle"""
                x, y = centroid
                inside = left <= x <= right and top <= y <= bottom
                return "inside" if inside else "outside"

            # Store rectangle for debug visualization
            self.stage_polygon = np.array([
                [left, top],
                [right, top],
                [right, bottom],
                [left, bottom]
            ], dtype=np.int32)
            return check_zone

        return None

    def detect_segments(self, video_path: str, json_output: bool = False) -> List[Tuple[float, float]]:
        """Detect segments using configured detection mode"""
        if not json_output:
            print(f"[STEP] Detecting segments using {self.mode} mode")

        if self.mode == "scene":
            return self._detect_scenes_ffmpeg(video_path, json_output)
        elif self.mode == "diarization":
            return self._detect_diarization(video_path, json_output)
        elif self.mode in ["multimodal", "face", "pose", "mediapipe"]:
            return self._detect_visual(video_path, json_output)
        else:
            raise ValueError(f"Unknown detection mode: {self.mode}")

    def _detect_scenes_ffmpeg(self, video_path: str, json_output: bool = False) -> List[Tuple[float, float]]:
        """Detect segments using FFmpeg scene detection"""
        if not json_output:
            print("[STEP] Analyzing video for scene changes")

        threshold = self.config.get("scene_detection.threshold", 0.3)

        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-filter:v', f"select='gt(scene,{threshold})',showinfo",
            '-f', 'null',
            '-'
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

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

        # Group scenes
        max_gap = self.config.get("scene_detection.max_gap", 5.0)
        min_duration = self.config.get("filtering.min_duration", 30.0)

        segments = []
        if len(timestamps) >= 2:
            current_start = timestamps[0]
            last_time = timestamps[0]

            for time in timestamps[1:]:
                gap = time - last_time
                if gap > max_gap:
                    duration = last_time - current_start
                    if duration >= min_duration:
                        segments.append((current_start, last_time))
                    current_start = time
                last_time = time

            # Final segment
            duration = last_time - current_start
            if duration >= min_duration:
                segments.append((current_start, last_time))

        print(f"Detected {len(segments)} segments from scenes")
        return segments

    def _detect_diarization(self, video_path: str, json_output: bool = False) -> List[Tuple[float, float]]:
        """Detect segments using speaker diarization"""
        if not json_output:
            print("[STEP] Extracting audio for diarization")

        # Extract audio
        audio_path = str(Path(video_path).with_suffix('.wav'))

        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vn', '-acodec', 'pcm_s16le',
            audio_path
        ]
        subprocess.run(cmd, capture_output=True)

        try:
            # Diarize
            if not json_output:
                print("[STEP] Running speaker diarization model")
            diarization = self.pipeline(audio_path)

            speaker_segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speaker_segments.append((turn.start, turn.end, speaker))

            print(f"Found {len(set(s[2] for s in speaker_segments))} unique speakers")
            print(f"Total segments: {len(speaker_segments)}")

            # Group by speaker
            min_duration = self.config.get("filtering.min_duration", 30.0)
            grouped = []

            if speaker_segments:
                current_speaker = speaker_segments[0][2]
                current_start = speaker_segments[0][0]
                current_end = speaker_segments[0][1]

                for start, end, speaker in speaker_segments[1:]:
                    if speaker == current_speaker:
                        current_end = end
                    else:
                        duration = current_end - current_start
                        if duration >= min_duration:
                            grouped.append((current_start, current_end))
                        current_speaker = speaker
                        current_start = start
                        current_end = end

                # Last segment
                duration = current_end - current_start
                if duration >= min_duration:
                    grouped.append((current_start, current_end))

            print(f"Grouped into {len(grouped)} segments")
            return grouped

        finally:
            # Cleanup audio file
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"Cleaned up temporary audio file")

    def _detect_visual(self, video_path: str, json_output: bool = False) -> List[Tuple[float, float]]:
        """Detect segments using visual detection (pose/face/multimodal)"""
        if not CV2_AVAILABLE:
            raise ImportError("OpenCV (cv2) not installed. Run: pip install opencv-python")

        if not json_output:
            print(f"[STEP] Loading video for {self.mode} detection")

        self._emit_progress("loading", 0, 0, 1, "Loading video file")

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"Video: {duration:.1f}s, {fps:.1f} fps, {total_frames} frames, {frame_width}x{frame_height}px")

        sample_rate = self.config.get("processing.sample_rate", 30)
        sample_interval = int(sample_rate)

        detection_history = []
        debug_data = {}

        # Initialize zone checker for zone crossing detection
        zone_checker = self._create_zone_checker(frame_width, frame_height)
        if zone_checker:
            print("Zone crossing detection enabled")
            print(f"  Stage boundary: {self.stage_polygon.tolist() if self.stage_polygon is not None else 'None'}")

        # Kalman filter
        use_kalman = self.config.get("kalman_filter.enabled", True) and KALMAN_AVAILABLE
        kalman_tracker = KalmanPositionTracker(self.config) if use_kalman else None

        # Blur detection
        use_blur_detection = self.config.get("blur_detection.enabled", True)
        blur_count = 0

        # Edge zones
        exit_threshold = self.config.get("position_detection.exit_threshold", 0.15)
        left_edge = frame_width * exit_threshold
        right_edge = frame_width * (1 - exit_threshold)

        frame_num = 0
        checked_frames = 0

        if not json_output:
            print("[STEP] Processing video frames")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_num % sample_interval == 0:
                # Calculate blur score
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

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                num_faces = 0
                face_positions = []
                face_detections_list = []

                num_poses = 0
                pose_positions = []
                pose_landmarks_list = []

                # Face detection
                if self.mode in ["multimodal", "face"]:
                    face_results = self.face_detection.process(rgb_frame)
                    if face_results.detections:
                        for detection in face_results.detections:
                            num_faces += 1
                            bbox = detection.location_data.relative_bounding_box
                            center_x = (bbox.xmin + bbox.width / 2) * frame_width
                            face_positions.append(center_x)
                            face_detections_list.append(detection)

                # Pose detection
                if self.mode in ["multimodal", "pose", "mediapipe"]:
                    pose_results = self.pose.process(rgb_frame)
                    if pose_results.pose_landmarks:
                        num_poses = 1
                        landmarks = pose_results.pose_landmarks.landmark

                        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
                        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
                        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
                        right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]

                        torso_x = (left_shoulder.x + right_shoulder.x + left_hip.x + right_hip.x) / 4
                        pose_positions.append(torso_x * frame_width)
                        pose_landmarks_list.append(pose_results.pose_landmarks)

                # YOLO detection
                num_yolo_persons = 0
                yolo_detections = []
                yolo_person_count_inside = 0
                yolo_person_count_outside = 0
                zone_crossings = []

                if self.yolo is not None:
                    # Run YOLO detection (class 0 = person)
                    yolo_confidence = self.config.get("yolo_detection.confidence", 0.5)
                    results = self.yolo(frame, classes=[0], conf=yolo_confidence, verbose=False)

                    if len(results) > 0 and len(results[0].boxes) > 0:
                        # Extract bounding boxes
                        boxes = results[0].boxes.xyxy.cpu().numpy()  # [x1, y1, x2, y2]

                        for box in boxes:
                            x1, y1, x2, y2 = box
                            w = x2 - x1
                            h = y2 - y1
                            yolo_detections.append((x1, y1, w, h))
                            num_yolo_persons += 1

                    # Update tracker with detections and velocity tracking
                    if self.person_tracker is not None:
                        # Set stage boundaries if available
                        if hasattr(self.person_tracker, 'set_stage_boundaries'):
                            zone_config = self.config.get("zone_crossing", {})
                            stage_boundary = zone_config.get("stage_boundary", {})
                            self.person_tracker.set_stage_boundaries(
                                stage_boundary.get("left", 0.05),
                                stage_boundary.get("right", 0.95),
                                stage_boundary.get("top", 0.0),
                                stage_boundary.get("bottom", 0.85)
                            )

                        # Update with frame dimensions for velocity calculation
                        if hasattr(self.person_tracker, 'detect_exit_events'):
                            tracked_objects, zone_crossings, exit_events = self.person_tracker.update(
                                yolo_detections,
                                zone_checker=zone_checker,
                                frame_width=frame_width,
                                frame_height=frame_height
                            )

                            # Log exit events
                            for obj_id, confidence in exit_events:
                                if not json_output and checked_frames < 20:
                                    print(f"  Frame {frame_num}: Person #{obj_id} likely exiting (confidence: {confidence:.2f})")
                        else:
                            # Fallback for original tracker
                            tracked_objects, zone_crossings = self.person_tracker.update(
                                yolo_detections,
                                zone_checker=zone_checker
                            )

                        # Count people inside/outside zone
                        if zone_checker:
                            yolo_person_count_inside = self.person_tracker.get_count_inside_zone()
                            yolo_person_count_outside = self.person_tracker.get_count_outside_zone()

                            # Log zone crossings
                            for obj_id, from_zone, to_zone in zone_crossings:
                                if not json_output and checked_frames < 20:
                                    print(f"  Frame {frame_num}: Person #{obj_id} crossed {from_zone}→{to_zone}")

                # Calculate person count
                person_count_method = self.config.get("transition_detection.person_count_method", "min")
                if person_count_method == "yolo":
                    # Use YOLO count (all detected people)
                    person_count = num_yolo_persons
                elif person_count_method == "yolo_zone":
                    # Use YOLO count inside zone only
                    person_count = yolo_person_count_inside
                elif person_count_method == "min":
                    person_count = min(num_faces, num_poses) if self.mode == "multimodal" else (num_faces or num_poses)
                elif person_count_method == "max":
                    person_count = max(num_faces, num_poses)
                elif person_count_method == "average":
                    person_count = int((num_faces + num_poses) / 2)
                elif person_count_method == "hybrid":
                    # Hybrid: prefer YOLO if available, fallback to max(faces, poses)
                    if num_yolo_persons > 0:
                        person_count = num_yolo_persons
                    else:
                        person_count = max(num_faces, num_poses)
                else:
                    person_count = num_faces or num_poses

                # Cap person count at 2 since we rarely have 3+ people on stage
                # Treating 3+ as noise (audience detection, false positives)
                # This prevents count=3 from interrupting legitimate 1→2 transitions
                if person_count > 2:
                    person_count = 2

                # Calculate average position
                all_positions = face_positions + pose_positions
                avg_position = sum(all_positions) / len(all_positions) if all_positions else None

                # Apply Kalman filter
                if use_kalman and kalman_tracker:
                    filtered_position = kalman_tracker.update(avg_position)
                else:
                    filtered_position = avg_position

                detection_history.append((
                    frame_num, num_faces, num_poses, person_count, filtered_position, blur_score, is_blurry
                ))

                # Debug: Print first few detections to understand what's happening
                if checked_frames < 5 and not json_output:
                    print(f"  Frame {frame_num}: faces={num_faces}, poses={num_poses}, person_count={person_count}, position={filtered_position}")

                if self.debug:
                    debug_data[frame_num] = (pose_landmarks_list, face_detections_list, blur_score, is_blurry, yolo_detections, yolo_person_count_inside, yolo_person_count_outside)

                checked_frames += 1

                if checked_frames % 30 == 0:
                    progress = int((frame_num / total_frames) * 100)
                    self._emit_progress("detection", progress, frame_num, total_frames, f"Processing frames")
                    if not json_output:
                        print(f"  Progress: {progress}% ({frame_num}/{total_frames} frames)")

            frame_num += 1

        cap.release()

        self._emit_progress("detection", 100, total_frames, total_frames, "Frame processing complete")

        # Calculate detection statistics
        total_with_faces = sum(1 for d in detection_history if d[1] > 0)
        total_with_poses = sum(1 for d in detection_history if d[2] > 0)
        total_with_people = sum(1 for d in detection_history if d[3] > 0)

        print(f"Analyzed {checked_frames} frames")
        print(f"  Frames with faces detected: {total_with_faces}/{checked_frames} ({100*total_with_faces/checked_frames:.1f}%)")
        print(f"  Frames with poses detected: {total_with_poses}/{checked_frames} ({100*total_with_poses/checked_frames:.1f}%)")
        print(f"  Frames with people detected: {total_with_people}/{checked_frames} ({100*total_with_people/checked_frames:.1f}%)")

        if use_blur_detection:
            blur_pct = (blur_count / checked_frames * 100) if checked_frames > 0 else 0
            print(f"  Blurry frames: {blur_count}/{checked_frames} ({blur_pct:.1f}%)")

        # Apply median filtering to person_count to reduce noise from inconsistent detection
        person_count_smoothing = self.config.get("transition_detection.person_count_smoothing", True)
        if person_count_smoothing and len(detection_history) > 0:
            window_size = self.config.get("transition_detection.smoothing_window", 5)
            print(f"\nApplying median filtering (window={window_size}) to smooth person counts...")

            # Extract person counts
            person_counts = [d[3] for d in detection_history]

            # Apply median filter
            smoothed_counts = []
            for i in range(len(person_counts)):
                # Get window around current position
                start = max(0, i - window_size // 2)
                end = min(len(person_counts), i + window_size // 2 + 1)
                window = person_counts[start:end]

                # Calculate median
                sorted_window = sorted(window)
                median = sorted_window[len(sorted_window) // 2]
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

        # Analyze transitions
        self._emit_progress("analysis", 0, 0, 1, "Analyzing transitions")
        segments = self._analyze_transitions(detection_history, fps, left_edge, right_edge, debug_data, video_path)
        self._emit_progress("analysis", 100, 1, 1, "Analysis complete")

        return segments

    def _analyze_transitions(self, detection_history, fps, left_edge, right_edge, debug_data, video_path):
        """Analyze transitions based on config rules"""

        # For mediapipe mode, skip transition detection and use position-based only
        if self.mode == "mediapipe":
            print("\nUsing position-based detection (stage entry/exit)...")
            segments = self._position_based_detection(detection_history, fps, left_edge, right_edge)
            # Export debug frames if enabled
            if self.debug and segments:
                self._export_debug_frames_simple(segments, detection_history, debug_data, left_edge, right_edge, video_path, fps)
            return segments

        print("\nAnalyzing transitions...")

        segments = []
        segment_frames = []
        current_start = None
        current_start_idx = None
        prev_count = 0

        stability_frames = self.config.get("transition_detection.transition_stability_frames", 3)
        stable_count = 0
        stable_value = 0

        for i, detection_data in enumerate(detection_history):
            if len(detection_data) >= 7:
                frame_num, num_faces, num_poses, person_count, position, blur_score, is_blurry = detection_data
            else:
                frame_num, num_faces, num_poses, person_count, position = detection_data[:5]
                blur_score = 0.0
                is_blurry = False

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
                        current_start = time
                        current_start_idx = i
                        segment_frames.append([])
                        print(f"  Segment start at {time:.1f}s: {prev_count}→{person_count} people")

                elif self.config.should_end_segment(prev_count, person_count):
                    if current_start is not None:
                        segments.append((current_start, time, current_start_idx, i))
                        print(f"  Segment end at {time:.1f}s: {prev_count}→{person_count} people")
                        current_start = None
                        current_start_idx = None

                prev_count = person_count

            # Track frames for debug
            if current_start is not None and segment_frames:
                segment_frames[-1].append((frame_num, num_faces, num_poses, person_count, position, blur_score))

        # Final segment
        if current_start is not None:
            final_time = detection_history[-1][0] / fps
            segments.append((current_start, final_time, current_start_idx, len(detection_history) - 1))

        print(f"Detected {len(segments)} segments from transitions")

        # Apply boundary adjustments
        if segments:
            segments = self._adjust_boundaries(segments, detection_history, fps)

        # Fallback to position-based if no segments
        if len(segments) == 0 and self.config.get("position_detection.enabled", True):
            print("No transitions found. Using position-based fallback...")
            segments = self._position_based_detection(detection_history, fps, left_edge, right_edge)

        # Export debug frames
        if self.debug and segments:
            self._export_debug_frames(segments, segment_frames, debug_data, left_edge, right_edge, video_path, fps, detection_history)

        return segments

    def _adjust_boundaries(self, segments, detection_history, fps):
        """Adjust segment boundaries for blur and time buffer"""
        video_duration = detection_history[-1][0] / fps if detection_history else 0
        buffer_before = self.config.get("filtering.buffer_before_start", 2.0)
        buffer_after = self.config.get("filtering.buffer_after_end", 2.0)

        adjusted = []
        for start_time, end_time, start_idx, end_idx in segments:
            # Shift boundaries to sharp frames if blur detection enabled
            if self.config.get("blur_detection.enabled", True):
                _, shifted_start = self._find_sharp_boundary(detection_history, start_idx, fps)
                _, shifted_end = self._find_sharp_boundary(detection_history, end_idx, fps)
            else:
                shifted_start = start_time
                shifted_end = end_time

            # Apply time buffer
            buffered_start = max(0, shifted_start - buffer_before)
            buffered_end = min(video_duration, shifted_end + buffer_after)

            # Preserve indices for debug export
            adjusted.append((buffered_start, buffered_end, start_idx, end_idx))

        return adjusted

    def _find_sharp_boundary(self, detection_history, target_frame_idx, fps):
        """Find nearest sharp frame for segment boundary"""
        if not self.config.get("blur_detection.enabled", True):
            frame_num = detection_history[target_frame_idx][0]
            return frame_num, frame_num / fps

        max_shift_history = self.config.get("blur_detection.boundary_shift_max_frames", 30)
        min_sharpness = self.config.get("blur_detection.boundary_sharpness_min", 150.0)

        if len(detection_history) > 1:
            frames_per_entry = abs(detection_history[1][0] - detection_history[0][0])
        else:
            frames_per_entry = 1

        max_shift_entries = max(1, int(max_shift_history / frames_per_entry))

        best_idx = target_frame_idx
        best_score = detection_history[target_frame_idx][5] if len(detection_history[target_frame_idx]) > 5 else 0

        # Search forward and backward
        for i in range(target_frame_idx, min(target_frame_idx + max_shift_entries, len(detection_history))):
            if len(detection_history[i]) > 5:
                blur_score = detection_history[i][5]
                if blur_score >= min_sharpness:
                    best_idx = i
                    break

        frame_num = detection_history[best_idx][0]
        return frame_num, frame_num / fps

    def _position_based_detection(self, detection_history, fps, left_edge, right_edge):
        """Fallback position-based detection"""
        segments = []
        current_start = None

        for i, detection_data in enumerate(detection_history):
            if len(detection_data) >= 7:
                frame_num, num_faces, num_poses, person_count, position, blur_score, is_blurry = detection_data
            else:
                frame_num, num_faces, num_poses, person_count, position = detection_data[:5]

            time = frame_num / fps

            if position is not None:
                is_at_edge = position < left_edge or position > right_edge
                has_person = person_count >= 1

                if has_person and not is_at_edge:
                    if current_start is None:
                        current_start = (time, i)
                elif current_start is not None:
                    segments.append((current_start[0], time, current_start[1], i))
                    current_start = None

        if current_start is not None:
            final_time = detection_history[-1][0] / fps
            segments.append((current_start[0], final_time, current_start[1], len(detection_history) - 1))

        print(f"Detected {len(segments)} segments from position")

        if segments:
            segments = self._adjust_boundaries(segments, detection_history, fps)

        return segments

    def _export_debug_frames_simple(self, segments, detection_history, debug_data, left_edge, right_edge, video_path, fps):
        """Export debug frames for position-based detection"""
        print("\nExporting debug frames...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_name = Path(video_path).stem
        output_dir = Path(video_path).parent / f"{video_name}_debug_mediapipe_{timestamp}"
        output_dir.mkdir(exist_ok=True)

        print(f"Debug frames saved to: {output_dir}")

    def _export_debug_frames(self, segments, segment_frames, debug_data, left_edge, right_edge, video_path, fps, detection_history):
        """Export debug frames with comprehensive visualization"""
        print("\nExporting debug frames...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_name = Path(video_path).stem
        debug_suffix = self.config.get("output.debug_folder_suffix", "debug")
        output_dir = Path(video_path).parent / f"{video_name}_{debug_suffix}_{timestamp}"
        output_dir.mkdir(exist_ok=True)

        # Store debug directory for later use
        self.debug_dir = str(output_dir)

        # Create subdirectories for organization
        transitions_dir = output_dir / "transitions"
        timeline_dir = output_dir / "timeline"
        segments_dir = output_dir / "segments"
        transitions_dir.mkdir(exist_ok=True)
        timeline_dir.mkdir(exist_ok=True)
        segments_dir.mkdir(exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("Error: Could not open video for debug export")
            return

        # Export timeline frames (every 30 seconds)
        print("Exporting timeline frames (every 30 seconds)...")
        timeline_interval = 30 * fps  # Every 30 seconds
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        for frame_num in range(0, frame_count, int(timeline_interval)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            if not ret:
                continue

            # Find detection data for this frame
            time_sec = frame_num / fps
            person_count = 0
            for detection_data in detection_history:
                if abs(detection_data[0] - frame_num) < fps:  # Within 1 second
                    person_count = detection_data[3] if len(detection_data) > 3 else 0
                    break

            # Draw info overlay
            annotated = frame.copy()

            # Draw stage boundary polygon if it exists
            if self.stage_polygon is not None:
                cv2.polylines(annotated, [self.stage_polygon], True, (255, 0, 0), 3)
                cv2.putText(annotated, "Stage Boundary", (int(self.stage_polygon[0][0]), int(self.stage_polygon[0][1]) - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

            # Draw YOLO detections if available
            yolo_detections = []
            yolo_count_inside = 0
            yolo_count_outside = 0
            if frame_num in debug_data:
                frame_debug = debug_data[frame_num]
                if len(frame_debug) >= 7:  # Check if YOLO data exists
                    yolo_detections = frame_debug[4] if frame_debug[4] else []
                    yolo_count_inside = frame_debug[5]
                    yolo_count_outside = frame_debug[6]

                    # Draw YOLO bounding boxes
                    for i, (x, y, w, h) in enumerate(yolo_detections):
                        x1, y1 = int(x), int(y)
                        x2, y2 = int(x + w), int(y + h)
                        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 255), 2)
                        cv2.putText(annotated, f"Person {i+1}", (x1, y1 - 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

            # Text overlays
            cv2.putText(annotated, f"Time: {int(time_sec)}s", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(annotated, f"Person count: {person_count}", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(annotated, f"Frame: {frame_num}", (10, 110),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Add YOLO info if available
            if yolo_detections:
                cv2.putText(annotated, f"YOLO: {len(yolo_detections)} detected", (10, 150),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                if yolo_count_inside > 0 or yolo_count_outside > 0:
                    cv2.putText(annotated, f"Inside: {yolo_count_inside} | Outside: {yolo_count_outside}", (10, 190),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            output_path = timeline_dir / f"frame_{int(time_sec):04d}s.jpg"
            cv2.imwrite(str(output_path), annotated)

        # Export transition frames (where person count changes)
        print("Exporting transition frames...")
        prev_count = None
        transition_num = 0

        for i, detection_data in enumerate(detection_history):
            frame_num = int(detection_data[0])
            person_count = detection_data[3] if len(detection_data) > 3 else 0

            # Detect transition
            if prev_count is not None and person_count != prev_count:
                transition_num += 1
                time_sec = frame_num / fps

                # Export frames around transition (5 seconds before and after)
                for offset in range(-int(5 * fps), int(5 * fps), int(fps)):
                    export_frame_num = frame_num + offset
                    if export_frame_num < 0 or export_frame_num >= frame_count:
                        continue

                    cap.set(cv2.CAP_PROP_POS_FRAMES, export_frame_num)
                    ret, frame = cap.read()
                    if not ret:
                        continue

                    export_time = export_frame_num / fps
                    is_transition = (offset == 0)

                    # Find detection for this frame
                    export_count = person_count
                    for det in detection_history:
                        if abs(det[0] - export_frame_num) < 1:
                            export_count = det[3] if len(det) > 3 else 0
                            break

                    annotated = frame.copy()
                    color = (0, 0, 255) if is_transition else (0, 255, 0)

                    cv2.putText(annotated, f"Transition #{transition_num}: {prev_count}->{person_count} people",
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                    cv2.putText(annotated, f"Time: {export_time:.1f}s ({offset/fps:+.1f}s from transition)",
                               (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    cv2.putText(annotated, f"Person count: {export_count}",
                               (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

                    if is_transition:
                        cv2.putText(annotated, ">>> TRANSITION POINT <<<",
                                   (10, frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

                    output_path = transitions_dir / f"t{transition_num:02d}_{int(export_time):04d}s_{offset/fps:+04.1f}s.jpg"
                    cv2.imwrite(str(output_path), annotated)

            prev_count = person_count

        # Export segment boundary frames
        print("Exporting segment boundary frames...")
        for i, (start, end, start_idx, end_idx) in enumerate(segments, 1):
            # Export start frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(start * fps))
            ret, frame = cap.read()
            if ret:
                annotated = frame.copy()
                cv2.putText(annotated, f"Segment {i} START", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(annotated, f"Time: {start:.1f}s", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                output_path = segments_dir / f"seg{i:02d}_start_{start:.1f}s.jpg"
                cv2.imwrite(str(output_path), annotated)

            # Export end frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(end * fps))
            ret, frame = cap.read()
            if ret:
                annotated = frame.copy()
                cv2.putText(annotated, f"Segment {i} END", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.putText(annotated, f"Time: {end:.1f}s", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                output_path = segments_dir / f"seg{i:02d}_end_{end:.1f}s.jpg"
                cv2.imwrite(str(output_path), annotated)

        cap.release()

        # Export detection data as CSV
        csv_path = output_dir / "detection_data.csv"
        with open(csv_path, 'w') as f:
            f.write("frame_num,time_sec,num_faces,num_poses,person_count,position,blur_score,is_blurry,notes\n")
            prev_count = None
            for detection_data in detection_history:
                frame_num = int(detection_data[0])
                time_sec = frame_num / fps
                num_faces = detection_data[1] if len(detection_data) > 1 else 0
                num_poses = detection_data[2] if len(detection_data) > 2 else 0
                person_count = detection_data[3] if len(detection_data) > 3 else 0
                position = detection_data[4] if len(detection_data) > 4 else 0.5
                blur_score = detection_data[5] if len(detection_data) > 5 else 0
                is_blurry = detection_data[6] if len(detection_data) > 6 else False

                notes = ""
                if prev_count is not None and person_count != prev_count:
                    notes = f"TRANSITION: {prev_count}->{person_count}"

                f.write(f"{frame_num},{time_sec:.2f},{num_faces},{num_poses},{person_count},{position:.3f},{blur_score:.1f},{is_blurry},{notes}\n")
                prev_count = person_count

        print(f"Debug frames saved to: {output_dir}")
        print(f"  - Timeline: {len(list(timeline_dir.glob('*.jpg')))} frames")
        print(f"  - Transitions: {len(list(transitions_dir.glob('*.jpg')))} frames")
        print(f"  - Segments: {len(list(segments_dir.glob('*.jpg')))} frames")
        print(f"  - Detection data CSV: {csv_path}")

    def filter_segments(self, segments: List[Tuple[float, float]], json_output: bool = False) -> List[Tuple[float, float]]:
        """Filter segments using configured rules"""
        if not json_output:
            print(f"[STEP] Filtering segments (found {len(segments)} raw segments)")

        min_dur = self.config.get("filtering.min_duration", 180.0)
        max_dur = self.config.get("filtering.max_duration", 0)
        min_gap = self.config.get("filtering.min_gap", 5.0)
        merge_close = self.config.get("filtering.merge_close_segments", True)

        filtered = []

        for seg in segments:
            # Segments are 4-tuples (start, end, start_idx, end_idx)
            start, end = seg[0], seg[1]
            duration = end - start

            if duration < min_dur:
                continue
            if max_dur > 0 and duration > max_dur:
                continue

            if merge_close and filtered:
                last_start, last_end = filtered[-1]
                gap = start - last_end

                if gap < min_gap:
                    filtered[-1] = (last_start, end)
                    continue

            filtered.append((start, end))

        return filtered

    def clip_video(self, video_path: str, segments: List[Tuple[float, float]], output_dir: str = None, json_output: bool = False) -> List[str]:
        """
        Clip video using configured settings

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
            print(f"[STEP] Creating {len(segments)} video clips")

        video_codec = self.config.get("output.ffmpeg.video_codec", "libx264")
        audio_codec = self.config.get("output.ffmpeg.audio_codec", "aac")
        preset = self.config.get("output.ffmpeg.preset", "fast")
        crf = self.config.get("output.ffmpeg.crf", 23)

        clip_files = []

        for i, (start, end) in enumerate(segments, 1):
            duration = end - start
            minutes = int(duration / 60)
            seconds = int(duration % 60)

            output_path = output_dir / f"{video_name}_clip{i:02d}_{minutes}m{seconds}s.mp4"

            # Emit progress for clipping
            progress = int((i / len(segments)) * 100)
            self._emit_progress("clipping", progress, i, len(segments), f"Creating clip {i}/{len(segments)}")

            if not json_output:
                print(f"  [{i}/{len(segments)}] {start:.1f}s - {end:.1f}s ({minutes}m {seconds}s)")

            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start),
                '-i', video_path,
                '-t', str(duration),
                '-c:v', video_codec,
                '-crf', str(crf),
                '-preset', preset,
                '-c:a', audio_codec,
                str(output_path)
            ]

            subprocess.run(cmd, capture_output=True)
            clip_files.append(str(output_path))

        if not json_output:
            print(f"\nDone! {len(segments)} clips saved to: {output_dir}")

        return clip_files

    def process_video(self, video_path: str, output_dir: str = None, json_output: bool = False) -> dict:
        """
        Complete pipeline - returns structured result

        Returns:
            dict with keys:
                - success: bool
                - segments_detected: list of (start, end) tuples
                - segments_filtered: list of (start, end) tuples
                - clips: list of clip file paths
                - output_dir: path to output directory
                - error: error message if failed
        """
        if not json_output:
            print(f"[STEP] Starting video processing")

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
            segments = self.detect_segments(video_path, json_output)
            # Segments are 4-tuples (start, end, start_idx, end_idx) from detect_segments
            result['segments_detected'] = [(float(seg[0]), float(seg[1])) for seg in segments]

            if not segments:
                if not json_output:
                    print("No segments detected")
                result['error'] = 'No segments detected'
                return result

            filtered = self.filter_segments(segments, json_output)
            result['segments_filtered'] = [(float(s), float(e)) for s, e in filtered]

            if not filtered:
                min_dur = self.config.get("filtering.min_duration", 180.0)
                if not json_output:
                    print(f"\nNo segments passed filtering (min duration: {min_dur/60:.1f} min)")
                    print(f"\nDetected {len(segments)} segments before filtering:")
                    for i, seg in enumerate(segments, 1):
                        start, end = seg[0], seg[1]
                        print(f"  {i}. {start:.1f}s - {end:.1f}s ({(end-start)/60:.1f} min)")
                result['error'] = f'No segments passed filtering (min duration: {min_dur}s)'
                result['success'] = True  # Processing completed successfully, just no clips created
                return result

            if not json_output:
                print(f"\nFinal segments after filtering:")
                for i, (start, end) in enumerate(filtered, 1):
                    print(f"  {i}. {start:.1f}s - {end:.1f}s ({(end-start)/60:.1f} min)")

            clips = self.clip_video(video_path, filtered, output_dir, json_output)
            result['clips'] = clips
            result['output_dir'] = str(Path(clips[0]).parent) if clips else None
            result['debug_dir'] = self.debug_dir  # Include debug directory if frames were exported
            result['success'] = True

            if not json_output:
                print(f"[STEP] Processing complete - {len(clips)} clips created")

            return result

        except Exception as e:
            result['error'] = str(e)
            if not json_output:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
            return result


def main():
    parser = argparse.ArgumentParser(
        description="Unified comedy clipper with multiple detection modes",
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
  python3 clipper_unified.py video.mp4

  # Specify detection mode
  python3 clipper_unified.py video.mp4 --mode scene

  # Use custom config
  python3 clipper_unified.py video.mp4 -c my_config.yaml

  # Enable debug output
  python3 clipper_unified.py video.mp4 -d

  # Override config minimum duration
  python3 clipper_unified.py video.mp4 --min-duration 120

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

    args = parser.parse_args()

    if not os.path.exists(args.video):
        error_msg = f"Error: Video not found: {args.video}"
        if args.json:
            import json
            print(json.dumps({'success': False, 'error': error_msg}))
        else:
            print(error_msg)
        sys.exit(1)

    try:
        # Load config
        config = load_config(args.config)
        if not args.json:
            print(f"Loaded config: {args.config or 'clipper_rules.yaml'}")

        # Override min duration if specified
        if args.min_duration is not None:
            config.raw.setdefault("filtering", {})["min_duration"] = args.min_duration

        # Create clipper
        clipper = UnifiedComedyClipper(config, mode=args.mode, debug=args.debug)

        # Process video
        result = clipper.process_video(args.video, output_dir=args.output, json_output=args.json)

        # Output JSON if requested
        if args.json:
            import json
            print(json.dumps(result, indent=2))

        # Exit with error code if failed
        if not result['success']:
            sys.exit(1)

    except Exception as e:
        error_msg = str(e)
        if args.json:
            import json
            print(json.dumps({'success': False, 'error': error_msg}))
        else:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
