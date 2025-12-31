# Manual Test Scripts

This directory contains manual test scripts for testing and debugging specific bot features.

## OCR Testing Scripts

### `track_hp_simple.py`
**Purpose:** Real-time HP tracking and OCR comparison

Continuously monitors HP using both Tesseract OCR and Template Matching OCR, displaying results side-by-side.

**Usage:**
```bash
python tests/manual/track_hp_simple.py
```

**Features:**
- Real-time HP monitoring (updates every 0.5s)
- Side-by-side comparison of both OCR methods
- Success rate statistics
- Match/mismatch detection
- Press Ctrl+C to stop and see final statistics

**What to look for:**
- Mismatches when HP contains 9 or 4
- Which method has higher success rate
- Which method fails less often

---

### `compare_ocr_methods.py`
**Purpose:** Compare OCR methods on a static screenshot

Tests both Tesseract and Template Matching OCR on a saved screenshot image.

**Usage:**
```bash
python tests/manual/compare_ocr_methods.py <image_path> <expected_value>
```

**Example:**
```bash
python tests/manual/compare_ocr_methods.py ocr_debug/hp_strategy_0.png 99
```

**Features:**
- Runs both OCR methods on the same image
- Shows preprocessing strategies for Tesseract
- Tests different correlation thresholds for Template Matching
- Identifies which method got the correct answer

---

### `test_template_ocr.py`
**Purpose:** Interactive template OCR testing

Allows you to manually position your mouse over the HP orb and test template matching.

**Usage:**
```bash
python tests/manual/test_template_ocr.py
```

**Features:**
- Interactive - asks you to position mouse over HP text
- Captures small region around HP orb
- Tests template matching with visual feedback
- Saves debug images

---

### `test_ocr_improvements.py`
**Purpose:** Test Tesseract OCR preprocessing improvements

Tests the drop shadow removal and color-adaptive preprocessing on a screenshot.

**Usage:**
```bash
python tests/manual/test_ocr_improvements.py <image_path> <expected_value>
```

**Example:**
```bash
python tests/manual/test_ocr_improvements.py ocr_debug/hp_strategy_0.png 70
```

**Features:**
- Tests color detection
- Shows drop shadow removal
- Shows color-adaptive preprocessing
- Generates multiple preprocessing strategies
- Saves debug images

---

### `diagnose_nine_detection.py`
**Purpose:** Diagnose 9 vs 4 detection issues

Specifically tests the shape detection heuristics for distinguishing between 9 and 4.

**Usage:**
```bash
python tests/manual/diagnose_nine_detection.py <image_path>
```

**Features:**
- Tests hole detection
- Tests tail detection
- Shows shape analysis results
- Helps identify why 9s are misread as 4s

---

## Recommended Testing Workflow

1. **Start with live tracking:**
   ```bash
   python tests/manual/track_hp_simple.py
   ```
   Run this while playing to see real-time OCR performance.

2. **If you notice mismatches, capture screenshots:**
   - Screenshots are automatically saved in `ocr_debug/` when debug mode is enabled
   - Or use `compare_ocr_methods.py` on existing screenshots

3. **Analyze specific failures:**
   ```bash
   python tests/manual/compare_ocr_methods.py ocr_debug/hp_49.png 49
   ```

4. **Debug 9 detection issues:**
   ```bash
   python tests/manual/diagnose_nine_detection.py ocr_debug/hp_99.png
   ```

---

## Expected Results

### Template Matching OCR (Recommended)
- **Accuracy:** ~99% (no 4/9 confusion)
- **Speed:** ~2ms per read
- **Preprocessing:** Minimal (just color isolation)

### Tesseract OCR (Legacy)
- **Accuracy:** ~90-95% (struggles with 4/9)
- **Speed:** ~100ms+ per read
- **Preprocessing:** Heavy (drop shadow, color-adaptive, morphology)

---

## Tips

- Template Matching should be **faster** and **more accurate**
- If Template Matching fails, check that font templates exist in `src/osrsbot/fonts/Plain11/`
- If Tesseract consistently misreads 9 as 4, Template Matching will fix this
- Use `track_hp_simple.py` for extended testing to gather statistics
