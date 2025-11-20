#!/usr/bin/env python3
"""
Comedy Clipper - Configurable Multi-Modal Detection
Fully rule-based clipper using config file
Supports face + pose detection, Kalman filtering, and custom transition rules
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import subprocess
import cv2
import numpy as np
from datetime import datetime
import mediapipe as mp
from filterpy.kalman import KalmanFilter
from config_loader import load_config, ClipperConfig


class KalmanPositionTracker:
    """Kalman filter for tracking person position over time"""

    def __init__(self, config: ClipperConfig):
        """Initialize Kalman filter from config"""
        self.kf = KalmanFilter(dim_x=2, dim_z=1)

        # State transition matrix (position and velocity)
        self.kf.F = np.array([[1., 1.],  # x = x + v*dt (dt=1)
                              [0., 1.]])  # v = v

        # Measurement function (we only measure position)
        self.kf.H = np.array([[1., 0.]])

        # Measurement noise (from config)
        measurement_noise = config.get("kalman_filter.measurement_noise", 5.0)
        self.kf.R = np.array([[measurement_noise]])

        # Process noise (from config)
        process_noise = config.get("kalman_filter.process_noise", 1.0)
        self.kf.Q = np.array([[process_noise, 0.],
                              [0., process_noise]])

        # Initial state covariance (from config)
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


class ConfigurableClipper:
    """Rule-based clipper using configuration file"""

    def __init__(self, config: ClipperConfig, debug: bool = False):
        """
        Initialize clipper from config.

        Args:
            config: Loaded configuration
            debug: Whether to export debug frames
        """
        self.config = config
        self.debug = debug or config.get("debug.export_frames", False)

        print("Initializing MediaPipe detectors from config...")

        # Face detection
        self.mp_face = mp.solutions.face_detection
        face_conf = config.get("confidence.face_detection.min_detection_confidence", 0.5)
        face_model = config.get("confidence.face_detection.model_selection", 1)
        self.face_detection = self.mp_face.FaceDetection(
            model_selection=face_model,
            min_detection_confidence=face_conf
        )

        # Pose detection
        self.mp_pose = mp.solutions.pose
        pose_det_conf = config.get("confidence.pose_detection.min_detection_confidence", 0.5)
        pose_track_conf = config.get("confidence.pose_detection.min_tracking_confidence", 0.5)
        pose_complexity = config.get("confidence.pose_detection.model_complexity", 1)
        pose_smooth = config.get("confidence.pose_detection.smooth_landmarks", True)

        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=pose_complexity,
            smooth_landmarks=pose_smooth,
            min_detection_confidence=pose_det_conf,
            min_tracking_confidence=pose_track_conf
        )

        # Drawing utilities
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        print("MediaPipe initialized from config!")

    def calculate_blur_score(self, frame) -> float:
        """
        Calculate blur score using Laplacian variance.
        Higher values = sharper image.

        Args:
            frame: BGR video frame

        Returns:
            Blur score (Laplacian variance)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        return float(variance)

    def is_frame_blurry(self, blur_score: float) -> bool:
        """Check if frame is blurry based on config threshold"""
        threshold = self.config.get("blur_detection.threshold", 100.0)
        return blur_score < threshold

    def find_sharp_boundary(self, detection_history, target_frame_idx: int, fps: float) -> Tuple[int, float]:
        """
        Find nearest sharp frame for segment boundary.

        Args:
            detection_history: List of detection tuples including blur scores
            target_frame_idx: Index in detection_history to start from
            fps: Video frame rate

        Returns:
            Tuple of (frame_number, time) for sharp boundary
        """
        if not self.config.get("blur_detection.enabled", True):
            # Blur detection disabled, use target frame
            frame_num = detection_history[target_frame_idx][0]
            return frame_num, frame_num / fps

        max_shift_history = self.config.get("blur_detection.boundary_shift_max_frames", 30)
        min_sharpness = self.config.get("blur_detection.boundary_sharpness_min", 150.0)

        # Calculate approximate frames per history entry
        # (detection_history is sampled, not every frame)
        if len(detection_history) > 1:
            frames_per_entry = abs(detection_history[1][0] - detection_history[0][0])
        else:
            frames_per_entry = 1

        # Convert max shift from video frames to history entries
        max_shift_entries = max(1, int(max_shift_history / frames_per_entry))

        # Search in both directions for sharp frame
        best_idx = target_frame_idx
        best_score = detection_history[target_frame_idx][5] if len(detection_history[target_frame_idx]) > 5 else 0  # blur_score

        # Search forward
        for i in range(target_frame_idx, min(target_frame_idx + max_shift_entries, len(detection_history))):
            if len(detection_history[i]) > 5:
                blur_score = detection_history[i][5]
                if blur_score >= min_sharpness:
                    best_idx = i
                    best_score = blur_score
                    break
                elif blur_score > best_score:
                    best_idx = i
                    best_score = blur_score

        # Search backward if forward didn't find good enough frame
        if best_score < min_sharpness:
            for i in range(target_frame_idx, max(target_frame_idx - max_shift_entries, -1), -1):
                if len(detection_history[i]) > 5:
                    blur_score = detection_history[i][5]
                    if blur_score >= min_sharpness:
                        best_idx = i
                        best_score = blur_score
                        break
                    elif blur_score > best_score:
                        best_idx = i
                        best_score = blur_score

        frame_num = detection_history[best_idx][0]
        time = frame_num / fps

        # Log if boundary was shifted
        if best_idx != target_frame_idx and len(detection_history[target_frame_idx]) > 5:
            shift_frames = abs(detection_history[best_idx][0] - detection_history[target_frame_idx][0])
            original_blur = detection_history[target_frame_idx][5]
            print(f"    Shifted boundary by {shift_frames} frames (blur: {original_blur:.1f} → {best_score:.1f})")

        return frame_num, time

    def calculate_person_count(self, num_faces: int, num_poses: int) -> int:
        """Calculate person count using configured method"""
        method = self.config.get("transition_detection.person_count_method", "min")

        if method == "min":
            return min(num_faces, num_poses)
        elif method == "max":
            return max(num_faces, num_poses)
        elif method == "average":
            return int((num_faces + num_poses) / 2)
        else:
            return min(num_faces, num_poses)  # Default to conservative

    def export_debug_frame(self, frame, frame_num: int,
                          num_faces: int, num_poses: int,
                          person_count: int, position: Optional[float],
                          pose_landmarks_list: List,
                          face_detections_list: List,
                          left_edge: float, right_edge: float,
                          output_path: str, label: str,
                          blur_score: float = 0.0, is_blurry: bool = False):
        """Export debug frame with configured overlays including blur info"""
        frame_copy = frame.copy()
        height, width = frame_copy.shape[:2]

        # Draw overlays based on config
        if self.config.get("debug.overlays.draw_pose_landmarks", True):
            for pose_landmarks in pose_landmarks_list:
                self.mp_drawing.draw_landmarks(
                    frame_copy,
                    pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
                )

        if self.config.get("debug.overlays.draw_face_boxes", True):
            for detection in face_detections_list:
                self.mp_drawing.draw_detection(frame_copy, detection)

        if self.config.get("debug.overlays.draw_stage_boundaries", True):
            cv2.line(frame_copy, (int(left_edge), 0), (int(left_edge), height), (0, 0, 255), 2)
            cv2.line(frame_copy, (int(right_edge), 0), (int(right_edge), height), (0, 0, 255), 2)

        if self.config.get("debug.overlays.draw_position_indicator", True) and position is not None:
            is_at_edge = position < left_edge or position > right_edge
            color = (0, 255, 0) if not is_at_edge else (255, 0, 0)
            cv2.circle(frame_copy, (int(position), height // 2), 20, color, -1)
            cv2.line(frame_copy, (int(position), 0), (int(position), height), color, 2)

        # Draw text info
        if self.config.get("debug.overlays.draw_text_info", True):
            text_items = self.config.get("debug.text_info", [])

            # Semi-transparent background
            overlay = frame_copy.copy()
            text_height = len(text_items) * 35 + 40
            cv2.rectangle(overlay, (0, 0), (600, text_height), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.5, frame_copy, 0.5, 0, frame_copy)

            y_offset = 30
            for item in text_items:
                if item == "frame_number":
                    text = f"{label} - Frame {frame_num}"
                elif item == "num_faces":
                    text = f"Faces: {num_faces}"
                elif item == "num_poses":
                    text = f"Poses: {num_poses}"
                elif item == "person_count":
                    text = f"Person Count: {person_count}"
                elif item == "confidence_score":
                    text = f"Confidence: {person_count}/2"
                elif item == "position" and position is not None:
                    text = f"Position: {int(position)}px"
                elif item == "status":
                    if position is not None:
                        is_at_edge = position < left_edge or position > right_edge
                        status = "AT EDGE" if is_at_edge else "CENTER STAGE"
                    else:
                        status = "NOT DETECTED"
                    text = f"Status: {status}"
                else:
                    continue

                cv2.putText(frame_copy, text, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                y_offset += 35

            # Always show blur score if blur detection is enabled
            if self.config.get("blur_detection.enabled", True):
                blur_color = (0, 255, 0) if not is_blurry else (0, 0, 255)  # Green if sharp, red if blurry
                blur_text = f"Blur: {blur_score:.1f} ({'BLURRY' if is_blurry else 'SHARP'})"
                cv2.putText(frame_copy, blur_text, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, blur_color, 2)
                y_offset += 35

        cv2.imwrite(output_path, frame_copy)
        print(f"  Exported: {Path(output_path).name}")

    def detect_segments(self, video_path: str) -> List[Tuple[float, float]]:
        """Detect segments using configured rules"""
        print(f"Analyzing video with configured detection rules...")
        print("This may take a few minutes...")

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

        print(f"Video: {duration:.1f}s, {fps:.1f} fps, {total_frames} frames, {frame_width}px wide")

        # Sample rate from config
        sample_rate = self.config.get("processing.sample_rate", 30)
        sample_interval = int(sample_rate)

        # Track detections over time
        detection_history = []
        debug_data = {}

        # Kalman filter
        use_kalman = self.config.get("kalman_filter.enabled", True)
        kalman_tracker = KalmanPositionTracker(self.config) if use_kalman else None

        # Blur detection
        use_blur_detection = self.config.get("blur_detection.enabled", True)
        log_blurry = self.config.get("blur_detection.log_blurry_frames", False)
        blur_count = 0

        # Edge zones
        exit_threshold = self.config.get("position_detection.exit_threshold", 0.15)
        left_edge = frame_width * exit_threshold
        right_edge = frame_width * (1 - exit_threshold)

        frame_num = 0
        checked_frames = 0

        print("\nProcessing frames...")
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_num % sample_interval == 0:
                # Calculate blur score before converting to RGB
                blur_score = 0.0
                is_blurry = False
                if use_blur_detection:
                    blur_score = self.calculate_blur_score(frame)
                    is_blurry = self.is_frame_blurry(blur_score)
                    if is_blurry:
                        blur_count += 1
                        if log_blurry:
                            print(f"  Blurry frame {frame_num}: score={blur_score:.1f}")

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Face detection
                face_results = self.face_detection.process(rgb_frame)
                num_faces = 0
                face_positions = []
                face_detections_list = []

                if face_results.detections:
                    for detection in face_results.detections:
                        num_faces += 1
                        bbox = detection.location_data.relative_bounding_box
                        center_x = (bbox.xmin + bbox.width / 2) * frame_width
                        face_positions.append(center_x)
                        face_detections_list.append(detection)

                # Pose detection
                pose_results = self.pose.process(rgb_frame)
                num_poses = 0
                pose_positions = []
                pose_landmarks_list = []

                if pose_results.pose_landmarks:
                    num_poses = 1
                    landmarks = pose_results.pose_landmarks.landmark

                    # Calculate torso center
                    left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
                    right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
                    left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
                    right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]

                    torso_x = (left_shoulder.x + right_shoulder.x + left_hip.x + right_hip.x) / 4
                    pose_positions.append(torso_x * frame_width)
                    pose_landmarks_list.append(pose_results.pose_landmarks)

                # Calculate person count using configured method
                person_count = self.calculate_person_count(num_faces, num_poses)

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

                if self.debug:
                    debug_data[frame_num] = (pose_landmarks_list, face_detections_list, blur_score, is_blurry)

                checked_frames += 1

                if checked_frames % 60 == 0:
                    progress = (frame_num / total_frames) * 100
                    print(f"  Progress: {progress:.1f}% ({frame_num}/{total_frames} frames)")

            frame_num += 1

        cap.release()
        print(f"Analyzed {checked_frames} frames")
        if use_blur_detection:
            blur_pct = (blur_count / checked_frames * 100) if checked_frames > 0 else 0
            print(f"Blurry frames: {blur_count}/{checked_frames} ({blur_pct:.1f}%)")

        # Analyze transitions using config rules
        segments = self._analyze_transitions(detection_history, fps, left_edge, right_edge,
                                            debug_data, video_path)

        return segments

    def _analyze_transitions(self, detection_history, fps, left_edge, right_edge,
                            debug_data, video_path) -> List[Tuple[float, float]]:
        """Analyze person count transitions using configured rules"""
        print("\nAnalyzing person count transitions...")

        segments = []
        segment_frames = []
        current_start = None
        current_start_idx = None
        prev_count = 0

        # Stability tracking
        stability_frames = self.config.get("transition_detection.transition_stability_frames", 3)
        stable_count = 0
        stable_value = 0

        for i, detection_data in enumerate(detection_history):
            # Unpack with backward compatibility
            if len(detection_data) >= 7:
                frame_num, num_faces, num_poses, person_count, position, blur_score, is_blurry = detection_data
            else:
                frame_num, num_faces, num_poses, person_count, position = detection_data
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
                # Check if this transition matches any rule
                if self.config.should_start_segment(prev_count, person_count):
                    if current_start is None:
                        current_start = time
                        current_start_idx = i
                        segment_frames.append([])
                        print(f"  Segment start at {time:.1f}s: {prev_count}→{person_count} people")

                elif self.config.should_end_segment(prev_count, person_count):
                    if current_start is not None:
                        segments.append((current_start, time, current_start_idx, i))  # Include start and end indices
                        print(f"  Segment end at {time:.1f}s: {prev_count}→{person_count} people")
                        current_start = None
                        current_start_idx = None

                prev_count = person_count

            # Track frames for debug
            if current_start is not None and segment_frames:
                segment_frames[-1].append((
                    frame_num, num_faces, num_poses, person_count, position, blur_score
                ))

        # Final segment
        if current_start is not None:
            final_time = detection_history[-1][0] / fps
            segments.append((current_start, final_time, current_start_idx, len(detection_history) - 1))

        print(f"Detected {len(segments)} segments from transitions")

        # Get video duration for clamping
        video_duration = detection_history[-1][0] / fps if detection_history else 0

        # Apply blur-based boundary shifting and time buffer
        if segments:
            # Get buffer settings
            buffer_before = self.config.get("filtering.buffer_before_start", 2.0)
            buffer_after = self.config.get("filtering.buffer_after_end", 2.0)

            if self.config.get("blur_detection.enabled", True):
                print("\nAdjusting boundaries to avoid blurry frames...")

            shifted_segments = []
            for start_time, end_time, start_idx, end_idx in segments:
                # Shift boundaries to sharp frames if blur detection enabled
                if self.config.get("blur_detection.enabled", True):
                    _, shifted_start = self.find_sharp_boundary(detection_history, start_idx, fps)
                    _, shifted_end = self.find_sharp_boundary(detection_history, end_idx, fps)
                else:
                    shifted_start = start_time
                    shifted_end = end_time

                # Apply time buffer
                buffered_start = max(0, shifted_start - buffer_before)
                buffered_end = min(video_duration, shifted_end + buffer_after)

                shifted_segments.append((buffered_start, buffered_end))

            # Replace original segments with shifted and buffered ones
            segments = shifted_segments

            if buffer_before > 0 or buffer_after > 0:
                print(f"Applied time buffer: -{buffer_before}s before start, +{buffer_after}s after end")

        # Fallback to position-based if enabled and no segments found
        if len(segments) == 0 and self.config.get("position_detection.enabled", True):
            print("No transitions found. Using position-based fallback...")
            segments = self._position_based_detection(detection_history, fps, left_edge, right_edge)
            segment_frames = []  # Reset for position-based

        # Export debug frames
        if self.debug and segments:
            self._export_debug_frames(segments, segment_frames, debug_data,
                                     left_edge, right_edge, video_path, fps)

        return segments

    def _position_based_detection(self, detection_history, fps, left_edge, right_edge):
        """Fallback: position-based detection"""
        segments = []
        current_start = None

        for i, detection_data in enumerate(detection_history):
            # Unpack with backward compatibility
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
                        current_start = (time, i)  # Store index for boundary shift
                elif current_start is not None:
                    segments.append((current_start[0], time, current_start[1], i))
                    current_start = None

        if current_start is not None:
            final_time = detection_history[-1][0] / fps
            segments.append((current_start[0], final_time, current_start[1], len(detection_history) - 1))

        print(f"Detected {len(segments)} segments from position")

        # Get video duration for clamping
        video_duration = detection_history[-1][0] / fps if detection_history else 0

        # Get buffer settings
        buffer_before = self.config.get("filtering.buffer_before_start", 2.0)
        buffer_after = self.config.get("filtering.buffer_after_end", 2.0)

        # Apply blur-based boundary shifting and time buffer
        if segments:
            if self.config.get("blur_detection.enabled", True):
                print("\nAdjusting position-based boundaries to avoid blurry frames...")

            shifted_segments = []
            for start_time, end_time, start_idx, end_idx in segments:
                # Shift boundaries to sharp frames if blur detection enabled
                if self.config.get("blur_detection.enabled", True):
                    _, shifted_start = self.find_sharp_boundary(detection_history, start_idx, fps)
                    _, shifted_end = self.find_sharp_boundary(detection_history, end_idx, fps)
                else:
                    shifted_start = start_time
                    shifted_end = end_time

                # Apply time buffer
                buffered_start = max(0, shifted_start - buffer_before)
                buffered_end = min(video_duration, shifted_end + buffer_after)

                shifted_segments.append((buffered_start, buffered_end))

            if buffer_before > 0 or buffer_after > 0:
                print(f"Applied time buffer: -{buffer_before}s before start, +{buffer_after}s after end")

            return shifted_segments

        # If no segments, return empty list
        return []

    def _export_debug_frames(self, segments, segment_frames, debug_data,
                            left_edge, right_edge, video_path, fps):
        """Export debug frames based on config"""
        print("\nExporting debug frames...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_name = Path(video_path).stem
        debug_suffix = self.config.get("output.debug_folder_suffix", "debug")
        output_dir = Path(video_path).parent / f"{video_name}_{debug_suffix}_{timestamp}"
        output_dir.mkdir(exist_ok=True)

        cap = cv2.VideoCapture(video_path)

        export_first = self.config.get("debug.export_first_frame", True)
        export_last = self.config.get("debug.export_last_frame", True)

        for seg_idx, frames_data in enumerate(segment_frames[:len(segments)], 1):
            if not frames_data:
                continue

            # First frame
            if export_first:
                first_data = frames_data[0]
                # Unpack with backward compatibility
                if len(first_data) >= 6:
                    frame_num, faces, poses, count, pos, blur = first_data
                else:
                    frame_num, faces, poses, count, pos = first_data[:5]
                    blur = 0.0

                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                if ret and frame_num in debug_data:
                    debug_info = debug_data[frame_num]
                    if len(debug_info) >= 4:
                        pose_lm, face_det, blur_score, is_blurry = debug_info
                    else:
                        pose_lm, face_det = debug_info[:2]
                        blur_score = blur
                        is_blurry = False

                    output_path = str(output_dir / f"seg{seg_idx:02d}_first_f{frame_num}_blur{int(blur_score)}.jpg")
                    self.export_debug_frame(
                        frame, frame_num, faces, poses, count, pos,
                        pose_lm, face_det, left_edge, right_edge,
                        output_path, f"Segment {seg_idx} FIRST",
                        blur_score=blur_score, is_blurry=is_blurry
                    )

            # Last frame
            if export_last:
                last_data = frames_data[-1]
                # Unpack with backward compatibility
                if len(last_data) >= 6:
                    frame_num, faces, poses, count, pos, blur = last_data
                else:
                    frame_num, faces, poses, count, pos = last_data[:5]
                    blur = 0.0

                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                if ret and frame_num in debug_data:
                    debug_info = debug_data[frame_num]
                    if len(debug_info) >= 4:
                        pose_lm, face_det, blur_score, is_blurry = debug_info
                    else:
                        pose_lm, face_det = debug_info[:2]
                        blur_score = blur
                        is_blurry = False

                    output_path = str(output_dir / f"seg{seg_idx:02d}_last_f{frame_num}_blur{int(blur_score)}.jpg")
                    self.export_debug_frame(
                        frame, frame_num, faces, poses, count, pos,
                        pose_lm, face_det, left_edge, right_edge,
                        output_path, f"Segment {seg_idx} LAST",
                        blur_score=blur_score, is_blurry=is_blurry
                    )

        cap.release()
        print(f"Debug frames saved to: {output_dir}")

    def filter_segments(self, segments: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Filter segments using configured rules"""
        min_dur = self.config.get("filtering.min_duration", 180.0)
        max_dur = self.config.get("filtering.max_duration", 0)
        min_gap = self.config.get("filtering.min_gap", 5.0)
        merge_close = self.config.get("filtering.merge_close_segments", True)

        filtered = []

        for start, end in segments:
            duration = end - start

            # Duration filters
            if duration < min_dur:
                continue
            if max_dur > 0 and duration > max_dur:
                continue

            # Merge close segments
            if merge_close and filtered:
                last_start, last_end = filtered[-1]
                gap = start - last_end

                if gap < min_gap:
                    # Merge with previous
                    filtered[-1] = (last_start, end)
                    continue

            filtered.append((start, end))

        return filtered

    def clip_video(self, video_path: str, segments: List[Tuple[float, float]], output_dir: str = None):
        """Clip video using configured settings"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_name = Path(video_path).stem

        if output_dir is None:
            base_dir = Path(video_path).parent
        else:
            base_dir = Path(output_dir)

        clips_suffix = self.config.get("output.clips_folder_suffix", "clips")
        output_dir = base_dir / f"{video_name}_{clips_suffix}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nClipping {len(segments)} segments...")

        # FFmpeg settings from config
        video_codec = self.config.get("output.ffmpeg.video_codec", "libx264")
        audio_codec = self.config.get("output.ffmpeg.audio_codec", "aac")
        preset = self.config.get("output.ffmpeg.preset", "fast")
        crf = self.config.get("output.ffmpeg.crf", 23)

        for i, (start, end) in enumerate(segments, 1):
            duration = end - start
            minutes = int(duration / 60)
            seconds = int(duration % 60)

            output_path = output_dir / f"{video_name}_comedian{i:02d}_{minutes}m{seconds}s.mp4"

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

        print(f"\nDone! {len(segments)} clips saved to: {output_dir}")

    def process_video(self, video_path: str, output_dir: str = None):
        """Complete pipeline using config"""
        segments = self.detect_segments(video_path)

        if not segments:
            print("No segments detected")
            return

        filtered = self.filter_segments(segments)

        if not filtered:
            min_dur = self.config.get("filtering.min_duration", 180.0)
            print(f"\nNo segments passed filtering (min duration: {min_dur/60:.1f} min)")
            print(f"\nDetected {len(segments)} segments before filtering:")
            for i, (start, end) in enumerate(segments, 1):
                print(f"  {i}. {start:.1f}s - {end:.1f}s ({(end-start)/60:.1f} min)")
            return

        print(f"\nFinal segments after filtering:")
        for i, (start, end) in enumerate(filtered, 1):
            print(f"  {i}. {start:.1f}s - {end:.1f}s ({(end-start)/60:.1f} min)")

        self.clip_video(video_path, filtered, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Configurable comedy clipper with rule-based detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default config
  python3 clipper_configurable.py test_vid.MOV

  # Use custom config
  python3 clipper_configurable.py test_vid.MOV -c my_rules.yaml

  # Enable debug
  python3 clipper_configurable.py test_vid.MOV -d

Configuration:
  Edit clipper_rules.yaml to customize detection rules
  - Transition rules (person count changes)
  - Position-based fallback
  - Kalman filter parameters
  - Segment filtering
  - Debug overlays
        """
    )

    parser.add_argument('video', help='Input video file')
    parser.add_argument('-c', '--config', help='Config file (default: clipper_rules.yaml)')
    parser.add_argument('-o', '--output', help='Output directory for clips')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"Error: Video not found: {args.video}")
        sys.exit(1)

    try:
        # Load config
        config = load_config(args.config)
        print(f"Loaded config: {args.config or 'clipper_rules.yaml'}")

        # Create clipper
        clipper = ConfigurableClipper(config, debug=args.debug)

        # Process video
        clipper.process_video(args.video, output_dir=args.output)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
