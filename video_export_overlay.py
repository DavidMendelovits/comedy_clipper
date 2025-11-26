#!/usr/bin/env python3
"""
Video Export with Overlay - Export video with CV overlays burned in
Reads from cached pose metadata and renders overlays on each frame
"""

import os
import sys
import json
import argparse
from pathlib import Path
import subprocess
from datetime import datetime

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("ERROR: OpenCV not installed. Run: pip install opencv-python", file=sys.stderr)
    sys.exit(1)


# COCO keypoint connections for skeleton
SKELETON = [
    (0, 1), (0, 2), (1, 3), (2, 4),  # Head
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # Arms
    (5, 11), (6, 12), (11, 12),  # Torso
    (11, 13), (13, 15), (12, 14), (14, 16)  # Legs
]

# Colors for different person IDs
PERSON_COLORS = [
    (255, 100, 0),   # Orange-blue
    (0, 255, 100),   # Green
    (100, 0, 255),   # Purple
    (255, 255, 0),   # Cyan
    (255, 0, 255),   # Magenta
    (0, 255, 255),   # Yellow
]


def emit_progress(phase: str, percent: int, frame: int = 0, total: int = 0, message: str = None):
    """Emit structured progress JSON for IPC"""
    progress_data = {
        "type": "export_progress",
        "phase": phase,
        "percent": percent,
        "frame": frame,
        "total": total
    }
    if message:
        progress_data["message"] = message

    print(f"[PROGRESS] {json.dumps(progress_data)}", flush=True)


def load_pose_metadata(cache_path: str) -> dict:
    """Load pose metadata from JSON cache file"""
    with open(cache_path, 'r') as f:
        data = json.load(f)

    # Convert string keys to float timestamps
    return {float(ts): info for ts, info in data.items()}


def find_nearest_pose_data(timestamp: float, pose_metadata: dict, tolerance: float = 1.0):
    """Find pose data for the nearest cached timestamp"""
    if not pose_metadata:
        return None

    timestamps = sorted(pose_metadata.keys())

    # Find closest timestamp
    closest_ts = None
    min_diff = float('inf')

    for ts in timestamps:
        diff = abs(ts - timestamp)
        if diff < min_diff:
            min_diff = diff
            closest_ts = ts

    # Return None if too far from any cached data
    if min_diff > tolerance:
        return None

    return pose_metadata.get(closest_ts)


def draw_skeleton(frame: np.ndarray, keypoints: list, color: tuple, opacity: float = 0.7):
    """Draw skeleton connections on frame"""
    overlay = frame.copy()

    for start_idx, end_idx in SKELETON:
        if start_idx < len(keypoints) and end_idx < len(keypoints):
            kp1 = keypoints[start_idx]
            kp2 = keypoints[end_idx]

            # keypoints format: (x, y, conf) or [x, y, conf]
            x1, y1 = float(kp1[0]), float(kp1[1])
            x2, y2 = float(kp2[0]), float(kp2[1])
            conf1 = float(kp1[2]) if len(kp1) > 2 else 1.0
            conf2 = float(kp2[2]) if len(kp2) > 2 else 1.0

            # Only draw if both keypoints are valid
            if x1 > 0 and y1 > 0 and x2 > 0 and y2 > 0 and conf1 > 0.3 and conf2 > 0.3:
                cv2.line(overlay, (int(x1), int(y1)), (int(x2), int(y2)), color, 3)

    cv2.addWeighted(overlay, opacity, frame, 1 - opacity, 0, frame)
    return frame


def draw_keypoints(frame: np.ndarray, keypoints: list, opacity: float = 0.7):
    """Draw keypoint circles on frame"""
    overlay = frame.copy()

    for idx, kp in enumerate(keypoints):
        x, y = float(kp[0]), float(kp[1])
        conf = float(kp[2]) if len(kp) > 2 else 1.0

        if x > 0 and y > 0 and conf > 0.3:
            # Radius based on confidence
            radius = int(4 + conf * 6)
            cv2.circle(overlay, (int(x), int(y)), radius, (0, 255, 0), -1)
            cv2.circle(overlay, (int(x), int(y)), radius + 2, (255, 255, 255), 1)

    cv2.addWeighted(overlay, opacity, frame, 1 - opacity, 0, frame)
    return frame


def draw_bbox(frame: np.ndarray, bbox: tuple, person_id: int, opacity: float = 0.7):
    """Draw bounding box with person ID label"""
    overlay = frame.copy()

    x1, y1, x2, y2 = [int(v) for v in bbox]
    color = PERSON_COLORS[person_id % len(PERSON_COLORS)]

    # Draw rectangle
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 3)

    # Draw label background
    label = f"Person {person_id}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness = 2
    (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)

    cv2.rectangle(overlay, (x1, y1 - text_height - 10), (x1 + text_width + 10, y1), color, -1)
    cv2.putText(overlay, label, (x1 + 5, y1 - 5), font, font_scale, (255, 255, 255), thickness)

    cv2.addWeighted(overlay, opacity, frame, 1 - opacity, 0, frame)
    return frame


def export_video_with_overlays(
    video_path: str,
    pose_cache_path: str,
    output_path: str,
    overlays: list = None
):
    """
    Export video with overlays burned in

    Args:
        video_path: Path to source video
        pose_cache_path: Path to pose metadata JSON cache
        output_path: Path for output video
        overlays: List of overlays to include ['skeleton', 'bbox', 'keypoints']
    """
    if overlays is None:
        overlays = ['skeleton', 'bbox', 'keypoints']

    print(f"[STEP] Loading pose metadata from cache...", flush=True)
    emit_progress("loading", 0, message="Loading pose metadata")

    # Load pose metadata
    pose_metadata = load_pose_metadata(pose_cache_path)
    print(f"  Loaded {len(pose_metadata)} cached timestamps", flush=True)

    emit_progress("loading", 50, message=f"Loaded {len(pose_metadata)} timestamps")

    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = total_frames / fps if fps > 0 else 0

    print(f"  Video: {total_frames} frames, {fps:.1f} fps, {width}x{height}", flush=True)
    print(f"  Duration: {duration:.1f}s", flush=True)
    print(f"  Overlays: {', '.join(overlays)}", flush=True)

    emit_progress("loading", 100, message="Video loaded")

    # Create output directory if needed
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use a temp file for initial encoding
    temp_output = str(Path(output_path).with_suffix('.temp.mp4'))

    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_output, fourcc, fps, (width, height))

    if not out.isOpened():
        raise RuntimeError(f"Could not create video writer for {temp_output}")

    print(f"\n[STEP] Rendering overlays on video frames...", flush=True)
    emit_progress("rendering", 0, 0, total_frames, "Starting render")

    frame_num = 0
    last_progress_percent = -1

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Calculate timestamp for this frame
            timestamp = frame_num / fps

            # Find pose data for this timestamp
            pose_data = find_nearest_pose_data(timestamp, pose_metadata)

            # Draw overlays if we have pose data
            if pose_data and 'detections' in pose_data:
                for detection in pose_data['detections']:
                    person_id = detection.get('person_id', 0)
                    bbox = detection.get('bbox')
                    keypoints = detection.get('keypoints', [])

                    color = PERSON_COLORS[person_id % len(PERSON_COLORS)]

                    # Draw skeleton
                    if 'skeleton' in overlays and keypoints:
                        frame = draw_skeleton(frame, keypoints, color)

                    # Draw keypoints
                    if 'keypoints' in overlays and keypoints:
                        frame = draw_keypoints(frame, keypoints)

                    # Draw bounding box
                    if 'bbox' in overlays and bbox:
                        frame = draw_bbox(frame, bbox, person_id)

            # Write frame
            out.write(frame)

            frame_num += 1

            # Emit progress every 1%
            progress_percent = int((frame_num / total_frames) * 100)
            if progress_percent != last_progress_percent:
                emit_progress("rendering", progress_percent, frame_num, total_frames,
                            f"Frame {frame_num}/{total_frames}")
                last_progress_percent = progress_percent

    finally:
        cap.release()
        out.release()

    print(f"  Rendered {frame_num} frames", flush=True)

    # Re-encode with H.264 for better compatibility
    print(f"\n[STEP] Re-encoding with H.264...", flush=True)
    emit_progress("encoding", 0, message="Re-encoding with H.264")

    cmd = [
        'ffmpeg', '-y',
        '-i', temp_output,
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            # Remove temp file
            os.remove(temp_output)
            print(f"  Encoded successfully", flush=True)
        else:
            print(f"Warning: FFmpeg re-encoding failed: {result.stderr}", file=sys.stderr)
            # Rename temp file as output
            os.rename(temp_output, output_path)

    except FileNotFoundError:
        print("Warning: FFmpeg not found, using raw output", file=sys.stderr)
        os.rename(temp_output, output_path)

    # Get output file size
    file_size = os.path.getsize(output_path)
    file_size_mb = file_size / (1024 * 1024)

    print(f"\n[STEP] Export complete!", flush=True)
    print(f"  Output: {output_path}", flush=True)
    print(f"  Size: {file_size_mb:.1f} MB", flush=True)

    emit_progress("complete", 100, frame_num, total_frames, "Export complete")

    return {
        "success": True,
        "outputPath": output_path,
        "frames": frame_num,
        "duration": duration,
        "fileSize": file_size
    }


def main():
    parser = argparse.ArgumentParser(
        description="Export video with CV overlays burned in"
    )

    parser.add_argument('--video', required=True, help='Input video file')
    parser.add_argument('--pose-cache', required=True, help='Path to pose metadata JSON cache')
    parser.add_argument('--output', required=True, help='Output video path')
    parser.add_argument('--overlays', default='skeleton,bbox,keypoints',
                       help='Comma-separated list of overlays: skeleton, bbox, keypoints')

    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.video):
        print(f"Error: Video not found: {args.video}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.pose_cache):
        print(f"Error: Pose cache not found: {args.pose_cache}", file=sys.stderr)
        sys.exit(1)

    # Parse overlays
    overlays = [o.strip() for o in args.overlays.split(',') if o.strip()]

    try:
        result = export_video_with_overlays(
            video_path=args.video,
            pose_cache_path=args.pose_cache,
            output_path=args.output,
            overlays=overlays
        )

        # Output final result as JSON
        print(json.dumps(result))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)


if __name__ == '__main__':
    main()
