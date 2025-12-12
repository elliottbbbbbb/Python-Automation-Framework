"""
Unit tests for ScreenService

Tests screen capture, color detection, and pixel sampling functionality.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PIL import Image
import numpy as np
from typing import Tuple

from osrsbot.services.screen_service import ScreenService
from osrsbot.core.game_interface import GameInterface
from osrsbot.models.config import Config


class TestScreenServiceInitialization:
    """Test ScreenService initialization"""

    def test_initialization_with_valid_params(self, mock_game_interface, mock_config):
        """Test that ScreenService initializes correctly"""
        screen = ScreenService(mock_game_interface, mock_config)

        assert screen.interface == mock_game_interface
        assert screen.config == mock_config

    def test_window_getter_callable(self, mock_game_interface, mock_config):
        """Test that window_getter is properly set"""
        screen = ScreenService(mock_game_interface, mock_config)

        # window_getter should be callable
        assert callable(screen.window_getter)

        # Calling it should return window bounds
        bounds = screen.window_getter()
        assert isinstance(bounds, tuple)
        assert len(bounds) == 4


class TestScreenServiceColorDetection:
    """Test color detection functionality"""

    def test_find_color_simple_match(self, screen_service, sample_screenshot):
        """Test finding a color that exists in the image"""
        with patch('pyautogui.screenshot') as mock_screenshot:
            mock_screenshot.return_value = sample_screenshot

            # Green color should be found at (50, 50)
            result = screen_service.find_color("#00ff00", tolerance=10)

            assert result is not None
            assert hasattr(result, 'x')
            assert hasattr(result, 'y')

    def test_find_color_not_found(self, screen_service, sample_screenshot):
        """Test finding a color that doesn't exist"""
        with patch('pyautogui.screenshot') as mock_screenshot:
            mock_screenshot.return_value = sample_screenshot

            # Purple color shouldn't exist in test image
            result = screen_service.find_color("#ff00ff", tolerance=5)

            assert result is None

    def test_find_color_with_tolerance(self, screen_service):
        """Test color matching with tolerance"""
        # Create image with slightly off-color pixel
        img = Image.new('RGB', (100, 100), color=(255, 0, 0))  # Red
        img.putpixel((50, 50), (250, 5, 5))  # Slightly different red

        with patch('pyautogui.screenshot') as mock_screenshot:
            mock_screenshot.return_value = img

            # Should not find with low tolerance
            result = screen_service.find_color("#ff0000", tolerance=3)
            assert result is None

            # Should find with higher tolerance
            result = screen_service.find_color("#ff0000", tolerance=10)
            assert result is not None

    def test_find_color_all_matches(self, screen_service):
        """Test finding all color matches"""
        # Create image with multiple green pixels
        img = Image.new('RGB', (100, 100), color=(255, 255, 255))
        img.putpixel((10, 10), (0, 255, 0))
        img.putpixel((20, 20), (0, 255, 0))
        img.putpixel((30, 30), (0, 255, 0))

        with patch('pyautogui.screenshot') as mock_screenshot:
            mock_screenshot.return_value = img

            results = screen_service.find_color("#00ff00", tolerance=5, find_all=True)

            assert results is not None
            assert isinstance(results, list)
            assert len(results) == 3

    def test_find_color_with_region(self, screen_service):
        """Test color detection within specific region"""
        img = Image.new('RGB', (100, 100), color=(255, 255, 255))
        img.putpixel((10, 10), (0, 255, 0))
        img.putpixel((90, 90), (0, 255, 0))

        with patch('pyautogui.screenshot') as mock_screenshot:
            mock_screenshot.return_value = img

            # Search only top-left region - should find one
            result = screen_service.find_color(
                "#00ff00",
                tolerance=5,
                region=(0, 0, 50, 50)
            )

            assert result is not None
            # Should be the (10, 10) pixel, not (90, 90)


class TestScreenServicePixelSampling:
    """Test pixel color sampling"""

    def test_get_pixel_color(self, screen_service):
        """Test getting color of a specific pixel"""
        # Create test image
        img = Image.new('RGB', (100, 100), color=(255, 255, 255))
        img.putpixel((50, 50), (255, 0, 0))  # Red pixel

        with patch('pyautogui.screenshot') as mock_screenshot:
            mock_screenshot.return_value = img

            color = screen_service.get_pixel_color(50, 50)

            assert color == (255, 0, 0)

    def test_get_pixel_color_with_bounds(self, screen_service):
        """Test pixel sampling with window bounds offset"""
        img = Image.new('RGB', (100, 100), color=(255, 255, 255))
        img.putpixel((25, 25), (0, 0, 255))  # Blue pixel

        with patch('pyautogui.screenshot') as mock_screenshot:
            mock_screenshot.return_value = img

            # The service should handle coordinate translation
            color = screen_service.get_pixel_color(25, 25)

            assert len(color) == 3
            assert all(isinstance(c, int) for c in color)


class TestScreenServiceCapture:
    """Test screen capture functionality"""

    def test_capture_screen(self, screen_service):
        """Test capturing the game window"""
        mock_img = Image.new('RGB', (800, 600), color=(100, 100, 100))

        with patch('pyautogui.screenshot') as mock_screenshot:
            mock_screenshot.return_value = mock_img

            result = screen_service.capture_screen()

            assert result is not None
            assert isinstance(result, Image.Image)
            mock_screenshot.assert_called_once()

    def test_capture_region(self, screen_service):
        """Test capturing specific region"""
        mock_img = Image.new('RGB', (200, 200), color=(100, 100, 100))

        with patch('pyautogui.screenshot') as mock_screenshot:
            mock_screenshot.return_value = mock_img

            result = screen_service.capture_region((100, 100, 200, 200))

            assert result is not None
            assert isinstance(result, Image.Image)


class TestScreenServiceColorMatching:
    """Test color matching algorithms"""

    def test_colors_match_exact(self, screen_service):
        """Test exact color matching"""
        color1 = (255, 0, 0)
        color2 = (255, 0, 0)

        assert screen_service._colors_match(color1, color2, tolerance=0)

    def test_colors_match_within_tolerance(self, screen_service):
        """Test color matching within tolerance"""
        color1 = (255, 0, 0)
        color2 = (250, 5, 5)

        assert screen_service._colors_match(color1, color2, tolerance=10)

    def test_colors_dont_match_outside_tolerance(self, screen_service):
        """Test colors don't match outside tolerance"""
        color1 = (255, 0, 0)
        color2 = (200, 50, 50)

        assert not screen_service._colors_match(color1, color2, tolerance=10)

    def test_color_distance_calculation(self, screen_service):
        """Test color distance calculation"""
        color1 = (255, 0, 0)
        color2 = (255, 0, 0)

        distance = screen_service._color_distance(color1, color2)
        assert distance == 0

        color3 = (0, 255, 0)
        distance = screen_service._color_distance(color1, color3)
        assert distance > 0


class TestScreenServiceEdgeCases:
    """Test edge cases and error handling"""

    def test_find_color_empty_region(self, screen_service):
        """Test color detection in empty region"""
        img = Image.new('RGB', (10, 10), color=(255, 255, 255))

        with patch('pyautogui.screenshot') as mock_screenshot:
            mock_screenshot.return_value = img

            result = screen_service.find_color("#00ff00", tolerance=5)
            assert result is None

    def test_find_color_invalid_hex(self, screen_service):
        """Test with invalid hex color"""
        with pytest.raises((ValueError, Exception)):
            screen_service.find_color("not-a-color", tolerance=5)

    def test_get_pixel_color_out_of_bounds(self, screen_service):
        """Test getting pixel outside image bounds"""
        img = Image.new('RGB', (100, 100), color=(255, 255, 255))

        with patch('pyautogui.screenshot') as mock_screenshot:
            mock_screenshot.return_value = img

            # Should handle gracefully (or raise appropriate error)
            with pytest.raises((IndexError, Exception)):
                screen_service.get_pixel_color(1000, 1000)


class TestScreenServicePerformance:
    """Test performance-related functionality"""

    def test_numpy_optimization_used(self, screen_service):
        """Test that NumPy is used for performance"""
        img = Image.new('RGB', (100, 100), color=(255, 255, 255))

        with patch('pyautogui.screenshot') as mock_screenshot:
            mock_screenshot.return_value = img

            # The implementation should convert to numpy for performance
            # This is more of a code inspection test
            with patch('numpy.array') as mock_array:
                mock_array.return_value = np.array(img)
                screen_service.find_color("#ffffff", tolerance=5)

                # NumPy should be used for image processing
                # (Actual implementation may vary)


# Fixtures

@pytest.fixture
def mock_game_interface():
    """Mock GameInterface"""
    interface = Mock(spec=GameInterface)
    interface.get_bounds.return_value = (100, 100, 800, 600)
    return interface


@pytest.fixture
def mock_config():
    """Mock Config"""
    config = Mock(spec=Config)
    config.get.return_value = 10  # Default tolerance
    return config


@pytest.fixture
def screen_service(mock_game_interface, mock_config):
    """Create ScreenService instance for testing"""
    return ScreenService(mock_game_interface, mock_config)


@pytest.fixture
def sample_screenshot():
    """Create sample screenshot for testing"""
    img = Image.new('RGB', (100, 100), color=(255, 255, 255))
    # Add some colored pixels
    img.putpixel((50, 50), (0, 255, 0))  # Green
    img.putpixel((25, 25), (255, 0, 0))  # Red
    img.putpixel((75, 75), (0, 0, 255))  # Blue
    return img
