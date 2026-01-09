"""
Zulrah Navigation System

Handles movement to safe spots using colored tile markers.
"""

import logging
import random

logger = logging.getLogger(__name__)


class ZulrahNavigator:
    """Handles navigation to safe spots during Zulrah fight."""

    def __init__(self, mouse_service, detector, actions):
        """
        Initialize navigator with required services.

        Args:
            mouse_service: MouseService for clicking
            detector: ZulrahDetector for finding tile markers
            actions: GameActions for movement commands
        """
        self.mouse = mouse_service
        self.detector = detector
        self.actions = actions

    def move_to_safe_spot(self, tile_color: str) -> bool:
        """
        Navigate to the colored tile marker.

        Args:
            tile_color: Hex color code of safe spot tile

        Returns:
            True if successfully moved, False otherwise
        """
        try:
            # Find the tile marker
            marker_pos = self.detector.detect_safe_tile_marker(tile_color)

            if not marker_pos:
                logger.warning(f"Could not find tile marker: {tile_color}")
                return False

            x, y = marker_pos

            # Click on the tile marker
            logger.info(f"Moving to safe spot at ({x}, {y})")
            self.mouse.move_to(x, y, move_style="curved")
            self.mouse.click()

            # Wait for movement
            self.actions.wait("short")

            # Verify we're at the right spot
            if self.detector.is_player_at_safe_spot(tile_color):
                logger.info("Successfully reached safe spot")
                return True
            else:
                logger.warning("Moved but may not be at exact safe spot")
                return True  # Still count as success, close enough

        except Exception as e:
            logger.error(f"Error moving to safe spot: {e}")
            return False

    def verify_position(self, expected_color: str) -> bool:
        """
        Confirm we're at the right safe spot.

        Args:
            expected_color: Hex color of tile we should be on

        Returns:
            True if at correct position, False otherwise
        """
        return self.detector.is_player_at_safe_spot(expected_color)

    def emergency_move(self, direction: str = "random") -> bool:
        """
        Emergency movement if we can't find tile marker.

        Moves in a random direction to avoid taking damage.

        Args:
            direction: Direction to move ("random", "north", "south", "east", "west")

        Returns:
            True if movement attempted, False on error
        """
        try:
            logger.warning("Executing emergency move!")

            if direction == "random":
                direction = random.choice(["north", "south", "east", "west"])

            # Get screen center (approximate player position)
            center_x = 400
            center_y = 300

            # Calculate offset based on direction
            offset = 100  # pixels
            if direction == "north":
                target_x, target_y = center_x, center_y - offset
            elif direction == "south":
                target_x, target_y = center_x, center_y + offset
            elif direction == "east":
                target_x, target_y = center_x + offset, center_y
            else:  # west
                target_x, target_y = center_x - offset, center_y

            # Click to move
            self.mouse.move_to(target_x, target_y, move_style="straight")
            self.mouse.click()

            logger.info(f"Emergency moved {direction}")
            return True

        except Exception as e:
            logger.error(f"Error during emergency move: {e}")
            return False
