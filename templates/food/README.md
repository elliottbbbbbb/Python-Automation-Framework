# Food Templates

This directory contains template images for food items used by the `eat()` method.

## Configured Food Items

The following food items are configured in `config.json`:

- **manta_ray** - Manta ray (22 HP heal)
- **shark** - Shark (20 HP heal)
- **anglerfish** - Anglerfish (3-22 HP heal, can overheal)
- **karambwan** - Cooked karambwan (18 HP heal, combo food)
- **lobster** - Lobster (12 HP heal)
- **swordfish** - Swordfish (14 HP heal)

## Creating Food Templates

### Steps

1. **Open RuneLite** with your inventory containing the food
2. **Take a screenshot** of just the food icon in inventory
3. **Crop tightly** around the food icon (usually ~32x32 pixels)
4. **Save as PNG** with the configured filename

### Example: Manta Ray

1. Put manta ray in inventory
2. Take screenshot
3. Crop to just the manta ray icon
4. Save as `templates/food/manta_ray.png`

### Tips

- Crop as tightly as possible around the icon
- Use the exact game brightness you'll use when running bot
- Test threshold values (0.7-0.8 usually works well)
- Higher threshold = stricter matching, less false positives
- Lower threshold = more lenient, finds degraded/partial matches

## How It Works

The `actions.eat(food_name)` method:

1. Registers the food template from config
2. Detects the inventory grid
3. Searches each inventory slot for the food icon
4. Clicks the first slot containing matching food

## Usage in Scripts

```python
# Simple usage
actions.eat("manta_ray")

# With error handling
if not actions.eat("shark"):
    logger.error("Failed to find/eat shark")
```

## Troubleshooting

### Food not detected

1. **Check threshold** - Lower it in config (try 0.7 or 0.65)
2. **Verify template** - Ensure it exactly matches in-game icon
3. **Check inventory visibility** - Inventory tab must be open
4. **Test template size** - Should match game icon size exactly

### Wrong item clicked

1. **Increase threshold** - Make matching stricter (try 0.8 or 0.85)
2. **Recrop template** - Ensure no extra pixels around icon
3. **Check similar items** - Different food can look similar

### Food detected but not clicked

1. **Check window bounds** - Ensure window tracking is working
2. **Verify inventory registration** - Check logs for inventory detection
3. **Test manually** - Try `actions.click_inventory_slot(1)` first
