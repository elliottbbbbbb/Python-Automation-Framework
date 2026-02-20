"""
Bank Queries - CQRS Query layer for bank-related state detection.

Handles:
- Bank interface state detection
- Template matching for bank items and NPCs
- Multi-template matching for better accuracy

Query layer responsibilities:
- READ-ONLY operations
- Detect game state
- Find elements on screen
- No mutations or actions
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import cv2 as cv
import numpy as np

from osrsbot.services.screen_service import ScreenService
from osrsbot.utils.template_helpers import resolve_template_path

logger = logging.getLogger(__name__)


class BankQueries:
    """Query layer for bank-related state detection and template matching."""

    def __init__(self, screen: ScreenService):
        """
        Initialize bank queries.

        Args:
            screen: Screen capture service
        """
        self.screen = screen

    def is_bank_open(self, search_button_template: str, threshold: float = 0.7) -> bool:
        """
        Check if bank interface is open by detecting the search button.

        Args:
            search_button_template: Path to bank search button template image
            threshold: Match confidence threshold (0.0-1.0)

        Returns:
            True if bank is open (search button visible), False otherwise
        """
        try:
            # Load search button template
            resolved_path = resolve_template_path(search_button_template)
            template = cv.imread(str(resolved_path), cv.IMREAD_COLOR)
            if template is None:
                logger.warning(
                    f"Failed to load bank search template: {search_button_template}"
                )
                return False

            # Capture current screen
            screenshot = self.screen.capture()
            if screenshot is None:
                logger.warning("Failed to capture screenshot for bank detection")
                return False

            # Convert PIL to numpy array (BGR for OpenCV)
            img_np = cv.cvtColor(np.array(screenshot), cv.COLOR_RGB2BGR)

            # Perform template matching
            result = cv.matchTemplate(img_np, template, cv.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv.minMaxLoc(result)

            # Bank is open if search button is visible
            is_open = max_val >= threshold
            logger.debug(
                f"Bank open check: {'YES' if is_open else 'NO'} "
                f"(search button confidence: {max_val:.3f})"
            )
            return is_open

        except Exception as e:
            logger.error(f"Error checking if bank is open: {e}")
            return False

    def find_template(
        self,
        template_path: str,
        threshold: float = 0.7,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[Tuple[int, int, float]]:
        """
        Find a template on screen.

        Args:
            template_path: Path to template image
            threshold: Match confidence threshold (0.0-1.0)
            region: Optional (x, y, width, height) to restrict search area

        Returns:
            Tuple of (center_x, center_y, confidence) if found, None otherwise
        """
        try:
            # Resolve template path for .exe
            resolved_path = resolve_template_path(template_path)

            # Load template
            template = cv.imread(str(resolved_path), cv.IMREAD_COLOR)
            if template is None:
                logger.error(f"Failed to load template: {template_path}")
                return None

            # Capture current screen
            screenshot = self.screen.capture()
            if screenshot is None:
                logger.error("Failed to capture screenshot")
                return None

            # Convert PIL to numpy array (BGR for OpenCV)
            img_np = cv.cvtColor(np.array(screenshot), cv.COLOR_RGB2BGR)

            # Apply region if specified (extract ROI before template matching)
            offset_x, offset_y = 0, 0
            if region:
                rx, ry, rw, rh = region
                # Ensure region is within image bounds
                img_h, img_w = img_np.shape[:2]
                rx = max(0, min(rx, img_w))
                ry = max(0, min(ry, img_h))
                rw = min(rw, img_w - rx)
                rh = min(rh, img_h - ry)
                img_np = img_np[ry:ry+rh, rx:rx+rw]
                offset_x, offset_y = rx, ry

            # Perform template matching
            result = cv.matchTemplate(img_np, template, cv.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv.minMaxLoc(result)

            # Always log the best confidence found for debugging
            template_name = Path(template_path).name
            logger.info(
                f"Template match '{template_name}': "
                f"best_confidence={max_val:.3f}, threshold={threshold}, "
                f"region={region}"
            )

            if max_val >= threshold:
                # Calculate center of matched region
                x, y = max_loc
                h, w = template.shape[:2]
                # Add offset back to get screen coordinates
                center_x = offset_x + x + w // 2
                center_y = offset_y + y + h // 2

                logger.debug(
                    f"Found template at ({center_x}, {center_y}) "
                    f"with confidence {max_val:.3f}"
                )
                return (center_x, center_y, max_val)
            else:
                logger.debug(f"Template not found (confidence: {max_val:.3f} < {threshold})")
                return None

        except Exception as e:
            logger.error(f"Error finding template: {e}")
            return None

    def find_multi_template(
        self,
        template_paths: List[str],
        threshold: float = 0.7,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[Tuple[int, int, float, str]]:
        """
        Find best matching template from multiple options.

        Useful for items that appear differently at different zoom levels, angles, etc.

        Args:
            template_paths: List of paths to template images
            threshold: Match confidence threshold (0.0-1.0)
            region: Optional (x, y, width, height) to restrict search area

        Returns:
            Tuple of (center_x, center_y, confidence, template_name) if found, None otherwise
        """
        best_match = None
        best_confidence = 0.0
        best_template_name = None
        best_center = None

        # Try all templates
        for template_path in template_paths:
            try:
                # Resolve and load template
                resolved_path = resolve_template_path(template_path)
                template = cv.imread(str(resolved_path), cv.IMREAD_COLOR)
                if template is None:
                    logger.warning(f"Failed to load template: {template_path}")
                    continue

                # Capture current screen
                screenshot = self.screen.capture()
                if screenshot is None:
                    continue

                # Convert PIL to numpy array (BGR for OpenCV)
                img_np = cv.cvtColor(np.array(screenshot), cv.COLOR_RGB2BGR)

                # Apply region if specified (extract ROI before template matching)
                offset_x, offset_y = 0, 0
                if region:
                    rx, ry, rw, rh = region
                    # Ensure region is within image bounds
                    img_h, img_w = img_np.shape[:2]
                    rx = max(0, min(rx, img_w))
                    ry = max(0, min(ry, img_h))
                    rw = min(rw, img_w - rx)
                    rh = min(rh, img_h - ry)
                    img_np = img_np[ry:ry+rh, rx:rx+rw]
                    offset_x, offset_y = rx, ry

                # Perform template matching
                result = cv.matchTemplate(img_np, template, cv.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv.minMaxLoc(result)

                # Keep track of best match
                if max_val > best_confidence:
                    best_confidence = max_val
                    best_match = max_loc
                    best_template_name = Path(template_path).name

                    # Calculate center (add offset to get screen coordinates)
                    x, y = max_loc
                    h, w = template.shape[:2]
                    center_x = offset_x + x + w // 2
                    center_y = offset_y + y + h // 2
                    best_center = (center_x, center_y)

            except Exception as e:
                logger.warning(f"Error checking template {template_path}: {e}")
                continue

        # Log summary at INFO level (matches find_template's logging pattern)
        logger.info(
            f"Multi-template match: best='{best_template_name}' "
            f"best_confidence={best_confidence:.3f}, threshold={threshold}, "
            f"region={region}, templates_tried={len(template_paths)}"
        )

        # Check if we found a match above threshold
        if best_match is not None and best_confidence >= threshold:
            return (*best_center, best_confidence, best_template_name)
        else:
            return None

    def find_all_multi_template(
        self,
        template_paths: List[str],
        threshold: float = 0.7,
        region: Optional[Tuple[int, int, int, int]] = None,
        cross_template_dedup_radius: int = 30,
    ) -> List[Tuple[int, int, float, str]]:
        """
        Find ALL matching locations from multiple templates above threshold.

        Uses iterative non-maximum suppression to extract multiple matches per
        template, then deduplicates across templates.

        Args:
            template_paths: List of paths to template images
            threshold: Match confidence threshold (0.0-1.0)
            region: Optional (x, y, width, height) to restrict search area
            cross_template_dedup_radius: Pixel radius to dedup matches across templates

        Returns:
            List of (center_x, center_y, confidence, template_name), sorted by
            confidence descending. Empty list if none found.
        """
        MAX_MATCHES_PER_TEMPLATE = 20

        # Capture screen once for all templates
        screenshot = self.screen.capture()
        if screenshot is None:
            return []
        img_np = cv.cvtColor(np.array(screenshot), cv.COLOR_RGB2BGR)

        # Apply region crop
        offset_x, offset_y = 0, 0
        if region:
            rx, ry, rw, rh = region
            img_h, img_w = img_np.shape[:2]
            rx = max(0, min(rx, img_w))
            ry = max(0, min(ry, img_h))
            rw = min(rw, img_w - rx)
            rh = min(rh, img_h - ry)
            img_np = img_np[ry:ry + rh, rx:rx + rw]
            offset_x, offset_y = rx, ry

        all_matches = []

        for template_path in template_paths:
            try:
                resolved_path = resolve_template_path(template_path)
                template = cv.imread(str(resolved_path), cv.IMREAD_COLOR)
                if template is None:
                    logger.warning(f"Failed to load template: {template_path}")
                    continue

                th, tw = template.shape[:2]
                result = cv.matchTemplate(img_np, template, cv.TM_CCOEFF_NORMED)
                template_name = Path(template_path).name

                # Iterative NMS: find max, zero out region, repeat
                result_copy = result.copy()
                for _ in range(MAX_MATCHES_PER_TEMPLATE):
                    _, max_val, _, max_loc = cv.minMaxLoc(result_copy)
                    if max_val < threshold:
                        break

                    mx, my = max_loc
                    center_x = offset_x + mx + tw // 2
                    center_y = offset_y + my + th // 2
                    all_matches.append((center_x, center_y, max_val, template_name))

                    # Zero out region around this match to suppress re-detection
                    y_start = max(0, my - th // 2)
                    y_end = min(result_copy.shape[0], my + th // 2 + 1)
                    x_start = max(0, mx - tw // 2)
                    x_end = min(result_copy.shape[1], mx + tw // 2 + 1)
                    result_copy[y_start:y_end, x_start:x_end] = 0.0

            except Exception as e:
                logger.warning(f"Error checking template {template_path}: {e}")
                continue

        # Cross-template dedup: keep higher confidence when two templates
        # match the same physical object
        all_matches.sort(key=lambda m: m[2], reverse=True)
        deduped = []
        for match in all_matches:
            mx, my = match[0], match[1]
            is_duplicate = False
            for kept in deduped:
                dist = ((mx - kept[0]) ** 2 + (my - kept[1]) ** 2) ** 0.5
                if dist < cross_template_dedup_radius:
                    is_duplicate = True
                    break
            if not is_duplicate:
                deduped.append(match)

        logger.info(
            f"find_all_multi_template: {len(deduped)} matches "
            f"(raw={len(all_matches)}, threshold={threshold}, "
            f"templates={len(template_paths)})"
        )

        return deduped
