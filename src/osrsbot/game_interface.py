import logging
import random
import pyautogui
import pywinctl as gw
from typing import Tuple, Optional, cast

from osrsbot.config import Config

logger = logging.getLogger(__name__)


class GameInterface:
    """Low-level interface for clicking and color detection"""

    def __init__(self, config: Config) -> None:
        logger.info("Initializing GameInterface")
        self.config = config
        self.window = self._find_window()
        logger.info(f"Attached to window: {self.window.title}")

    def _find_window(self) -> gw.Window:
        """Find the game window by title from config."""
        title = self.config.get("window_title")

        if not title:
            logger.error("Window title not in config")
            raise ValueError("Window title must be set in config")

        logger.debug(f"Searching for window: '{title}'")

        try:
            windows = gw.getWindowsWithTitle(title)
        except Exception as e:
            logger.error(f"Window search failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to search for windows: {e}") from e

        if not windows:
            logger.error(f"Window not found: '{title}'")
            raise RuntimeError(
                f"Window '{title}' not found! Is the game running?")

        logger.debug(f"Found {len(windows)} matching window(s)")
        return windows[0]

    def click(self, x: int, y: int, button: str = 'left',
              offset: Tuple[int, int] = (0, 0)) -> bool:
        """Click at window-relative coordinates. Returns False if out of bounds."""
        if not (self.window and hasattr(self.window, 'topleft')):
            raise RuntimeError("Window no longer available")

        left, top = self.window.topleft
        width, height = self.window.size

        if not (0 <= x < width and 0 <= y < height):
            logger.warning(f"Out-of-bounds click: ({x},{y})")
            return False

        ox = random.randint(-offset[0], offset[0]) if offset[0] else 0
        oy = random.randint(-offset[1], offset[1]) if offset[1] else 0

        pyautogui.click(left + x + ox, top + y + oy, button=button)
        return True

    def click_coord(self, coord: dict, button: str = 'left') -> bool:
        """Click using config coordinate dict with 'x' and 'y' keys."""
        if not coord or not isinstance(coord, dict):
            raise ValueError("coord must be a dictionary")

        if 'x' not in coord or 'y' not in coord:
            raise ValueError("coord must have 'x' and 'y' keys")

        try:
            x = int(coord['x'])
            y = int(coord['y'])
        except (ValueError, TypeError) as e:
            raise ValueError(f"coord values must be integers: {e}") from e

        return self.click(x, y, button)

    def find_color(self, hex_color: str,
                   tolerance: Optional[int] = None) -> Optional[Tuple[int, int]]:
        """Find first pixel matching hex_color. Returns (x,y) or None."""
        if not hex_color:
            raise ValueError("hex_color is required")

        if tolerance is None:
            tolerance = cast(int, self.config.get("tolerances", "color_match"))
            if tolerance is None:
                tolerance = 10

        try:
            target = self._hex_to_rgb(hex_color)
        except ValueError as e:
            logger.error(f"Invalid hex color '{hex_color}': {e}")
            raise

        if not (self.window and hasattr(self.window, 'topleft')):
            raise RuntimeError("Window no longer available")

        left, top = self.window.topleft
        width, height = self.window.size

        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        pixels = screenshot.load()

        if pixels is None:
            logger.error("Screenshot pixel data is None")
            return None

        for x in range(screenshot.width):
            for y in range(screenshot.height):
                pixel = cast(Tuple[int, int, int, int], pixels[x, y])[:3]
                if self._color_match(pixel, target, tolerance):
                    return (x, y)

        return None

    def click_color(self, hex_color: str, offset: Tuple[int, int] = (
            0, 0), tolerance: Optional[int] = None) -> bool:
        """Find and click a color. Returns True if found and clicked."""
        pos = self.find_color(hex_color, tolerance)
        if pos:
            return self.click(pos[0] + offset[0], pos[1] + offset[1])
        return False

    def get_pixel(self, x: int, y: int) -> Tuple[int, int, int]:
        """Get RGB color at window-relative coordinate."""
        if not (self.window and hasattr(self.window, 'topleft')):
            raise RuntimeError("Window no longer available")

        left, top = self.window.topleft
        width, height = self.window.size

        if not (0 <= x < width and 0 <= y < height):
            raise ValueError(f"Coordinates ({x}, {y}) outside window bounds")

        return pyautogui.pixel(left + x, top + y)

    def get_window_position(self) -> Optional[Tuple[int, int, int, int]]:
        """Get window position as (left, top, width, height)."""
        if not (self.window and hasattr(self.window, 'topleft')):
            return None
        left, top = self.window.topleft
        width, height = self.window.size
        return (left, top, width, height)

    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None):
        """Screenshot of window or region (x, y, width, height)."""
        if not (self.window and hasattr(self.window, 'topleft')):
            raise RuntimeError("Window no longer available")

        left, top = self.window.topleft

        if region:
            if len(region) != 4:
                raise ValueError("region must be (x, y, width, height)")

            return pyautogui.screenshot(region=(
                left + region[0],
                top + region[1],
                region[2],
                region[3]
            ))
        else:
            width, height = self.window.size
            return pyautogui.screenshot(region=(left, top, width, height))

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex string to RGB tuple."""
        if not hex_color:
            raise ValueError("hex_color cannot be empty")

        hex_color = hex_color.lstrip('#')

        if len(hex_color) != 6:
            raise ValueError(
                f"Invalid hex color '{hex_color}': must be 6 chars (RRGGBB)")

        if not all(c in '0123456789ABCDEFabcdef' for c in hex_color):
            raise ValueError(
                f"Invalid hex color '{hex_color}': non-hex characters")

        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (r, g, b)
        except ValueError as e:
            raise ValueError(
                f"Failed to parse hex color '{hex_color}': {e}") from e

    @staticmethod
    def _color_match(c1: Tuple[int, int, int],
                     c2: Tuple[int, int, int], tolerance: int) -> bool:
        """Check if two RGB colors match within tolerance."""
        return all(abs(c1[i] - c2[i]) <= tolerance for i in range(3))
