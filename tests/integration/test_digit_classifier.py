"""
Test script for the CNN digit classifier.

Creates test images of digits and verifies the classifier can read them.
"""

from PIL import Image, ImageDraw, ImageFont

from osrsbot.services.digit_classifier import get_digit_classifier


def create_test_digit(digit: int, size=(40, 60)) -> Image.Image:
    """Create a simple test image of a digit."""
    img = Image.new("RGB", size, color="black")
    draw = ImageDraw.Draw(img)

    # Try to use a default font, fallback to basic if not available
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()

    # Draw digit in white
    text = str(digit)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2

    draw.text((x, y), text, fill="white", font=font)

    return img


def main():
    print("=" * 60)
    print("CNN DIGIT CLASSIFIER TEST")
    print("=" * 60)

    classifier = get_digit_classifier()

    if not classifier.is_available():
        print("\nERROR: Classifier not available!")
        print("Run: python scripts/download_mnist_model.py")
        return

    print("\nClassifier loaded successfully!")
    print("\nTesting single digit recognition...")

    # Test each digit 0-9
    correct = 0
    total = 10

    for digit in range(10):
        img = create_test_digit(digit)
        predicted = classifier.predict_digit(img)

        if predicted == digit:
            print(f"  Digit {digit}: OK (predicted {predicted})")
            correct += 1
        else:
            print(f"  Digit {digit}: FAIL (predicted {predicted})")

    print(f"\nAccuracy: {correct}/{total} ({correct/total*100:.0f}%)")

    # Test two-digit numbers
    print("\nTesting two-digit number recognition...")

    test_numbers = [12, 34, 56, 78, 90, 99, 49, 94]

    for number in test_numbers:
        # Create image with two digits side by side
        img = Image.new("RGB", (80, 60), color="black")
        digit1 = number // 10
        digit2 = number % 10

        img1 = create_test_digit(digit1, (40, 60))
        img2 = create_test_digit(digit2, (40, 60))

        img.paste(img1, (0, 0))
        img.paste(img2, (40, 0))

        predicted = classifier.predict_number(img, max_digits=2)

        if predicted == number:
            print(f"  Number {number}: OK (predicted {predicted})")
        else:
            print(f"  Number {number}: FAIL (predicted {predicted})")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
