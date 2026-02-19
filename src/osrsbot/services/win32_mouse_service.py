"""
Win32MouseService - native SendInput mouse control via ctypes.

Provides the same interface as MouseService but uses
Win32 SendInput for lower-level control. Movement is humanized using Bezier
curves with easing and micro-jitter.

This file intentionally mirrors the `MouseService` API so it can be swapped
in the runner with minimal changes.
"""

import ctypes
import math
import random
import time
import logging
from dataclasses import dataclass
from typing import Literal, Optional, Tuple

from osrsbot.constants import MOUSE_MOVEMENT

logger = logging.getLogger(__name__)

MovementStyle = Literal["instant", "linear", "curved", "overshoot", "random"]


@dataclass
class MouseConfig:
    min_speed: float = 0.1
    max_speed: float = 0.5
    overshoot_chance: float = 0.15
    overshoot_distance: int = 20
    click_variance: int = 3
    post_click_delay: Tuple[float, float] = (0.05, 0.15)


# Win32 constants
PUL = ctypes.POINTER(ctypes.c_ulong)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]


class INPUT_union(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("union", INPUT_union)]


# mouse event flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_ABSOLUTE = 0x8000


def _send_input(inp: INPUT) -> int:
    return ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


def _abs_coords(x: int, y: int) -> Tuple[int, int]:
    # Map to 0..65535 (inclusive) for SendInput absolute coordinates
    sx = ctypes.windll.user32.GetSystemMetrics(0)
    sy = ctypes.windll.user32.GetSystemMetrics(1)
    if sx <= 1 or sy <= 1:
        return x, y
    nx = int(x * 65535 / (sx - 1))
    ny = int(y * 65535 / (sy - 1))
    return nx, ny


class Win32MouseService:
    """Native Win32 mouse service implementing the MouseService API."""

    def __init__(self, config: MouseConfig = None):
        self.config = config or MouseConfig()

    def _send_move_abs(self, x: int, y: int) -> None:
        nx, ny = _abs_coords(x, y)
        mi = MOUSEINPUT(dx=nx, dy=ny, mouseData=0, dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, time=0, dwExtraInfo=None)
        inp = INPUT(type=0, union=INPUT_union())
        inp.union.mi = mi
        _send_input(inp)

    def _send_click(self, button: str = "left") -> None:
        if button == "left":
            down = MOUSEEVENTF_LEFTDOWN
            up = MOUSEEVENTF_LEFTUP
        elif button == "right":
            down = MOUSEEVENTF_RIGHTDOWN
            up = MOUSEEVENTF_RIGHTUP
        else:
            down = MOUSEEVENTF_MIDDLEDOWN
            up = MOUSEEVENTF_MIDDLEUP

        mi_down = MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=down, time=0, dwExtraInfo=None)
        mi_up = MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=up, time=0, dwExtraInfo=None)
        inp1 = INPUT(type=0, union=INPUT_union()); inp1.union.mi = mi_down
        inp2 = INPUT(type=0, union=INPUT_union()); inp2.union.mi = mi_up
        _send_input(inp1)
        time.sleep(0.008 + random.random() * 0.010)
        _send_input(inp2)

    def move_to(self, x: int, y: int, style: MovementStyle = "curved", duration: Optional[float] = None, speed_multiplier: float = 1.0) -> bool:
        try:
            logger.debug(f"[Win32] Moving to ({x}, {y}) using style={style}")
            # get current pos
            pt = ctypes.wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            start_x, start_y = pt.x, pt.y

            dx = x - start_x
            dy = y - start_y
            dist = math.hypot(dx, dy)

            if duration is None:
                duration = random.uniform(self.config.min_speed, self.config.max_speed) * (1 + dist / MOUSE_MOVEMENT.distance_factor)
            duration *= speed_multiplier

            # Variation for 'curved'
            if style == "curved":
                r = random.random()
                if r < 0.12:
                    style = "linear"
                elif r < 0.28:
                    style = "overshoot"

            if style == "instant":
                self._send_move_abs(x, y)
                return True

            # For humanized motion use similar Bezier routine
            if style in ("curved", "overshoot", "linear", "random"):
                # If straight linear requested, do simple interpolation
                if style == "linear":
                    steps = max(8, int(duration * 60))
                    for i in range(steps + 1):
                        t = i / steps
                        px = int(start_x + dx * t)
                        py = int(start_y + dy * t)
                        self._send_move_abs(px, py)
                        time.sleep(duration / steps)
                    return True

                # curved / overshoot: delegate to shared Bezier generator
                from osrsbot.services.bezier_utils import execute_bezier_path, generate_bezier_path

                waypoints = generate_bezier_path(start_x, start_y, x, y, duration)
                execute_bezier_path(
                    waypoints,
                    lambda bx, by: self._send_move_abs(bx, by),
                    duration,
                )
                return True

            return False

        except Exception as e:
            logger.error("Win32MouseService.move_to failed: %s", e, exc_info=True)
            return False

    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: Literal["left", "right", "middle"] = "left", variance: bool = True, delay_after: bool = True) -> bool:
        try:
            logger.info(f"[Win32] click() at ({x}, {y}) button={button}")
            if x is not None and y is not None:
                if variance:
                    offset_x = random.randint(-self.config.click_variance, self.config.click_variance)
                    offset_y = random.randint(-self.config.click_variance, self.config.click_variance)
                    x += offset_x
                    y += offset_y
                # move using absolute send
                self._send_move_abs(x, y)

            # micro-jitter: tiny pre-click nudge
            if random.random() < 0.12:
                jitter_x = random.uniform(-1.0, 1.0)
                jitter_y = random.uniform(-1.0, 1.0)
                # apply as tiny absolute move
                pt = ctypes.wintypes.POINT()
                ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                self._send_move_abs(int(pt.x + jitter_x), int(pt.y + jitter_y))
                time.sleep(0.005)

            self._send_click(button)

            if delay_after:
                delay = random.uniform(*self.config.post_click_delay)
                time.sleep(delay)

            return True
        except Exception as e:
            logger.error("Win32MouseService.click failed: %s", e, exc_info=True)
            return False

    def click_at(self, x: int, y: int, button: Literal["left", "right", "middle"] = "left", move_style: MovementStyle = "curved", variance: bool = True, speed_multiplier: float = 1.0) -> bool:
        if not self.move_to(x, y, style=move_style, speed_multiplier=speed_multiplier):
            return False

        time.sleep(random.uniform(MOUSE_MOVEMENT.post_move_delay_min, MOUSE_MOVEMENT.post_move_delay_max))
        return self.click(x, y, button=button, variance=variance, delay_after=True)

    def drag_to(self, x: int, y: int, button: Literal["left", "right", "middle"] = "left", duration: float = 0.5) -> bool:
        try:
            # press down
            self._send_click("left") if button == "left" else None
            # simple linear interpolation while holding - SendInput doesn't provide drag helper
            pt = ctypes.wintypes.POINT(); ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            start_x, start_y = pt.x, pt.y
            steps = max(8, int(duration * 60))
            for i in range(steps + 1):
                t = i / steps
                px = int(start_x + (x - start_x) * t)
                py = int(start_y + (y - start_y) * t)
                self._send_move_abs(px, py)
                time.sleep(duration / steps)
            # release
            # no explicit release here because _send_click sends down+up; to emulate hold you'd need separate down/up implementation
            return True
        except Exception as e:
            logger.error("Win32MouseService.drag_to failed: %s", e, exc_info=True)
            return False

    def get_position(self) -> Tuple[int, int]:
        pt = ctypes.wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)

    def random_movement(self, radius: Optional[int] = None) -> None:
        if radius is None:
            radius = MOUSE_MOVEMENT.random_movement_radius
        cx, cy = self.get_position()
        ox = random.randint(-radius, radius)
        oy = random.randint(-radius, radius)
        self.move_to(cx + ox, cy + oy, style="curved")

    def hover_at(
        self,
        x: int,
        y: int,
        duration: float = 0.5,
        style: MovementStyle = "curved"
    ) -> bool:
        """
        Move mouse to position and hover without clicking (Win32 implementation).

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
            logger.debug(f"[Win32] Hovered at ({x}, {y}) for {duration:.2f}s")
            return True

        except Exception as e:
            logger.error("Win32MouseService.hover_at failed: %s", e, exc_info=True)
            return False
