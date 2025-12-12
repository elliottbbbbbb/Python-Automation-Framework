"""
Inventory Queries - CQRS read-only inventory state detection.

Provides inventory state queries using pixel-based empty slot detection:
- Check center pixel of each slot against empty slot color (#453c33)
- Pixel matches → slot is empty
- Pixel doesn't match → slot has item
- inventory_full() → checks if slot 28 has item

All queries are read-only and cached for performance.
"""

import logging
import time
from typing import Optional, List, Tuple, TYPE_CHECKING
from dataclasses import dataclass

import numpy as np

from osrsbot.models.config import Config
from osrsbot.utils.color_helpers import hex_to_rgb, colors_match

if TYPE_CHECKING:
    from osrsbot.services.template_match_service import TemplateMatchService
    from osrsbot.services.screen_service import ScreenService

logger = logging.getLogger(__name__)


@dataclass
class InventorySnapshot:
    """Snapshot of inventory state at a point in time."""

    filled_slots: List[int]  # Slot indices with items (0-27)
    empty_slots: List[int]   # Slot indices without items (0-27)
    total_items: int
    timestamp: float


class InventoryState:
    """
    CQRS Query for inventory state using pixel-based detection.

    Detects inventory fullness by checking center pixel of each slot
    against empty slot background color (#453c33).

    Features:
    - Simple and fast pixel checking
    - Caching with configurable TTL (default 1 second)
    - All 28 slots supported
    - is_full() checks slot 28 (last slot)
    """

    def __init__(
        self,
        template_service: 'TemplateMatchService',
        screen_service: 'ScreenService',
        config: Config
    ):
        """
        Initialize inventory state queries.

        Args:
            template_service: TemplateMatchService for grid detection
            screen_service: ScreenService for pixel sampling
            config: Configuration instance
        """
        self.template_service = template_service
        self.screen = screen_service
        self.config = config

        # Get empty slot color from config
        empty_color_hex = config.get("inventory.empty_slot_color", default="#453c33")
        self.empty_slot_color = hex_to_rgb(empty_color_hex)

        # Get detection TTL from config
        self.detection_ttl = config.get(
            "inventory.detection_ttl_seconds",
            default=1.0
        )

        # Color tolerance for matching
        self.color_tolerance = config.get(
            "inventory.color_tolerance",
            default=15
        )

        # Cache
        self._cache: Optional[InventorySnapshot] = None
        self._cache_time: float = 0.0

        logger.debug(
            f"InventoryState initialized: empty_color={empty_color_hex}, "
            f"tolerance={self.color_tolerance}, ttl={self.detection_ttl}s"
        )

    def is_full(self, threshold: int = 27) -> bool:
        """
        Check if inventory is full (has >= threshold items).

        Args:
            threshold: Number of items to consider "full" (default 27)

        Returns:
            True if inventory has >= threshold items

        Example:
            >>> if state.inventory.is_full(threshold=26):
            >>>     logger.info("Nearly full, should bank soon")
        """
        snapshot = self.get_snapshot()
        return snapshot.total_items >= threshold

    def count_filled_slots(self) -> int:
        """
        Count total items in inventory.

        Returns:
            Number of filled slots (0-28)
        """
        snapshot = self.get_snapshot()
        return snapshot.total_items

    def get_empty_slots(self) -> List[int]:
        """
        Get list of empty slot indices.

        Returns:
            List of empty slot indices (0-27)

        Example:
            >>> empty = state.inventory.get_empty_slots()
            >>> logger.info(f"{len(empty)} empty slots: {empty}")
        """
        snapshot = self.get_snapshot()
        return snapshot.empty_slots.copy()

    def get_filled_slots(self) -> List[int]:
        """
        Get list of filled slot indices.

        Returns:
            List of filled slot indices (0-27)
        """
        snapshot = self.get_snapshot()
        return snapshot.filled_slots.copy()

    def has_item_in_slot(self, slot_index: int) -> bool:
        """
        Check if specific slot contains an item.

        Args:
            slot_index: Slot index (0-27)

        Returns:
            True if slot has item, False if empty or invalid index
        """
        if not (0 <= slot_index <= 27):
            logger.warning(f"Invalid slot index: {slot_index} (must be 0-27)")
            return False

        snapshot = self.get_snapshot()
        return slot_index in snapshot.filled_slots

    def get_snapshot(self, force: bool = False) -> InventorySnapshot:
        """
        Get complete inventory state snapshot.

        Uses cached data if available and not expired.

        Args:
            force: Force fresh scan even if cache valid

        Returns:
            InventorySnapshot with current state
        """
        # Check cache validity
        if not force and self._cache is not None:
            age = time.time() - self._cache_time
            if age < self.detection_ttl:
                logger.debug(f"Using cached inventory state (age: {age:.2f}s)")
                return self._cache

        # Perform fresh scan
        snapshot = self._scan_inventory()
        self._cache = snapshot
        self._cache_time = time.time()

        logger.debug(
            f"Inventory scanned: {snapshot.total_items} items, "
            f"{len(snapshot.empty_slots)} empty slots"
        )

        return snapshot

    def _scan_inventory(self) -> InventorySnapshot:
        """
        Scan all 28 inventory slots and detect items.

        Returns:
            InventorySnapshot with detected state

        Implementation:
            1. Detect inventory grid using template matching
            2. For each of 28 slots, get center pixel color
            3. If pixel matches empty color → slot is empty
            4. If pixel doesn't match → slot has item
        """
        filled_slots: List[int] = []
        empty_slots: List[int] = []

        # Capture current screen
        img = self.screen.grab_screen()
        img_gray = self.screen.convert_to_gray(img)

        # Detect inventory grid
        inventory_grid = self.template_service.detect_grid("inventory", img_gray, force=True)

        if not inventory_grid or not inventory_grid.detected:
            logger.warning("Inventory grid not detected, returning empty state")
            # All slots empty if inventory not detected
            return InventorySnapshot(
                filled_slots=[],
                empty_slots=list(range(28)),
                total_items=0,
                timestamp=time.time()
            )

        # Check each of 28 slots
        for slot_index in range(28):
            if slot_index >= len(inventory_grid.elements):
                logger.warning(f"Slot {slot_index} not in grid, marking as empty")
                empty_slots.append(slot_index)
                continue

            # Get slot element
            slot_element = inventory_grid.elements[slot_index]

            # Get center pixel of slot
            center_x, center_y = slot_element.center

            # Sample pixel color at center (relative to game window)
            pixel_color = self._get_pixel_color(img, center_x, center_y)

            if pixel_color is None:
                logger.warning(f"Could not sample slot {slot_index}, marking as empty")
                empty_slots.append(slot_index)
                continue

            # Check if pixel matches empty slot color
            if colors_match(pixel_color, self.empty_slot_color, self.color_tolerance):
                # Pixel matches empty color → slot is empty
                empty_slots.append(slot_index)
                logger.debug(
                    f"Slot {slot_index}: EMPTY (color={pixel_color}, "
                    f"expected={self.empty_slot_color})"
                )
            else:
                # Pixel doesn't match → slot has item
                filled_slots.append(slot_index)
                logger.debug(
                    f"Slot {slot_index}: FILLED (color={pixel_color}, "
                    f"expected={self.empty_slot_color})"
                )

        return InventorySnapshot(
            filled_slots=filled_slots,
            empty_slots=empty_slots,
            total_items=len(filled_slots),
            timestamp=time.time()
        )

    def _get_pixel_color(
        self,
        img: np.ndarray,
        x: int,
        y: int
    ) -> Optional[Tuple[int, int, int]]:
        """
        Get pixel color at coordinates.

        Args:
            img: Screenshot image (BGR format from OpenCV)
            x: X coordinate (relative to game window)
            y: Y coordinate (relative to game window)

        Returns:
            RGB tuple or None if out of bounds
        """
        try:
            # OpenCV uses BGR format, we need RGB
            # Also note: numpy arrays are indexed [y, x] not [x, y]
            if 0 <= y < img.shape[0] and 0 <= x < img.shape[1]:
                bgr_pixel = img[y, x]
                # Convert BGR to RGB
                rgb_pixel = (int(bgr_pixel[2]), int(bgr_pixel[1]), int(bgr_pixel[0]))
                return rgb_pixel
            else:
                logger.warning(f"Pixel coordinates out of bounds: ({x}, {y})")
                return None
        except Exception as e:
            logger.error(f"Error sampling pixel at ({x}, {y}): {e}")
            return None

    def clear_cache(self):
        """Clear cached inventory state, forcing fresh scan on next query."""
        self._cache = None
        self._cache_time = 0.0
        logger.debug("Inventory cache cleared")
