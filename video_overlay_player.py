#!/usr/bin/env python3
"""
Interactive Video Overlay Player
Plays videos with real-time detection overlays (YOLO pose, MediaPipe, face detection)
Supports toggling overlays, adjusting speed, and seeking
"""

import os
import sys
import argparse
from pathlib import Path
import cv2
import numpy as np
import subprocess
from datetime import datetime

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    YOLO = None

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None


class VideoOverlayPlayer:
    """Interactive video player with detection overlays"""

    def __init__(self, video_path: str, detection_modes: list = None):
        """
        Initialize player.

        Args:
            video_path: Path to video file
            detection_modes: List of detection modes to enable
                            ['yolo_pose', 'mediapipe_pose', 'mediapipe_face']
        """
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)

        if not self.cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.duration = self.total_frames / self.fps

        print(f"Video: {self.duration:.1f}s, {self.fps:.1f} fps, {self.total_frames} frames")
        print(f"Size: {self.frame_width}x{self.frame_height}px")

        # Detection state
        self.detection_modes = detection_modes or ['yolo_pose']
        self.detectors = {}

        # Overlay settings
        self.show_yolo_pose = 'yolo_pose' in self.detection_modes
        self.show_mediapipe_pose = 'mediapipe_pose' in self.detection_modes
        self.show_mediapipe_face = 'mediapipe_face' in self.detection_modes
        self.show_info = True
        self.show_stage_boundary = True
        self.overlay_opacity = 0.7

        # Playback state
        self.playing = True
        self.current_frame = 0
        self.playback_speed = 1.0

        # Stage boundary (can be configured)
        self.stage_boundary = {
            'left': 0.15,
            'right': 0.85,
            'top': 0.1,
            'bottom': 0.85
        }

        self._init_detectors()

    def _init_detectors(self):
        """Initialize requested detectors"""
        if 'yolo_pose' in self.detection_modes:
            if not YOLO_AVAILABLE:
                print("Warning: YOLO not available. Install: pip install ultralytics")
                self.show_yolo_pose = False
            else:
                print("Loading YOLO pose model...")
                self.detectors['yolo_pose'] = YOLO('yolo11n-pose.pt')
                print("  YOLO pose model loaded")

        if 'mediapipe_pose' in self.detection_modes or 'mediapipe_face' in self.detection_modes:
            if not MEDIAPIPE_AVAILABLE:
                print("Warning: MediaPipe not available. Install: pip install mediapipe")
                self.show_mediapipe_pose = False
                self.show_mediapipe_face = False
            else:
                if 'mediapipe_pose' in self.detection_modes:
                    print("Loading MediaPipe pose...")
                    mp_pose = mp.solutions.pose
                    self.detectors['mediapipe_pose'] = mp_pose.Pose(
                        static_image_mode=False,
                        model_complexity=1,
                        smooth_landmarks=True,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5
                    )
                    self.detectors['mp_pose_module'] = mp_pose
                    self.detectors['mp_drawing'] = mp.solutions.drawing_utils
                    self.detectors['mp_drawing_styles'] = mp.solutions.drawing_styles
                    print("  MediaPipe pose loaded")

                if 'mediapipe_face' in self.detection_modes:
                    print("Loading MediaPipe face detection...")
                    mp_face = mp.solutions.face_detection
                    self.detectors['mediapipe_face'] = mp_face.FaceDetection(
                        model_selection=1,
                        min_detection_confidence=0.5
                    )
                    print("  MediaPipe face detection loaded")

    def _draw_yolo_pose(self, frame, detections):
        """Draw YOLO pose detections"""
        overlay = frame.copy()

        # COCO keypoint connections for skeleton
        SKELETON = [
            (0, 1), (0, 2), (1, 3), (2, 4),  # Head
            (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # Arms
            (5, 11), (6, 12), (11, 12),  # Torso
            (11, 13), (13, 15), (12, 14), (14, 16)  # Legs
        ]

        if len(detections) > 0 and hasattr(detections[0], 'keypoints'):
            keypoints = detections[0].keypoints

            if keypoints is not None and keypoints.xy is not None:
                num_poses = len(keypoints.xy)

                for person_idx in range(num_poses):
                    kpts = keypoints.xy[person_idx]
                    conf = keypoints.conf[person_idx] if keypoints.conf is not None else None

                    # Draw skeleton
                    for start_idx, end_idx in SKELETON:
                        if start_idx < len(kpts) and end_idx < len(kpts):
                            x1, y1 = kpts[start_idx]
                            x2, y2 = kpts[end_idx]

                            if x1 > 0 and y1 > 0 and x2 > 0 and y2 > 0:
                                cv2.line(overlay, (int(x1), int(y1)), (int(x2), int(y2)),
                                        (255, 100, 0), 3)

                    # Draw keypoints
                    for idx, (x, y) in enumerate(kpts):
                        if x > 0 and y > 0:
                            radius = 6
                            if conf is not None and idx < len(conf):
                                radius = int(4 + conf[idx] * 6)
                            cv2.circle(overlay, (int(x), int(y)), radius, (0, 255, 0), -1)
                            cv2.circle(overlay, (int(x), int(y)), radius+2, (255, 255, 255), 1)

        # Blend with original frame
        cv2.addWeighted(overlay, self.overlay_opacity, frame, 1 - self.overlay_opacity, 0, frame)
        return frame

    def _draw_mediapipe_pose(self, frame, rgb_frame):
        """Draw MediaPipe pose detections"""
        overlay = frame.copy()

        results = self.detectors['mediapipe_pose'].process(rgb_frame)

        if results.pose_landmarks:
            mp_pose = self.detectors['mp_pose_module']
            mp_drawing = self.detectors['mp_drawing']
            mp_drawing_styles = self.detectors['mp_drawing_styles']

            mp_drawing.draw_landmarks(
                overlay,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
            )

        # Blend with original frame
        cv2.addWeighted(overlay, self.overlay_opacity, frame, 1 - self.overlay_opacity, 0, frame)
        return frame

    def _draw_mediapipe_face(self, frame, rgb_frame):
        """Draw MediaPipe face detections"""
        overlay = frame.copy()

        results = self.detectors['mediapipe_face'].process(rgb_frame)

        if results.detections:
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                h, w = frame.shape[:2]
                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                width = int(bbox.width * w)
                height = int(bbox.height * h)

                # Draw bounding box
                cv2.rectangle(overlay, (x, y), (x + width, y + height), (0, 255, 0), 3)

                # Draw confidence
                score = detection.score[0] if detection.score else 0
                cv2.putText(overlay, f"{score:.2f}", (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Blend with original frame
        cv2.addWeighted(overlay, self.overlay_opacity, frame, 1 - self.overlay_opacity, 0, frame)
        return frame

    def _draw_stage_boundary(self, frame):
        """Draw stage boundary overlay"""
        overlay = frame.copy()

        left = int(self.stage_boundary['left'] * self.frame_width)
        right = int(self.stage_boundary['right'] * self.frame_width)
        top = int(self.stage_boundary['top'] * self.frame_height)
        bottom = int(self.stage_boundary['bottom'] * self.frame_height)

        # Draw boundary rectangle
        cv2.rectangle(overlay, (left, top), (right, bottom), (255, 0, 0), 3)

        # Draw corner markers
        corner_size = 30
        # Top-left
        cv2.line(overlay, (left, top), (left + corner_size, top), (255, 0, 0), 5)
        cv2.line(overlay, (left, top), (left, top + corner_size), (255, 0, 0), 5)
        # Top-right
        cv2.line(overlay, (right, top), (right - corner_size, top), (255, 0, 0), 5)
        cv2.line(overlay, (right, top), (right, top + corner_size), (255, 0, 0), 5)
        # Bottom-left
        cv2.line(overlay, (left, bottom), (left + corner_size, bottom), (255, 0, 0), 5)
        cv2.line(overlay, (left, bottom), (left, bottom - corner_size), (255, 0, 0), 5)
        # Bottom-right
        cv2.line(overlay, (right, bottom), (right - corner_size, bottom), (255, 0, 0), 5)
        cv2.line(overlay, (right, bottom), (right, bottom - corner_size), (255, 0, 0), 5)

        # Label
        cv2.putText(overlay, "Stage Boundary", (left + 10, top - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

        # Blend with original frame
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
        return frame

    def _draw_info(self, frame):
        """Draw info overlay"""
        current_time = self.current_frame / self.fps
        progress = (self.current_frame / self.total_frames) * 100

        # Semi-transparent background for text
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (400, 150), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

        # Time info
        cv2.putText(frame, f"Time: {current_time:.1f}s / {self.duration:.1f}s",
                   (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Progress bar
        bar_width = 370
        bar_height = 20
        bar_x = 20
        bar_y = 60
        filled_width = int((self.current_frame / self.total_frames) * bar_width)

        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                     (100, 100, 100), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + filled_width, bar_y + bar_height),
                     (0, 255, 0), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                     (255, 255, 255), 2)

        # Playback info
        status = "PLAYING" if self.playing else "PAUSED"
        cv2.putText(frame, f"{status} | Speed: {self.playback_speed}x",
                   (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Active overlays
        overlays_text = "Overlays: "
        active_overlays = []
        if self.show_yolo_pose:
            active_overlays.append("YOLO")
        if self.show_mediapipe_pose:
            active_overlays.append("MP-Pose")
        if self.show_mediapipe_face:
            active_overlays.append("MP-Face")
        if self.show_stage_boundary:
            active_overlays.append("Stage")

        overlays_text += ", ".join(active_overlays) if active_overlays else "None"
        cv2.putText(frame, overlays_text, (20, 135),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        return frame

    def _draw_controls_help(self, frame):
        """Draw controls help overlay (bottom right)"""
        help_text = [
            "CONTROLS:",
            "SPACE - Play/Pause",
            "Y - Toggle YOLO Pose",
            "P - Toggle MediaPipe Pose",
            "F - Toggle Face Detection",
            "B - Toggle Stage Boundary",
            "I - Toggle Info",
            "+/- - Adjust Speed",
            "LEFT/RIGHT - Seek -/+ 5s",
            "Q - Quit"
        ]

        # Calculate text size for background
        line_height = 25
        padding = 10
        bg_height = len(help_text) * line_height + padding * 2
        bg_width = 300

        # Semi-transparent background
        overlay = frame.copy()
        bg_x = self.frame_width - bg_width - 20
        bg_y = self.frame_height - bg_height - 20
        cv2.rectangle(overlay, (bg_x, bg_y),
                     (bg_x + bg_width, bg_y + bg_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Draw text
        for i, text in enumerate(help_text):
            y = bg_y + padding + (i + 1) * line_height
            cv2.putText(frame, text, (bg_x + padding, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return frame

    def process_frame(self, frame):
        """Process frame with active detectors"""
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Run YOLO pose detection
        if self.show_yolo_pose and 'yolo_pose' in self.detectors:
            results = self.detectors['yolo_pose'](frame, conf=0.5, verbose=False)
            frame = self._draw_yolo_pose(frame, results)

        # Run MediaPipe pose detection
        if self.show_mediapipe_pose and 'mediapipe_pose' in self.detectors:
            frame = self._draw_mediapipe_pose(frame, rgb_frame)

        # Run MediaPipe face detection
        if self.show_mediapipe_face and 'mediapipe_face' in self.detectors:
            frame = self._draw_mediapipe_face(frame, rgb_frame)

        # Draw stage boundary
        if self.show_stage_boundary:
            frame = self._draw_stage_boundary(frame)

        # Draw info overlay
        if self.show_info:
            frame = self._draw_info(frame)

        # Always draw controls
        frame = self._draw_controls_help(frame)

        return frame

    def seek(self, frame_offset):
        """Seek to a specific frame offset"""
        new_frame = max(0, min(self.total_frames - 1, self.current_frame + frame_offset))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)
        self.current_frame = new_frame

    def export_with_overlays(self, output_path: str = None, start_time: float = None, end_time: float = None):
        """
        Export the entire video (or a segment) with overlays rendered.

        Args:
            output_path: Path to save the output video (default: video_name_overlays.mp4)
            start_time: Start time in seconds (default: start of video)
            end_time: End time in seconds (default: end of video)
        """
        # Determine output path
        if output_path is None:
            video_dir = Path(self.video_path).parent
            video_name = Path(self.video_path).stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = video_dir / f"{video_name}_overlays_{timestamp}.mp4"
        else:
            output_path = Path(output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"\nExporting video with overlays...")
        print(f"Output: {output_path}")

        # Determine frame range
        start_frame = 0 if start_time is None else int(start_time * self.fps)
        end_frame = self.total_frames if end_time is None else int(end_time * self.fps)
        start_frame = max(0, start_frame)
        end_frame = min(self.total_frames, end_frame)
        total_export_frames = end_frame - start_frame

        print(f"Frames: {start_frame} to {end_frame} ({total_export_frames} frames)")
        print(f"Duration: {total_export_frames / self.fps:.1f}s")

        # Show which overlays are enabled
        print(f"\nEnabled overlays:")
        if self.show_yolo_pose:
            print("  - YOLO Pose")
        if self.show_mediapipe_pose:
            print("  - MediaPipe Pose")
        if self.show_mediapipe_face:
            print("  - MediaPipe Face Detection")
        if self.show_stage_boundary:
            print("  - Stage Boundary")
        if self.show_info:
            print("  - Info Overlay")

        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, self.fps,
                             (self.frame_width, self.frame_height))

        if not out.isOpened():
            raise RuntimeError(f"Could not create video writer for {output_path}")

        # Seek to start frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        frame_count = 0
        last_progress = -1

        print("\nProcessing frames...")

        try:
            while frame_count < total_export_frames:
                ret, frame = self.cap.read()
                if not ret:
                    break

                # Temporarily disable controls overlay for export
                original_frame = frame.copy()

                # Process frame with overlays (without controls help)
                frame_with_overlays = self.process_frame_for_export(original_frame)

                # Write frame to output video
                out.write(frame_with_overlays)

                frame_count += 1

                # Show progress
                progress = int((frame_count / total_export_frames) * 100)
                if progress != last_progress and progress % 5 == 0:
                    elapsed_time = frame_count / self.fps
                    total_time = total_export_frames / self.fps
                    print(f"  Progress: {progress}% ({frame_count}/{total_export_frames} frames, "
                          f"{elapsed_time:.1f}s / {total_time:.1f}s)")
                    last_progress = progress

        finally:
            out.release()

        print(f"\nExport complete!")
        print(f"Saved to: {output_path}")

        # Re-encode with H.264 for better compatibility using FFmpeg
        print("\nRe-encoding with H.264 for better compatibility...")
        final_output = output_path.parent / f"{output_path.stem}_h264.mp4"

        cmd = [
            'ffmpeg', '-y',
            '-i', str(output_path),
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            str(final_output)
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            # Remove temporary file
            output_path.unlink()
            print(f"Final output: {final_output}")
            return str(final_output)
        except subprocess.CalledProcessError as e:
            print(f"Warning: FFmpeg re-encoding failed. Using original output.")
            print(f"Error: {e.stderr.decode() if e.stderr else 'Unknown error'}")
            return str(output_path)
        except FileNotFoundError:
            print("Warning: FFmpeg not found. Using original output.")
            print("Install FFmpeg for better video compatibility.")
            return str(output_path)

    def process_frame_for_export(self, frame):
        """Process frame with overlays, but without the controls help overlay"""
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Run YOLO pose detection
        if self.show_yolo_pose and 'yolo_pose' in self.detectors:
            results = self.detectors['yolo_pose'](frame, conf=0.5, verbose=False)
            frame = self._draw_yolo_pose(frame, results)

        # Run MediaPipe pose detection
        if self.show_mediapipe_pose and 'mediapipe_pose' in self.detectors:
            frame = self._draw_mediapipe_pose(frame, rgb_frame)

        # Run MediaPipe face detection
        if self.show_mediapipe_face and 'mediapipe_face' in self.detectors:
            frame = self._draw_mediapipe_face(frame, rgb_frame)

        # Draw stage boundary
        if self.show_stage_boundary:
            frame = self._draw_stage_boundary(frame)

        # Draw info overlay
        if self.show_info:
            frame = self._draw_info(frame)

        # Note: NOT drawing controls help for export

        return frame

    def play(self):
        """Main playback loop"""
        cv2.namedWindow('Video Overlay Player', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Video Overlay Player', 1280, 720)

        frame_delay = int(1000 / (self.fps * self.playback_speed))

        while True:
            if self.playing:
                ret, frame = self.cap.read()
                if not ret:
                    # Loop back to start
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.current_frame = 0
                    continue

                self.current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))

                # Process frame with overlays
                frame = self.process_frame(frame)

                cv2.imshow('Video Overlay Player', frame)
            else:
                # Paused - just redraw current frame
                current_pos = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                ret, frame = self.cap.read()
                if ret:
                    frame = self.process_frame(frame)
                    cv2.imshow('Video Overlay Player', frame)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)

            # Handle keyboard input
            key = cv2.waitKey(frame_delay) & 0xFF

            if key == ord('q'):
                break
            elif key == ord(' '):
                self.playing = not self.playing
            elif key == ord('y'):
                self.show_yolo_pose = not self.show_yolo_pose
            elif key == ord('p'):
                self.show_mediapipe_pose = not self.show_mediapipe_pose
            elif key == ord('f'):
                self.show_mediapipe_face = not self.show_mediapipe_face
            elif key == ord('b'):
                self.show_stage_boundary = not self.show_stage_boundary
            elif key == ord('i'):
                self.show_info = not self.show_info
            elif key == ord('+') or key == ord('='):
                self.playback_speed = min(4.0, self.playback_speed + 0.25)
                frame_delay = int(1000 / (self.fps * self.playback_speed))
            elif key == ord('-') or key == ord('_'):
                self.playback_speed = max(0.25, self.playback_speed - 0.25)
                frame_delay = int(1000 / (self.fps * self.playback_speed))
            elif key == 81 or key == 2:  # Left arrow
                self.seek(-int(5 * self.fps))  # -5 seconds
            elif key == 83 or key == 3:  # Right arrow
                self.seek(int(5 * self.fps))  # +5 seconds

        self.cap.release()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(
        description="Interactive Video Overlay Player with Detection Visualization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Detection Modes:
  yolo_pose         - YOLO11 pose detection (default)
  mediapipe_pose    - MediaPipe pose tracking
  mediapipe_face    - MediaPipe face detection

Interactive Player Examples:
  # Play with YOLO pose detection
  python3 video_overlay_player.py video.mp4

  # Play with all detections
  python3 video_overlay_player.py video.mp4 --detections yolo_pose mediapipe_pose mediapipe_face

  # Use specific YOLO model
  python3 video_overlay_player.py video.mp4 --yolo-model yolo11m-pose.pt

Export Mode Examples:
  # Export entire video with YOLO pose overlays
  python3 video_overlay_player.py video.mp4 --export

  # Export with custom output path
  python3 video_overlay_player.py video.mp4 --export -o my_output.mp4

  # Export a specific time range (from 30s to 90s)
  python3 video_overlay_player.py video.mp4 --export --start-time 30 --end-time 90

  # Export with all detections
  python3 video_overlay_player.py video.mp4 --export --detections yolo_pose mediapipe_pose mediapipe_face

  # Export with only stage boundary and info (no pose detection)
  python3 video_overlay_player.py video.mp4 --export --no-yolo --no-mediapipe-pose --no-mediapipe-face

Interactive Player Controls:
  SPACE      - Play/Pause
  Y          - Toggle YOLO Pose overlay
  P          - Toggle MediaPipe Pose overlay
  F          - Toggle Face Detection overlay
  B          - Toggle Stage Boundary
  I          - Toggle Info overlay
  +/-        - Adjust playback speed
  LEFT/RIGHT - Seek backward/forward 5 seconds
  Q          - Quit
        """
    )

    parser.add_argument('video', help='Input video file')
    parser.add_argument('--detections', nargs='+',
                       default=['yolo_pose'],
                       choices=['yolo_pose', 'mediapipe_pose', 'mediapipe_face'],
                       help='Detection modes to enable (default: yolo_pose)')
    parser.add_argument('--yolo-model', default='yolo11n-pose.pt',
                       help='YOLO model to use (default: yolo11n-pose.pt)')

    # Export mode arguments
    parser.add_argument('--export', action='store_true',
                       help='Export mode: render overlays to output video instead of playing')
    parser.add_argument('--output', '-o',
                       help='Output video path for export mode')
    parser.add_argument('--start-time', type=float,
                       help='Start time in seconds for export (default: start of video)')
    parser.add_argument('--end-time', type=float,
                       help='End time in seconds for export (default: end of video)')
    parser.add_argument('--no-yolo', action='store_true',
                       help='Disable YOLO pose overlay in export')
    parser.add_argument('--no-mediapipe-pose', action='store_true',
                       help='Disable MediaPipe pose overlay in export')
    parser.add_argument('--no-mediapipe-face', action='store_true',
                       help='Disable MediaPipe face overlay in export')
    parser.add_argument('--no-stage-boundary', action='store_true',
                       help='Disable stage boundary overlay in export')
    parser.add_argument('--no-info', action='store_true',
                       help='Disable info overlay in export')

    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"Error: Video not found: {args.video}")
        sys.exit(1)

    try:
        player = VideoOverlayPlayer(args.video, detection_modes=args.detections)

        # Apply overlay disable flags if in export mode
        if args.export:
            if args.no_yolo:
                player.show_yolo_pose = False
            if args.no_mediapipe_pose:
                player.show_mediapipe_pose = False
            if args.no_mediapipe_face:
                player.show_mediapipe_face = False
            if args.no_stage_boundary:
                player.show_stage_boundary = False
            if args.no_info:
                player.show_info = False

            # Run export
            player.export_with_overlays(
                output_path=args.output,
                start_time=args.start_time,
                end_time=args.end_time
            )
        else:
            # Run interactive player
            player.play()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
