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
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np

from osrsbot.constants import TEMPLATE_MATCHING
from osrsbot.models.config import Config
from osrsbot.models.ui_elements import UIButton, UIElementGrid

logger = logging.getLogger(__name__)


# ==================== UI Element Classes ====================
# UIElement, UIElementGrid, and UIButton have been moved to osrsbot.models.ui_elements
# They are imported at the top of this file for use by the service


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
        threshold: float = TEMPLATE_MATCHING.default_threshold,
        sticky: bool = True,
        ttl_seconds: float = TEMPLATE_MATCHING.default_ttl_seconds,
        padding: int = TEMPLATE_MATCHING.default_padding,
        border_offset: int = 0,
        border_offset_x: Optional[int] = None,
        border_offset_y: Optional[int] = None,
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
            border_offset: Pixels of border in template to exclude from grid area
            border_offset_x: Optional horizontal border offset (overrides border_offset)
            border_offset_y: Optional vertical border offset (overrides border_offset)

        Example:
            service.register_grid(
                name="inventory",
                template_path="templates/inventory_grid.png",
                num_rows=7,
                num_cols=4,
                sticky=True,
                border_offset=3  # if template includes 3px border
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
            padding=padding,
            border_offset=border_offset,
            border_offset_x=border_offset_x,
            border_offset_y=border_offset_y,
        )
        self.grids[name] = grid
        logger.info(f"Registered grid: {name} ({num_rows}×{num_cols})")

    def register_button(
        self,
        name: str,
        template_path: str,
        threshold: float = TEMPLATE_MATCHING.default_threshold,
        sticky: bool = False,
        ttl_seconds: float = TEMPLATE_MATCHING.default_ttl_seconds,
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
            ttl_seconds=ttl_seconds,
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
                        "threshold": TEMPLATE_MATCHING.default_threshold,
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
                threshold=grid_config.get(
                    "threshold", TEMPLATE_MATCHING.default_threshold
                ),
                sticky=grid_config.get("sticky", True),
                ttl_seconds=grid_config.get("ttl_seconds", 5.0),
                padding=grid_config.get("padding", 4),
                border_offset=grid_config.get("border_offset", 0),
                border_offset_x=grid_config.get("border_offset_x"),
                border_offset_y=grid_config.get("border_offset_y"),
            )

        # Load buttons
        buttons = config.get("templates", "ui_buttons", default={})
        for btn_name, btn_config in buttons.items():
            self.register_button(
                name=btn_name,
                template_path=btn_config["path"],
                threshold=btn_config.get(
                    "threshold", TEMPLATE_MATCHING.default_threshold
                ),
                sticky=btn_config.get("sticky", False),
                ttl_seconds=btn_config.get("ttl_seconds", 5.0),
            )

    # ==================== Detection ====================

    def detect_grid(self, name: str, img_gray: np.ndarray, force: bool = False) -> bool:
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
        self, name: str, img_gray: np.ndarray, force: bool = False
    ) -> bool:
        """Detect specific button."""
        if name not in self.buttons:
            logger.error(f"Button '{name}' not registered")
            return False

        return self.buttons[name].detect(img_gray, force=force)

    def detect_all(self, img_gray: np.ndarray, force: bool = False) -> Dict[str, bool]:
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
        self, grid_name: str, slot_index: int
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
                f"Valid range: 0-{total_slots - 1}"
            )
            return None

        element = grid.get_element(slot_index)
        if not element:
            logger.error(
                f"Failed to get element for slot {slot_index} in grid '{grid_name}'"
            )
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
