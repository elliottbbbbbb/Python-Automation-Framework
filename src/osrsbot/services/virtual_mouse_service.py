"""
VirtualMouseService - Sends mouse input directly to window without moving physical cursor.

Uses Windows API to send mouse messages directly to the game window,
allowing you to use your computer for other tasks while the bot runs.
"""
import time
import random
import logging
from typing import Tuple, Optional, Literal
import win32gui
import win32con
import win32api

from osrsbot.services.mouse_service import MouseConfig, MovementStyle

logger = logging.getLogger(__name__)


class VirtualMouseService:
    """
    Virtual mouse service that sends input directly to window.

    Doesn't move your physical cursor - sends clicks directly to the
    game window using Windows messages.
    """

    def __init__(self, window_title: str, config: MouseConfig = None):
        """
        Initialize virtual mouse service.

        Args:
            window_title: Title of the window to send input to (e.g., "RuneLite - username")
            config: Mouse configuration
        """
        self.config = config or MouseConfig()
        self.window_title = window_title
        self.hwnd = None
        self._find_window()

    def _find_window(self) -> bool:
        """Find and store the window handle."""
        try:
            self.hwnd = win32gui.FindWindow(None, self.window_title)
            if self.hwnd:
                logger.info(f"Found window '{self.window_title}' with handle {self.hwnd}")
                return True
            else:
                logger.error(f"Could not find window with title '{self.window_title}'")
                return False
        except Exception as e:
            logger.error(f"Error finding window: {e}", exc_info=True)
            return False

    def _screen_to_client(self, x: int, y: int) -> Tuple[int, int]:
        """
        Convert absolute screen coordinates to window-relative coordinates.

        Args:
            x: Absolute screen X
            y: Absolute screen Y

        Returns:
            (client_x, client_y) relative to window
        """
        if not self.hwnd:
            self._find_window()

        try:
            # Get window position
            rect = win32gui.GetWindowRect(self.hwnd)
            window_x = rect[0]
            window_y = rect[1]

            # Convert to client coordinates
            client_x = x - window_x
            client_y = y - window_y

            return (client_x, client_y)
        except Exception as e:
            logger.error(f"Error converting coordinates: {e}", exc_info=True)
            return (x, y)

    def click(
        self,
        x: int,
        y: int,
        button: Literal["left", "right", "middle"] = "left",
        variance: bool = True,
        delay_after: bool = True
    ) -> bool:
        """
        Click at absolute screen coordinates using Windows messages.

        Doesn't move your physical cursor.

        Args:
            x: Absolute screen X coordinate
            y: Absolute screen Y coordinate
            button: Mouse button to click
            variance: Add random offset to click position
            delay_after: Add human-like delay after click

        Returns:
            True if click successful
        """
        try:
            if not self.hwnd:
                if not self._find_window():
                    return False

            # Add variance
            if variance:
                offset_x = random.randint(
                    -self.config.click_variance,
                    self.config.click_variance
                )
                offset_y = random.randint(
                    -self.config.click_variance,
                    self.config.click_variance
                )
                x += offset_x
                y += offset_y

            # Convert to window-relative coordinates
            client_x, client_y = self._screen_to_client(x, y)

            # Pack coordinates into lParam
            lParam = win32api.MAKELONG(client_x, client_y)

            # Determine message types based on button
            if button == "left":
                down_msg = win32con.WM_LBUTTONDOWN
                up_msg = win32con.WM_LBUTTONUP
                wParam = win32con.MK_LBUTTON
            elif button == "right":
                down_msg = win32con.WM_RBUTTONDOWN
                up_msg = win32con.WM_RBUTTONUP
                wParam = win32con.MK_RBUTTON
            elif button == "middle":
                down_msg = win32con.WM_MBUTTONDOWN
                up_msg = win32con.WM_MBUTTONUP
                wParam = win32con.MK_MBUTTON
            else:
                logger.error(f"Invalid button: {button}")
                return False

            # Send mouse down
            win32gui.SendMessage(self.hwnd, down_msg, wParam, lParam)

            # Small delay between down and up
            time.sleep(random.uniform(0.01, 0.03))

            # Send mouse up
            win32gui.SendMessage(self.hwnd, up_msg, 0, lParam)

            if delay_after:
                delay = random.uniform(*self.config.post_click_delay)
                time.sleep(delay)

            logger.debug(f"Virtual clicked at screen({x}, {y}) -> client({client_x}, {client_y}) with {button} button")
            return True

        except Exception as e:
            logger.error(f"Failed to virtual click: {e}", exc_info=True)
            return False

    def click_at(
        self,
        x: int,
        y: int,
        button: Literal["left", "right", "middle"] = "left",
        move_style: MovementStyle = "instant",
        variance: bool = True
    ) -> bool:
        """
        Click at absolute coordinates.

        Note: move_style is ignored for virtual mouse (no movement needed).

        Args:
            x: Target X coordinate (absolute screen position)
            y: Target Y coordinate (absolute screen position)
            button: Mouse button to click
            move_style: Ignored (compatibility with regular MouseService)
            variance: Add random offset to click

        Returns:
            True if successful
        """
        # For virtual mouse, we don't need to move, just add a small delay
        # to simulate the time it would take to move
        if move_style != "instant":
            time.sleep(random.uniform(0.05, 0.15))

        return self.click(x, y, button=button, variance=variance)

    def move_to(
        self,
        x: int,
        y: int,
        style: MovementStyle = "instant",
        duration: Optional[float] = None
    ) -> bool:
        """
        Virtual mouse doesn't move cursor, so this is a no-op.

        Returns True for compatibility with MouseService interface.
        """
        logger.debug(f"Virtual mouse: move_to({x}, {y}) is no-op")
        return True

    def get_position(self) -> Tuple[int, int]:
        """
        Returns (0, 0) since virtual mouse doesn't track position.

        For compatibility with MouseService interface.
        """
        return (0, 0)
