"""
Simple HP tracking script - Continuously monitors HP using both OCR methods.

Compares Tesseract OCR vs Template Matching OCR in real-time.
Press Ctrl+C to stop.
"""
import time
import logging
import cv2
import numpy as np
import pyautogui
from pathlib import Path
import sys

# Add src to path (go up 2 levels from tests/manual/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from osrsbot.models.config import Config
from osrsbot.services.ocr_service import OCRService, OCRRegion
from osrsbot.services.template_ocr_service import (
    get_template_ocr_service,
    ORB_GREEN,
    ORB_RED,
)
from osrsbot.core.game_interface import GameInterface

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def track_hp():
    """Track HP using both OCR methods and compare results."""
    print("=" * 70)
    print("HP TRACKING - Tesseract vs Template Matching OCR")
    print("=" * 70)
    print("Press Ctrl+C to stop\n")

    # Initialize services
    config = Config()
    interface = GameInterface(config)

    # Find RuneLite window
    if not interface.window:
        print("ERROR: Could not find RuneLite window")
        print("Please start RuneLite and try again")
        return

    print(f"✓ Found RuneLite window: {interface.window.title}\n")

    # Initialize OCR services
    tesseract_ocr = OCRService(
        window_getter=lambda: interface.get_absolute_bounds(),
        debug=False,
        use_cnn=False
    )
    template_ocr = get_template_ocr_service()

    # Get HP region from config
    hp_region_config = config.get("coordinates", "ocr", "hp_region")
    if not hp_region_config:
        print("ERROR: hp_region not found in config")
        return

    hp_region = OCRRegion(
        x=hp_region_config["x"],
        y=hp_region_config["y"],
        width=hp_region_config["width"],
        height=hp_region_config["height"],
        name="hp"
    )

    print(f"HP Region: x={hp_region.x}, y={hp_region.y}, "
          f"width={hp_region.width}, height={hp_region.height}\n")

    # Tracking stats
    total_reads = 0
    tesseract_successes = 0
    template_successes = 0
    matches = 0
    mismatches = 0
    tesseract_failures = 0
    template_failures = 0

    try:
        while True:
            # Get window position
            win_pos = interface.get_absolute_bounds()
            if not win_pos:
                print("WARNING: Lost window position")
                time.sleep(1)
                continue

            win_x, win_y, _, _ = win_pos

            # === Tesseract OCR ===
            hp_tesseract = tesseract_ocr.read_number(
                region=hp_region,
                min_value=1,
                max_value=99,
                smooth=False
            )

            # === Template Matching OCR ===
            hp_x = win_x + hp_region.x
            hp_y = win_y + hp_region.y
            screenshot = pyautogui.screenshot(
                region=(hp_x, hp_y, hp_region.width, hp_region.height)
            )
            img_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            hp_template = template_ocr.extract_number(
                img_np,
                font_name="plain11",
                colors=[ORB_GREEN, ORB_RED],
                correlation_threshold=0.98
            )

            # Debug: Save image if template matching fails
            if hp_template is None and total_reads < 5:
                cv2.imwrite(f"debug_hp_fail_{total_reads}.png", img_np)
                logger.debug(f"Saved debug image: debug_hp_fail_{total_reads}.png")

            # Update stats
            total_reads += 1
            if hp_tesseract is not None:
                tesseract_successes += 1
            else:
                tesseract_failures += 1

            if hp_template is not None:
                template_successes += 1
            else:
                template_failures += 1

            # Compare results
            if hp_tesseract is not None and hp_template is not None:
                if hp_tesseract == hp_template:
                    matches += 1
                    status = "✓ MATCH"
                else:
                    mismatches += 1
                    status = "✗ MISMATCH"
            else:
                status = "- PARTIAL"

            # Display results
            tesseract_str = f"{hp_tesseract:2d}" if hp_tesseract is not None else "XX"
            template_str = f"{hp_template:2d}" if hp_template is not None else "XX"

            print(f"[{total_reads:4d}] Tesseract: {tesseract_str} | "
                  f"Template: {template_str} | {status}")

            # Show stats every 10 reads
            if total_reads % 10 == 0:
                print()
                print("=" * 70)
                print(f"STATISTICS (after {total_reads} reads)")
                print("-" * 70)
                print(f"Tesseract Success Rate: {tesseract_successes}/{total_reads} "
                      f"({100*tesseract_successes/total_reads:.1f}%)")
                print(f"Template Success Rate:  {template_successes}/{total_reads} "
                      f"({100*template_successes/total_reads:.1f}%)")
                print(f"Matches:                {matches}")
                print(f"Mismatches:             {mismatches}")
                print(f"Tesseract Failures:     {tesseract_failures}")
                print(f"Template Failures:      {template_failures}")
                print("=" * 70)
                print()

            # Wait before next read
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("FINAL STATISTICS")
        print("=" * 70)
        print(f"Total Reads:            {total_reads}")
        print(f"Tesseract Successes:    {tesseract_successes} "
              f"({100*tesseract_successes/total_reads:.1f}%)")
        print(f"Template Successes:     {template_successes} "
              f"({100*template_successes/total_reads:.1f}%)")
        print(f"Matches:                {matches}")
        print(f"Mismatches:             {mismatches}")
        print(f"Tesseract Failures:     {tesseract_failures}")
        print(f"Template Failures:      {template_failures}")
        print("=" * 70)

        if mismatches > 0:
            print("\nMISMATCH ANALYSIS:")
            print("When both methods returned a value but disagreed,")
            print("check the ocr_debug/ folder to see preprocessing images")
            print("and determine which method was correct.")

        print("\nStopped by user")


if __name__ == "__main__":
    track_hp()
