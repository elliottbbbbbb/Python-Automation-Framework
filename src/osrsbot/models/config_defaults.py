import platform


def get_defaults() -> dict:
    """
    Complete default configuration for the OSRS bot.

    These values are used as the base for every run. The user's config.json
    is deep-merged on top, so users only need to specify what they want to
    override (typically: account_name, window_title, colors, live_view).

    Template image paths point to the bundled developer images. Users who
    need different templates (different client theme / resolution) should
    replace the relevant images in the images/ folder next to the exe.
    """
    system = platform.system()
    if system == "Windows":
        tesseract_default = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    elif system == "Darwin":
        tesseract_default = "/opt/homebrew/bin/tesseract"
    else:
        tesseract_default = "/usr/bin/tesseract"

    return {
        "account_name": "YourAccountName",
        "window_title": "RuneLite - YourAccountName",
        "log_level": "DEBUG",
        "tesseract_path": tesseract_default,

        # ── Colors ────────────────────────────────────────────────────────────
        # Match these to your RuneLite NPC Indicator / tile marker colors.
        "colors": {
            "yellow_tile_marker": "#fcfc01",
            "blue_outline": "#00ffff",
            "purple_item_outline": "#7d00ff",
            "red_outline": "#FF0000",
            "green_dragon": "#00ffff",
            "guns_npc": "#00ffff",
            "banker": "#00FFFF",
            "ge_banker": "#00FFFF",
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
            "chinning_rope_color": "#8B4513",
            "sand_crab_afk_marker": "#FFFFFF",
        },

        # ── Coordinates ───────────────────────────────────────────────────────
        # Absolute screen coordinates. Calibrate these with option 1 in the menu.
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

        # ── Timings ───────────────────────────────────────────────────────────
        "timings": {
            "short": [0.4, 0.7],
            "medium": [0.8, 1.3],
            "long": [2.5, 3.8],
            "teleport": [11.0, 13.0],
        },

        # ── Tolerances ────────────────────────────────────────────────────────
        "tolerances": {
            "color_match": 5,
            "click_offset": [0, 0],
        },

        # ── Mouse ─────────────────────────────────────────────────────────────
        "mouse": {
            "min_speed": 0.2,
            "max_speed": 0.6,
            "overshoot_chance": 0.15,
            "overshoot_distance": 20,
            "click_variance": 3,
            "post_click_delay_min": 0.05,
            "post_click_delay_max": 0.15,
        },

        # ── Walker ────────────────────────────────────────────────────────────
        "walker": {
            "minimap_center_x": 654,
            "minimap_center_y": 111,
            "tile_size": 4,
            "arrival_tolerance": 2,
            "max_click_distance": 15,
            "enable_anti_ban_variance": True,
            # Minimap localisation — set these to enable the walker.
            # map_image: filename inside images/maps/ (e.g. "sand_crabs.png")
            # map_origin_world_x/y: world tile coords of the map image's top-left (NW) corner.
            "minimap_localization": {
                "map_image": "",
                "map_origin_world_x": 0,
                "map_origin_world_y": 0,
            },
        },

        # ── Arduino ───────────────────────────────────────────────────────────
        "arduino": {
            "enabled": False,
            "serial_port": "COM3",
            "baud_rate": 115200,
            "fallback_to_software": True,
            "connection_timeout": 2.0,
        },

        # ── Templates ─────────────────────────────────────────────────────────
        # Paths are relative to the bundled images/ directory.
        # Replace images next to the exe if your client looks different.
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
                "all_settings": {
                    "path": "images/bot/ui_templates/all_settings.PNG",
                    "rows": 1,
                    "cols": 1,
                    "threshold": 0.65,
                },
                "audio": {
                    "path": "images/bot/ui_templates/audio.PNG",
                    "rows": 1,
                    "cols": 1,
                    "threshold": 0.65,
                },
                "activities": {
                    "path": "images/bot/ui_templates/activities.PNG",
                    "rows": 1,
                    "cols": 1,
                    "threshold": 0.65,
                },
            },
            "ui_buttons": {
                "inventory_tab": {
                    "path": "images/bot/ui_templates/inventory.png",
                    "threshold": 0.50,
                },
                "inventory_open": {
                    "path": "images/bot/ui_templates/inventory_open.PNG",
                    "threshold": 0.70,
                },
                "worn_equipment_open": {
                    "path": "images/bot/ui_templates/worn_equipment_open.PNG",
                    "threshold": 0.70,
                },
                "prayer_open": {
                    "path": "images/bot/ui_templates/prayer_open.PNG",
                    "threshold": 0.70,
                },
                "magic_open": {
                    "path": "images/bot/ui_templates/magic_open.PNG",
                    "threshold": 0.70,
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
                "settings_tab": {
                    "path": "images/bot/ui_templates/settings_tab.PNG",
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

        # ── License ───────────────────────────────────────────────────────────
        "license": {
            "api_url": "https://osrs-automation-framework-production.up.railway.app",
            "purchase_url": "https://yoursite.com/buy",
            "timeout": 10,
            "cache_file": ".license_cache",
            "offline_grace_period_hours": 24,
        },

        # ── Zulrah ────────────────────────────────────────────────────────────
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

        # ── Feature flags ─────────────────────────────────────────────────────
        "item_detection": {
            "enabled": False,
            "items_dir": "images/items",
            "threshold": 0.75,
            "load_at_startup": True,
        },
        "live_view": {
            "enabled": False,
            "fps": 10,
        },
    }
