# Blur Detection Feature Guide

## 🎯 What It Does

Prevents clipping at blurry/out-of-focus frames by automatically shifting segment boundaries to nearby sharp frames.

**Problem Solved:** Blurry frames often occur during:
- Camera transitions
- Focus changes
- Camera movement
- Scene changes

Clipping at these moments creates poor-quality clip boundaries.

---

## ✅ How It Works

### 1. Blur Measurement
Uses **Laplacian variance** to calculate frame sharpness:
- **Higher score** = Sharper image
- **Lower score** = Blurrier image

```python
blur_score = cv2.Laplacian(gray_frame, cv2.CV_64F).var()
```

### 2. Blur Classification
Compares each frame's score against threshold:
```yaml
blur_detection:
  threshold: 100.0  # Frames below this are "blurry"
```

### 3. Boundary Shifting
When a segment boundary lands on a blurry frame:
1. Searches nearby frames (forward and backward)
2. Finds the sharpest frame within max_shift range
3. Moves boundary to that sharp frame
4. Logs the shift

---

## 🔧 Configuration

### Basic Settings

```yaml
blur_detection:
  enabled: true

  # Blur threshold (Laplacian variance)
  # Lower = more strict (more frames considered blurry)
  threshold: 100.0

  # Max frames to search for sharp boundary
  boundary_shift_max_frames: 30  # ~1 second at 30fps

  # Minimum sharpness for boundaries
  # Higher than general threshold for better clip quality
  boundary_sharpness_min: 150.0

  # Log blurry frames to console
  log_blurry_frames: false
```

### Threshold Tuning

**Typical Laplacian variance values:**
- **<50**: Very blurry (motion blur, out of focus)
- **50-100**: Moderately blurry
- **100-200**: Acceptable sharpness
- **200+**: Sharp/crisp

**Recommended settings by video quality:**

```yaml
# High-quality professional video
blur_detection:
  threshold: 200.0
  boundary_sharpness_min: 300.0

# Standard quality (YouTube, etc.)
blur_detection:
  threshold: 100.0
  boundary_sharpness_min: 150.0

# Low-quality/compressed video
blur_detection:
  threshold: 50.0
  boundary_sharpness_min: 75.0

# Very low quality (disable if everything is blurry)
blur_detection:
  enabled: false
```

---

## 📊 Output & Debugging

### Console Output

**During processing:**
```
Analyzed 906 frames
Blurry frames: 45/906 (5.0%)
```

**When shifting boundaries:**
```
Adjusting boundaries to avoid blurry frames...
  Shifted boundary by 15 frames (blur: 85.2 → 245.8)
  Shifted boundary by 8 frames (blur: 62.3 → 198.4)
```

### Debug Frames

**Filename includes blur score:**
```
seg01_first_f60_blur245.jpg   ← Sharp frame (score 245)
seg01_last_f3060_blur87.jpg   ← Blurry frame (score 87)
```

**Visual overlay:**
- **Text shows**: `Blur: 245.8 (SHARP)` in green
- **Text shows**: `Blur: 87.3 (BLURRY)` in red

---

## 🎬 Real-World Example

### Before Blur Detection

```
Original boundary at frame 1000 (blur score: 45)
  ↓ Segment starts on blurry transition frame
[BLURRY FRAME] → [Sharp frames...]
```

### After Blur Detection

```
Shifted boundary to frame 1015 (blur score: 220)
Shifted boundary by 15 frames (blur: 45.2 → 220.1)
  ↓ Segment starts on sharp frame
[Sharp frames...]
```

---

## 🔍 When to Use

### ✅ Use Blur Detection When:
- Professional video production
- Camera has autofocus that hunts
- Frequent camera movements/pans
- Scene transitions with fades
- Variable video quality

### ❌ Disable When:
- Entire video is consistently blurry/low quality
- Video is highly compressed (everything scores low)
- Using webcam/security camera footage
- Blur detection causes unwanted boundary shifts

---

## 🎯 Best Practices

### 1. Test with Debug Mode
```bash
python3 clipper_configurable.py video.mp4 -d
```

Check debug frame filenames:
- `blur250.jpg` = Sharp frame (good)
- `blur45.jpg` = Blurry frame (poor boundary)

### 2. Review Console Output
```
Blurry frames: 850/900 (94.4%)  ← Most frames blurry, lower threshold
Blurry frames: 23/900 (2.6%)    ← Few blurry frames, threshold good
```

### 3. Adjust Threshold Iteratively
1. Run with default (100.0)
2. Check blur percentage
3. If >50% blurry, lower threshold
4. If <5% blurry, consider raising threshold

### 4. Validate Shifted Boundaries
- Check debug frames show sharp images
- Verify shifts didn't break segment timing
- Ensure max_shift isn't too large (creates big jumps)

---

## ⚙️ Advanced Configuration

### Different Thresholds for Start vs End

While not directly supported, you can adjust `boundary_sharpness_min` to be more strict:

```yaml
blur_detection:
  threshold: 100.0              # General blur detection
  boundary_sharpness_min: 200.0  # Higher bar for boundaries
```

This means:
- Frames with score <100 are "blurry"
- But boundaries require score ≥200 to be used

### Disable for Low-Quality Videos

```yaml
blur_detection:
  enabled: false
```

### Enable Logging for Tuning

```yaml
blur_detection:
  log_blurry_frames: true
```

Output:
```
  Blurry frame 1234: score=45.2
  Blurry frame 1235: score=38.7
  Blurry frame 5678: score=62.3
```

---

## 📈 Performance Impact

**Blur detection adds:**
- ~5-10% processing time (Laplacian calculation)
- Negligible memory usage
- Worth it for better clip quality

**Can be optimized:**
- Already sampled (not every frame analyzed)
- Parallel processing possible
- Cached during detection phase

---

## 🐛 Troubleshooting

### Problem: All frames marked as blurry

**Cause:** Threshold too high for video quality

**Solution:**
```yaml
blur_detection:
  threshold: 50.0  # Lower threshold
```

### Problem: No boundary shifts happening

**Cause:**
1. All frames are similar quality, or
2. `boundary_sharpness_min` too high

**Solution:**
```yaml
blur_detection:
  boundary_sharpness_min: 100.0  # Lower minimum
```

### Problem: Boundaries shifted too far

**Cause:** `boundary_shift_max_frames` too large

**Solution:**
```yaml
blur_detection:
  boundary_shift_max_frames: 15  # Reduce max shift
```

### Problem: Wrong frames selected

**Cause:** Not enough sharp frames in search range

**Solution:**
```yaml
blur_detection:
  boundary_shift_max_frames: 60  # Increase search range
```

---

## 📚 Technical Details

### Laplacian Variance Explained

The Laplacian operator detects edges by computing second derivatives:

1. **Convert to grayscale** (edges more visible)
2. **Apply Laplacian filter** (highlights edges/details)
3. **Calculate variance** (measure edge strength)

**Why it works:**
- Sharp images have strong edges → High variance
- Blurry images have weak edges → Low variance
- Motion blur reduces edge contrast → Low variance

### Alternative Methods Considered

1. **Sobel gradient** - Similar but less precise
2. **FFT frequency analysis** - Too slow
3. **Tenengrad** - More expensive, similar results

Laplacian variance chosen for **speed + accuracy balance**.

---

## 🎯 Summary

Blur detection:
- ✅ Automatically finds sharp frames for boundaries
- ✅ Prevents clipping during camera transitions
- ✅ Configurable for different video qualities
- ✅ Visual feedback in debug frames
- ✅ Minimal performance impact

**Recommended for all professional use cases!**
