"""
Combat Queries - CQRS Query for combat state.

Handles:
- Combat detection (in_combat check)
- Click success detection
- Combat-related visual checks

Responsibilities:
- Read combat state (no writes)
- Template-based detection with pixel fallback
- Click verification
"""

import logging
from typing import Optional, Any, TYPE_CHECKING

from osrsbot.models.config import Config
from osrsbot.utils.color_helpers import hex_to_rgb
from osrsbot.constants import COLOR_DETECTION

if TYPE_CHECKING:
    from osrsbot.services.screen_service import ScreenService
    from osrsbot.services.template_match_service import TemplateMatchService

logger = logging.getLogger(__name__)


class CombatQueries:
    """
    Combat state queries.

    Focused on reading combat-related state.
    """

    def __init__(
        self,
        screen: 'ScreenService',
        config: Config,
        template_service: Optional['TemplateMatchService'] = None
    ):
        self.screen = screen
        self.config = config
        self.template_service = template_service

    def in_combat(self) -> bool:
        """
        Check if player is in combat.

        Uses pixel-based detection of combat indicator color.

        Returns:
            True if in combat
        """
        coord = self.config.get("coordinates", "checks", "combat_indicator")
        if not coord:
            logger.error("combat_indicator coordinates not found in config")
            return False

        color = self.screen.get_pixel_color(coord['x'], coord['y'], relative=True)

        combat_green_hex = self.config.get("colors", "combat_indicator_green")
        combat_red_hex = self.config.get("colors", "combat_indicator_red")

        if combat_green_hex and combat_red_hex:
            combat_colors = [
                hex_to_rgb(combat_green_hex),
                hex_to_rgb(combat_red_hex)
            ]
        else:
            logger.warning("Combat indicator colors not in config, using fallback")
            combat_colors = [(7, 139, 54), (99, 21, 19)]

        tolerance = self.config.get("tolerances", "color_match", default=10)

        return any(
            all(abs(color[i] - cc[i]) <= tolerance for i in range(3))
            for cc in combat_colors
        )

    def click_success(self, tries: int = 3) -> bool:
        """
        Check if a click was detected using template matching.

        Retries across multiple frames and uses majority vote.

        Args:
            tries: Number of frames to check

        Returns:
            True if click detected in majority of frames
        """
        if not self.template_service or not self.screen:
            logger.warning("Services not available for click check")
            return False

        buttons = ["good_click_1", "good_click_2", "good_click_3", "good_click_4"]
        detections = 0

        for attempt in range(tries):
            img_gray = self.screen.capture_grayscale()
            if img_gray is None:
                continue

            # Check if ANY of the red click templates match
            for button_name in buttons:
                if self.template_service.detect_button(button_name, img_gray, force=True):
                    detections += 1
                    logger.debug(f"Click check attempt {attempt + 1}: Click template '{button_name}' detected")
                    break

            # Early exit if we already have majority
            if detections > tries // 2:
                logger.info(f"Click success confirmed ({detections}/{attempt + 1} frames)")
                return True

        success = detections > tries // 2
        logger.info(f"Click check complete: {detections}/{tries} frames detected click (success={success})")
        return success
