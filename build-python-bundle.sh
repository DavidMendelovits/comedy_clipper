#!/bin/bash

# Build Python Bundle Script
# This script creates a standalone Python environment for distribution with the Electron app

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_DIR="$SCRIPT_DIR/python-bundle"
PLATFORM="${1:-$(uname -s)}"

echo "Building Python bundle for platform: $PLATFORM"
echo "Bundle directory: $BUNDLE_DIR"

# Clean previous bundle
if [ -d "$BUNDLE_DIR" ]; then
    echo "Removing previous bundle..."
    rm -rf "$BUNDLE_DIR"
fi

mkdir -p "$BUNDLE_DIR"

# Determine Python command - use python3 and verify version
PYTHON_CMD="python3"

# Verify Python version is compatible (3.8-3.12)
PYTHON_VERSION_FULL=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
MAJOR=$(echo $PYTHON_VERSION_FULL | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION_FULL | cut -d. -f2)

echo "Using Python $PYTHON_VERSION_FULL"

if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 13 ]; then
    echo "ERROR: Python $PYTHON_VERSION_FULL is not compatible with MediaPipe"
    echo "Please use Python 3.8-3.12"
    exit 1
fi

echo "Creating portable Python environment..."

case "$PLATFORM" in
    Darwin|darwin|macos)
        echo "Building for macOS..."

        # Use python-build-standalone for a truly portable Python
        # Alternative: Use existing venv but make it relocatable

        # For now, we'll create a relocatable venv
        $PYTHON_CMD -m venv "$BUNDLE_DIR/python-env"

        # Activate and install dependencies
        source "$BUNDLE_DIR/python-env/bin/activate"

        # Upgrade pip
        pip install --upgrade pip setuptools wheel --quiet

        # Install all requirements with specific torch version
        echo "Installing PyTorch..."
        pip install torch==2.8.0 torchaudio==2.8.0 torchvision --quiet

        echo "Installing dependencies..."
        [ -f "requirements_simple.txt" ] && pip install -r requirements_simple.txt --quiet
        [ -f "requirements_speaker.txt" ] && pip install -r requirements_speaker.txt --quiet
        [ -f "requirements.txt" ] && pip install -r requirements.txt --quiet
        [ -f "requirements_advanced.txt" ] && pip install -r requirements_advanced.txt --quiet
        [ -f "requirements_mediapipe.txt" ] && pip install -r requirements_mediapipe.txt --quiet

        # Install additional packages
        pip install moviepy pydub --quiet

        echo "Downloading YOLO model..."
        if [ ! -f "yolov8n.pt" ]; then
            python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
        fi

        deactivate

        # Make the venv relocatable by using relative paths
        # Update activation scripts to use relative paths
        echo "Making environment relocatable..."

        # Remove symlinks in bin directory (electron-builder doesn't handle them well)
        echo "Converting symlinks to copies..."
        cd "$BUNDLE_DIR/python-env/bin"
        for link in python python3*; do
            if [ -L "$link" ]; then
                target=$(readlink "$link")
                rm "$link"
                cp "$target" "$link" 2>/dev/null || true
            fi
        done
        cd "$SCRIPT_DIR"

        # Copy Python scripts
        echo "Copying Python scripts..."
        cp *.py "$BUNDLE_DIR/" 2>/dev/null || true
        cp *.yaml "$BUNDLE_DIR/" 2>/dev/null || true
        cp yolov8n.pt "$BUNDLE_DIR/" 2>/dev/null || true

        ;;

    Linux|linux)
        echo "Building for Linux..."

        # Similar process for Linux
        $PYTHON_CMD -m venv "$BUNDLE_DIR/python-env"
        source "$BUNDLE_DIR/python-env/bin/activate"

        pip install --upgrade pip setuptools wheel --quiet
        pip install torch==2.8.0 torchaudio==2.8.0 torchvision --quiet

        [ -f "requirements_simple.txt" ] && pip install -r requirements_simple.txt --quiet
        [ -f "requirements_speaker.txt" ] && pip install -r requirements_speaker.txt --quiet
        [ -f "requirements.txt" ] && pip install -r requirements.txt --quiet
        [ -f "requirements_advanced.txt" ] && pip install -r requirements_advanced.txt --quiet
        [ -f "requirements_mediapipe.txt" ] && pip install -r requirements_mediapipe.txt --quiet

        pip install moviepy pydub --quiet

        if [ ! -f "yolov8n.pt" ]; then
            python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
        fi

        deactivate

        cp *.py "$BUNDLE_DIR/" 2>/dev/null || true
        cp *.yaml "$BUNDLE_DIR/" 2>/dev/null || true
        cp yolov8n.pt "$BUNDLE_DIR/" 2>/dev/null || true

        ;;

    MINGW*|msys*|Windows|windows)
        echo "Building for Windows..."

        # Windows uses Scripts instead of bin
        $PYTHON_CMD -m venv "$BUNDLE_DIR/python-env"

        # Activate (Windows style)
        source "$BUNDLE_DIR/python-env/Scripts/activate"

        pip install --upgrade pip setuptools wheel --quiet
        pip install torch==2.8.0 torchaudio==2.8.0 torchvision --quiet

        [ -f "requirements_simple.txt" ] && pip install -r requirements_simple.txt --quiet
        [ -f "requirements_speaker.txt" ] && pip install -r requirements_speaker.txt --quiet
        [ -f "requirements.txt" ] && pip install -r requirements.txt --quiet
        [ -f "requirements_advanced.txt" ] && pip install -r requirements_advanced.txt --quiet
        # Skip MediaPipe on Windows if it fails
        [ -f "requirements_mediapipe.txt" ] && pip install -r requirements_mediapipe.txt --quiet || echo "MediaPipe install failed, continuing..."

        pip install moviepy pydub --quiet

        if [ ! -f "yolov8n.pt" ]; then
            python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
        fi

        deactivate

        cp *.py "$BUNDLE_DIR/" 2>/dev/null || true
        cp *.yaml "$BUNDLE_DIR/" 2>/dev/null || true
        cp yolov8n.pt "$BUNDLE_DIR/" 2>/dev/null || true

        ;;

    *)
        echo "Unknown platform: $PLATFORM"
        exit 1
        ;;
esac

# Create bundle info file
echo "Creating bundle info..."
cat > "$BUNDLE_DIR/bundle-info.json" <<EOF
{
  "platform": "$PLATFORM",
  "python_version": "$PYTHON_VERSION_FULL",
  "build_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "architecture": "$(uname -m)"
}
EOF

echo ""
echo "✅ Python bundle created successfully!"
echo "Bundle location: $BUNDLE_DIR"
echo "Bundle size: $(du -sh "$BUNDLE_DIR" | awk '{print $1}')"
echo ""
echo "Next step: Run 'npm run build' to package the Electron app with Python"
