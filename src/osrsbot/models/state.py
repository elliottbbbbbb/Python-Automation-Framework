import logging
import os
import pytesseract
from typing import Optional, Any

from osrsbot.services.ocr_service import OCRService, OCRRegion
from osrsbot.models.config import Config

logger = logging.getLogger(__name__)


class GameState:
    """
    Manages game state checks like HP, inventory, and combat status.

    Uses OCRService for reading stats from the game UI.
    """

    def __init__(
            self,
            interface: Any,
            config: Config,
            screen_service=None) -> None:
        self.interface = interface
        self.config = config
        self.screen = screen_service

        # Set up Tesseract path
        tesseract_path = self.config.get("tesseract_path")
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            logger.info(f"Using Tesseract from config: {tesseract_path}")
        elif os.getenv("TESSERACT_PATH"):
            pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_PATH")
            logger.info(f"Using Tesseract from env: {os.getenv('TESSERACT_PATH')}")
        else:
            logger.info("Using default Tesseract path (system)")

        # Initialize OCR service
        self.ocr_service = OCRService(
            window_getter=self.interface.get_window_position,
            tesseract_path=tesseract_path,
            debug=True
        )

        # Get OCR TTL from config
        self._hp_ttl = float(self.config.get("ocr", "hp_ttl", default=0.5))
        self._ocr_window_size = self.config.get("ocr", "window_size", default=5)

    def inventory_full(self) -> bool:
        """Check if inventory is full by checking the last slot color."""
        coord = self.config.get("coordinates", "inventory", "last_slot")
        if not coord:
            logger.error("last_slot coordinates not in config")
            return False

        # Get empty slot color from config
        empty_color_hex = self.config.get("colors", "empty_inventory_slot")
        if empty_color_hex:
            empty_color = self._hex_to_rgb(empty_color_hex)
        else:
            logger.warning("empty_inventory_slot color not in config, using fallback")
            empty_color = (75, 66, 58)

        # Use ScreenService if available, otherwise fall back to interface
        if self.screen:
            color = self.screen.get_pixel_color(coord['x'], coord['y'], relative=True)
        else:
            color = self.interface.get_pixel(coord['x'], coord['y'])

        is_full = color != empty_color
        logger.debug(f"Inventory full check: {is_full} (slot color: {color})")
        return is_full

    def in_combat(self) -> bool:
        """Check if player is in combat by checking combat indicator color."""
        coord = self.config.get("coordinates", "checks", "combat_indicator")
        if not coord:
            logger.error("combat check coordinates were not found in config.")
            return False

        # Use ScreenService if available, otherwise fall back to interface
        if self.screen:
            color = self.screen.get_pixel_color(coord['x'], coord['y'], relative=True)
        else:
            color = self.interface.get_pixel(coord['x'], coord['y'])

        # Get combat colors from config
        combat_green_hex = self.config.get("colors", "combat_indicator_green")
        combat_red_hex = self.config.get("colors", "combat_indicator_red")

        if combat_green_hex and combat_red_hex:
            combat_colors = [
                self._hex_to_rgb(combat_green_hex),
                self._hex_to_rgb(combat_red_hex)
            ]
        else:
            logger.warning("Combat indicator colors not in config, using fallback")
            combat_colors = [(7, 139, 54), (99, 21, 19)]

        tolerance = self.config.get("tolerances", "color_match", default=10)

        return any(
            all(abs(color[i] - cc[i]) <= tolerance for i in range(3))
            for cc in combat_colors
        )

    def get_hp(self, force: bool = False) -> Optional[int]:
        """
        Get current HP using OCR.

        Args:
            force: If True, bypass cache and force new OCR reading

        Returns:
            Current HP value or None if OCR failed
        """
        # Get HP region from config
        hp_region_config = self.config.get("coordinates", "ocr", "hp_region")
        if not hp_region_config:
            logger.error("hp_region not in config")
            return None

        # Create OCR region
        hp_region = OCRRegion(
            x=hp_region_config["x"],
            y=hp_region_config["y"],
            width=hp_region_config["width"],
            height=hp_region_config["height"],
            name="hp"
        )

        # Read HP using OCR service
        hp = self.ocr_service.read_number(
            region=hp_region,
            min_value=1,
            max_value=99,
            smooth=not force,
            window_size=self._ocr_window_size,
            ttl=self._hp_ttl if not force else 0
        )

        if hp is None:
            logger.debug("get_hp: OCR returned None")
        else:
            logger.debug(f"get_hp: {hp}")

        return hp

    def get_health(self, force: bool = False) -> Optional[int]:
        """Alias for get_hp() for backward compatibility."""
        return self.get_hp(force=force)

    def get_prayer(self, force: bool = False) -> Optional[int]:
        """
        Get current prayer points using OCR.

        Args:
            force: If True, bypass cache and force new OCR reading

        Returns:
            Current prayer points or None if OCR failed
        """
        # Get prayer region from config
        prayer_region_config = self.config.get("coordinates", "ocr", "prayer_region")
        if not prayer_region_config:
            logger.warning("prayer_region not in config")
            return None

        # Create OCR region
        prayer_region = OCRRegion(
            x=prayer_region_config["x"],
            y=prayer_region_config["y"],
            width=prayer_region_config["width"],
            height=prayer_region_config["height"],
            name="prayer"
        )

        # Read prayer using OCR service
        prayer = self.ocr_service.read_number(
            region=prayer_region,
            min_value=0,
            max_value=99,
            smooth=not force,
            window_size=self._ocr_window_size,
            ttl=self._hp_ttl if not force else 0
        )

        if prayer is None:
            logger.debug("get_prayer: OCR returned None")
        else:
            logger.debug(f"get_prayer: {prayer}")

        return prayer

    def get_run_energy(self, force: bool = False) -> Optional[int]:
        """
        Get current run energy using OCR.

        Args:
            force: If True, bypass cache and force new OCR reading

        Returns:
            Current run energy (0-100) or None if OCR failed
        """
        # Get run energy region from config
        run_region_config = self.config.get("coordinates", "ocr", "run_energy_region")
        if not run_region_config:
            logger.warning("run_energy_region not in config")
            return None

        # Create OCR region
        run_region = OCRRegion(
            x=run_region_config["x"],
            y=run_region_config["y"],
            width=run_region_config["width"],
            height=run_region_config["height"],
            name="run_energy"
        )

        # Read run energy using OCR service
        energy = self.ocr_service.read_number(
            region=run_region,
            min_value=0,
            max_value=100,
            smooth=not force,
            window_size=self._ocr_window_size,
            ttl=self._hp_ttl if not force else 0
        )

        if energy is None:
            logger.debug("get_run_energy: OCR returned None")
        else:
            logger.debug(f"get_run_energy: {energy}")

        return energy

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
