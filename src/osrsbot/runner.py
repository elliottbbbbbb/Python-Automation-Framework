import logging
from typing import Any, Callable

from osrsbot.game_interface import GameInterface
from osrsbot.actions import Actions
from osrsbot.game_state import GameState
from osrsbot.config import Config
from osrsbot.game_state import HPDetector
logger = logging.getLogger(__name__)


class ScriptRunner:
    """Main script runner that sets up everything"""

    def __init__(self, window_title: str, config_file: str = "config.json") -> None:
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
            raise FileNotFoundError(f"Config file '{config_file}' not found") from e
        except Exception as e:
            logger.error(f"Failed to load config: {e}", exc_info=True)
            raise

        # Update window title if provided
        if window_title:
            self.config.data["window_title"] = window_title
            logger.debug(f"Updated window title in config to: '{window_title}'")

        try:
            # Initialize game interface
            logger.debug("Initializing GameInterface")
            self.interface = GameInterface(self.config)
            logger.info("GameInterface initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GameInterface: {e}", exc_info=True)
            raise Exception(f"Could not find or attach to window '{window_title}'") from e

        try:
            # Initialize game state
            logger.debug("Initializing GameState")
            self.state = GameState(self.interface, self.config)
            logger.info("GameState initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GameState: {e}", exc_info=True)
            raise

        try:
            # Initialize actions
            logger.debug("Initializing Actions")
            self.actions = Actions(self.interface, self.state, self.config)
            logger.info("Actions initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Actions: {e}", exc_info=True)
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
        script_name = script_func.__name__ if hasattr(script_func, '__name__') else 'unknown'
        logger.info(f"Starting script: {script_name}")
        logger.debug(f"Script arguments: {kwargs}")

        try:
            script_func(self.interface, self.state, self.actions, self.config, **kwargs)
            logger.info(f"Script '{script_name}' completed successfully")
        except KeyboardInterrupt:
            logger.warning(f"Script '{script_name}' interrupted by user")
            raise
        except Exception as e:
            logger.error(f"Script '{script_name}' failed with error: {e}", exc_info=True)
            raise Exception(f"Script '{script_name}' failed: {e}") from e
