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
import pywinctl as gw
from typing import Tuple, Optional

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
        """
        Initialize game interface.

        Args:
            config: Configuration instance

        Raises:
            RuntimeError: If window not found
        """
        self.config = config
        window_title = config.get("window_title")

        if not window_title:
            raise ValueError("Window title must be set in config")

        logger.info(f"Initializing GameInterface for: '{window_title}'")
        self.window_title = window_title
        self.window = self._find_window()
        logger.info(f"Successfully attached to window: {self.window.title}")

    def _find_window(self) -> gw.Window:
        """Find the game window by title."""
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
        return windows[0]

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
        """
        Get window bounds.

        Returns:
            (left, top, width, height) tuple
        """
        if not self.window or not hasattr(self.window, 'topleft'):
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
        """
        Convert window-relative coordinates to absolute screen coordinates.

        Args:
            x: Relative X coordinate
            y: Relative Y coordinate

        Returns:
            (absolute_x, absolute_y) tuple
        """
        left, top, _, _ = self.get_bounds()
        return (left + x, top + y)

    def absolute_to_relative(self, x: int, y: int) -> Tuple[int, int]:
        """
        Convert absolute screen coordinates to window-relative coordinates.

        Args:
            x: Absolute X coordinate
            y: Absolute Y coordinate

        Returns:
            (relative_x, relative_y) tuple
        """
        left, top, _, _ = self.get_bounds()
        return (x - left, y - top)

    def is_in_bounds(self, x: int, y: int, relative: bool = True) -> bool:
        """
        Check if coordinates are within window bounds.

        Args:
            x: X coordinate
            y: Y coordinate
            relative: If True, coordinates are relative to window

        Returns:
            True if coordinates are within window
        """
        _, _, width, height = self.get_bounds()

        if relative:
            return 0 <= x < width and 0 <= y < height
        else:
            left, top, width, height = self.get_bounds()
            return left <= x < left + width and top <= y < top + height

    def activate(self) -> bool:
        """
        Bring game window to foreground.

        Returns:
            True if successful
        """
        try:
            if hasattr(self.window, 'activate'):
                self.window.activate()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to activate window: {e}")
            return False

    def is_active(self) -> bool:
        """
        Check if game window is currently active/focused.

        Returns:
            True if window is active
        """
        try:
            if hasattr(self.window, 'isActive'):
                return self.window.isActive
            return False
        except Exception:
            return False

    def get_title(self) -> str:
        """Get current window title."""
        try:
            return self.window.title if hasattr(self.window, 'title') else ""
        except Exception:
            return ""

    def exists(self) -> bool:
        """
        Check if window still exists.

        Returns:
            True if window exists
        """
        try:
            _ = self.window.title
            return True
        except Exception:
            return False
