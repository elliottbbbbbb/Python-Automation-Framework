"""Test single digit detection to ensure it doesn't incorrectly split."""

from PIL import Image
from osrsbot.services.digit_classifier import get_digit_classifier

# Test with the actual image
img_path = "segmentation_debug/test_3.png"

try:
    # Load the image the user showed (green 3)
    # For now, test with a created image
    from PIL import ImageDraw, ImageFont

    img = Image.new('RGB', (20, 20), color='white')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("consola.ttf", 14)
    except:
        font = ImageFont.load_default()

    # Draw a single digit
    for digit in [3, 6, 8, 9, 0, 1]:
        img = Image.new('RGB', (20, 20), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((5, 2), str(digit), fill='black', font=font)

        classifier = get_digit_classifier()

        # Check segmentation
        digit_images = classifier._segment_digits(img, max_digits=2)

        # Predict
        predicted = classifier.predict_number(img, max_digits=2)

        status = "OK" if predicted == digit else "FAIL"
        print(f"Digit {digit}: {len(digit_images)} segments found, predicted={predicted} [{status}]")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
