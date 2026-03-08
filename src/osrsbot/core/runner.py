import logging
import os
import sys
from typing import TYPE_CHECKING, Any, Callable, Union
from pathlib import Path

from osrsbot.commands.game_actions import GameActions
from osrsbot.core.game_interface import GameInterface
from osrsbot.services.ui_manager_service import UIManager
from osrsbot.models.config import Config
from osrsbot.queries.game_queries import GameState
from osrsbot.services.anti_ban_service import AntiBanService
from osrsbot.services.loot_detection_service import LootDetectionService
from osrsbot.services.mouse_service import MouseConfig, MouseService
from osrsbot.services.screen_service import ScreenService
from osrsbot.services.keyboard_service import KeyboardService
from osrsbot.services.template_match_service import TemplateMatchService
from osrsbot.services.template_ocr_service import TemplateOCRService

if TYPE_CHECKING:
    from osrsbot.core.base_bot import Bot

logger = logging.getLogger(__name__)

# EXE CONFIG HELPER

def resolve_config_path(config_file: str) -> Path:
    # If user provided an absolute path, respect it
    path = Path(config_file)
    if path.is_absolute():
        return path

    # Running as PyInstaller exe
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / config_file

    return path

class ScriptRunner:
    """Main script runner that sets up everything"""

    def __init__(self, window_title: str, config_file: str = "config.json") -> None:
        """
        Args:
            window_title: Title of the game window to attach to
            config_file: Path to config JSON file

        Raises:
            ValueError: If window_title is empty
            FileNotFoundError: If config file doesn't exist
            Exception: If game window not found or initialization fails
        """

        if not window_title or not window_title.strip():
            logger.error("Window title cannot be empty")
            raise ValueError("Window title is required and cannot be empty")

        logger.info(f"Initializing ScriptRunner for window: '{window_title}'")



        try:
            config_path = Path(config_file)
            if config_path.is_absolute():
                # Explicit absolute path — use it directly
                self.config = Config(str(config_path))
            elif getattr(sys, "frozen", False):
                # Frozen exe: look for config.json next to the exe
                self.config = Config(str(Path(sys.executable).parent / config_file))
            else:
                # Dev mode: let Config resolve its own canonical path (src/osrsbot/config.json)
                self.config = Config()
            logger.info("Config loaded successfully")

        except FileNotFoundError:
            if getattr(sys, "frozen", False):
                # Last resort: bundled config baked into the exe
                bundled_config = Path(getattr(sys, "_MEIPASS", "")) / "osrsbot" / "config.json"
                logger.warning(f"Exe config not found, falling back to bundled: {bundled_config}")
                self.config = Config(str(bundled_config))
                logger.info("Config loaded from bundled fallback")
            else:
                raise

        except Exception as e:
            logger.error(f"Failed to load config: {e}", exc_info=True)
            raise

        print("\nStarting bot...")

        if window_title:
            self.config.data["window_title"] = window_title
            logger.debug(f"Updated window title in config to: '{window_title}'")

        print(f"  Finding game window '{window_title}'...")
        try:
            logger.debug("Initializing GameInterface")
            self.interface = GameInterface(self.config)
            logger.info("GameInterface initialized successfully")
            print("  Game window found.")
        except Exception as e:
            logger.error(f"Failed to initialize GameInterface: {e}", exc_info=True)
            raise Exception(
                f"Could not find or attach to window '{window_title}'"
            ) from e

        try:
            mouse_config_dict = self.config.get("mouse", default={})
            mouse_config = MouseConfig(
                min_speed=mouse_config_dict.get("min_speed", 0.2),
                max_speed=mouse_config_dict.get("max_speed", 0.6),
                overshoot_chance=mouse_config_dict.get("overshoot_chance", 0.15),
                overshoot_distance=mouse_config_dict.get("overshoot_distance", 20),
                click_variance=mouse_config_dict.get("click_variance", 3),
                post_click_delay=(
                    mouse_config_dict.get("post_click_delay_min", 0.05),
                    mouse_config_dict.get("post_click_delay_max", 0.15),
                ),
            )

            # Load .env file if present so local env config works when launching via scripts
            env_path = Path(self.config.config_file.parent, ".env") if hasattr(self, 'config') else Path(".env")
            if env_path.exists():
                try:
                    for raw in env_path.read_text(encoding='utf-8').splitlines():
                        line = raw.strip()
                        if not line or line.startswith('#'):
                            continue
                        if '=' not in line:
                            continue
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        # don't overwrite existing environment variables
                        os.environ.setdefault(k, v)
                except Exception:
                    logger.debug("Failed to load .env file for runner", exc_info=True)

            # Win32 SendInput is the default. Falls back to MouseService if unavailable.
            try:
                from osrsbot.services.win32_mouse_service import Win32MouseService

                logger.debug("Initializing Win32MouseService (SendInput)")
                self.mouse = Win32MouseService(mouse_config)  # type: ignore[arg-type]
                logger.info("Win32MouseService initialized successfully")
            except Exception as e:
                logger.warning(f"Win32MouseService not available: {e}. Falling back to MouseService.")
                logger.debug("Initializing MouseService (fallback)")
                self.mouse = MouseService(mouse_config)
                logger.info("MouseService initialized successfully (fallback)")

            logger.debug("Initializing ScreenService")
            self.screen = ScreenService(window_getter=self.interface.get_bounds)
            logger.info("ScreenService initialized successfully")

            print("  Loading UI templates...")
            logger.debug("Initializing TemplateMatchService")
            self.template_service = TemplateMatchService()

            try:
                self.template_service.register_from_config(self.config)
                logger.info("TemplateMatchService initialized and templates registered")
            except Exception as e:
                logger.warning(
                    f"TemplateMatchService initialized but template registration failed: {e}. "
                    "Template matching features will not be available."
                )
                self.template_service = None

            # Initialize UIManager
            logger.debug("Initializing UIManager")
            self.ui_manager = UIManager(self.template_service)
            if self.template_service:
                self.ui_manager.sync_from_template_service()
                logger.info(f"UIManager initialized with {len(self.ui_manager.grids)} grids and {len(self.ui_manager.buttons)} buttons")
            else:
                logger.info("UIManager initialized (no templates available)")

            # LiveViewService — enabled via LIVE_VIEW=true env var or config
            live_view_config = self.config.get("live_view", default={})
            live_view_enabled = (
                os.getenv("LIVE_VIEW", "").lower() in ("1", "true", "yes")
                or live_view_config.get("enabled", False)
            )
            if live_view_enabled:
                print("  Starting live view window...")
                try:
                    from osrsbot.services.live_view_service import LiveViewService

                    self.live_view = LiveViewService(
                        screen_service=self.screen,
                        fps=live_view_config.get("fps", 10),
                    )
                    self.ui_manager.register_live_overlay(self.live_view)
                    self.live_view.start()
                    logger.info("LiveViewService started")
                    print("  Live view started.")

                    # Register fixed OCR stat regions so they're always visible in the overlay.
                    # Colors are BGR. Coordinates are window-relative (same space as the capture).
                    _ocr = self.config.get("coordinates", "ocr", default={})
                    _stat_defs = [
                        ("hp_region",            "HP",     (80,  80,  255)),  # red
                        ("prayer_region",         "Prayer", (255, 140,  0)),   # blue
                        ("run_energy_region",     "Run",    (0,   220, 255)),  # yellow
                        ("special_attack_region", "Spec",   (180, 0,   255)),  # purple
                        ("world_coord_region",    "Coords", (200, 200, 200)),  # grey
                    ]
                    for key, label, color in _stat_defs:
                        r = _ocr.get(key)
                        if r:
                            self.ui_manager.register_static_region(
                                key,
                                r["x"], r["y"],
                                r.get("width", r.get("w", 30)),
                                r.get("height", r.get("h", 20)),
                                color=color,
                                label=label,
                            )
                except Exception as e:
                    logger.warning(f"LiveViewService failed to start: {e}")
                    print(f"  Live view unavailable: {e}")
                    self.live_view = None
            else:
                self.live_view = None

            logger.debug("Initializing TemplateOCRService")
            self.ocr = TemplateOCRService()
            logger.info("TemplateOCRService initialized successfully")

            logger.debug("Initializing KeyboardService")
            self.keyboard = KeyboardService()
            logger.info("KeyboardService initialized successfully")

            # Initialize ItemDetectionService if enabled
            logger.debug("Checking item detection configuration")
            item_detection_config = self.config.get("item_detection", default={})
            if item_detection_config.get("enabled", False):
                print("  Loading item templates...")
                try:
                    from osrsbot.services.item_detection_service import ItemDetectionService

                    logger.debug("Initializing ItemDetectionService")
                    items_dir = item_detection_config.get("items_dir", "images/items")
                    threshold = item_detection_config.get("threshold", 0.75)

                    self.item_detection = ItemDetectionService(items_dir, threshold)
                    logger.info(f"ItemDetectionService initialized with {len(self.item_detection.templates)} item templates loaded")
                except Exception as e:
                    logger.warning(f"ItemDetectionService initialization failed: {e}. Item detection disabled.")
                    self.item_detection = None
            else:
                logger.debug("Item detection disabled in config")
                self.item_detection = None


        except Exception as e:
            logger.error(f"Failed to initialize services: {e}", exc_info=True)
            raise

        try:
            logger.debug("Initializing GameState")
            self.state = GameState(
                self.interface,
                self.config,
                self.ocr,
                self.screen,
                self.template_service,
                self.item_detection,  # NEW: Pass ItemDetectionService
            )
            logger.info("GameState initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GameState: {e}", exc_info=True)
            raise

        try:
            logger.debug("Initializing AntiBanService")
            self.anti_ban = AntiBanService(self.config)
            logger.info("AntiBanService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AntiBanService: {e}", exc_info=True)
            raise

        try:
            logger.debug("Initializing LootDetectionService")
            self.loot_detection = LootDetectionService(self.screen)
            logger.info("LootDetectionService initialized successfully")
        except Exception as e:
            logger.error(
                f"Failed to initialize LootDetectionService: {e}", exc_info=True
            )
            raise

        try:
            logger.debug("Initializing utility helpers")
            from osrsbot.utils.coordinate_helpers import CoordinateResolver
            from osrsbot.utils.timing_helpers import TimingHelper

            self.coord_resolver = CoordinateResolver(
                self.screen, self.config, self.template_service
            )
            self.timing = TimingHelper(self.config, self.anti_ban)
            logger.info("Utility helpers initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize utility helpers: {e}", exc_info=True)
            raise

        try:
            logger.debug("Initializing GameActions (Commands)")
            self.actions = GameActions(
                self.mouse,  # type: ignore[arg-type]
                self.screen,
                self.interface,
                self.config,
                self.template_service,
                self.anti_ban,
                self.loot_detection,
                coord_resolver=self.coord_resolver,
                timing_helper=self.timing,
                ui_manager=self.ui_manager,
                inventory_state=self.state.inventory,
                keyboard_service=self.keyboard,
            )
            logger.info("GameActions initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GameActions: {e}", exc_info=True)
            raise

        print("  Ready!\n")
        logger.info("ScriptRunner initialization complete")

    def _execute_with_error_handling(
        self, script_name: str, executable: Callable[[], None]
    ) -> None:
        """
        Execute a script with standardized error handling and logging.

        Args:
            script_name: Name of the script for logging
            executable: Callable that executes the script logic

        Raises:
            KeyboardInterrupt: If user interrupts execution
            Exception: If script execution fails
        """
        try:
            executable()
            logger.info(f"Script '{script_name}' completed successfully")
        except KeyboardInterrupt:
            logger.warning(f"Script '{script_name}' interrupted by user")
            raise
        except Exception as e:
            logger.error(
                f"Script '{script_name}' failed with error: {e}", exc_info=True
            )
            raise Exception(f"Script '{script_name}' failed: {e}") from e
        finally:
            live_view = getattr(self, "live_view", None)
            if live_view is not None:
                live_view.stop()

    def run_script(self, script: Union[Callable, type, "Bot"], **kwargs: Any) -> None:
        """
        Run a script, supporting both function-based and class-based bots.

        Args:
            script: Either a function (legacy) or a Bot class/instance
            **kwargs: Additional arguments to pass to the script

        Raises:
            Exception: If script execution fails
        """
        from osrsbot.core.base_bot import Bot

        if isinstance(script, type) and issubclass(script, Bot):
            script_name = script.__name__
            logger.info(f"Starting bot class: {script_name}")
            logger.debug(f"Bot arguments: {kwargs}")

            def execute_bot_class():
                bot_instance = script(
                    interface=self.interface,
                    state=self.state,
                    actions=self.actions,
                    config=self.config,
                )
                bot_instance.run(**kwargs)

            self._execute_with_error_handling(script_name, execute_bot_class)

        elif isinstance(script, Bot):
            script_name = script.script_name
            logger.info(f"Starting bot instance: {script_name}")
            logger.debug(f"Bot arguments: {kwargs}")

            def execute_bot_instance():
                script.run(**kwargs)

            self._execute_with_error_handling(script_name, execute_bot_instance)

        elif callable(script):
            script_name = script.__name__ if hasattr(script, "__name__") else "unknown"
            logger.info(f"Starting script function: {script_name}")
            logger.debug(f"Script arguments: {kwargs}")

            def execute_function():
                script(self.interface, self.state, self.actions, self.config, **kwargs)

            self._execute_with_error_handling(script_name, execute_function)

        else:
            raise TypeError(
                f"script must be a Bot class, Bot instance, or callable function, "
                f"got {type(script)}"
            )
