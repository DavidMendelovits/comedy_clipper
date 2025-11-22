# Settings Modal Enhancement - Visual Detection Zone Editor

## Overview

The settings modal has been completely redesigned to include a **live video preview with interactive stage boundary visualization**. Users can now see exactly what areas will be detected while adjusting settings.

---

## New Features

### 1. Two-Column Layout

**Before**: Small modal with just settings
**After**: Wide modal (max-w-7xl) with two panels:
- **Left Panel**: Live video preview with canvas overlay
- **Right Panel**: Settings form (scrollable)

### 2. Live Video Preview

Shows the selected video in real-time with:
- Auto-seeks to 5 seconds for a good preview frame
- Displays video resolution and duration
- Shows current frame while adjusting settings

### 3. Interactive Stage Boundary Visualization

When **Zone Crossing Detection** is enabled:

#### Visual Elements

1. **Semi-transparent Black Overlay** (50% opacity)
   - Covers excluded areas (top, bottom, left, right)
   - Shows what will be ignored during detection

2. **Green Dashed Rectangle** (#22c55e)
   - Marks the stage boundary
   - Updates in real-time as sliders move
   - 10px dash, 5px gap pattern

3. **Corner Markers**
   - L-shaped markers at all 4 corners
   - Make boundaries easier to see

4. **Labels**
   - "STAGE AREA" text inside boundary
   - Percentage labels at each edge
   - Shows exact boundary values

### 4. Real-Time Updates

As you adjust the boundary sliders:
- Canvas redraws immediately
- No lag or flicker
- Smooth visualization
- Percentages update in both the overlay and info panel

### 5. Video Information Panel

Bottom of video shows:
- **Resolution**: e.g., "1920 × 1080"
- **Duration**: e.g., "7:16"
- **Stage Boundary Active**: Shows current values
  - Left: 5%
  - Right: 95%
  - Top: 0%
  - Bottom: 85%

---

## How It Works

### Canvas Overlay Implementation

```typescript
// Video element loads first
<video ref={videoRef} src={videoUrl} onLoadedMetadata={...} />

// Canvas positioned absolutely over video
<canvas ref={canvasRef} className="absolute top-0 left-0" />

// useEffect watches for changes
useEffect(() => {
  // Redraw when:
  // - Video loads
  // - Stage boundary values change
  // - Zone crossing toggled
}, [videoLoaded, config.stageBoundary, config.zoneCrossingEnabled])
```

### Drawing Logic

1. **Set canvas size** to match video dimensions
2. **Clear previous drawing**
3. **Calculate pixel coordinates** from percentages
4. **Draw excluded areas** (semi-transparent black)
5. **Draw stage boundary** (green dashed rectangle)
6. **Draw corner markers**
7. **Add labels** with percentages

---

## User Benefits

### 1. Immediate Visual Feedback

- **See what you're excluding** in real-time
- **Understand detection zones** visually
- **No guessing** about where boundaries are

### 2. Better Configuration

- **Precise adjustments** with visual confirmation
- **Avoid mistakes** like excluding the performer
- **Optimize for your specific videos**

### 3. Educational

- **Learn how detection works** by seeing it
- **Understand YOLO zone** vs full frame
- **Visualize impact** of different settings

---

## Usage Example

### Typical Workflow

1. **Select video**
   → Settings modal opens automatically

2. **Enable Zone Crossing Detection**
   → Green boundary rectangle appears on video

3. **Adjust Bottom slider** (to exclude audience)
   → Watch dark overlay cover bottom 15%
   → Green rectangle shrinks from bottom

4. **Adjust Left/Right** (to focus on stage)
   → Rectangle narrows
   → Side areas get darker

5. **Check video info panel**
   → Verify boundary percentages
   → Confirm resolution looks right

6. **Click "Start Processing"**
   → Modal closes
   → Processing begins with your exact settings

---

## Technical Details

### Canvas Sizing

The canvas uses `objectFit: 'contain'` to match the video scaling:
```css
canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  pointer-events: none; /* Click-through to video */
}
```

### Performance

- **Efficient rendering**: Only redraws when values change
- **No animation loop**: Static canvas, updated on demand
- **Lightweight**: Simple 2D drawing operations

### Accessibility

- **High contrast**: Green (#22c55e) on black background
- **Clear labels**: Bold text with percentages
- **Visual hierarchy**: Important areas stand out

---

## Settings Preserved

All the original settings remain:
- Detection Mode
- Minimum Clip Duration
- Configuration File
- Debug Mode
- YOLO Detection
- Person Count Method
- Zone Crossing Detection
- Stage Boundary sliders

---

## Code Structure

### File: `src/components/SettingsModal.tsx`

**Key Sections:**

1. **Refs**
   ```typescript
   const videoRef = useRef<HTMLVideoElement>(null)
   const canvasRef = useRef<HTMLCanvasElement>(null)
   ```

2. **State**
   ```typescript
   const [videoLoaded, setVideoLoaded] = useState(false)
   ```

3. **Drawing Effect**
   ```typescript
   useEffect(() => {
     // Draw stage boundary
   }, [videoLoaded, config.stageBoundary, config.zoneCrossingEnabled])
   ```

4. **Layout**
   ```tsx
   <div className="flex-1 flex">
     <div className="w-1/2"> {/* Video */} </div>
     <div className="w-1/2"> {/* Settings */} </div>
   </div>
   ```

---

## Future Enhancements

### Possible Additions

1. **Interactive Dragging**
   - Drag boundary edges directly on video
   - Click and drag to resize rectangle
   - Easier than sliders for some users

2. **Polygon Mode**
   - Click to add points
   - Create custom stage shapes
   - For non-rectangular stages

3. **Detection Preview**
   - Run single-frame detection
   - Show YOLO bounding boxes
   - Preview face/pose landmarks

4. **Preset Boundaries**
   - Save common configurations
   - "Comedy Club", "Theater", "Outdoor"
   - One-click application

5. **Undo/Redo**
   - History of boundary changes
   - Quick rollback
   - Comparison mode

---

## Testing Checklist

- [x] Video loads in modal
- [x] Canvas overlay renders
- [x] Stage boundary draws correctly
- [x] Sliders update boundary in real-time
- [x] Percentages show on canvas
- [x] Video info panel updates
- [x] No performance issues
- [x] TypeScript types pass
- [x] Modal closes properly
- [x] Settings persist after closing

---

## Summary

The enhanced settings modal provides:
- ✅ **Visual feedback** for stage boundaries
- ✅ **Real-time updates** as settings change
- ✅ **Better user understanding** of detection zones
- ✅ **Improved configuration accuracy**
- ✅ **Professional, polished UI**

Users can now **see exactly what the detector will see** before processing begins!
