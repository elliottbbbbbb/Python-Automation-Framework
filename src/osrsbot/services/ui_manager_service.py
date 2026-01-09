from osrsbot.models.ui_elements import UIButton, UIElementGrid
from typing import Dict, List, Optional, TYPE_CHECKING
import cv2 as cv
import numpy as np
import logging
from pathlib import Path
from datetime import datetime

if TYPE_CHECKING:
    from osrsbot.services.template_match_service import TemplateMatchService

logger = logging.getLogger(__name__)


class UIManager:
    """
    Manages UI elements and provides debug visualization capabilities.

    This class wraps TemplateMatchService and provides:
    - Centralized access to detected UI grids and buttons
    - Active grid tracking for context-aware operations
    - Debug visualization with red boxes showing detected elements
    - Screenshot annotations with element labels and confidence scores
    """

    def __init__(self, template_service: Optional["TemplateMatchService"] = None):
        """
        Initialize UIManager.

        Args:
            template_service: Optional TemplateMatchService reference for automatic sync
        """
        self.grids: Dict[str, UIElementGrid] = {}
        self.active_grid_name: Optional[str] = None
        self.buttons: Dict[str, UIButton] = {}
        self.template_service = template_service

        # Debug settings
        self.debug_enabled = False
        self.debug_output_dir = Path("ui_debug")
        self.debug_output_dir.mkdir(exist_ok=True)

    def add_grid(self, name: str, grid: UIElementGrid):
        """Add a UI grid to the manager."""
        self.grids[name] = grid
        logger.debug(f"Added grid '{name}' to UIManager")

    def set_active_grid(self, name: str):
        """Set the currently active grid for context-aware operations."""
        if name in self.grids:
            self.active_grid_name = name
            logger.debug(f"Active grid set to '{name}'")
        else:
            raise ValueError(f"Grid '{name}' not found in UIManager.")

    def get_active_grid(self) -> Optional[UIElementGrid]:
        """Get the currently active grid."""
        if self.active_grid_name:
            return self.grids.get(self.active_grid_name)
        return None

    def get_grid(self, name: str) -> Optional[UIElementGrid]:
        """Get a specific grid by name."""
        return self.grids.get(name)

    def add_button(self, name: str, button: UIButton):
        """Add a UI button to the manager."""
        self.buttons[name] = button
        logger.debug(f"Added button '{name}' to UIManager")

    def get_button(self, name: str) -> Optional[UIButton]:
        """Get a specific button by name."""
        return self.buttons.get(name)

    def sync_from_template_service(self):
        """
        Sync grids and buttons from the associated TemplateMatchService.

        This is useful when templates are registered via config but UIManager
        needs to access them.
        """
        if not self.template_service:
            logger.warning("No template_service associated with UIManager")
            return

        # Sync grids
        for name, grid in self.template_service.grids.items():
            if name not in self.grids:
                self.grids[name] = grid

        # Sync buttons
        for name, button in self.template_service.buttons.items():
            if name not in self.buttons:
                self.buttons[name] = button

        logger.info(f"Synced {len(self.grids)} grids and {len(self.buttons)} buttons from template_service")

    def get_visible_elements(self) -> Dict[str, List[str]]:
        """
        Get all currently visible UI elements.

        Returns:
            Dictionary with 'grids' and 'buttons' lists containing visible element names
        """
        visible = {
            "grids": [name for name, grid in self.grids.items() if grid.visible],
            "buttons": [name for name, button in self.buttons.items() if button.visible]
        }
        return visible

    def enable_debug(self, output_dir: Optional[str] = None):
        """
        Enable debug visualization mode.

        Args:
            output_dir: Optional custom output directory for debug images
        """
        self.debug_enabled = True
        if output_dir:
            self.debug_output_dir = Path(output_dir)
            self.debug_output_dir.mkdir(exist_ok=True)
        logger.info(f"UI debug visualization enabled. Output: {self.debug_output_dir}")

    def disable_debug(self):
        """Disable debug visualization mode."""
        self.debug_enabled = False
        logger.info("UI debug visualization disabled")

    def draw_debug_overlay(
        self,
        img: np.ndarray,
        show_grids: bool = True,
        show_buttons: bool = True,
        show_slots: bool = True,
        show_labels: bool = True,
        visible_grids: Optional[Dict[str, bool]] = None
    ) -> np.ndarray:
        """
        Draw debug overlay on image showing detected UI elements with red boxes.

        Args:
            img: Input image (BGR or grayscale)
            show_grids: Draw grid bounding boxes
            show_buttons: Draw button bounding boxes
            show_slots: Draw individual grid slot boxes
            show_labels: Add text labels to elements
            visible_grids: Optional dict of grid names to visibility (True/False)

        Returns:
            Image with debug overlay drawn
        """
        # Convert grayscale to BGR if needed
        if len(img.shape) == 2:
            img_debug = cv.cvtColor(img, cv.COLOR_GRAY2BGR)
        else:
            img_debug = img.copy()

        # Color mapping for different grids (BGR format)
        grid_colors = {
            "inventory": (0, 255, 0),      # Green
            "spellbook": (0, 0, 255),      # Red
            "prayer": (255, 0, 0),         # Blue
            "equipment": (0, 255, 255),    # Yellow
            "chat": (255, 255, 0),         # Cyan
            "minimap": (255, 0, 255),      # Magenta
        }
        default_color = (128, 128, 128)    # Gray for unknown grids

        # Draw grids
        if show_grids:
            for name, grid in self.grids.items():
                # Check if this grid should be visible based on filter
                if visible_grids is not None and not visible_grids.get(name, False):
                    continue

                if grid.visible and grid.detected_bbox:
                    x, y, w, h = grid.detected_bbox

                    # Get color for this grid
                    color = grid_colors.get(name, default_color)

                    # Draw grid bounding box (thick)
                    cv.rectangle(img_debug, (x, y), (x + w, y + h), color, 1)

                    # Add grid name label at top-left
                    if show_labels:
                        label = f"{name}"
                        cv.putText(img_debug, label, (x + 5, y + 20),
                                  cv.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

                    # Draw individual slots
                    if show_slots:
                        # Draw boxes and center points (no labels)
                        for element in grid.elements:
                            x0, y0, x1, y1 = element.bbox
                            # Draw slot box (thin)
                            cv.rectangle(img_debug, (x0, y0), (x1, y1), color, 1)

                            # Draw center point with same color
                            cx, cy = element.center
                            cv.circle(img_debug, (cx, cy), 2, color, -1)

        # Buttons are not drawn - only grids are visualized

        return img_debug

    def save_debug_image(
        self,
        img: np.ndarray,
        prefix: str = "ui_debug",
        show_grids: bool = True,
        show_buttons: bool = True,
        show_slots: bool = True,
        show_labels: bool = True,
        visible_grids: Optional[Dict[str, bool]] = None
    ) -> Optional[str]:
        """
        Save debug visualization to file.

        Args:
            img: Input image
            prefix: Filename prefix
            show_grids: Draw grid bounding boxes
            show_buttons: Draw button bounding boxes
            show_slots: Draw individual grid slot boxes
            show_labels: Add text labels
            visible_grids: Optional dict of grid names to visibility (True/False)

        Returns:
            Path to saved image, or None if debug disabled
        """
        if not self.debug_enabled:
            return None

        # Draw overlay
        img_debug = self.draw_debug_overlay(
            img, show_grids, show_buttons, show_slots, show_labels, visible_grids
        )

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"{prefix}_{timestamp}.png"
        filepath = self.debug_output_dir / filename

        # Save
        cv.imwrite(str(filepath), img_debug)
        logger.info(f"Saved debug image: {filepath}")

        return str(filepath)

    def get_element_info(self) -> Dict[str, Dict]:
        """
        Get detailed information about all registered elements.

        Returns:
            Dictionary with detailed info about grids and buttons
        """
        info = {
            "grids": {},
            "buttons": {}
        }

        # Grid info
        for name, grid in self.grids.items():
            info["grids"][name] = {
                "visible": grid.visible,
                "rows": grid.num_rows,
                "cols": grid.num_cols,
                "num_slots": len(grid.elements),
                "confidence": grid.last_confidence,
                "bbox": grid.detected_bbox,
                "threshold": grid.threshold
            }

        # Button info
        for name, button in self.buttons.items():
            info["buttons"][name] = {
                "visible": button.visible,
                "confidence": button.last_confidence,
                "position": button.element.center if button.element else None,
                "threshold": button.threshold
            }

        return info

