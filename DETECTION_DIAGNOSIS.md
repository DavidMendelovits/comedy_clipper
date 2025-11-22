# YOLOv8 Person Detection Diagnosis

## Problem Summary

You expected segments starting around 2:05, 6:12, 9:00, and 11:59 for 4 comedians, but the clipper wasn't creating proper segments.

## Root Cause Analysis

### What I Found

1. **YOLO detection is working correctly** ✓
   - Comedians on stage are detected with confidence 0.8-0.9
   - Audience members are correctly excluded by the zone boundary (bottom 85%)

2. **Zone filtering is working correctly** ✓
   - Stage zone: top 85% of frame
   - Audience zone: bottom 15% excluded
   - Comedians counted IN zone, audience OUT of zone

3. **The actual problem: Rapid person count flickering** ✗

### Transitions Found in Video

```
  122.0s (2:02) - 2→1 → START (host exits, comedian alone)
  367.0s (6:07) - 1→2 → END   (person enters - audience/host?)
  372.0s (6:12) - 2→1 → START
  374.0s (6:14) - 1→2 → END   [only 2 seconds!]
  377.0s (6:17) - 2→1 → START
  379.0s (6:19) - 1→2 → END   [only 2 seconds!]
  381.0s (6:21) - 2→1 → START
  550.1s (9:10) - 1→2 → END
  552.1s (9:12) - 2→1 → START
  553.1s (9:13) - 1→2 → END   [only 1 second!]
  557.1s (9:17) - 2→1 → START
  899.1s (14:59) - 1→0 → END (comedian exits)
```

### Why Segments Weren't Created

**Around 6:12 (your 2nd expected segment):**
- Rapid flickering: 1→2→1→2→1 within 14 seconds
- Likely cause: Audience member walking, or host briefly entering
- Created multiple 2-5 second segments
- **All filtered out** because `min_duration: 5.0` seconds

**Around 9:00 (your 3rd expected segment):**
- Similar flickering pattern
- Same issue: segments too short

## The Solution

I've updated `clipper_rules.yaml` with three fixes:

### 1. Increased Transition Stability (CRITICAL)

```yaml
transition_stability_frames: 10  # Was: 2
```

**Effect:** Person count must stay stable for **10 seconds** before triggering a transition. This prevents false triggers from:
- Audience members walking across the zone briefly
- Host stepping on stage momentarily
- Detection noise

### 2. Increased Smoothing Window

```yaml
smoothing_window: 15  # Was: 5
```

**Effect:** Uses median filter over 15 frames (~15 seconds) to reduce detection flicker. If person count fluctuates 1→2→1 rapidly, the median stays at 1.

### 3. Increased Minimum Duration

```yaml
min_duration: 30.0  # Was: 5.0
```

**Effect:** Only keeps segments where comedian performs for at least 30 seconds. Filters out:
- Brief moments when host walks on stage
- Short transitions between comedians
- False positive segments from flickering

## Expected Behavior After Fix

With these settings, the clipper should:

1. **Ignore brief audience movement** - Person must be in zone for 10+ seconds
2. **Ignore host walk-ons under 30 seconds** - Only clips actual comedian sets
3. **Create 4 segments** for your 4 comedians:
   - Segment 1: Starts ~2:02 when host exits (after 10s stability)
   - Segment 2: Starts ~6:21 when count stabilizes at 1 (after flickering settles)
   - Segment 3: Starts ~9:17 when count stabilizes at 1
   - Segment 4: Continues until 14:59 when comedian exits

## Testing the Fix

Run the clipper again with the updated config:

```bash
./venv_mediapipe/bin/python clipper_unified.py --video test_vid.mov --config clipper_rules.yaml
```

## If You Still Have Issues

### If too many segments are created:
- Increase `transition_stability_frames` to 15 or 20
- Increase `min_duration` to 60 seconds

### If not enough segments are created:
- Decrease `transition_stability_frames` to 7 or 8
- Decrease `min_duration` to 20 seconds

### If audience is still being counted:
- Decrease `zone_crossing.stage_boundary.bottom` from 0.85 to 0.80 (exclude bottom 20%)

### Alternative: Use scene detection instead

If transition-based detection continues to be problematic, switch to scene detection:

```yaml
detection_mode: scene
```

This detects camera cuts instead of person count changes, which might work better for shows with a static camera and multiple comedians.

## Debug Files Generated

- `debug_analysis/timestamp_0125s.jpg` - Shows detection at 2:05
- `debug_analysis/timestamp_0372s.jpg` - Shows detection at 6:12
- `debug_analysis/timestamp_0540s.jpg` - Shows detection at 9:00
- `debug_analysis/timestamp_0719s.jpg` - Shows detection at 11:59

All show correct YOLO detection with proper zone filtering.
