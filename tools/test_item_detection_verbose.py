"""
Verbose test script to see exactly what confidence scores we're getting.
Shows the top 3 matches for each slot with their confidence scores.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2
import numpy as np
from osrsbot.services.item_detection_service import ItemDetectionService
from osrsbot.services.screen_service import ScreenService
from osrsbot.services.template_match_service import TemplateMatchService
from osrsbot.models.config import Config

def main():
    print("=" * 80)
    print("VERBOSE ITEM DETECTION TEST - Shows Confidence Scores")
    print("=" * 80)

    # Initialize services
    config = Config()
    script_dir = Path(__file__).parent.parent
    items_dir = script_dir / "src" / "osrsbot" / "images" / "items"

    # Load templates
    print("\n1. Loading item templates...")
    item_detection = ItemDetectionService(str(items_dir), threshold=0.75)
    print(f"   ✓ Loaded {item_detection.get_template_count()} templates")

    # Get window
    print("\n2. Initializing screen capture...")
    window_title = config.get("window_title", default="RuneLite")
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            print(f"   ✗ Could not find window: {window_title}")
            return 1
        window = windows[0]
        print(f"   ✓ Found window: {window.title}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return 1

    # Capture screenshot
    print("\n3. Capturing screenshot...")
    screen = ScreenService(window_getter=lambda: (window.left, window.top, window.width, window.height))
    img_color = screen.capture()
    img_array = np.array(img_color)
    img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    print(f"   ✓ Captured: {img_gray.shape}")

    # Detect grid
    print("\n4. Detecting inventory grid...")
    template_service = TemplateMatchService()
    template_path = script_dir / "src" / "osrsbot" / "images" / "bot" / "ui_templates" / "inventory_empty.PNG"
    template_service.register_grid("inventory", str(template_path), 7, 4, 0.30, True, 20, 0)

    detected = template_service.detect_grid("inventory", img_gray, force=True)
    if not detected:
        print("   ✗ Could not detect inventory grid")
        return 1

    grid = template_service.get_grid("inventory")
    print(f"   ✓ Grid detected at {grid.detected_bbox}")

    # Test each filled slot and show top 3 matches
    print("\n5. Testing each slot (showing top 3 matches)...")
    print("=" * 80)

    for slot_idx in range(28):
        element = grid.get_element(slot_idx)
        if not element:
            continue

        # Crop slot
        x0, y0, x1, y1 = element.bbox
        slot_image = img_gray[y0:y1, x0:x1]

        # Check if filled
        variance = np.std(slot_image)
        if variance < 10:
            continue  # Skip empty slots

        # Try to match against ALL templates and get top 3
        matches = []
        for item_name, template in item_detection.templates.items():
            try:
                if slot_image.shape[0] < template.shape[0] or slot_image.shape[1] < template.shape[1]:
                    continue

                result = cv2.matchTemplate(slot_image, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                matches.append((item_name, max_val))
            except:
                continue

        # Sort by confidence and show top 3
        matches.sort(key=lambda x: x[1], reverse=True)
        top_3 = matches[:3]

        print(f"\nSlot {slot_idx:2d} (variance: {variance:.1f}):")
        for i, (name, conf) in enumerate(top_3):
            marker = "✓" if conf >= 0.75 else "✗"
            print(f"  {i+1}. {marker} {name:40s} confidence: {conf:.3f}")

    print("\n" + "=" * 80)
    print("ANALYSIS:")
    print("  - If best matches are < 0.75: Templates don't match well (background issue)")
    print("  - If best matches are 0.60-0.74: Lower threshold to 0.65 might work")
    print("  - If best matches are < 0.60: Need manual templates from your game")
    print("=" * 80)

    return 0

if __name__ == "__main__":
    sys.exit(main())
