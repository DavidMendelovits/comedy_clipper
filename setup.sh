#!/bin/bash

# Comedy Clipper Setup Script
# This script sets up both the Electron app and Python dependencies

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}!${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Main setup
print_header "Comedy Clipper Setup"

# Check system dependencies
print_step "Checking system dependencies..."

if ! command_exists node; then
    print_error "Node.js is not installed. Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi
print_success "Node.js $(node --version) found"

# Find a MediaPipe-compatible Python version (3.8-3.12)
PYTHON_CMD=""
PYENV_VERSION=""
if command_exists pyenv; then
    # Try to find a compatible version in pyenv
    for version in 3.12 3.11 3.10 3.9 3.8; do
        FOUND_VERSION=$(pyenv versions --bare | grep "^${version}" | head -1)
        if [ ! -z "$FOUND_VERSION" ]; then
            PYENV_VERSION="$FOUND_VERSION"
            # Set local pyenv version for this directory
            pyenv local "$PYENV_VERSION"
            PYTHON_CMD="python3"
            print_success "Using Python $PYENV_VERSION via pyenv"
            break
        fi
    done
fi

# Fallback to system Python if no pyenv version found
if [ -z "$PYTHON_CMD" ]; then
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3.8-3.12 from https://www.python.org/"
        print_error "Note: MediaPipe requires Python 3.8-3.12 (Python 3.13+ is not yet supported)"
        exit 1
    fi
    PYTHON_CMD="python3"
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    print_success "Python $PYTHON_VERSION found"

    # Check if it's compatible
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 13 ]; then
        print_error "Python $PYTHON_VERSION is not compatible with MediaPipe"
        print_error "Please install Python 3.8-3.12 or use pyenv to install a compatible version:"
        print_error "  pyenv install 3.11.10"
        exit 1
    fi
fi

if ! command_exists ffmpeg; then
    print_warning "FFmpeg is not installed. Some video processing features may not work."
    print_warning "Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)"
else
    print_success "FFmpeg found"
fi

# Setup Node.js dependencies
print_header "Setting up Electron App"

print_step "Installing Node.js dependencies..."
npm install
print_success "Node.js dependencies installed"

print_step "Rebuilding native modules for Electron..."
npm run postinstall
print_success "Native modules rebuilt"

# Setup Python environment
print_header "Setting up Python Environment"

print_step "Setting up all Python clippers..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_step "Creating Python virtual environment with $PYTHON_CMD..."
    $PYTHON_CMD -m venv venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists - removing to recreate with compatible Python..."
    rm -rf venv
    print_step "Creating Python virtual environment with $PYTHON_CMD..."
    $PYTHON_CMD -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_step "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_step "Upgrading pip..."
pip install --upgrade pip --quiet

# Install all requirements
print_step "Installing all Python dependencies (this may take a few minutes)..."

# Get Python version from the venv
PYTHON_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
print_step "Using Python version: $PYTHON_VERSION"

# Install PyTorch with version compatible with all packages
# Note: pyannote-audio requires torch==2.8.0 specifically
print_step "  Installing PyTorch (version 2.8.0)..."
pip install torch==2.8.0 torchaudio==2.8.0 torchvision --quiet 2>/dev/null || true

# Install in order to avoid conflicts
if [ -f "requirements_simple.txt" ]; then
    print_step "  Installing basic dependencies..."
    pip install -r requirements_simple.txt --quiet 2>/dev/null || true
fi

if [ -f "requirements_speaker.txt" ]; then
    print_step "  Installing speaker diarization dependencies..."
    pip install -r requirements_speaker.txt --quiet 2>/dev/null || true
fi

if [ -f "requirements.txt" ]; then
    print_step "  Installing core dependencies..."
    pip install -r requirements.txt --quiet 2>/dev/null || true
fi

# Install advanced features (YOLO, MediaPipe)
if [ -f "requirements_advanced.txt" ]; then
    print_step "  Installing advanced (YOLO) dependencies..."
    pip install -r requirements_advanced.txt --quiet 2>/dev/null || true
fi

if [ -f "requirements_mediapipe.txt" ]; then
    print_step "  Installing MediaPipe dependencies..."
    pip install -r requirements_mediapipe.txt --quiet 2>/dev/null || true
fi

# Install pose detection model dependencies
if [ -f "requirements_movenet.txt" ]; then
    print_step "  Installing MoveNet (TensorFlow) dependencies..."
    pip install -r requirements_movenet.txt --quiet 2>/dev/null || true
fi

if [ -f "requirements_mmpose.txt" ]; then
    print_step "  Installing MMPose dependencies..."
    pip install -r requirements_mmpose.txt --quiet 2>/dev/null || true
    # Install mmpose separately without dependencies to avoid chumpy build issues
    print_step "  Installing MMPose (without chumpy)..."
    pip install --no-deps mmpose --quiet 2>/dev/null || true
fi

if [ -f "requirements_openpose.txt" ]; then
    print_step "  Installing OpenPose dependencies..."
    pip install -r requirements_openpose.txt --quiet 2>/dev/null || true
fi

print_success "Python dependencies installed successfully"

# Download YOLO model if it doesn't exist
if [ ! -f "yolov8n.pt" ]; then
    print_step "Downloading YOLOv8 model (this may take a minute)..."
    python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')" 2>/dev/null
    print_success "YOLOv8 model downloaded"
else
    print_success "YOLOv8 model already exists"
fi

# Download OpenPose models if they don't exist
if [ ! -d "openpose_models" ]; then
    print_step "Downloading OpenPose models (this may take several minutes)..."
    if [ -f "download_openpose_models.sh" ]; then
        bash download_openpose_models.sh
        print_success "OpenPose models downloaded"
    else
        print_warning "download_openpose_models.sh not found - skipping OpenPose model download"
        print_warning "You can download them later by running: bash download_openpose_models.sh"
    fi
else
    print_success "OpenPose models already exist"
fi

deactivate

# Final instructions
print_header "Setup Complete!"

echo "All dependencies have been installed!"
echo ""
echo "Next steps:"
echo ""
echo "1. Start the Electron app:"
echo "   ${GREEN}npm run dev${NC}"
echo ""
echo "2. Or use Python clippers directly (activate venv first):"
echo "   ${GREEN}source venv/bin/activate${NC}"
echo ""
echo "   Available clippers:"
echo "   ${GREEN}python3 clipper_speaker.py your_video.mp4 -m 300${NC}  # Speaker diarization (recommended)"
echo "   ${GREEN}python3 clipper_pose.py your_video.mp4 -m 180${NC}     # Pose detection (YOLO)"
echo "   ${GREEN}python3 clipper_ffmpeg.py your_video.mp4${NC}          # FFmpeg-based (fastest)"
echo "   ${GREEN}python3 clipper_whisper.py your_video.mp4${NC}         # With transcripts"
echo "   ${GREEN}python3 clipper_mediapipe.py your_video.mp4${NC}       # MediaPipe pose tracking"
echo ""
echo "   Pose model comparison:"
echo "   ${GREEN}python3 compare_pose_models.py your_video.mp4${NC}     # Compare all pose models"
echo ""

echo "For more information, see:"
echo "  - ${BLUE}README.md${NC} - General documentation"
echo "  - ${BLUE}QUICKSTART.md${NC} - Quick start guide"
echo "  - ${BLUE}GETTING_STARTED.md${NC} - Detailed setup guide"
echo ""

print_success "All done! Happy clipping!"
