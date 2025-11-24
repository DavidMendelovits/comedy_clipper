#!/usr/bin/env python3
"""
Pose Model Comparison Script
Runs multiple pose detection models on the same video and generates comparison report.
"""

import subprocess
import json
import time
import argparse
from pathlib import Path
import sys


class PoseModelComparison:
    def __init__(self, input_video, output_dir):
        """
        Initialize comparison runner.

        Args:
            input_video: Path to input video file
            output_dir: Directory to save output videos and reports
        """
        self.input_video = Path(input_video)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.results = {}

    def run_mediapipe(self, complexity=2):
        """Run MediaPipe Pose detection."""
        print("\n" + "="*60)
        print("RUNNING: MediaPipe Pose")
        print("="*60)

        output_file = self.output_dir / f"{self.input_video.stem}_mediapipe.mp4"

        cmd = [
            sys.executable, "pose_mediapipe.py",
            str(self.input_video),
            "-o", str(output_file),
            "-c", str(complexity)
        ]

        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            elapsed = time.time() - start_time

            # Parse statistics from output
            stats = self._parse_output(result.stdout)
            stats['total_time'] = elapsed
            stats['status'] = 'success'
            stats['output_file'] = str(output_file)

            self.results['mediapipe'] = stats

            print(f"✓ MediaPipe completed in {elapsed:.1f}s")
            return True

        except subprocess.CalledProcessError as e:
            print(f"✗ MediaPipe failed: {e}")
            self.results['mediapipe'] = {
                'status': 'failed',
                'error': str(e),
                'total_time': time.time() - start_time
            }
            return False

    def run_movenet(self, model_type='thunder'):
        """Run MoveNet pose detection."""
        print("\n" + "="*60)
        print(f"RUNNING: MoveNet {model_type.capitalize()}")
        print("="*60)

        output_file = self.output_dir / f"{self.input_video.stem}_movenet_{model_type}.mp4"

        cmd = [
            sys.executable, "pose_movenet.py",
            str(self.input_video),
            "-o", str(output_file),
            "-m", model_type
        ]

        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            elapsed = time.time() - start_time

            stats = self._parse_output(result.stdout)
            stats['total_time'] = elapsed
            stats['status'] = 'success'
            stats['output_file'] = str(output_file)

            self.results[f'movenet_{model_type}'] = stats

            print(f"✓ MoveNet {model_type} completed in {elapsed:.1f}s")
            return True

        except subprocess.CalledProcessError as e:
            print(f"✗ MoveNet {model_type} failed: {e}")
            self.results[f'movenet_{model_type}'] = {
                'status': 'failed',
                'error': str(e),
                'total_time': time.time() - start_time
            }
            return False

    def run_openpose(self, model_dir, model_type='COCO'):
        """Run OpenPose detection."""
        print("\n" + "="*60)
        print(f"RUNNING: OpenPose {model_type}")
        print("="*60)

        if not Path(model_dir).exists():
            print(f"✗ OpenPose model directory not found: {model_dir}")
            self.results[f'openpose_{model_type.lower()}'] = {
                'status': 'skipped',
                'error': 'Model directory not found'
            }
            return False

        output_file = self.output_dir / f"{self.input_video.stem}_openpose_{model_type.lower()}.mp4"

        cmd = [
            sys.executable, "pose_openpose.py",
            str(self.input_video),
            "-m", model_dir,
            "-o", str(output_file),
            "-t", model_type
        ]

        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            elapsed = time.time() - start_time

            stats = self._parse_output(result.stdout)
            stats['total_time'] = elapsed
            stats['status'] = 'success'
            stats['output_file'] = str(output_file)

            self.results[f'openpose_{model_type.lower()}'] = stats

            print(f"✓ OpenPose {model_type} completed in {elapsed:.1f}s")
            return True

        except subprocess.CalledProcessError as e:
            print(f"✗ OpenPose {model_type} failed: {e}")
            self.results[f'openpose_{model_type.lower()}'] = {
                'status': 'failed',
                'error': str(e),
                'total_time': time.time() - start_time
            }
            return False

    def run_mmpose(self, model_name='rtmpose-m', device='cpu'):
        """Run MMPose detection."""
        print("\n" + "="*60)
        print(f"RUNNING: MMPose {model_name}")
        print("="*60)

        output_file = self.output_dir / f"{self.input_video.stem}_mmpose_{model_name}.mp4"

        cmd = [
            sys.executable, "pose_mmpose.py",
            str(self.input_video),
            "-o", str(output_file),
            "-m", model_name,
            "-d", device
        ]

        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            elapsed = time.time() - start_time

            stats = self._parse_output(result.stdout)
            stats['total_time'] = elapsed
            stats['status'] = 'success'
            stats['output_file'] = str(output_file)

            self.results[f'mmpose_{model_name}'] = stats

            print(f"✓ MMPose {model_name} completed in {elapsed:.1f}s")
            return True

        except subprocess.CalledProcessError as e:
            print(f"✗ MMPose {model_name} failed: {e}")
            self.results[f'mmpose_{model_name}'] = {
                'status': 'failed',
                'error': str(e),
                'total_time': time.time() - start_time
            }
            return False

    def run_yolo(self, model='yolo11l-pose.pt'):
        """Run YOLO Pose detection."""
        print("\n" + "="*60)
        print("RUNNING: YOLO Pose")
        print("="*60)

        if not Path(model).exists():
            print(f"✗ YOLO model file not found: {model}")
            self.results['yolo_pose'] = {
                'status': 'skipped',
                'error': 'Model file not found'
            }
            return False

        output_file = self.output_dir / f"{self.input_video.stem}_yolo.mp4"

        cmd = [
            sys.executable, "clipper_yolo_pose.py",
            str(self.input_video),
            "--output", str(output_file)
        ]

        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            elapsed = time.time() - start_time

            stats = self._parse_output(result.stdout)
            stats['total_time'] = elapsed
            stats['status'] = 'success'
            stats['output_file'] = str(output_file)

            self.results['yolo_pose'] = stats

            print(f"✓ YOLO Pose completed in {elapsed:.1f}s")
            return True

        except subprocess.CalledProcessError as e:
            print(f"✗ YOLO Pose failed: {e}")
            self.results['yolo_pose'] = {
                'status': 'failed',
                'error': str(e),
                'total_time': time.time() - start_time
            }
            return False

    def _parse_output(self, output):
        """Parse statistics from script output."""
        stats = {}

        lines = output.split('\n')
        for line in lines:
            if 'Total frames processed:' in line:
                stats['total_frames'] = int(line.split(':')[1].strip())
            elif 'Frames with pose detected:' in line or 'detected:' in line:
                stats['detected_frames'] = int(line.split(':')[1].strip())
            elif 'Detection rate:' in line:
                stats['detection_rate'] = float(line.split(':')[1].strip().replace('%', ''))
            elif 'Average processing time per frame:' in line:
                time_str = line.split(':')[1].strip().replace('ms', '')
                stats['avg_time_per_frame_ms'] = float(time_str)
            elif 'Average FPS:' in line:
                stats['avg_fps'] = float(line.split(':')[1].strip())

        return stats

    def generate_report(self):
        """Generate comparison report."""
        report_file = self.output_dir / "comparison_report.txt"

        with open(report_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("POSE DETECTION MODEL COMPARISON REPORT\n")
            f.write("="*70 + "\n\n")
            f.write(f"Input Video: {self.input_video}\n")
            f.write(f"Output Directory: {self.output_dir}\n\n")

            # Summary table
            f.write("-"*70 + "\n")
            f.write(f"{'Model':<25} {'Status':<10} {'Det.Rate':<10} {'Avg FPS':<10} {'Time':<10}\n")
            f.write("-"*70 + "\n")

            for model_name, stats in sorted(self.results.items()):
                status = stats.get('status', 'unknown')
                det_rate = stats.get('detection_rate', 0)
                avg_fps = stats.get('avg_fps', 0)
                total_time = stats.get('total_time', 0)

                f.write(f"{model_name:<25} {status:<10} {det_rate:>6.1f}%   "
                       f"{avg_fps:>6.1f}     {total_time:>6.1f}s\n")

            f.write("-"*70 + "\n\n")

            # Detailed results
            f.write("\nDETAILED RESULTS:\n")
            f.write("="*70 + "\n\n")

            for model_name, stats in sorted(self.results.items()):
                f.write(f"\n{model_name.upper()}\n")
                f.write("-"*40 + "\n")
                for key, value in stats.items():
                    f.write(f"  {key}: {value}\n")

        # Also save JSON
        json_file = self.output_dir / "comparison_report.json"
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\n✓ Report saved to: {report_file}")
        print(f"✓ JSON data saved to: {json_file}")

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print summary to console."""
        print("\n" + "="*70)
        print("COMPARISON SUMMARY")
        print("="*70)
        print(f"{'Model':<25} {'Status':<10} {'Det.Rate':<10} {'Avg FPS':<10} {'Time':<10}")
        print("-"*70)

        for model_name, stats in sorted(self.results.items()):
            status = stats.get('status', 'unknown')
            det_rate = stats.get('detection_rate', 0)
            avg_fps = stats.get('avg_fps', 0)
            total_time = stats.get('total_time', 0)

            print(f"{model_name:<25} {status:<10} {det_rate:>6.1f}%   "
                  f"{avg_fps:>6.1f}     {total_time:>6.1f}s")

        print("="*70)


def main():
    parser = argparse.ArgumentParser(description='Compare Multiple Pose Detection Models')
    parser.add_argument('input', help='Input video file path')
    parser.add_argument('-o', '--output-dir', default='pose_comparison',
                       help='Output directory for results (default: pose_comparison)')
    parser.add_argument('--models', nargs='+',
                       choices=['mediapipe', 'movenet-lightning', 'movenet-thunder',
                               'openpose-coco', 'openpose-mpi', 'mmpose-rtmpose-m',
                               'mmpose-rtmpose-l', 'mmpose-hrnet-w32', 'mmpose-hrnet-w48',
                               'yolo'],
                       help='Specific models to run (default: all available)')
    parser.add_argument('--openpose-dir', help='Directory containing OpenPose models')
    parser.add_argument('--yolo-model', default='yolo11l-pose.pt',
                       help='Path to YOLO pose model')
    parser.add_argument('--device', default='cpu', help='Device for models (cpu/cuda)')

    args = parser.parse_args()

    # Create comparison runner
    comparison = PoseModelComparison(args.input, args.output_dir)

    # Determine which models to run
    if args.models:
        models_to_run = args.models
    else:
        # Run all available models
        models_to_run = ['mediapipe', 'movenet-lightning', 'movenet-thunder', 'yolo']

    # Run each model
    for model in models_to_run:
        if model == 'mediapipe':
            comparison.run_mediapipe()
        elif model == 'movenet-lightning':
            comparison.run_movenet('lightning')
        elif model == 'movenet-thunder':
            comparison.run_movenet('thunder')
        elif model == 'openpose-coco':
            if args.openpose_dir:
                comparison.run_openpose(args.openpose_dir, 'COCO')
            else:
                print("⚠ Skipping OpenPose (no model directory specified)")
        elif model == 'openpose-mpi':
            if args.openpose_dir:
                comparison.run_openpose(args.openpose_dir, 'MPI')
            else:
                print("⚠ Skipping OpenPose (no model directory specified)")
        elif model.startswith('mmpose-'):
            mmpose_model = model.replace('mmpose-', '')
            comparison.run_mmpose(mmpose_model, args.device)
        elif model == 'yolo':
            comparison.run_yolo(args.yolo_model)

    # Generate final report
    comparison.generate_report()

    print("\n✓ All comparisons complete!")


if __name__ == "__main__":
    main()
