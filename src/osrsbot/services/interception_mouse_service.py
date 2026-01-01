"""
InterceptionMouseService - Kernel-level mouse control using Interception driver.

Provides hardware-level mouse input that is indistinguishable from real mouse movements.
Requires interception-python package and Interception driver installation.
"""

import logging
import random
import time
from dataclasses import dataclass
from typing import Literal, Optional, Tuple

try:
    from interception import Interception, click, move_to

    INTERCEPTION_AVAILABLE = True
except ImportError:
    INTERCEPTION_AVAILABLE = False
    logging.warning(
        "interception-python not installed. "
        "Install with: pip install interception-python"
    )

from osrsbot.constants import BEZIER_CURVE, MOUSE_MOVEMENT

logger = logging.getLogger(__name__)

MovementStyle = Literal["instant", "linear", "curved", "overshoot", "random"]


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


class InterceptionMouseService:
    """
    Kernel-level mouse service using Interception driver.

    Features:
    - Hardware-level input (undetectable by standard anti-cheat)
    - Multiple movement styles (linear, curved, overshoot)
    - Bezier curve movement with human-like patterns
    - Click variance and humanization
    - Configurable speeds and behaviors
    """

    def __init__(self, config: MouseConfig = None):
        if not INTERCEPTION_AVAILABLE:
            raise ImportError(
                "Interception driver not available. "
                "Install with: pip install interception-python"
            )

        self.config = config or MouseConfig()

        try:
            self.context = Interception()
            self.mouse_device = self.context.mouse
            logger.info(
                f"Interception context initialized (mouse device: {self.mouse_device})"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Interception: {e}")
            raise RuntimeError(
                "Failed to initialize Interception driver. "
                "Make sure the driver is installed and system has been rebooted. "
                "You may need to run as Administrator."
            ) from e

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
            import pyautogui

            current_x, current_y = pyautogui.position()

            distance = ((x - current_x) ** 2 + (y - current_y) ** 2) ** 0.5

            if duration is None:
                duration = random.uniform(
                    self.config.min_speed, self.config.max_speed
                ) * (1 + distance / MOUSE_MOVEMENT.distance_factor)

            duration *= speed_multiplier

            if style == "instant":
                move_to(x, y, blocking=True)

            elif style == "linear":
                self._move_linear(current_x, current_y, x, y, duration)

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

    def _move_linear(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float
    ) -> None:
        """Move mouse in a straight line."""
        steps = max(10, int(duration * 60))
        start_time = time.time()

        for i in range(steps + 1):
            t = i / steps
            elapsed = time.time() - start_time

            x = int(start_x + (end_x - start_x) * t)
            y = int(start_y + (end_y - start_y) * t)

            move_to(x, y, blocking=True)

            expected_time = (i / steps) * duration
            sleep_time = expected_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

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

                move_to(x, y, blocking=True)

            click(button=button)

            if delay_after:
                delay = random.uniform(*self.config.post_click_delay)
                time.sleep(delay)

            logger.debug(f"Clicked at ({x}, {y}) with {button} button")
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
        """
        Move mouse along a Bezier curve.

        Creates a smooth curved path with random control points.
        """
        cp1_x = start_x + random.randint(
            BEZIER_CURVE.control_point_offset_min, BEZIER_CURVE.control_point_offset_max
        )
        cp1_y = start_y + random.randint(
            BEZIER_CURVE.control_point_offset_min, BEZIER_CURVE.control_point_offset_max
        )
        cp2_x = end_x + random.randint(
            BEZIER_CURVE.control_point_offset_min, BEZIER_CURVE.control_point_offset_max
        )
        cp2_y = end_y + random.randint(
            BEZIER_CURVE.control_point_offset_min, BEZIER_CURVE.control_point_offset_max
        )

        steps = max(
            BEZIER_CURVE.min_steps, int(duration * BEZIER_CURVE.steps_per_second)
        )

        start_time = time.time()

        for i in range(steps + 1):
            t = i / steps
            elapsed = time.time() - start_time

            x = int(
                (1 - t) ** 3 * start_x
                + 3 * (1 - t) ** 2 * t * cp1_x
                + 3 * (1 - t) * t**2 * cp2_x
                + t**3 * end_x
            )
            y = int(
                (1 - t) ** 3 * start_y
                + 3 * (1 - t) ** 2 * t * cp1_y
                + 3 * (1 - t) * t**2 * cp2_y
                + t**3 * end_y
            )

            move_to(x, y, blocking=True)

            expected_time = (i / steps) * duration
            sleep_time = expected_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _move_with_overshoot(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float
    ) -> None:
        """
        Move with occasional overshoot (human-like correction).
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

                self._move_linear(
                    overshoot_x,
                    overshoot_y,
                    end_x,
                    end_y,
                    duration * MOUSE_MOVEMENT.correction_duration_fraction,
                )
            else:
                self._move_linear(start_x, start_y, end_x, end_y, duration)
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
        """
        try:
            import pyautogui

            current_x, current_y = pyautogui.position()

            # Use pyautogui drag since interception-python doesn't expose drag directly
            pyautogui.drag(
                x - current_x, y - current_y, duration=duration, button=button
            )

            return True
        except Exception as e:
            logger.error(f"Failed to drag: {e}", exc_info=True)
            return False

    def get_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        import pyautogui

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
