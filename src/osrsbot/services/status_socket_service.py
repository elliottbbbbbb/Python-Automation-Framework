"""
StatusSocketService - Reads live player position and camera data from RuneLite/OpenOSRS.

Monitors live_data.json written by the Status Socket plugin for real-time game state.
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PlayerState:
    """Player state data from Status Socket plugin."""

    world_x: int
    world_y: int
    plane: int
    camera_yaw: int  # 0-2048 (RuneLite camera angle)
    timestamp: float
    is_moving: bool = False
    animation_id: int = -1


class StatusSocketService:
    """
    Monitors RuneLite/OpenOSRS Status Socket plugin output for player state.

    Features:
    - File modification time monitoring (avoids re-parsing unchanged data)
    - JSON parsing with error handling
    - Graceful degradation if file unavailable
    - Last known good state caching
    """

    def __init__(self, data_file: str = "live_data.json", poll_interval: float = 0.1):
        """
        Initialize Status Socket service.

        Args:
            data_file: Path to live_data.json written by RuneLite plugin
            poll_interval: How often to check file for updates (seconds)
        """
        self.data_file = Path(data_file)
        self.poll_interval = poll_interval
        self._last_state: Optional[PlayerState] = None
        self._last_modified: float = 0
        self._file_unavailable_warned: bool = False
        self._stale_data_threshold: float = 5.0  # Warn if no updates for 5 seconds

    def get_player_state(self) -> Optional[PlayerState]:
        """
        Get current player state from Status Socket plugin.

        Returns:
            PlayerState if available, None if file unavailable or parse error
        """
        if not self.data_file.exists():
            if not self._file_unavailable_warned:
                logger.warning(
                    f"Status Socket data file not found: {self.data_file}. "
                    "Ensure RuneLite/OpenOSRS Status Socket plugin is enabled. "
                    "See SETUP_GUIDE.md for installation instructions."
                )
                self._file_unavailable_warned = True
            return None

        try:
            # Check if file has been modified since last read
            current_modified = self.data_file.stat().st_mtime
            if current_modified == self._last_modified:
                # File hasn't changed, return cached state
                return self._last_state

            # Read and parse JSON
            with open(self.data_file, "r") as f:
                data = json.load(f)

            # Extract player state
            world_point = data.get("worldPoint", {})
            camera = data.get("camera", {})

            state = PlayerState(
                world_x=world_point.get("x", 0),
                world_y=world_point.get("y", 0),
                plane=world_point.get("plane", 0),
                camera_yaw=camera.get("yaw", 0),
                timestamp=time.time(),
                is_moving=data.get("isMoving", False),
                animation_id=data.get("animation", -1),
            )

            # Update cache
            self._last_state = state
            self._last_modified = current_modified

            # Reset warnings on successful read
            self._file_unavailable_warned = False

            return state

        except json.JSONDecodeError as e:
            logger.warning(
                f"Failed to parse Status Socket JSON: {e}. Using last known state."
            )
            return self._last_state
        except Exception as e:
            logger.error(f"Error reading Status Socket data: {e}")
            return self._last_state

    def is_available(self) -> bool:
        """
        Check if Status Socket plugin is active and providing data.

        Returns:
            True if plugin available, False otherwise
        """
        state = self.get_player_state()
        if state is None:
            return False

        # Check for stale data
        time_since_update = time.time() - state.timestamp
        if time_since_update > self._stale_data_threshold:
            logger.warning(
                f"Status Socket data is stale ({time_since_update:.1f}s since last update). "
                "Plugin may not be running."
            )
            return False

        return True

    def wait_for_arrival(
        self, target_x: int, target_y: int, tolerance: int = 2, timeout: float = 10.0
    ) -> bool:
        """
        Poll until player reaches target coordinates or timeout.

        Args:
            target_x: Target world X coordinate
            target_y: Target world Y coordinate
            tolerance: Distance in tiles to consider "arrived" (default 2)
            timeout: Maximum time to wait in seconds (default 10.0)

        Returns:
            True if arrived within tolerance, False on timeout
        """
        start_time = time.time()
        stuck_threshold = 5  # Number of checks without movement = stuck
        stuck_counter = 0
        last_position = None

        while (time.time() - start_time) < timeout:
            state = self.get_player_state()
            if not state:
                logger.warning("Lost Status Socket connection during wait_for_arrival")
                return False

            # Calculate distance to target
            distance = self._calculate_distance(
                state.world_x, state.world_y, target_x, target_y
            )

            # Arrived!
            if distance <= tolerance:
                logger.debug(
                    f"Arrived at ({target_x}, {target_y}) "
                    f"from ({state.world_x}, {state.world_y})"
                )
                return True

            # Stuck detection
            current_position = (state.world_x, state.world_y)
            if current_position == last_position:
                stuck_counter += 1
                if stuck_counter >= stuck_threshold:
                    logger.warning(
                        f"Player appears stuck at {current_position} "
                        f"(target: {target_x}, {target_y})"
                    )
                    return False
            else:
                stuck_counter = 0  # Reset if moved
                last_position = current_position

            # Sleep before next check
            time.sleep(self.poll_interval)

        logger.warning(
            f"Timeout waiting for arrival at ({target_x}, {target_y}). "
            f"Current position: ({state.world_x if state else 'unknown'}, "
            f"{state.world_y if state else 'unknown'})"
        )
        return False

    def _calculate_distance(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Calculate Euclidean distance between two points."""
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
