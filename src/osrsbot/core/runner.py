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
            # First: try config next to the exe (or cwd when not frozen)
            primary_config = Path(config_file)

            if not primary_config.is_absolute():
                if getattr(sys, "frozen", False):
                    primary_config = Path(sys.executable).parent / config_file
                else:
                    primary_config = Path.cwd() / config_file

            logger.debug(f"Trying config from: {primary_config}")
            self.config = Config(primary_config)
            logger.info("Config loaded successfully from primary location")

        except FileNotFoundError:
            # Fallback: use bundled config inside .exe (or default behavior)
            logger.warning(
                f"Primary config not found ({primary_config}), falling back to bundled config"
            )
            try:
                if getattr(sys, "frozen", False):
                    # Try bundled config in .exe
                    bundled_config = Path(sys._MEIPASS) / "osrsbot" / "config.json"
                    logger.debug(f"Trying bundled config: {bundled_config}")
                    self.config = Config(str(bundled_config))
                else:
                    # In dev mode, use default Config behavior
                    logger.debug("Using default config location")
                    self.config = Config()
                logger.info("Config loaded successfully from fallback location")
            except Exception as e:
                logger.error(f"Failed to load config from both locations: {e}", exc_info=True)
                raise

        except Exception as e:
            logger.error(f"Failed to load config: {e}", exc_info=True)
            raise

        # Validate license before proceeding
        logger.info("Checking license...")
        print("Validating license...")
        self._validate_license()

        if window_title:
            self.config.data["window_title"] = window_title
            logger.debug(f"Updated window title in config to: '{window_title}'")

        try:
            logger.debug("Initializing GameInterface")
            self.interface = GameInterface(self.config)
            logger.info("GameInterface initialized successfully")
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
                self.mouse = Win32MouseService(mouse_config)
                logger.info("Win32MouseService initialized successfully")
            except Exception as e:
                logger.warning(f"Win32MouseService not available: {e}. Falling back to MouseService.")
                logger.debug("Initializing MouseService (fallback)")
                self.mouse = MouseService(mouse_config)
                logger.info("MouseService initialized successfully (fallback)")

            logger.debug("Initializing ScreenService")
            self.screen = ScreenService(window_getter=self.interface.get_bounds)
            logger.info("ScreenService initialized successfully")

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

            # Initialize Position Tracking Service (OCR-based)
            logger.debug("Initializing position tracking service")
            from osrsbot.services.coordinate_ocr_service import CoordinateOCRService

            ocr_service = CoordinateOCRService(
                screen=self.screen,
                ocr=self.ocr,
                config=self.config
            )

            if ocr_service.is_available():
                logger.info("Using CoordinateOCRService for position tracking")
                self.position_service = ocr_service
                position_service_available = True
            else:
                logger.warning("Position tracking unavailable. Walker disabled.")
                self.position_service = None
                position_service_available = False

            # Initialize Walker Service if we have position tracking
            if position_service_available and self.position_service:
                logger.debug("Initializing WalkerService")
                walker_config_dict = self.config.get("walker", default={})
                from osrsbot.services.walker_service import WalkerConfig, WalkerService

                walker_config = WalkerConfig(
                    minimap_center_x=walker_config_dict.get("minimap_center_x", 654),
                    minimap_center_y=walker_config_dict.get("minimap_center_y", 111),
                    tile_size=walker_config_dict.get("tile_size", 4),
                    arrival_tolerance=walker_config_dict.get("arrival_tolerance", 2),
                    max_click_distance=walker_config_dict.get("max_click_distance", 15),
                )
                self.walker = WalkerService(
                    config=walker_config,
                    status_socket=self.position_service,
                    mouse=self.mouse,
                    screen=self.screen,
                    interface=self.interface,
                )
                logger.info("✓ WalkerService initialized successfully")
            else:
                logger.info("✗ WalkerService disabled (no position tracking available)")
                self.walker = None

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
                self.mouse,
                self.screen,
                self.interface,
                self.config,
                self.template_service,
                self.anti_ban,
                self.loot_detection,
                coord_resolver=self.coord_resolver,
                timing_helper=self.timing,
                walker=self.walker,
                ui_manager=self.ui_manager,
                inventory_state=self.state.inventory,
                keyboard_service=self.keyboard,
            )
            logger.info("GameActions initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GameActions: {e}", exc_info=True)
            raise

        logger.info("ScriptRunner initialization complete")

    def _validate_license(self) -> None:
        """
        Validate license before allowing bot execution.

        This method checks if a valid license exists and is not expired.
        If no license is found, it displays a GUI dialog for activation.
        If license validation fails, the program exits immediately.

        Raises:
            SystemExit: If license validation fails or user cancels activation
        """
        from osrsbot.services.license_service import LicenseService
        from osrsbot.ui.license_dialog import LicenseDialog
        from osrsbot.exceptions.license_exceptions import (
            LicenseExpiredException,
            LicenseInvalidException,
        )

        # Get license configuration from config
        license_config = self.config.get("license", default={})
        api_url = os.getenv(
            "LICENSE_API_URL",
            license_config.get("api_url", "http://localhost:8000")
        )
        purchase_url = license_config.get("purchase_url", "https://yoursite.com/buy")
        cache_file = license_config.get("cache_file", ".license_cache")

        # Initialize license service
        license_service = LicenseService(api_url=api_url, cache_file=cache_file)

        try:
            # Try to validate existing license
            license_service.validate()

            # Get license status for user feedback
            status = license_service.get_license_status()
            if status["status"] == "active":
                hours = status.get("hours_remaining", 0)
                logger.info(f"✓ License validated successfully ({hours:.1f} hours remaining)")
            else:
                logger.info("✓ License validated successfully")

        except LicenseInvalidException as e:
            # No license found - show activation dialog
            logger.info("No active license found. Please activate a license key.")
            print("\n" + "="*60)
            print("  OSRS Bot - License Activation Required")
            print("="*60)
            print(f"  Error: {e}")
            print(f"  Purchase a license at: {purchase_url}")
            print("="*60 + "\n")

            def activate_callback(key: str) -> bool:
                """Callback for license activation from GUI dialog."""
                try:
                    result = license_service.activate(key)
                    logger.info(f"License activated: {result.get('message')}")
                    return True
                except Exception as activation_error:
                    logger.error(f"Activation failed: {activation_error}")
                    raise

            # Show GUI dialog for license activation
            dialog = LicenseDialog(
                on_activate=activate_callback,
                purchase_url=purchase_url
            )

            if not dialog.show():
                logger.error("License activation cancelled by user")
                print("\n❌ License activation required to use this bot.")
                print(f"   Visit: {purchase_url}")
                raise SystemExit(1)

            # After successful activation, validate once more
            try:
                license_service.validate()
                logger.info("✓ License activated and validated successfully")
            except Exception as final_validation_error:
                logger.error(f"Post-activation validation failed: {final_validation_error}")
                print("\n❌ License validation failed after activation.")
                print("   Please contact support if this persists.")
                raise SystemExit(1)

        except LicenseExpiredException as e:
            logger.error(f"License expired: {e}")
            print("\n" + "="*60)
            print("  OSRS Bot - License Expired")
            print("="*60)
            print(f"  {e}")
            print(f"  Purchase a new license at: {purchase_url}")
            print("="*60 + "\n")
            raise SystemExit(1)

        except Exception as e:
            logger.error(f"License validation failed: {e}")
            print("\n" + "="*60)
            print("  OSRS Bot - License Error")
            print("="*60)
            print(f"  Error: {e}")
            print(f"  Please check your internet connection or contact support.")
            print("="*60 + "\n")
            raise SystemExit(1)

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
