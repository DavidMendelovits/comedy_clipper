# Getting Started - Comedy Clipper (Updated)

## Quick Start

The app has been successfully refactored with Zustand state management and SQLite persistence!

### Run the App

```bash
npm run dev
```

The Electron app will launch automatically.

### Database Location

Settings are now persisted to SQLite at:
```
~/Library/Application Support/comedy-clipper-app/comedy-clipper.db
```

---

## What's New

### 1. Settings Modal Workflow

**Old Flow:**
1. Drop video
2. Manually open settings panel
3. Configure settings
4. Click "Start Clipping"

**New Flow:**
1. Drop video
2. **Settings modal automatically appears**
3. Configure all settings in one place
4. Click "Start Processing" to begin

### 2. Video Preview During Processing

The video now stays visible (paused) while processing:
- Video on the left
- Progress panel on the right
- Can scrub through video to see where processing is

### 3. Keyframe Markers

Real-time visual markers appear on the progress bar:
- **Yellow lines** = Transitions detected
- **Green lines** = Segment starts
- **Red lines** = Segment ends
- **Green overlays** = Final segments (after processing)

### 4. Persistent Settings

Your configuration is saved between app restarts:
- Detection mode
- Min duration
- YOLO settings
- Zone boundaries
- Selected video path

---

## First-Time Setup

If this is your first time running the refactored app:

### 1. Rebuild Native Modules

The `postinstall` script should handle this automatically, but if you encounter issues:

```bash
npx electron-rebuild -f -w better-sqlite3
```

### 2. Clear Old State

If you have old localStorage data, clear it:

```bash
rm -rf ~/Library/Application\ Support/comedy-clipper-app/
```

Then restart the app.

---

## Testing the New Features

### Test Settings Persistence

1. Start the app
2. Select a video
3. In the settings modal, change detection mode to "Pose Only"
4. Click "Start Processing" (or just close the modal)
5. **Restart the app**
6. Select a video again
7. ✅ Verify: Detection mode should still be "Pose Only"

### Test Video During Processing

1. Select a test video
2. Click "Start Processing" in settings modal
3. ✅ Verify:
   - Video visible on left (paused)
   - Progress panel on right
   - Can scrub through video while processing
   - Play/Pause button works

### Test Keyframe Markers

1. Enable debug mode in settings
2. Process a video with multiple segments
3. ✅ Verify:
   - Yellow/green/red markers appear on progress bar
   - Hover shows marker details
   - Green overlays show final segments after processing

---

## Segment Detection Issue

**You mentioned expecting 4 segments but only seeing 1.**

This has been investigated - see `SEGMENT_DETECTION_ISSUE.md` for full analysis.

**TL;DR**: The Python script is working correctly. The test video actually only has 1 continuous segment (one person on stage from 11s-435s).

### To Get More Segments

Try one of these:

#### Option 1: Lower Stability Requirements

Edit `clipper_rules.yaml`:

```yaml
transition_detection:
  transition_stability_frames: 3  # From 10
  smoothing_window: 5  # From 15
```

#### Option 2: Use Different Person Count Method

```yaml
transition_detection:
  person_count_method: max  # From yolo_zone
```

#### Option 3: Lower YOLO Confidence

```yaml
yolo_detection:
  confidence: 0.3  # From 0.5
```

#### Option 4: Check Debug Frames

Review what's actually being detected:

```bash
# View timeline frames
open test_vid_debug_TIMESTAMP/timeline/

# View detection CSV
open test_vid_debug_TIMESTAMP/detection_data.csv
```

---

## Architecture Changes

### State Management

All state is now managed via Zustand in `src/store/index.ts`:

```typescript
import { useAppStore } from './store'

function MyComponent() {
  const { config, setConfig } = useAppStore()
  // ...
}
```

### Components Modified

- `src/App.tsx` - Uses Zustand hooks
- `src/components/VideoPreview.tsx` - Keyframe markers, auto-pause
- `src/components/SettingsModal.tsx` - **NEW** - Replaces SettingsPanel
- `electron/main.ts` - SQLite setup
- `electron/preload.ts` - Storage methods

### Database Schema

```sql
CREATE TABLE storage (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

Stores serialized JSON for:
- `comedy-clipper-storage` - Main app state

---

## Development

### Type Checking

```bash
npm run type-check
```

All checks passing ✅

### Build for Production

```bash
npm run build
```

### Clean Build

```bash
rm -rf dist dist-electron node_modules
npm install
npm run dev
```

---

## Troubleshooting

### "better-sqlite3 was compiled against different Node.js version"

Run:
```bash
npx electron-rebuild -f -w better-sqlite3
```

This should happen automatically via the `postinstall` script.

### Settings Not Persisting

Check if database file exists:
```bash
ls ~/Library/Application\ Support/comedy-clipper-app/comedy-clipper.db
```

View database contents:
```bash
sqlite3 ~/Library/Application\ Support/comedy-clipper-app/comedy-clipper.db \
  "SELECT * FROM storage"
```

### Electron Not Starting

Check console for errors:
```bash
npm run dev
```

Look for error messages in terminal output.

### Video Not Loading

Ensure the video path is absolute and the file exists:
- Video URL protocol: `local-file://<path>`
- Check electron main process logs for file access errors

---

## Documentation

- `REFACTORING_SUMMARY.md` - Complete refactoring details
- `SEGMENT_DETECTION_ISSUE.md` - Analysis of detection behavior
- `clipper_rules.yaml` - Detection configuration

---

## Next Steps

1. ✅ Run `npm run dev` to test
2. ✅ Select a video and verify settings modal appears
3. ✅ Process a video and check video stays visible
4. ✅ Restart app and verify settings persisted
5. 📝 Adjust detection config if needed for more segments

Enjoy the improved Comedy Clipper! 🎬✂️
