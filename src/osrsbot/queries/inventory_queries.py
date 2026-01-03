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
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

from osrsbot.constants import INVENTORY
from osrsbot.models.config import Config
from osrsbot.utils.color_helpers import colors_match, hex_to_rgb

if TYPE_CHECKING:
    from osrsbot.services.screen_service import ScreenService
    from osrsbot.services.template_match_service import TemplateMatchService

logger = logging.getLogger(__name__)


@dataclass
class InventorySnapshot:
    """Snapshot of inventory state at a point in time."""

    filled_slots: List[int]  # Slot indices with items (0-27)
    empty_slots: List[int]  # Slot indices without items (0-27)
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
        template_service: "TemplateMatchService",
        screen_service: "ScreenService",
        config: Config,
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
        self.detection_ttl = config.get("inventory.detection_ttl_seconds", default=1.0)

        # Color tolerance for matching
        self.color_tolerance = config.get("inventory.color_tolerance", default=15)

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
        if not (0 <= slot_index < INVENTORY.total_slots):
            logger.warning(
                f"Invalid slot index: {slot_index} (must be 0-{INVENTORY.total_slots - 1})"
            )
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

        # Capture ONE screenshot and use it for both grid detection and pixel sampling
        img_color = self.screen.capture()

        if img_color is None:
            logger.warning("Failed to capture screenshot, returning empty state")
            return InventorySnapshot(
                filled_slots=[],
                empty_slots=list(range(INVENTORY.total_slots)),
                total_items=0,
                timestamp=time.time(),
            )

        # Convert color PIL image to numpy array for pixel access
        import numpy as np
        import cv2

        img_array = np.array(img_color)

        # Convert the SAME image to grayscale for template matching
        img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        # Detect inventory grid using template matching on the SAME screenshot
        detected = self.template_service.detect_grid("inventory", img_gray, force=True)

        if not detected:
            logger.warning("Inventory grid not detected, returning empty state")
            # All slots empty if inventory not detected
            return InventorySnapshot(
                filled_slots=[],
                empty_slots=list(range(INVENTORY.total_slots)),
                total_items=0,
                timestamp=time.time(),
            )

        # Get the grid
        grid = self.template_service.get_grid("inventory")
        if not grid or not grid.visible:
            logger.warning("Inventory grid not visible, returning empty state")
            return InventorySnapshot(
                filled_slots=[],
                empty_slots=list(range(INVENTORY.total_slots)),
                total_items=0,
                timestamp=time.time(),
            )

        # Check each of 28 slots
        for slot_index in range(INVENTORY.total_slots):
            # Get slot element
            slot_element = grid.get_element(slot_index)
            if not slot_element:
                logger.warning(f"Slot {slot_index} not in grid, marking as empty")
                empty_slots.append(slot_index)
                continue

            # Multi-point sampling: check 5 pixels (center + 4 around it)
            center_x, center_y = slot_element.center

            try:
                # Sample 9 points in a 3x3 grid around center
                sample_points = [
                    (center_x - 4, center_y - 4), (center_x, center_y - 4), (center_x + 4, center_y - 4),
                    (center_x - 4, center_y),     (center_x, center_y),     (center_x + 4, center_y),
                    (center_x - 4, center_y + 4), (center_x, center_y + 4), (center_x + 4, center_y + 4),
                ]

                # Collect all pixel colors
                sampled_colors = []
                for px, py in sample_points:
                    try:
                        pixel_color_sample = tuple(int(c) for c in img_array[py, px])
                        sampled_colors.append(pixel_color_sample)
                    except:
                        pass  # Out of bounds, skip this point

                # Calculate variance of the sampled pixels
                # Empty slots have low variance (uniform brown color)
                # Items have high variance (different colors across the icon)
                if len(sampled_colors) >= 5:
                    # Calculate std dev across all RGB channels
                    import statistics
                    all_values = [c for color in sampled_colors for c in color]
                    variance = statistics.stdev(all_values) if len(all_values) > 1 else 0

                    # If variance is low, it's likely empty (uniform color)
                    # If variance is high, it's likely an item (varied colors)
                    variance_threshold = 10.0
                    is_empty = variance < variance_threshold
                    matches_count = int(variance)  # For logging
                    total_samples = len(sampled_colors)
                else:
                    is_empty = True  # Default to empty if can't sample enough points
                    matches_count = 0
                    total_samples = len(sampled_colors)

                # Get center pixel for logging
                pixel_color = tuple(int(c) for c in img_array[center_y, center_x])

            except Exception as e:
                logger.warning(f"Could not sample slot {slot_index}: {e}")
                empty_slots.append(slot_index)
                continue

            # Calculate per-channel diffs for debugging
            r_diff = abs(pixel_color[0] - self.empty_slot_color[0])
            g_diff = abs(pixel_color[1] - self.empty_slot_color[1])
            b_diff = abs(pixel_color[2] - self.empty_slot_color[2])

            logger.info(
                f"Slot {slot_index:2d} @ ({center_x},{center_y}): RGB={pixel_color} vs {self.empty_slot_color}, "
                f"diffs=[{r_diff},{g_diff},{b_diff}], variance={matches_count}, samples={total_samples} → {'EMPTY' if is_empty else 'FILLED'}"
            )

            if is_empty:
                empty_slots.append(slot_index)
            else:
                filled_slots.append(slot_index)

        snapshot = InventorySnapshot(
            filled_slots=filled_slots,
            empty_slots=empty_slots,
            total_items=len(filled_slots),
            timestamp=time.time(),
        )

        logger.info("=" * 80)
        logger.info(
            f"INVENTORY SCAN COMPLETE: {snapshot.total_items} items detected, "
            f"{len(snapshot.empty_slots)} empty slots"
        )
        logger.info(f"Filled slots: {sorted(snapshot.filled_slots)}")
        logger.info(f"Empty slots: {sorted(snapshot.empty_slots)}")
        logger.info("=" * 80)

        return snapshot

    def clear_cache(self):
        """Clear cached inventory state, forcing fresh scan on next query."""
        self._cache = None
        self._cache_time = 0.0
        logger.debug("Inventory cache cleared")
