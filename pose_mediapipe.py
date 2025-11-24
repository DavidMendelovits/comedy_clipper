#!/usr/bin/env python3
"""
MediaPipe Pose Detection Script
Detects poses and overlays skeleton on video for visual testing.
"""

import cv2
import mediapipe as mp
import numpy as np
import argparse
import time
from pathlib import Path


class MediaPipePoseDetector:
    def __init__(self, model_complexity=2, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        """
        Initialize MediaPipe Pose detector.

        Args:
            model_complexity: 0, 1, or 2. Higher is more accurate but slower.
            min_detection_confidence: Minimum confidence for pose detection.
            min_tracking_confidence: Minimum confidence for pose tracking.
        """
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        self.pose = self.mp_pose.Pose(
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            enable_segmentation=False,
            smooth_landmarks=True
        )

        self.frame_times = []
        self.detection_count = 0

    def process_video(self, input_path, output_path):
        """Process video and create overlay visualization."""
        cap = cv2.VideoCapture(input_path)

        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Setup video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        print(f"Processing video: {input_path}")
        print(f"Resolution: {width}x{height}, FPS: {fps}, Frames: {total_frames}")

        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            start_time = time.time()

            # Convert to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Process pose detection
            results = self.pose.process(rgb_frame)

            # Draw pose landmarks
            if results.pose_landmarks:
                self.detection_count += 1

                # Draw landmarks and connections
                self.mp_drawing.draw_landmarks(
                    frame,
                    results.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
                )

                # Add detection indicator
                cv2.putText(frame, "POSE DETECTED", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "NO POSE", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            # Calculate and display FPS
            elapsed = time.time() - start_time
            self.frame_times.append(elapsed)
            fps_current = 1 / elapsed if elapsed > 0 else 0

            # Add info overlay
            cv2.putText(frame, f"Frame: {frame_count}/{total_frames}", (10, height - 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, f"FPS: {fps_current:.1f}", (10, height - 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, f"MediaPipe Pose", (10, height - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

            # Write frame
            out.write(frame)

            # Progress indicator
            if frame_count % 30 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"Progress: {progress:.1f}% ({frame_count}/{total_frames})")

        # Cleanup
        cap.release()
        out.release()

        # Print statistics
        self.print_statistics(total_frames)

    def print_statistics(self, total_frames):
        """Print processing statistics."""
        avg_time = np.mean(self.frame_times) if self.frame_times else 0
        avg_fps = 1 / avg_time if avg_time > 0 else 0
        detection_rate = (self.detection_count / total_frames) * 100 if total_frames > 0 else 0

        print("\n" + "="*50)
        print("MEDIAPIPE POSE STATISTICS")
        print("="*50)
        print(f"Total frames processed: {total_frames}")
        print(f"Frames with pose detected: {self.detection_count}")
        print(f"Detection rate: {detection_rate:.1f}%")
        print(f"Average processing time per frame: {avg_time*1000:.2f}ms")
        print(f"Average FPS: {avg_fps:.1f}")
        print("="*50)

    def cleanup(self):
        """Cleanup resources."""
        self.pose.close()


def main():
    parser = argparse.ArgumentParser(description='MediaPipe Pose Detection with Video Overlay')
    parser.add_argument('input', help='Input video file path')
    parser.add_argument('-o', '--output', help='Output video file path (default: input_mediapipe.mp4)')
    parser.add_argument('-c', '--complexity', type=int, default=2, choices=[0, 1, 2],
                       help='Model complexity: 0=fastest, 2=most accurate (default: 2)')
    parser.add_argument('--min-detection', type=float, default=0.5,
                       help='Minimum detection confidence (default: 0.5)')
    parser.add_argument('--min-tracking', type=float, default=0.5,
                       help='Minimum tracking confidence (default: 0.5)')

    args = parser.parse_args()

    # Setup output path
    if args.output:
        output_path = args.output
    else:
        input_path = Path(args.input)
        output_path = str(input_path.parent / f"{input_path.stem}_mediapipe.mp4")

    print(f"Output will be saved to: {output_path}")

    # Create detector and process video
    detector = MediaPipePoseDetector(
        model_complexity=args.complexity,
        min_detection_confidence=args.min_detection,
        min_tracking_confidence=args.min_tracking
    )

    try:
        detector.process_video(args.input, output_path)
        print(f"\n✓ Successfully created overlay video: {output_path}")
    except Exception as e:
        print(f"\n✗ Error processing video: {e}")
        raise
    finally:
        detector.cleanup()


if __name__ == "__main__":
    main()
