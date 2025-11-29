import json
import logging
import platform
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Config:
    """Centralized configuration for all scripts"""

    def __init__(self, config_file: str = "config.json") -> None:
        self.config_file = Path(config_file)
        self.data = self._load_config()

    def _load_config(self) -> dict:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load config: {e}")

        logger.info(
            f"Config file not found, creating default at {
                self.config_file}")
        config = self._default_config()
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Created default config file: {self.config_file}")
        except IOError as e:
            logger.warning(f"Failed to create config file: {e}")
        return config

    def _default_config(self) -> dict:
        """Default configuration template"""
        # Platform-specific Tesseract defaults
        system = platform.system()
        if system == "Windows":
            tesseract_default = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        elif system == "Darwin":  # macOS
            tesseract_default = "/opt/homebrew/bin/tesseract"
        else:  # Linux
            tesseract_default = "/usr/bin/tesseract"

        return {
            "window_title": "RuneLite - ",
            "tesseract_path": tesseract_default,

            "colors": {
                # Marker
                "yellow_tile_marker": "#FFFF00",
                "blue_tile_marker": "#FFFF00",

                # Item outlines
                "purple_item_outline": "#7d00ff",
                "red_outline": "#FF0000",

                # NPCs
                "green_dragon": "#00ffff",
                "guns_npc": "#00ffff",
                "banker": "#00FFFF",

                # Items
                "manta_ray": "#765C45",
                "sandwich": "#A81522",
                "extended_antifire": "#b392cb",
                "super_combat": "#1e6c0e",

                # Equipment
                "ardy_cloak": "#7d666e",
                "mythical_cape": "#aea2a3",
            },

            "coordinates": {
                # Inventory slots (28 total)
                "inventory": {
                    "slot_1": {"x": 591, "y": 257},
                    "slot_2": {"x": 633, "y": 256},
                    "slot_3": {"x": 672, "y": 257},
                    "slot_4": {"x": 715, "y": 258},
                    "last_slot": {"x": 715, "y": 470},
                },

                # UI elements
                "ui": {
                    "settings": {"x": 689, "y": 506},
                    "brightness": {"x": 712, "y": 308},
                    "zoom": {"x": 686, "y": 345},
                    "bank_deposit_all": {"x": 455, "y": 337},
                    "bank_search": {"x": 414, "y": 338},
                    "bank_close": {"x": 497, "y": 51},
                    "ge_collect": {"x": 466, "y": 93},
                },

                # Minimap locations
                "minimap": {
                    "green_dragons": {"x": 673, "y": 135},
                },

                # World interactions
                "world": {
                    "ge_clerk": {"x": 273, "y": 151},
                    "varrock_fountain": {"x": 594, "y": 85},
                    "bank_booth": {"x": 463, "y": 143},
                },

                # State checks
                "checks": {
                    "combat_indicator": {"x": 30, "y": 81},
                    "health_bar": {"x": 530, "y": 68, "w": 27, "h": 30},
                }
            },

            "timings": {
                "short": 0.5,
                "medium": 1.0,
                "long": 3.0,
                "teleport": 12.0,
            },

            "tolerances": {
                "color_match": 5,
                "click_offset": (0, 0),
            }
        }

    def save(self) -> bool:
        """Save config to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.data, indent=2, fp=f)
            return True
        except IOError as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def get(self, *path, default: Any = None) -> Any:
        """Get config value by path"""
        current = self.data
        try:
            for key in path:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
