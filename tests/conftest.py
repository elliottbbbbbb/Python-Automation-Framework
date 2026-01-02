"""
Shared pytest fixtures for OSRSbot testing.

Provides mock objects and test data for unit tests.
"""

from unittest.mock import Mock

import numpy as np
import pytest
from PIL import Image


@pytest.fixture
def mock_config():
    """
    Mock Config with common test data.

    Returns mock config that responds to get() calls with predefined values.
    """
    config = Mock()
    config.get.side_effect = lambda *keys, default=None: {
        ("timings", "wait", "short"): (0.1, 0.3),
        ("timings", "wait", "medium"): (0.3, 0.6),
        ("timings", "wait", "long"): (0.6, 1.0),
        ("colors", "combat_red"): "#FF0000",
        ("colors", "combat_green"): "#00FF00",
        ("tolerances", "color_match"): 10,
        ("coordinates", "hp", "x"): 100,
        ("coordinates", "hp", "y"): 50,
    }.get(tuple(keys), default)
    return config


@pytest.fixture
def mock_mouse():
    """
    Mock MouseService.

    Returns mock mouse service with all methods stubbed.
    """
    mouse = Mock()
    mouse.move_to.return_value = None
    mouse.click.return_value = None
    mouse.click_at.return_value = None
    mouse.drag_to.return_value = None
    mouse.random_movement.return_value = None
    return mouse


@pytest.fixture
def mock_screen():
    """
    Mock ScreenService.

    Returns mock screen service with common return values.
    """
    screen = Mock()
    screen.capture.return_value = Image.new("RGB", (100, 100))
    screen.capture_grayscale.return_value = np.zeros((100, 100), dtype=np.uint8)
    screen.get_pixel_color.return_value = (255, 0, 0)
    screen.find_color.return_value = [(50, 50), (75, 75)]
    screen.find_color_with_distance.return_value = [((50, 50), 10.0), ((75, 75), 20.0)]
    return screen


@pytest.fixture
def mock_template_service():
    """
    Mock TemplateMatchService.

    Returns mock template service with button/grid detection.
    """
    template = Mock()
    template.detect_button.return_value = True
    template.detect_grid.return_value = True
    template.get_button.return_value = None
    template.get_grid.return_value = None
    return template


@pytest.fixture
def mock_window():
    """
    Mock window handle for GameInterface.

    Returns mock window with bounds.
    """
    window = Mock()
    window.title = "RuneLite - Test"
    window.left = 100
    window.top = 100
    window.width = 800
    window.height = 600
    return window


@pytest.fixture
def mock_window_getter(mock_window):
    """
    Mock window getter callable.

    Returns function that returns mock window.
    """
    return lambda: mock_window


@pytest.fixture
def sample_screenshot():
    """
    Generate test screenshot with known color patterns.

    Returns PIL Image with colored squares:
    - Top-left (50x50): Red
    - Center (50x50): Green
    - Bottom-right (50x50): Blue
    """
    arr = np.zeros((200, 200, 3), dtype=np.uint8)
    arr[50:100, 50:100] = [255, 0, 0]  # Red square
    arr[100:150, 100:150] = [0, 255, 0]  # Green square
    arr[150:200, 150:200] = [0, 0, 255]  # Blue square
    return Image.fromarray(arr)


@pytest.fixture
def sample_grayscale():
    """
    Generate test grayscale screenshot.

    Returns numpy array with gray patterns.
    """
    arr = np.zeros((100, 100), dtype=np.uint8)
    arr[25:75, 25:75] = 128  # Gray square in center
    return arr


@pytest.fixture
def sample_colors():
    """
    Common RGB color tuples for testing.

    Returns dict of color name to RGB tuple.
    """
    return {
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "white": (255, 255, 255),
        "black": (0, 0, 0),
        "combat_red": (99, 21, 19),
        "combat_green": (7, 139, 54),
    }


@pytest.fixture
def sample_config_dict():
    """
    Sample configuration dictionary for Config testing.

    Returns nested dict matching config.json structure.
    """
    return {
        "timings": {
            "wait": {"short": [0.1, 0.3], "medium": [0.3, 0.6], "long": [0.6, 1.0]}
        },
        "coordinates": {
            "hp": {"x": 100, "y": 50, "width": 30, "height": 15},
            "prayer": {"x": 100, "y": 70, "width": 30, "height": 15},
        },
        "colors": {"combat_red": "#631513", "combat_green": "#078B36"},
        "tolerances": {"color_match": 10},
    }
