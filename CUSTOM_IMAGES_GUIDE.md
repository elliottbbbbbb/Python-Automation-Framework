# Custom Images Guide

This guide explains how to use custom template images with the OSRS Automation Framework.

## Overview

You can use your own custom images for template matching in three ways:

1. **Custom user images** - Stored in `user_images/` folder (recommended for end users)
2. **Short bundled paths** - Auto-prefixed with `src/osrsbot/`
3. **Full bundled paths** - Full path to bundled images

## 1. Custom User Images (Recommended)

### For End Users (.exe)

When you run the bot as an `.exe`, a `user_images/` folder will be automatically created next to the executable.

**Folder structure:**
```
my_bot.exe
user_images/           <- Created automatically
  ├── my_custom_item.png
  ├── special_npc.png
  └── custom_button.png
```

**Usage in code:**
```python
# Click a custom template from user_images folder
self.actions.click_template("custom:my_custom_item.png", "my item")
self.actions.click_template("custom:special_npc.png", "special NPC")
```

### For Developers

In development mode, the `user_images/` folder is created in the project root:

```
OSRS-Automation-Framework/
  ├── src/
  ├── user_images/       <- Created in project root
  │   └── my_test.png
  └── ...
```

**Same usage:**
```python
self.actions.click_template("custom:my_test.png", "test item")
```

## 2. Short Bundled Paths

You can use short paths that get automatically prefixed with `src/osrsbot/`:

```python
# These are equivalent:
self.actions.click_template("images/bot/items/overload_potion.png", "overload")
self.actions.click_template("src/osrsbot/images/bot/items/overload_potion.png", "overload")
```

## 3. Full Bundled Paths

Use the full path for bundled images:

```python
self.actions.click_template("src/osrsbot/images/bot/items/absorption_potion.png", "absorption")
```

## Path Format Comparison

| Format | Example | When to Use |
|--------|---------|-------------|
| **custom:** | `custom:my_item.png` | User-provided custom images |
| **Short path** | `images/bot/items/potion.png` | Convenience for bundled images |
| **Full path** | `src/osrsbot/images/bot/items/potion.png` | Explicit bundled images |

## How It Works

### In Development Mode
- `custom:` paths resolve to `<project_root>/user_images/`
- Other paths resolve to `<project_root>/src/osrsbot/...`

### In .exe Mode
- `custom:` paths resolve to `<exe_directory>/user_images/`
- Other paths resolve to bundled `_MEIPASS` directory

## Creating Custom Templates

1. **Screenshot the item/button/NPC** in RuneLite
2. **Crop the image** to just the element you want to detect
3. **Save as PNG** with a descriptive name
4. **Place in user_images folder** (created automatically)
5. **Use in code** with `custom:` prefix

## Example: Adding a Custom Item

### Step 1: Create the template
```
user_images/
  └── twisted_bow.png    <- Your screenshot
```

### Step 2: Use in your script
```python
class MyCustomBot(StateMachineBot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.TWISTED_BOW_TEMPLATE = "custom:twisted_bow.png"

    def equip_bow(self):
        if self.actions.click_template(self.TWISTED_BOW_TEMPLATE, "twisted bow"):
            logger.info("Equipped twisted bow")
            return True
        return False
```

## Multi-Template Support for Better Accuracy

### The Resolution/Zoom Problem

Template matching requires **exact pixel-perfect matching**. If your game zoom or resolution changes, templates won't match. To solve this, you can provide **multiple templates** at different zoom levels:

```python
# Single template (simple but may fail at different zooms)
self.actions.click_template("custom:potion.png", "potion")

# Multiple templates (more reliable across zoom levels)
self.actions.click_template([
    "custom:potion_zoom1.png",  # Zoomed in
    "custom:potion_zoom2.png",  # Normal
    "custom:potion_zoom3.png",  # Zoomed out
], "potion")
```

The bot will try all templates and use the best match!

### Performance Impact

- **Single template**: ~1-5ms
- **3 templates**: ~3-15ms
- **5 templates**: ~5-25ms

This is **negligible** compared to game ticks (600ms) and human reaction time.

### When to Use Multiple Templates

✅ **Use multiple templates when:**
- Users may have different zoom levels
- Camera angle changes during gameplay
- Item appears in different states (4-dose, 3-dose, 2-dose, 1-dose potions)
- NPCs can be viewed from different angles

❌ **Single template is fine when:**
- Everyone uses the same fixed zoom/settings
- Template is a UI button that never changes
- Speed is critical and you control the environment

## Tips for Creating Good Templates

1. **Use RuneLite** for consistent graphics
2. **Crop tightly** around the item/button
3. **Avoid UI elements** that change (highlighted vs non-highlighted)
4. **Test different thresholds** (default is 0.7)
5. **Use PNG format** for best quality
6. **For multi-template**: Take screenshots at min/normal/max zoom levels

## Troubleshooting

### Template not found
- Check the file exists in `user_images/`
- Verify the filename matches exactly (case-sensitive)
- Make sure you're using the `custom:` prefix

### Template found but wrong item clicked
- Crop the template more precisely
- Increase the threshold: `click_template("custom:item.png", "item", threshold=0.8)`

### Template never matches
- Decrease the threshold: `click_template("custom:item.png", "item", threshold=0.6)`
- Verify the game graphics settings match when you took the screenshot

## Advanced: Subfolders

You can organize custom images in subfolders:

```
user_images/
  ├── items/
  │   ├── twisted_bow.png
  │   └── tbow_spec.png
  └── npcs/
      └── vorkath.png
```

**Usage:**
```python
self.actions.click_template("custom:items/twisted_bow.png", "twisted bow")
self.actions.click_template("custom:npcs/vorkath.png", "vorkath")
```

## Distribution Note

When distributing your bot to other users:
- The `user_images/` folder is **NOT** included in the .exe
- Users must provide their own screenshots
- This is intentional - ensures users take their own images with their settings
- Include instructions telling users which templates they need to create
