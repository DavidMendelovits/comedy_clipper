#!/bin/bash
# Demo script for YOLO pose detection features

set -e

echo "=========================================="
echo "YOLO Pose Detection Features Demo"
echo "=========================================="
echo ""

# Check if video file is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <video_file>"
    echo ""
    echo "This demo will:"
    echo "  1. Show interactive overlay player"
    echo "  2. Run YOLO pose detection clipper with debug"
    echo "  3. Compare with MediaPipe pose detection"
    echo ""
    exit 1
fi

VIDEO="$1"

if [ ! -f "$VIDEO" ]; then
    echo "Error: Video file not found: $VIDEO"
    exit 1
fi

echo "Video file: $VIDEO"
echo ""

# Check dependencies
echo "Checking dependencies..."
python3 -c "from ultralytics import YOLO; import cv2; import yaml" 2>/dev/null || {
    echo "Error: Missing dependencies. Please run:"
    echo "  pip install -r requirements_yolo.txt"
    exit 1
}
echo "✓ All dependencies installed"
echo ""

# Demo 1: Interactive overlay player
echo "=========================================="
echo "Demo 1: Interactive Overlay Player"
echo "=========================================="
echo ""
echo "This will open an interactive video player with:"
echo "  - Real-time YOLO pose detection overlays"
echo "  - MediaPipe pose and face detection"
echo "  - Stage boundary visualization"
echo ""
echo "Controls:"
echo "  SPACE      - Play/Pause"
echo "  Y          - Toggle YOLO Pose"
echo "  P          - Toggle MediaPipe Pose"
echo "  F          - Toggle Face Detection"
echo "  B          - Toggle Stage Boundary"
echo "  +/-        - Adjust speed"
echo "  LEFT/RIGHT - Seek ±5 seconds"
echo "  Q          - Quit"
echo ""
read -p "Press Enter to start overlay player (or Ctrl+C to skip)..."

python3 video_overlay_player.py "$VIDEO" --detections yolo_pose mediapipe_pose mediapipe_face

echo ""
echo "✓ Demo 1 complete"
echo ""

# Demo 2: YOLO clipper with debug
echo "=========================================="
echo "Demo 2: YOLO Pose Clipper (with debug)"
echo "=========================================="
echo ""
echo "This will run the YOLO pose clipper with:"
echo "  - yolo11m-pose.pt (medium model for accuracy)"
echo "  - Debug visualization enabled"
echo "  - 30-second minimum clip duration"
echo ""
read -p "Press Enter to start clipper (or Ctrl+C to skip)..."

python3 clipper_yolo_pose.py "$VIDEO" \
    --model yolo11m-pose.pt \
    --min-duration 30 \
    -d

echo ""
echo "✓ Demo 2 complete"
echo ""
echo "Check the output folders for:"
echo "  - Video clips"
echo "  - Debug frames with pose overlays"
echo ""

# Demo 3: Comparison
echo "=========================================="
echo "Demo 3: Compare YOLO vs MediaPipe"
echo "=========================================="
echo ""
echo "Running MediaPipe pose detection for comparison..."

python3 clipper_unified.py "$VIDEO" \
    --mode mediapipe \
    --min-duration 30 \
    -d

echo ""
echo "✓ Demo 3 complete"
echo ""

# Summary
echo "=========================================="
echo "Demo Complete!"
echo "=========================================="
echo ""
echo "You now have:"
echo "  1. YOLO pose clips + debug frames"
echo "  2. MediaPipe pose clips + debug frames"
echo ""
echo "Compare the debug folders to see the difference!"
echo ""
echo "Next steps:"
echo "  - Review the clips"
echo "  - Check debug frames to see pose detection quality"
echo "  - Choose the best model/method for your use case"
echo ""
echo "Documentation:"
echo "  - YOLO_POSE_README.md - Full feature documentation"
echo "  - INSTALL_YOLO.md - Installation and troubleshooting"
echo ""
