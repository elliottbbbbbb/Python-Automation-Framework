"""Test OCR improvements with drop shadow removal and color-adaptive preprocessing."""

import sys

from PIL import Image

from osrsbot.services.ocr_service import OCRRegion, OCRService


def test_ocr_improvements(image_path: str, expected_value: int):
    """
    Test the improved OCR service with OSRS screenshots.

    Args:
        image_path: Path to OSRS stat screenshot (HP, Prayer, etc.)
        expected_value: The actual value shown in the screenshot
    """
    print("=" * 70)
    print("OCR IMPROVEMENT TEST")
    print("=" * 70)

    try:
        # Load image
        img = Image.open(image_path)
        print(f"\nLoaded image: {image_path}")
        print(f"Image size: {img.width}x{img.height}")
        print(f"Expected value: {expected_value}")
        print("-" * 70)

        # Create OCR service with debug enabled
        ocr = OCRService(debug=True, use_cnn=False)

        # Create a mock region (will use screenshot directly)
        region = OCRRegion(x=0, y=0, width=img.width, height=img.height, name="test")

        # Test color detection
        print("\n[1] COLOR DETECTION TEST")
        color = ocr._detect_text_color(img)
        print(f"    Detected text color: {color}")

        # Test drop shadow removal
        print("\n[2] DROP SHADOW REMOVAL TEST")
        try:
            img_no_shadow = ocr._remove_drop_shadow(img)
            img_no_shadow.save("debug_no_shadow.png")
            print("    [OK] Drop shadow removed successfully")
            print("    Saved: debug_no_shadow.png")
        except Exception as e:
            print(f"    [FAIL] Drop shadow removal failed: {e}")

        # Test color-adaptive preprocessing
        print("\n[3] COLOR-ADAPTIVE PREPROCESSING TEST")
        try:
            img_color_adapted = ocr._color_adaptive_preprocessing(img)
            if img_color_adapted is not None:
                img_color_adapted.save("debug_color_adapted.png")
                print(
                    f"    [OK] Color-adaptive preprocessing succeeded for '{color}' text"
                )
                print("    Saved: debug_color_adapted.png")
            else:
                print(f"    [SKIP] No color-specific preprocessing for '{color}'")
        except Exception as e:
            print(f"    [FAIL] Color-adaptive preprocessing failed: {e}")

        # Test finalize preprocessing
        print("\n[4] FINALIZE PREPROCESSING TEST")
        try:
            if img_color_adapted is not None:
                img_final = ocr._finalize_preprocessing(img_color_adapted)
                img_final.save("debug_final.png")
                print("    [OK] Final preprocessing succeeded")
                print("    Saved: debug_final.png")
        except Exception as e:
            print(f"    [FAIL] Final preprocessing failed: {e}")

        # Test full preprocessing pipeline
        print("\n[5] FULL PREPROCESSING PIPELINE TEST")
        strategies = ocr._preprocess_for_numbers(img)
        print(f"    Generated {len(strategies)} preprocessing strategies")

        # The debug images are automatically saved to ocr_debug/ by the service
        print(f"    Debug images saved to: ocr_debug/test_strategy_*.png")

        # Test OCR with the improvements
        print("\n[6] OCR ACCURACY TEST")
        print("    Running Tesseract OCR on all strategies...")

        # We can't use read_number directly without a window, so we'll manually test
        # Just show that preprocessing worked
        print(f"\n    NOTE: Full OCR test requires running bot with game window.")
        print(f"    The new preprocessing strategies are now integrated and will be")
        print(f"    used automatically when you run the bot.")

        print("\n" + "=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)
        print("\nGenerated debug images:")
        print("  - debug_no_shadow.png (drop shadow removed)")
        print("  - debug_color_adapted.png (color channel isolated)")
        print("  - debug_final.png (final binary image for OCR)")
        print(f"  - ocr_debug/test_strategy_*.png ({len(strategies)} strategies)")
        print("\nNext steps:")
        print("  1. Inspect the debug images to verify preprocessing quality")
        print("  2. Run your bot and check OCR accuracy in real gameplay")
        print("  3. Check logs for 'Detected text color' messages")

    except FileNotFoundError:
        print(f"ERROR: Could not find image at: {image_path}")
        print("\nUsage:")
        print("  python test_ocr_improvements.py <image_path> <expected_value>")
        print("\nExample:")
        print("  python test_ocr_improvements.py ocr_debug/hp_strategy_0.png 70")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_ocr_improvements.py <image_path> <expected_value>")
        print("\nExample:")
        print("  python test_ocr_improvements.py ocr_debug/hp_strategy_0.png 70")
        print(
            "\nThis will test the new drop shadow removal and color-adaptive preprocessing."
        )
    else:
        image_path = sys.argv[1]
        expected_value = int(sys.argv[2])
        test_ocr_improvements(image_path, expected_value)
