# Templates Directory

This directory contains template images used for UI element detection.

## Setup

Add your template images here for the template matching system to detect game UI elements.

### Required Templates (as configured in config.json)

**UI Grids:**
- `inventory_grid.png` - Full inventory grid (7 rows × 4 cols)
- `prayer_tab.png` - Prayer tab grid (6 rows × 5 cols)
- `equipment_slots.png` - Equipment slots (4 rows × 3 cols)

**UI Buttons:**
- `prayer_button.png` - Prayer tab button
- `inventory_button.png` - Inventory tab button
- `equipment_button.png` - Equipment tab button
- `logout_button.png` - Logout button
- `special_attack.png` - Special attack button

**Food Items:** (in `food/` subdirectory)
- `food/manta_ray.png` - Manta ray icon
- `food/shark.png` - Shark icon
- `food/anglerfish.png` - Anglerfish icon
- `food/karambwan.png` - Cooked karambwan icon
- `food/lobster.png` - Lobster icon
- `food/swordfish.png` - Swordfish icon

See [food/README.md](food/README.md) for detailed food template instructions.

## Creating Templates

1. **Take a screenshot** of the RuneLite client
2. **Crop the UI element** you want to detect
3. **Save as PNG** with the filename matching config.json
4. **Test the threshold** value (0.65-0.75 typically works)

### Tips

- Use consistent game brightness settings
- Crop tightly around the element
- For grids, include the entire grid area
- Avoid elements with changing content (like item icons)
- Test at different zoom levels

## Example

To create an inventory template:
1. Open RuneLite with your inventory visible
2. Take screenshot (Alt+PrintScreen or use Snipping Tool)
3. Crop to show just the inventory grid
4. Save as `templates/inventory_grid.png`
5. Configure in `config.json` with rows=7, cols=4

See [docs/TEMPLATE_MATCHING_GUIDE.md](../docs/TEMPLATE_MATCHING_GUIDE.md) for detailed instructions.
