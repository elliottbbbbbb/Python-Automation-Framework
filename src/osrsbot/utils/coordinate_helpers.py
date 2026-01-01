"""
Coordinate resolution utilities.

Provides coordinate conversion and resolution with multiple fallback strategies:
1. Template detection (preferred)
2. Config coordinates (fallback)
3. Error handling and logging
"""

from typing import Optional, Tuple, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from osrsbot.services.screen_service import ScreenService
    from osrsbot.services.template_match_service import TemplateMatchService
    from osrsbot.models.config import Config

logger = logging.getLogger(__name__)


class CoordinateResolver:
    """
    Resolves coordinates using template detection with config fallback.

    Shared by inventory, combat, and other action modules.
    """

    def __init__(
        self,
        screen: 'ScreenService',
        config: 'Config',
        template_service: Optional['TemplateMatchService'] = None
    ):
        self.screen = screen
        self.config = config
        self.template_service = template_service

    def to_absolute(self, x: int, y: int) -> Tuple[int, int]:
        """Convert relative coords to absolute screen coords."""
        return self.screen.relative_to_absolute(x, y)

    def resolve_inventory_slot(
        self,
        slot_num: int,
        force_detect: bool = False
    ) -> Optional[Tuple[int, int]]:
        """
        Resolve inventory slot position (template-first, config fallback).

        Args:
            slot_num: Slot number (1-28)
            force_detect: Force template detection (ignore cache)

        Returns:
            (rel_x, rel_y) relative coordinates or None if failed
        """
        if not 1 <= slot_num <= 28:
            logger.error(f"Invalid slot number: {slot_num}. Must be 1-28.")
            return None

        # Strategy 1: Template detection (if available)
        if self.template_service:
            img_gray = self.screen.capture_grayscale()
            if img_gray is not None:
                if self.template_service.detect_grid("inventory", img_gray, force=force_detect):
                    # Convert 1-indexed to 0-indexed
                    position = self.template_service.get_slot_position("inventory", slot_num - 1)
                    if position:
                        logger.debug(f"Slot {slot_num} resolved via template: {position}")
                        return position

        # Strategy 2: Config fallback
        coord = self.config.get("coordinates", "inventory", f"slot_{slot_num}")
        if coord and "x" in coord and "y" in coord:
            pos = (coord["x"], coord["y"])
            logger.debug(f"Slot {slot_num} resolved via config: {pos}")
            return pos

        logger.error(f"Failed to resolve slot {slot_num} (template and config failed)")
        return None

    def resolve_ui_button(
        self,
        button_name: str,
        force_detect: bool = False
    ) -> Optional[Tuple[int, int]]:
        """
        Resolve UI button position using template detection.

        Args:
            button_name: Name of the button template
            force_detect: Force template detection (ignore cache)

        Returns:
            (rel_x, rel_y) relative coordinates or None if failed
        """
        if not self.template_service:
            logger.error("Template service not available for button detection")
            return None

        img_gray = self.screen.capture_grayscale()
        if img_gray is None:
            logger.error("Failed to capture screenshot")
            return None

        if self.template_service.detect_button(button_name, img_gray, force=force_detect):
            position = self.template_service.get_button_position(button_name)
            if position:
                logger.debug(f"Button '{button_name}' resolved via template: {position}")
                return position

        logger.debug(f"Failed to detect button: {button_name}")
        return None

    def resolve_coordinate_path(
        self,
        *coord_path: str
    ) -> Optional[Tuple[int, int]]:
        """
        Resolve nested config coordinate path.

        Args:
            *coord_path: Variable number of keys to traverse config
                        Example: ("world", "varrock_fountain")

        Returns:
            (x, y) coordinates or None if path not found
        """
        current = self.config.get("coordinates")
        if not current:
            logger.error("No coordinates section in config")
            return None

        for key in coord_path:
            if not isinstance(current, dict):
                logger.error(f"Expected dict at '{key}' in coordinate path")
                return None
            current = current.get(key, {})
            if not current:
                logger.error(f"Coordinate path not found: {' -> '.join(coord_path)}")
                return None

        if isinstance(current, dict) and "x" in current and "y" in current:
            return (current["x"], current["y"])

        logger.error(f"No x/y coordinates at path: {' -> '.join(coord_path)}")
        return None

    def get_player_position(self) -> Tuple[int, int]:
        """
        Get player position (center of viewport).

        Returns:
            (x, y) relative coordinates of viewport center
        """
        dims = self.screen.get_viewport_dimensions()
        if not dims:
            logger.warning("Failed to get viewport dimensions, using fallback")
            return (400, 300)  # Reasonable fallback for typical OSRS window
        width, height = dims
        return (width // 2, height // 2)
