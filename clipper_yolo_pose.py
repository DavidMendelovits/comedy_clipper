#!/usr/bin/env python3
"""
YOLO11/12 Pose Detection Clipper
Uses Ultralytics YOLO11 or YOLO12 for advanced pose detection
Supports real-time visualization and overlay export
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import subprocess
from datetime import datetime
from config_loader import load_config, ClipperConfig
import json

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    YOLO = None


class YOLOPoseClipper:
    """YOLO11/12-based pose detection clipper with advanced visualization"""

    def __init__(self, config: ClipperConfig, model_name: str = "yolo11n-pose.pt", debug: bool = False):
        """
        Initialize YOLO pose clipper.

        Args:
            config: Loaded configuration
            model_name: YOLO model (yolo11n-pose.pt, yolo11s-pose.pt, yolo11m-pose.pt,
                        yolo11l-pose.pt, yolo11x-pose.pt)
            debug: Whether to export debug frames with overlays
        """
        if not YOLO_AVAILABLE:
            raise ImportError("Ultralytics not installed. Run: pip install ultralytics")
        if not CV2_AVAILABLE:
            raise ImportError("OpenCV not installed. Run: pip install opencv-python")

        self.config = config
        self.debug = debug or config.get("debug.export_frames", False)
        self.debug_dir = None

        print(f"Initializing YOLO Pose Detection ({model_name})...")
        self.yolo = YOLO(model_name)

        # Verify it's a pose model
        if hasattr(self.yolo, 'task') and self.yolo.task != 'pose':
            print(f"Warning: Model {model_name} is not a pose model (task={self.yolo.task})")
            print("Consider using: yolo11n-pose.pt, yolo11s-pose.pt, yolo11m-pose.pt, etc.")

        self.confidence_threshold = config.get("yolo_detection.confidence", 0.5)
        print(f"  Model: {model_name}")
        print(f"  Confidence threshold: {self.confidence_threshold}")

    def _emit_progress(self, phase: str, percent: int, current: int = None, total: int = None, message: str = None):
        """Emit structured progress JSON for UI consumption"""
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

        print(f"[PROGRESS] {json.dumps(progress_data)}")
        sys.stdout.flush()

    def detect_segments(self, video_path: str, json_output: bool = False) -> List[Tuple[float, float]]:
        """Detect segments using YOLO pose detection"""
        if not json_output:
            print(f"[STEP] Loading video for YOLO pose detection")

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

        # Edge zones for exit detection
        exit_threshold = self.config.get("position_detection.exit_threshold", 0.15)
        left_edge = frame_width * exit_threshold
        right_edge = frame_width * (1 - exit_threshold)

        frame_num = 0
        checked_frames = 0

        if not json_output:
            print("[STEP] Processing video frames with YOLO pose detection")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_num % sample_interval == 0:
                # Run YOLO pose detection
                results = self.yolo(frame, conf=self.confidence_threshold, verbose=False)

                num_poses = 0
                pose_positions = []
                keypoints_data = []

                if len(results) > 0 and hasattr(results[0], 'keypoints'):
                    keypoints = results[0].keypoints

                    if keypoints is not None and keypoints.xy is not None:
                        num_poses = len(keypoints.xy)

                        # Process each detected person
                        for person_idx in range(num_poses):
                            kpts = keypoints.xy[person_idx]  # Shape: (17, 2) for COCO keypoints

                            # Calculate center position from keypoints
                            # Use shoulders and hips if available
                            # COCO format: 0=nose, 5=left_shoulder, 6=right_shoulder,
                            #              11=left_hip, 12=right_hip
                            valid_points = []
                            for idx in [5, 6, 11, 12]:  # shoulders and hips
                                if idx < len(kpts):
                                    x, y = kpts[idx]
                                    if x > 0 and y > 0:  # valid keypoint
                                        valid_points.append(x.item())

                            if valid_points:
                                center_x = sum(valid_points) / len(valid_points)
                                pose_positions.append(center_x)

                            # Store keypoints for visualization
                            keypoints_data.append({
                                'xy': kpts.cpu().numpy(),
                                'conf': keypoints.conf[person_idx].cpu().numpy() if keypoints.conf is not None else None
                            })

                # Calculate average position
                avg_position = sum(pose_positions) / len(pose_positions) if pose_positions else None

                detection_history.append((
                    frame_num, num_poses, avg_position
                ))

                # Debug: Print first few detections
                if checked_frames < 5 and not json_output:
                    print(f"  Frame {frame_num}: poses={num_poses}, position={avg_position}")

                if self.debug:
                    # Store frame and keypoints for visualization
                    debug_data[frame_num] = {
                        'frame': frame.copy(),
                        'keypoints': keypoints_data,
                        'num_poses': num_poses
                    }

                checked_frames += 1

                if checked_frames % 30 == 0:
                    progress = int((frame_num / total_frames) * 100)
                    self._emit_progress("detection", progress, frame_num, total_frames, "Processing frames")
                    if not json_output:
                        print(f"  Progress: {progress}% ({frame_num}/{total_frames} frames)")

            frame_num += 1

        cap.release()

        self._emit_progress("detection", 100, total_frames, total_frames, "Frame processing complete")

        # Statistics
        total_with_poses = sum(1 for d in detection_history if d[1] > 0)
        print(f"Analyzed {checked_frames} frames")
        print(f"  Frames with poses detected: {total_with_poses}/{checked_frames} ({100*total_with_poses/checked_frames:.1f}%)")

        # Analyze transitions
        self._emit_progress("analysis", 0, 0, 1, "Analyzing transitions")
        segments = self._analyze_transitions(detection_history, fps, left_edge, right_edge, debug_data, video_path)
        self._emit_progress("analysis", 100, 1, 1, "Analysis complete")

        return segments

    def _analyze_transitions(self, detection_history, fps, left_edge, right_edge, debug_data, video_path):
        """Analyze transitions based on pose detection"""
        print("\nUsing position-based detection (stage entry/exit)...")

        segments = []
        current_start = None
        exit_stability_frames = self.config.get("position_detection.exit_stability_frames", 2)

        # Track consecutive frames at edge
        at_edge_count = 0

        print(f"\nPosition-based detection parameters:")
        print(f"  Left edge threshold: {left_edge:.1f} pixels")
        print(f"  Right edge threshold: {right_edge:.1f} pixels")
        print(f"  Exit stability frames: {exit_stability_frames}")

        for i, (frame_num, num_poses, position) in enumerate(detection_history):
            time = frame_num / fps

            has_detection = num_poses > 0

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
            # No detection at all - also end segment if one is active
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

        # Export debug visualization if enabled
        if self.debug and segments and debug_data:
            self._export_debug_visualization(segments, debug_data, video_path, fps)

        return segments

    def _export_debug_visualization(self, segments, debug_data, video_path, fps):
        """Export frames with pose overlay visualization"""
        print("\nExporting debug frames with pose overlays...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_name = Path(video_path).stem
        output_dir = Path(video_path).parent / f"{video_name}_yolo_pose_debug_{timestamp}"
        output_dir.mkdir(exist_ok=True)

        self.debug_dir = str(output_dir)

        # COCO keypoint connections for skeleton
        SKELETON = [
            (0, 1), (0, 2), (1, 3), (2, 4),  # Head
            (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # Arms
            (5, 11), (6, 12), (11, 12),  # Torso
            (11, 13), (13, 15), (12, 14), (14, 16)  # Legs
        ]

        # Colors for keypoints (BGR)
        KEYPOINT_COLOR = (0, 255, 0)  # Green
        SKELETON_COLOR = (255, 100, 0)  # Blue

        # Export timeline frames (every 30 seconds)
        print("Exporting timeline frames...")
        timeline_dir = output_dir / "timeline"
        timeline_dir.mkdir(exist_ok=True)

        exported_count = 0
        for frame_num, data in debug_data.items():
            time_sec = frame_num / fps

            # Export every 30 seconds
            if int(time_sec) % 30 != 0:
                continue

            frame = data['frame']
            keypoints_list = data['keypoints']

            # Draw pose overlays
            annotated = self._draw_pose_overlay(frame, keypoints_list, SKELETON, KEYPOINT_COLOR, SKELETON_COLOR)

            # Add info text
            cv2.putText(annotated, f"Time: {int(time_sec)}s", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(annotated, f"Poses: {data['num_poses']}", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            output_path = timeline_dir / f"frame_{int(time_sec):04d}s.jpg"
            cv2.imwrite(str(output_path), annotated)
            exported_count += 1

        print(f"Exported {exported_count} timeline frames")

        # Export segment boundary frames
        print("Exporting segment boundary frames...")
        segments_dir = output_dir / "segments"
        segments_dir.mkdir(exist_ok=True)

        for i, (start, end, start_idx, end_idx) in enumerate(segments, 1):
            # Export start frame
            start_frame_num = int(start * fps)
            if start_frame_num in debug_data:
                data = debug_data[start_frame_num]
                frame = data['frame']
                keypoints_list = data['keypoints']

                annotated = self._draw_pose_overlay(frame, keypoints_list, SKELETON, KEYPOINT_COLOR, SKELETON_COLOR)

                cv2.putText(annotated, f"Segment {i} START", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(annotated, f"Time: {start:.1f}s", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                output_path = segments_dir / f"seg{i:02d}_start_{start:.1f}s.jpg"
                cv2.imwrite(str(output_path), annotated)

            # Export end frame
            end_frame_num = int(end * fps)
            if end_frame_num in debug_data:
                data = debug_data[end_frame_num]
                frame = data['frame']
                keypoints_list = data['keypoints']

                annotated = self._draw_pose_overlay(frame, keypoints_list, SKELETON, KEYPOINT_COLOR, SKELETON_COLOR)

                cv2.putText(annotated, f"Segment {i} END", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.putText(annotated, f"Time: {end:.1f}s", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                output_path = segments_dir / f"seg{i:02d}_end_{end:.1f}s.jpg"
                cv2.imwrite(str(output_path), annotated)

        print(f"Debug frames saved to: {output_dir}")

    def _draw_pose_overlay(self, frame, keypoints_list, skeleton, keypoint_color, skeleton_color):
        """Draw pose keypoints and skeleton on frame"""
        annotated = frame.copy()

        for kpt_data in keypoints_list:
            kpts = kpt_data['xy']
            conf = kpt_data['conf']

            # Draw skeleton connections
            for start_idx, end_idx in skeleton:
                if start_idx < len(kpts) and end_idx < len(kpts):
                    x1, y1 = kpts[start_idx]
                    x2, y2 = kpts[end_idx]

                    # Only draw if both keypoints are valid
                    if x1 > 0 and y1 > 0 and x2 > 0 and y2 > 0:
                        cv2.line(annotated, (int(x1), int(y1)), (int(x2), int(y2)),
                                skeleton_color, 2)

            # Draw keypoints
            for idx, (x, y) in enumerate(kpts):
                if x > 0 and y > 0:
                    # Vary circle size based on confidence if available
                    radius = 5
                    if conf is not None and idx < len(conf):
                        radius = int(3 + conf[idx] * 5)
                    cv2.circle(annotated, (int(x), int(y)), radius, keypoint_color, -1)

        return annotated

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

    def _generate_overlay_video(self, video_path: str, output_dir: str = None, json_output: bool = False) -> str:
        """
        Generate overlay video with pose detection visualizations using video_overlay_player.py

        Args:
            video_path: Path to input video
            output_dir: Directory to save overlay video (default: same as video)
            json_output: Whether to suppress print output

        Returns:
            Path to generated overlay video, or None if generation failed
        """
        import sys
        import subprocess

        # Determine output path
        if output_dir is None:
            output_dir = str(Path(video_path).parent)

        video_name = Path(video_path).stem
        overlay_output = Path(output_dir) / f"{video_name}_overlay.mp4"

        # Path to video_overlay_player.py script
        script_dir = Path(__file__).parent
        overlay_script = script_dir / "video_overlay_player.py"

        if not overlay_script.exists():
            if not json_output:
                print(f"[WARNING] Overlay script not found: {overlay_script}")
            return None

        # Build command to generate overlay video - use YOLO pose detection
        cmd = [
            sys.executable,
            str(overlay_script),
            video_path,
            '--export',
            '--output', str(overlay_output),
            '--detections', 'yolo_pose',
        ]

        # Add overlay configuration options
        if not self.config.get("overlay_include_skeletons", True):
            cmd.append('--no-yolo')

        if not self.config.get("overlay_show_info", True):
            cmd.append('--no-info')

        try:
            if not json_output:
                print(f"Generating overlay video: {overlay_output}")
                print(f"Command: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # 1 hour timeout

            if result.returncode == 0:
                # The script might return the final H.264 path
                if overlay_output.exists():
                    return str(overlay_output)
                else:
                    # Check for _h264 version
                    h264_output = overlay_output.parent / f"{overlay_output.stem}_h264.mp4"
                    if h264_output.exists():
                        return str(h264_output)
            else:
                if not json_output:
                    print(f"[WARNING] Overlay generation failed with code {result.returncode}")
                    print(f"STDERR: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            if not json_output:
                print(f"[WARNING] Overlay generation timed out after 1 hour")
            return None
        except Exception as e:
            if not json_output:
                print(f"[WARNING] Overlay generation error: {e}")
            return None

    def process_video(self, video_path: str, output_dir: str = None, json_output: bool = False) -> dict:
        """Complete pipeline - returns structured result"""
        if not json_output:
            print(f"[STEP] Starting YOLO pose video processing")

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
                result['error'] = f'No segments passed filtering (min duration: {min_dur}s)'
                result['success'] = True
                return result

            if not json_output:
                print(f"\nFinal segments after filtering:")
                for i, (start, end) in enumerate(filtered, 1):
                    print(f"  {i}. {start:.1f}s - {end:.1f}s ({(end-start)/60:.1f} min)")

            clips = self.clip_video(video_path, filtered, output_dir, json_output)
            result['clips'] = clips
            result['output_dir'] = str(Path(clips[0]).parent) if clips else None
            result['debug_dir'] = self.debug_dir
            result['success'] = True

            # Generate overlay video if requested
            export_overlay = self.config.get("export_overlay_video", False)
            if export_overlay:
                if not json_output:
                    print(f"[STEP] Generating overlay video...")

                try:
                    overlay_video_path = self._generate_overlay_video(video_path, output_dir or str(Path(clips[0]).parent) if clips else None, json_output)
                    if overlay_video_path:
                        result['overlay_video'] = overlay_video_path
                        if not json_output:
                            print(f"[STEP] Overlay video created: {overlay_video_path}")
                except Exception as e:
                    if not json_output:
                        print(f"[WARNING] Failed to generate overlay video: {e}")
                    # Don't fail the entire job if overlay generation fails

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
        description="YOLO11/12 Pose Detection Comedy Clipper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
YOLO Models:
  yolo11n-pose.pt  - Nano (fastest, least accurate)
  yolo11s-pose.pt  - Small
  yolo11m-pose.pt  - Medium (recommended)
  yolo11l-pose.pt  - Large
  yolo11x-pose.pt  - Extra Large (slowest, most accurate)

  Also supports yolo12 models when available

Examples:
  # Use default model (yolo11n-pose)
  python3 clipper_yolo_pose.py video.mp4

  # Use medium model for better accuracy
  python3 clipper_yolo_pose.py video.mp4 --model yolo11m-pose.pt

  # Enable debug visualization
  python3 clipper_yolo_pose.py video.mp4 -d

  # Use custom config
  python3 clipper_yolo_pose.py video.mp4 -c my_config.yaml
        """
    )

    parser.add_argument('video', help='Input video file')
    parser.add_argument('--model', default='yolo11n-pose.pt',
                       help='YOLO pose model (default: yolo11n-pose.pt)')
    parser.add_argument('-c', '--config', help='Config file (default: clipper_rules.yaml)')
    parser.add_argument('-o', '--output', help='Output directory for clips')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug visualization')
    parser.add_argument('--min-duration', type=float, help='Override minimum duration (seconds)')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')

    # Overlay video generation options
    parser.add_argument('--export-overlay', action='store_true',
                       help='Export full video with pose detection overlays')
    parser.add_argument('--no-overlay-skeletons', action='store_true',
                       help='Disable skeleton overlays in overlay video')
    parser.add_argument('--overlay-show-info', action='store_true',
                       help='Show info overlay in overlay video (default: True)')

    args = parser.parse_args()

    if not os.path.exists(args.video):
        error_msg = f"Error: Video not found: {args.video}"
        if args.json:
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

        # Override overlay settings if specified
        if args.export_overlay:
            config.raw["export_overlay_video"] = True
            config.raw["overlay_include_skeletons"] = not args.no_overlay_skeletons
            config.raw["overlay_show_info"] = args.overlay_show_info

        # Create clipper
        clipper = YOLOPoseClipper(config, model_name=args.model, debug=args.debug)

        # Process video
        result = clipper.process_video(args.video, output_dir=args.output, json_output=args.json)

        # Output JSON if requested
        if args.json:
            print(json.dumps(result, indent=2))

        # Exit with error code if failed
        if not result['success']:
            sys.exit(1)

    except Exception as e:
        error_msg = str(e)
        if args.json:
            print(json.dumps({'success': False, 'error': error_msg}))
        else:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
