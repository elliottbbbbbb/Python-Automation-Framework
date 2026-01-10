"""
KeyboardService - Handles keyboard input with humanization.

Uses native keyboard library on Windows for better control.
Fallback to pyautogui for cross-platform compatibility.
"""

import logging
import platform
import random
import time
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# Try to import keyboard library (Windows-only, more reliable)
KEYBOARD_AVAILABLE = False
try:
    if platform.system() == "Windows":
        import keyboard
        KEYBOARD_AVAILABLE = True
        logger.debug("Using native keyboard library (Windows)")
except ImportError:
    logger.debug("Keyboard library not available, will use pyautogui fallback")

# Fallback to pyautogui
import pyautogui


KeyMode = Literal["instant", "humanized"]


class KeyboardService:
    """
    Professional keyboard service with human-like typing patterns.

    Features:
    - Key press/release control
    - Text typing with realistic delays
    - Hold key functionality
    - Configurable typing speed variance
    """

    def __init__(
        self,
        typing_speed_min: float = 0.05,
        typing_speed_max: float = 0.15,
        key_hold_duration: float = 0.1,
    ):
        """
        Initialize keyboard service.

        Args:
            typing_speed_min: Minimum delay between keystrokes (seconds)
            typing_speed_max: Maximum delay between keystrokes (seconds)
            key_hold_duration: How long to hold keys when pressing (seconds)
        """
        self.typing_speed_min = typing_speed_min
        self.typing_speed_max = typing_speed_max
        self.key_hold_duration = key_hold_duration
        self.use_native = KEYBOARD_AVAILABLE

    def press(self, key: str, mode: KeyMode = "humanized") -> bool:
        """
        Press and release a key.

        Args:
            key: Key name (e.g., 'a', 'enter', 'space', 'ctrl', 'f1')
            mode: 'instant' or 'humanized' (adds natural delay)

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.use_native:
                # Native keyboard library
                keyboard.press_and_release(key)
            else:
                # Fallback to pyautogui
                pyautogui.press(key)

            if mode == "humanized":
                # Add natural post-key delay
                delay = random.uniform(0.05, 0.15)
                time.sleep(delay)

            logger.debug(f"Pressed key: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to press key '{key}': {e}", exc_info=True)
            return False

    def press_and_hold(self, key: str, duration: float) -> bool:
        """
        Press key and hold for specified duration.

        Args:
            key: Key name
            duration: How long to hold (seconds)

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.use_native:
                keyboard.press(key)
                time.sleep(duration)
                keyboard.release(key)
            else:
                # Pyautogui doesn't have explicit hold, simulate with keyDown/keyUp
                pyautogui.keyDown(key)
                time.sleep(duration)
                pyautogui.keyUp(key)

            logger.debug(f"Held key '{key}' for {duration:.2f}s")
            return True

        except Exception as e:
            logger.error(f"Failed to hold key '{key}': {e}", exc_info=True)
            return False

    def write(
        self, text: str, typing_speed: Optional[float] = None, mode: KeyMode = "humanized"
    ) -> bool:
        """
        Type text with human-like delays.

        Args:
            text: Text to type
            typing_speed: Override default typing speed (delay between chars)
            mode: 'instant' or 'humanized'

        Returns:
            True if successful, False otherwise
        """
        try:
            if mode == "instant":
                # Fast typing without delays
                if self.use_native:
                    keyboard.write(text, delay=0)
                else:
                    pyautogui.write(text, interval=0)
            else:
                # Humanized typing with variance
                for char in text:
                    if self.use_native:
                        keyboard.write(char, delay=0)
                    else:
                        pyautogui.write(char, interval=0)

                    # Variable delay between characters
                    if typing_speed is not None:
                        delay = typing_speed
                    else:
                        delay = random.uniform(
                            self.typing_speed_min, self.typing_speed_max
                        )

                    # Occasional longer pauses (thinking)
                    if random.random() < 0.05:
                        delay *= random.uniform(2.0, 4.0)

                    time.sleep(delay)

            logger.debug(f"Typed text: '{text}' (mode: {mode})")
            return True

        except Exception as e:
            logger.error(f"Failed to type text: {e}", exc_info=True)
            return False

    def hotkey(self, *keys: str) -> bool:
        """
        Press key combination (e.g., ctrl+c, alt+f4).

        Args:
            *keys: Key names in order (e.g., 'ctrl', 'c')

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.use_native:
                # Native keyboard: pass as string with '+'
                hotkey_str = "+".join(keys)
                keyboard.send(hotkey_str)
            else:
                # Pyautogui: pass as list
                pyautogui.hotkey(*keys)

            logger.debug(f"Pressed hotkey: {'+'.join(keys)}")
            return True

        except Exception as e:
            logger.error(f"Failed to press hotkey {'+'.join(keys)}: {e}", exc_info=True)
            return False

    def is_pressed(self, key: str) -> bool:
        """
        Check if key is currently pressed.

        Args:
            key: Key name

        Returns:
            True if pressed, False otherwise

        Note: Only works with native keyboard library (Windows)
        """
        if not self.use_native:
            logger.warning("is_pressed() only available on Windows with keyboard library")
            return False

        try:
            return keyboard.is_pressed(key)
        except Exception as e:
            logger.error(f"Failed to check if key '{key}' is pressed: {e}")
            return False

    def send(self, key_sequence: str) -> bool:
        """
        Send key sequence (supports special syntax like 'ctrl+c', 'alt+tab').

        Args:
            key_sequence: Sequence like 'ctrl+c' or 'alt+f4'

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.use_native:
                keyboard.send(key_sequence)
            else:
                # Parse and execute with pyautogui
                keys = key_sequence.split("+")
                pyautogui.hotkey(*keys)

            logger.debug(f"Sent key sequence: {key_sequence}")
            return True

        except Exception as e:
            logger.error(f"Failed to send key sequence '{key_sequence}': {e}", exc_info=True)
            return False

    def tab(self, count: int = 1, delay: Optional[float] = None) -> bool:
        """
        Press Tab key multiple times (useful for UI navigation).

        Args:
            count: Number of times to press Tab
            delay: Delay between presses (uses humanized default if None)

        Returns:
            True if successful, False otherwise
        """
        try:
            for i in range(count):
                self.press("tab", mode="humanized")

                if delay is not None:
                    time.sleep(delay)
                elif count > 1:
                    # Add small delay between tabs
                    time.sleep(random.uniform(0.1, 0.3))

            logger.debug(f"Pressed Tab {count} time(s)")
            return True

        except Exception as e:
            logger.error(f"Failed to press Tab: {e}", exc_info=True)
            return False

    def enter(self, mode: KeyMode = "humanized") -> bool:
        """Convenience method to press Enter."""
        return self.press("enter", mode=mode)

    def escape(self, mode: KeyMode = "humanized") -> bool:
        """Convenience method to press Escape."""
        return self.press("escape", mode=mode)

    def space(self, mode: KeyMode = "humanized") -> bool:
        """Convenience method to press Space."""
        return self.press("space", mode=mode)

    def backspace(self, count: int = 1, mode: KeyMode = "humanized") -> bool:
        """
        Press Backspace multiple times.

        Args:
            count: Number of times to press
            mode: Key mode

        Returns:
            True if successful, False otherwise
        """
        try:
            for _ in range(count):
                self.press("backspace", mode=mode)

            logger.debug(f"Pressed Backspace {count} time(s)")
            return True

        except Exception as e:
            logger.error(f"Failed to press Backspace: {e}", exc_info=True)
            return False
