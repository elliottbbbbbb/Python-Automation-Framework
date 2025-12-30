"""Test digit segmentation with OSRS-style numbers."""

from PIL import Image, ImageDraw, ImageFont
from osrsbot.services.digit_classifier import get_digit_classifier
import os

def create_test_image(number: int, spacing: int = 1) -> Image.Image:
    """Create a test image with a number using a monospace font."""
    # Create image with white background
    img = Image.new('RGB', (40, 20), color='white')
    draw = ImageDraw.Draw(img)

    # Try to use a simple font
    try:
        # Windows default monospace font
        font = ImageFont.truetype("consola.ttf", 14)
    except:
        font = ImageFont.load_default()

    # Draw the number in black
    text = str(number)
    draw.text((5, 2), text, fill='black', font=font)

    return img

def test_segmentation():
    """Test digit segmentation with various numbers."""
    classifier = get_digit_classifier()

    if not classifier.is_available():
        print("ERROR: Classifier not available!")
        return

    print("Testing digit segmentation...")
    print("=" * 60)

    # Create debug directory
    os.makedirs("segmentation_debug", exist_ok=True)

    test_numbers = [12, 23, 45, 67, 89, 99, 10, 50]

    for number in test_numbers:
        # Create test image
        img = create_test_image(number)
        img.save(f"segmentation_debug/test_{number}.png")

        # Segment digits
        digit_images = classifier._segment_digits(img, max_digits=2)

        print(f"\nNumber {number}:")
        print(f"  Segments found: {len(digit_images)}")

        # Save segmented digits
        for i, digit_img in enumerate(digit_images):
            digit_img.save(f"segmentation_debug/test_{number}_digit_{i}.png")
            print(f"    Digit {i}: saved")

        # Predict the number
        predicted = classifier.predict_number(img, max_digits=2)

        if predicted == number:
            print(f"  OK Prediction: {predicted} (CORRECT)")
        else:
            print(f"  FAIL Prediction: {predicted} (expected {number})")

    print("\n" + "=" * 60)
    print("Debug images saved to segmentation_debug/")

if __name__ == "__main__":
    test_segmentation()
