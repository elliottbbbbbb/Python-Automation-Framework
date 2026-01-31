"""
Login Queries - CQRS Query layer for login/disconnect state detection.

Handles:
- Disconnect screen detection ("You were disconnected from the server")
- Login screen detection ("Play Now" button)
- Lobby screen detection ("CLICK HERE TO PLAY")

Query layer responsibilities:
- READ-ONLY operations
- Detect login/logout state via template matching
- No mutations or actions
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

import cv2 as cv
import numpy as np

from osrsbot.queries.bank_queries import _resolve_template_path
from osrsbot.services.screen_service import ScreenService

logger = logging.getLogger(__name__)


class LoginQueries:
    """Query layer for login/disconnect state detection."""

    # Template paths for the 3 login screens
    OK_BUTTON_TEMPLATE = "src/osrsbot/images/bot/login/ok_button.png"
    PLAY_NOW_TEMPLATE = "src/osrsbot/images/bot/login/play_now_button.png"
    CLICK_TO_PLAY_TEMPLATE = "src/osrsbot/images/bot/login/click_to_play_button.png"

    # Default confidence threshold for login screen detection
    DEFAULT_THRESHOLD = 0.6

    def __init__(self, screen: ScreenService) -> None:
        """
        Initialize login queries.

        Args:
            screen: Screen capture service
        """
        self.screen = screen

    def _find_template(
        self, template_path: str, threshold: float = DEFAULT_THRESHOLD
    ) -> Optional[Tuple[int, int, float]]:
        """
        Find a template on the full screen (no region restriction).

        Args:
            template_path: Path to template image
            threshold: Match confidence threshold (0.0-1.0)

        Returns:
            Tuple of (center_x, center_y, confidence) if found, None otherwise
        """
        try:
            resolved_path = _resolve_template_path(template_path)
            template = cv.imread(str(resolved_path), cv.IMREAD_COLOR)
            if template is None:
                logger.warning(f"Failed to load login template: {template_path}")
                return None

            screenshot = self.screen.capture()
            if screenshot is None:
                logger.warning("Failed to capture screenshot for login detection")
                return None

            img_np = cv.cvtColor(np.array(screenshot), cv.COLOR_RGB2BGR)
            result = cv.matchTemplate(img_np, template, cv.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv.minMaxLoc(result)

            template_name = Path(template_path).name

            if max_val >= threshold:
                x, y = max_loc
                h, w = template.shape[:2]
                center_x = x + w // 2
                center_y = y + h // 2
                logger.info(
                    f"Login screen detected: '{template_name}' "
                    f"at ({center_x}, {center_y}) confidence={max_val:.3f}"
                )
                return (center_x, center_y, max_val)

            return None

        except Exception as e:
            logger.error(f"Error in login template detection: {e}")
            return None

    def find_ok_button(self) -> Optional[Tuple[int, int, float]]:
        """Find the 'Ok' button on the disconnect screen.

        Returns:
            Tuple of (center_x, center_y, confidence) if found, None otherwise
        """
        return self._find_template(self.OK_BUTTON_TEMPLATE)

    def find_play_now_button(self) -> Optional[Tuple[int, int, float]]:
        """Find the 'Play Now' button on the login screen.

        Returns:
            Tuple of (center_x, center_y, confidence) if found, None otherwise
        """
        return self._find_template(self.PLAY_NOW_TEMPLATE)

    def find_click_to_play_button(self) -> Optional[Tuple[int, int, float]]:
        """Find the 'CLICK HERE TO PLAY' button on the lobby screen.

        Returns:
            Tuple of (center_x, center_y, confidence) if found, None otherwise
        """
        return self._find_template(self.CLICK_TO_PLAY_TEMPLATE)

    def is_disconnected(self) -> bool:
        """Check if the disconnect screen ('Ok' button) is visible."""
        return self.find_ok_button() is not None

    def is_on_login_screen(self) -> bool:
        """Check if the login screen ('Play Now' button) is visible."""
        return self.find_play_now_button() is not None

    def is_on_lobby_screen(self) -> bool:
        """Check if the lobby screen ('CLICK HERE TO PLAY') is visible."""
        return self.find_click_to_play_button() is not None

    def is_logged_out(self) -> bool:
        """Check if ANY of the 3 logout/login screens are visible."""
        return self.is_disconnected() or self.is_on_login_screen() or self.is_on_lobby_screen()

    def get_login_state(self) -> str:
        """
        Determine the current login state.

        Returns:
            One of: 'disconnected', 'login_screen', 'lobby', 'logged_in'
        """
        if self.is_disconnected():
            return "disconnected"
        if self.is_on_login_screen():
            return "login_screen"
        if self.is_on_lobby_screen():
            return "lobby"
        return "logged_in"
