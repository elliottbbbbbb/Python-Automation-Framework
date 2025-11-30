import logging
from typing import Any, Callable

from osrsbot.core.game_interface import GameInterface
from osrsbot.services.mouse_service import MouseService, MouseConfig
from osrsbot.services.screen_service import ScreenService
from osrsbot.models.state import GameState
from osrsbot.controllers.actions import GameActions
from osrsbot.models.config import Config

logger = logging.getLogger(__name__)


class ScriptRunner:
    """Main script runner that sets up everything"""

    def __init__(
            self,
            window_title: str,
            config_file: str = "config.json") -> None:
        """Initialize the script runner with all dependencies.

        Args:
            window_title: Title of the game window to attach to
            config_file: Path to config JSON file

        Raises:
            ValueError: If window_title is empty
            FileNotFoundError: If config file doesn't exist
            Exception: If game window not found or initialization fails
        """
        # Validate window title
        if not window_title or not window_title.strip():
            logger.error("Window title cannot be empty")
            raise ValueError("Window title is required and cannot be empty")

        logger.info(f"Initializing ScriptRunner for window: '{window_title}'")

        try:
            # Load configuration
            logger.debug(f"Loading config from: {config_file}")
            self.config = Config(config_file)
            logger.info("Config loaded successfully")
        except FileNotFoundError as e:
            logger.error(f"Config file not found: {config_file}")
            raise FileNotFoundError(
                f"Config file '{config_file}' not found") from e
        except Exception as e:
            logger.error(f"Failed to load config: {e}", exc_info=True)
            raise

        # Update window title if provided
        if window_title:
            self.config.data["window_title"] = window_title
            logger.debug(
                f"Updated window title in config to: '{window_title}'")

        try:
            # Initialize game interface (window management only)
            logger.debug("Initializing GameInterface")
            self.interface = GameInterface(self.config)
            logger.info("GameInterface initialized successfully")
        except Exception as e:
            logger.error(
                f"Failed to initialize GameInterface: {e}",
                exc_info=True)
            raise Exception(
                f"Could not find or attach to window '{window_title}'") from e

        try:
            # Get window bounds for services
            bounds = self.interface.get_bounds()
            logger.debug(f"Window bounds: {bounds}")

            # Initialize MouseService
            logger.debug("Initializing MouseService")
            mouse_config_dict = self.config.get("mouse", default={})
            mouse_config = MouseConfig(
                min_speed=mouse_config_dict.get("min_speed", 0.2),
                max_speed=mouse_config_dict.get("max_speed", 0.6),
                overshoot_chance=mouse_config_dict.get("overshoot_chance", 0.15),
                overshoot_distance=mouse_config_dict.get("overshoot_distance", 20),
                click_variance=mouse_config_dict.get("click_variance", 3),
                post_click_delay=(
                    mouse_config_dict.get("post_click_delay_min", 0.05),
                    mouse_config_dict.get("post_click_delay_max", 0.15)
                )
            )
            self.mouse = MouseService(mouse_config)
            logger.info("MouseService initialized successfully")

            # Initialize ScreenService
            logger.debug("Initializing ScreenService")
            self.screen = ScreenService(window_bounds=bounds)
            logger.info("ScreenService initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize services: {e}", exc_info=True)
            raise

        try:
            # Initialize game state
            logger.debug("Initializing GameState")
            self.state = GameState(self.interface, self.config, self.screen)
            logger.info("GameState initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GameState: {e}", exc_info=True)
            raise

        try:
            # Initialize actions (Commands - change game state)
            logger.debug("Initializing GameActions")
            self.actions = GameActions(
                self.mouse,
                self.screen,
                self.config
            )
            logger.info("GameActions initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GameActions: {e}", exc_info=True)
            raise

        logger.info("ScriptRunner initialization complete")

    def run_script(self, script_func: Callable, **kwargs: Any) -> None:
        """Run a script function with all dependencies.

        Args:
            script_func: The script function to execute
            **kwargs: Additional arguments to pass to the script

        Raises:
            Exception: If script execution fails
        """
        script_name = script_func.__name__ if hasattr(
            script_func, '__name__') else 'unknown'
        logger.info(f"Starting script: {script_name}")
        logger.debug(f"Script arguments: {kwargs}")

        try:
            script_func(
                self.interface,
                self.state,
                self.actions,
                self.config,
                **kwargs)
            logger.info(f"Script '{script_name}' completed successfully")
        except KeyboardInterrupt:
            logger.warning(f"Script '{script_name}' interrupted by user")
            raise
        except Exception as e:
            logger.error(
                f"Script '{script_name}' failed with error: {e}",
                exc_info=True)
            raise Exception(f"Script '{script_name}' failed: {e}") from e
