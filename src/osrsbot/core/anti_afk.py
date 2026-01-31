"""
Anti-AFK / Auto-Relogin module.

Detects when the game has logged the player out (6-hour timer, disconnect, etc.)
and automatically clicks through the 3 login screens to get back in-game.

Screens handled (in order):
1. Disconnect screen - "You were disconnected from the server." -> Click "Ok"
2. Login screen - "Welcome to RuneScape" with "Play Now" -> Click "Play Now"
3. Lobby screen - "Welcome to Old School RuneScape" -> Click "CLICK HERE TO PLAY"
"""

import logging
import random
import time
from typing import TYPE_CHECKING

from osrsbot.queries.login_queries import LoginQueries

if TYPE_CHECKING:
    from osrsbot.commands.game_actions import GameActions
    from osrsbot.services.screen_service import ScreenService

logger = logging.getLogger(__name__)

# Max attempts to click through each screen before giving up
MAX_SCREEN_RETRIES = 5

# Max total time (seconds) to spend trying to relogin before giving up
MAX_RELOGIN_TIMEOUT = 60

# Seconds between each state poll after clicking a button
POLL_INTERVAL = 2.0

# Max seconds to wait for a screen transition after clicking
TRANSITION_TIMEOUT = 15.0


class AntiAFK:
    """Handles automatic relogin when disconnected from the server."""

    def __init__(
        self,
        actions: "GameActions",
        screen: "ScreenService",
    ) -> None:
        """
        Initialize anti-AFK handler.

        Args:
            actions: Game actions facade (for mouse clicks and coordinate conversion)
            screen: Screen service (for screenshots)
        """
        self.actions = actions
        self.login_queries = LoginQueries(screen)

    def _click_template_result(self, result: tuple) -> None:
        """
        Click on a template match result with humanized movement.

        Args:
            result: Tuple of (center_x, center_y, confidence) from template match
        """
        cx, cy, confidence = result
        abs_x, abs_y = self.actions._to_absolute(cx, cy)
        self.actions.mouse.click_at(
            abs_x,
            abs_y,
            move_style="curved",
            speed_multiplier=self.actions._get_mouse_speed_multiplier(),
        )
        logger.debug(
            f"Clicked login button at ({abs_x}, {abs_y}), confidence={confidence:.3f}"
        )

    def _wait_between_screens(self) -> None:
        """Humanized delay between login screen transitions."""
        delay = random.uniform(1.5, 3.0)
        logger.debug(f"Waiting {delay:.1f}s between login screens")
        time.sleep(delay)

    def _wait_for_screen(self, target_state: str, timeout: float = TRANSITION_TIMEOUT) -> bool:
        """
        Poll every ~2s until a specific login screen appears.

        Args:
            target_state: The state we're waiting for (e.g. 'lobby', 'login_screen')
            timeout: Max seconds to wait before giving up

        Returns:
            True if the target screen appeared, False if timed out.
        """
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(POLL_INTERVAL)
            current = self.login_queries.get_login_state()
            logger.info(f"Polling: state={current} (waiting for '{target_state}')")
            if current == target_state:
                return True
        logger.warning(f"Timed out waiting for '{target_state}' screen to appear")
        return False

    def _wait_for_screen_gone(self, screen_state: str, timeout: float = TRANSITION_TIMEOUT) -> bool:
        """
        Poll every ~2s until a specific login screen disappears.

        Args:
            screen_state: The state we're waiting to disappear (e.g. 'lobby')
            timeout: Max seconds to wait before giving up

        Returns:
            True if the screen disappeared, False if timed out.
        """
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(POLL_INTERVAL)
            current = self.login_queries.get_login_state()
            logger.info(f"Polling: state={current} (waiting for '{screen_state}' to disappear)")
            if current != screen_state:
                return True
        logger.warning(f"Timed out waiting for '{screen_state}' screen to disappear")
        return False

    def _handle_disconnect_screen(self) -> bool:
        """
        Handle the disconnect screen by clicking 'Ok'.

        Returns:
            True if the Ok button was found and clicked, False otherwise.
        """
        for attempt in range(MAX_SCREEN_RETRIES):
            result = self.login_queries.find_ok_button()
            if result:
                logger.info(f"Disconnect screen detected (attempt {attempt + 1}), clicking Ok")
                self._click_template_result(result)
                self._wait_between_screens()
                return True
            time.sleep(0.5)

        logger.warning("Disconnect screen: Ok button not found after retries")
        return False

    def _handle_login_screen(self) -> bool:
        """
        Handle the login screen by clicking 'Play Now'.

        Returns:
            True if the Play Now button was found and clicked, False otherwise.
        """
        for attempt in range(MAX_SCREEN_RETRIES):
            result = self.login_queries.find_play_now_button()
            if result:
                logger.info(
                    f"Login screen detected (attempt {attempt + 1}), clicking Play Now"
                )
                self._click_template_result(result)
                self._wait_between_screens()
                return True
            time.sleep(0.5)

        logger.warning("Login screen: Play Now button not found after retries")
        return False

    def _handle_lobby_screen(self) -> bool:
        """
        Handle the lobby screen by clicking 'CLICK HERE TO PLAY'.

        Returns:
            True if the button was found and clicked, False otherwise.
        """
        for attempt in range(MAX_SCREEN_RETRIES):
            result = self.login_queries.find_click_to_play_button()
            if result:
                logger.info(
                    f"Lobby screen detected (attempt {attempt + 1}), clicking Click to Play"
                )
                self._click_template_result(result)
                self._wait_between_screens()
                return True
            time.sleep(0.5)

        logger.warning("Lobby screen: Click to Play button not found after retries")
        return False

    def check_and_relogin(self) -> bool:
        """
        Check if logged out and handle the full relogin sequence.

        Detects the current login state and clicks through all necessary
        screens to get back in-game. Handles partial states (e.g., if the
        player is already past the disconnect screen but still on login).

        Returns:
            True if a relogin was performed successfully, False if already
            logged in or relogin failed.
        """
        login_state = self.login_queries.get_login_state()

        if login_state == "logged_in":
            return False

        logger.info(f"Player is logged out (state: {login_state}), starting relogin sequence")
        start_time = time.time()

        # Step 1: Handle disconnect screen if present
        # After clicking Ok, wait for the login screen to appear
        if login_state == "disconnected":
            if not self._handle_disconnect_screen():
                logger.error("Failed to handle disconnect screen")
                return False
            if not self._wait_for_screen("login_screen"):
                logger.error("Login screen did not appear after dismissing disconnect")
                return False
            login_state = "login_screen"

        # Step 2: Handle login screen if present
        # After clicking Play Now, wait for the lobby screen to appear
        if login_state == "login_screen":
            if not self._handle_login_screen():
                logger.error("Failed to handle login screen")
                return False
            if not self._wait_for_screen("lobby"):
                logger.error("Lobby screen did not appear after clicking Play Now")
                return False
            login_state = "lobby"

        # Step 3: Handle lobby screen if present
        # After clicking Click to Play, wait for the lobby to disappear (= logged in)
        if login_state == "lobby":
            if not self._handle_lobby_screen():
                logger.error("Failed to handle lobby screen")
                return False
            if not self._wait_for_screen_gone("lobby"):
                logger.error("Lobby screen did not disappear after clicking")
                return False

        elapsed = time.time() - start_time
        logger.info(f"Relogin successful (took {elapsed:.1f}s)")
        return True
