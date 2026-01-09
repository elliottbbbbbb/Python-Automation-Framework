"""
Timing utilities with anti-ban variance.

Handles wait operations, timing variance, and micro-breaks.
"""

import logging
import random
import time
from typing import Any, Optional

from osrsbot.constants import GAME_TIMING
from osrsbot.models.config import Config

logger = logging.getLogger(__name__)


class TimingHelper:
    """
    Manages timing operations with anti-ban variance.

    Used by all action modules for consistent timing behavior.
    """

    def __init__(self, config: Config, anti_ban_service: Optional[Any] = None):
        self.config = config
        self.anti_ban = anti_ban_service

    def wait(self, timing_type: str) -> None:
        """
        Wait for configured duration with anti-ban variance.

        Args:
            timing_type: Key in config timings (e.g., "short", "medium", "long")
        """
        delay = self.config.get(
            "timings", timing_type, default=GAME_TIMING.default_wait
        )

        # Handle tuple/list ranges for variance
        if isinstance(delay, (list, tuple)) and len(delay) == 2:
            min_delay, max_delay = delay
            # Use triangular distribution (peaks at middle) instead of uniform (flat)
            # This creates more human-like clustering around the center value
            mode = (float(min_delay) + float(max_delay)) / 2
            actual_delay = random.triangular(float(min_delay), float(max_delay), mode)
            logger.debug(
                f"Wait '{timing_type}': {
                    actual_delay:.2f}s (range: {min_delay}-{max_delay}s)"
            )
        elif isinstance(delay, (int, float)):
            actual_delay = float(delay)
        else:
            logger.warning(
                f"Invalid timing for '{timing_type}', using {GAME_TIMING.default_wait}s"
            )
            actual_delay = GAME_TIMING.default_wait

        # Apply anti-ban variance
        if self.anti_ban:
            variance = self.anti_ban.get_timing_variance()
            actual_delay *= variance
            logger.debug(
                f"Applied session variance ({variance:.3f}): {actual_delay:.2f}s"
            )

        time.sleep(actual_delay)

        # Micro-break check
        if self.anti_ban and self.anti_ban.should_micro_break():
            self.anti_ban.execute_micro_break()

    def get_mouse_speed_multiplier(self) -> float:
        """
        Get anti-ban mouse speed variance (0.9-1.1x).

        Returns:
            Speed multiplier for mouse movements
        """
        if self.anti_ban:
            return self.anti_ban.get_mouse_speed_variance()
        return 1.0
