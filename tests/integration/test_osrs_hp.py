"""Test digit classifier with actual OSRS HP screenshot."""

import sys

from PIL import Image

from osrsbot.services.digit_classifier import get_digit_classifier


def test_hp_image(image_path: str):
    """
    Test the digit classifier with an OSRS HP screenshot.

    Usage:
        python test_osrs_hp.py path/to/hp_screenshot.png
    """
    try:
        # Load the image
        img = Image.open(image_path)
        print(f"Loaded image: {image_path}")
        print(f"Image size: {img.width}x{img.height}")
        print("=" * 60)

        # Get classifier
        classifier = get_digit_classifier()

        if not classifier.is_available():
            print("ERROR: Classifier not available!")
            return

        # Segment the image
        print("\nSegmentation Analysis:")
        digit_images = classifier._segment_digits(img, max_digits=2)
        print(f"  Segments found: {len(digit_images)}")

        # Save segments for inspection
        for i, seg in enumerate(digit_images):
            seg.save(f"hp_segment_{i}.png")
            print(
                f"    Segment {i}: {seg.width}x{seg.height} -> saved as hp_segment_{i}.png"
            )

        # Calculate aspect ratio of the digit region
        img_gray = img.convert("L")
        list(img_gray.getdata())

        # Predict the number
        print("\nPrediction:")
        predicted = classifier.predict_number(img, max_digits=2)
        print(f"  Predicted HP: {predicted}")

        # Also predict each digit individually
        if len(digit_images) > 0:
            print("\nIndividual digit predictions:")
            for i, digit_img in enumerate(digit_images):
                digit = classifier.predict_digit(digit_img)
                print(f"    Digit {i}: {digit}")

        print("\n" + "=" * 60)
        print("Debug images saved:")
        for i in range(len(digit_images)):
            print(f"  - hp_segment_{i}.png")

    except FileNotFoundError:
        print(f"ERROR: Could not find image at: {image_path}")
        print("\nUsage:")
        print("  python test_osrs_hp.py path/to/hp_screenshot.png")
        print("\nExample:")
        print("  python test_osrs_hp.py ocr_debug/hp_strategy_0.png")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Try to use an existing debug image if available
        import os

        if os.path.exists("ocr_debug/hp_strategy_0.png"):
            print("No image path provided, using ocr_debug/hp_strategy_0.png")
            test_hp_image("ocr_debug/hp_strategy_0.png")
        else:
            print("Usage: python test_osrs_hp.py path/to/hp_screenshot.png")
            print("\nExample:")
            print("  python test_osrs_hp.py ocr_debug/hp_strategy_0.png")
    else:
        test_hp_image(sys.argv[1])
