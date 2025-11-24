#!/usr/bin/env python3
"""
MMPose Detection Script
Detects poses using OpenMMLab's MMPose framework.
Supports various models including HRNet, RTMPose, etc.
"""

import cv2
import numpy as np
import argparse
import time
from pathlib import Path

try:
    from mmpose.apis import init_model, inference_topdown
    from mmpose.structures import PoseDataSample, merge_data_samples
    MMPOSE_AVAILABLE = True
except ImportError:
    MMPOSE_AVAILABLE = False


class MMPoseDetector:
    # Predefined model configurations
    MODELS = {
        'rtmpose-m': {
            'config': 'rtmpose/body_2d_keypoint/rtmpose-m_8xb256-420e_coco-256x192.py',
            'checkpoint': 'https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/rtmpose-m_simcc-body7_pt-body7_420e-256x192-e48f03d0_20230504.pth'
        },
        'rtmpose-l': {
            'config': 'rtmpose/body_2d_keypoint/rtmpose-l_8xb256-420e_coco-256x192.py',
            'checkpoint': 'https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/rtmpose-l_simcc-body7_pt-body7_420e-256x192-4dba18fc_20230504.pth'
        },
        'hrnet-w32': {
            'config': 'body_2d_keypoint/topdown_heatmap/coco/td-hm_hrnet-w32_8xb64-210e_coco-256x192.py',
            'checkpoint': 'https://download.openmmlab.com/mmpose/top_down/hrnet/hrnet_w32_coco_256x192-c78dce93_20200708.pth'
        },
        'hrnet-w48': {
            'config': 'body_2d_keypoint/topdown_heatmap/coco/td-hm_hrnet-w48_8xb32-210e_coco-256x192.py',
            'checkpoint': 'https://download.openmmlab.com/mmpose/top_down/hrnet/hrnet_w48_coco_256x192-b9e0b3ab_20200708.pth'
        },
    }

    # COCO keypoint connections
    SKELETON = [
        [15, 13], [13, 11], [16, 14], [14, 12], [11, 12],
        [5, 11], [6, 12], [5, 6], [5, 7], [6, 8], [7, 9],
        [8, 10], [1, 2], [0, 1], [0, 2], [1, 3], [2, 4],
        [3, 5], [4, 6]
    ]

    def __init__(self, model_name='rtmpose-m', device='cpu', confidence_threshold=0.3):
        """
        Initialize MMPose detector.

        Args:
            model_name: Name of the model to use (see MODELS dict)
            device: 'cpu' or 'cuda:0'
            confidence_threshold: Minimum confidence for keypoint detection
        """
        if not MMPOSE_AVAILABLE:
            raise ImportError(
                "MMPose is not installed. Install with:\n"
                "pip install mmpose mmcv mmengine mmdet"
            )

        self.confidence_threshold = confidence_threshold
        self.model_name = model_name
        self.device = device

        if model_name not in self.MODELS:
            raise ValueError(
                f"Unknown model: {model_name}. Available models: {list(self.MODELS.keys())}"
            )

        model_info = self.MODELS[model_name]

        print(f"Loading MMPose model: {model_name}...")
        print(f"Config: {model_info['config']}")
        print(f"Checkpoint: {model_info['checkpoint']}")

        # Initialize model
        self.model = init_model(
            model_info['config'],
            model_info['checkpoint'],
            device=device
        )

        self.frame_times = []
        self.detection_count = 0

        print(f"✓ Model loaded successfully on {device}")

    def draw_pose(self, frame, keypoints, scores):
        """Draw pose skeleton on frame."""
        height, width = frame.shape[:2]

        # Check if pose is detected
        valid_keypoints = np.sum(scores > self.confidence_threshold)

        if valid_keypoints < 5:  # Require at least 5 keypoints
            return False

        # Draw skeleton connections
        for connection in self.SKELETON:
            pt1_idx, pt2_idx = connection
            if pt1_idx >= len(keypoints) or pt2_idx >= len(keypoints):
                continue

            if scores[pt1_idx] > self.confidence_threshold and scores[pt2_idx] > self.confidence_threshold:
                pt1 = tuple(keypoints[pt1_idx].astype(int))
                pt2 = tuple(keypoints[pt2_idx].astype(int))
                cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

        # Draw keypoints
        for i, (keypoint, score) in enumerate(zip(keypoints, scores)):
            if score > self.confidence_threshold:
                x, y = keypoint.astype(int)

                # Color coding
                if i < 5:  # Head
                    color = (255, 0, 255)
                elif i < 11:  # Arms
                    color = (255, 255, 0)
                else:  # Legs
                    color = (0, 255, 255)

                cv2.circle(frame, (x, y), 4, color, -1)
                cv2.circle(frame, (x, y), 6, (255, 255, 255), 1)

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

            # Create bounding box for full frame (topdown requires bbox)
            bbox = np.array([[0, 0, width, height]])

            # Run inference
            results = inference_topdown(self.model, frame, bboxes=bbox)

            # Extract keypoints and scores
            pose_detected = False
            if results and len(results) > 0:
                pred_instances = results[0].pred_instances
                if len(pred_instances.keypoints) > 0:
                    keypoints = pred_instances.keypoints[0]
                    scores = pred_instances.keypoint_scores[0]
                    pose_detected = self.draw_pose(frame, keypoints, scores)

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
            cv2.putText(frame, f"MMPose {self.model_name}", (10, height - 10),
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
        print(f"MMPOSE {self.model_name.upper()} STATISTICS")
        print("="*50)
        print(f"Total frames processed: {total_frames}")
        print(f"Frames with pose detected: {self.detection_count}")
        print(f"Detection rate: {detection_rate:.1f}%")
        print(f"Average processing time per frame: {avg_time*1000:.2f}ms")
        print(f"Average FPS: {avg_fps:.1f}")
        print("="*50)


def main():
    parser = argparse.ArgumentParser(description='MMPose Detection with Video Overlay')
    parser.add_argument('input', help='Input video file path')
    parser.add_argument('-o', '--output', help='Output video file path (default: input_mmpose.mp4)')
    parser.add_argument('-m', '--model', default='rtmpose-m',
                       choices=list(MMPoseDetector.MODELS.keys()),
                       help='Model to use (default: rtmpose-m)')
    parser.add_argument('-d', '--device', default='cpu',
                       help='Device to use: cpu or cuda:0 (default: cpu)')
    parser.add_argument('-c', '--confidence', type=float, default=0.3,
                       help='Minimum confidence threshold (default: 0.3)')

    args = parser.parse_args()

    # Setup output path
    if args.output:
        output_path = args.output
    else:
        input_path = Path(args.input)
        output_path = str(input_path.parent / f"{input_path.stem}_mmpose_{args.model}.mp4")

    print(f"Output will be saved to: {output_path}")

    # Create detector and process video
    try:
        detector = MMPoseDetector(
            model_name=args.model,
            device=args.device,
            confidence_threshold=args.confidence
        )

        detector.process_video(args.input, output_path)
        print(f"\n✓ Successfully created overlay video: {output_path}")
    except Exception as e:
        print(f"\n✗ Error processing video: {e}")
        raise


if __name__ == "__main__":
    main()
