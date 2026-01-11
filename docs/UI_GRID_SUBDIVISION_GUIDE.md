# UI Grid Subdivision System - Technical Guide

## Overview

The UI Grid Subdivision system automatically detects grid-based UI elements (inventory, prayer tab, spellbook) using template matching, then mathematically divides them into individual clickable slots. This eliminates the need to template-match each individual item.

## Architecture

### Core Classes

1. **UIElement** ([ui_elements.py:27-83](c:\Users\elliott\Documents\Rsbot\OSRS-bot\OSRS-Automation-Framework\src\osrsbot\models\ui_elements.py#L27-L83))
   - Represents a single clickable UI element
   - Stores bounding box coordinates (x0, y0, x1, y1)
   - Provides center point calculation
   - All coordinates are relative to game window

2. **UIElementGrid** ([ui_elements.py:85-358](c:\Users\elliott\Documents\Rsbot\OSRS-bot\OSRS-Automation-Framework\src\osrsbot\models\ui_elements.py#L85-L358))
   - Represents a grid of UI elements
   - Handles template detection and subdivision
   - Caches results with TTL for performance

3. **UIManager** ([ui_manager_service.py:15-286](c:\Users\elliott\Documents\Rsbot\OSRS-bot\OSRS-Automation-Framework\src\osrsbot\services\ui_manager_service.py#L15-L286))
   - Centralized manager for all UI elements
   - Provides debug visualization capabilities
   - Tracks active grids for context-aware operations

---

## How Grid Subdivision Works

### Step 1: Template Detection

**Location:** [ui_elements.py:187-261](c:\Users\elliott\Documents\Rsbot\OSRS-bot\OSRS-Automation-Framework\src\osrsbot\models\ui_elements.py#L187-L261)

```python
def detect(self, img_gray: np.ndarray, force: bool = False) -> bool
```

**Process:**

1. **Cache Check:** If sticky mode is enabled and TTL hasn't expired, returns cached detection
2. **Template Matching:** Uses OpenCV's `cv.matchTemplate()` with `TM_CCOEFF_NORMED`
3. **Threshold Check:** Compares max confidence value against threshold
4. **Subdivision:** If detected, calls `_subdivide_grid()` to calculate slot positions

**Key Variables:**
- `max_val`: Confidence score (0.0-1.0)
- `max_loc`: (x, y) position of top-left corner
- `self.template.shape`: (height, width) of template image

**Example:**
```
Inventory template detected at (1000, 500) with 174×294 pixels
Confidence: 0.95 (above 0.80 threshold)
```

---

### Step 2: Grid Subdivision Calculation

**Location:** [ui_elements.py:263-324](c:\Users\elliott\Documents\Rsbot\OSRS-bot\OSRS-Automation-Framework\src\osrsbot\models\ui_elements.py#L263-L324)

```python
def _subdivide_grid(self, x: int, y: int, w: int, h: int) -> None
```

**Mathematical Process:**

#### 2.1 Adjust for Border Offset

Template images often include border pixels that aren't part of the actual grid area:

```python
grid_x = x + self.border_offset_x
grid_y = y + self.border_offset_y
grid_w = w - (2 * self.border_offset_x)
grid_h = h - (2 * self.border_offset_y)
```

**Example (Inventory with 8px border):**
```
Template detected at: (1000, 500), size: 174×294
Border offset: 8px (left/right/top/bottom)

Actual grid area:
grid_x = 1000 + 8 = 1008
grid_y = 500 + 8 = 508
grid_w = 174 - (2 × 8) = 158
grid_h = 294 - (2 × 8) = 278
```

#### 2.2 Calculate Cell Dimensions

```python
cell_w = grid_w / self.num_cols
cell_h = grid_h / self.num_rows
```

**Example (Inventory: 7 rows × 4 cols):**
```
cell_w = 158 / 4 = 39.5 pixels
cell_h = 278 / 7 = 39.71 pixels
```

#### 2.3 Calculate Each Slot Position

**Center-First Approach** (more accurate):

```python
for row in range(self.num_rows):
    for col in range(self.num_cols):
        # 1. Calculate exact center point (float precision)
        center_x_float = grid_x + (col + 0.5) * cell_w
        center_y_float = grid_y + (row + 0.5) * cell_h

        # 2. Round to integer for pixel-perfect clicking
        center_x_int = int(round(center_x_float))
        center_y_int = int(round(center_y_float))

        # 3. Calculate bounds with padding
        half_w = (cell_w / 2) - self.padding
        half_h = (cell_h / 2) - self.padding

        x0 = int(center_x_float - half_w)
        y0 = int(center_y_float - half_h)
        x1 = int(center_x_float + half_w)
        y1 = int(center_y_float + half_h)

        # 4. Create element with precise center
        element = UIElement(x0, y0, x1, y1,
                          _center_x=center_x_int,
                          _center_y=center_y_int)
```

**Why Center-First?**
- Avoids cumulative rounding errors
- Each slot's center is independently calculated
- Ensures center point matches what debug visualization shows

**Example (Slot 0: row=0, col=0 with 2px padding):**
```
center_x_float = 1008 + (0 + 0.5) × 39.5 = 1027.75
center_y_float = 508 + (0 + 0.5) × 39.71 = 527.86

center_x_int = round(1027.75) = 1028
center_y_int = round(527.86) = 528

half_w = (39.5 / 2) - 2 = 17.75
half_h = (39.71 / 2) - 2 = 17.86

x0 = int(1027.75 - 17.75) = 1010
y0 = int(527.86 - 17.86) = 510
x1 = int(1027.75 + 17.75) = 1045
y1 = int(527.86 + 17.86) = 545

Final slot 0: bounds=(1010, 510, 1045, 545), center=(1028, 528)
```

---

### Step 3: Accessing Elements

**By Index** (0-based, left-to-right, top-to-bottom):

```python
slot_5 = inventory.get_element(5)  # 2nd row, 2nd col (index 5)
```

**By Row/Column**:

```python
slot_5 = inventory.get_element_at(row=1, col=1)  # Same as index 5
```

**Index to (row, col) formula:**
```python
index = row * num_cols + col
row = index // num_cols
col = index % num_cols
```

---

## Debug Visualization

### How Debug Drawing Works

**Location:** [ui_manager_service.py:129-205](c:\Users\elliott\Documents\Rsbot\OSRS-bot\OSRS-Automation-Framework\src\osrsbot\services\ui_manager_service.py#L129-L205)

```python
def draw_debug_overlay(self, img: np.ndarray,
                       show_grids: bool = True,
                       show_slots: bool = True,
                       show_labels: bool = True) -> np.ndarray
```

**Drawing Process:**

1. **Grid Outer Box:** Draws the full detected template bounding box
   ```python
   x, y, w, h = grid.detected_bbox
   cv.rectangle(img_debug, (x, y), (x + w, y + h), color, 1)
   ```

2. **Individual Slot Boxes:** Draws each subdivided element
   ```python
   for element in grid.elements:
       x0, y0, x1, y1 = element.bbox
       cv.rectangle(img_debug, (x0, y0), (x1, y1), color, 1)
   ```

3. **Center Points:** Draws a small circle at each element's center
   ```python
   cx, cy = element.center
   cv.circle(img_debug, (cx, cy), 2, color, -1)
   ```

**Color Mapping (BGR format):**
- Inventory: Green (0, 255, 0)
- Spellbook: Red (0, 0, 255)
- Prayer: Blue (255, 0, 0)
- Equipment: Yellow (0, 255, 255)
- Chat: Cyan (255, 255, 0)
- Minimap: Magenta (255, 0, 255)

### Verification: Debug Matches Subdivision

**The debug visualization is 100% accurate** because:

1. It reads `element.bbox` and `element.center` directly
2. These values are set during `_subdivide_grid()`
3. No additional calculations or transformations are applied

**What you see in the debug image is exactly what the bot will click.**

---

## Configuration Parameters

### Border Offset

Excludes template border pixels from grid calculations:

```python
UIElementGrid(
    name="inventory",
    border_offset=8,  # Applies to all edges
    # OR use separate offsets:
    border_offset_x=8,  # Left/right
    border_offset_y=10  # Top/bottom
)
```

**When to adjust:**
- Template includes thick borders: Increase offset
- First/last slots misaligned: Fine-tune X/Y separately
- Grid detection works but clicks miss targets: Adjust offset

### Padding

Shrinks each slot's clickable area (avoids border pixels):

```python
UIElementGrid(
    name="inventory",
    padding=2  # Remove 2px from each edge of each slot
)
```

**Effect:**
- `padding=0`: Full cell width/height (may click grid lines)
- `padding=2`: Safer, avoids clicking between slots
- `padding=5`: Very conservative, smaller click area

### Threshold

Detection confidence requirement (0.0-1.0):

```python
UIElementGrid(
    name="inventory",
    threshold=0.80  # Require 80% match
)
```

**Guidelines:**
- `0.70-0.75`: More permissive, may have false positives
- `0.80-0.85`: Balanced (default)
- `0.90-0.95`: Strict, may miss valid detections

### Sticky Mode & TTL

Cache detection results to avoid re-matching every frame:

```python
UIElementGrid(
    name="inventory",
    sticky=True,      # Enable caching
    ttl_seconds=5.0   # Cache for 5 seconds
)
```

**Use Cases:**
- `sticky=True`: UI rarely moves (inventory, prayer tab)
- `sticky=False`: UI can disappear (dialog boxes, tooltips)
- Higher TTL: Performance optimization for static UIs
- Lower TTL: More responsive to UI changes

---

## Common Use Cases

### Example 1: Inventory Slot Detection

```python
# Define inventory grid
inventory = UIElementGrid(
    name="inventory",
    template_path="images/bot/inventory_template.png",
    num_rows=7,
    num_cols=4,
    threshold=0.80,
    border_offset=8,
    padding=2,
    sticky=True,
    ttl_seconds=5.0
)

# Detect in screenshot
img_gray = screen.capture_grayscale()
if inventory.detect(img_gray):
    # Access first slot (top-left)
    slot_0 = inventory.get_element(0)
    center_x, center_y = slot_0.center
    print(f"First slot center: ({center_x}, {center_y})")

    # Access bottom-right slot (index 27)
    slot_27 = inventory.get_element(27)
    # Or by row/col
    slot_27 = inventory.get_element_at(row=6, col=3)
```

### Example 2: Prayer Tab (6 rows × 5 cols)

```python
prayer_tab = UIElementGrid(
    name="prayer",
    template_path="images/bot/prayer_tab_template.png",
    num_rows=6,
    num_cols=5,
    threshold=0.85,
    border_offset_x=10,  # Different X/Y offsets
    border_offset_y=12,
    padding=3
)

# Detect and access "Protect from Melee" (example: row 2, col 1)
if prayer_tab.detect(img_gray):
    protect_melee = prayer_tab.get_element_at(row=2, col=1)
    x, y = protect_melee.center
    # Click the prayer
    bot.actions.click(x, y)
```

### Example 3: Debug Visualization

```python
from osrsbot.services.ui_manager_service import UIManager

# Setup UI manager
ui_manager = UIManager()
ui_manager.add_grid("inventory", inventory)
ui_manager.add_grid("prayer", prayer_tab)

# Enable debug mode
ui_manager.enable_debug("ui_debug/my_bot")

# Capture and detect
img_gray = screen.capture_grayscale()
img_color = screen.capture_bgr()

inventory.detect(img_gray)
prayer_tab.detect(img_gray)

# Save debug image with all grids and slots drawn
ui_manager.save_debug_image(
    img_color,
    prefix="inventory_prayer",
    show_grids=True,    # Draw outer grid boxes
    show_slots=True,    # Draw individual slot boxes
    show_labels=True    # Add grid names
)
# Output: ui_debug/my_bot/inventory_prayer_20260111_143045_123.png
```

---

## Troubleshooting Guide

### Issue: Slots are offset from actual UI

**Symptoms:**
- Debug boxes don't align with actual slots
- First/last rows/columns are misaligned
- Center points are off-target

**Solutions:**

1. **Check template borders:**
   ```python
   # Open template image and measure border pixels
   # Adjust border_offset accordingly
   grid.border_offset_x = 8  # Measured left/right border
   grid.border_offset_y = 10  # Measured top/bottom border
   ```

2. **Verify row/column count:**
   ```python
   # Inventory is 7×4, not 4×7!
   grid.num_rows = 7    # Vertical slots
   grid.num_cols = 4    # Horizontal slots
   ```

3. **Check padding:**
   ```python
   # Too much padding shrinks click area too much
   grid.padding = 2  # Start with 2px
   ```

### Issue: Grid not detected

**Symptoms:**
- `grid.visible == False`
- Template matching fails
- Low confidence scores

**Solutions:**

1. **Lower threshold:**
   ```python
   grid.threshold = 0.70  # Try lower value
   ```

2. **Check template image:**
   - Template must be exact size of UI element
   - Use grayscale template images
   - Avoid UI elements with dynamic content

3. **Force re-detection:**
   ```python
   grid.detect(img_gray, force=True)  # Bypass cache
   ```

### Issue: Clicks miss targets slightly

**Symptoms:**
- Clicks land near but not on intended slots
- Edge slots more accurate than center slots

**Solutions:**

1. **Fine-tune border offset:**
   ```python
   # Increment/decrement by 1px and test
   grid.border_offset_x = 9  # Was 8
   ```

2. **Reduce padding:**
   ```python
   grid.padding = 1  # Was 2
   ```

3. **Verify center calculation:**
   - Debug image shows red circles at centers
   - Visually verify circles are centered in slots

---

## Performance Optimization

### Sticky Mode (Recommended)

Caches detection results to avoid repeated template matching:

```python
grid = UIElementGrid(
    name="inventory",
    sticky=True,        # Enable caching
    ttl_seconds=5.0     # Cache for 5 seconds
)
```

**Performance Impact:**
- Without sticky: ~5-10ms per detection per frame
- With sticky: ~0.01ms (just cache lookup)

**Best Practices:**
- Use sticky=True for static UI elements (inventory, prayer, spellbook)
- Use sticky=False for dynamic UI (tooltips, dialogs)
- Adjust TTL based on how often UI changes

### Selective Detection

Only detect what you need:

```python
# BAD: Detect everything every frame
for grid in all_grids:
    grid.detect(img_gray, force=True)

# GOOD: Only detect when needed
if need_inventory:
    inventory.detect(img_gray)
if need_prayer:
    prayer_tab.detect(img_gray)
```

### Template Size Optimization

Smaller templates = faster matching:

```python
# SLOW: Full inventory window (200×350 pixels)
template = "images/inventory_full.png"

# FAST: Just the border (174×294 pixels, minimal content)
template = "images/inventory_border.png"
```

---

## Advanced Topics

### Edge Row Adjustment (Commented Out)

In [ui_elements.py:303-306](c:\Users\elliott\Documents\Rsbot\OSRS-bot\OSRS-Automation-Framework\src\osrsbot\models\ui_elements.py#L303-L306), there's commented code for nudging edge rows:

```python
# edge_row_nudge = 15
# if row == 0:
#     center_y_int -= edge_row_nudge
# if row == self.num_rows - 1:
#     center_y_int += edge_row_nudge
```

**Purpose:** Adjust first/last row centers if they're systematically misaligned.

**When to use:**
- First row clicks too low: Negative nudge
- Last row clicks too high: Positive nudge
- Only needed if border_offset doesn't fix the issue

### Custom Center Calculation

Elements support pre-calculated centers to avoid rounding errors:

```python
element = UIElement(
    x0, y0, x1, y1,
    _center_x=precise_center_x,  # Pre-calculated
    _center_y=precise_center_y
)

# Property returns pre-calculated value if available
cx, cy = element.center  # Returns (_center_x, _center_y)
```

**Why this matters:**
- Center calculated once during subdivision
- Debug visualization uses same center
- No recalculation rounding errors

### Multi-Template Support

Some UI elements may need multiple templates (different states):

```python
# Template for inventory when open
inventory_open = UIElementGrid(
    name="inventory",
    template_path="images/inventory_open.png",
    num_rows=7, num_cols=4
)

# Template for inventory when minimized
inventory_minimized = UIElementGrid(
    name="inventory_mini",
    template_path="images/inventory_mini.png",
    num_rows=7, num_cols=4
)

# Try both
if not inventory_open.detect(img_gray):
    inventory_minimized.detect(img_gray)
```

---

## Related Files

- [ui_elements.py](c:\Users\elliott\Documents\Rsbot\OSRS-bot\OSRS-Automation-Framework\src\osrsbot\models\ui_elements.py) - Core UIElement and UIElementGrid classes
- [ui_manager_service.py](c:\Users\elliott\Documents\Rsbot\OSRS-bot\OSRS-Automation-Framework\src\osrsbot\services\ui_manager_service.py) - UIManager and debug visualization
- [example_ui_debug_bot.py](c:\Users\elliott\Documents\Rsbot\OSRS-bot\OSRS-Automation-Framework\examples\example_ui_debug_bot.py) - Example usage with debug output

---

## Conclusion

The UI Grid Subdivision system provides:

1. **Accuracy:** Center-first calculation avoids cumulative errors
2. **Efficiency:** Sticky caching eliminates redundant template matching
3. **Debuggability:** Visual overlay shows exactly what bot sees
4. **Flexibility:** Configurable offsets, padding, and thresholds

**Key Takeaway:** Debug visualization is 100% accurate - what you see is what the bot will click. If debug boxes don't align with actual UI, adjust `border_offset`, not the subdivision logic.
