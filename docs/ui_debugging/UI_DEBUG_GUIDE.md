# UI Debug Visualization Guide

This guide explains how to use the UI Manager and debug visualization system to see exactly what UI elements your bot detects.

## Overview

The UI debug system draws **red boxes** around all detected UI elements, showing you:
- **Grid boundaries** (thick red boxes) - inventory, prayer, equipment, etc.
- **Individual slots** (thin red boxes with numbers) - each clickable cell in a grid
- **Button positions** (red boxes with center dots) - logout, prayers, tabs, etc.
- **Confidence scores** - how confident the detection was (0.0 to 1.0)
- **Center points** (green dots) - exact coordinates where the bot will click

## Quick Start

### 1. Run the Debug Script

The easiest way to visualize UI elements is to use the standalone debug script:

```bash
python debug_ui_elements.py
```

**Requirements:**
- Game window must be open
- `config.json` must have the correct `window_title`
- Template images must exist in `src/osrsbot/images/bot/`

### 2. Controls

While the debug window is open:
- **'q'** - Capture new screenshot and refresh detection
- **ESC** - Exit the program
- **'s'** - Toggle slot numbers on/off
- **'g'** - Toggle grid boxes on/off
- **'b'** - Toggle button boxes on/off
- **'l'** - Toggle labels on/off

### 3. Output

Debug images are automatically saved to the `ui_debug/` folder with timestamps:
```
ui_debug/
├── ui_detection_20260108_143025_123.png
├── ui_detection_20260108_143030_456.png
└── ...
```

## Integration with Your Bot Scripts

### Basic Usage

The UIManager is automatically initialized in `ScriptRunner` and available through `runner.ui_manager`:

```python
from osrsbot.core.runner import ScriptRunner

# Initialize runner
runner = ScriptRunner("RuneLite - YourAccount", "config.json")

# Access UI manager
ui_manager = runner.ui_manager

# Enable debug mode
ui_manager.enable_debug()

# Capture and detect
img_gray = runner.screen.capture_grayscale()
img_pil = runner.screen.capture()  # Returns PIL Image
img = cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)  # Convert to BGR numpy array

# Detect all UI elements
runner.template_service.detect_all(img_gray, force=True)

# Get visible elements
visible = ui_manager.get_visible_elements()
print(f"Visible grids: {visible['grids']}")
print(f"Visible buttons: {visible['buttons']}")

# Save debug image
ui_manager.save_debug_image(img, prefix="my_bot_debug")
```

### In Your Bot Class

The UIManager is accessible through `self.actions.ui_manager`:

```python
class MyBot(Bot):
    def run_cycle(self, bank_location: str, run_number: int):
        # Enable debug for this run
        if self.actions.ui_manager:
            self.actions.ui_manager.enable_debug("ui_debug/my_bot")

        # Your bot logic here...
        img_pil = self.state.screen.capture()
        img = cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)

        # Save debug image showing current UI state
        if self.actions.ui_manager:
            self.actions.ui_manager.save_debug_image(
                img,
                prefix=f"run_{run_number}"
            )
```

### Checking Specific UI Elements

```python
# Check if inventory is visible
if ui_manager.get_grid("inventory"):
    inventory = ui_manager.get_grid("inventory")
    if inventory.visible:
        print(f"Inventory detected with {len(inventory.elements)} slots")
        print(f"Confidence: {inventory.last_confidence:.3f}")

# Check if a button is visible
if ui_manager.get_button("prayer_tab"):
    prayer_btn = ui_manager.get_button("prayer_tab")
    if prayer_btn.visible:
        print(f"Prayer tab found at {prayer_btn.element.center}")
```

### Getting Element Information

```python
# Get detailed info about all elements
info = ui_manager.get_element_info()

# Grid info
for grid_name, grid_info in info["grids"].items():
    print(f"{grid_name}:")
    print(f"  Visible: {grid_info['visible']}")
    print(f"  Size: {grid_info['rows']}x{grid_info['cols']}")
    print(f"  Confidence: {grid_info['confidence']:.3f}")
    print(f"  Threshold: {grid_info['threshold']}")

# Button info
for button_name, button_info in info["buttons"].items():
    print(f"{button_name}:")
    print(f"  Visible: {button_info['visible']}")
    print(f"  Position: {button_info['position']}")
    print(f"  Confidence: {button_info['confidence']:.3f}")
```

## Understanding the Visualization

### Color Coding

- **Red boxes** - Detected UI elements
  - **Thick red** (3px) - Grid boundaries
  - **Thin red** (1px) - Individual grid slots
  - **Medium red** (2px) - Buttons
- **Green dots** - Center points where bot will click
- **Yellow text** - Slot numbers (0-indexed)
- **Red text** - Element names and confidence scores

### Confidence Scores

Confidence scores range from 0.0 to 1.0:
- **0.95+** - Excellent match (very reliable)
- **0.80-0.95** - Good match (reliable)
- **0.70-0.80** - Acceptable match (may have issues)
- **<0.70** - Poor match (likely unreliable)

Thresholds are configured in `config.json` under `templates.ui_grids` and `templates.ui_buttons`.

### Grid Slot Numbering

Grid slots are numbered 0-indexed, left-to-right, top-to-bottom:

**Inventory (7 rows × 4 cols = 28 slots):**
```
 0   1   2   3
 4   5   6   7
 8   9  10  11
12  13  14  15
16  17  18  19
20  21  22  23
24  25  26  27
```

**Prayer (6 rows × 5 cols = 30 slots):**
```
 0   1   2   3   4
 5   6   7   8   9
10  11  12  13  14
15  16  17  18  19
20  21  22  23  24
25  26  27  28  29
```

## Registered UI Elements

### Grids

The following grids are registered from `config.json`:

| Name | Size | Description |
|------|------|-------------|
| `inventory` | 7×4 | Main inventory (28 slots) |
| `equipment` | 7×2 | Equipment tab (14 slots) |
| `prayer` | 6×5 | Prayer tab (30 prayers) |
| `spellbook` | 10×7 | Spellbook tab (70 spells) |
| `minimap` | 1×1 | Minimap detection |
| `chat` | 1×1 | Chat box detection |

### Buttons

Common buttons registered from `config.json`:

| Name | Description |
|------|-------------|
| `inventory_tab` | Inventory tab icon |
| `equipment_tab` | Equipment tab icon |
| `prayer_tab` | Prayer tab icon |
| `spellbook_tab` | Spellbook tab icon |
| `combat_tab` | Combat tab icon |
| `skills_tab` | Skills tab icon |
| `logout_tab` | Logout tab icon |
| `prayer_melee` | Melee prayer button |
| `prayer_magic` | Magic prayer button |
| `prayer_ranged` | Ranged prayer button |
| `autoretal_on` | Auto-retaliate on |
| `autoretal_off` | Auto-retaliate off |
| `runelite_logout` | RuneLite logout button |
| `runelite_settings_collapse` | Settings collapse |

## Troubleshooting

### No Elements Detected

**Possible causes:**
1. **Wrong window title** - Check `config.json` has correct `window_title`
2. **Game interface changed** - Templates may need updating
3. **Threshold too high** - Lower threshold in `config.json` (try 0.4 for grids)
4. **Wrong game client** - Templates are for RuneLite, may not work on official client
5. **Resolution mismatch** - Templates are for specific resolution

**Solutions:**
- Run `debug_ui_elements.py` to see what's detected
- Check logs for detection confidence scores
- Lower thresholds in `config.json` if confidence is close but below threshold
- Create new templates if game UI has changed

### Low Confidence Scores

If elements are detected but with low confidence (<0.7):

1. **Check template quality** - Templates in `src/osrsbot/images/bot/ui_templates/`
2. **Verify game settings** - Same zoom, brightness, interface scaling
3. **Update templates** - Capture new screenshots and create new templates
4. **Adjust thresholds** - Lower threshold if detection is consistent

### Wrong Slot Positions

If slots are misaligned:

1. **Check `border_offset`** - Pixels to exclude from template border
2. **Check `padding`** - Pixels to subtract from cell edges
3. **Verify template** - Ensure template matches current UI exactly
4. **Check grid size** - `rows` and `cols` must match actual grid

Example from `config.json`:
```json
"inventory": {
    "path": "src/osrsbot/images/bot/ui_templates/inventory_empty.PNG",
    "rows": 7,
    "cols": 4,
    "threshold": 0.40,
    "sticky": true,
    "padding": 0,
    "border_offset": 13
}
```

### Debug Images Not Saving

Ensure:
1. `ui_manager.enable_debug()` is called
2. `ui_debug/` folder exists and is writable
3. Sufficient disk space

## Advanced Usage

### Custom Debug Output Directory

```python
ui_manager.enable_debug("my_custom_debug_folder")
```

### Manual Debug Overlay

```python
# Capture screenshot
img_pil = runner.screen.capture()
img = cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)

# Draw overlay without saving
img_with_overlay = ui_manager.draw_debug_overlay(
    img,
    show_grids=True,
    show_buttons=True,
    show_slots=True,
    show_labels=True
)

# Display with OpenCV
import cv2 as cv
cv.imshow("Debug", img_with_overlay)
cv.waitKey(0)
```

### Selective Visualization

```python
# Only show grids, no buttons
img_debug = ui_manager.draw_debug_overlay(
    img,
    show_grids=True,
    show_buttons=False,
    show_slots=True,
    show_labels=True
)

# Only show buttons
img_debug = ui_manager.draw_debug_overlay(
    img,
    show_grids=False,
    show_buttons=True,
    show_slots=False,
    show_labels=True
)
```

### Syncing with TemplateMatchService

If you manually register templates, sync them to UIManager:

```python
# Register new template
template_service.register_grid(
    "my_custom_grid",
    "path/to/template.png",
    rows=5,
    cols=5,
    threshold=0.7
)

# Sync to UIManager
ui_manager.sync_from_template_service()

# Now accessible
grid = ui_manager.get_grid("my_custom_grid")
```

## Example: Debugging Bot Detection Issues

```python
from osrsbot.core.runner import ScriptRunner

runner = ScriptRunner("RuneLite - YourAccount")

# Enable debug
runner.ui_manager.enable_debug()

# Capture and detect
img_gray = runner.screen.capture_grayscale()
img_color = runner.screen.capture_color()

# Force fresh detection
results = runner.template_service.detect_all(img_gray, force=True)

# Print results
visible = runner.ui_manager.get_visible_elements()
print(f"\nDetected {len(visible['grids'])} grids:")
for name in visible['grids']:
    grid = runner.ui_manager.get_grid(name)
    print(f"  ✓ {name}: confidence={grid.last_confidence:.3f}")

print(f"\nDetected {len(visible['buttons'])} buttons:")
for name in visible['buttons']:
    button = runner.ui_manager.get_button(name)
    print(f"  ✓ {name}: confidence={button.last_confidence:.3f}")

# Save debug image
path = runner.ui_manager.save_debug_image(img_color, "detection_test")
print(f"\nSaved debug image: {path}")
```

## API Reference

### UIManager Methods

| Method | Description |
|--------|-------------|
| `enable_debug(output_dir=None)` | Enable debug mode, optionally set output directory |
| `disable_debug()` | Disable debug mode |
| `sync_from_template_service()` | Sync grids/buttons from TemplateMatchService |
| `get_visible_elements()` | Get dict of visible grids and buttons |
| `get_grid(name)` | Get specific grid by name |
| `get_button(name)` | Get specific button by name |
| `get_active_grid()` | Get currently active grid |
| `set_active_grid(name)` | Set active grid for context-aware ops |
| `draw_debug_overlay(img, ...)` | Draw red boxes on image |
| `save_debug_image(img, prefix, ...)` | Save annotated debug image |
| `get_element_info()` | Get detailed info about all elements |

### UIManager Properties

| Property | Type | Description |
|----------|------|-------------|
| `grids` | `Dict[str, UIElementGrid]` | Registered UI grids |
| `buttons` | `Dict[str, UIButton]` | Registered UI buttons |
| `active_grid_name` | `Optional[str]` | Name of active grid |
| `template_service` | `TemplateMatchService` | Reference to template service |
| `debug_enabled` | `bool` | Whether debug mode is enabled |
| `debug_output_dir` | `Path` | Output directory for debug images |

## Further Reading

- [models/ui_elements.py](src/osrsbot/models/ui_elements.py) - UIElement, UIElementGrid, UIButton classes
- [services/template_match_service.py](src/osrsbot/services/template_match_service.py) - Template matching implementation
- [core/ui_manager.py](src/osrsbot/core/ui_manager.py) - UIManager implementation
- [config.json](config.json) - Template configuration

## Support

If you encounter issues:
1. Run `debug_ui_elements.py` to see current detection
2. Check logs for error messages
3. Verify template paths and thresholds in `config.json`
4. Create new templates if game UI has changed
5. Report issues with debug screenshots showing the problem
