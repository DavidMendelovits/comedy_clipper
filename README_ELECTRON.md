# 🎬 Comedy Clipper Desktop App

A beautiful, modern Electron desktop app for automatically clipping comedy videos using AI-powered detection.

![Electron + React + TypeScript](https://img.shields.io/badge/Electron-React-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-5.3-blue)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.3-blue)

## ✨ Features

### 🎯 Drag & Drop Interface
- Simply drag a video file into the app
- Supports MP4, MOV, AVI, MKV, WEBM
- Instant file recognition

### 🤖 Multiple AI Detection Methods
- **Configurable (Multi-Modal)** - Face + pose detection with YAML rules
- **Speaker Detection** - Voice-based identification
- **Pose Detection** - Person entry/exit tracking
- **Scene Detection** - Camera cut detection

### 📊 Real-Time Progress Tracking
- Live console output
- Frame-by-frame progress
- Percentage completion
- Process monitoring

### 🎥 Built-In Output Viewer
- Video player for clips
- Thumbnail gallery
- Debug frame viewer
- Side-by-side comparison

### ⚙️ Configurable Settings
- Adjust detection parameters
- Set minimum clip duration
- Enable debug mode
- Select output directory

### 🎨 Modern, Clean UI
- Dark theme
- Smooth animations
- Responsive design
- Intuitive navigation

## 🚀 Quick Start

### Run in Development Mode

```bash
npm run electron:dev
```

This will:
1. Start Vite dev server on http://localhost:5173
2. Launch Electron with hot-reload
3. Open DevTools automatically

### Build for Production

```bash
npm run electron:build
```

Outputs:
- **macOS**: `.dmg` and `.zip` in `dist/`
- **Windows**: `.exe` installer and portable
- **Linux**: `.AppImage` and `.deb`

## 📁 Project Structure

```
comedy-clipper/
├── electron/                    # Main process
│   ├── main.ts                 # Electron main (IPC, Python runner)
│   └── preload.ts              # Preload script (API exposure)
│
├── src/                         # Renderer process (UI)
│   ├── components/
│   │   ├── DropZone.tsx        # Drag & drop file input
│   │   ├── ProgressPanel.tsx   # Real-time progress display
│   │   ├── OutputViewer.tsx    # Clip viewer with video player
│   │   └── SettingsPanel.tsx   # Configuration interface
│   ├── types/
│   │   └── electron.d.ts       # TypeScript declarations
│   ├── App.tsx                 # Main application
│   ├── main.tsx                # Entry point
│   └── index.css               # Global styles (Tailwind)
│
├── *.py                         # Python clippers
├── *.yaml                       # Configuration files
├── package.json                 # Dependencies & scripts
├── vite.config.ts              # Vite configuration
├── tsconfig.json               # TypeScript config
└── tailwind.config.js          # Tailwind config
```

## 🎮 Usage Guide

### 1. Start the App
```bash
npm run electron:dev
```

### 2. Drop a Video
Drag and drop a comedy video into the app window

### 3. Configure Settings (Optional)
Click the Settings button to adjust:
- Detection method (Configurable recommended)
- Minimum clip duration (180s = 3 min)
- Debug mode (enable to see detection frames)
- Output directory

### 4. Start Clipping
Click "Start Clipping" button

### 5. Monitor Progress
Watch real-time console output and progress bar

### 6. View Results
- Browse clips in the output viewer
- Play clips with built-in video player
- View debug frames (if enabled)
- Open files in Finder/Explorer

## 🔧 Technical Details

### Stack
- **Electron 28** - Desktop app framework
- **React 18** - UI framework
- **TypeScript 5.3** - Type safety
- **Vite 5** - Fast build tool
- **Tailwind CSS 3.3** - Utility-first styling
- **Lucide React** - Icon library

### IPC Communication
The app uses Electron IPC for communication:
- `select-video` - File picker
- `run-clipper` - Start Python process
- `stop-clipper` - Kill Python process
- `clipper-output` - Stream stdout/stderr
- `clipper-progress` - Progress updates

### Python Integration
- Spawns Python subprocess
- Streams output in real-time
- Parses progress from stdout
- Handles errors gracefully
- Auto-kills on window close

## 🎨 UI Components

### DropZone
Drag-and-drop area with:
- Visual feedback on hover/drag
- File type indicators
- Browse button fallback
- Tips and hints

### ProgressPanel
Real-time monitoring with:
- Animated progress bar
- Frame counter
- Console output viewer
- Color-coded messages (stdout/stderr)
- Auto-scrolling

### OutputViewer
Dual-tab viewer:
- **Clips Tab**: Video thumbnails + player
- **Debug Tab**: Detection frame gallery
- File info (size, duration)
- Quick open in Finder

### SettingsPanel
Configuration interface:
- Detection method selector
- Duration slider
- Debug toggle
- Config file input
- Method descriptions

## 🎯 Detection Methods

### Configurable (⭐ Recommended)
- Face detection via MediaPipe
- 33-point pose estimation
- Kalman filtering for smooth tracking
- YAML-based transition rules
- Debug frame visualization

**Best for:**
- Static camera shows
- Host + comedian format
- Good lighting

### Speaker Detection
- Voice embedding analysis
- True speaker diarization
- Groups same comedian's segments

**Best for:**
- Good audio quality
- Multiple comedians
- Static camera

### Pose Detection
- YOLO person detection
- Entry/exit tracking
- Position interpolation

**Best for:**
- Clear stage entry/exit
- Gaps between comedians

### Scene Detection
- FFmpeg scene cuts
- Fast processing
- No AI required

**Best for:**
- Multi-camera shows
- Visible cuts

## 📝 Configuration

### Default Config (`clipper_rules.yaml`)
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

filtering:
  min_duration: 180.0
  merge_close_segments: true
```

See `RULES_GUIDE.md` for full options.

## 🐛 Troubleshooting

### App Won't Start
```bash
# Check Node.js version (18+)
node --version

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### Python Not Found
```bash
# Check Python version (3.8-3.12)
python3 --version

# Install in venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_advanced.txt
```

### Video Won't Process
- Verify FFmpeg is installed: `ffmpeg -version`
- Check video format is supported
- Enable debug mode to see errors
- Lower minimum duration

### Build Errors
```bash
# Type check
npm run type-check

# Clear build cache
rm -rf dist dist-electron

# Rebuild
npm run electron:build
```

## 🚀 Performance Tips

- **First Run**: Downloads ~500MB of AI models
- **Processing Speed**:
  - Configurable: 1-2x realtime
  - Speaker: 10-20x realtime (CPU), 2-5x (GPU)
  - Pose: 1-2x realtime
  - Scene: <1x realtime (fastest)
- **Debug Mode**: Slower due to frame saving

## 📦 Distribution

### macOS
```bash
npm run electron:build
# Creates .dmg and .zip in dist/
```

### Windows
```bash
npm run electron:build
# Creates .exe installer in dist/
```

### Linux
```bash
npm run electron:build
# Creates .AppImage and .deb in dist/
```

## 🎓 Development Notes

### Hot Reload
- React components: Instant
- Main process: Auto-restart
- Preload scripts: Auto-reload

### Debugging
- Renderer: Chrome DevTools (opens automatically)
- Main: VSCode debugger
- Console: `npm run electron:dev`

### Adding Features
1. Add IPC handler in `electron/main.ts`
2. Update types in `src/types/electron.d.ts`
3. Create/update React component
4. Update `App.tsx`

## 🌟 Future Enhancements

- [ ] Video timeline editor
- [ ] Clip trimming
- [ ] Batch processing
- [ ] Custom output formats
- [ ] Cloud storage integration
- [ ] AI model fine-tuning

## 📄 License

MIT

---

**Made with ❤️ using Electron, React, and Python**

🎬 Happy Clipping!
