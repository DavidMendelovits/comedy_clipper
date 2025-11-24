#!/usr/bin/env python3
"""
MoveNet Pose Detection Script
Detects poses using TensorFlow MoveNet and overlays skeleton on video.
Supports both Lightning (fast) and Thunder (accurate) models.
"""

import cv2
import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import argparse
import time
from pathlib import Path


class MoveNetPoseDetector:
    # MoveNet keypoint connections for drawing skeleton
    EDGES = [
        (0, 1), (0, 2), (1, 3), (2, 4),  # Head
        (0, 5), (0, 6),  # Shoulders
        (5, 7), (7, 9),  # Left arm
        (6, 8), (8, 10),  # Right arm
        (5, 6),  # Shoulder connection
        (5, 11), (6, 12),  # Torso
        (11, 12),  # Hip connection
        (11, 13), (13, 15),  # Left leg
        (12, 14), (14, 16)  # Right leg
    ]

    KEYPOINT_NAMES = [
        'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
        'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
        'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
        'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
    ]

    def __init__(self, model_type='thunder', confidence_threshold=0.3):
        """
        Initialize MoveNet detector.

        Args:
            model_type: 'lightning' (faster) or 'thunder' (more accurate)
            confidence_threshold: Minimum confidence for keypoint detection
        """
        self.confidence_threshold = confidence_threshold
        self.model_type = model_type

        # Load model from TensorFlow Hub
        print(f"Loading MoveNet {model_type} model...")
        if model_type == 'lightning':
            model_url = "https://tfhub.dev/google/movenet/singlepose/lightning/4"
            self.input_size = 192
        else:  # thunder
            model_url = "https://tfhub.dev/google/movenet/singlepose/thunder/4"
            self.input_size = 256

        self.model = hub.load(model_url)
        self.movenet = self.model.signatures['serving_default']

        self.frame_times = []
        self.detection_count = 0

        print(f"✓ Model loaded successfully (input size: {self.input_size}x{self.input_size})")

    def preprocess_frame(self, frame):
        """Preprocess frame for MoveNet."""
        # Resize to model input size
        img = cv2.resize(frame, (self.input_size, self.input_size))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Convert to tensor
        img = tf.cast(img, dtype=tf.int32)
        img = tf.expand_dims(img, axis=0)

        return img

    def draw_pose(self, frame, keypoints, confidence_scores):
        """Draw pose skeleton on frame."""
        height, width = frame.shape[:2]

        # Check if pose is detected (at least some keypoints with good confidence)
        valid_keypoints = np.sum(confidence_scores > self.confidence_threshold)

        if valid_keypoints < 5:  # Require at least 5 keypoints
            return False

        # Draw connections
        for edge in self.EDGES:
            y1, x1, c1 = keypoints[edge[0]]
            y2, x2, c2 = keypoints[edge[1]]

            if c1 > self.confidence_threshold and c2 > self.confidence_threshold:
                # Convert normalized coordinates to pixel coordinates
                x1_px = int(x1 * width)
                y1_px = int(y1 * height)
                x2_px = int(x2 * width)
                y2_px = int(y2 * height)

                # Draw line
                cv2.line(frame, (x1_px, y1_px), (x2_px, y2_px), (0, 255, 0), 2)

        # Draw keypoints
        for i, (y, x, confidence) in enumerate(keypoints):
            if confidence > self.confidence_threshold:
                x_px = int(x * width)
                y_px = int(y * height)

                # Different colors for different body parts
                if i < 5:  # Head
                    color = (255, 0, 255)
                elif i < 11:  # Arms
                    color = (255, 255, 0)
                else:  # Legs
                    color = (0, 255, 255)

                cv2.circle(frame, (x_px, y_px), 4, color, -1)
                cv2.circle(frame, (x_px, y_px), 6, (255, 255, 255), 1)

        return True

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

            # Preprocess frame
            input_frame = self.preprocess_frame(frame)

            # Run inference
            outputs = self.movenet(input_frame)
            keypoints_with_scores = outputs['output_0'].numpy()[0, 0, :, :]

            # Extract keypoints and scores
            keypoints = keypoints_with_scores[:, :3]  # y, x, confidence
            confidence_scores = keypoints_with_scores[:, 2]

            # Draw pose
            pose_detected = self.draw_pose(frame, keypoints, confidence_scores)

            if pose_detected:
                self.detection_count += 1
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
            cv2.putText(frame, f"MoveNet {self.model_type.capitalize()}", (10, height - 10),
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
        print(f"MOVENET {self.model_type.upper()} STATISTICS")
        print("="*50)
        print(f"Total frames processed: {total_frames}")
        print(f"Frames with pose detected: {self.detection_count}")
        print(f"Detection rate: {detection_rate:.1f}%")
        print(f"Average processing time per frame: {avg_time*1000:.2f}ms")
        print(f"Average FPS: {avg_fps:.1f}")
        print("="*50)


def main():
    parser = argparse.ArgumentParser(description='MoveNet Pose Detection with Video Overlay')
    parser.add_argument('input', help='Input video file path')
    parser.add_argument('-o', '--output', help='Output video file path (default: input_movenet.mp4)')
    parser.add_argument('-m', '--model', default='thunder', choices=['lightning', 'thunder'],
                       help='Model type: lightning (fast) or thunder (accurate) (default: thunder)')
    parser.add_argument('-c', '--confidence', type=float, default=0.3,
                       help='Minimum confidence threshold (default: 0.3)')

    args = parser.parse_args()

    # Setup output path
    if args.output:
        output_path = args.output
    else:
        input_path = Path(args.input)
        output_path = str(input_path.parent / f"{input_path.stem}_movenet_{args.model}.mp4")

    print(f"Output will be saved to: {output_path}")

    # Create detector and process video
    detector = MoveNetPoseDetector(
        model_type=args.model,
        confidence_threshold=args.confidence
    )

    try:
        detector.process_video(args.input, output_path)
        print(f"\n✓ Successfully created overlay video: {output_path}")
    except Exception as e:
        print(f"\n✗ Error processing video: {e}")
        raise


if __name__ == "__main__":
    main()
