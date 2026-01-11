"""
Extract individual item images from your inventory for comparison.

This will help you see if the wiki templates match your actual items.

Usage:
    1. Have RuneLite open with inventory visible
    2. Run: python tools/extract_inventory_items.py
    3. Check src/osrsbot/images/extracted_items/ for results
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2
import numpy as np
from PIL import Image
from osrsbot.services.screen_service import ScreenService
from osrsbot.services.template_match_service import TemplateMatchService
from osrsbot.models.config import Config

def main():
    print("Extracting inventory items from your game...")

    # Initialize services
    config = Config()
    window_title = config.get("window_title", default="RuneLite")

    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            print(f"ERROR: Could not find window: {window_title}")
            return 1

        window = windows[0]
        print(f"Found window: {window.title}")

    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    # Capture screenshot
    screen = ScreenService(window_getter=lambda: (window.left, window.top, window.width, window.height))
    img_color = screen.capture()
    img_array = np.array(img_color)
    img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    # Initialize template service with config
    template_service = TemplateMatchService()

    # Register inventory grid template directly (use absolute path from script location)
    script_dir = Path(__file__).parent.parent
    template_path = script_dir / "src" / "osrsbot" / "images" / "bot" / "ui_templates" / "inventory_empty.PNG"

    template_service.register_grid(
        name="inventory",
        template_path=str(template_path),
        num_rows=7,
        num_cols=4,
        threshold=0.30,
        sticky=True,
        border_offset=20,
        padding=0
    )

    print("Registered inventory grid template")

    detected = template_service.detect_grid("inventory", img_gray, force=True)

    if not detected:
        print("ERROR: Could not detect inventory grid")
        return 1

    grid = template_service.get_grid("inventory")
    print(f"Inventory grid detected at {grid.detected_bbox}")
    print(f"Grid has {len(grid.elements) if grid.elements else 0} slots")

    # Create output directory
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "src" / "osrsbot" / "images" / "extracted_items"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract each slot
    print(f"\nExtracting items to {output_dir}/")
    print("=" * 60)

    extracted_count = 0

    for slot_idx in range(28):
        element = grid.get_element(slot_idx)
        if not element:
            continue

        # Crop slot region (grayscale)
        x0, y0, x1, y1 = element.bbox
        slot_image_gray = img_gray[y0:y1, x0:x1]

        # Also crop color version
        slot_image_color = img_array[y0:y1, x0:x1]

        # Check if slot has item (simple variance check)
        variance = np.std(slot_image_gray)

        if variance > 10:  # Likely has an item
            # Save both grayscale and color versions
            output_gray = output_dir / f"slot_{slot_idx:02d}_gray.png"
            output_color = output_dir / f"slot_{slot_idx:02d}_color.png"

            # Convert grayscale to PIL Image
            img_gray_pil = Image.fromarray(slot_image_gray)
            img_gray_pil.save(output_gray)

            # Convert color to PIL Image (RGB)
            img_color_pil = Image.fromarray(slot_image_color)
            img_color_pil.save(output_color)

            print(f"  Slot {slot_idx:2d}: ✓ Extracted (variance: {variance:.1f})")
            extracted_count += 1
        else:
            print(f"  Slot {slot_idx:2d}: ✗ Empty (variance: {variance:.1f})")

    print("=" * 60)
    print(f"\n✓ Extracted {extracted_count} items to: {output_dir}/")

    if extracted_count == 0:
        print("\nNo items detected! This could mean:")
        print("  1. Your inventory is empty")
        print("  2. The inventory tab is not visible in RuneLite")
        print("  3. The grid detection failed")
    else:
        print("\nYou can now:")
        print("  1. Compare extracted items with templates in auto/")
        print("  2. Copy good matches to manual/ if wiki versions don't work")
        print("  3. Check if RuneLite overlays interfere with matching")

    return 0

if __name__ == "__main__":
    sys.exit(main())
