"""
ClickTargetTracker - Track click history and blacklisted locations.

Manages intelligent target selection by tracking:
- Click history to detect stuck clicking patterns
- Blacklisted locations to avoid inaccessible areas
"""
import time
import logging
from dataclasses import dataclass
from typing import List
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class ClickRecord:
    """Record of a single click attempt."""
    timestamp: float
    x: int
    y: int


@dataclass
class BlacklistEntry:
    """Temporarily blacklisted location."""
    x: int
    y: int
    radius: int  # Area around point to blacklist
    expires_at: float  # Timestamp when blacklist expires


class ClickTargetTracker:
    """
    Tracks click history and blacklisted locations.

    Features:
    - Detects stuck clicking (same location repeatedly)
    - Blacklists inaccessible locations temporarily
    """

    def __init__(self, history_size: int = 10):
        """
        Initialize tracker.

        Args:
            history_size: Maximum number of clicks to track
        """
        self._click_history: deque = deque(maxlen=history_size)
        self._blacklist: List[BlacklistEntry] = []

    def add_click(self, x: int, y: int) -> None:
        """
        Record a click in history.

        Args:
            x: Click X coordinate (relative to window)
            y: Click Y coordinate (relative to window)
        """
        record = ClickRecord(
            timestamp=time.time(),
            x=x,
            y=y
        )
        self._click_history.append(record)
        logger.debug(f"Recorded click at ({x}, {y})")

    def get_recent_clicks(self, n: int) -> List[ClickRecord]:
        """
        Get last N clicks from history.

        Args:
            n: Number of recent clicks to retrieve

        Returns:
            List of ClickRecords (newest first)
        """
        if n <= 0:
            return []
        return list(self._click_history)[-n:]

    def is_stuck(
        self,
        window: int = 3,
        threshold_pixels: int = 18
    ) -> bool:
        """
        Check if last N clicks are within threshold distance (stuck).

        Args:
            window: Number of recent clicks to check
            threshold_pixels: Max distance between clicks to consider stuck

        Returns:
            True if stuck (all clicks within threshold), False otherwise
        """
        recent_clicks = self.get_recent_clicks(window)

        if len(recent_clicks) < window:
            # Not enough click history yet
            return False

        # Calculate pairwise distances between all recent clicks
        for i in range(len(recent_clicks)):
            for j in range(i + 1, len(recent_clicks)):
                click1 = recent_clicks[i]
                click2 = recent_clicks[j]

                # Euclidean distance
                distance = ((click1.x - click2.x) ** 2 + (click1.y - click2.y) ** 2) ** 0.5

                if distance > threshold_pixels:
                    # Found clicks that are far apart, not stuck
                    return False

        # All clicks are within threshold - we're stuck!
        logger.warning(
            f"Stuck detected: last {window} clicks within {threshold_pixels}px"
        )
        return True

    def blacklist_location(
        self,
        x: int,
        y: int,
        duration: float = 12.0,
        radius: int = 25
    ) -> None:
        """
        Add location to blacklist temporarily.

        Args:
            x: X coordinate to blacklist
            y: Y coordinate to blacklist
            duration: How long to blacklist (seconds)
            radius: Radius around point to blacklist (pixels)
        """
        # Clean expired entries first
        self._clean_expired_blacklist()

        entry = BlacklistEntry(
            x=x,
            y=y,
            radius=radius,
            expires_at=time.time() + duration
        )
        self._blacklist.append(entry)
        logger.info(
            f"Blacklisted location ({x}, {y}) "
            f"with {radius}px radius for {duration}s"
        )

    def is_blacklisted(self, x: int, y: int) -> bool:
        """
        Check if location is currently blacklisted.

        Args:
            x: X coordinate to check
            y: Y coordinate to check

        Returns:
            True if location is blacklisted, False otherwise
        """
        # Clean expired entries first
        self._clean_expired_blacklist()

        for entry in self._blacklist:
            # Calculate distance from blacklist center
            distance = ((x - entry.x) ** 2 + (y - entry.y) ** 2) ** 0.5

            if distance <= entry.radius:
                logger.debug(
                    f"Location ({x}, {y}) is blacklisted "
                    f"(within {entry.radius}px of ({entry.x}, {entry.y}))"
                )
                return True

        return False

    def _clean_expired_blacklist(self) -> None:
        """Remove expired blacklist entries."""
        current_time = time.time()
        original_count = len(self._blacklist)

        self._blacklist = [
            entry for entry in self._blacklist
            if entry.expires_at > current_time
        ]

        removed = original_count - len(self._blacklist)
        if removed > 0:
            logger.debug(f"Cleaned {removed} expired blacklist entries")

    def reset(self) -> None:
        """Clear all state (history, blacklist)."""
        self._click_history.clear()
        self._blacklist.clear()
        logger.debug("Click tracker reset")
