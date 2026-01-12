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
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import cv2 as cv
import numpy as np

from osrsbot.services.screen_service import ScreenService

logger = logging.getLogger(__name__)


def _resolve_template_path(template_path: str) -> Path:
    """
    Resolve template path for .exe environment.

    When running as .exe, converts relative paths like 'src/osrsbot/images/...'
    to absolute paths inside the bundled _MEIPASS directory.

    Args:
        template_path: Original template path (relative or absolute)

    Returns:
        Resolved Path object
    """
    resolved_path = Path(template_path)

    # When running as .exe, resolve relative paths from the bundled location
    if not resolved_path.is_absolute() and getattr(sys, "frozen", False):
        # Normalize path to use forward slashes for comparison (Windows uses backslashes)
        normalized_path = template_path.replace("\\", "/")

        # Check if path starts with src/osrsbot (from config or hardcoded)
        if normalized_path.startswith("src/osrsbot/"):
            # Strip src/osrsbot/ prefix and resolve from _MEIPASS
            relative_path = normalized_path.replace("src/osrsbot/", "", 1)
            resolved_path = Path(sys._MEIPASS) / "osrsbot" / relative_path
            logger.info(f"Resolved bundled template: {template_path} -> {resolved_path}")
        else:
            logger.warning(f"Path doesn't start with 'src/osrsbot/': {normalized_path}")

    return resolved_path


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
            resolved_path = _resolve_template_path(search_button_template)
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
        self, template_path: str, threshold: float = 0.7
    ) -> Optional[Tuple[int, int, float]]:
        """
        Find a template on screen.

        Args:
            template_path: Path to template image
            threshold: Match confidence threshold (0.0-1.0)

        Returns:
            Tuple of (center_x, center_y, confidence) if found, None otherwise
        """
        try:
            # Resolve template path for .exe
            resolved_path = _resolve_template_path(template_path)

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

            # Perform template matching
            result = cv.matchTemplate(img_np, template, cv.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv.minMaxLoc(result)

            if max_val >= threshold:
                # Calculate center of matched region
                x, y = max_loc
                h, w = template.shape[:2]
                center_x = x + w // 2
                center_y = y + h // 2

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
        self, template_paths: List[str], threshold: float = 0.7
    ) -> Optional[Tuple[int, int, float, str]]:
        """
        Find best matching template from multiple options.

        Useful for items that appear differently at different zoom levels, angles, etc.

        Args:
            template_paths: List of paths to template images
            threshold: Match confidence threshold (0.0-1.0)

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
                resolved_path = _resolve_template_path(template_path)
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

                # Perform template matching
                result = cv.matchTemplate(img_np, template, cv.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv.minMaxLoc(result)

                # Keep track of best match
                if max_val > best_confidence:
                    best_confidence = max_val
                    best_match = max_loc
                    best_template_name = Path(template_path).name

                    # Calculate center
                    x, y = max_loc
                    h, w = template.shape[:2]
                    center_x = x + w // 2
                    center_y = y + h // 2
                    best_center = (center_x, center_y)

            except Exception as e:
                logger.warning(f"Error checking template {template_path}: {e}")
                continue

        # Check if we found a match above threshold
        if best_match is not None and best_confidence >= threshold:
            logger.debug(
                f"Found best template '{best_template_name}' at {best_center} "
                f"with confidence {best_confidence:.3f}"
            )
            return (*best_center, best_confidence, best_template_name)
        else:
            logger.debug(
                f"No templates found (best confidence: {best_confidence:.3f} < {threshold})"
            )
            return None
