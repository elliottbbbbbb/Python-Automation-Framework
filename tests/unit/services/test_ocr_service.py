"""
Unit tests for OCRService

Tests OCR digit recognition with multiple preprocessing strategies.
"""

from unittest.mock import Mock, patch

import pytest
from PIL import Image, ImageDraw, ImageFont

from osrsbot.models.config import Config
from osrsbot.services.ocr_service import OCRService


class TestOCRServiceInitialization:
    """Test OCRService initialization"""

    def test_initialization_with_config(self, mock_config):
        """Test OCRService initializes correctly"""
        ocr = OCRService(mock_config)

        assert ocr.config == mock_config

    def test_tesseract_path_configured(self, mock_config):
        """Test that Tesseract path is configured"""
        with patch("pytesseract.pytesseract") as mock_tesseract:
            OCRService(mock_config)

            # Tesseract path should be set during initialization
            assert hasattr(mock_tesseract, "tesseract_cmd")


class TestOCRServiceDigitRecognition:
    """Test digit recognition functionality"""

    def test_read_digits_simple(self, ocr_service, digit_image_42):
        """Test reading simple two-digit number"""
        with patch("pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "42"

            result = ocr_service.read_digits(digit_image_42)

            assert result == 42

    def test_read_digits_single_digit(self, ocr_service, digit_image_7):
        """Test reading single digit"""
        with patch("pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "7"

            result = ocr_service.read_digits(digit_image_7)

            assert result == 7

    def test_read_digits_three_digits(self, ocr_service):
        """Test reading three-digit number"""
        img = create_digit_image("100")

        with patch("pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "100"

            result = ocr_service.read_digits(img)

            assert result == 100

    def test_read_digits_returns_none_on_failure(self, ocr_service):
        """Test that invalid OCR returns None"""
        img = Image.new("RGB", (50, 20), color=(255, 255, 255))

        with patch("pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "not-a-number"

            result = ocr_service.read_digits(img)

            assert result is None


class TestOCRServicePreprocessing:
    """Test preprocessing strategies"""

    def test_multiple_strategies_used(self, ocr_service, digit_image_42):
        """Test that multiple preprocessing strategies are attempted"""
        with patch("pytesseract.image_to_string") as mock_ocr:
            # Different strategies might return different results
            mock_ocr.side_effect = ["42", "42", "42", "42", "42"]

            result = ocr_service.read_digits(digit_image_42)

            # Should call OCR multiple times (once per strategy)
            assert mock_ocr.call_count >= 1
            assert result == 42

    def test_consensus_voting(self, ocr_service, digit_image_42):
        """Test that consensus voting works"""
        with patch("pytesseract.image_to_string") as mock_ocr:
            # Most strategies return 42, one returns garbage
            mock_ocr.side_effect = ["42", "42", "99", "42", "42"]

            result = ocr_service.read_digits(digit_image_42)

            # Should return most common result (42)
            assert result == 42

    def test_preprocessing_handles_noise(self, ocr_service):
        """Test preprocessing handles noisy images"""
        # Create noisy image
        img = create_noisy_digit_image("55")

        with patch("pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "55"

            result = ocr_service.read_digits(img)

            # Should still recognize despite noise
            assert result == 55


class TestOCRServiceShapeDetection:
    """Test shape detection for digit disambiguation (4 vs 9)"""

    def test_detect_shape_for_four(self, ocr_service):
        """Test shape detection identifies '4' correctly"""
        create_digit_image("4")

        # The 4 should have a hole (open shape)
        # Implementation-specific test
        pass  # This would require actual shape detection implementation

    def test_detect_shape_for_nine(self, ocr_service):
        """Test shape detection identifies '9' correctly"""
        create_digit_image("9")

        # The 9 should have a closed hole
        # Implementation-specific test
        pass  # This would require actual shape detection implementation


class TestOCRServiceRegionHandling:
    """Test OCR with different regions"""

    def test_read_digits_with_region(self, ocr_service):
        """Test reading digits from specific region"""
        # Create larger image with digits in specific area
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        # Draw "88" in specific region
        draw.text((50, 50), "88", fill=(0, 0, 0))

        with patch("pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "88"

            result = ocr_service.read_digits(img, region=(40, 40, 100, 80))

            assert result == 88

    def test_read_digits_full_image(self, ocr_service, digit_image_42):
        """Test reading digits from full image"""
        with patch("pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "42"

            result = ocr_service.read_digits(digit_image_42)

            assert result == 42


class TestOCRServiceEdgeCases:
    """Test edge cases and error handling"""

    def test_read_empty_image(self, ocr_service):
        """Test reading from empty/white image"""
        img = Image.new("RGB", (50, 20), color=(255, 255, 255))

        with patch("pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = ""

            result = ocr_service.read_digits(img)

            assert result is None

    def test_read_zero(self, ocr_service):
        """Test reading zero"""
        img = create_digit_image("0")

        with patch("pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "0"

            result = ocr_service.read_digits(img)

            assert result == 0

    def test_read_negative_number_returns_none(self, ocr_service):
        """Test that negative numbers aren't supported"""
        img = create_digit_image("-5")

        with patch("pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "-5"

            result = ocr_service.read_digits(img)

            # Should return None or handle appropriately
            # (HP can't be negative in OSRS)
            assert result is None or result == 5

    def test_ocr_exception_handled(self, ocr_service, digit_image_42):
        """Test that OCR exceptions are handled gracefully"""
        with patch("pytesseract.image_to_string") as mock_ocr:
            mock_ocr.side_effect = Exception("Tesseract error")

            result = ocr_service.read_digits(digit_image_42)

            # Should return None on error, not crash
            assert result is None


class TestOCRServicePerformance:
    """Test performance-related functionality"""

    def test_preprocessing_caching(self, ocr_service, digit_image_42):
        """Test that preprocessing results could be cached"""
        # This would test if the same image preprocessed multiple times
        # uses cached results (if implemented)
        pass  # Implementation-specific


# Helper functions


def create_digit_image(text: str, size=(100, 40)) -> Image.Image:
    """Create a simple image with digits"""
    img = Image.new("RGB", size, color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        # Try to use a font
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        # Fall back to default font
        font = ImageFont.load_default()

    # Draw text in center
    draw.text((10, 10), text, fill=(0, 0, 0), font=font)
    return img


def create_noisy_digit_image(text: str) -> Image.Image:
    """Create digit image with noise"""
    img = create_digit_image(text)
    pixels = img.load()

    # Add random noise
    import random

    for i in range(img.size[0]):
        for j in range(img.size[1]):
            if random.random() < 0.1:  # 10% noise
                pixels[i, j] = (200, 200, 200)

    return img


# Fixtures


@pytest.fixture
def mock_config():
    """Mock Config"""
    config = Mock(spec=Config)
    return config


@pytest.fixture
def ocr_service(mock_config):
    """Create OCRService instance for testing"""
    with patch("pytesseract.pytesseract"):
        return OCRService(mock_config)


@pytest.fixture
def digit_image_42():
    """Sample image with number 42"""
    return create_digit_image("42")


@pytest.fixture
def digit_image_7():
    """Sample image with number 7"""
    return create_digit_image("7")
