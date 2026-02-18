import json
import logging
import platform
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Config:
    """Centralized configuration for all scripts"""

    def __init__(self, config_file: str = None) -> None:
        # If no config file specified, determine the best location
        if config_file is None:
            # When running as .exe, prioritize config.json next to the executable
            if getattr(sys, "frozen", False):
                external_config = Path(sys.executable).parent / "config.json"
                if external_config.exists():
                    logger.info(f"Using external config next to .exe: {external_config}")
                    self.config_file = external_config
                else:
                    # Fall back to bundled config inside .exe
                    logger.info("No external config found, using bundled config")
                    config_dir = Path(__file__).parent.parent
                    self.config_file = config_dir / "config.json"
            else:
                # When running in dev mode, use the one in src/osrsbot/
                config_dir = Path(__file__).parent.parent
                self.config_file = config_dir / "config.json"
        else:
            self.config_file = Path(config_file)
        self.data = self._load_config()

    def _load_config(self) -> dict:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load config: {e}")

        logger.info(
            f"Config file not found, creating default at {
                self.config_file}"
        )
        config = self._default_config()
        try:
            with open(self.config_file, "w") as f:
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
            status_socket_default = r"C:\Users\YourUsername\.runelite\live_data.json"
        elif system == "Darwin":  # macOS
            tesseract_default = "/opt/homebrew/bin/tesseract"
            status_socket_default = "~/.runelite/live_data.json"
        else:  # Linux
            tesseract_default = "/usr/bin/tesseract"
            status_socket_default = "~/.runelite/live_data.json"

        return {
            "account_name": "YourAccountName",
            "window_title": "RuneLite - YourAccountName",
            "log_level": "DEBUG",
            "tesseract_path": tesseract_default,
            "colors": {
                "yellow_tile_marker": "#fcfc01",
                "blue_outline": "#00ffff",
                "purple_item_outline": "#7d00ff",
                "red_outline": "#FF0000",
                "green_dragon": "#00ffff",
                "guns_npc": "#00ffff",
                "banker": "#00FFFF",
                "manta_ray": "#765C45",
                "sandwich": "#A81522",
                "extended_antifire": "#b392cb",
                "super_combat": "#1e6c0e",
                "ardy_cloak": "#7d666e",
                "mythical_cape": "#aea2a3",
                "empty_inventory_slot": "#4B423A",
                "combat_indicator_green": "#078B36",
                "combat_indicator_red": "#63150D",
                "combat_indicator_teal": "#068a34",
                "clay_rock": "#CD853F",
                "copper_rock": "#B87333",
                "tin_rock": "#708090",
                "iron_rock": "#8B7355",
                "coal_rock": "#36454F",
                "gold_rock": "#FFD700",
                "mithril_rock": "#4682B4",
                "adamantite_rock": "#50C878",
                "runite_rock": "#00CED1",
                "granite_rock": "#A9A9A9",
                "chinning_stack_tile_1": "#00FFFF",
                "chinning_stack_tile_2": "#FF00FF",
                "chinning_rope_color": "#8B4513"
            },
            "coordinates": {
                "inventory": {
                    "slot_1": {"x": 591, "y": 257},
                    "slot_2": {"x": 633, "y": 256},
                    "slot_3": {"x": 672, "y": 257},
                    "slot_4": {"x": 715, "y": 258},
                    "last_slot": {"x": 715, "y": 470},
                },
                "ui": {
                    "settings": {"x": 687, "y": 509},
                    "brightness": {"x": 712, "y": 308},
                    "zoom": {"x": 686, "y": 345},
                    "bank_deposit_all": {"x": 455, "y": 337},
                    "bank_search": {"x": 414, "y": 338},
                    "bank_close": {"x": 497, "y": 51},
                    "ge_collect": {"x": 466, "y": 93},
                },
                "minimap": {
                    "green_dragons": {"x": 673, "y": 135},
                },
                "world": {
                    "ge_clerk": {"x": 273, "y": 151},
                    "varrock_fountain": {"x": 594, "y": 85},
                    "bank_booth": {"x": 463, "y": 143},
                },
                "checks": {
                    "combat_indicator": {"x": 30, "y": 81},
                    "health_bar": {"x": 530, "y": 68, "w": 27, "h": 30},
                },
                "ocr": {
                    "hp_region": {"x": 527, "y": 79, "width": 35, "height": 20},
                    "prayer_region": {"x": 527, "y": 111, "width": 45, "height": 30},
                    "run_energy_region": {"x": 530, "y": 143, "width": 35, "height": 20},
                    "special_attack_region": {"x": 557, "y": 169, "width": 35, "height": 20},
                    "world_coord_region": {"x": 50, "y": 305, "width": 100, "height": 21},
                },
            },
            "timings": {
                "short": [0.4, 0.7],
                "medium": [0.8, 1.3],
                "long": [2.5, 3.8],
                "teleport": [11.0, 13.0],
            },
            "tolerances": {
                "color_match": 5,
                "click_offset": [0, 0],
            },
            "ocr": {
                "hp_ttl": 0.1,
                "window_size": 5,
            },
            "mouse": {
                "min_speed": 0.2,
                "max_speed": 0.6,
                "overshoot_chance": 0.15,
                "overshoot_distance": 20,
                "click_variance": 3,
                "post_click_delay_min": 0.05,
                "post_click_delay_max": 0.15,
            },
            "status_socket": {
                "enabled": True,
                "data_file": status_socket_default,
                "poll_interval": 0.1,
            },
            "walker": {
                "minimap_center_x": 654,
                "minimap_center_y": 111,
                "tile_size": 4,
                "arrival_tolerance": 2,
                "max_click_distance": 15,
                "enable_anti_ban_variance": True,
            },
            "arduino": {
                "enabled": False,
                "serial_port": "COM3",
                "baud_rate": 115200,
                "fallback_to_software": True,
                "connection_timeout": 2.0,
            },
            "templates": {
                "overload_potion": "images/bot/items/overload_potion.png",
                "absorption_potion": "images/bot/items/absorption_potion.png",
                "dwarven_rock_cake": "images/bot/items/dwarven_rock_cake.png",
                "locator_orb": "images/bot/items/locator_orb.png",
                "banker_templates": [
                    "images/bot/bank/banker_santa_hat.PNG",
                    "images/bot/bank/banker_2.PNG",
                    "images/bot/bank/banker_3_zoomed_out.PNG",
                ],
                "bank_search_button": "images/bot/bank/bank_search_button.PNG",
                "ui_grids": {
                    "inventory": {
                        "path": "images/bot/ui_templates/inventory_empty.PNG",
                        "rows": 7,
                        "cols": 4,
                        "threshold": 0.30,
                        "sticky": True,
                        "padding": 0,
                        "border_offset": 20,
                    },
                    "equipment": {
                        "path": "images/bot/ui_templates/inventory_empty.PNG",
                        "rows": 7,
                        "cols": 2,
                        "threshold": 0.30,
                        "sticky": True,
                        "padding": 0,
                        "border_offset": 13,
                    },
                    "prayer": {
                        "path": "images/bot/ui_templates/inventory_empty.PNG",
                        "rows": 6,
                        "cols": 5,
                        "threshold": 0.30,
                        "sticky": True,
                        "padding": 0,
                        "border_offset": 13,
                    },
                    "spellbook": {
                        "path": "images/bot/ui_templates/inventory_empty.PNG",
                        "rows": 10,
                        "cols": 7,
                        "threshold": 0.30,
                        "sticky": True,
                        "padding": 2,
                        "border_offset": 15,
                        "border_offset_x": 22,
                        "border_offset_y": 12,
                    },
                    "minimap": {
                        "path": "images/bot/ui_templates/minimap_fixed.png",
                        "rows": 1,
                        "cols": 1,
                        "threshold": 0.55,
                        "sticky": True,
                    },
                    "chat": {
                        "path": "images/bot/ui_templates/chat.png",
                        "rows": 1,
                        "cols": 1,
                        "threshold": 0.40,
                        "sticky": True,
                    },
                },
                "ui_buttons": {
                    "inventory_tab": {
                        "path": "images/bot/ui_templates/inventory.png",
                        "threshold": 0.50,
                    },
                    "equipment_tab": {
                        "path": "images/bot/ui_templates/equipment.PNG",
                        "threshold": 0.70,
                    },
                    "prayer_tab": {
                        "path": "images/bot/ui_templates/prayer.PNG",
                        "threshold": 0.75,
                    },
                    "protect_from_melee": {
                        "path": "images/bot/prayers/melee.PNG",
                        "threshold": 0.70,
                    },
                    "protect_from_magic": {
                        "path": "images/bot/prayers/magic.PNG",
                        "threshold": 0.70,
                    },
                    "protect_from_ranged": {
                        "path": "images/bot/prayers/ranged.PNG",
                        "threshold": 0.70,
                    },
                    "spellbook_tab": {
                        "path": "images/bot/ui_templates/spellbook.PNG",
                        "threshold": 0.70,
                    },
                    "skills_tab": {
                        "path": "images/bot/ui_templates/skills.PNG",
                        "threshold": 0.70,
                    },
                    "logout_tab": {
                        "path": "images/bot/ui_templates/logout.PNG",
                        "threshold": 0.70,
                    },
                    "logout": {
                        "path": "images/bot/settings/runelite_logout.png",
                        "threshold": 0.68,
                    },
                    "settings_collapse": {
                        "path": "images/bot/settings/runelite_settings_collapse.png",
                        "threshold": 0.68,
                    },
                    "bank_presets": {
                        "path": "images/bot/near_reality/bank_presets.png",
                        "threshold": 0.70,
                    },
                    "autoretal_on": {
                        "path": "images/bot/combat/autoretal_on.png",
                        "threshold": 0.70,
                    },
                    "autoretal_off": {
                        "path": "images/bot/combat/autoretal_off.png",
                        "threshold": 0.70,
                    },
                    "good_click_1": {
                        "path": "images/bot/mouse_clicks/red_1.png",
                        "threshold": 0.89,
                    },
                    "good_click_2": {
                        "path": "images/bot/mouse_clicks/red_2.png",
                        "threshold": 0.89,
                    },
                    "good_click_3": {
                        "path": "images/bot/mouse_clicks/red_3.png",
                        "threshold": 0.89,
                    },
                    "good_click_4": {
                        "path": "images/bot/mouse_clicks/red_4.png",
                        "threshold": 0.89,
                    },
                },
            },
            "license": {
                "api_url": "https://osrs-automation-framework-production.up.railway.app",
                "purchase_url": "https://yoursite.com/buy",
                "timeout": 10,
                "cache_file": ".license_cache",
                "offline_grace_period_hours": 24,
            },
            "zulrah": {
                "tile_colors": {
                    "middle": "#FF0000",
                    "south": "#00FF00",
                    "west": "#0000FF",
                    "east": "#FFFF00",
                    "pillar_west_side": "#00FFFF",
                    "pillar_east_side": "#FF00FF",
                    "north": "#FFA500",
                    "starting_area": "#800080",
                },
                "rotations": {
                    "1": {
                        "phases": [
                            {"phase_num": 1, "safe_position": "starting_area", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 2, "safe_position": "south", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": True},
                            {"phase_num": 3, "safe_position": "west", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 4, "safe_position": "south", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": False},
                            {"phase_num": 5, "safe_position": "middle", "prayer": "protect_magic", "attack_style": "range", "form": "magma", "spawns_snakelings": False},
                            {"phase_num": 6, "safe_position": "west", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": False},
                            {"phase_num": 7, "safe_position": "middle", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 8, "safe_position": "east", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": False},
                            {"phase_num": 9, "safe_position": "middle", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": False},
                            {"phase_num": 10, "safe_position": "west", "prayer": "protect_both", "attack_style": "both", "form": "tanzanite", "spawns_snakelings": False},
                        ]
                    },
                    "2": {
                        "phases": [
                            {"phase_num": 1, "safe_position": "starting_area", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": False},
                            {"phase_num": 2, "safe_position": "north", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 3, "safe_position": "west", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": True},
                            {"phase_num": 4, "safe_position": "south", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": False},
                            {"phase_num": 5, "safe_position": "middle", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 6, "safe_position": "west", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 7, "safe_position": "pillar_west_side", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": False},
                            {"phase_num": 8, "safe_position": "middle", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 9, "safe_position": "pillar_east_side", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": False},
                            {"phase_num": 10, "safe_position": "middle", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 11, "safe_position": "east", "prayer": "protect_both", "attack_style": "both", "form": "tanzanite", "spawns_snakelings": False},
                        ]
                    },
                    "3": {
                        "phases": [
                            {"phase_num": 1, "safe_position": "starting_area", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 2, "safe_position": "west", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 3, "safe_position": "south", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": True},
                            {"phase_num": 4, "safe_position": "middle", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 5, "safe_position": "east", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": False},
                            {"phase_num": 6, "safe_position": "north", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 7, "safe_position": "west", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": False},
                            {"phase_num": 8, "safe_position": "middle", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 9, "safe_position": "pillar_west_side", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": False},
                            {"phase_num": 10, "safe_position": "middle", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 11, "safe_position": "west", "prayer": "protect_both", "attack_style": "both", "form": "tanzanite", "spawns_snakelings": False},
                        ]
                    },
                    "4": {
                        "phases": [
                            {"phase_num": 1, "safe_position": "starting_area", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": False},
                            {"phase_num": 2, "safe_position": "east", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": True},
                            {"phase_num": 3, "safe_position": "south", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": False},
                            {"phase_num": 4, "safe_position": "west", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 5, "safe_position": "east", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": False},
                            {"phase_num": 6, "safe_position": "middle", "prayer": "protect_magic", "attack_style": "range", "form": "magma", "spawns_snakelings": False},
                            {"phase_num": 7, "safe_position": "west", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 8, "safe_position": "east", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": False},
                            {"phase_num": 9, "safe_position": "middle", "prayer": "protect_ranged", "attack_style": "mage", "form": "serpentine", "spawns_snakelings": False},
                            {"phase_num": 10, "safe_position": "pillar_west_side", "prayer": "protect_magic", "attack_style": "range", "form": "tanzanite", "spawns_snakelings": False},
                            {"phase_num": 11, "safe_position": "east", "prayer": "protect_both", "attack_style": "both", "form": "tanzanite", "spawns_snakelings": False},
                        ]
                    },
                },
                "form_colors": {
                    "serpentine": "#006400",
                    "tanzanite": "#4169E1",
                    "magma": "#DC143C",
                },
                "hp_threshold": 40,
                "prayer_threshold": 20,
                "food_slot": 1,
                "prayer_potion_slot": 2,
                "teleport_threshold_hp": 15,
                "phase_duration": 30,
                "color_tolerance": 30,
                "form_detection_delay": 0.5,
                "movement_delay": "medium",
                "attack_delay": "short",
            },
            "item_detection": {
                "enabled": False,
                "items_dir": "images/items",
                "threshold": 0.75,
                "load_at_startup": True,
            },
        }

    def save(self) -> bool:
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.data, f, indent=2)
            return True
        except IOError as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def get(self, *path, default: Any = None) -> Any:
        current = self.data
        try:
            for key in path:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default

    def get_window_title(self) -> str:
        """Constructs window title from account name"""
        account_name = self.get("account_name", default="")
        if not account_name or account_name == "YourAccountName":
            logger.warning(
                "No account_name set in config.json. "
                "Please set 'account_name' field."
            )
            return "RuneLite - "
        return f"RuneLite - {account_name}"
