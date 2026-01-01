"""
GameInterface - Window management and coordinate translation only.

This class is now focused ONLY on:
- Finding the game window
- Managing window state
- Converting relative to absolute coordinates

It NO LONGER handles:
- Mouse clicking (use MouseService)
- Color detection (use ScreenService)
- Screenshots (use ScreenService)
"""

import logging
from typing import Optional, Tuple

import pywinctl as gw

from osrsbot.constants import COORDINATES
from osrsbot.models.config import Config

logger = logging.getLogger(__name__)


class GameInterface:
    """
    Manages game window and coordinate system.

    Responsibilities:
    - Find and track game window
    - Convert relative <-> absolute coordinates
    - Provide window bounds to services
    """

    def __init__(self, config: Config):
        self.config = config
        window_title = config.get("window_title")

        if not window_title:
            raise ValueError("Window title must be set in config")

        logger.info(f"Initializing GameInterface for: '{window_title}'")
        self.window_title = window_title
        self.window = self._find_window()
        logger.info(f"Successfully attached to window: {self.window.title}")

    def _find_window(self) -> gw.Window:
        if not self.window_title:
            raise ValueError("Window title cannot be empty")

        logger.debug(f"Searching for window: '{self.window_title}'")

        try:
            windows = gw.getWindowsWithTitle(self.window_title)
        except Exception as e:
            logger.error(f"Window search failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to search for windows: {e}") from e

        if not windows:
            raise RuntimeError(
                f"Window '{self.window_title}' not found! Is the game running?"
            )

        logger.debug(f"Found {len(windows)} matching window(s)")
        return windows[COORDINATES.first_window_index]

    def refresh_window(self) -> bool:
        """
        Refresh window handle (useful if window was closed/reopened).

        Returns:
            True if window found, False otherwise
        """
        try:
            self.window = self._find_window()
            return True
        except Exception as e:
            logger.warning(f"Failed to refresh window: {e}")
            return False

    def get_bounds(self) -> Tuple[int, int, int, int]:
        if not self.window or not hasattr(self.window, "topleft"):
            raise RuntimeError("Window no longer available")

        left, top = self.window.topleft
        width, height = self.window.size

        return (left, top, width, height)

    def get_window_position(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get window position (alias for get_bounds for backward compatibility).

        Returns:
            (left, top, width, height) tuple or None if window unavailable
        """
        try:
            return self.get_bounds()
        except Exception:
            return None

    def relative_to_absolute(self, x: int, y: int) -> Tuple[int, int]:
        left, top, _, _ = self.get_bounds()
        return (left + x, top + y)

    def absolute_to_relative(self, x: int, y: int) -> Tuple[int, int]:
        left, top, _, _ = self.get_bounds()
        return (x - left, y - top)

    def is_in_bounds(self, x: int, y: int, relative: bool = True) -> bool:
        _, _, width, height = self.get_bounds()

        if relative:
            return (
                COORDINATES.origin_x <= x < width and COORDINATES.origin_y <= y < height
            )
        else:
            left, top, width, height = self.get_bounds()
            return left <= x < left + width and top <= y < top + height

    def activate(self) -> bool:
        try:
            if hasattr(self.window, "activate"):
                self.window.activate()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to activate window: {e}")
            return False

    def is_active(self) -> bool:
        try:
            if hasattr(self.window, "isActive"):
                return self.window.isActive
            return False
        except Exception:
            return False

    def get_title(self) -> str:
        try:
            return self.window.title if hasattr(self.window, "title") else ""
        except Exception:
            return ""

    def exists(self) -> bool:
        try:
            _ = self.window.title
            return True
        except Exception:
            return False
