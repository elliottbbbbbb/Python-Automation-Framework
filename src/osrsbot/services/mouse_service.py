"""
MouseService - Handles all mouse movement and clicking with humanization.

Inspired by OSBC's Bezier curve implementation but with added flexibility.
"""
import time
import random
import logging
import pyautogui
from typing import Tuple, Optional, Literal
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MovementStyle = Literal["instant", "linear", "curved", "overshoot", "random"]


@dataclass
class MouseConfig:
    """Configuration for mouse behavior"""
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
        duration: Optional[float] = None
    ) -> bool:
        """
        Move mouse to absolute screen coordinates.

        Args:
            x: Target X coordinate (absolute screen position)
            y: Target Y coordinate (absolute screen position)
            style: Movement style to use
            duration: Override automatic duration calculation

        Returns:
            True if movement successful
        """
        try:
            current_x, current_y = pyautogui.position()

            distance = ((x - current_x)**2 + (y - current_y)**2)**0.5

            if duration is None:
                duration = random.uniform(
                    self.config.min_speed,
                    self.config.max_speed
                ) * (1 + distance / 1000)

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
        delay_after: bool = True
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
                        -self.config.click_variance,
                        self.config.click_variance
                    )
                    offset_y = random.randint(
                        -self.config.click_variance,
                        self.config.click_variance
                    )
                    x += offset_x
                    y += offset_y

                pyautogui.moveTo(x, y)

            pyautogui.click(button=button)

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
        variance: bool = True
    ) -> bool:
        """
        Move to position and click (combined operation).

        Args:
            x: Target X coordinate
            y: Target Y coordinate
            button: Mouse button to click
            move_style: How to move to target
            variance: Add random offset to click

        Returns:
            True if successful
        """
        if not self.move_to(x, y, style=move_style):
            return False

        time.sleep(random.uniform(0.05, 0.15))

        return self.click(x, y, button=button, variance=variance)

    def _move_bezier(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float
    ) -> None:
        """
        Move mouse along a Bezier curve (OSBC-inspired).

        Creates a smooth curved path with random control points.
        """
        cp1_x = start_x + random.randint(-100, 100)
        cp1_y = start_y + random.randint(-100, 100)
        cp2_x = end_x + random.randint(-100, 100)
        cp2_y = end_y + random.randint(-100, 100)

        steps = max(10, int(duration * 60))

        start_time = time.time()

        for i in range(steps + 1):
            t = i / steps
            elapsed = time.time() - start_time

            x = (
                (1-t)**3 * start_x +
                3*(1-t)**2*t * cp1_x +
                3*(1-t)*t**2 * cp2_x +
                t**3 * end_x
            )
            y = (
                (1-t)**3 * start_y +
                3*(1-t)**2*t * cp1_y +
                3*(1-t)*t**2 * cp2_y +
                t**3 * end_y
            )

            pyautogui.moveTo(int(x), int(y))

            expected_time = (i / steps) * duration
            sleep_time = expected_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _move_with_overshoot(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float
    ) -> None:
        """
        Move with occasional overshoot (human-like correction).
        """
        if random.random() < self.config.overshoot_chance:
            overshoot_dist = random.randint(
                5,
                self.config.overshoot_distance
            )

            dx = end_x - start_x
            dy = end_y - start_y
            length = (dx**2 + dy**2)**0.5

            if length > 0:
                overshoot_x = end_x + int((dx / length) * overshoot_dist)
                overshoot_y = end_y + int((dy / length) * overshoot_dist)

                self._move_bezier(
                    start_x, start_y,
                    overshoot_x, overshoot_y,
                    duration * 0.7
                )

                time.sleep(0.02)
                pyautogui.moveTo(end_x, end_y, duration=duration * 0.3)
            else:
                pyautogui.moveTo(end_x, end_y, duration=duration)
        else:
            self._move_bezier(start_x, start_y, end_x, end_y, duration)

    def drag_to(
        self,
        x: int,
        y: int,
        button: Literal["left", "right", "middle"] = "left",
        duration: float = 0.5
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
                button=button
            )
            return True
        except Exception as e:
            logger.error(f"Failed to drag: {e}", exc_info=True)
            return False

    def get_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        return pyautogui.position()

    def random_movement(self, radius: int = 50) -> None:
        """
        Make a small random mouse movement (anti-AFK).

        Args:
            radius: Maximum pixels to move from current position
        """
        current_x, current_y = self.get_position()

        offset_x = random.randint(-radius, radius)
        offset_y = random.randint(-radius, radius)

        self.move_to(
            current_x + offset_x,
            current_y + offset_y,
            style="curved"
        )
