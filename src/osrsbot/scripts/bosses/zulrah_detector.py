"""
Zulrah Detection System

Handles all computer vision detection for Zulrah:
- Zulrah form detection (Serpentine/Tanzanite/Magma)
- Zulrah position detection
- Tile marker detection
- Snakeling detection
"""

import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class ZulrahDetector:
    """Centralized detection logic for Zulrah boss fight."""

    def __init__(self, screen_service, template_service, config):
        """
        Initialize detector with required services.

        Args:
            screen_service: ScreenService for capturing and analyzing screen
            template_service: TemplateMatchService for template matching
            config: Config object with Zulrah settings
        """
        self.screen = screen_service
        self.template_service = template_service
        self.config = config

        # Cache for reducing CPU usage
        self._last_form_detection = None
        self._last_form_time = 0

        # Get config values
        zulrah_config = config.get("zulrah", {})
        self.form_colors = zulrah_config.get("form_colors", {})
        self.color_tolerance = zulrah_config.get("color_tolerance", 30)

    def detect_zulrah_form(self) -> Optional[str]:
        """
        Detect current Zulrah form using color detection.

        Returns:
            'serpentine', 'tanzanite', 'magma', or None if not visible
        """
        try:
            # Try to detect each form color
            for form_name, color_hex in self.form_colors.items():
                match = self.screen.find_color(
                    color_hex,
                    tolerance=self.color_tolerance
                )

                if match:
                    logger.debug(f"Detected Zulrah form: {form_name}")
                    return form_name

            logger.debug("No Zulrah form detected (may be submerged)")
            return None

        except Exception as e:
            logger.error(f"Error detecting Zulrah form: {e}")
            return None

    def detect_zulrah_position(self) -> Optional[str]:
        """
        Detect where Zulrah spawned based on screen coordinates.

        Maps form location to position zones:
        - middle: Center of arena
        - east: Eastern platform
        - west: Western platform
        - south: Southern area
        - north: Northern area

        Returns:
            Position name or None if Zulrah not visible
        """
        try:
            # First detect if Zulrah is visible
            form = self.detect_zulrah_form()
            if not form:
                return None

            # Find Zulrah on screen using form color
            color_hex = self.form_colors.get(form)
            match = self.screen.find_color(color_hex, tolerance=self.color_tolerance)

            if not match:
                return None

            # Map screen coordinates to position zones
            # These are approximate - adjust based on actual game window
            x, y = match.x, match.y

            # Rough position mapping (will need calibration)
            if 250 < x < 350 and 150 < y < 250:
                return "middle"
            elif x > 400:
                return "east"
            elif x < 200:
                return "west"
            elif y > 300:
                return "south"
            elif y < 100:
                return "north"
            else:
                return "middle"  # Default fallback

        except Exception as e:
            logger.error(f"Error detecting Zulrah position: {e}")
            return None

    def detect_safe_tile_marker(self, color: str) -> Optional[Tuple[int, int]]:
        """
        Find colored tile marker on screen.

        Args:
            color: Hex color code to search for (e.g., "#FF0000")

        Returns:
            (x, y) screen coordinates of tile marker, or None if not found
        """
        try:
            match = self.screen.find_color(color, tolerance=self.color_tolerance)

            if match:
                logger.debug(f"Found tile marker at ({match.x}, {match.y})")
                return (match.x, match.y)

            logger.warning(f"Tile marker {color} not found on screen")
            return None

        except Exception as e:
            logger.error(f"Error detecting tile marker: {e}")
            return None

    def is_zulrah_visible(self) -> bool:
        """
        Check if Zulrah is currently visible (not submerged).

        Returns:
            True if Zulrah is on screen, False otherwise
        """
        form = self.detect_zulrah_form()
        return form is not None

    def detect_snakelings(self) -> List[Tuple[int, int]]:
        """
        Find all snakelings on screen.

        Snakelings are small NPCs that spawn during certain phases.
        Use color detection to find them.

        Returns:
            List of (x, y) positions for each snakeling found
        """
        try:
            # Snakelings have distinctive color (greenish)
            snakeling_color = "#00FF00"  # Adjust based on actual color

            # Find all instances
            matches = self.screen.find_color(
                snakeling_color,
                tolerance=self.color_tolerance,
                find_all=True
            )

            if matches:
                positions = [(m.x, m.y) for m in matches]
                logger.debug(f"Found {len(positions)} snakelings")
                return positions

            return []

        except Exception as e:
            logger.error(f"Error detecting snakelings: {e}")
            return []

    def is_player_at_safe_spot(self, expected_color: str) -> bool:
        """
        Verify player is standing on correct colored tile.

        Args:
            expected_color: Hex color of tile player should be on

        Returns:
            True if player appears to be at safe spot, False otherwise
        """
        try:
            # Check if tile marker is very close to center of screen
            # (implies player is standing on it)
            match = self.detect_safe_tile_marker(expected_color)

            if not match:
                return False

            # Get screen center (player position)
            # Adjust these values based on actual window size
            screen_center_x = 400
            screen_center_y = 300

            x, y = match
            distance = ((x - screen_center_x)**2 + (y - screen_center_y)**2)**0.5

            # If tile marker is within small radius of player, we're there
            return distance < 50  # pixels

        except Exception as e:
            logger.error(f"Error checking safe spot: {e}")
            return False
