# UI Debug Quick Reference

## Quick Start

```bash
# 1. Run standalone debug tool
python debug_ui_elements.py

# 2. Run example bot
python example_ui_debug_bot.py
```

## In Your Bot Code

```python
# Enable debug mode
if self.actions.ui_manager:
    self.actions.ui_manager.enable_debug()

# Capture and detect
img_pil = self.state.screen.capture()
img = cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)

# Save debug image with red boxes
self.actions.ui_manager.save_debug_image(img, "my_debug")
```

## Check UI Elements

```python
# Check inventory
inventory = self.actions.ui_manager.get_grid("inventory")
if inventory and inventory.visible:
    print(f"Inventory: {len(inventory.elements)} slots, confidence={inventory.last_confidence:.3f}")

# Check prayer tab
prayer_tab = self.actions.ui_manager.get_button("prayer_tab")
if prayer_tab and prayer_tab.visible:
    print(f"Prayer tab at {prayer_tab.element.center}")

# Get all visible elements
visible = self.actions.ui_manager.get_visible_elements()
print(f"Visible: {visible['grids']} grids, {visible['buttons']} buttons")
```

## Visualization Legend

- **Red box (thick)** = Grid boundary
- **Red box (thin)** = Individual slot
- **Green dot** = Click center point
- **Yellow text** = Slot number
- **Red text** = Element name + confidence

## Common Grids

| Name | Size | Slots |
|------|------|-------|
| inventory | 7×4 | 28 |
| equipment | 7×2 | 14 |
| prayer | 6×5 | 30 |
| spellbook | 10×7 | 70 |

## Debug Controls

### debug_ui_elements.py
- **q** = Refresh detection
- **ESC** = Exit
- **s** = Toggle slot numbers
- **g** = Toggle grid boxes
- **b** = Toggle button boxes
- **l** = Toggle labels

## Output Locations

- **ui_debug/** = Default debug image directory
- **ui_debug/example_bot/** = Example bot output
- Filenames include timestamp: `ui_detection_20260108_143025_123.png`

## Troubleshooting

### No elements detected?
1. Check window_title in config.json
2. Lower thresholds (try 0.4 for grids)
3. Run debug_ui_elements.py to see what's detected

### Low confidence?
1. Update templates in src/osrsbot/images/bot/
2. Match game settings (zoom, brightness)
3. Check resolution matches templates

### Wrong slot positions?
1. Adjust border_offset in config.json
2. Adjust padding in config.json
3. Verify template matches current UI

## API Quick Reference

```python
# UIManager methods
ui_manager.enable_debug(output_dir=None)
ui_manager.disable_debug()
ui_manager.sync_from_template_service()
ui_manager.get_visible_elements() -> Dict[str, List[str]]
ui_manager.get_grid(name) -> Optional[UIElementGrid]
ui_manager.get_button(name) -> Optional[UIButton]
ui_manager.draw_debug_overlay(img, ...) -> np.ndarray
ui_manager.save_debug_image(img, prefix, ...) -> Optional[str]
ui_manager.get_element_info() -> Dict[str, Dict]

# Grid properties
grid.visible -> bool
grid.last_confidence -> float
grid.num_rows -> int
grid.num_cols -> int
grid.elements -> List[UIElement]
grid.threshold -> float

# Button properties
button.visible -> bool
button.last_confidence -> float
button.element -> Optional[UIElement]
button.threshold -> float

# Element properties
element.center -> Tuple[int, int]
element.center_x -> int
element.center_y -> int
element.bbox -> Tuple[int, int, int, int]
element.width -> int
element.height -> int
```

## Full Documentation

- [UI_DEBUG_GUIDE.md](UI_DEBUG_GUIDE.md) - Complete user guide
- [UI_INTEGRATION_SUMMARY.md](UI_INTEGRATION_SUMMARY.md) - Technical overview
- [src/osrsbot/core/ui_manager.py](src/osrsbot/core/ui_manager.py) - Source code
