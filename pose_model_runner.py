#!/usr/bin/env python3
"""
Pose Model Runner for Frontend Integration
Runs multiple pose detection models in parallel and streams results back.
"""

import sys
import json
import subprocess
import threading
import time
from pathlib import Path
from typing import List, Dict, Any
import cv2
import base64


class PoseModelRunner:
    """Manages parallel execution of multiple pose detection models."""

    AVAILABLE_MODELS = {
        'mediapipe': {
            'script': 'pose_mediapipe.py',
            'name': 'MediaPipe Pose',
            'requires_model_file': False,
        },
        'movenet_lightning': {
            'script': 'pose_movenet.py',
            'name': 'MoveNet Lightning',
            'requires_model_file': False,
            'args': ['-m', 'lightning']
        },
        'movenet_thunder': {
            'script': 'pose_movenet.py',
            'name': 'MoveNet Thunder',
            'requires_model_file': False,
            'args': ['-m', 'thunder']
        },
        'yolo': {
            'script': 'clipper_yolo_pose.py',
            'name': 'YOLO Pose',
            'requires_model_file': True,
            'model_file': 'yolo11l-pose.pt',
        },
        'openpose_coco': {
            'script': 'pose_openpose.py',
            'name': 'OpenPose COCO',
            'requires_model_file': True,
            'model_dir': 'openpose_models',
            'args': ['-t', 'COCO']
        },
        'mmpose_rtmpose_m': {
            'script': 'pose_mmpose.py',
            'name': 'MMPose RTMPose-M',
            'requires_model_file': False,
            'args': ['-m', 'rtmpose-m']
        },
        'mmpose_hrnet_w48': {
            'script': 'pose_mmpose.py',
            'name': 'MMPose HRNet-W48',
            'requires_model_file': False,
            'args': ['-m', 'hrnet-w48']
        }
    }

    def __init__(self, video_path: str, output_dir: str = None):
        """
        Initialize model runner.

        Args:
            video_path: Path to input video
            output_dir: Directory for output files
        """
        self.video_path = Path(video_path)

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.video_path.parent / 'pose_comparison'

        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.results = {}
        self.threads = {}
        self.processes = {}

    def check_model_availability(self, model_id: str) -> Dict[str, Any]:
        """Check if a model is available to run."""
        if model_id not in self.AVAILABLE_MODELS:
            return {'available': False, 'reason': 'Unknown model'}

        model_config = self.AVAILABLE_MODELS[model_id]
        script_path = Path(__file__).parent / model_config['script']

        if not script_path.exists():
            return {'available': False, 'reason': f"Script not found: {model_config['script']}"}

        # Check for required model files
        if model_config.get('requires_model_file'):
            if 'model_file' in model_config:
                model_file = Path(__file__).parent / model_config['model_file']
                if not model_file.exists():
                    return {
                        'available': False,
                        'reason': f"Model file not found: {model_config['model_file']}"
                    }

            if 'model_dir' in model_config:
                model_dir = Path(__file__).parent / model_config['model_dir']
                if not model_dir.exists():
                    return {
                        'available': False,
                        'reason': f"Model directory not found: {model_config['model_dir']}"
                    }

        return {'available': True}

    def get_output_path(self, model_id: str) -> Path:
        """Get output video path for a model."""
        return self.output_dir / f"{self.video_path.stem}_{model_id}.mp4"

    def extract_debug_frame(self, video_path: Path, frame_number: int = 0) -> str:
        """Extract a debug frame from video as base64."""
        try:
            cap = cv2.VideoCapture(str(video_path))

            # Seek to frame
            if frame_number > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

            ret, frame = cap.read()
            cap.release()

            if ret:
                # Encode as JPEG
                _, buffer = cv2.imencode('.jpg', frame)
                # Convert to base64
                jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                return f"data:image/jpeg;base64,{jpg_as_text}"

            return None
        except Exception as e:
            print(f"Error extracting frame: {e}", file=sys.stderr)
            return None

    def run_model(self, model_id: str, progress_callback=None) -> Dict[str, Any]:
        """
        Run a single model.

        Args:
            model_id: Model identifier
            progress_callback: Callback function(model_id, progress_data)

        Returns:
            Result dictionary with stats and output path
        """
        # Check availability
        availability = self.check_model_availability(model_id)
        if not availability['available']:
            return {
                'status': 'skipped',
                'error': availability['reason']
            }

        model_config = self.AVAILABLE_MODELS[model_id]
        output_path = self.get_output_path(model_id)

        # Build command
        cmd = [
            sys.executable,
            str(Path(__file__).parent / model_config['script']),
            str(self.video_path),
            '-o', str(output_path)
        ]

        # Add model-specific args
        if 'args' in model_config:
            cmd.extend(model_config['args'])

        # Add model directory for OpenPose
        if 'model_dir' in model_config:
            cmd.extend(['-m', str(Path(__file__).parent / model_config['model_dir'])])

        # Run process
        start_time = time.time()

        try:
            if progress_callback:
                progress_callback(model_id, {
                    'status': 'running',
                    'progress': 0,
                    'message': f'Starting {model_config["name"]}...'
                })

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            elapsed = time.time() - start_time

            # Parse statistics from output
            stats = self._parse_output(result.stdout)
            stats['total_time'] = elapsed
            stats['status'] = 'success'
            stats['output_file'] = str(output_path)
            stats['model_name'] = model_config['name']

            # Extract debug frame from output video
            if output_path.exists():
                debug_frame = self.extract_debug_frame(output_path, frame_number=30)
                stats['debug_frame'] = debug_frame

            if progress_callback:
                progress_callback(model_id, {
                    'status': 'complete',
                    'progress': 100,
                    'stats': stats
                })

            return stats

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)

            if progress_callback:
                progress_callback(model_id, {
                    'status': 'failed',
                    'error': error_msg
                })

            return {
                'status': 'failed',
                'error': error_msg,
                'total_time': time.time() - start_time,
                'model_name': model_config['name']
            }

    def _parse_output(self, output: str) -> Dict[str, Any]:
        """Parse statistics from script output."""
        stats = {}

        lines = output.split('\n')
        for line in lines:
            if 'Total frames processed:' in line:
                try:
                    stats['total_frames'] = int(line.split(':')[1].strip())
                except:
                    pass
            elif 'Frames with pose detected:' in line or 'detected:' in line:
                try:
                    stats['detected_frames'] = int(line.split(':')[1].strip())
                except:
                    pass
            elif 'Detection rate:' in line:
                try:
                    stats['detection_rate'] = float(line.split(':')[1].strip().replace('%', ''))
                except:
                    pass
            elif 'Average processing time per frame:' in line:
                try:
                    time_str = line.split(':')[1].strip().replace('ms', '')
                    stats['avg_time_per_frame_ms'] = float(time_str)
                except:
                    pass
            elif 'Average FPS:' in line:
                try:
                    stats['avg_fps'] = float(line.split(':')[1].strip())
                except:
                    pass

        return stats

    def run_models_parallel(self, model_ids: List[str], progress_callback=None) -> Dict[str, Any]:
        """
        Run multiple models in parallel.

        Args:
            model_ids: List of model identifiers to run
            progress_callback: Callback function(model_id, progress_data)

        Returns:
            Dictionary of results keyed by model_id
        """
        results = {}
        threads = []

        def run_thread(model_id):
            results[model_id] = self.run_model(model_id, progress_callback)

        # Start threads
        for model_id in model_ids:
            thread = threading.Thread(target=run_thread, args=(model_id,))
            thread.start()
            threads.append(thread)

        # Wait for all to complete
        for thread in threads:
            thread.join()

        return results

    def export_overlay_video(
        self,
        model_id: str,
        overlay_config: Dict[str, Any] = None,
        progress_callback=None
    ) -> Path:
        """
        Export full video with pose detection overlays.

        Args:
            model_id: Model identifier (used to determine detection type)
            overlay_config: Configuration for overlay export:
                - includeSkeletons: bool (default True)
                - includeBoundingBoxes: bool (default False)
                - includeInfoOverlay: bool (default True)
                - includeStageMarkers: bool (default True)
                - opacity: float 0-1 (default 0.7)
            progress_callback: Callback function for progress updates

        Returns:
            Path to exported overlay video
        """
        if overlay_config is None:
            overlay_config = {}

        # Default config
        include_skeletons = overlay_config.get('includeSkeletons', True)
        include_boxes = overlay_config.get('includeBoundingBoxes', False)
        include_info = overlay_config.get('includeInfoOverlay', True)
        include_stage = overlay_config.get('includeStageMarkers', True)

        # Map model_id to detection mode for video_overlay_player.py
        detection_mode_map = {
            'yolo': 'yolo_pose',
            'mediapipe': 'mediapipe_pose',
            'openpose_coco': 'yolo_pose',  # Fallback to YOLO for visualization
            'openpose_mpi': 'yolo_pose',
            'movenet_lightning': 'yolo_pose',
            'movenet_thunder': 'yolo_pose',
            'mmpose_rtmpose_m': 'yolo_pose',
            'mmpose_hrnet_w48': 'yolo_pose',
        }

        detection_mode = detection_mode_map.get(model_id, 'yolo_pose')

        # Output path for overlay video
        overlay_path = self.output_dir / f"{self.video_path.stem}_{model_id}_overlay.mp4"

        # Build command for video_overlay_player.py
        cmd = [
            sys.executable,
            str(Path(__file__).parent / 'video_overlay_player.py'),
            str(self.video_path),
            '--export',
            '-o', str(overlay_path),
            '--detections', detection_mode
        ]

        # Add optional flags
        if not include_skeletons:
            cmd.append('--no-yolo')
        if not include_info:
            cmd.append('--no-info')
        if not include_stage:
            cmd.append('--no-stage-boundary')

        try:
            if progress_callback:
                progress_callback(model_id, {
                    'status': 'exporting_overlay',
                    'message': 'Generating overlay video...'
                })

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            if progress_callback:
                progress_callback(model_id, {
                    'status': 'overlay_complete',
                    'overlay_path': str(overlay_path)
                })

            return overlay_path

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            print(f"Error exporting overlay for {model_id}: {error_msg}", file=sys.stderr)

            if progress_callback:
                progress_callback(model_id, {
                    'status': 'overlay_failed',
                    'error': error_msg
                })

            return None

    def generate_comparison_json(self, results: Dict[str, Any]) -> Path:
        """Generate a JSON comparison report."""
        report_path = self.output_dir / 'comparison_results.json'

        with open(report_path, 'w') as f:
            json.dump({
                'video': str(self.video_path),
                'output_dir': str(self.output_dir),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'results': results
            }, f, indent=2)

        return report_path


def main():
    """CLI interface for running models."""
    if len(sys.argv) < 3:
        print("Usage: python pose_model_runner.py <video_path> <model_ids...>")
        print("\nAvailable models:")
        for model_id, config in PoseModelRunner.AVAILABLE_MODELS.items():
            print(f"  - {model_id}: {config['name']}")
        sys.exit(1)

    video_path = sys.argv[1]
    model_ids = sys.argv[2:]

    runner = PoseModelRunner(video_path)

    # Progress callback that prints to stdout as JSON
    def progress_callback(model_id, data):
        print(json.dumps({
            'type': 'progress',
            'model_id': model_id,
            'data': data
        }), flush=True)

    # Run models
    results = runner.run_models_parallel(model_ids, progress_callback)

    # Generate report
    report_path = runner.generate_comparison_json(results)

    # Print final results
    print(json.dumps({
        'type': 'complete',
        'results': results,
        'report_path': str(report_path)
    }), flush=True)


if __name__ == '__main__':
    main()
