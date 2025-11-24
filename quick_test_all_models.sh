#!/bin/bash
# Quick test script to run a short video through all available pose detection models

set -e

# Configuration
INPUT_VIDEO="${1:-}"
OUTPUT_DIR="pose_test_output"

if [ -z "$INPUT_VIDEO" ]; then
    echo "Usage: $0 <input_video.mp4>"
    echo ""
    echo "This script will:"
    echo "  1. Test all available pose detection models"
    echo "  2. Generate overlay videos for each"
    echo "  3. Display performance statistics"
    exit 1
fi

if [ ! -f "$INPUT_VIDEO" ]; then
    echo "Error: Video file not found: $INPUT_VIDEO"
    exit 1
fi

echo "=========================================="
echo "Pose Detection Model Testing"
echo "=========================================="
echo "Input video: $INPUT_VIDEO"
echo "Output directory: $OUTPUT_DIR"
echo ""

mkdir -p "$OUTPUT_DIR"

# Test MediaPipe
echo "----------------------------------------"
echo "Testing MediaPipe Pose..."
echo "----------------------------------------"
if python pose_mediapipe.py "$INPUT_VIDEO" -o "$OUTPUT_DIR/mediapipe.mp4" 2>&1; then
    echo "✓ MediaPipe completed"
else
    echo "✗ MediaPipe failed or not available"
fi
echo ""

# Test MoveNet Lightning
echo "----------------------------------------"
echo "Testing MoveNet Lightning..."
echo "----------------------------------------"
if python pose_movenet.py "$INPUT_VIDEO" -m lightning -o "$OUTPUT_DIR/movenet_lightning.mp4" 2>&1; then
    echo "✓ MoveNet Lightning completed"
else
    echo "✗ MoveNet Lightning failed or not available"
fi
echo ""

# Test MoveNet Thunder
echo "----------------------------------------"
echo "Testing MoveNet Thunder..."
echo "----------------------------------------"
if python pose_movenet.py "$INPUT_VIDEO" -m thunder -o "$OUTPUT_DIR/movenet_thunder.mp4" 2>&1; then
    echo "✓ MoveNet Thunder completed"
else
    echo "✗ MoveNet Thunder failed or not available"
fi
echo ""

# Test YOLO (if model exists)
if [ -f "yolo11l-pose.pt" ]; then
    echo "----------------------------------------"
    echo "Testing YOLO Pose..."
    echo "----------------------------------------"
    if python clipper_yolo_pose.py "$INPUT_VIDEO" --output "$OUTPUT_DIR/yolo.mp4" --overlay 2>&1; then
        echo "✓ YOLO Pose completed"
    else
        echo "✗ YOLO Pose failed"
    fi
    echo ""
fi

# Test OpenPose (if models exist)
if [ -d "openpose_models" ]; then
    echo "----------------------------------------"
    echo "Testing OpenPose COCO..."
    echo "----------------------------------------"
    if python pose_openpose.py "$INPUT_VIDEO" -m openpose_models -t COCO -o "$OUTPUT_DIR/openpose_coco.mp4" 2>&1; then
        echo "✓ OpenPose COCO completed"
    else
        echo "✗ OpenPose COCO failed"
    fi
    echo ""
fi

# Test MMPose (if installed)
echo "----------------------------------------"
echo "Testing MMPose RTMPose-M..."
echo "----------------------------------------"
if python pose_mmpose.py "$INPUT_VIDEO" -m rtmpose-m -o "$OUTPUT_DIR/mmpose_rtmpose-m.mp4" 2>&1; then
    echo "✓ MMPose RTMPose-M completed"
else
    echo "✗ MMPose RTMPose-M failed or not available"
fi
echo ""

echo "=========================================="
echo "Testing Complete!"
echo "=========================================="
echo ""
echo "Output videos saved to: $OUTPUT_DIR/"
echo ""
echo "Output files:"
ls -lh "$OUTPUT_DIR/"
echo ""
echo "To view videos, open the output directory:"
echo "  open $OUTPUT_DIR/"
echo ""
