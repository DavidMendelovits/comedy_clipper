# Building Comedy Clipper

This guide explains how to build and package the Comedy Clipper app with bundled Python support.

## Overview

The Comedy Clipper app packages a complete Python environment with all dependencies, so users don't need to install Python separately. The build process creates platform-specific installers (DMG for macOS, NSIS for Windows, AppImage/deb for Linux) with everything included.

## Prerequisites

### All Platforms
- Node.js 18+
- Python 3.8-3.12 (3.13+ not supported due to MediaPipe)
- FFmpeg (for video processing)

### macOS
```bash
brew install node python@3.11 ffmpeg
```

### Linux (Ubuntu/Debian)
```bash
sudo apt install nodejs npm python3.11 python3.11-venv ffmpeg
```

### Windows
- Install Node.js from https://nodejs.org/
- Install Python 3.11 from https://www.python.org/
- Install FFmpeg from https://ffmpeg.org/

## Setup

1. **Install Node dependencies:**
   ```bash
   npm install
   ```

2. **Set up Python environment (for development):**
   ```bash
   ./setup.sh
   ```

   This creates a local `venv` with all Python dependencies for development and testing.

## Build Process

The build process has two main steps:

### 1. Build Python Bundle

This creates a standalone Python environment with all dependencies:

```bash
npm run build:python
```

This will:
- Create a `python-bundle` directory
- Set up a virtual environment with Python 3.11
- Install all required packages (PyTorch, MediaPipe, OpenCV, YOLO, etc.)
- Copy all Python scripts (clippers, config files, YOLO model)
- Create a bundle-info.json file

**Note:** This step can take 5-15 minutes depending on your internet speed and system.

### 2. Build Electron App

Build the complete application with the Python bundle:

```bash
npm run build
```

This will:
1. Run `build:python` (if not already done)
2. Compile TypeScript
3. Build React UI with Vite
4. Package everything with electron-builder

The final distributable will be in the `dist/` directory.

## Platform-Specific Builds

### macOS

Builds a DMG installer and ZIP archive:

```bash
npm run build
```

Output:
- `dist/Comedy Clipper-1.0.0.dmg` - Installer
- `dist/Comedy Clipper-1.0.0-mac.zip` - Portable app

**Code Signing (Optional):**
To sign the app for distribution:

```bash
export CSC_LINK=/path/to/certificate.p12
export CSC_KEY_PASSWORD=your_password
npm run build
```

### Windows

Cross-compilation from macOS/Linux requires wine:

```bash
brew install wine-stable  # macOS
# or
sudo apt install wine  # Linux

npm run build
```

Output:
- `dist/Comedy Clipper Setup 1.0.0.exe` - Installer
- `dist/Comedy Clipper 1.0.0.exe` - Portable

### Linux

```bash
npm run build
```

Output:
- `dist/Comedy Clipper-1.0.0.AppImage` - Universal Linux app
- `dist/comedy-clipper-app_1.0.0_amd64.deb` - Debian package

## Development

For development with hot-reload:

```bash
npm run dev
```

This starts the Vite dev server and uses the local `venv` for Python scripts.

## Bundle Structure

The packaged app has this structure:

```
Comedy Clipper.app/
├── Contents/
│   ├── MacOS/
│   │   └── Comedy Clipper          # Electron executable
│   ├── Resources/
│   │   ├── app.asar                # Electron code (UI, main process)
│   │   └── python-bundle/          # Python environment
│   │       ├── python-env/         # Virtual environment
│   │       │   ├── bin/python3     # Python interpreter
│   │       │   └── lib/            # All Python packages
│   │       ├── clipper_unified.py  # Main clipper script
│   │       ├── clipper_*.py        # Other clipper variants
│   │       ├── clipper_rules.yaml  # Default configuration
│   │       └── yolov8n.pt         # YOLO model
```

## Python Environment Details

The bundled Python environment includes:

**Core Dependencies:**
- Python 3.11
- PyTorch 2.8.0
- TorchAudio 2.8.0
- MediaPipe 0.10.14
- OpenCV 4.12+
- Ultralytics (YOLO)

**Clipper-Specific:**
- Resemblyzer (speaker embeddings)
- pyannote.audio (speaker diarization)
- Whisper (transcription)
- MoviePy (video editing)

**Size:**
- Python bundle: ~2-3 GB (compressed: ~800 MB)
- Total app size: ~1 GB (DMG/installer)

## Troubleshooting

### Python Bundle Failed

If the Python bundle build fails:

1. Check Python version: `python3 --version` (must be 3.8-3.12)
2. Clean and rebuild:
   ```bash
   rm -rf python-bundle venv
   npm run build:python
   ```

### Package Size Too Large

The Python environment is large due to ML dependencies. To reduce size:

1. Use PyTorch CPU-only (in `build-python-bundle.sh`):
   ```bash
   pip install torch==2.8.0+cpu torchaudio==2.8.0+cpu -f https://download.pytorch.org/whl/torch_stable.html
   ```

2. Remove unnecessary clippers (edit `build-python-bundle.sh`)

### Packaged App Can't Find Python

Check the console logs:
1. Open packaged app
2. Help → Toggle Developer Tools
3. Look for "Python path" and "Script path" logs

The app should find:
- Python: `Contents/Resources/python-bundle/python-env/bin/python3`
- Scripts: `Contents/Resources/python-bundle/clipper_unified.py`

## CI/CD

For automated builds, use GitHub Actions:

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    strategy:
      matrix:
        os: [macos-latest, ubuntu-latest, windows-latest]

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: 18

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: npm install

      - name: Build
        run: npm run build

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: ${{ matrix.os }}-build
          path: dist/
```

## Release Checklist

Before releasing a new version:

- [ ] Update version in `package.json`
- [ ] Test Python bundle creation on target platform
- [ ] Test packaged app with all clipper modes
- [ ] Verify Python dependencies are up to date
- [ ] Update CHANGELOG.md
- [ ] Create git tag: `git tag v1.0.0`
- [ ] Build for all platforms
- [ ] Test installers on clean machines
- [ ] Upload to release page

## Resources

- [electron-builder docs](https://www.electron.build/)
- [Python virtual environments](https://docs.python.org/3/library/venv.html)
- [Code signing guide](https://www.electron.build/code-signing)
