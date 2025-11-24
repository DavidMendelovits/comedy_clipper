# Comedy Clipper - Python Packaging System

## Overview

The Comedy Clipper uses a custom packaging system to bundle a complete Python environment with the Electron app. This allows users to run the app without installing Python or any dependencies.

## How It Works

### 1. Build-Time Python Bundle Creation

The `build-python-bundle.sh` script creates a standalone Python environment:

```bash
npm run build:python
```

**What it does:**
1. Creates a `python-bundle` directory
2. Sets up a Python 3.11 virtual environment
3. Installs all required packages (~2GB):
   - PyTorch 2.8.0 (ML framework)
   - MediaPipe 0.10.14 (pose detection)
   - OpenCV 4.12+ (computer vision)
   - Ultralytics YOLO (object detection)
   - Resemblyzer (speaker embeddings)
   - pyannote.audio (speaker diarization)
   - And ~50 more dependencies
4. Copies all Python scripts (clippers, config files)
5. Downloads the YOLOv8 model (6.5MB)

**Output Structure:**
```
python-bundle/
├── python-env/              # Virtual environment
│   ├── bin/python3          # Python interpreter
│   ├── lib/python3.11/      # All installed packages
│   └── pyvenv.cfg
├── clipper_unified.py       # Main clipper script
├── clipper_*.py             # Other clipper variants
├── clipper_rules.yaml       # Default configuration
├── yolov8n.pt              # YOLO model weights
└── bundle-info.json        # Bundle metadata
```

### 2. Electron Packaging with electron-builder

The `package.json` build configuration includes the Python bundle:

```json
{
  "build": {
    "extraResources": [
      {
        "from": "python-bundle",
        "to": "python-bundle"
      }
    ]
  }
}
```

This copies the entire `python-bundle` directory into the app's resources folder.

### 3. Runtime Python Detection

The `electron/main.ts` file detects and uses the bundled Python:

```typescript
const pythonSearchPaths = app.isPackaged ? [
  // Packaged app - look in resources
  path.join(resourcesPath, 'python-bundle', 'python-env', 'bin', 'python3'),
] : [
  // Development - look for local venv
  path.join(appPath, 'venv', 'bin', 'python3'),
]
```

**Runtime paths:**
- **Development:** Uses local `venv/bin/python3`
- **Packaged (macOS):** `Comedy Clipper.app/Contents/Resources/python-bundle/python-env/bin/python3`
- **Packaged (Windows):** `resources/python-bundle/python-env/Scripts/python.exe`
- **Packaged (Linux):** `resources/python-bundle/python-env/bin/python3`

## Platform Support

### macOS ✅
- **Python:** 3.11 (universal binary works on Intel + Apple Silicon)
- **Bundle size:** ~1.8GB (compressed to ~800MB in DMG)
- **Packaging:** DMG + ZIP
- **Tested:** ✅

### Windows ⚠️
- **Python:** 3.11 (cross-compile from macOS/Linux with wine)
- **Bundle size:** ~2.1GB
- **Packaging:** NSIS installer + portable EXE
- **Tested:** Needs testing on Windows

### Linux ✅
- **Python:** 3.11
- **Bundle size:** ~1.9GB
- **Packaging:** AppImage + deb
- **Tested:** Ubuntu/Debian

## Development vs Production

### Development Mode (`npm run dev`)

- Uses **local `venv`** created by `setup.sh`
- Python at: `./venv/bin/python3`
- Scripts at: `./clipper_unified.py`
- Hot-reload for UI changes
- Python changes require restart

### Production Mode (packaged app)

- Uses **bundled `python-bundle`**
- Python at: `app/Resources/python-bundle/python-env/bin/python3`
- Scripts at: `app/Resources/python-bundle/clipper_unified.py`
- Self-contained, no external dependencies
- User can't modify Python code

## File Access and Permissions

### Writable Locations

The app uses these directories for runtime data:

```typescript
// User data directory (writable)
const userDataPath = app.getPath('userData')

// Database
const dbPath = path.join(userDataPath, 'comedy-clipper.db')

// Temporary config
const tempConfigPath = path.join(userDataPath, 'temp_clipper_config.yaml')

// Logs
const logDir = path.join(appPath, 'logs')  // In dev
const logDir = path.join(userDataPath, 'logs')  // In packaged (recommended)
```

**macOS Paths:**
- Dev: `./logs/`
- Packaged: `~/Library/Application Support/Comedy Clipper/`

**Windows Paths:**
- Dev: `./logs/`
- Packaged: `%APPDATA%/Comedy Clipper/`

**Linux Paths:**
- Dev: `./logs/`
- Packaged: `~/.config/Comedy Clipper/`

### Read-Only Locations

These are bundled with the app (read-only):

- Python scripts: `resources/python-bundle/*.py`
- Config templates: `resources/python-bundle/clipper_rules.yaml`
- YOLO model: `resources/python-bundle/yolov8n.pt`

## Build Commands

### Full Build Process

```bash
# 1. Install Node dependencies
npm install

# 2. Setup local Python (for development)
./setup.sh

# 3. Build Python bundle (for packaging)
npm run build:python

# 4. Package Electron app
npm run build
```

### Individual Steps

```bash
# Just build Python bundle
npm run build:python

# Just compile TypeScript and React
tsc && vite build

# Just package with electron-builder (requires previous steps)
electron-builder
```

## Bundle Optimization

### Current Size: ~1.8GB

**What takes space:**
- PyTorch: ~800MB
- TorchAudio: ~150MB
- MediaPipe: ~100MB
- OpenCV: ~200MB
- Ultralytics: ~50MB
- Other packages: ~500MB

### Size Reduction Options

1. **Use CPU-only PyTorch** (saves ~200MB):
   ```bash
   pip install torch==2.8.0+cpu torchaudio==2.8.0+cpu
   ```

2. **Remove unused clippers** (saves ~50-100MB):
   ```bash
   # In build-python-bundle.sh, skip certain requirements
   # Skip whisper: comment out requirements_simple.txt
   # Skip pyannote: comment out requirements.txt
   ```

3. **Compress bundle** (already done by DMG/NSIS):
   - DMG: ~800MB (compressed from 1.8GB)
   - NSIS: ~900MB (compressed from 2.1GB)

### Can't Reduce:

- YOLO model: 6.5MB (required)
- MediaPipe: 100MB (required)
- Python interpreter: ~40MB (required)

## Troubleshooting

### Bundle Creation Fails

**Problem:** `build-python-bundle.sh` fails
**Check:**
1. Python version: `python3 --version` (must be 3.8-3.12)
2. Disk space: Need 5GB free
3. Internet: Downloads ~800MB of packages

**Fix:**
```bash
rm -rf python-bundle venv
./setup.sh
npm run build:python
```

### Packaged App Can't Find Python

**Problem:** App shows "Python not found" error
**Check Console Logs:**
1. Open app
2. Help → Toggle Developer Tools
3. Look for "Python path:" logs

**Expected Logs:**
```
App path: /Applications/Comedy Clipper.app/Contents/Resources/app.asar
Resources path: /Applications/Comedy Clipper.app/Contents/Resources
Is packaged: true
Checking Python paths: [
  '/Applications/Comedy Clipper.app/Contents/Resources/python-bundle/python-env/bin/python3',
  ...
]
Using Python: /Applications/Comedy Clipper.app/Contents/Resources/python-bundle/python-env/bin/python3
Python exists: true
```

**If Python doesn't exist:**
- Re-run `npm run build:python`
- Re-run `npm run build`

### Clipper Scripts Not Found

**Problem:** "Script not found" error
**Check:**
```bash
# After building
ls dist/mac/Comedy\ Clipper.app/Contents/Resources/python-bundle/

# Should see:
# clipper_unified.py
# clipper_rules.yaml
# yolov8n.pt
# etc.
```

**Fix:** Rebuild with `npm run build`

### Import Errors in Packaged App

**Problem:** Python import errors (e.g., "No module named 'torch'")
**Cause:** Virtual environment not activated or incomplete

**Fix:**
1. Delete bundle: `rm -rf python-bundle`
2. Rebuild: `npm run build:python`
3. Verify: `python-bundle/python-env/bin/python3 -c "import torch; print('OK')"`

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Release

on:
  push:
    tags: ['v*']

jobs:
  build-macos:
    runs-on: macos-latest
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

      - name: Build Python bundle
        run: npm run build:python

      - name: Build app
        run: npm run build

      - name: Upload DMG
        uses: actions/upload-artifact@v3
        with:
          name: macos-dmg
          path: dist/*.dmg
```

## Future Improvements

### Potential Enhancements

1. **Lazy Loading:**
   - Don't bundle all clippers
   - Download models on first use
   - Reduces initial download size

2. **Binary Compilation:**
   - Use PyInstaller/Nuitka to compile Python
   - Smaller bundle size
   - Faster startup

3. **Shared Dependencies:**
   - Detect system Python/PyTorch
   - Use if available, fall back to bundled
   - Better for advanced users

4. **Auto-Updates:**
   - Update Python bundle separately from app
   - Only download changed packages
   - Faster updates

## Resources

- [electron-builder extraResources](https://www.electron.build/configuration/contents#extraresources)
- [Python venv documentation](https://docs.python.org/3/library/venv.html)
- [PyTorch installation](https://pytorch.org/get-started/locally/)
- [MediaPipe installation](https://developers.google.com/mediapipe/solutions/guide)
