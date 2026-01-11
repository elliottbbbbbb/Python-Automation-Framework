"""
Test script to verify item detection works with actual in-game inventory.

Usage:
    1. Have RuneLite open with inventory visible
    2. Run: python tools/test_item_detection.py
    3. It will screenshot and try to detect items
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2
import numpy as np
from osrsbot.services.item_detection_service import ItemDetectionService
from osrsbot.services.screen_service import ScreenService
from osrsbot.services.template_match_service import TemplateMatchService
from osrsbot.models.config import Config

def main():
    print("=" * 80)
    print("ITEM DETECTION TEST")
    print("=" * 80)

    # Initialize services
    config = Config()

    # Initialize ItemDetectionService with absolute path
    print("\n1. Loading item templates...")
    script_dir = Path(__file__).parent.parent
    items_dir = script_dir / "src" / "osrsbot" / "images" / "items"

    item_detection = ItemDetectionService(
        items_dir=str(items_dir),
        threshold=0.75
    )
    print(f"   ✓ Loaded {item_detection.get_template_count()} templates")

    # Initialize ScreenService
    print("\n2. Initializing screen capture...")
    window_title = config.get("window_title", default="RuneLite")

    try:
        # Try to get window bounds
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            print(f"   ✗ Could not find window: {window_title}")
            print(f"   Please make sure RuneLite is open")
            return 1

        window = windows[0]
        print(f"   ✓ Found window: {window.title}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return 1

    # Initialize template matching
    print("\n3. Initializing template matching...")
    template_service = TemplateMatchService()

    # Register inventory grid template directly (use absolute path)
    from pathlib import Path as PathLib
    script_dir = PathLib(__file__).parent.parent
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
    print(f"   ✓ Registered inventory grid template")

    # Capture screenshot
    print("\n4. Capturing screenshot...")
    screen = ScreenService(window_getter=lambda: (window.left, window.top, window.width, window.height))
    img_color = screen.capture()
    img_array = np.array(img_color)
    img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    print(f"   ✓ Captured screenshot: {img_gray.shape}")

    # Detect inventory grid
    print("\n5. Detecting inventory grid...")
    detected = template_service.detect_grid("inventory", img_gray, force=True)

    if not detected:
        print("   ✗ Could not detect inventory grid")
        print("   Make sure inventory tab is open in RuneLite")
        return 1

    grid = template_service.get_grid("inventory")
    print(f"   ✓ Inventory grid detected at {grid.detected_bbox}")

    # Test item detection on first few slots
    print("\n6. Testing item detection on inventory slots...")
    print("   " + "=" * 76)

    test_items = ["shark", "lobster", "swordfish", "prayer_potion(4)", "super_combat_potion(4)"]

    for slot_idx in range(min(10, 28)):  # Test first 10 slots
        element = grid.get_element(slot_idx)
        if not element:
            continue

        # Crop slot region
        x0, y0, x1, y1 = element.bbox
        slot_image = img_gray[y0:y1, x0:x1]

        # Try to identify
        item_name = item_detection.identify_item_in_slot(slot_image)

        if item_name:
            print(f"   Slot {slot_idx:2d}: ✓ Detected '{item_name}'")
        else:
            print(f"   Slot {slot_idx:2d}: ✗ No match (or empty)")

    print("   " + "=" * 76)

    # Try to find specific items
    print("\n7. Testing find_item() for common items...")

    # Get all filled slots (simple check - not empty)
    filled_slots = []
    for i in range(28):
        element = grid.get_element(i)
        if element:
            x0, y0, x1, y1 = element.bbox
            slot_image = img_gray[y0:y1, x0:x1]
            # Simple variance check
            variance = np.std(slot_image)
            if variance > 10:  # Likely has an item
                filled_slots.append(i)

    print(f"   Detected {len(filled_slots)} filled slots: {filled_slots}")

    # Get slot positions
    slot_positions = []
    for i in range(28):
        element = grid.get_element(i)
        if element:
            slot_positions.append(element.bbox)
        else:
            slot_positions.append((0, 0, 0, 0))

    # Test finding common items
    for item_name in test_items:
        slots = item_detection.find_item(
            item_name=item_name,
            filled_slots=filled_slots,
            screenshot=img_gray,
            slot_positions=slot_positions
        )

        if slots:
            print(f"   ✓ Found '{item_name}' in slots: {slots}")
        else:
            print(f"   ✗ '{item_name}' not found")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    # Recommendations
    print("\n📋 RECOMMENDATIONS:")
    print("   1. If no items detected: Try lowering threshold in config")
    print("   2. If false positives: Try raising threshold in config")
    print("   3. If specific items fail: Screenshot them and add to manual/")
    print("   4. Turn off RuneLite item highlights for better matching")
    print("\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
