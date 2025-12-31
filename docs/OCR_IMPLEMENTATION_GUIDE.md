# OCR Implementation Guide

This guide explains the two OCR approaches available in the bot and how to use them.

## Overview

The bot now supports two OCR methods for reading HP, Prayer, and other stats:

1. **Tesseract OCR** (Legacy) - Machine learning-based text recognition
2. **Template Matching OCR** (Recommended) - Pixel-perfect template matching

## Quick Comparison

| Feature | Tesseract OCR | Template Matching |
|---------|--------------|-------------------|
| **Speed** | ~100ms+ | ~2ms |
| **Accuracy** | ~90-95% | ~99% |
| **9/4 Confusion** | Common issue | No confusion |
| **Preprocessing** | Heavy | Minimal |
| **Best For** | Variable fonts | Fixed-width game fonts |

## Template Matching OCR (Recommended)

### How It Works

Based on kellton's OS-Bot-COLOR implementation:
1. **Color Isolation**: Uses `cv2.inRange()` to isolate HP orb colors (green/red)
2. **Template Matching**: Uses `cv2.matchTemplate()` with 0.98 correlation threshold
3. **Character Detection**: Matches exact pixel patterns against font templates
4. **Result**: Returns the digits found, sorted left-to-right

### Key Advantages

- **No 9/4 confusion**: Exact pixel matching means 9 is never misread as 4
- **Much faster**: ~2ms vs 100ms+ for Tesseract
- **Simpler**: No complex preprocessing needed
- **More reliable**: Works consistently across different HP values

### Font Templates

Font templates are stored in `src/osrsbot/fonts/Plain11/`:
- `48.bmp` - Character '0' (ASCII 48)
- `49.bmp` - Character '1' (ASCII 49)
- ...
- `57.bmp` - Character '9' (ASCII 57)

These are grayscale BMP images of each digit as it appears in OSRS.

### Usage Example

```python
from osrsbot.services.template_ocr_service import (
    get_template_ocr_service,
    ORB_GREEN,
    ORB_RED,
)
import cv2
import numpy as np
import pyautogui

# Initialize service
template_ocr = get_template_ocr_service()

# Capture HP region
screenshot = pyautogui.screenshot(region=(x, y, width, height))
img_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

# Extract HP
hp = template_ocr.extract_number(
    img_np,
    font_name="plain11",
    colors=[ORB_GREEN, ORB_RED],
    correlation_threshold=0.98
)

print(f"HP: {hp}")
```

### Available Colors

```python
from osrsbot.services.template_ocr_service import (
    ORB_GREEN,   # HP (high health)
    ORB_RED,     # HP (low health)
    CYAN,        # Prayer points
    YELLOW,      # General UI text
    WHITE,       # White text
)
```

## Tesseract OCR (Legacy)

### How It Works

1. **Preprocessing Pipeline**:
   - Drop shadow removal
   - Color-adaptive channel isolation
   - Multiple resize/contrast/threshold strategies
   - Morphological operations
2. **OCR Recognition**: Tesseract interprets preprocessed images
3. **Heuristics**: Shape detection to distinguish 9 from 4
4. **Smoothing**: Temporal smoothing across multiple reads

### Known Issues

- **9/4 Confusion**: Tesseract often misreads 9 as 4 despite heuristics
- **Slower**: Heavy preprocessing takes 100ms+
- **Complex**: Many tunable parameters and strategies

### When to Use

- You don't have font templates
- You're reading variable-width text (not game stats)
- You need to read non-numeric text

## Testing Both Methods

### Real-time Tracking

Track HP continuously and compare both methods:

```bash
python tests/manual/track_hp_simple.py
```

Output:
```
[   1] Tesseract: 99 | Template: 99 | ✓ MATCH
[   2] Tesseract: 94 | Template: 99 | ✗ MISMATCH
[   3] Tesseract: 99 | Template: 99 | ✓ MATCH
```

### Screenshot Comparison

Compare on a saved screenshot:

```bash
python tests/manual/compare_ocr_methods.py ocr_debug/hp_99.png 99
```

### Comprehensive Bot Test

Run the comprehensive test bot to see OCR comparison:

```bash
python -m osrsbot.main
```

The OCR test (Test 8/9) will show:
- Tesseract HP result
- Template HP result
- Whether they match
- Performance comparison

## Migration Guide

### Switching to Template Matching

If you want to replace Tesseract with Template Matching in your bot:

**1. Update `game_queries.py`:**

```python
# OLD (Tesseract)
def get_hp(self, force: bool = False) -> Optional[int]:
    hp_region = OCRRegion(...)
    hp = self.ocr_service.read_number(
        region=hp_region,
        min_value=1,
        max_value=99
    )
    return hp

# NEW (Template Matching)
def get_hp(self, force: bool = False) -> Optional[int]:
    from osrsbot.services.template_ocr_service import (
        get_template_ocr_service,
        ORB_GREEN,
        ORB_RED,
    )
    import cv2
    import numpy as np
    import pyautogui

    # Get region config
    hp_region_config = self.config.get("coordinates", "ocr", "hp_region")
    win_pos = self.ocr_service.get_window_position()

    # Capture
    hp_x = win_pos[0] + hp_region_config["x"]
    hp_y = win_pos[1] + hp_region_config["y"]
    screenshot = pyautogui.screenshot(
        region=(hp_x, hp_y, hp_region_config["width"], hp_region_config["height"])
    )

    # Template match
    img_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    template_ocr = get_template_ocr_service()
    hp = template_ocr.extract_number(
        img_np,
        font_name="plain11",
        colors=[ORB_GREEN, ORB_RED]
    )

    return hp
```

**2. Update Prayer similarly** (use CYAN color instead of ORB_GREEN/ORB_RED)

**3. Test thoroughly** using `track_hp_simple.py` before deploying

## Troubleshooting

### Template Matching Returns None

**Causes:**
1. Font templates not found
2. Wrong HP region coordinates
3. Colors don't match (wrong color list)
4. Correlation threshold too high

**Debug:**
1. Check font templates exist: `ls src/osrsbot/fonts/Plain11/`
2. Save screenshot: `cv2.imwrite("debug.png", img_np)`
3. Try lower threshold: `correlation_threshold=0.95`
4. Test different colors or add more to the list

### Tesseract Still Misreads 9 as 4

**Solutions:**
1. Switch to Template Matching (recommended)
2. Adjust preprocessing strategies in `constants.py`
3. Check shape detection thresholds in `SHAPE_DETECTION`
4. Use CNN classifier instead: `use_cnn=True`

### Performance Issues

**Template Matching:**
- Should be <5ms per read
- If slower, check font loading (should only load once)

**Tesseract:**
- 100ms+ is normal due to heavy preprocessing
- Reduce number of strategies to speed up
- Disable debug mode: `debug=False`

## Best Practices

1. **Use Template Matching for game stats** (HP, Prayer, Run Energy)
2. **Use Tesseract for dynamic text** (chat, item names)
3. **Test extensively** with both methods before choosing
4. **Monitor accuracy** in production using logs
5. **Keep font templates updated** if OSRS fonts change

## References

- **kellton's OS-Bot-COLOR**: Original template matching implementation
  - Repository: https://github.com/kelltom/OS-Bot-COLOR
  - OCR: `src/utilities/ocr.py`
  - Fonts: `src/utilities/fonts/`

- **Our Implementation**:
  - Service: `src/osrsbot/services/template_ocr_service.py`
  - Fonts: `src/osrsbot/fonts/Plain11/`
  - Tests: `tests/manual/`
