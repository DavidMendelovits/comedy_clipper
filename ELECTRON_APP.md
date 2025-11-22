# Comedy Clipper - Electron Desktop App

A beautiful desktop application for automatically clipping comedy videos using AI detection.

## Features

- **Drag & Drop Interface** - Simply drag a video file into the app to start
- **Multiple Detection Methods**:
  - Configurable (Multi-Modal) - Face + pose detection with YAML rules
  - Speaker Detection - Voice-based identification
  - Pose Detection - Person entry/exit detection
  - Scene Detection - Camera cut detection
- **Real-Time Progress** - Watch the processing in real-time with console output
- **Output Viewer** - Preview clips with built-in video player
- **Debug Frames** - View detection overlays when debug mode is enabled
- **Clean, Modern UI** - Dark theme with smooth animations

## Setup

### Prerequisites

- Node.js 18+ and npm
- Python 3.8-3.12 (for MediaPipe compatibility)
- FFmpeg installed and in PATH

### Installation

1. Install Node.js dependencies:
```bash
npm install
```

2. Install Python dependencies (if not already installed):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements_advanced.txt
```

## Development

Run the app in development mode:

```bash
npm run electron:dev
```

This will:
1. Start the Vite dev server
2. Launch Electron with hot-reload enabled
3. Open DevTools for debugging

## Building

Build the app for production:

```bash
npm run electron:build
```

This will create distributable packages in the `dist` folder:
- **macOS**: `.dmg` and `.zip` files
- **Windows**: `.exe` installer and portable `.exe`
- **Linux**: `.AppImage` and `.deb` packages

## Usage

### Basic Workflow

1. **Drop a Video**: Drag and drop a comedy video file (MP4, MOV, AVI, MKV, WEBM)
2. **Configure Settings**: Click the Settings button to adjust:
   - Detection method
   - Minimum clip duration
   - Debug mode
   - Config file (for configurable clipper)
3. **Start Clipping**: Click "Start Clipping" to begin processing
4. **Monitor Progress**: Watch real-time console output and progress bar
5. **View Results**: Browse clips in the output viewer, play them back

### Detection Methods

#### Configurable (Recommended)
Uses MediaPipe for face and pose detection with configurable YAML rules. Best for:
- Static camera shows
- Host + comedian format
- Good lighting conditions

**Settings:**
- Enable debug mode to see detection frames
- Edit `clipper_rules.yaml` for custom rules

#### Speaker Detection
Identifies comedians by voice characteristics. Best for:
- Static camera shows
- Good audio quality
- Multiple comedians

**Settings:**
- Min duration: 180s (3 min) for full sets, 60s for shorter clips

#### Pose Detection
Uses YOLO to detect person entry/exit. Best for:
- Clear stage entry/exit
- Gaps between comedians

#### Scene Detection
Uses FFmpeg scene detection. Best for:
- Multi-camera shows
- Visible camera cuts

### Tips

- **Enable Debug Mode**: See exactly what the AI detects with visual overlays
- **Adjust Min Duration**: Filter out announcements and short segments
- **Check Output Directory**: Clips are saved to the same directory as the input video by default
- **Review Debug Frames**: Use the Debug tab to verify detection accuracy

## Architecture

### Main Process (`electron/main.ts`)
- Handles Python subprocess execution
- Manages IPC communication
- Parses clipper output for clips and progress

### Renderer Process (`src/`)
- React + TypeScript UI
- Tailwind CSS for styling
- Real-time updates via IPC

### Components
- **DropZone**: Drag-and-drop file input
- **ProgressPanel**: Real-time processing display
- **OutputViewer**: Clip and debug frame viewer
- **SettingsPanel**: Configuration interface

## Configuration Files

### `clipper_rules.yaml`
Defines detection rules for the configurable clipper:
```yaml
transition_detection:
  enabled: true
  rules:
    - from: 0
      to: 1
      action: start_segment
    - from: 1
      to: 0
      action: end_segment
```

See `RULES_GUIDE.md` for full configuration options.

## Troubleshooting

### Python Not Found
Make sure Python 3.8-3.12 is installed and in your PATH:
```bash
python3 --version
```

### FFmpeg Not Found
Install FFmpeg:
- **macOS**: `brew install ffmpeg`
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
- **Linux**: `sudo apt install ffmpeg`

### MediaPipe Errors
MediaPipe requires Python 3.8-3.12 (not 3.13+):
```bash
python3 --version  # Check version
pyenv install 3.11.10  # Install compatible version if needed
```

### No Output
- Check console output for errors
- Verify video file is valid
- Try lowering minimum duration
- Enable debug mode to see detection

## Development Notes

### Hot Reload
The app uses Vite for fast hot-reload during development. Changes to:
- React components: Auto-reload
- Main process: Auto-restart
- Preload scripts: Auto-reload

### Building for Distribution
The build process:
1. Compiles TypeScript
2. Bundles React app with Vite
3. Packages Electron app with electron-builder
4. Includes Python scripts and models

### File Structure
```
comedy-clipper/
├── electron/           # Main process
│   ├── main.ts        # Electron main
│   └── preload.ts     # Preload script
├── src/               # Renderer process
│   ├── components/    # React components
│   ├── types/         # TypeScript types
│   ├── App.tsx        # Main app
│   └── main.tsx       # Entry point
├── *.py               # Python clippers
├── *.yaml             # Config files
└── package.json       # Dependencies
```

## Contributing

To add new features:
1. Add IPC handlers in `electron/main.ts`
2. Update types in `src/types/electron.d.ts`
3. Create/update React components in `src/components/`
4. Update UI in `src/App.tsx`

## License

MIT
