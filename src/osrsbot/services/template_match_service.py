"""
Template Matching Service for OSRS UI Element Detection.

This service provides template matching capabilities for detecting UI elements
in OSRS, including inventory grids, prayer tabs, and UI buttons.

Key Features:
- Detect inventory grid and calculate all 28 slot positions
- Detect UI buttons (prayer, run, logout, etc.)
- Sticky caching with TTL for performance
- Mathematical grid subdivision
- OpenCV-based template matching
"""
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import cv2 as cv
import numpy as np

from osrsbot.models.config import Config

logger = logging.getLogger(__name__)


@dataclass
class UIElement:
    """
    Represents a single clickable UI element.

    Coordinates are relative to the game window (not absolute screen coords).
    Use GameActions._to_absolute() to convert to screen coordinates.
    """
    x0: int  # Top-left X (relative to window)
    y0: int  # Top-left Y (relative to window)
    x1: int  # Bottom-right X (relative to window)
    y1: int  # Bottom-right Y (relative to window)

    @property
    def center_x(self) -> int:
        """Center X coordinate (relative to window)"""
        return self.x0 + (self.x1 - self.x0) // 2

    @property
    def center_y(self) -> int:
        """Center Y coordinate (relative to window)"""
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
    """

    def __init__(
        self,
        name: str,
        template_path: str,
        num_rows: int,
        num_cols: int,
        threshold: float = 0.68,
        sticky: bool = True,
        ttl_seconds: float = 5.0,
        padding: int = 4
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
        """
        self.name = name
        self.template_path = template_path
        self.num_rows = num_rows
        self.num_cols = num_cols
        self.threshold = threshold
        self.sticky = sticky
        self.ttl_seconds = ttl_seconds
        self.padding = padding

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

    def detect(
        self,
        img_gray: np.ndarray,
        force: bool = False
    ) -> bool:
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

    def _subdivide_grid(
        self,
        x: int,
        y: int,
        w: int,
        h: int
    ) -> None:
        """
        Subdivide detected grid into individual clickable elements.

        For inventory (7 rows × 4 cols):
        - cell_width = w / 4 ≈ 42 pixels
        - cell_height = h / 7 ≈ 36 pixels
        - Apply padding to avoid clicking grid borders

        Args:
            x: Top-left X of detected grid (relative to window)
            y: Top-left Y of detected grid (relative to window)
            w: Grid width in pixels
            h: Grid height in pixels
        """
        cell_w = w / self.num_cols
        cell_h = h / self.num_rows

        self.elements = []
        for row in range(self.num_rows):
            for col in range(self.num_cols):
                # Calculate cell bounds with padding
                x0 = int(x + col * cell_w + self.padding)
                y0 = int(y + row * cell_h + self.padding)
                x1 = int(x + (col + 1) * cell_w - self.padding)
                y1 = int(y + (row + 1) * cell_h - self.padding)

                element = UIElement(x0, y0, x1, y1)
                self.elements.append(element)

        logger.debug(
            f"{self.name}: Subdivided into {len(self.elements)} elements "
            f"({self.num_rows}×{self.num_cols})"
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

    def get_element_at(
        self,
        row: int,
        col: int
    ) -> Optional[UIElement]:
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
        threshold: float = 0.68,
        sticky: bool = False,
        ttl_seconds: float = 5.0
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

    def detect(
        self,
        img_gray: np.ndarray,
        force: bool = False
    ) -> bool:
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


class TemplateMatchService:
    """
    Template matching service for OSRS UI element detection.

    Features:
    - Register grids (inventory, prayer, equipment)
    - Register buttons (prayer, run, logout, special attack)
    - Detect all registered elements in one pass
    - Calculate slot positions mathematically
    - Cache results with TTL
    - Force re-detection when needed

    Usage:
        # Initialize service
        service = TemplateMatchService(templates_dir="templates")

        # Register inventory grid
        service.register_grid(
            name="inventory",
            template_path="templates/inventory_grid.png",
            num_rows=7,
            num_cols=4
        )

        # Register prayer button
        service.register_button(
            name="prayer_button",
            template_path="templates/prayer_button.png"
        )

        # Detect elements
        img_gray = screen_service.capture_grayscale()
        service.detect_grid("inventory", img_gray)

        # Get slot position
        slot_pos = service.get_slot_position("inventory", 0)  # First slot
    """

    def __init__(self, templates_dir: str = "templates"):
        """
        Initialize template matching service.

        Args:
            templates_dir: Root directory for template images
        """
        self.templates_dir = Path(templates_dir)

        # Registered elements
        self.grids: Dict[str, UIElementGrid] = {}
        self.buttons: Dict[str, UIButton] = {}

        logger.info(f"TemplateMatchService initialized (dir: {templates_dir})")

    # ==================== Registration ====================

    def register_grid(
        self,
        name: str,
        template_path: str,
        num_rows: int,
        num_cols: int,
        threshold: float = 0.68,
        sticky: bool = True,
        ttl_seconds: float = 5.0,
        padding: int = 4
    ) -> None:
        """
        Register a grid template (inventory, prayer, equipment).

        Args:
            name: Identifier (e.g., "inventory", "prayer_tab")
            template_path: Path to template image (relative to project root)
            num_rows: Number of rows in grid
            num_cols: Number of columns in grid
            threshold: Match confidence (0.0-1.0)
            sticky: If True, stays detected once found (until TTL expires)
            ttl_seconds: Cache time-to-live
            padding: Pixels to subtract from each cell edge

        Example:
            service.register_grid(
                name="inventory",
                template_path="templates/inventory_grid.png",
                num_rows=7,
                num_cols=4,
                sticky=True
            )
        """
        grid = UIElementGrid(
            name=name,
            template_path=template_path,
            num_rows=num_rows,
            num_cols=num_cols,
            threshold=threshold,
            sticky=sticky,
            ttl_seconds=ttl_seconds,
            padding=padding
        )
        self.grids[name] = grid
        logger.info(f"Registered grid: {name} ({num_rows}×{num_cols})")

    def register_button(
        self,
        name: str,
        template_path: str,
        threshold: float = 0.68,
        sticky: bool = False,
        ttl_seconds: float = 5.0
    ) -> None:
        """
        Register a button template.

        Args:
            name: Identifier (e.g., "prayer_button", "logout")
            template_path: Path to template image
            threshold: Match confidence
            sticky: If True, stays detected once found
            ttl_seconds: Cache time-to-live
        """
        button = UIButton(
            name=name,
            template_path=template_path,
            threshold=threshold,
            sticky=sticky,
            ttl_seconds=ttl_seconds
        )
        self.buttons[name] = button
        logger.info(f"Registered button: {name}")

    def register_from_config(self, config: Config) -> None:
        """
        Register all templates from config.json.

        Expected config structure:
        {
            "templates": {
                "ui_grids": {
                    "inventory": {
                        "path": "templates/inventory_grid.png",
                        "rows": 7,
                        "cols": 4,
                        "threshold": 0.68,
                        "sticky": true
                    }
                },
                "ui_buttons": {
                    "prayer_button": {
                        "path": "templates/prayer_button.png",
                        "threshold": 0.68
                    }
                }
            }
        }
        """
        # Load grids
        grids = config.get("templates", "ui_grids", default={})
        for grid_name, grid_config in grids.items():
            self.register_grid(
                name=grid_name,
                template_path=grid_config["path"],
                num_rows=grid_config.get("rows", 1),
                num_cols=grid_config.get("cols", 1),
                threshold=grid_config.get("threshold", 0.68),
                sticky=grid_config.get("sticky", True),
                ttl_seconds=grid_config.get("ttl_seconds", 5.0),
                padding=grid_config.get("padding", 4)
            )

        # Load buttons
        buttons = config.get("templates", "ui_buttons", default={})
        for btn_name, btn_config in buttons.items():
            self.register_button(
                name=btn_name,
                template_path=btn_config["path"],
                threshold=btn_config.get("threshold", 0.68),
                sticky=btn_config.get("sticky", False),
                ttl_seconds=btn_config.get("ttl_seconds", 5.0)
            )

    # ==================== Detection ====================

    def detect_grid(
        self,
        name: str,
        img_gray: np.ndarray,
        force: bool = False
    ) -> bool:
        """
        Detect specific grid.

        Args:
            name: Grid identifier
            img_gray: Grayscale screenshot
            force: Force re-detection

        Returns:
            True if detected
        """
        if name not in self.grids:
            logger.error(f"Grid '{name}' not registered")
            return False

        return self.grids[name].detect(img_gray, force=force)

    def detect_button(
        self,
        name: str,
        img_gray: np.ndarray,
        force: bool = False
    ) -> bool:
        """Detect specific button."""
        if name not in self.buttons:
            logger.error(f"Button '{name}' not registered")
            return False

        return self.buttons[name].detect(img_gray, force=force)

    def detect_all(
        self,
        img_gray: np.ndarray,
        force: bool = False
    ) -> Dict[str, bool]:
        """
        Detect all registered elements in one pass.

        Returns:
            Dictionary of {element_name: detected_status}
        """
        results = {}

        # Detect all grids
        for name, grid in self.grids.items():
            results[name] = grid.detect(img_gray, force=force)

        # Detect all buttons
        for name, button in self.buttons.items():
            results[name] = button.detect(img_gray, force=force)

        return results

    # ==================== Getters ====================

    def get_grid(self, name: str) -> Optional[UIElementGrid]:
        """Get grid by name."""
        return self.grids.get(name)

    def get_button(self, name: str) -> Optional[UIButton]:
        """Get button by name."""
        return self.buttons.get(name)

    def is_visible(self, name: str) -> bool:
        """Check if element is currently visible."""
        if name in self.grids:
            return self.grids[name].visible
        if name in self.buttons:
            return self.buttons[name].visible
        return False

    def get_slot_position(
        self,
        grid_name: str,
        slot_index: int
    ) -> Optional[Tuple[int, int]]:
        """
        Get center coordinates for a grid slot.

        Args:
            grid_name: Grid identifier (e.g., "inventory")
            slot_index: Slot index (0-based)

        Returns:
            (x, y) center coordinates (relative to window) or None
        """
        grid = self.get_grid(grid_name)
        if not grid:
            logger.error(f"Grid '{grid_name}' not registered")
            return None

        if not grid.visible:
            logger.warning(f"Grid '{grid_name}' not currently visible")
            return None

        # Validate slot index
        total_slots = grid.num_rows * grid.num_cols
        if not 0 <= slot_index < total_slots:
            logger.error(
                f"Invalid slot index {slot_index} for grid '{grid_name}'. "
                f"Valid range: 0-{total_slots-1}"
            )
            return None

        element = grid.get_element(slot_index)
        if not element:
            logger.error(f"Failed to get element for slot {slot_index} in grid '{grid_name}'")
            return None

        return element.center

    def get_button_position(self, button_name: str) -> Optional[Tuple[int, int]]:
        """
        Get center coordinates for a button.

        Args:
            button_name: Button identifier (e.g., "prayer_button")

        Returns:
            (x, y) center coordinates (relative to window) or None
        """
        button = self.get_button(button_name)
        if not button or not button.visible or not button.element:
            return None

        return button.element.center

    def has_button(self, button_name: str) -> bool:
        """
        Check if a button is registered.

        Args:
            button_name: Button identifier

        Returns:
            True if button is registered, False otherwise
        """
        return button_name in self.buttons

    def invalidate_cache(self, name: Optional[str] = None) -> None:
        """
        Invalidate detection cache.

        Args:
            name: Element name to invalidate (None = invalidate all)
        """
        if name is None:
            # Invalidate all
            for grid in self.grids.values():
                grid.visible = False
                grid.last_detection_time = 0.0
            for button in self.buttons.values():
                button.visible = False
                button.last_detection_time = 0.0
            logger.debug("Invalidated all template caches")
        else:
            # Invalidate specific element
            if name in self.grids:
                self.grids[name].visible = False
                self.grids[name].last_detection_time = 0.0
            if name in self.buttons:
                self.buttons[name].visible = False
                self.buttons[name].last_detection_time = 0.0
            logger.debug(f"Invalidated cache for: {name}")
