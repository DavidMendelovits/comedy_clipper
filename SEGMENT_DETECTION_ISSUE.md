# Segment Detection Analysis

## Issue Summary

**Expected**: 4 segments in test_vid.mov
**Actual**: 1 segment detected (1.0s - 435.2s)

## Root Cause Analysis

Based on the log file from `test_vid_2025-11-21T19-19-02-483Z.log`:

```
Analyzed 436 frames
  Frames with faces detected: 386/436 (88.5%)
  Frames with poses detected: 432/436 (99.1%)
  Frames with people detected: 434/436 (99.5%)

Analyzing transitions...
  Segment start at 11.0s: 0→1 people
Detected 1 segments from transitions
```

### The Problem

The Python script only detected **ONE transition**:
- At 11.0 seconds: person count changed from 0 to 1 (triggered "start_segment")
- No subsequent transitions were detected that would end this segment or start new ones

## Likely Causes

### 1. **Stable Person Count Throughout Video**

The detection shows:
- 99.5% of frames have people detected (434/436)
- 88.5% have faces (386/436)
- 99.1% have poses (432/436)

This suggests the person count remained **constant at 1 person** throughout most of the video.

### 2. **Configuration Settings Too Conservative**

From `clipper_rules.yaml`:

```yaml
transition_detection:
  transition_stability_frames: 10  # Needs 10s of stable count
  person_count_smoothing: true
  smoothing_window: 15  # 15-frame median filter
  min_duration: 30.0  # Segments must be >= 30 seconds
```

**Impact:**
- `transition_stability_frames: 10` means a person count change must persist for 10 seconds before triggering
- `smoothing_window: 15` applies median filtering across 15 frames, which can suppress real transitions
- If person count fluctuates (1 → 2 → 1 briefly), it may not meet the 10-second stability requirement

### 3. **Zone Crossing Configuration**

```yaml
zone_crossing:
  enabled: true
  stage_boundary:
    left: 0.05
    right: 0.95
    top: 0.0
    bottom: 0.85  # Excludes bottom 15% (audience)
```

**Impact:**
- If people briefly enter/exit the stage but stay within the defined boundary, no transition is detected
- Audience members in the bottom 15% are correctly ignored

### 4. **Transition Rules**

The rules that would trigger segments:

```yaml
rules:
  - from: 0, to: 1, action: start_segment  # ✅ TRIGGERED at 11.0s
  - from: 1, to: 0, action: end_segment    # ❌ NOT triggered
  - from: 2, to: 1, action: start_segment  # ❌ NOT triggered
  - from: 1, to: 2, action: end_segment    # ❌ NOT triggered
```

**Analysis:**
- Only the "0 → 1" transition was detected
- This means the video never had:
  - A person exit completely (1 → 0)
  - A second person enter (1 → 2)
  - A second person leave (2 → 1)

## What's Actually Happening

Based on the data, the test video appears to have:
1. **Empty stage** (0-11 seconds)
2. **ONE person on stage** (11s - 435s) continuously

The script is working **correctly** - it's detecting what's actually in the video!

## Why You Expected 4 Segments

Possible reasons:

### Option A: Multiple Comedians with Host
If the video has multiple comedians introduced by a host:
- Expected flow: Host enters (0→1), Comedian enters (1→2), Host exits (2→1), Comedian exits (1→0), repeat
- **Problem**: The person count may not be changing as expected
  - Host and comedian might be detected as "1 person" due to zone boundaries
  - Detection confidence issues (person flickers in/out of detection)

### Option B: Detection Not Finding People
- YOLO detector might not be detecting all people consistently
- Zone boundaries might be excluding performers
- Confidence thresholds might be too high

### Option C: Wrong Video or Debug Output
- The test_vid.mov being processed might not be the expected file
- Debug frames from previous runs might be showing different segments

## Solutions

### 1. **Review the Actual Video**
Open `test_vid.mov` and verify:
- Are there actually 4 distinct segments?
- How many people are on stage at different times?
- Do people enter and exit in ways that would trigger the rules?

### 2. **Check Debug Frames**
Look at the debug output to see what's being detected:
```
test_vid_debug_20251121_141948/
  - Timeline: 15 frames (every 30s)
  - Segments: 2 frames (segment boundaries)
  - detection_data.csv (full frame-by-frame data)
```

**To debug**:
```bash
# View the detection data CSV
open test_vid_debug_20251121_141948/detection_data.csv

# Check timeline frames to see person counts at different times
open test_vid_debug_20251121_141948/timeline/
```

### 3. **Adjust Configuration**

**Option A: Lower Stability Requirements**
```yaml
transition_detection:
  transition_stability_frames: 3  # From 10 → 3 seconds
  smoothing_window: 5  # From 15 → 5 frames
```

**Option B: Enable Position-Based Detection as Primary**
```yaml
position_detection:
  enabled: true
  exit_threshold: 0.15
```

**Option C: Add More Transition Rules**
```yaml
transition_detection:
  rules:
    # Add: Multiple people on stage
    - from: 1
      to: 2+
      action: start_segment
      description: "Second person enters"

    # Add: Return to solo
    - from: 2+
      to: 1
      action: end_segment
      description: "Return to solo performer"
```

### 4. **Run with Different Person Count Method**

Try different methods to see which detects changes better:
```yaml
person_count_method: max  # Instead of yolo_zone
```

Options:
- `yolo_zone` - Only counts people inside stage boundary (current)
- `yolo` - Counts all detected people
- `max` - Uses max(faces, poses)
- `hybrid` - Prefers YOLO, falls back to max

### 5. **Check YOLO Detection Settings**

```yaml
yolo_detection:
  confidence: 0.5  # Try lowering to 0.3
  max_disappeared_frames: 30  # Try increasing to 60
```

## Recommended Next Steps

1. **Verify video content**: Watch test_vid.mov and count actual segments
2. **Review debug frames**: Check `detection_data.csv` for person count over time
3. **Test with lower thresholds**: Try `transition_stability_frames: 3`
4. **Compare script vs Electron output**: Run script directly vs through Electron
5. **Add logging**: Check what person counts are being detected frame-by-frame

## Testing Command

Run the Python script directly to see full output:

```bash
python3 clipper_unified.py test_vid.mov \
  --mode multimodal \
  --json \
  -o /tmp/test_output \
  --min-duration 5 \
  -d \
  -c clipper_rules.yaml
```

This will show you exactly what transitions are being detected.

## Conclusion

The discrepancy is **NOT** between the Python script and Electron - they both show 1 segment.

The issue is either:
1. The video actually only has 1 segment (most likely)
2. The detection config is too conservative and missing transitions
3. YOLO/detection is not finding people when they appear

Check the debug frames and detection_data.csv to confirm what's being detected!
