"""
Stat Queries - CQRS Query for player stats.

Handles:
- HP reading (OCR-based)
- Prayer points reading (OCR-based)
- Run energy reading (OCR-based)

Responsibilities:
- Read player stats via OCR
- Error handling and fallbacks
"""

import logging
from typing import Optional, TYPE_CHECKING
import numpy as np
import cv2

from osrsbot.services.template_ocr_service import TemplateOCRService, ORB_GREEN, ORB_RED, CYAN, YELLOW
from osrsbot.models.config import Config

if TYPE_CHECKING:
    from osrsbot.services.screen_service import ScreenService

logger = logging.getLogger(__name__)


class StatQueries:
    """
    Player stat queries (HP, prayer, run energy).

    Uses OCR for reading stat values from orbs.
    """

    def __init__(
        self,
        screen: 'ScreenService',
        ocr_service: TemplateOCRService,
        config: Config
    ):
        self.screen = screen
        self.ocr = ocr_service
        self.config = config

    def get_hp(self, force: bool = False) -> Optional[int]:
        """
        Get current HP.

        Args:
            force: Currently ignored (OCR is fast enough)

        Returns:
            Current HP or None if OCR failed
        """
        hp_region_config = self.config.get("coordinates", "ocr", "hp_region")
        if not hp_region_config:
            logger.error("hp_region not in config")
            return None

        x, y = hp_region_config["x"], hp_region_config["y"]
        width, height = hp_region_config["width"], hp_region_config["height"]

        img = self.screen.capture(region=(x, y, width, height), relative=True)
        if img is None:
            logger.debug("get_hp: Failed to capture screen region")
            return None

        # Convert PIL to numpy array for OCR
        img_np = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        hp = self.ocr.extract_number(
            img_np,
            font_name="plain11",
            colors=[ORB_GREEN, ORB_RED],
            correlation_threshold=0.95
        )

        if hp is None:
            logger.debug("get_hp: OCR returned None")
        else:
            logger.debug(f"get_hp: {hp}")

        return hp

    def get_prayer(self, force: bool = False) -> Optional[int]:
        """
        Get current prayer points.

        Args:
            force: Currently ignored (OCR is fast enough)

        Returns:
            Current prayer points or None if OCR failed
        """
        prayer_region_config = self.config.get("coordinates", "ocr", "prayer_region")
        if not prayer_region_config:
            logger.warning("prayer_region not in config")
            return None

        x, y = prayer_region_config["x"], prayer_region_config["y"]
        width, height = prayer_region_config["width"], prayer_region_config["height"]

        img = self.screen.capture(region=(x, y, width, height), relative=True)
        if img is None:
            logger.debug("get_prayer: Failed to capture screen region")
            return None

        # Convert PIL to numpy array for OCR
        img_np = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        prayer = self.ocr.extract_number(
            img_np,
            font_name="plain11",
            colors=[CYAN],
            correlation_threshold=0.95
        )

        if prayer is None:
            logger.debug("get_prayer: OCR returned None")
        else:
            logger.debug(f"get_prayer: {prayer}")

        return prayer

    def get_run_energy(self, force: bool = False) -> Optional[int]:
        """
        Get current run energy (0-100).

        Args:
            force: Currently ignored (OCR is fast enough)

        Returns:
            Current run energy or None if OCR failed
        """
        run_region_config = self.config.get("coordinates", "ocr", "run_energy_region")
        if not run_region_config:
            logger.warning("run_energy_region not in config")
            return None

        x, y = run_region_config["x"], run_region_config["y"]
        width, height = run_region_config["width"], run_region_config["height"]

        img = self.screen.capture(region=(x, y, width, height), relative=True)
        if img is None:
            logger.debug("get_run_energy: Failed to capture screen region")
            return None

        # Convert PIL to numpy array for OCR
        img_np = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        energy = self.ocr.extract_number(
            img_np,
            font_name="plain11",
            colors=[YELLOW],
            correlation_threshold=0.95
        )

        if energy is None:
            logger.debug("get_run_energy: OCR returned None")
        else:
            logger.debug(f"get_run_energy: {energy}")

        return energy
