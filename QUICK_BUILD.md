# Quick Build Guide

## TL;DR

```bash
# Setup once
./setup.sh

# Build for distribution
npm run build

# Find your installer
ls dist/
```

## Commands

### Development

```bash
npm run dev              # Start dev mode (uses local venv)
```

### Building

```bash
npm run build:python     # Create Python bundle (~5 min)
npm run build            # Full build: Python + Electron package
```

### Testing

```bash
npm run type-check       # Check TypeScript
```

## File Locations

### Development Mode
- Python: `./venv/bin/python3`
- Scripts: `./clipper_unified.py`
- Logs: `./logs/`

### Packaged App (macOS)
- Python: `Comedy Clipper.app/Contents/Resources/python-bundle/python-env/bin/python3`
- Scripts: `Comedy Clipper.app/Contents/Resources/python-bundle/`
- Logs: `~/Library/Application Support/Comedy Clipper/logs/`
- Database: `~/Library/Application Support/Comedy Clipper/comedy-clipper.db`

## Output Files

### macOS
- `dist/Comedy Clipper-1.0.0.dmg` (~800 MB)
- `dist/Comedy Clipper-1.0.0-mac.zip`

### Windows
- `dist/Comedy Clipper Setup 1.0.0.exe`
- `dist/Comedy Clipper 1.0.0.exe` (portable)

### Linux
- `dist/Comedy Clipper-1.0.0.AppImage`
- `dist/comedy-clipper-app_1.0.0_amd64.deb`

## Troubleshooting

### Build fails with Python error
```bash
rm -rf python-bundle venv
./setup.sh
npm run build:python
```

### TypeScript errors
```bash
npm run type-check
```

### Packaged app can't find Python
Check Console: Help → Toggle Developer Tools

Look for:
```
Using Python: /path/to/python
Python exists: true
```

## What Gets Bundled?

- ✅ Python 3.11 interpreter
- ✅ PyTorch 2.8.0
- ✅ MediaPipe 0.10.14
- ✅ OpenCV, YOLO, all ML libs
- ✅ All Python scripts
- ✅ YOLO model (6.5MB)
- ✅ Config files

Total: ~1.8GB (compresses to ~800MB)

## See Also

- [BUILD.md](BUILD.md) - Complete build documentation
- [PACKAGING.md](PACKAGING.md) - Packaging system details
- [README.md](README.md) - General documentation
