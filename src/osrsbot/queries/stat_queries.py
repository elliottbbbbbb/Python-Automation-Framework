"""
Stat Queries - CQRS Query for player stats.

Handles:
- HP reading (OCR-based)
- Prayer points reading (OCR-based)
- Run energy reading (OCR-based)
- Skill level reading from skills tab (OCR-based)

Responsibilities:
- Read player stats via OCR
- Error handling and fallbacks
"""

import logging
from typing import TYPE_CHECKING, Optional, Dict

import cv2
import numpy as np

from osrsbot.models.config import Config
from osrsbot.services.template_ocr_service import (
    CYAN,
    ORB_GREEN,
    ORB_RED,
    WHITE,
    YELLOW,
    TemplateOCRService,
)

if TYPE_CHECKING:
    from osrsbot.services.screen_service import ScreenService

logger = logging.getLogger(__name__)

# OSRS skills tab grid layout (Fixed Mode).
# Each skill cell shows current/base level. We read the base level.
# Grid is 3 columns x 8 rows. Mapping: skill -> (col, row).
SKILL_POSITIONS = {
    # Column 0 (left)
    "attack": (0, 0),
    "strength": (0, 1),
    "defence": (0, 2),
    "ranged": (0, 3),
    "prayer": (0, 4),
    "magic": (0, 5),
    "runecraft": (0, 6),
    "construction": (0, 7),
    # Column 1 (middle)
    "hitpoints": (1, 0),
    "agility": (1, 1),
    "herblore": (1, 2),
    "thieving": (1, 3),
    "crafting": (1, 4),
    "fletching": (1, 5),
    "slayer": (1, 6),
    "hunter": (1, 7),
    # Column 2 (right)
    "mining": (2, 0),
    "smithing": (2, 1),
    "fishing": (2, 2),
    "cooking": (2, 3),
    "firemaking": (2, 4),
    "woodcutting": (2, 5),
    "farming": (2, 6),
}


class StatQueries:
    """
    Player stat queries (HP, prayer, run energy).

    Uses OCR for reading stat values from orbs.
    """

    def __init__(
        self, screen: "ScreenService", ocr_service: TemplateOCRService, config: Config
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
            correlation_threshold=0.95,
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

        # Use ORB_GREEN, ORB_RED for better color range coverage (prayer orb can vary slightly)
        prayer = self.ocr.extract_number(
            img_np, font_name="plain11", colors=[ORB_GREEN, ORB_RED], correlation_threshold=0.95
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

        # Use ORB_GREEN, ORB_RED for better color range coverage (run energy can vary)
        energy = self.ocr.extract_number(
            img_np, font_name="plain11", colors=[ORB_GREEN, ORB_RED], correlation_threshold=0.95
        )

        if energy is None:
            logger.debug("get_run_energy: OCR returned None")
        else:
            logger.debug(f"get_run_energy: {energy}")

        return energy

    def get_special_attack_percentage(self, force: bool = False) -> Optional[int]:
        """
        Get current special attack percentage (0-100).

        Args:
            force: Currently ignored (OCR is fast enough)

        Returns:
            Current special attack percentage or None if OCR failed
        """
        spec_region_config = self.config.get(
            "coordinates", "ocr", "special_attack_region"
        )
        if not spec_region_config:
            logger.warning("special_attack_region not in config")
            return None

        x, y = spec_region_config["x"], spec_region_config["y"]
        width, height = spec_region_config["width"], spec_region_config["height"]

        img = self.screen.capture(region=(x, y, width, height), relative=True)
        if img is None:
            logger.debug("get_special_attack_percentage: Failed to capture screen region")
            return None

        # Convert PIL to numpy array for OCR
        img_np = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        # Use ORB_GREEN, ORB_RED for better color range coverage (spec attack can vary)
        percentage = self.ocr.extract_number(
            img_np, font_name="plain11", colors=[ORB_GREEN, ORB_RED], correlation_threshold=0.95
        )

        if percentage is None:
            logger.debug("get_special_attack_percentage: OCR returned None")
        else:
            logger.debug(f"get_special_attack_percentage: {percentage}")

        return percentage

    def get_all_stats(self, force: bool = False) -> Dict[str, Optional[int]]:
        """
        Read all player stats using template OCR.

        Returns:
            dict with keys: hp, prayer, run, spec
        """
        return {
            "hp": self._read_stat(
                region_key="hp_region",
                colors=[ORB_GREEN, ORB_RED],
            ),
            "prayer": self._read_stat(
                region_key="prayer_region",
                colors=[ORB_GREEN, ORB_RED],
            ),
            "run": self._read_stat(
                region_key="run_energy_region",
                colors=[ORB_GREEN, ORB_RED],
            ),
            "spec": self._read_stat(
                region_key="special_attack_region",
                colors=[ORB_GREEN, ORB_RED],
            ),
        }

    def _read_stat(
        self,
        region_key: str,
        colors: list,
        threshold: float = 0.95,
    ) -> Optional[int]:
        """
        Internal helper to OCR a numeric stat from a region.
        """
        region = self.config.get("coordinates", "ocr", region_key)
        if not region:
            return None

        img = self.screen.capture(
            region=(
                region["x"],
                region["y"],
                region["width"],
                region["height"],
            ),
            relative=True,
        )
        if img is None:
            return None

        img_np = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        return self.ocr.extract_number(
            img_np,
            font_name="plain11",
            colors=colors,
            correlation_threshold=threshold,
        )

    def get_skill_level(self, skill_name: str) -> Optional[int]:
        """
        Read a skill's base level from the skills tab via OCR.

        The skills tab must already be open when this is called.

        Args:
            skill_name: Lowercase skill name (e.g. "fletching", "herblore").

        Returns:
            Base level as int (1-99), or None if OCR failed.
        """
        if skill_name not in SKILL_POSITIONS:
            logger.warning(f"get_skill_level: Unknown skill '{skill_name}'")
            return None

        col, row = SKILL_POSITIONS[skill_name]

        grid = self.config.get("coordinates", "ocr", "skills_tab")
        if not grid:
            logger.warning("get_skill_level: skills_tab not in config")
            return None

        # Compute pixel region for the base level number within the cell
        x = grid["origin_x"] + col * grid["cell_width"] + grid["base_level_offset_x"]
        y = grid["origin_y"] + row * grid["cell_height"] + grid["base_level_offset_y"]
        w = grid["base_level_width"]
        h = grid["base_level_height"]

        img = self.screen.capture(region=(x, y, w, h), relative=True)
        if img is None:
            logger.debug(f"get_skill_level: Failed to capture region for {skill_name}")
            return None

        img_np = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        # Try YELLOW first (standard skills tab text color)
        level = self.ocr.extract_number(
            img_np,
            font_name="plain11",
            colors=[YELLOW],
            correlation_threshold=0.95,
        )

        if level is None:
            # Retry with contrast enhancement for dim/anti-aliased text
            enhanced = cv2.convertScaleAbs(img_np, alpha=2.5, beta=50)
            level = self.ocr.extract_number(
                enhanced,
                font_name="plain11",
                colors=[YELLOW, WHITE],
                correlation_threshold=0.85,
            )

        # Validate range
        if level is not None and not (1 <= level <= 99):
            logger.warning(
                f"get_skill_level: OCR returned {level} for {skill_name}, "
                f"outside valid range 1-99"
            )
            return None

        if level is not None:
            logger.info(f"get_skill_level: {skill_name} = {level}")
        else:
            logger.debug(f"get_skill_level: OCR returned None for {skill_name}")

        return level