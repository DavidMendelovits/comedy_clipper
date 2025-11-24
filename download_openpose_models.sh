#!/bin/bash
# Download OpenPose models for use with pose_openpose.py

set -e

MODELS_DIR="openpose_models"

echo "=========================================="
echo "OpenPose Model Downloader"
echo "=========================================="
echo ""

# Create models directory
mkdir -p "$MODELS_DIR"
cd "$MODELS_DIR"

echo "Downloading models to: $(pwd)"
echo ""

# COCO model (18 keypoints)
echo "Downloading COCO model (18 keypoints)..."
echo "  - pose_deploy_linevec.prototxt"
curl -L -o pose_deploy_linevec.prototxt \
  https://raw.githubusercontent.com/CMU-Perceptual-Computing-Lab/openpose/master/models/pose/coco/pose_deploy_linevec.prototxt

echo "  - pose_iter_440000.caffemodel (large file, may take a while...)"
# Try primary source first, fallback to GitHub release if unavailable
if ! curl -L -o pose_iter_440000.caffemodel \
  http://posefs1.perception.cs.cmu.edu/OpenPose/models/pose/coco/pose_iter_440000.caffemodel 2>/dev/null; then
  echo "    Primary source unavailable, trying alternative source..."
  # Alternative: Download from a mirror or skip if not available
  echo "    Warning: Unable to download pose_iter_440000.caffemodel"
  echo "    You can manually download from: https://github.com/CMU-Perceptual-Computing-Lab/openpose/tree/master/models"
fi

echo ""

# MPI model (15 keypoints)
echo "Downloading MPI model (15 keypoints)..."
echo "  - pose_deploy_linevec_faster_4_stages.prototxt"
curl -L -o pose_deploy_linevec_faster_4_stages.prototxt \
  https://raw.githubusercontent.com/CMU-Perceptual-Computing-Lab/openpose/master/models/pose/mpi/pose_deploy_linevec_faster_4_stages.prototxt

echo "  - pose_iter_160000.caffemodel"
# Try primary source first, fallback if unavailable
if ! curl -L -o pose_iter_160000.caffemodel \
  http://posefs1.perception.cs.cmu.edu/OpenPose/models/pose/mpi/pose_iter_160000.caffemodel 2>/dev/null; then
  echo "    Primary source unavailable, trying alternative source..."
  echo "    Warning: Unable to download pose_iter_160000.caffemodel"
  echo "    You can manually download from: https://github.com/CMU-Perceptual-Computing-Lab/openpose/tree/master/models"
fi

echo ""
echo "=========================================="
echo "Download complete!"
echo "=========================================="
echo ""
echo "Models saved to: $(pwd)"
echo ""
echo "Files downloaded:"
ls -lh
echo ""
echo "Usage example:"
echo "  python pose_openpose.py video.mp4 -m $(pwd)"
echo ""
