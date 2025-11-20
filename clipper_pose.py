#!/usr/bin/env python3
"""
Comedy Clipper - Pose/Person Detection
Detects when a person enters/exits the stage using computer vision
Perfect for static camera standup shows
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Optional
import subprocess
import cv2
import numpy as np
from datetime import datetime
from ultralytics import YOLO


class PoseDetectionClipper:
    """Clipper using person detection to identify entry/exit from stage"""

    def __init__(self, model_size: str = "n", debug: bool = False):
        """
        Initialize clipper.

        Args:
            model_size: YOLO model size (n=nano, s=small, m=medium, l=large)
            debug: Whether to export debug frames with pose overlays
        """
        print(f"Loading YOLO{model_size} model for person detection...")
        self.model = YOLO(f'yolov8{model_size}.pt')
        self.debug = debug
        print("Model loaded!")

    def interpolate_positions(self, person_positions: List[Tuple[int, Optional[float], bool]]) -> List[Tuple[int, Optional[float], bool]]:
        """
        Interpolate missing person positions.

        Args:
            person_positions: List of (frame_num, center_x, is_at_edge) tuples

        Returns:
            List with interpolated positions for missing frames
        """
        if not person_positions:
            return person_positions

        interpolated = []

        for i, (frame_num, center_x, is_at_edge) in enumerate(person_positions):
            if center_x is None:
                # Try to interpolate from surrounding frames
                prev_x = None
                next_x = None

                # Look backwards for last known position
                for j in range(i - 1, -1, -1):
                    if person_positions[j][1] is not None:
                        prev_x = person_positions[j][1]
                        break

                # Look forwards for next known position
                for j in range(i + 1, len(person_positions)):
                    if person_positions[j][1] is not None:
                        next_x = person_positions[j][1]
                        break

                # Interpolate if we have both prev and next
                if prev_x is not None and next_x is not None:
                    # Simple linear interpolation
                    center_x = (prev_x + next_x) / 2
                elif prev_x is not None:
                    # Use previous position
                    center_x = prev_x
                elif next_x is not None:
                    # Use next position
                    center_x = next_x
                # else: leave as None

            interpolated.append((frame_num, center_x, is_at_edge))

        return interpolated

    def export_debug_frame(self, frame, frame_num: int, center_x: Optional[float],
                          is_at_edge: bool, left_edge: float, right_edge: float,
                          output_path: str, label: str):
        """
        Export a frame with pose detection overlay.

        Args:
            frame: Video frame
            frame_num: Frame number
            center_x: X-coordinate of person center (None if not detected)
            is_at_edge: Whether person is at edge
            left_edge: Left edge threshold
            right_edge: Right edge threshold
            output_path: Path to save the frame
            label: Label for the frame (e.g., "First Frame", "Last Frame")
        """
        frame_copy = frame.copy()
        height, width = frame_copy.shape[:2]

        # Draw edge zones
        cv2.line(frame_copy, (int(left_edge), 0), (int(left_edge), height), (0, 0, 255), 2)
        cv2.line(frame_copy, (int(right_edge), 0), (int(right_edge), height), (0, 0, 255), 2)

        # Draw person position if detected
        if center_x is not None:
            color = (0, 255, 0) if not is_at_edge else (255, 0, 0)
            cv2.circle(frame_copy, (int(center_x), height // 2), 20, color, -1)
            cv2.line(frame_copy, (int(center_x), 0), (int(center_x), height), color, 2)

        # Add text overlay
        status = "AT EDGE" if is_at_edge else "CENTER STAGE" if center_x is not None else "NOT DETECTED"
        cv2.putText(frame_copy, f"{label} - Frame {frame_num}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame_copy, f"Status: {status}", (10, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        if center_x is not None:
            cv2.putText(frame_copy, f"Position: {int(center_x)}px", (10, 110),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        cv2.imwrite(output_path, frame_copy)
        print(f"  Exported debug frame: {output_path}")

    def detect_person_segments(self, video_path: str,
                               confidence_threshold: float = 0.5,
                               exit_threshold: float = 0.15) -> List[Tuple[float, float]]:
        """
        Detect when a person exits stage left or right.

        Args:
            video_path: Path to video
            confidence_threshold: Confidence threshold for person detection
            exit_threshold: Position threshold for stage exit (0.15 = within 15% of frame edge)

        Returns:
            List of (start, end) tuples representing comedian sets
        """
        print(f"Analyzing video for stage exits (left/right edge detection)...")
        print("This may take a few minutes...")

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

        print(f"Video: {duration:.1f}s, {fps:.1f} fps, {total_frames} frames, {frame_width}px wide")

        # Sample frames (check every second for efficiency)
        sample_interval = int(fps)

        # Track person position over time: (frame_num, center_x, is_at_edge)
        person_positions = []

        frame_num = 0
        checked_frames = 0

        # Define edge zones
        left_edge = frame_width * exit_threshold
        right_edge = frame_width * (1 - exit_threshold)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Only process every Nth frame
            if frame_num % sample_interval == 0:
                # Run YOLO detection
                results = self.model(frame, verbose=False)

                # Find person (class 0 in COCO) and track position
                person_center_x = None
                is_at_edge = False

                for result in results:
                    for box in result.boxes:
                        if box.cls == 0 and box.conf >= confidence_threshold:  # Class 0 = person
                            # Get bounding box coordinates
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            person_center_x = (x1 + x2) / 2

                            # Check if person is at left or right edge
                            if person_center_x < left_edge or person_center_x > right_edge:
                                is_at_edge = True

                            # Use first detected person (assumes single performer)
                            break
                    if person_center_x is not None:
                        break

                person_positions.append((frame_num, person_center_x, is_at_edge))
                checked_frames += 1

                if checked_frames % 60 == 0:
                    progress = (frame_num / total_frames) * 100
                    print(f"  Progress: {progress:.1f}% ({frame_num}/{total_frames} frames)")

            frame_num += 1

        cap.release()

        print(f"Analyzed {checked_frames} frames")

        # Count missing detections before interpolation
        missing_count = sum(1 for _, x, _ in person_positions if x is None)
        if missing_count > 0:
            print(f"Missing detections in {missing_count}/{len(person_positions)} frames ({missing_count/len(person_positions)*100:.1f}%)")
            print("Interpolating missing positions...")
            person_positions = self.interpolate_positions(person_positions)
            still_missing = sum(1 for _, x, _ in person_positions if x is None)
            print(f"After interpolation: {still_missing}/{len(person_positions)} frames still missing")

        # Convert to time-based segments based on stage exits
        segments = []
        current_start = None
        segment_frames = []  # Track frames for each segment for debug export

        for i, (frame_num, center_x, is_at_edge) in enumerate(person_positions):
            time = frame_num / fps

            # Person detected in center of stage
            if center_x is not None and not is_at_edge:
                if current_start is None:
                    # Person entered center stage
                    current_start = time
                    segment_frames.append([])
                if segment_frames:
                    segment_frames[-1].append((frame_num, center_x, is_at_edge))

            # Person exited stage (at edge or disappeared)
            elif current_start is not None:
                # End the current segment
                segments.append((current_start, time))
                current_start = None

        # Don't forget final segment if person is still on stage at end
        if current_start is not None:
            final_time = person_positions[-1][0] / fps
            segments.append((current_start, final_time))

        print(f"Detected {len(segments)} segments based on stage exits")

        # Debug info
        if segments:
            print(f"Exit detection zones: left edge < {left_edge:.0f}px, right edge > {right_edge:.0f}px")

        # Export debug frames if enabled
        if self.debug and segments and segment_frames:
            print("\nExporting debug frames for each segment...")

            # Create timestamped debug folder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_name = Path(video_path).stem
            output_dir = Path(video_path).parent / f"{video_name}_debug_{timestamp}"
            output_dir.mkdir(exist_ok=True)

            cap = cv2.VideoCapture(video_path)

            for seg_idx, frames_data in enumerate(segment_frames[:len(segments)], 1):
                if not frames_data:
                    continue

                # Export first frame
                first_frame_num, first_x, first_edge = frames_data[0]
                cap.set(cv2.CAP_PROP_POS_FRAMES, first_frame_num)
                ret, frame = cap.read()
                if ret:
                    output_path = str(output_dir / f"segment{seg_idx:02d}_first_frame{first_frame_num}.jpg")
                    self.export_debug_frame(frame, first_frame_num, first_x, first_edge,
                                          left_edge, right_edge, output_path,
                                          f"Segment {seg_idx} - FIRST")

                # Export last frame
                last_frame_num, last_x, last_edge = frames_data[-1]
                cap.set(cv2.CAP_PROP_POS_FRAMES, last_frame_num)
                ret, frame = cap.read()
                if ret:
                    output_path = str(output_dir / f"segment{seg_idx:02d}_last_frame{last_frame_num}.jpg")
                    self.export_debug_frame(frame, last_frame_num, last_x, last_edge,
                                          left_edge, right_edge, output_path,
                                          f"Segment {seg_idx} - LAST")

            cap.release()
            print(f"Debug frames saved to: {output_dir}")

        return segments

    def filter_segments(self, segments: List[Tuple[float, float]],
                       min_duration: float = 180.0) -> List[Tuple[float, float]]:
        """
        Filter segments by minimum duration.

        Args:
            segments: List of (start, end) tuples
            min_duration: Minimum duration in seconds (default 3 min)

        Returns:
            Filtered list of segments
        """
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
        """Clip video based on presence segments."""
        # Create timestamped folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_name = Path(video_path).stem

        if output_dir is None:
            base_dir = Path(video_path).parent
        else:
            base_dir = Path(output_dir)

        # Create timestamped subdirectory
        output_dir = base_dir / f"{video_name}_clips_{timestamp}"
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
                     min_duration: float = 180.0, confidence: float = 0.5,
                     exit_threshold: float = 0.15, model_size: str = "n"):
        """
        Complete pipeline: detect stage exits and clip.

        Args:
            video_path: Path to input video
            output_dir: Directory to save clips
            min_duration: Minimum duration for a set (default 3 min = 180s)
            confidence: Detection confidence threshold (default 0.5)
            exit_threshold: Position threshold for stage exit (default 0.15 = 15% from edge)
            model_size: YOLO model size
        """
        # Detect person segments based on stage exits
        segments = self.detect_person_segments(video_path, confidence, exit_threshold)

        if not segments:
            print("No person detected in video")
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
        description="Comedy clipper using person detection (detects entry/exit from stage)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (3 min minimum)
  python3 clipper_pose.py standup_show.mp4

  # 5 minute minimum sets
  python3 clipper_pose.py show.mp4 -m 300

  # More sensitive detection
  python3 clipper_pose.py show.mp4 -c 0.3

  # Save to specific directory
  python3 clipper_pose.py show.mp4 -o clips/

  # Enable debug mode (exports first/last frames with overlays)
  python3 clipper_pose.py show.mp4 -d

How it works:
  - Uses YOLO computer vision to detect person position on stage
  - Tracks when person exits stage left or right (based on horizontal position)
  - Clips from when person enters center stage to when they exit the edge
  - Perfect for static camera standup shows with comedians exiting stage left/right

Models:
  -s n  - Nano (fastest, less accurate)
  -s s  - Small (good balance) [default]
  -s m  - Medium (better accuracy)
  -s l  - Large (best accuracy, slower)
        """
    )

    parser.add_argument('video', help='Input video file')
    parser.add_argument('-o', '--output', help='Output directory for clips')
    parser.add_argument('-m', '--min-duration', type=float, default=180.0,
                       help='Minimum duration for a set in seconds (default: 180 = 3 minutes)')
    parser.add_argument('-c', '--confidence', type=float, default=0.5,
                       help='Detection confidence threshold 0-1 (default: 0.5)')
    parser.add_argument('-e', '--exit-threshold', type=float, default=0.15,
                       help='Edge threshold for stage exit 0-0.5 (default: 0.15 = 15%% from edge)')
    parser.add_argument('-s', '--model-size', default='n',
                       choices=['n', 's', 'm', 'l'],
                       help='YOLO model size: n=nano, s=small, m=medium, l=large (default: n)')
    parser.add_argument('-d', '--debug', action='store_true',
                       help='Export debug frames showing pose detection overlays')

    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"Error: Video file not found: {args.video}")
        sys.exit(1)

    try:
        clipper = PoseDetectionClipper(model_size=args.model_size, debug=args.debug)
        clipper.process_video(
            args.video,
            output_dir=args.output,
            min_duration=args.min_duration,
            confidence=args.confidence,
            exit_threshold=args.exit_threshold
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
