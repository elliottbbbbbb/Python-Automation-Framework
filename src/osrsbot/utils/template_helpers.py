"""
Template detection helpers with config fallbacks.

Provides:
- resolve_template_path: Resolve image paths for dev and .exe environments
- TemplateHelper: Template-first detection with graceful degradation
"""

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional, TypeVar

if TYPE_CHECKING:
    from osrsbot.services.screen_service import ScreenService
    from osrsbot.services.template_match_service import TemplateMatchService

logger = logging.getLogger(__name__)


def resolve_template_path(template_path: str) -> Path:
    """
    Resolve template path for both development and .exe environments.

    Supports three path formats:
    1. Custom user images: 'custom:my_item.png' -> looks in user_images/ folder next to exe
    2. Short bundled paths: 'images/bot/items/my_item.png' -> auto-prefixed with 'src/osrsbot/'
    3. Full bundled paths: 'src/osrsbot/images/bot/items/my_item.png' -> used as-is

    When running as .exe:
    - 'custom:' paths resolve to './user_images/' folder (created if missing)
    - Bundled paths resolve to _MEIPASS directory

    Args:
        template_path: Original template path (relative or absolute)

    Returns:
        Resolved Path object
    """
    resolved_path = Path(template_path)

    # Skip resolution if already an absolute path
    if resolved_path.is_absolute():
        return resolved_path

    # Normalize path to use forward slashes for comparison (Windows uses backslashes)
    normalized_path = template_path.replace("\\", "/")

    # Handle 'custom:' prefix for user images
    if normalized_path.startswith("custom:"):
        custom_filename = normalized_path.replace("custom:", "", 1)

        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            user_images_dir = exe_dir / "user_images"
        else:
            project_root = Path(__file__).parent.parent.parent.parent
            user_images_dir = project_root / "user_images"

        user_images_dir.mkdir(exist_ok=True)
        resolved_path = user_images_dir / custom_filename
        logger.info(f"Resolved custom template: {template_path} -> {resolved_path}")
        return resolved_path

    # Auto-add 'src/osrsbot/' prefix if missing
    if not normalized_path.startswith("src/osrsbot/"):
        normalized_path = f"src/osrsbot/{normalized_path}"
        logger.debug(f"Auto-prefixed template path: {template_path} -> {normalized_path}")

    # When running as .exe, resolve from bundled location
    if getattr(sys, "frozen", False):
        relative_path = normalized_path.replace("src/osrsbot/", "", 1)
        resolved_path = Path(sys._MEIPASS) / "osrsbot" / relative_path
        logger.info(f"Resolved bundled template: {template_path} -> {resolved_path}")
    else:
        resolved_path = Path(normalized_path)

    return resolved_path

T = TypeVar("T")


class TemplateHelper:
    """
    Encapsulates template detection patterns with fallback logic.
    """

    def __init__(
        self,
        screen: "ScreenService",
        template_service: Optional["TemplateMatchService"] = None,
    ):
        self.screen = screen
        self.template_service = template_service

    def detect_with_fallback(
        self,
        template_detection: Callable[[], Optional[T]],
        fallback: Callable[[], Optional[T]],
        strategy_name: str = "detection",
    ) -> Optional[T]:
        """
        Try template detection first, fall back to alternative strategy.

        Args:
            template_detection: Function that attempts template detection
            fallback: Fallback function if template fails
            strategy_name: Name for logging

        Returns:
            Result from either strategy or None
        """
        # Try template detection
        if self.template_service:
            try:
                result = template_detection()
                if result is not None:
                    logger.debug(f"{strategy_name}: Template detection succeeded")
                    return result
            except Exception as e:
                logger.warning(f"{strategy_name}: Template detection failed: {e}")

        # Fallback strategy
        try:
            result = fallback()
            if result is not None:
                logger.debug(f"{strategy_name}: Fallback succeeded")
            else:
                logger.warning(f"{strategy_name}: Both strategies failed")
            return result
        except Exception as e:
            logger.error(f"{strategy_name}: Fallback also failed: {e}")
            return None
