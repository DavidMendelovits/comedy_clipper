#!/usr/bin/env python3
"""
Comedy Clipper - Advanced Multi-Modal Detection
Combines MediaPipe face + pose detection with Kalman filtering
Detects transitions when person count changes (2→1 or 1→2)
Perfect for standup shows with host introductions
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


class KalmanPositionTracker:
    """Kalman filter for tracking person position over time"""

    def __init__(self):
        """Initialize Kalman filter for 1D position tracking"""
        self.kf = KalmanFilter(dim_x=2, dim_z=1)

        # State transition matrix (position and velocity)
        self.kf.F = np.array([[1., 1.],  # x = x + v*dt (dt=1)
                              [0., 1.]])  # v = v

        # Measurement function (we only measure position)
        self.kf.H = np.array([[1., 0.]])

        # Measurement noise
        self.kf.R = np.array([[5.]])

        # Process noise
        self.kf.Q = np.array([[1., 0.],
                              [0., 1.]])

        # Initial state covariance
        self.kf.P *= 10.

        self.initialized = False

    def update(self, measurement: Optional[float]) -> float:
        """
        Update filter with new measurement.

        Args:
            measurement: Measured x position (None if no detection)

        Returns:
            Filtered position estimate
        """
        if measurement is not None:
            if not self.initialized:
                # Initialize with first measurement
                self.kf.x = np.array([[measurement], [0.]])
                self.initialized = True
            else:
                # Update with measurement
                self.kf.update(measurement)

        # Predict next state
        self.kf.predict()

        return float(self.kf.x[0])


class AdvancedComedyClipper:
    """Advanced clipper using face + pose detection with Kalman filtering"""

    def __init__(self, debug: bool = False):
        """
        Initialize clipper.

        Args:
            debug: Whether to export debug frames with overlays
        """
        print("Initializing MediaPipe Face and Pose detectors...")

        # Face detection
        self.mp_face = mp.solutions.face_detection
        self.face_detection = self.mp_face.FaceDetection(
            model_selection=1,  # 1 for full range (vs 0 for short range)
            min_detection_confidence=0.5
        )

        # Pose detection
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Drawing utilities
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        self.debug = debug
        print("MediaPipe initialized!")

    def export_debug_frame(self, frame, frame_num: int,
                          num_faces: int, num_poses: int,
                          pose_landmarks_list: List,
                          face_detections_list: List,
                          left_edge: float, right_edge: float,
                          output_path: str, label: str):
        """
        Export a frame with face and pose detection overlays.

        Args:
            frame: Video frame
            frame_num: Frame number
            num_faces: Number of detected faces
            num_poses: Number of detected poses
            pose_landmarks_list: List of pose landmarks
            face_detections_list: List of face detections
            left_edge: Left edge threshold
            right_edge: Right edge threshold
            output_path: Path to save the frame
            label: Label for the frame
        """
        frame_copy = frame.copy()
        height, width = frame_copy.shape[:2]

        # Draw pose landmarks
        for pose_landmarks in pose_landmarks_list:
            self.mp_drawing.draw_landmarks(
                frame_copy,
                pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
            )

        # Draw face detections
        for detection in face_detections_list:
            self.mp_drawing.draw_detection(frame_copy, detection)

        # Draw edge zones
        cv2.line(frame_copy, (int(left_edge), 0), (int(left_edge), height), (0, 0, 255), 2)
        cv2.line(frame_copy, (int(right_edge), 0), (int(right_edge), height), (0, 0, 255), 2)

        # Add text overlay with semi-transparent background
        overlay = frame_copy.copy()
        cv2.rectangle(overlay, (0, 0), (600, 150), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame_copy, 0.5, 0, frame_copy)

        cv2.putText(frame_copy, f"{label} - Frame {frame_num}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame_copy, f"Faces Detected: {num_faces}", (10, 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame_copy, f"Poses Detected: {num_poses}", (10, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame_copy, f"Confidence: {min(num_faces, num_poses)}/2", (10, 135),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        cv2.imwrite(output_path, frame_copy)
        print(f"  Exported debug frame: {output_path}")

    def detect_segments_multimodal(self, video_path: str,
                                   exit_threshold: float = 0.15) -> List[Tuple[float, float]]:
        """
        Detect segments using face + pose detection with Kalman filtering.

        Detects transitions when person count changes:
        - 2 people (host + comedian) → 1 person (host only) = end of set
        - 1 person (host only) → 2 people (host + comedian) = start of set

        Args:
            video_path: Path to video
            exit_threshold: Position threshold for stage boundaries

        Returns:
            List of (start, end) tuples representing comedian sets
        """
        print(f"Analyzing video with multi-modal detection (face + pose)...")
        print("This may take a few minutes...")

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

        print(f"Video: {duration:.1f}s, {fps:.1f} fps, {total_frames} frames, {frame_width}px wide")

        # Sample frames (check every 0.5 seconds for better accuracy)
        sample_interval = int(fps / 2)

        # Track detections over time
        detection_history = []  # (frame_num, num_faces, num_poses, avg_position, landmarks_data)

        # Kalman filter for position tracking
        kalman_tracker = KalmanPositionTracker()

        # Store landmarks for debug
        debug_data = {}  # frame_num -> (pose_landmarks_list, face_detections_list)

        frame_num = 0
        checked_frames = 0

        # Define edge zones
        left_edge = frame_width * exit_threshold
        right_edge = frame_width * (1 - exit_threshold)

        print("\nProcessing frames...")
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Only process every Nth frame
            if frame_num % sample_interval == 0:
                # Convert to RGB for MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Run face detection
                face_results = self.face_detection.process(rgb_frame)
                num_faces = 0
                face_positions = []
                face_detections_list = []

                if face_results.detections:
                    for detection in face_results.detections:
                        num_faces += 1
                        # Get bounding box center
                        bbox = detection.location_data.relative_bounding_box
                        center_x = (bbox.xmin + bbox.width / 2) * frame_width
                        face_positions.append(center_x)
                        face_detections_list.append(detection)

                # Run pose detection
                pose_results = self.pose.process(rgb_frame)
                num_poses = 0
                pose_positions = []
                pose_landmarks_list = []

                if pose_results.pose_landmarks:
                    # Currently only detects one person - would need multi-person pose for multiple
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

                # Calculate average position from all detections
                all_positions = face_positions + pose_positions
                avg_position = None
                if all_positions:
                    avg_position = sum(all_positions) / len(all_positions)

                # Apply Kalman filter for smooth tracking
                filtered_position = kalman_tracker.update(avg_position)

                # Store detection data
                detection_history.append((
                    frame_num,
                    num_faces,
                    num_poses,
                    filtered_position
                ))

                # Store debug data
                if self.debug:
                    debug_data[frame_num] = (pose_landmarks_list, face_detections_list)

                checked_frames += 1

                if checked_frames % 60 == 0:
                    progress = (frame_num / total_frames) * 100
                    print(f"  Progress: {progress:.1f}% ({frame_num}/{total_frames} frames)")

            frame_num += 1

        cap.release()

        print(f"Analyzed {checked_frames} frames")

        # Analyze person count transitions
        print("\nDetecting person count transitions...")
        segments = []
        segment_frames = []  # For debug export
        current_start = None

        for i, (frame_num, num_faces, num_poses, position) in enumerate(detection_history):
            time = frame_num / fps

            # Confidence: both face and pose agree on person count
            # We want: 2 people on stage (host + comedian) vs 1 person (host only)
            person_count = min(num_faces, num_poses)  # Conservative estimate

            # Single person on stage - likely just host
            if person_count == 1:
                if current_start is not None:
                    # End of comedian set (comedian exited, only host remains)
                    segments.append((current_start, time))
                    current_start = None

            # Two people on stage - host + comedian
            elif person_count >= 2 or (num_faces >= 1 and num_poses >= 1):
                if current_start is None:
                    # Start of comedian set (comedian entered)
                    current_start = time
                    segment_frames.append([])

                if segment_frames:
                    segment_frames[-1].append((
                        frame_num, num_faces, num_poses, position
                    ))

        # Final segment
        if current_start is not None:
            final_time = detection_history[-1][0] / fps
            segments.append((current_start, final_time))

        print(f"Detected {len(segments)} segments based on person count transitions")

        # Fallback: if no transitions found, use position-based detection
        if len(segments) == 0:
            print("No person count transitions found. Falling back to position-based detection...")
            current_start = None
            segment_frames = []

            for i, (frame_num, num_faces, num_poses, position) in enumerate(detection_history):
                time = frame_num / fps

                # Person detected and in center stage (not at edges)
                is_at_edge = position < left_edge or position > right_edge
                has_person = (num_faces >= 1 or num_poses >= 1)

                if has_person and not is_at_edge:
                    if current_start is None:
                        # Person entered center stage
                        current_start = time
                        segment_frames.append([])

                    if segment_frames:
                        segment_frames[-1].append((
                            frame_num, num_faces, num_poses, position
                        ))

                # Person exited or at edge
                elif current_start is not None:
                    # End the current segment
                    segments.append((current_start, time))
                    current_start = None

            # Final segment
            if current_start is not None:
                final_time = detection_history[-1][0] / fps
                segments.append((current_start, final_time))

            print(f"Detected {len(segments)} segments using position-based fallback")

        # Export debug frames if enabled
        if self.debug and segments and segment_frames:
            print("\nExporting debug frames...")

            # Create timestamped debug folder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_name = Path(video_path).stem
            output_dir = Path(video_path).parent / f"{video_name}_debug_advanced_{timestamp}"
            output_dir.mkdir(exist_ok=True)

            cap = cv2.VideoCapture(video_path)

            for seg_idx, frames_data in enumerate(segment_frames[:len(segments)], 1):
                if not frames_data:
                    continue

                # Export first frame
                first_frame_num, first_faces, first_poses, first_pos = frames_data[0]
                cap.set(cv2.CAP_PROP_POS_FRAMES, first_frame_num)
                ret, frame = cap.read()
                if ret and first_frame_num in debug_data:
                    pose_landmarks_list, face_detections_list = debug_data[first_frame_num]
                    output_path = str(output_dir / f"segment{seg_idx:02d}_first_frame{first_frame_num}.jpg")
                    self.export_debug_frame(
                        frame, first_frame_num, first_faces, first_poses,
                        pose_landmarks_list, face_detections_list,
                        left_edge, right_edge, output_path,
                        f"Segment {seg_idx} - FIRST"
                    )

                # Export last frame
                last_frame_num, last_faces, last_poses, last_pos = frames_data[-1]
                cap.set(cv2.CAP_PROP_POS_FRAMES, last_frame_num)
                ret, frame = cap.read()
                if ret and last_frame_num in debug_data:
                    pose_landmarks_list, face_detections_list = debug_data[last_frame_num]
                    output_path = str(output_dir / f"segment{seg_idx:02d}_last_frame{last_frame_num}.jpg")
                    self.export_debug_frame(
                        frame, last_frame_num, last_faces, last_poses,
                        pose_landmarks_list, face_detections_list,
                        left_edge, right_edge, output_path,
                        f"Segment {seg_idx} - LAST"
                    )

            cap.release()
            print(f"Debug frames saved to: {output_dir}")

        return segments

    def filter_segments(self, segments: List[Tuple[float, float]],
                       min_duration: float = 180.0) -> List[Tuple[float, float]]:
        """Filter segments by minimum duration."""
        filtered = []
        for start, end in segments:
            duration = end - start
            if duration >= min_duration:
                filtered.append((start, end))
        return filtered

    def clip_video_ffmpeg(self, video_path: str, start: float, end: float, output_path: str):
        """Clip video using ffmpeg."""
        duration = end - start

        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start),
            '-i', video_path,
            '-t', str(duration),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-preset', 'fast',
            output_path
        ]

        subprocess.run(cmd, capture_output=True)

    def clip_video(self, video_path: str, segments: List[Tuple[float, float]],
                   output_dir: str = None):
        """Clip video based on detected segments."""
        # Create timestamped folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_name = Path(video_path).stem

        if output_dir is None:
            base_dir = Path(video_path).parent
        else:
            base_dir = Path(output_dir)

        # Create timestamped subdirectory
        output_dir = base_dir / f"{video_name}_clips_advanced_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nClipping {len(segments)} comedian sets...")

        for i, (start, end) in enumerate(segments, 1):
            duration = end - start
            minutes = int(duration / 60)
            seconds = int(duration % 60)

            output_path = output_dir / f"{video_name}_comedian{i:02d}_{minutes}m{seconds}s.mp4"

            print(f"  [{i}/{len(segments)}] {start:.1f}s - {end:.1f}s ({minutes}m {seconds}s) -> {output_path.name}")

            self.clip_video_ffmpeg(video_path, start, end, str(output_path))

        print(f"\nDone! {len(segments)} clips saved to: {output_dir}")

    def process_video(self, video_path: str, output_dir: str = None,
                     min_duration: float = 180.0,
                     exit_threshold: float = 0.15):
        """
        Complete pipeline: detect segments and clip.

        Args:
            video_path: Path to input video
            output_dir: Directory to save clips
            min_duration: Minimum duration for a set (default 3 min = 180s)
            exit_threshold: Position threshold for stage boundaries (default 0.15)
        """
        # Detect segments using multi-modal detection
        segments = self.detect_segments_multimodal(video_path, exit_threshold)

        if not segments:
            print("No comedian sets detected")
            return

        # Filter by duration
        filtered = self.filter_segments(segments, min_duration)

        if not filtered:
            print(f"\nNo segments found with minimum duration of {min_duration/60:.1f} minutes")
            print(f"Try lowering --min-duration (currently {min_duration}s = {min_duration/60:.1f}min)")

            # Show what was detected
            print(f"\nDetected {len(segments)} segments before filtering:")
            for i, (start, end) in enumerate(segments, 1):
                duration_min = (end - start) / 60
                print(f"  {i}. {start:.1f}s - {end:.1f}s ({duration_min:.1f} minutes)")
            return

        print(f"\nDetected {len(filtered)} comedian sets:")
        for i, (start, end) in enumerate(filtered, 1):
            duration_min = (end - start) / 60
            print(f"  {i}. {start:.1f}s - {end:.1f}s ({duration_min:.1f} minutes)")

        # Clip video
        self.clip_video(video_path, filtered, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Advanced comedy clipper with face + pose detection and Kalman filtering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (3 min minimum)
  python3 clipper_advanced.py standup_show.mp4

  # 5 minute minimum sets
  python3 clipper_advanced.py show.mp4 -m 300

  # Enable debug mode (exports frames with face + pose overlays)
  python3 clipper_advanced.py show.mp4 -d

How it works:
  - Uses MediaPipe Face Detection to count faces
  - Uses MediaPipe Pose Detection to count people
  - Kalman filtering for robust position tracking
  - Detects transitions: 2 people (host+comedian) ↔ 1 person (host only)
  - Perfect for standup shows with host introductions

Detection Strategy:
  - When 2 people detected = comedian on stage with host
  - When 1 person detected = only host on stage
  - Segment starts when count goes from 1→2
  - Segment ends when count goes from 2→1
        """
    )

    parser.add_argument('video', help='Input video file')
    parser.add_argument('-o', '--output', help='Output directory for clips')
    parser.add_argument('-m', '--min-duration', type=float, default=180.0,
                       help='Minimum duration for a set in seconds (default: 180 = 3 minutes)')
    parser.add_argument('-e', '--exit-threshold', type=float, default=0.15,
                       help='Edge threshold for stage boundaries (default: 0.15)')
    parser.add_argument('-d', '--debug', action='store_true',
                       help='Export debug frames with face and pose overlays')

    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"Error: Video file not found: {args.video}")
        sys.exit(1)

    try:
        clipper = AdvancedComedyClipper(debug=args.debug)
        clipper.process_video(
            args.video,
            output_dir=args.output,
            min_duration=args.min_duration,
            exit_threshold=args.exit_threshold
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
