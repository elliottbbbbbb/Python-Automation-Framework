"""
Bank Actions - CQRS Command layer for bank-related actions.

Handles:
- Clicking at coordinates (banker, items, buttons)
- Typing in search boxes
- All bank-related mouse/keyboard interactions

Command layer responsibilities:
- WRITE operations (mutations)
- Execute clicks at given coordinates
- NO query logic - bot scripts query first, then call actions

Architecture note:
  Bot scripts should query via self.state (BankQueries) to find elements,
  then call these action methods with the coordinates. This keeps Commands
  layer pure (no imports from Queries layer).
"""

import logging
from typing import Optional, Tuple

import pyautogui

from osrsbot.services.mouse_service import MouseService
from osrsbot.utils.coordinate_helpers import CoordinateResolver
from osrsbot.utils.timing_helpers import TimingHelper

logger = logging.getLogger(__name__)


class BankActions:
    """Command layer for bank-related actions (clicks/typing only)."""

    def __init__(
        self,
        mouse: MouseService,
        coord_resolver: CoordinateResolver,
        timing: TimingHelper,
    ):
        """
        Initialize bank actions.

        Args:
            mouse: Mouse service for clicking
            coord_resolver: Coordinate resolution helper
            timing: Timing helper for waits
        """
        self.mouse = mouse
        self.coord_resolver = coord_resolver
        self.timing = timing

    def click_at(
        self,
        center_x: int,
        center_y: int,
        item_name: str = "target",
        move_style: str = "curved",
        speed_multiplier: float = 1.0,
    ) -> bool:
        """
        Click at given relative coordinates.

        Args:
            center_x: Relative X coordinate (from query result)
            center_y: Relative Y coordinate (from query result)
            item_name: Name for logging
            move_style: Mouse movement style
            speed_multiplier: Speed variance multiplier

        Returns:
            True if click successful
        """
        abs_x, abs_y = self.coord_resolver.to_absolute(center_x, center_y)
        success = self.mouse.click_at(
            abs_x, abs_y, move_style=move_style, speed_multiplier=speed_multiplier
        )

        if success:
            logger.info(f"Clicked {item_name} at ({center_x}, {center_y})")
        else:
            logger.warning(f"Failed to click {item_name}")

        return success

    def type_text(self, text: str, interval: float = 0.05) -> bool:
        """
        Type text (e.g., in bank search box).

        Args:
            text: Text to type
            interval: Delay between keypresses

        Returns:
            True if successful
        """
        try:
            logger.debug(f"Typing: '{text}'")
            pyautogui.write(text, interval=interval)
            return True
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return False

    def press_escape(self) -> bool:
        """Press escape key (e.g., to clear search or close interface)."""
        try:
            pyautogui.press("escape")
            return True
        except Exception as e:
            logger.error(f"Failed to press escape: {e}")
            return False
