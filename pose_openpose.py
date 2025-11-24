#!/usr/bin/env python3
"""
OpenPose Detection Script
Detects poses using OpenCV's DNN module with OpenPose models.
Download models from: https://github.com/CMU-Perceptual-Computing-Lab/openpose/tree/master/models
"""

import cv2
import numpy as np
import argparse
import time
from pathlib import Path


class OpenPoseDetector:
    # COCO format: 18 keypoints
    POSE_PAIRS_COCO = [
        [1, 2], [1, 5], [2, 3], [3, 4], [5, 6], [6, 7],
        [1, 8], [8, 9], [9, 10], [1, 11], [11, 12], [12, 13],
        [1, 0], [0, 14], [14, 16], [0, 15], [15, 17]
    ]

    KEYPOINT_NAMES_COCO = [
        "Nose", "Neck", "RShoulder", "RElbow", "RWrist",
        "LShoulder", "LElbow", "LWrist", "RHip", "RKnee",
        "RAnkle", "LHip", "LKnee", "LAnkle", "REye",
        "LEye", "REar", "LEar"
    ]

    # MPI format: 15 keypoints
    POSE_PAIRS_MPI = [
        [0, 1], [1, 2], [2, 3], [3, 4], [1, 5], [5, 6],
        [6, 7], [1, 14], [14, 8], [8, 9], [9, 10],
        [14, 11], [11, 12], [12, 13]
    ]

    KEYPOINT_NAMES_MPI = [
        "Head", "Neck", "RShoulder", "RElbow", "RWrist",
        "LShoulder", "LElbow", "LWrist", "RHip", "RKnee",
        "RAnkle", "LHip", "LKnee", "LAnkle", "Chest"
    ]

    def __init__(self, model_dir, model_type='COCO', confidence_threshold=0.1):
        """
        Initialize OpenPose detector.

        Args:
            model_dir: Directory containing OpenPose models
            model_type: 'COCO' (18 points) or 'MPI' (15 points)
            confidence_threshold: Minimum confidence for keypoint detection
        """
        self.confidence_threshold = confidence_threshold
        self.model_type = model_type

        model_dir = Path(model_dir)

        # Setup model files based on type
        if model_type == 'COCO':
            proto_file = model_dir / "pose_deploy_linevec.prototxt"
            weights_file = model_dir / "pose_iter_440000.caffemodel"
            self.num_points = 18
            self.pose_pairs = self.POSE_PAIRS_COCO
            self.keypoint_names = self.KEYPOINT_NAMES_COCO
        else:  # MPI
            proto_file = model_dir / "pose_deploy_linevec_faster_4_stages.prototxt"
            weights_file = model_dir / "pose_iter_160000.caffemodel"
            self.num_points = 15
            self.pose_pairs = self.POSE_PAIRS_MPI
            self.keypoint_names = self.KEYPOINT_NAMES_MPI

        # Check if model files exist
        if not proto_file.exists():
            raise FileNotFoundError(
                f"Prototxt file not found: {proto_file}\n"
                f"Download from: https://github.com/CMU-Perceptual-Computing-Lab/openpose/tree/master/models"
            )
        if not weights_file.exists():
            raise FileNotFoundError(
                f"Weights file not found: {weights_file}\n"
                f"Download from: https://github.com/CMU-Perceptual-Computing-Lab/openpose/tree/master/models"
            )

        # Load network
        print(f"Loading OpenPose {model_type} model...")
        self.net = cv2.dnn.readNetFromCaffe(str(proto_file), str(weights_file))

        # Try to use GPU if available
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            print("Using CUDA GPU acceleration")
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
        else:
            print("Using CPU")
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        self.frame_times = []
        self.detection_count = 0

        print(f"✓ Model loaded successfully ({self.num_points} keypoints)")

    def detect_pose(self, frame):
        """Detect pose keypoints in frame."""
        frame_height, frame_width = frame.shape[:2]

        # Prepare input blob
        input_blob = cv2.dnn.blobFromImage(
            frame, 1.0 / 255, (368, 368),
            (0, 0, 0), swapRB=False, crop=False
        )

        self.net.setInput(input_blob)
        output = self.net.forward()

        # Extract keypoints
        points = []
        for i in range(self.num_points):
            prob_map = output[0, i, :, :]
            min_val, prob, min_loc, point = cv2.minMaxLoc(prob_map)

            # Scale point to frame size
            x = int((frame_width * point[0]) / output.shape[3])
            y = int((frame_height * point[1]) / output.shape[2])

            if prob > self.confidence_threshold:
                points.append((x, y, prob))
            else:
                points.append(None)

        return points

    def draw_pose(self, frame, points):
        """Draw pose skeleton on frame."""
        # Check if enough keypoints detected
        valid_points = sum(1 for p in points if p is not None)

        if valid_points < 5:  # Require at least 5 keypoints
            return False

        # Draw skeleton connections
        for pair in self.pose_pairs:
            part_a = pair[0]
            part_b = pair[1]

            if points[part_a] and points[part_b]:
                cv2.line(frame,
                        (points[part_a][0], points[part_a][1]),
                        (points[part_b][0], points[part_b][1]),
                        (0, 255, 0), 3, lineType=cv2.LINE_AA)

        # Draw keypoints
        for i, point in enumerate(points):
            if point:
                # Color coding
                if i < 5:  # Head area
                    color = (255, 0, 255)
                elif i < 8:  # Arms
                    color = (255, 255, 0)
                else:  # Legs
                    color = (0, 255, 255)

                cv2.circle(frame, (point[0], point[1]), 6, color, -1)
                cv2.circle(frame, (point[0], point[1]), 8, (255, 255, 255), 2)

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

            # Detect pose
            points = self.detect_pose(frame)

            # Draw pose
            pose_detected = self.draw_pose(frame, points)

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
            cv2.putText(frame, f"OpenPose {self.model_type}", (10, height - 10),
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
        print(f"OPENPOSE {self.model_type} STATISTICS")
        print("="*50)
        print(f"Total frames processed: {total_frames}")
        print(f"Frames with pose detected: {self.detection_count}")
        print(f"Detection rate: {detection_rate:.1f}%")
        print(f"Average processing time per frame: {avg_time*1000:.2f}ms")
        print(f"Average FPS: {avg_fps:.1f}")
        print("="*50)


def main():
    parser = argparse.ArgumentParser(description='OpenPose Detection with Video Overlay')
    parser.add_argument('input', help='Input video file path')
    parser.add_argument('-m', '--model-dir', required=True,
                       help='Directory containing OpenPose model files')
    parser.add_argument('-o', '--output', help='Output video file path (default: input_openpose.mp4)')
    parser.add_argument('-t', '--type', default='COCO', choices=['COCO', 'MPI'],
                       help='Model type: COCO (18 points) or MPI (15 points) (default: COCO)')
    parser.add_argument('-c', '--confidence', type=float, default=0.1,
                       help='Minimum confidence threshold (default: 0.1)')

    args = parser.parse_args()

    # Setup output path
    if args.output:
        output_path = args.output
    else:
        input_path = Path(args.input)
        output_path = str(input_path.parent / f"{input_path.stem}_openpose_{args.type.lower()}.mp4")

    print(f"Output will be saved to: {output_path}")

    # Create detector and process video
    try:
        detector = OpenPoseDetector(
            model_dir=args.model_dir,
            model_type=args.type,
            confidence_threshold=args.confidence
        )

        detector.process_video(args.input, output_path)
        print(f"\n✓ Successfully created overlay video: {output_path}")
    except Exception as e:
        print(f"\n✗ Error processing video: {e}")
        raise


if __name__ == "__main__":
    main()
