import logging
import os
from typing import Any, Callable, Union, TYPE_CHECKING

import pytesseract

from osrsbot.core.game_interface import GameInterface
from osrsbot.services.mouse_service import MouseService, MouseConfig
from osrsbot.services.screen_service import ScreenService
from osrsbot.services.ocr_service import OCRService
from osrsbot.services.template_match_service import TemplateMatchService
from osrsbot.models.state import GameState
from osrsbot.controllers.actions import GameActions
from osrsbot.models.config import Config

if TYPE_CHECKING:
    from osrsbot.core.base_bot import Bot

logger = logging.getLogger(__name__)


class ScriptRunner:
    """Main script runner that sets up everything"""

    def __init__(
            self,
            window_title: str,
            config_file: str = "config.json") -> None:
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
            raise FileNotFoundError(
                f"Config file '{config_file}' not found") from e
        except Exception as e:
            logger.error(f"Failed to load config: {e}", exc_info=True)
            raise

        if window_title:
            self.config.data["window_title"] = window_title
            logger.debug(
                f"Updated window title in config to: '{window_title}'")

        try:
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
            logger.debug("Initializing MouseService")
            mouse_config_dict = self.config.get("mouse", default={})
            mouse_config = MouseConfig(
                min_speed=mouse_config_dict.get("min_speed", 0.2),
                max_speed=mouse_config_dict.get("max_speed", 0.6),
                overshoot_chance=mouse_config_dict.get(
                    "overshoot_chance", 0.15),
                overshoot_distance=mouse_config_dict.get(
                    "overshoot_distance", 20),
                click_variance=mouse_config_dict.get("click_variance", 3),
                post_click_delay=(
                    mouse_config_dict.get("post_click_delay_min", 0.05),
                    mouse_config_dict.get("post_click_delay_max", 0.15)
                )
            )
            self.mouse = MouseService(mouse_config)
            logger.info("MouseService initialized successfully")

            # ScreenService uses GameInterface.get_bounds as single source of truth for window position
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

            tesseract_path = self.config.get("tesseract_path")
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                logger.info(f"Using Tesseract from config: {tesseract_path}")
            elif os.getenv("TESSERACT_PATH"):
                pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_PATH")
                logger.info(f"Using Tesseract from env: {os.getenv('TESSERACT_PATH')}")
            else:
                logger.info("Using default Tesseract path (system)")

            self.ocr = OCRService(window_getter=self.interface.get_window_position,
                                          tesseract_path=tesseract_path,
                                          debug=True)

            logger.info("OCR Service initialized successfully")


        except Exception as e:
            logger.error(f"Failed to initialize services: {e}", exc_info=True)
            raise
        

        try:
            logger.debug("Initializing GameState")
            self.state = GameState(self.interface, self.config, self.ocr, self.screen)
            logger.info("GameState initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GameState: {e}", exc_info=True)
            raise

        try:
            logger.debug("Initializing GameActions")
            self.actions = GameActions(
                self.mouse,
                self.screen,
                self.interface,
                self.config,
                self.state,
                self.template_service
            )
            logger.info("GameActions initialized successfully")
        except Exception as e:
            logger.error(
                f"Failed to initialize GameActions: {e}", exc_info=True)
            raise

        logger.info("ScriptRunner initialization complete")

    def run_script(
            self,
            script: Union[Callable, type, "Bot"],
            **kwargs: Any) -> None:
        """
        Run a script, supporting both function-based and class-based bots.

        Args:
            script: Either a function (legacy) or a Bot class/instance
            **kwargs: Additional arguments to pass to the script

        Raises:
            Exception: If script execution fails
        """
        from osrsbot.core.base_bot import Bot

        # Determine if it's a bot class/instance or a function
        if isinstance(script, type) and issubclass(script, Bot):
            # It's a Bot class - instantiate it
            script_name = script.__name__
            logger.info(f"Starting bot class: {script_name}")
            logger.debug(f"Bot arguments: {kwargs}")

            try:
                bot_instance = script(
                    interface=self.interface,
                    state=self.state,
                    actions=self.actions,
                    config=self.config
                )
                bot_instance.run(**kwargs)
                logger.info(f"Bot '{script_name}' completed successfully")
            except KeyboardInterrupt:
                logger.warning(f"Bot '{script_name}' interrupted by user")
                raise
            except Exception as e:
                logger.error(
                    f"Bot '{script_name}' failed with error: {e}",
                    exc_info=True)
                raise Exception(f"Bot '{script_name}' failed: {e}") from e

        elif isinstance(script, Bot):
            # It's already a Bot instance
            script_name = script.script_name
            logger.info(f"Starting bot instance: {script_name}")
            logger.debug(f"Bot arguments: {kwargs}")

            try:
                script.run(**kwargs)
                logger.info(f"Bot '{script_name}' completed successfully")
            except KeyboardInterrupt:
                logger.warning(f"Bot '{script_name}' interrupted by user")
                raise
            except Exception as e:
                logger.error(
                    f"Bot '{script_name}' failed with error: {e}",
                    exc_info=True)
                raise Exception(f"Bot '{script_name}' failed: {e}") from e

        elif callable(script):
            # It's a function (legacy support)
            script_name = script.__name__ if hasattr(
                script, '__name__') else 'unknown'
            logger.info(f"Starting script function: {script_name}")
            logger.debug(f"Script arguments: {kwargs}")

            try:
                script(
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

        else:
            raise TypeError(
                f"script must be a Bot class, Bot instance, or callable function, "
                f"got {type(script)}"
            )
