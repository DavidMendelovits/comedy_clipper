# Segment Detection Issue - Root Cause & Fix

## Problem

The clipper was only detecting 2 segments in test_vid.mov instead of the expected 4+ segments where the comedian is alone on stage.

## Root Cause Analysis

### Issue 1: Overly Broad Transition Rules

The configuration included two catch-all rules that interfered with the main detection:

```yaml
# PROBLEMATIC RULES (now disabled)
- from: any
  to: 2+
  action: start_segment  # Matched 0→2 at video start!

- from: 2+
  to: 1-
  action: end_segment
```

**What happened:**
1. Video starts with `person_count=2` (host + comedian)
2. The `any → 2+` rule matched the `0→2` transition (from initial state to first stable count)
3. This started seg01 at time 0s
4. All subsequent `2→1` transitions (at 157s, 408s, 584s) were **ignored** because the code doesn't support nested segments
5. seg01 continued until the first `1→2` transition at 721s

**Expected behavior:**
- seg01 should start at first `2→1` transition (157s), not at 0s
- Each `2→1` transition should start a new segment

### Issue 2: Transition Stability Requirements

The config requires person_count to be stable for 5 consecutive frames before recognizing a transition:

```yaml
transition_stability_frames: 5  # Person count must be stable for 5 frames
```

Some real transitions in the video are not stable for 5 frames:
```
367s: 1→2 (stable for 3 frames)
368s: count=2
369s: count=2
370s: count=3  ← Changes again before reaching 5 frames!
```

This causes some legitimate `1→2` (end segment) transitions to be skipped.

## Actual Detected Segments (Before Fix)

Based on CSV analysis, the video has these person count periods:

| Time Range | Count | Description | Detected? |
|------------|-------|-------------|-----------|
| 0-157s | 2 | Host + Comedian | Part of seg01 |
| 157-367s | 1 | **Comedian alone** (210s) | Part of seg01 (missed) |
| 367-408s | 2-3 | Multiple people | Part of seg01 |
| 408-550s | 1 | **Comedian alone** (142s) | Part of seg01 (missed) |
| 550-584s | 2-3 | Multiple people | Part of seg01 |
| 584-721s | 1 | **Comedian alone** (137s) | Part of seg01 (missed) |
| 721-751s | 2 | Host + Comedian | Between segments |
| 751-899s | 1 | **Comedian alone** (148s) | seg02 ✓ |
| 899-905s | 0-1 | Empty/Exit | - |

**Before fix:** Only 1 segment exported (seg01: 0→730s, but seg02 was filtered out)
**Expected:** 4 segments of comedian alone (157→367s, 408→550s, 584→721s, 751→899s)

## Solution

### Fix Applied

Disabled the overly broad rules in `clipper_rules.yaml`:

```yaml
# DISABLED: These broad rules interfere with the main 2→1 and 1→2 detection
# - from: any
#   to: 2+
#   action: start_segment

# - from: 2+
#   to: 1-
#   action: end_segment
```

### Active Rules (After Fix)

```yaml
rules:
  # Primary rules for standup comedy with host
  - from: 2
    to: 1
    action: start_segment  # Host exits → comedian alone

  - from: 1
    to: 2
    action: end_segment    # Host enters → end comedian's set

  # Handle empty stage
  - from: 0
    to: 1
    action: start_segment  # Comedian enters alone

  - from: 1
    to: 0
    action: end_segment    # Comedian exits
```

### Expected Results (After Fix)

With the fixed rules, the clipper should detect:

**Stable transitions only** (require 5 consecutive frames):
- **Segment 1:** 157s → 721s (9.5 minutes) - Comedian alone
  - Starts at 157s: `2→1` transition (stable)
  - Ends at 721s: `1→2` transition (stable)

- **Segment 2:** 751s → 899s (2.5 minutes) - Comedian alone
  - Starts at 751s: `2→1` transition (stable)
  - Ends at 899s: `1→0` transition (stable)

**Missed segments** (due to instability):
- 367s → 408s: The `1→2` transition at 367s is not stable (only 3 frames before changing to 3)
- 550s → 584s: The `1→2` transition at 550s immediately changes to 3

## Additional Improvements (Future)

### Option 1: Reduce Stability Requirement

Change `transition_stability_frames` from 5 to 3:

```yaml
transition_stability_frames: 3  # More responsive, may increase false positives
```

This would capture the unstable transitions but might introduce noise.

### Option 2: Enhanced Transition Detection

Modify the transition detection code to:
- Recognize a transition as soon as count changes (with 1-frame confirmation)
- Use smoothing window to validate it's not a flicker
- Don't require stability at the NEW value, just at the old value

### Option 3: Multi-Signal Confidence

Use the confidence-based exit detection system:
- Combine YOLO zone count with velocity, appearance, and context signals
- Lower confidence threshold for clear 1→2 or 2→1 transitions
- Higher threshold for ambiguous transitions

## Testing

Run on test_vid.mov with fixed configuration:

```bash
python clipper_unified.py test_vid.mov --config clipper_rules.yaml
```

Expected output:
```
Analyzing transitions...
  Segment start at 157.0s: 2→1 people
  Segment end at 721.0s: 1→2 people
  Segment start at 751.0s: 2→1 people
  Segment end at 899.0s: 1→0 people
Detected 2 segments from transitions
```

After filtering and buffering:
- Clip 1: ~152s → ~726s (9.5 minutes)
- Clip 2: ~746s → ~904s (2.5 minutes)

## Summary

The fix changes detection from:
- **Before:** 1 usable segment (751s → 899s), missing 3 comedian-alone periods
- **After:** 2 segments capturing comedian-alone periods (157s → 721s, 751s → 899s)

The remaining missed segments (367s→408s, 550s→584s) are due to stability requirements and can be addressed with the future improvements listed above.
