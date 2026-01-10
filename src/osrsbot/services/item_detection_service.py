"""
ItemDetectionService - Template-based item identification for inventory slots.

Provides hybrid inventory detection:
- Fast pixel-variance for filled/empty detection (existing)
- Template matching for item identification (new)

Features:
- Load item templates from manual/ (priority) or auto/ (wiki scraped)
- Match items using OpenCV template matching
- Pre-load all templates at startup for performance
- Configurable confidence threshold

Usage:
    service = ItemDetectionService("src/osrsbot/images/items", threshold=0.75)
    item_name = service.identify_item_in_slot(slot_image)
    slots = service.find_item("shark", snapshot, screenshot, grid)
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2 as cv
import numpy as np

logger = logging.getLogger(__name__)


class ItemDetectionService:
    """
    Service for identifying items in inventory slots using template matching.

    Templates are loaded from:
    1. {items_dir}/manual/{item_name}.png (checked first - manual overrides)
    2. {items_dir}/auto/{item_id}_{item_name}.png (wiki scraped)

    All templates are:
    - Grayscale numpy arrays
    - Normalized to standard inventory icon size
    - Indexed by item_name (lowercase, underscores)
    - Cached in memory for fast lookup
    """

    def __init__(self, items_dir: str = "src/osrsbot/images/items", threshold: float = 0.75):
        """
        Initialize ItemDetectionService and load all item templates.

        Args:
            items_dir: Root directory containing manual/ and auto/ subdirectories
            threshold: Minimum confidence for template matching (0.0-1.0)
        """
        self.items_dir = Path(items_dir)
        self.threshold = threshold
        self.templates: Dict[str, np.ndarray] = {}  # item_name → grayscale template
        self.template_sizes: Dict[str, Tuple[int, int]] = {}  # item_name → (width, height)

        logger.info(f"ItemDetectionService initializing from {self.items_dir}")
        logger.info(f"Template matching threshold: {self.threshold:.2f}")

        self._load_templates()

        logger.info(f"ItemDetectionService initialized with {len(self.templates)} templates")

    def _load_templates(self) -> None:
        """
        Load all item templates from manual/ and auto/ directories.

        Priority:
        1. Manual overrides (manual/)
        2. Wiki scraped (auto/)

        Templates are converted to grayscale and stored as numpy arrays.
        """
        start_time = time.time()

        manual_dir = self.items_dir / "manual"
        auto_dir = self.items_dir / "auto"

        # Create directories if they don't exist
        manual_dir.mkdir(parents=True, exist_ok=True)
        auto_dir.mkdir(parents=True, exist_ok=True)

        # Load manual templates first (priority)
        if manual_dir.exists():
            manual_count = self._load_templates_from_dir(manual_dir, source="manual")
            logger.debug(f"Loaded {manual_count} manual templates")

        # Load auto templates (wiki scraped)
        if auto_dir.exists():
            auto_count = self._load_templates_from_dir(auto_dir, source="auto")
            logger.debug(f"Loaded {auto_count} auto templates")

        elapsed = (time.time() - start_time) * 1000
        logger.info(f"Template loading completed in {elapsed:.1f}ms")

    def _load_templates_from_dir(self, directory: Path, source: str) -> int:
        """
        Load all PNG templates from a directory.

        Args:
            directory: Directory to scan for PNG files
            source: Source identifier ("manual" or "auto")

        Returns:
            Number of templates loaded
        """
        count = 0

        for file_path in directory.glob("*.png"):
            try:
                # Parse filename
                filename = file_path.stem  # Without .png extension

                # Extract item name
                # Format: {item_id}_{item_name}.png or {item_name}.png
                if "_" in filename and filename.split("_")[0].isdigit():
                    # Format: 385_shark → "shark"
                    item_name = "_".join(filename.split("_")[1:])
                else:
                    # Format: shark → "shark"
                    item_name = filename

                # Normalize item name (lowercase, keep underscores)
                item_name = item_name.lower()

                # Skip if already loaded (manual overrides auto)
                if item_name in self.templates and source == "auto":
                    logger.debug(f"Skipping {file_path.name} (manual override exists)")
                    continue

                # Load image
                img = cv.imread(str(file_path), cv.IMREAD_GRAYSCALE)

                if img is None:
                    logger.warning(f"Failed to load template: {file_path}")
                    continue

                # Store template
                self.templates[item_name] = img
                self.template_sizes[item_name] = (img.shape[1], img.shape[0])  # (width, height)

                logger.debug(f"Loaded template '{item_name}' from {source}: {img.shape[1]}×{img.shape[0]}")
                count += 1

            except Exception as e:
                logger.warning(f"Error loading template {file_path}: {e}")
                continue

        return count

    def identify_item_in_slot(self, slot_image: np.ndarray) -> Optional[str]:
        """
        Identify which item is in a slot image using template matching.

        Args:
            slot_image: Cropped slot region (grayscale numpy array)

        Returns:
            Item name if identified above threshold, None otherwise
        """
        if slot_image is None or slot_image.size == 0:
            return None

        best_match_name = None
        best_match_confidence = 0.0

        # Try matching against all templates
        for item_name, template in self.templates.items():
            try:
                # Ensure slot image is large enough for template
                if slot_image.shape[0] < template.shape[0] or slot_image.shape[1] < template.shape[1]:
                    continue

                # Perform template matching
                result = cv.matchTemplate(slot_image, template, cv.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)

                # Track best match
                if max_val > best_match_confidence:
                    best_match_confidence = max_val
                    best_match_name = item_name

            except Exception as e:
                logger.debug(f"Template matching error for {item_name}: {e}")
                continue

        # Check if best match meets threshold
        if best_match_confidence >= self.threshold:
            logger.debug(f"Identified item: {best_match_name} (confidence: {best_match_confidence:.2f})")
            return best_match_name
        else:
            logger.debug(f"No item identified (best: {best_match_name} @ {best_match_confidence:.2f}, threshold: {self.threshold:.2f})")
            return None

    def find_item(
        self,
        item_name: str,
        filled_slots: List[int],
        screenshot: np.ndarray,
        slot_positions: List[Tuple[int, int, int, int]]
    ) -> List[int]:
        """
        Find all inventory slots containing the specified item.

        Args:
            item_name: Item name to search for (lowercase, underscores)
            filled_slots: List of slot indices that contain items (optimization)
            screenshot: Full screenshot (grayscale)
            slot_positions: List of (x0, y0, x1, y1) bounding boxes for each slot

        Returns:
            List of slot indices (0-27) containing the item
        """
        # Normalize item name
        item_name_normalized = item_name.lower().replace(" ", "_")

        # Check if template exists
        if item_name_normalized not in self.templates:
            logger.warning(f"No template found for item: {item_name}")
            return []

        template = self.templates[item_name_normalized]
        matching_slots = []

        # Only check filled slots (optimization)
        for slot_idx in filled_slots:
            if slot_idx < 0 or slot_idx >= len(slot_positions):
                continue

            # Get slot bounding box
            x0, y0, x1, y1 = slot_positions[slot_idx]

            # Crop slot region
            slot_image = screenshot[y0:y1, x0:x1]

            if slot_image.size == 0:
                continue

            # Ensure slot image is large enough for template
            if slot_image.shape[0] < template.shape[0] or slot_image.shape[1] < template.shape[1]:
                continue

            # Perform template matching
            try:
                result = cv.matchTemplate(slot_image, template, cv.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)

                if max_val >= self.threshold:
                    matching_slots.append(slot_idx)
                    logger.debug(f"Found {item_name} in slot {slot_idx} (confidence: {max_val:.2f})")

            except Exception as e:
                logger.debug(f"Error matching slot {slot_idx}: {e}")
                continue

        return matching_slots

    def has_item(
        self,
        item_name: str,
        filled_slots: List[int],
        screenshot: np.ndarray,
        slot_positions: List[Tuple[int, int, int, int]]
    ) -> bool:
        """
        Quick check if item exists in inventory (early exit optimization).

        Args:
            item_name: Item name to search for
            filled_slots: List of filled slot indices
            screenshot: Full screenshot (grayscale)
            slot_positions: List of slot bounding boxes

        Returns:
            True if item found, False otherwise
        """
        # Normalize item name
        item_name_normalized = item_name.lower().replace(" ", "_")

        # Check if template exists
        if item_name_normalized not in self.templates:
            logger.warning(f"No template found for item: {item_name}")
            return False

        template = self.templates[item_name_normalized]

        # Check filled slots, exit early if found
        for slot_idx in filled_slots:
            if slot_idx < 0 or slot_idx >= len(slot_positions):
                continue

            # Get slot bounding box
            x0, y0, x1, y1 = slot_positions[slot_idx]

            # Crop slot region
            slot_image = screenshot[y0:y1, x0:x1]

            if slot_image.size == 0:
                continue

            # Ensure slot image is large enough
            if slot_image.shape[0] < template.shape[0] or slot_image.shape[1] < template.shape[1]:
                continue

            # Perform template matching
            try:
                result = cv.matchTemplate(slot_image, template, cv.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)

                if max_val >= self.threshold:
                    logger.debug(f"Found {item_name} in slot {slot_idx} (confidence: {max_val:.2f})")
                    return True  # Early exit

            except Exception as e:
                logger.debug(f"Error matching slot {slot_idx}: {e}")
                continue

        return False

    def get_loaded_items(self) -> List[str]:
        """
        Get list of all loaded item names.

        Returns:
            List of item names (lowercase, underscores)
        """
        return list(self.templates.keys())

    def get_template_count(self) -> int:
        """Get number of loaded templates."""
        return len(self.templates)
