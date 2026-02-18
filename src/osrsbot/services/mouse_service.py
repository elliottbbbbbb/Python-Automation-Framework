"""
MouseService - Handles all mouse movement and clicking with humanization.

Inspired by OSBC's Bezier curve implementation but with added flexibility.
"""

import logging
import random
import time
from dataclasses import dataclass
from typing import Literal, Optional, Tuple

import pyautogui

from osrsbot.constants import MOUSE_MOVEMENT, MovementStyle

logger = logging.getLogger(__name__)


@dataclass
class MouseConfig:
    """
    Configuration for mouse behavior.

    Defaults are set in constants.py for easy tuning.
    """

    min_speed: float = 0.1
    max_speed: float = 0.5
    overshoot_chance: float = 0.15
    overshoot_distance: int = 20
    click_variance: int = 3
    post_click_delay: Tuple[float, float] = (0.05, 0.15)


class MouseService:
    """
    Professional mouse service with human-like movement patterns.

    Features:
    - Multiple movement styles (linear, curved, overshoot)
    - Bezier curve movement (OSBC-inspired)
    - Click variance and humanization
    - Configurable speeds and behaviors
    """

    def __init__(self, config: MouseConfig = None):
        self.config = config or MouseConfig()
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0

    def move_to(
        self,
        x: int,
        y: int,
        style: MovementStyle = "curved",
        duration: Optional[float] = None,
        speed_multiplier: float = 1.0,
    ) -> bool:
        """
        Move mouse to absolute screen coordinates.

        Args:
            x: Target X coordinate (absolute screen position)
            y: Target Y coordinate (absolute screen position)
            style: Movement style to use
            duration: Override automatic duration calculation
            speed_multiplier: Anti-ban speed variance (1.0 = normal, >1.0 = slower, <1.0 = faster)

        Returns:
            True if movement successful
        """
        try:
            current_x, current_y = pyautogui.position()

            distance = ((x - current_x) ** 2 + (y - current_y) ** 2) ** 0.5

            if duration is None:
                duration = random.uniform(
                    self.config.min_speed, self.config.max_speed
                ) * (1 + distance / MOUSE_MOVEMENT.distance_factor)

            # Apply anti-ban speed variance
            duration *= speed_multiplier

            # Introduce small variation so repeated 'curved' calls don't look identical
            if style == "curved":
                r = random.random()
                if r < 0.12:
                    style = "linear"
                elif r < 0.28:
                    style = "overshoot"

            if style == "instant":
                pyautogui.moveTo(x, y, duration=0)

            elif style == "linear":
                pyautogui.moveTo(x, y, duration=duration)

            elif style == "curved":
                self._move_bezier(current_x, current_y, x, y, duration)

            elif style == "overshoot":
                self._move_with_overshoot(current_x, current_y, x, y, duration)

            elif style == "random":
                chosen_style = random.choice(["linear", "curved", "overshoot"])
                return self.move_to(x, y, style=chosen_style, duration=duration)

            logger.debug(f"Moved to ({x}, {y}) using {style} style")
            return True

        except Exception as e:
            logger.error(f"Failed to move mouse: {e}", exc_info=True)
            return False

    def click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: Literal["left", "right", "middle"] = "left",
        variance: bool = True,
        delay_after: bool = True,
    ) -> bool:
        """
        Click at position with optional variance.

        Args:
            x: X coordinate (if None, clicks at current position)
            y: Y coordinate (if None, clicks at current position)
            button: Mouse button to click
            variance: Add random offset to click position
            delay_after: Add human-like delay after click

        Returns:
            True if click successful
        """
        try:
            if x is not None and y is not None:
                if variance:
                    offset_x = random.randint(
                        -self.config.click_variance, self.config.click_variance
                    )
                    offset_y = random.randint(
                        -self.config.click_variance, self.config.click_variance
                    )
                    x += offset_x
                    y += offset_y

                pyautogui.moveTo(x, y)

            pyautogui.click(button=button)

            if delay_after:
                delay = random.uniform(*self.config.post_click_delay)
                time.sleep(delay)

            logger.info(f"[PyAutoGUI] Clicked at ({x}, {y}) with {button} button")
            return True

        except Exception as e:
            logger.error(f"Failed to click: {e}", exc_info=True)
            return False

    def click_at(
        self,
        x: int,
        y: int,
        button: Literal["left", "right", "middle"] = "left",
        move_style: MovementStyle = "curved",
        variance: bool = True,
        speed_multiplier: float = 1.0,
    ) -> bool:
        """
        Move and click at absolute coordinates.

        This function must be passed absolute coordinates otherwise
        the click may end up out of bounds.

        Args:
            x: Target X coordinate
            y: Target Y coordinate
            button: Mouse button to click
            move_style: How to move to target
            variance: Add random offset to click
            speed_multiplier: Anti-ban speed variance (1.0 = normal, >1.0 = slower, <1.0 = faster)

        Returns:
            True if successful
        """
        if not self.move_to(x, y, style=move_style, speed_multiplier=speed_multiplier):
            return False

        time.sleep(
            random.uniform(
                MOUSE_MOVEMENT.post_move_delay_min, MOUSE_MOVEMENT.post_move_delay_max
            )
        )

        return self.click(x, y, button=button, variance=variance)

    def _move_bezier(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float
    ) -> None:
        """Move mouse along a Bezier curve (delegates to bezier_utils)."""
        from osrsbot.services.bezier_utils import execute_bezier_path, generate_bezier_path

        waypoints = generate_bezier_path(start_x, start_y, end_x, end_y, duration)
        execute_bezier_path(
            waypoints,
            lambda bx, by: pyautogui.moveTo(bx, by),
            duration,
        )

    def _move_with_overshoot(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float
    ) -> None:
        """
        Move with occasional overshoot (human-like correction).

        Uses configuration from constants.MOUSE_MOVEMENT.
        """
        if random.random() < self.config.overshoot_chance:
            overshoot_dist = random.randint(
                MOUSE_MOVEMENT.overshoot_distance_min, self.config.overshoot_distance
            )

            dx = end_x - start_x
            dy = end_y - start_y
            length = (dx**2 + dy**2) ** 0.5

            if length > 0:
                overshoot_x = end_x + int((dx / length) * overshoot_dist)
                overshoot_y = end_y + int((dy / length) * overshoot_dist)

                self._move_bezier(
                    start_x,
                    start_y,
                    overshoot_x,
                    overshoot_y,
                    duration * MOUSE_MOVEMENT.overshoot_duration_fraction,
                )

                time.sleep(MOUSE_MOVEMENT.correction_delay)
                pyautogui.moveTo(
                    end_x,
                    end_y,
                    duration=duration * MOUSE_MOVEMENT.correction_duration_fraction,
                )
            else:
                pyautogui.moveTo(end_x, end_y, duration=duration)
        else:
            self._move_bezier(start_x, start_y, end_x, end_y, duration)

    def drag_to(
        self,
        x: int,
        y: int,
        button: Literal["left", "right", "middle"] = "left",
        duration: float = 0.5,
    ) -> bool:
        """
        Drag mouse to position while holding button.

        Useful for camera movement, etc.
        """
        try:
            pyautogui.drag(
                x - pyautogui.position()[0],
                y - pyautogui.position()[1],
                duration=duration,
                button=button,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to drag: {e}", exc_info=True)
            return False

    def get_position(self) -> Tuple[int, int]:
        return pyautogui.position()

    def random_movement(self, radius: Optional[int] = None) -> None:
        """
        Perform random mouse movement within a radius.

        Args:
            radius: Movement radius in pixels (defaults to MOUSE_MOVEMENT.random_movement_radius)
        """
        if radius is None:
            radius = MOUSE_MOVEMENT.random_movement_radius

        current_x, current_y = self.get_position()

        offset_x = random.randint(-radius, radius)
        offset_y = random.randint(-radius, radius)

        self.move_to(current_x + offset_x, current_y + offset_y, style="curved")

    def hover_at(
        self,
        x: int,
        y: int,
        duration: float = 0.5,
        style: MovementStyle = "curved"
    ) -> bool:
        """
        Move mouse to position and hover without clicking.

        Args:
            x: Target X coordinate (absolute)
            y: Target Y coordinate (absolute)
            duration: How long to hover in seconds
            style: Movement style (curved, linear, overshoot)

        Returns:
            True if hover successful, False otherwise
        """
        try:
            # Move to target position
            if not self.move_to(x, y, style=style):
                return False

            # Hover for specified duration
            time.sleep(duration)
            logger.debug(f"Hovered at ({x}, {y}) for {duration:.2f}s")
            return True

        except Exception as e:
            logger.error(f"Failed to hover: {e}", exc_info=True)
            return False
