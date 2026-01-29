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
                      Examples:
                      - 'custom:my_custom_item.png' (user images folder)
                      - 'images/bot/items/my_item.png' (auto-prefixed)
                      - 'src/osrsbot/images/bot/items/my_item.png' (full path)

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
        # Strip 'custom:' prefix
        custom_filename = normalized_path.replace("custom:", "", 1)

        # Determine user_images folder location
        if getattr(sys, "frozen", False):
            # .exe mode: user_images folder next to the .exe
            exe_dir = Path(sys.executable).parent
            user_images_dir = exe_dir / "user_images"
        else:
            # Development mode: user_images folder in project root
            project_root = Path(__file__).parent.parent.parent.parent
            user_images_dir = project_root / "user_images"

        # Create user_images folder if it doesn't exist
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
        # Strip src/osrsbot/ prefix and resolve from _MEIPASS
        relative_path = normalized_path.replace("src/osrsbot/", "", 1)
        resolved_path = Path(sys._MEIPASS) / "osrsbot" / relative_path
        logger.info(f"Resolved bundled template: {template_path} -> {resolved_path}")
    else:
        # Development mode: use the normalized path as-is
        resolved_path = Path(normalized_path)

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
