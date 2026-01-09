# UI Manager Integration Summary

## What Was Done

Successfully integrated UIManager into the OSRS bot framework and created a comprehensive debug visualization system with red boxes showing all detected UI elements.

## Files Modified

### 1. [src/osrsbot/services/ui_manager_service.py](src/osrsbot/services/ui_manager_service.py)
**Status:** Enhanced with debug visualization capabilities

**New Features:**
- `enable_debug()` / `disable_debug()` - Toggle debug mode
- `draw_debug_overlay()` - Draw red boxes on screenshots
- `save_debug_image()` - Save annotated images to disk
- `sync_from_template_service()` - Auto-sync templates
- `get_visible_elements()` - Query visible UI elements
- `get_element_info()` - Get detailed element information

**Debug Visualization Features:**
- Thick red boxes (3px) around grid boundaries
- Thin red boxes (1px) around individual grid slots
- Medium red boxes (2px) around buttons
- Green dots showing click center points
- Yellow text showing slot numbers
- Red text showing element names and confidence scores

### 2. [src/osrsbot/core/runner.py](src/osrsbot/core/runner.py)
**Status:** Modified to initialize UIManager

**Changes:**
- Added `from osrsbot.services.ui_manager_service import UIManager` import
- Added UIManager initialization after TemplateMatchService (lines 162-169)
- Syncs grids and buttons from TemplateMatchService automatically
- Passes `ui_manager` to GameActions (line 285)
- Logs number of registered grids and buttons

### 3. [src/osrsbot/commands/game_actions.py](src/osrsbot/commands/game_actions.py)
**Status:** Modified to accept UIManager

**Changes:**
- Added `ui_manager` parameter to `__init__()` (line 65)
- Stored as `self.ui_manager` (line 77)
- Now accessible to all bot scripts via `self.actions.ui_manager`

## Files Created

### 1. [debug_ui_elements.py](debug_ui_elements.py)
**Purpose:** Standalone debug tool for visualizing UI detection

**Features:**
- Interactive visualization with OpenCV window
- Real-time detection results printed to console
- Automatic saving of debug images to `ui_debug/`
- Keyboard controls for toggling visualization options
- Summary of detected vs not-detected elements
- Confidence scores for all detections

**Usage:**
```bash
python debug_ui_elements.py
```

### 2. [example_ui_debug_bot.py](example_ui_debug_bot.py)
**Purpose:** Example bot demonstrating UI debug integration

**Features:**
- Shows how to enable debug mode in bot scripts
- Captures screenshots and detects UI elements
- Saves annotated debug images per cycle
- Prints detailed detection results to console
- Example of checking specific UI elements
- Includes press 'q' to exit functionality

**Usage:**
```bash
python example_ui_debug_bot.py
```

### 3. [UI_DEBUG_GUIDE.md](UI_DEBUG_GUIDE.md)
**Purpose:** Comprehensive user guide for UI debug system

**Contents:**
- Quick start guide
- Keyboard controls reference
- Integration examples for bot scripts
- Understanding visualizations (colors, scores, numbering)
- List of all registered UI elements
- Troubleshooting common issues
- Advanced usage patterns
- Complete API reference

### 4. [UI_INTEGRATION_SUMMARY.md](UI_INTEGRATION_SUMMARY.md) (This File)
**Purpose:** Summary of changes for developers

## How It Works

### Architecture

```
ScriptRunner
├── TemplateMatchService (detects UI via template matching)
├── UIManager (wraps template service + adds debug)
│   ├── grids: Dict[str, UIElementGrid]
│   ├── buttons: Dict[str, UIButton]
│   └── debug methods
├── GameActions (has ui_manager reference)
└── Bot Scripts (access via self.actions.ui_manager)
```

### Detection Flow

1. **Initialization:**
   - Runner creates TemplateMatchService
   - Runner creates UIManager with reference to TemplateMatchService
   - UIManager syncs all registered templates
   - UIManager passed to GameActions

2. **Runtime:**
   - Bot captures screenshot (grayscale for detection)
   - TemplateMatchService detects UI elements via template matching
   - Elements marked as visible/invisible with confidence scores
   - UIManager queries TemplateMatchService for visible elements

3. **Debug Visualization:**
   - Bot captures color screenshot
   - UIManager draws red boxes on screenshot
   - Annotates with labels, confidence scores, slot numbers
   - Saves to `ui_debug/` directory with timestamp

### Debug Visualization Legend

| Visual Element | Meaning |
|----------------|---------|
| Thick red box (3px) | Grid boundary (inventory, prayer, etc.) |
| Thin red box (1px) | Individual grid slot |
| Medium red box (2px) | Button element |
| Green dot | Center point where bot clicks |
| Yellow text (small) | Slot number (0-indexed) |
| Red text (large) | Element name and confidence score |

## Usage Examples

### Enable Debug in Your Bot

```python
class MyBot(Bot):
    def run_cycle(self, bank_location: str, run_number: int):
        # Enable debug
        if self.actions.ui_manager:
            self.actions.ui_manager.enable_debug()

        # Your bot logic...

        # Save debug image
        img_pil = self.state.screen.capture()
        img = cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)
        if self.actions.ui_manager:
            self.actions.ui_manager.save_debug_image(img, "my_bot")
```

### Check UI Element Visibility

```python
# Check if inventory is detected
inventory = self.actions.ui_manager.get_grid("inventory")
if inventory and inventory.visible:
    print(f"Inventory found with confidence {inventory.last_confidence:.3f}")
    print(f"Has {len(inventory.elements)} slots")

# Check if prayer tab is detected
prayer_tab = self.actions.ui_manager.get_button("prayer_tab")
if prayer_tab and prayer_tab.visible:
    print(f"Prayer tab at {prayer_tab.element.center}")
```

### Get All Visible Elements

```python
visible = self.actions.ui_manager.get_visible_elements()
print(f"Visible grids: {visible['grids']}")
print(f"Visible buttons: {visible['buttons']}")
```

## Testing

### Test 1: Run Debug Script
```bash
python debug_ui_elements.py
```
**Expected:** Window opens showing game with red boxes around detected UI elements

### Test 2: Run Example Bot
```bash
python example_ui_debug_bot.py
```
**Expected:** Bot runs 3 cycles, saves debug images to `ui_debug/example_bot/`

### Test 3: Verify Integration
```bash
python -c "from osrsbot.core.runner import ScriptRunner; r = ScriptRunner('RuneLite'); print(f'UIManager has {len(r.ui_manager.grids)} grids and {len(r.ui_manager.buttons)} buttons')"
```
**Expected:** Prints number of registered UI elements

## Registered UI Elements

Based on `config.json`, the following elements are automatically registered:

### Grids (6 total)
- `inventory` - 7×4 grid (28 slots)
- `equipment` - 7×2 grid (14 slots)
- `prayer` - 6×5 grid (30 slots)
- `spellbook` - 10×7 grid (70 slots)
- `minimap` - Minimap detection
- `chat` - Chat box detection

### Buttons (~15+ total)
- Tab buttons: inventory, equipment, prayer, spellbook, combat, skills, logout
- Prayer buttons: melee, magic, ranged
- Combat: autoretal_on, autoretal_off
- Settings: runelite_logout, runelite_settings_collapse
- Bank: presets
- And more...

## Benefits

### For Bot Development
- **Visual debugging** - See exactly what bot detects
- **Faster debugging** - Identify detection issues immediately
- **Better testing** - Verify templates work before running bot
- **Documentation** - Screenshots show bot's "vision"

### For Users
- **Transparency** - Understand what bot sees
- **Troubleshooting** - Diagnose detection failures
- **Verification** - Confirm bot is working correctly
- **Learning** - Understand template matching system

## Performance Impact

- **Minimal** - Debug visualization only runs when explicitly enabled
- **Optional** - Can be completely disabled for production runs
- **Efficient** - Uses same detection results, just adds drawing
- **Configurable** - Can disable specific overlays (grids/buttons/slots/labels)

## Future Enhancements

Possible additions:
1. Real-time overlay window (without saving to disk)
2. Detection confidence heatmaps
3. Failed detection visualization (show where bot looked)
4. Template matching result visualization (correlation maps)
5. Interactive overlay editing (adjust padding/offsets live)
6. Recording mode (save video of detections over time)
7. Comparison mode (compare current vs expected detections)
8. Performance metrics (detection time, FPS, etc.)

## Backward Compatibility

All changes are **100% backward compatible**:
- Existing bots work without modification
- `ui_manager` parameter is optional in GameActions
- Debug features are opt-in (disabled by default)
- No breaking changes to any APIs

## Integration Checklist

- [x] UIManager class with debug visualization methods
- [x] Integration into ScriptRunner
- [x] Integration into GameActions
- [x] Standalone debug script (debug_ui_elements.py)
- [x] Example bot script (example_ui_debug_bot.py)
- [x] User guide (UI_DEBUG_GUIDE.md)
- [x] Developer summary (this file)
- [x] Red box visualization for grids
- [x] Red box visualization for buttons
- [x] Green dots for center points
- [x] Slot numbering overlay
- [x] Confidence score labels
- [x] Automatic image saving
- [x] Configurable output directory
- [x] Toggle options for visualization elements

## Conclusion

The UIManager integration provides a powerful debugging tool that makes template matching transparent and easy to troubleshoot. The red box visualization clearly shows what the bot detects, where it will click, and how confident the detections are. This will significantly speed up bot development and make troubleshooting detection issues much easier.

All code is production-ready, well-documented, and backward compatible with existing scripts.
