import logging
import os
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
from osrsbot.services.template_match_service import TemplateMatchService
from osrsbot.services.template_ocr_service import TemplateOCRService

if TYPE_CHECKING:
    from osrsbot.core.base_bot import Bot

logger = logging.getLogger(__name__)


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
            logger.debug(f"Loading config from: {config_file}")
            self.config = Config(config_file)
            logger.info("Config loaded successfully")
        except FileNotFoundError as e:
            logger.error(f"Config file not found: {config_file}")
            raise FileNotFoundError(f"Config file '{config_file}' not found") from e
        except Exception as e:
            logger.error(f"Failed to load config: {e}", exc_info=True)
            raise

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

            use_win32 = os.getenv("USE_WIN32", "").lower() in ("1", "true", "yes")
            use_interception = os.getenv("USE_INTERCEPTION", "").lower() in (
                "1",
                "true",
                "yes",
            )

            # Prefer Win32 if explicitly requested
            if use_win32:
                try:
                    from osrsbot.services.win32_mouse_service import Win32MouseService

                    logger.debug("Initializing Win32MouseService (SendInput)")
                    self.mouse = Win32MouseService(mouse_config)
                    logger.info("Win32MouseService initialized successfully")
                except Exception as e:
                    logger.warning(f"Win32MouseService not available: {e}. Falling back to other services.")
                    use_win32 = False

            # If Win32 was requested and initialized above, keep it.
            if not use_win32:
                if use_interception:
                    try:
                        from osrsbot.services.interception_mouse_service import (
                            InterceptionMouseService,
                        )

                        logger.debug("Initializing InterceptionMouseService (kernel-level)")
                        self.mouse = InterceptionMouseService(mouse_config)
                        logger.info("InterceptionMouseService initialized successfully")
                    except (ImportError, RuntimeError) as e:
                        logger.warning(
                            f"InterceptionMouseService not available: {e}. "
                            "Falling back to MouseService. "
                            "To use Interception: install driver and reboot system (see INTERCEPTION_SETUP.md)"
                        )
                        logger.debug("Initializing MouseService (fallback)")
                        self.mouse = MouseService(mouse_config)
                        logger.info("MouseService initialized successfully (fallback)")
                else:
                    logger.debug("Initializing MouseService")
                    self.mouse = MouseService(mouse_config)
                    logger.info("MouseService initialized successfully")

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

            # Initialize Position Tracking Service
            # Try Status Socket plugin first, fall back to OCR-based tracking
            logger.debug("Initializing position tracking service")
            status_socket_config = self.config.get("status_socket", default={})
            from osrsbot.services.status_socket_service import StatusSocketService
            from osrsbot.services.coordinate_ocr_service import CoordinateOCRService

            # Try RuneLite plugin first
            status_socket_plugin = StatusSocketService(
                data_file=status_socket_config.get("data_file", "live_data.json"),
                poll_interval=status_socket_config.get("poll_interval", 0.1),
            )

            if status_socket_plugin.is_available():
                logger.info("✓ Using StatusSocketService (RuneLite plugin detected)")
                self.status_socket = status_socket_plugin
                position_service_available = True
            else:
                logger.info("✗ RuneLite plugin not detected, trying OCR-based tracking")
                # Fall back to OCR-based coordinate reading
                ocr_service = CoordinateOCRService(
                    screen=self.screen,
                    ocr=self.ocr,
                    config=self.config
                )

                if ocr_service.is_available():
                    logger.info("✓ Using CoordinateOCRService (reading from screen)")
                    self.status_socket = ocr_service
                    position_service_available = True
                else:
                    logger.warning(
                        "✗ Position tracking unavailable (no plugin or OCR). "
                        "Walker disabled. See PATHFINDING_GUIDE.md"
                    )
                    self.status_socket = None
                    position_service_available = False

            # Initialize Walker Service if we have position tracking
            if position_service_available and self.status_socket:
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
                    status_socket=self.status_socket,
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
            )
            logger.info("GameActions initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GameActions: {e}", exc_info=True)
            raise

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
