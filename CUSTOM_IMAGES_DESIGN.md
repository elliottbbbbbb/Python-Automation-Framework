# Custom Images System - Design Document

**Date:** 2026-01-12
**Feature:** Allow users to add custom template images alongside bundled images

---

## Overview

Allow users to create a `custom_images/` folder next to the .exe where they can add their own template images. The bot will:
1. Check custom images folder first (priority)
2. Fall back to bundled images if not found in custom
3. Support same path structure as bundled images
4. Allow config.json to reference custom images

---

## User Experience

### Setup
```
my_bot.exe
├── config.json (user editable)
├── custom_images/                    ← User creates this folder
│   ├── items/
│   │   ├── my_custom_potion.png     ← User adds custom images
│   │   └── rare_item.png
│   ├── ui_templates/
│   │   └── custom_button.png
│   └── npcs/
│       └── custom_npc_highlight.png
└── osrs_bot_debug.log
```

### Config Usage
```json
{
  "templates": {
    "ui_buttons": {
      "my_custom_button": {
        "path": "custom:ui_templates/custom_button.png",
        "threshold": 0.75
      }
    }
  },
  "custom": {
    "potions": {
      "my_potion": "custom:items/my_custom_potion.png"
    }
  }
}
```

**Syntax:**
- `"custom:path/to/image.png"` - Load from custom_images/ folder
- `"src/osrsbot/images/..."` - Load from bundled images (existing)
- `"path/to/image.png"` - Auto-detect (check custom first, then bundled)

---

## Implementation Design

### 1. Path Resolution Strategy

**Priority Order:**
1. **Custom images** (next to .exe or in project root)
2. **Bundled images** (inside .exe or src/osrsbot/images/)
3. **Error if not found in either**

### 2. New Path Resolver Function

**File:** `src/osrsbot/utils/path_helpers.py` (NEW FILE)

```python
"""
Path resolution utilities for template images.

Handles resolution of image paths in different environments:
- Development mode: src/osrsbot/images/
- .exe mode (bundled): sys._MEIPASS/osrsbot/images/
- .exe mode (custom): next to executable/custom_images/
"""

import sys
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ImagePathResolver:
    """
    Resolves template image paths with support for custom images.

    Path Resolution Order:
    1. Custom images folder (user-provided)
    2. Bundled images (included with bot)
    3. Error if not found
    """

    def __init__(self):
        """Initialize path resolver with base directories."""
        self.is_frozen = getattr(sys, "frozen", False)

        # Custom images location (next to .exe or in project root)
        if self.is_frozen:
            self.custom_images_dir = Path(sys.executable).parent / "custom_images"
        else:
            self.custom_images_dir = Path.cwd() / "custom_images"

        # Bundled images location
        if self.is_frozen:
            self.bundled_images_dir = Path(sys._MEIPASS) / "osrsbot" / "images"
        else:
            self.bundled_images_dir = Path(__file__).parent.parent / "images"

    def resolve(self, image_path: str) -> Path:
        """
        Resolve image path to absolute path.

        Args:
            image_path: Path to image, one of:
                - "custom:items/my_item.png" (explicit custom)
                - "src/osrsbot/images/items/item.png" (explicit bundled)
                - "items/my_item.png" (auto-detect)

        Returns:
            Absolute Path to image file

        Raises:
            FileNotFoundError: If image not found in any location
        """
        # Handle explicit custom: prefix
        if image_path.startswith("custom:"):
            relative_path = image_path.replace("custom:", "", 1)
            return self._resolve_custom(relative_path)

        # Handle explicit bundled path
        if image_path.startswith("src/osrsbot/images/"):
            relative_path = image_path.replace("src/osrsbot/images/", "", 1)
            return self._resolve_bundled(relative_path)

        # Auto-detect: try custom first, then bundled
        return self._resolve_auto(image_path)

    def _resolve_custom(self, relative_path: str) -> Path:
        """
        Resolve path in custom images folder.

        Args:
            relative_path: Path relative to custom_images/ (e.g., "items/my_item.png")

        Returns:
            Absolute Path to custom image

        Raises:
            FileNotFoundError: If not found in custom folder
        """
        # Normalize path separators (Windows compatibility)
        normalized_path = relative_path.replace("\\", "/")
        absolute_path = self.custom_images_dir / normalized_path

        if absolute_path.exists():
            logger.debug(f"Custom image found: {absolute_path}")
            return absolute_path

        raise FileNotFoundError(
            f"Custom image not found: {relative_path}\n"
            f"Expected location: {absolute_path}\n"
            f"Make sure the file exists in: {self.custom_images_dir}"
        )

    def _resolve_bundled(self, relative_path: str) -> Path:
        """
        Resolve path in bundled images folder.

        Args:
            relative_path: Path relative to images/ (e.g., "bot/items/overload.png")

        Returns:
            Absolute Path to bundled image

        Raises:
            FileNotFoundError: If not found in bundled images
        """
        # Normalize path separators
        normalized_path = relative_path.replace("\\", "/")
        absolute_path = self.bundled_images_dir / normalized_path

        if absolute_path.exists():
            logger.debug(f"Bundled image found: {absolute_path}")
            return absolute_path

        raise FileNotFoundError(
            f"Bundled image not found: {relative_path}\n"
            f"Expected location: {absolute_path}"
        )

    def _resolve_auto(self, image_path: str) -> Path:
        """
        Auto-detect image location (custom first, then bundled).

        Args:
            image_path: Path without prefix (e.g., "items/my_item.png")

        Returns:
            Absolute Path to image

        Raises:
            FileNotFoundError: If not found in either location
        """
        # Normalize path separators
        normalized_path = image_path.replace("\\", "/")

        # Try custom first
        custom_path = self.custom_images_dir / normalized_path
        if custom_path.exists():
            logger.info(f"Using custom image: {custom_path}")
            return custom_path

        # Try bundled
        # Strip "src/osrsbot/" prefix if present
        if normalized_path.startswith("src/osrsbot/"):
            normalized_path = normalized_path.replace("src/osrsbot/", "", 1)

        # Remove "images/" prefix if present
        if normalized_path.startswith("images/"):
            normalized_path = normalized_path.replace("images/", "", 1)

        bundled_path = self.bundled_images_dir / normalized_path
        if bundled_path.exists():
            logger.debug(f"Using bundled image: {bundled_path}")
            return bundled_path

        # Not found in either location
        raise FileNotFoundError(
            f"Image not found: {image_path}\n"
            f"Checked locations:\n"
            f"  1. Custom: {custom_path}\n"
            f"  2. Bundled: {bundled_path}\n"
            f"Please add the image to custom_images/ folder or check the path."
        )


# Global resolver instance
_resolver = None

def get_image_path_resolver() -> ImagePathResolver:
    """Get or create the global image path resolver."""
    global _resolver
    if _resolver is None:
        _resolver = ImagePathResolver()
    return _resolver


def resolve_image_path(image_path: str) -> Path:
    """
    Convenience function to resolve an image path.

    Args:
        image_path: Path to image file

    Returns:
        Absolute Path to image

    Raises:
        FileNotFoundError: If image not found
    """
    resolver = get_image_path_resolver()
    return resolver.resolve(image_path)
```

---

### 3. Update Existing Path Resolution

**Files to Update:**
1. `src/osrsbot/queries/bank_queries.py`
2. `src/osrsbot/models/ui_elements.py`

**Replace current `_resolve_template_path()` logic with:**

```python
from osrsbot.utils.path_helpers import resolve_image_path

# Old code:
resolved_path = _resolve_template_path(template_path)

# New code:
resolved_path = resolve_image_path(template_path)
```

---

### 4. Config.json Support

**Add custom images section to config:**

```json
{
  "custom_images": {
    "enabled": true,
    "folder": "custom_images",
    "examples": {
      "my_custom_potion": "custom:items/my_custom_potion.png",
      "rare_item": "items/rare_item.png"
    }
  },

  "templates": {
    "ui_grids": {
      "inventory": {
        "path": "src/osrsbot/images/bot/ui_templates/inventory_empty.PNG",
        "rows": 7,
        "cols": 4
      }
    },
    "ui_buttons": {
      "my_custom_button": {
        "path": "custom:ui_templates/my_button.png",
        "threshold": 0.75
      }
    }
  }
}
```

---

### 5. User Documentation

**Add to README or docs folder:**

```markdown
# Custom Images Guide

## Overview
You can add your own custom template images that the bot can use for detection and clicking.

## Setup

1. Create a `custom_images/` folder next to your bot.exe:
   ```
   my_bot.exe
   custom_images/    ← Create this folder
   ```

2. Add your image files following the same structure as bundled images:
   ```
   custom_images/
   ├── items/
   │   └── my_item.png
   ├── ui_templates/
   │   └── my_button.png
   └── npcs/
       └── my_npc.png
   ```

3. Reference them in config.json:
   ```json
   {
     "custom": {
       "my_item": "custom:items/my_item.png"
     }
   }
   ```

## Path Syntax

Three ways to reference images:

1. **Explicit Custom** (from custom_images/ folder):
   ```
   "custom:items/my_item.png"
   ```

2. **Explicit Bundled** (from bot's included images):
   ```
   "src/osrsbot/images/bot/items/overload.png"
   ```

3. **Auto-Detect** (checks custom first, then bundled):
   ```
   "items/my_item.png"
   ```

## Image Guidelines

- **Format**: PNG recommended (supports transparency)
- **Size**: Match the in-game size (typically 30-40 pixels)
- **Quality**: Take screenshots with same resolution as your game client
- **Naming**: Use descriptive names (e.g., `super_restore_4.png`)

## Folder Structure

Recommended structure matching bundled images:

```
custom_images/
├── items/              # Inventory items
├── ui_templates/       # UI buttons, panels
├── npcs/              # NPC highlights
├── prayers/           # Prayer icons
├── spellbooks/        # Spell icons
└── bank/              # Bank interface elements
```

## Tips

1. **Capture Method**: Use Windows Snipping Tool or ShareX
2. **Exact Match**: Capture exactly as it appears in-game
3. **Test First**: Use the Template Test script to verify detection
4. **Threshold**: Lower threshold (0.6-0.7) for flexible matching
5. **Multiple Variations**: Create variants for different states (e.g., lit/unlit)

## Example Use Cases

### Custom Item (Rare Drop)
```json
{
  "custom": {
    "rare_drop": {
      "path": "custom:items/twisted_bow.png",
      "threshold": 0.75
    }
  }
}
```

Then in your script:
```python
self.actions.click_template("custom:items/twisted_bow.png", "Twisted Bow")
```

### Custom NPC Marker
```json
{
  "custom": {
    "my_npc": "custom:npcs/specific_goblin.png"
  }
}
```

### Override Bundled Image
Just name your custom image the same and use auto-detect:
```
custom_images/items/overload_potion.png  ← Custom version
```

Config:
```json
{
  "path": "items/overload_potion.png"  ← Auto-detect finds custom first!
}
```
```

---

## Implementation Checklist

### Phase 1: Core Functionality
- [ ] Create `src/osrsbot/utils/path_helpers.py` with `ImagePathResolver`
- [ ] Update `bank_queries.py` to use new resolver
- [ ] Update `ui_elements.py` to use new resolver
- [ ] Add unit tests for path resolution

### Phase 2: Config Support
- [ ] Add `custom_images` section to default config
- [ ] Update config loading to handle `custom:` prefix
- [ ] Add validation for custom image paths

### Phase 3: User Experience
- [ ] Auto-create `custom_images/` folder on first run
- [ ] Add example images with README
- [ ] Add logging for which images are being used (custom vs bundled)
- [ ] Add error messages that guide users to fix path issues

### Phase 4: Documentation
- [ ] Create CUSTOM_IMAGES_GUIDE.md
- [ ] Add examples to README
- [ ] Create video tutorial
- [ ] Add to in-app help text

---

## Example Usage Scenarios

### Scenario 1: Custom Potion (User-Specific)
User has a custom potion with unique coloring:

```python
# Script code
self.actions.click_template(
    "custom:items/my_special_potion.png",
    "Special Potion"
)
```

### Scenario 2: Custom NPC Markers
User's RuneLite has specific NPC colors:

```json
{
  "custom": {
    "npcs": {
      "my_target": "custom:npcs/cyan_cow.png"
    }
  }
}
```

### Scenario 3: Override Bundled Template
User's game client renders UI differently:

```
custom_images/ui_templates/inventory_empty.PNG  ← User's version
```

Bot automatically uses custom version when referenced:
```json
{
  "templates": {
    "ui_grids": {
      "inventory": {
        "path": "ui_templates/inventory_empty.PNG"  ← Auto-resolves to custom!
      }
    }
  }
}
```

---

## Benefits

1. **Flexibility**: Users can customize without modifying bot code
2. **Client Compatibility**: Support different RuneLite themes/plugins
3. **Custom Scripts**: Users can create scripts with unique images
4. **Override System**: Easy to fix detection issues without rebuilding .exe
5. **No Conflicts**: Custom images don't affect bundled images

---

## Technical Notes

### Performance Impact
- Minimal: Only checks file existence (2 filesystem calls max)
- Custom images are checked first (most common use case)
- Path resolution is cached within services

### Security
- Custom images folder is read-only for bot
- No code execution from images (only image data)
- Path traversal protection (no `../` allowed)

### Compatibility
- Works in both dev mode and .exe mode
- Backward compatible (existing paths still work)
- No changes to existing scripts required

---

## Future Enhancements

1. **Image Validation**: Check image format/size on load
2. **Hot Reload**: Detect when custom images change
3. **Image Library**: Share custom images between users
4. **Config UI**: Visual editor for adding custom images
5. **Template Variants**: Support multiple versions of same template

---

**End of Design Document**
