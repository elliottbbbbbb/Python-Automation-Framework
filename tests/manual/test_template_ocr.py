"""
Test script for template-based OCR service.
Tests HP extraction using kellton's template matching approach.
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import cv2
import numpy as np
import pyautogui

from osrsbot.services.template_ocr_service import (
    ORB_GREEN,
    ORB_RED,
    TemplateOCRService,
)

# Setup logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_hp_extraction():
    """Test HP extraction using template matching OCR."""
    # Initialize service
    ocr = TemplateOCRService()

    # HP orb coordinates (adjust these for your screen)
    # These are relative to game window - you'll need to adjust
    print("Move your mouse to the HP orb text and press Enter...")
    input()
    x, y = pyautogui.position()
    print(f"Mouse position: {x}, {y}")

    # Capture a small region around HP text
    # HP orb text is typically around 25x15 pixels
    region = (x - 12, y - 7, 25, 15)

    print(f"\nCapturing region: {region}")
    screenshot = pyautogui.screenshot(region=region)

    # Convert to numpy array (BGR format for OpenCV)
    img_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    # Save debug image
    cv2.imwrite("test_hp_raw.png", img_np)
    print("Saved raw screenshot to test_hp_raw.png")

    # Test with ORB_GREEN and ORB_RED colors
    print("\n--- Testing Template OCR ---")
    result = ocr.extract_number(
        img_np,
        font_name="plain11",
        colors=[ORB_GREEN, ORB_RED],
        correlation_threshold=0.98,
    )

    print(f"Template OCR Result: {result}")

    # Also extract text (to see all characters detected)
    text_result = ocr.extract_text(
        img_np,
        font_name="plain11",
        colors=[ORB_GREEN, ORB_RED],
        correlation_threshold=0.98,
    )
    print(f"Template OCR Text: '{text_result}'")

    return result


if __name__ == "__main__":
    print("=== Template OCR HP Extraction Test ===\n")
    result = test_hp_extraction()
    print(f"\nFinal HP Value: {result}")
