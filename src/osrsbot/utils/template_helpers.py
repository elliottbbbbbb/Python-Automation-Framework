"""
Template detection helpers with config fallbacks.

Provides reusable patterns for template-first detection with graceful degradation.
"""

from typing import Optional, Callable, TypeVar, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from osrsbot.services.screen_service import ScreenService
    from osrsbot.services.template_match_service import TemplateMatchService

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TemplateHelper:
    """
    Encapsulates template detection patterns with fallback logic.
    """

    def __init__(
        self,
        screen: 'ScreenService',
        template_service: Optional['TemplateMatchService'] = None
    ):
        self.screen = screen
        self.template_service = template_service

    def detect_with_fallback(
        self,
        template_detection: Callable[[], Optional[T]],
        fallback: Callable[[], Optional[T]],
        strategy_name: str = "detection"
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
