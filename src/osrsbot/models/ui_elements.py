"""
UI Element Models - Data structures for template-matched UI elements.

Contains dataclasses and classes representing UI elements detected via template matching.
Used by TemplateMatchService, GameActions, and game state queries.

Key Classes:
- UIElement: Single clickable UI element with bounding box
- UIElementGrid: Grid of elements (inventory, prayer tab) with subdivision logic
"""

import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import cv2 as cv
import numpy as np

from osrsbot.constants import TEMPLATE_MATCHING

logger = logging.getLogger(__name__)


@dataclass
class UIElement:
    """
    Represents a single clickable UI element.

    Coordinates are relative to the game window (not absolute screen coords).
    Use GameActions._to_absolute() to convert to screen coordinates.

    Attributes:
        x0: Top-left X (relative to window)
        y0: Top-left Y (relative to window)
        x1: Bottom-right X (relative to window)
        y1: Bottom-right Y (relative to window)
        _center_x: Optional pre-calculated center X (avoids rounding errors)
        _center_y: Optional pre-calculated center Y (avoids rounding errors)
    """

    x0: int
    y0: int
    x1: int
    y1: int
    _center_x: Optional[int] = None
    _center_y: Optional[int] = None

    @property
    def center_x(self) -> int:
        """Center X coordinate (relative to window)"""
        if self._center_x is not None:
            return self._center_x
        return self.x0 + (self.x1 - self.x0) // 2

    @property
    def center_y(self) -> int:
        """Center Y coordinate (relative to window)"""
        if self._center_y is not None:
            return self._center_y
        return self.y0 + (self.y1 - self.y0) // 2

    @property
    def center(self) -> Tuple[int, int]:
        """Center coordinates (x, y) relative to window"""
        return (self.center_x, self.center_y)

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        """Bounding box (x0, y0, x1, y1) relative to window"""
        return (self.x0, self.y0, self.x1, self.y1)

    @property
    def width(self) -> int:
        """Element width in pixels"""
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        """Element height in pixels"""
        return self.y1 - self.y0


class UIElementGrid:
    """
    Represents a grid of UI elements (e.g., inventory 7×4, prayer 6×5).

    Detects the grid via template matching, then subdivides into individual
    clickable slots using mathematical calculation.

    Example:
        Inventory grid (7 rows × 4 cols = 28 slots):
        - Detect full grid border once
        - Calculate 28 individual slot positions
        - Cache results with TTL

    Attributes:
        name: Identifier (e.g., "inventory", "prayer_tab")
        template_path: Path to template image
        num_rows: Number of rows in grid
        num_cols: Number of columns in grid
        visible: True if grid currently detected
        elements: List of UIElement instances for each grid cell
    """

    def __init__(
        self,
        name: str,
        template_path: str,
        num_rows: int,
        num_cols: int,
        threshold: float = TEMPLATE_MATCHING.default_threshold,
        sticky: bool = True,
        ttl_seconds: float = TEMPLATE_MATCHING.default_ttl_seconds,
        padding: int = TEMPLATE_MATCHING.default_padding,
        border_offset: int = 0,
        border_offset_x: Optional[int] = None,
        border_offset_y: Optional[int] = None,
    ):
        """
        Initialize grid template.

        Args:
            name: Identifier (e.g., "inventory", "prayer_tab")
            template_path: Path to template image
            num_rows: Number of rows in grid
            num_cols: Number of columns in grid
            threshold: Detection confidence threshold (0.0-1.0)
            sticky: If True, cache detection until TTL expires
            ttl_seconds: Cache time-to-live in seconds
            padding: Pixels to subtract from each cell edge (avoid clicking borders)
            border_offset: Pixels of border in template image to exclude from grid area
            border_offset_x: Optional horizontal border offset (overrides border_offset)
            border_offset_y: Optional vertical border offset (overrides border_offset)
        """
        self.name = name
        self.template_path = template_path
        self.num_rows = num_rows
        self.num_cols = num_cols
        self.threshold = threshold
        self.sticky = sticky
        self.ttl_seconds = ttl_seconds
        self.padding = padding
        self.border_offset = border_offset
        self.border_offset_x = border_offset_x if border_offset_x is not None else border_offset
        self.border_offset_y = border_offset_y if border_offset_y is not None else border_offset

        # Load template image
        self.template = self._load_template()

        # Detection state
        self.visible = False
        self.detected_bbox: Optional[Tuple[int, int, int, int]] = None
        self.elements: List[UIElement] = []
        self.last_detection_time: float = 0.0
        self.last_confidence: float = 0.0

    def _load_template(self) -> np.ndarray:
        """
        Load template image as grayscale NumPy array.

        Returns:
            Grayscale template image

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        template_path = Path(self.template_path)

        # When running as .exe, resolve relative paths from the bundled location
        if not template_path.is_absolute() and getattr(sys, "frozen", False):
            # Normalize to forward slashes for comparison (Windows uses backslashes)
            normalized_path = self.template_path.replace("\\", "/")

            # Check if path starts with src/osrsbot (from config)
            if normalized_path.startswith("src/osrsbot/"):
                # Strip src/osrsbot/ prefix and resolve from _MEIPASS
                relative_path = normalized_path.replace("src/osrsbot/", "", 1)
                template_path = Path(sys._MEIPASS) / "osrsbot" / relative_path
                logger.debug(f"Resolved bundled template path: {template_path}")

        # Try loading the template
        template = cv.imread(str(template_path), cv.IMREAD_GRAYSCALE)

        if template is None:
            raise FileNotFoundError(
                f"Template not found or unreadable: {self.template_path}\n"
                f"Please ensure the template file exists and is a valid image.\n"
                f"Expected location: {template_path.absolute()}"
            )

        logger.debug(
            f"Loaded template '{self.name}': "
            f"{template.shape[1]}×{template.shape[0]} pixels"
        )
        return template

    def detect(self, img_gray: np.ndarray, force: bool = False) -> bool:
        """
        Detect grid in screenshot and subdivide into elements.

        Args:
            img_gray: Grayscale screenshot (NumPy array from capture_grayscale())
            force: Force re-detection even if cached

        Returns:
            True if grid detected, False otherwise
        """
        # Check sticky cache
        if self.sticky and self.visible and not force:
            time_since_detection = time.time() - self.last_detection_time
            if time_since_detection < self.ttl_seconds:
                logger.debug(
                    f"{self.name}: Using cached detection "
                    f"(age: {time_since_detection:.1f}s)"
                )
                return True

        # Perform template matching
        try:
            # Validate dimensions before matching
            template_h, template_w = self.template.shape[:2]
            img_h, img_w = img_gray.shape[:2]

            if template_w > img_w or template_h > img_h:
                logger.error(
                    f"{self.name}: Template ({template_w}x{template_h}) is larger than "
                    f"screenshot ({img_w}x{img_h}). Cannot perform matching."
                )
                self.visible = False
                return False

            res = cv.matchTemplate(img_gray, self.template, cv.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)

            if max_val >= self.threshold:
                x, y = max_loc
                h, w = self.template.shape

                self.detected_bbox = (x, y, w, h)
                self.last_confidence = max_val
                self.last_detection_time = time.time()

                # Subdivide into grid cells
                self._subdivide_grid(x, y, w, h)

                self.visible = True
                logger.info(
                    f"{self.name} detected at ({x}, {y}) "
                    f"with confidence {max_val:.3f}"
                )
                return True
            else:
                # Detection failed
                if self.visible:
                    logger.warning(
                        f"{self.name} no longer detected "
                        f"(confidence {max_val:.3f} < {self.threshold})"
                    )
                else:
                    logger.debug(
                        f"{self.name} not detected "
                        f"(confidence {max_val:.3f} < {self.threshold})"
                    )

                self.visible = False
                return False

        except Exception as e:
            logger.error(f"Error detecting {self.name}: {e}")
            self.visible = False
            return False

    def _subdivide_grid(self, x: int, y: int, w: int, h: int) -> None:
        """
        Subdivide detected grid into individual clickable elements.

        For inventory (7 rows × 4 cols):
        - cell_width = w / 4 ≈ 42 pixels
        - cell_height = h / 7 ≈ 36 pixels
        - Apply border_offset to exclude template border from grid area
        - Apply padding to avoid clicking grid borders

        Args:
            x: Top-left X of detected grid (relative to window)
            y: Top-left Y of detected grid (relative to window)
            w: Grid width in pixels (including template border)
            h: Grid height in pixels (including template border)
        """
        # Adjust for border offset (template image may include border pixels)
        # The actual grid area is smaller than the template
        # Use separate X and Y offsets if provided
        edge_row_nudge = 15

        grid_x = x + self.border_offset_x
        #grid_y = y  + self.border_offset_y
        grid_y = y
        grid_w = w - (2 * self.border_offset_x)
        grid_h = h - (0 * self.border_offset_y)

        cell_w = grid_w / self.num_cols
        cell_h = grid_h / self.num_rows

        self.elements = []
        for row in range(self.num_rows):
            for col in range(self.num_cols):
                # Calculate cell center first (more accurate)
                center_x_float = grid_x + (col + 0.5) * cell_w
                center_y_float = grid_y + (row + 0.5) * cell_h
                
                # Round center to int - this is the EXACT center we'll use
                center_x_int = int(round(center_x_float))
                center_y_int = int(round(center_y_float))
                
                #if row == 0:
                #    center_y_int -= edge_row_nudge
                #if row == self.num_rows - 1:
                #    center_y_int += edge_row_nudge

                # Calculate bounds from center with padding
                half_w = (cell_w / 2) - self.padding
                half_h = (cell_h / 2) - self.padding

                x0 = int(center_x_float - half_w)
                y0 = int(center_y_float - half_h)
                x1 = int(center_x_float + half_w)
                y1 = int(center_y_float + half_h)

                # Store the precise center to avoid recalculation rounding errors
                element = UIElement(x0, y0, x1, y1, _center_x=center_x_int, _center_y=center_y_int)
                self.elements.append(element)

        logger.debug(
            f"{self.name}: Subdivided into {len(self.elements)} elements "
            f"({self.num_rows}×{self.num_cols}, border_offset={self.border_offset}px)"
        )

    def get_element(self, index: int) -> Optional[UIElement]:
        """
        Get element by linear index (0-based).

        For inventory: index 0-27 corresponds to slots 1-28.
        Elements are ordered left-to-right, top-to-bottom.

        Args:
            index: Element index (0-based)

        Returns:
            UIElement or None if invalid index
        """
        if 0 <= index < len(self.elements):
            return self.elements[index]
        return None

    def get_element_at(self, row: int, col: int) -> Optional[UIElement]:
        """
        Get element by row/col coordinates (0-based).

        Args:
            row: Row index (0-based)
            col: Column index (0-based)

        Returns:
            UIElement or None if invalid coordinates
        """
        if 0 <= row < self.num_rows and 0 <= col < self.num_cols:
            index = row * self.num_cols + col
            return self.get_element(index)
        return None


class UIButton:
    """
    Represents a single UI button (prayer, run, logout, etc.).

    Detects button via template matching and stores center position.
    """

    def __init__(
        self,
        name: str,
        template_path: str,
        threshold: float = TEMPLATE_MATCHING.default_threshold,
        sticky: bool = False,
        ttl_seconds: float = TEMPLATE_MATCHING.default_ttl_seconds,
    ):
        """
        Initialize button template.

        Args:
            name: Identifier (e.g., "prayer_button", "logout")
            template_path: Path to template image
            threshold: Detection confidence threshold (0.0-1.0)
            sticky: If True, cache detection until TTL expires
            ttl_seconds: Cache time-to-live in seconds
        """
        self.name = name
        self.template_path = template_path
        self.threshold = threshold
        self.sticky = sticky
        self.ttl_seconds = ttl_seconds

        # Load template image
        self.template = self._load_template()

        # Detection state
        self.visible = False
        self.element: Optional[UIElement] = None
        self.last_detection_time: float = 0.0
        self.last_confidence: float = 0.0

    def _load_template(self) -> np.ndarray:
        """Load template image as grayscale NumPy array."""
        template_path = Path(self.template_path)

        # When running as .exe, resolve relative paths from the bundled location
        if not template_path.is_absolute() and getattr(sys, "frozen", False):
            # Normalize to forward slashes for comparison (Windows uses backslashes)
            normalized_path = self.template_path.replace("\\", "/")

            # Check if path starts with src/osrsbot (from config)
            if normalized_path.startswith("src/osrsbot/"):
                # Strip src/osrsbot/ prefix and resolve from _MEIPASS
                relative_path = normalized_path.replace("src/osrsbot/", "", 1)
                template_path = Path(sys._MEIPASS) / "osrsbot" / relative_path
                logger.debug(f"Resolved bundled template path: {template_path}")

        template = cv.imread(str(template_path), cv.IMREAD_GRAYSCALE)

        if template is None:
            raise FileNotFoundError(
                f"Template not found or unreadable: {self.template_path}\n"
                f"Please ensure the template file exists and is a valid image.\n"
                f"Expected location: {template_path.absolute()}"
            )

        logger.debug(
            f"Loaded template '{self.name}': "
            f"{template.shape[1]}×{template.shape[0]} pixels"
        )
        return template

    def detect(self, img_gray: np.ndarray, force: bool = False) -> bool:
        """
        Detect button in screenshot.

        Args:
            img_gray: Grayscale screenshot (NumPy array)
            force: Force re-detection even if cached

        Returns:
            True if button detected, False otherwise
        """
        # Check sticky cache
        if self.sticky and self.visible and not force:
            time_since_detection = time.time() - self.last_detection_time
            if time_since_detection < self.ttl_seconds:
                logger.debug(
                    f"{self.name}: Using cached detection "
                    f"(age: {time_since_detection:.1f}s)"
                )
                return True

        # Perform template matching
        try:
            # Validate dimensions before matching
            template_h, template_w = self.template.shape[:2]
            img_h, img_w = img_gray.shape[:2]

            if template_w > img_w or template_h > img_h:
                logger.error(
                    f"{self.name}: Template ({template_w}x{template_h}) is larger than "
                    f"screenshot ({img_w}x{img_h}). Cannot perform matching."
                )
                self.visible = False
                return False

            res = cv.matchTemplate(img_gray, self.template, cv.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)

            if max_val >= self.threshold:
                x, y = max_loc
                h, w = self.template.shape

                # Create UIElement for button
                self.element = UIElement(x, y, x + w, y + h)
                self.last_confidence = max_val
                self.last_detection_time = time.time()
                self.visible = True

                logger.info(
                    f"{self.name} detected at ({x}, {y}) "
                    f"with confidence {max_val:.3f}"
                )
                return True
            else:
                if self.visible:
                    logger.warning(
                        f"{self.name} no longer detected "
                        f"(confidence {max_val:.3f} < {self.threshold})"
                    )
                else:
                    logger.debug(
                        f"{self.name} not detected "
                        f"(confidence {max_val:.3f} < {self.threshold})"
                    )

                self.visible = False
                return False

        except Exception as e:
            logger.error(f"Error detecting {self.name}: {e}")
            self.visible = False
            return False
