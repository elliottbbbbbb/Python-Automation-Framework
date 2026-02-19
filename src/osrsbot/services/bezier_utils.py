"""
Bezier curve utilities for humanized mouse movement.

Extracts the shared Bezier curve generation logic used by MouseService
and Win32MouseService into a single module.

Design: generate_bezier_path() produces a sequence of (x, y) waypoints.
Each mouse service iterates and applies its own move function
(pyautogui.moveTo or Win32 SendInput).
"""

import math
import random
import time
from typing import Callable, List, Tuple

from osrsbot.constants import BEZIER_CURVE

# Standardized constants (was 0.08 in MouseService, 0.06 in Win32)
JITTER_PROBABILITY = 0.08
JITTER_RANGE = (-1.2, 1.2)
TIMING_VARIANCE = (0.85, 1.15)


def ease_in_out(t: float) -> float:
    """Quadratic ease-in-out for human-like velocity profile."""
    if t < 0.5:
        return 2 * t * t
    return 1 - pow(-2 * t + 2, 2) / 2


def generate_bezier_path(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: float,
) -> List[Tuple[int, int]]:
    """
    Generate waypoints along a cubic Bezier curve.

    Args:
        start_x, start_y: Starting position
        end_x, end_y: Target position
        duration: Total movement duration in seconds

    Returns:
        List of (x, y) integer coordinate pairs
    """
    dx = end_x - start_x
    dy = end_y - start_y
    dist = math.hypot(dx, dy)

    # Base control offsets scale with distance for natural curves
    base_off = int(max(1, dist * 0.2))
    off_min = BEZIER_CURVE.control_point_offset_min
    off_max = BEZIER_CURVE.control_point_offset_max

    # Compute unit perpendicular vector
    if dist == 0:
        perp_x, perp_y = 0.0, 0.0
    else:
        ux = dx / dist
        uy = dy / dist
        perp_x = -uy
        perp_y = ux

    # Place control points at 1/3 and 2/3 along the line
    cp1_base_x = start_x + dx * 0.33
    cp1_base_y = start_y + dy * 0.33
    cp2_base_x = start_x + dx * 0.66
    cp2_base_y = start_y + dy * 0.66

    # Random perpendicular offset magnitude
    mag1 = random.uniform(off_min, off_max) + random.uniform(-base_off, base_off)
    mag2 = random.uniform(off_min, off_max) + random.uniform(-base_off, base_off)
    if random.random() < 0.5:
        mag1 *= -1
    if random.random() < 0.5:
        mag2 *= -1

    cp1_x = cp1_base_x + perp_x * mag1
    cp1_y = cp1_base_y + perp_y * mag1
    cp2_x = cp2_base_x + perp_x * mag2
    cp2_y = cp2_base_y + perp_y * mag2

    steps = max(BEZIER_CURVE.min_steps, int(duration * BEZIER_CURVE.steps_per_second))

    waypoints: List[Tuple[int, int]] = []

    for i in range(steps + 1):
        t = i / steps
        u = ease_in_out(t)

        # Cubic Bezier interpolation
        x = (
            (1 - u) ** 3 * start_x
            + 3 * (1 - u) ** 2 * u * cp1_x
            + 3 * (1 - u) * u ** 2 * cp2_x
            + u ** 3 * end_x
        )
        y = (
            (1 - u) ** 3 * start_y
            + 3 * (1 - u) ** 2 * u * cp1_y
            + 3 * (1 - u) * u ** 2 * cp2_y
            + u ** 3 * end_y
        )

        # Occasional tiny hand jitter
        if random.random() < JITTER_PROBABILITY:
            x += random.uniform(*JITTER_RANGE)
            y += random.uniform(*JITTER_RANGE)

        waypoints.append((int(round(x)), int(round(y))))

    return waypoints


def execute_bezier_path(
    waypoints: List[Tuple[int, int]],
    move_fn: Callable[[int, int], None],
    duration: float,
) -> None:
    """
    Execute a Bezier path using the provided move function.

    Handles real-time scheduling to match the eased timing profile.

    Args:
        waypoints: List of (x, y) from generate_bezier_path()
        move_fn: Callable(x, y) that moves the cursor
        duration: Total duration in seconds (same value passed to generate_bezier_path)
    """
    steps = len(waypoints) - 1
    if steps <= 0:
        if waypoints:
            move_fn(waypoints[0][0], waypoints[0][1])
        return

    start_time = time.time()

    for i, (x, y) in enumerate(waypoints):
        move_fn(x, y)

        elapsed = time.time() - start_time
        expected_time = ease_in_out(i / steps) * duration
        sleep_time = expected_time - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time * random.uniform(*TIMING_VARIANCE))
