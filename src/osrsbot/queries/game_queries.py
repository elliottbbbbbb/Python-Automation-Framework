"""
Game State Facade - CQRS Query layer.

BACKWARD COMPATIBILITY FACADE:
This class maintains the original GameState API while delegating
to focused modules (CombatQueries, StatQueries, InventoryState).

All existing bot code continues to work unchanged.

New code should prefer using focused modules directly:
- CombatQueries for combat state
- StatQueries for HP/prayer/run
- InventoryState for inventory checks

Migration path:
1. Old code uses this facade (works unchanged)
2. New code uses focused modules
3. Eventually deprecate facade in favor of focused modules
"""

import logging
from typing import TYPE_CHECKING, Any, Optional

from osrsbot.models.config import Config

# Import new focused modules
from osrsbot.queries.bank_queries import BankQueries
from osrsbot.queries.combat_queries import CombatQueries
from osrsbot.queries.stat_queries import StatQueries
from osrsbot.services.template_ocr_service import TemplateOCRService

if TYPE_CHECKING:
    from osrsbot.services.screen_service import ScreenService

logger = logging.getLogger(__name__)


class GameState:
    """
    Game state facade (BACKWARD COMPATIBILITY).

    Delegates to focused query modules while maintaining original API.
    """

    def __init__(
        self,
        interface: Any,
        config: Config,
        ocr_service: TemplateOCRService,
        screen_service: Optional["ScreenService"] = None,
        template_service: Optional[Any] = None,
        item_detection_service: Optional[Any] = None,
    ) -> None:
        """Initialize game state queries."""
        self._interface = interface  # Keep for backward compatibility
        self.config = config
        self.ocr_service = ocr_service
        self.screen = screen_service
        self.template_service = template_service
        self.item_detection_service = item_detection_service  # NEW: Optional item detection

        # Initialize focused query modules
        if screen_service:
            self.combat_queries = CombatQueries(
                screen_service, config, template_service
            )
            self.stat_queries = StatQueries(screen_service, ocr_service, config)
            self.bank_queries = BankQueries(screen_service)
        else:
            self.combat_queries = None
            self.stat_queries = None
            self.bank_queries = None
            logger.warning(
                "ScreenService not available - combat, stat, and bank queries unavailable"
            )

        # Initialize inventory detection (with optional item detection)
        if template_service and screen_service:
            from osrsbot.queries.inventory_queries import InventoryState

            self.inventory = InventoryState(
                template_service, screen_service, config, item_detection_service
            )
            logger.debug("InventoryState initialized successfully")
        else:
            self.inventory = None
            logger.debug("InventoryState not initialized (missing services)")

    # ==================== Backward Compatibility Methods ====================
    # These delegate to new modules while maintaining exact same API

    # --- Combat Queries (delegate to CombatQueries) ---
    def in_combat(self) -> bool:
        """Check if player is in combat."""
        if self.combat_queries:
            return self.combat_queries.in_combat()

        # Fallback to false if module not available
        logger.warning("CombatQueries not available, using fallback")
        return False

    def click_success(self, tries: int = 3) -> bool:
        """Check if click was detected."""
        if self.combat_queries:
            return self.combat_queries.click_success(tries)

        logger.warning("CombatQueries not available")
        return False

    # --- Stat Queries (delegate to StatQueries) ---
    def get_all_stats(self, force: bool = False) -> dict[str, Optional[int]]:
        if self.stat_queries:
            return self.stat_queries.get_all_stats(force)

    def get_hp(self, force: bool = False) -> Optional[int]:
        """Get current HP."""
        if self.stat_queries:
            return self.stat_queries.get_hp(force)

        logger.error("StatQueries not available")
        return None

    def get_health(self, force: bool = False) -> Optional[int]:
        """Alias for get_hp() for backward compatibility."""
        return self.get_hp(force=force)

    def get_prayer(self, force: bool = False) -> Optional[int]:
        """Get current prayer points."""
        if self.stat_queries:
            return self.stat_queries.get_prayer(force)

        logger.error("StatQueries not available")
        return None

    def get_run_energy(self, force: bool = False) -> Optional[int]:
        """Get current run energy."""
        if self.stat_queries:
            return self.stat_queries.get_run_energy(force)

        logger.error("StatQueries not available")
        return None

    def get_special_attack_percentage(self, force: bool = False) -> Optional[int]:
        """Get current special attack percentage."""
        if self.stat_queries:
            return self.stat_queries.get_special_attack_percentage(force)

        logger.error("StatQueries not available")
        return None

    # --- Inventory Queries (delegate to InventoryState) ---
    def inventory_full(self, threshold: int = 27) -> bool:
        """
        Check if inventory has >= threshold items.

        Delegates to InventoryState for detection. Falls back to legacy
        implementation if InventoryState unavailable (backward compatibility).

        Args:
            threshold: Number of items to consider "full" (default 27 out of 28)

        Returns:
            True if inventory has >= threshold items, False otherwise
        """
        # Use new InventoryState system if available
        if self.inventory:
            try:
                result = self.inventory.is_full(threshold=threshold)
                logger.debug(f"inventory_full: InventoryState returned {result}")
                return result
            except Exception as e:
                logger.error(f"InventoryState check failed: {e}", exc_info=True)
                # Fall through to conservative default

        # Fallback: assume full (conservative)
        logger.warning(
            "InventoryState not available - assuming inventory is full (conservative)"
        )
        return True

    # --- Debug methods (keep unchanged) ---
    def debug_hp_ocr(self, num_samples: int = 20) -> None:
        """Debug HP OCR by taking multiple samples."""
        if not self.stat_queries:
            logger.error("StatQueries not available for debugging")
            return

        logger.info(f"\n{'=' * 50}")
        logger.info(f"HP OCR Debug - Taking {num_samples} samples")
        logger.info(f"{'=' * 50}")

        successful_reads = 0
        failed_reads = 0
        values = []

        for i in range(num_samples):
            hp = self.stat_queries.get_hp(force=True)
            if hp is not None:
                successful_reads += 1
                values.append(hp)
                logger.info(f"[{i + 1:2d}/{num_samples}] HP: {hp}")
            else:
                failed_reads += 1
                logger.warning(f"[{i + 1:2d}/{num_samples}] HP: FAILED")

        success_rate = (100 * successful_reads / num_samples) if num_samples > 0 else 0

        logger.info(f"\n{'=' * 50}")
        logger.info("Results:")
        logger.info(
            f"  Successful: {successful_reads}/{num_samples} ({success_rate:.1f}%)"
        )
        logger.info(f"  Failed:     {failed_reads}/{num_samples}")
        if values:
            logger.info(f"  Values:     {values}")
            logger.info(f"  Min:        {min(values)}")
            logger.info(f"  Max:        {max(values)}")
            logger.info(f"  Most common: {max(set(values), key=values.count)}")
        logger.info(f"{'=' * 50}\n")

    def debug_prayer_ocr(self, num_samples: int = 20) -> None:
        """Debug Prayer OCR by taking multiple samples."""
        if not self.stat_queries:
            logger.error("StatQueries not available for debugging")
            return

        logger.info(f"\n{'=' * 50}")
        logger.info(f"Prayer OCR Debug - Taking {num_samples} samples")
        logger.info(f"{'=' * 50}")

        successful_reads = 0
        failed_reads = 0
        values = []

        for i in range(num_samples):
            prayer = self.stat_queries.get_prayer(force=True)
            if prayer is not None:
                successful_reads += 1
                values.append(prayer)
                logger.info(f"[{i + 1:2d}/{num_samples}] Prayer: {prayer}")
            else:
                failed_reads += 1
                logger.warning(f"[{i + 1:2d}/{num_samples}] Prayer: FAILED")

        success_rate = (100 * successful_reads / num_samples) if num_samples > 0 else 0

        logger.info(f"\n{'=' * 50}")
        logger.info("Results:")
        logger.info(
            f"  Successful: {successful_reads}/{num_samples} ({success_rate:.1f}%)"
        )
        logger.info(f"  Failed:     {failed_reads}/{num_samples}")
        if values:
            logger.info(f"  Values:     {values}")
            logger.info(f"  Min:        {min(values)}")
            logger.info(f"  Max:        {max(values)}")
            logger.info(f"  Most common: {max(set(values), key=values.count)}")
        logger.info(f"{'=' * 50}\n")

    def debug_run_energy_ocr(self, num_samples: int = 20) -> None:
        """Debug Run Energy OCR by taking multiple samples."""
        if not self.stat_queries:
            logger.error("StatQueries not available for debugging")
            return

        logger.info(f"\n{'=' * 50}")
        logger.info(f"Run Energy OCR Debug - Taking {num_samples} samples")
        logger.info(f"{'=' * 50}")

        successful_reads = 0
        failed_reads = 0
        values = []

        for i in range(num_samples):
            energy = self.stat_queries.get_run_energy(force=True)
            if energy is not None:
                successful_reads += 1
                values.append(energy)
                logger.info(f"[{i + 1:2d}/{num_samples}] Run Energy: {energy}")
            else:
                failed_reads += 1
                logger.warning(f"[{i + 1:2d}/{num_samples}] Run Energy: FAILED")

        success_rate = (100 * successful_reads / num_samples) if num_samples > 0 else 0

        logger.info(f"\n{'=' * 50}")
        logger.info("Results:")
        logger.info(
            f"  Successful: {successful_reads}/{num_samples} ({success_rate:.1f}%)"
        )
        logger.info(f"  Failed:     {failed_reads}/{num_samples}")
        if values:
            logger.info(f"  Values:     {values}")
            logger.info(f"  Min:        {min(values)}")
            logger.info(f"  Max:        {max(values)}")
            logger.info(f"  Most common: {max(set(values), key=values.count)}")
        logger.info(f"{'=' * 50}\n")

    def debug_get_viewport_dimensions(self) -> Optional[tuple]:
        """
        Get viewport dimensions for diagnostic purposes.

        Returns width and height of game window viewport.
        Used by test code to calculate game viewport region.

        Returns:
            (width, height) tuple or None if screen service unavailable

        Example:
            >>> width, height = self.state.debug_get_viewport_dimensions()
            >>> viewport_region = (0, 0, int(width * 0.70), height)
        """
        if not self.screen:
            logger.error("ScreenService not available for viewport dimensions")
            return None

        try:
            dims = self.screen.get_viewport_dimensions()
            if dims:
                width, height = dims
                logger.debug(f"Viewport dimensions: {width}x{height}")
                return dims
            else:
                logger.error("Failed to get viewport dimensions from ScreenService")
                return None
        except Exception as e:
            logger.error(f"Failed to get viewport dimensions: {e}")
            return None

    def debug_capture_screen(self, grayscale: bool = True) -> Optional[Any]:
        """
        Capture current screen for diagnostic purposes.

        Bypasses caching and provides direct screen capture capability.
        Used by test code to verify template detection.

        Args:
            grayscale: If True, return grayscale numpy array; if False, return PIL Image

        Returns:
            Grayscale numpy array, PIL Image, or None if capture fails

        Example:
            >>> img_gray = self.state.debug_capture_screen()
            >>> if img_gray is not None:
            >>>     # Perform custom analysis
        """
        if not self.screen:
            logger.warning("ScreenService not available for debug capture")
            return None

        try:
            if grayscale:
                img = self.screen.capture_grayscale()
                logger.debug(
                    f"Debug screen capture: grayscale {
                        'success' if img is not None else 'failed'}"
                )
                return img
            else:
                img = self.screen.capture()
                logger.debug("Debug screen capture: color success")
                return img
        except Exception as e:
            logger.error(f"Debug screen capture failed: {e}")
            return None
