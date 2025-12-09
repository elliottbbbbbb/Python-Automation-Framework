import logging
import os
import pytesseract
from typing import Optional, Any, TYPE_CHECKING

from osrsbot.services.ocr_service import OCRService, OCRRegion
from osrsbot.models.config import Config

if TYPE_CHECKING:
    from osrsbot.services.screen_service import ScreenService

logger = logging.getLogger(__name__)


class GameState:
    """
    Manages game state checks like HP and combat status.

    Uses OCRService for reading stats from the game UI.
    """

    def __init__(
            self,
            interface: Any,
            config: Config,
            ocr_service: Any,
            screen_service: Optional["ScreenService"] = None) -> None:
        self.interface = interface
        self.config = config
        self.ocr_service = ocr_service
        self.screen: Optional["ScreenService"] = screen_service

        self._hp_ttl = float(self.config.get("ocr", "hp_ttl", default=0.5))
        self._ocr_window_size = self.config.get(
            "ocr", "window_size", default=5)

    def in_combat(self) -> bool:
        coord = self.config.get("coordinates", "checks", "combat_indicator")
        if not coord:
            logger.error("combat check coordinates were not found in config.")
            return False

        if self.screen:
            color = self.screen.get_pixel_color(
                coord['x'], coord['y'], relative=True)
        else:
            color = self.interface.get_pixel(coord['x'], coord['y'])

        combat_green_hex = self.config.get("colors", "combat_indicator_green")
        combat_red_hex = self.config.get("colors", "combat_indicator_red")

        if combat_green_hex and combat_red_hex:
            combat_colors = [
                self._hex_to_rgb(combat_green_hex),
                self._hex_to_rgb(combat_red_hex)
            ]
        else:
            logger.warning(
                "Combat indicator colors not in config, using fallback")
            combat_colors = [(7, 139, 54), (99, 21, 19)]

        tolerance = self.config.get("tolerances", "color_match", default=10)

        return any(
            all(abs(color[i] - cc[i]) <= tolerance for i in range(3))
            for cc in combat_colors
        )

    def get_hp(self, force: bool = False) -> Optional[int]:
        """
        Args:
            force: If True, bypass cache and force new OCR reading

        Returns:
            Current HP value or None if OCR failed
        """
        hp_region_config = self.config.get("coordinates", "ocr", "hp_region")
        if not hp_region_config:
            logger.error("hp_region not in config")
            return None

        hp_region = OCRRegion(
            x=hp_region_config["x"],
            y=hp_region_config["y"],
            width=hp_region_config["width"],
            height=hp_region_config["height"],
            name="hp"
        )

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
        Args:
            force: If True, bypass cache and force new OCR reading

        Returns:
            Current prayer points or None if OCR failed
        """
        prayer_region_config = self.config.get(
            "coordinates", "ocr", "prayer_region")
        if not prayer_region_config:
            logger.warning("prayer_region not in config")
            return None

        prayer_region = OCRRegion(
            x=prayer_region_config["x"],
            y=prayer_region_config["y"],
            width=prayer_region_config["width"],
            height=prayer_region_config["height"],
            name="prayer"
        )

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
        Args:
            force: If True, bypass cache and force new OCR reading

        Returns:
            Current run energy (0-100) or None if OCR failed
        """
        run_region_config = self.config.get(
            "coordinates", "ocr", "run_energy_region")
        if not run_region_config:
            logger.warning("run_energy_region not in config")
            return None

        run_region = OCRRegion(
            x=run_region_config["x"],
            y=run_region_config["y"],
            width=run_region_config["width"],
            height=run_region_config["height"],
            name="run_energy"
        )

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
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
