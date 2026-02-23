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

    # Maps open-state template button name → grid shown when that tab is active.
    # Detection: button.visible == True AND open_confidence > closed_confidence.
    # Add an entry here when you have a *_open.PNG template for a tab.
    _TAB_OPEN_MAP: Dict[str, str] = {
        "inventory_open":      "inventory",
        "worn_equipment_open": "equipment",
        "prayer_open":         "prayer",
        "magic_open":          "spellbook",
    }

    # Maps open-state button → its corresponding always-visible closed-state button.
    # Used to disambiguate false positives: if the closed template scores higher
    # than the open template, the tab is actually closed.
    _TAB_OPEN_CLOSED_PAIR: Dict[str, str] = {
        "inventory_open":      "inventory_tab",
        "worn_equipment_open": "equipment_tab",
        "prayer_open":         "prayer_tab",
        "magic_open":          "spellbook_tab",
    }

    # Maps always-visible tab button name → grid name for colour-based detection.
    # Used as fallback for tabs that don't yet have an open-state template.
    # All tabs now have open-state templates, so this is empty — kept for extensibility.
    _TAB_GRID_MAP: Dict[str, str] = {}

    # Active tab highlight colour: #230c0a = RGB(35,12,10) = BGR(10,12,35)
    _TAB_ACTIVE_BGR  = (10,  12,  35)
    _TAB_COLOR_TOL   = 45   # per-channel tolerance

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

        # Static regions: always drawn in live view regardless of detection state.
        # Format: {name: {"x", "y", "w", "h", "color" (BGR), "label"}}
        self._static_regions: Dict[str, dict] = {}

        # Last known active tab-gated grid name (inventory / equipment / prayer / spellbook)
        self._active_panel_grid: Optional[str] = None

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

    def register_static_region(
        self,
        name: str,
        x: int,
        y: int,
        w: int,
        h: int,
        color: tuple = (0, 200, 255),
        label: Optional[str] = None,
    ) -> None:
        """
        Register a named region that is always drawn in the live view overlay.

        Unlike grids/buttons, static regions don't require template detection —
        they're drawn on every frame at the given window-relative coordinates.
        Useful for OCR stat regions (HP, prayer, run energy, spec) and any
        other fixed UI areas the bot reads from.

        Args:
            name: Unique identifier (re-registering replaces the existing entry).
            x, y: Top-left corner relative to the game window.
            w, h: Width and height in pixels.
            color: BGR colour tuple for the overlay box.
            label: Text label drawn above the box. Defaults to ``name``.
        """
        self._static_regions[name] = {
            "x": x, "y": y, "w": w, "h": h,
            "color": color,
            "label": label if label is not None else name,
        }
        logger.debug(f"UIManager: registered static region '{name}' at ({x},{y}) {w}×{h}")

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
            "inventory":    (0, 255, 0),      # Green
            "spellbook":    (0, 0, 255),      # Red
            "prayer":       (255, 0, 0),      # Blue
            "equipment":    (0, 255, 255),    # Yellow
            "chat":         (255, 255, 0),    # Cyan
            "minimap":      (255, 0, 255),    # Magenta
            "all_settings": (0, 165, 255),    # Orange
            "audio":        (255, 50, 180),   # Pink
            "activities":   (50, 255, 180),   # Lime
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

        # Draw buttons
        if show_buttons:
            button_color = (0, 165, 255)  # Orange
            for name, button in self.buttons.items():
                if button.visible and button.element:
                    x0, y0, x1, y1 = button.element.bbox
                    cv.rectangle(img_debug, (x0, y0), (x1, y1), button_color, 1)
                    if show_labels:
                        cv.putText(img_debug, name, (x0, y0 - 4),
                                   cv.FONT_HERSHEY_SIMPLEX, 0.4, button_color, 1)

        # Draw static regions (always visible, no detection required)
        for region in self._static_regions.values():
            rx, ry, rw, rh = region["x"], region["y"], region["w"], region["h"]
            rcolor = region["color"]
            cv.rectangle(img_debug, (rx, ry), (rx + rw, ry + rh), rcolor, 1)
            if show_labels and region["label"]:
                label_y = max(ry - 4, 10)
                cv.putText(img_debug, region["label"], (rx + 2, label_y),
                           cv.FONT_HERSHEY_SIMPLEX, 0.45, rcolor, 1)

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

    # ── Tab-state detection ────────────────────────────────────────────────────

    def _button_region_has_active_color(
        self, frame_bgr: np.ndarray, button
    ) -> bool:
        """
        Return True if ANY pixel inside the button's bounding box matches the
        active-tab highlight colour within tolerance.

        Scanning the full region is necessary because the reddish highlight can
        appear at different positions within the button (corners, edges, or
        scattered pixels) rather than at a single fixed point.
        """
        if not button.element:
            return False
        x0, y0, x1, y1 = button.element.bbox
        fh, fw = frame_bgr.shape[:2]
        y0, y1 = max(0, y0), min(fh, y1)
        x0, x1 = max(0, x0), min(fw, x1)
        if y0 >= y1 or x0 >= x1:
            return False
        region = frame_bgr[y0:y1, x0:x1].astype(np.int16)
        tb, tg, tr = self._TAB_ACTIVE_BGR  # stored as BGR
        tol = self._TAB_COLOR_TOL
        diff = np.abs(region - np.array([tb, tg, tr], dtype=np.int16))
        return bool(np.any(np.all(diff <= tol, axis=2)))

    def _detect_active_tab_from_frame(self, frame_bgr: np.ndarray) -> Optional[str]:
        """
        Determine the active tab-gated grid from the current BGR live-view frame.

        Detection order:
          1. Template-based: if a button in ``_TAB_OPEN_MAP`` is marked visible
             (its open-state template was matched in the last detection pass),
             that grid is active — no pixel sampling needed.
          2. Colour-based fallback: scan each button in ``_TAB_GRID_MAP`` for the
             reddish active-tab highlight (#230c0a ± tolerance).

        Called inside the live-view overlay callback — no extra screen capture.
        When no tab matches, ``_active_panel_grid`` is cleared to None.
        """
        # 1. Template-based (most reliable)
        for btn_name, grid_name in self._TAB_OPEN_MAP.items():
            button = self.buttons.get(btn_name)
            if not button or not button.visible:
                continue
            # Guard against false positives: the open and closed templates often
            # look similar enough that both match. Only trust "open" if its
            # confidence beats the closed-state button's confidence.
            open_conf = button.last_confidence
            closed_btn_name = self._TAB_OPEN_CLOSED_PAIR.get(btn_name)
            if closed_btn_name:
                closed_btn = self.buttons.get(closed_btn_name)
                closed_conf = closed_btn.last_confidence if closed_btn else 0.0
                if open_conf <= closed_conf:
                    continue  # Closed template matches better — tab is not open
            self._active_panel_grid = grid_name
            return grid_name

        # 2. Colour-based fallback for tabs without open-state templates
        for btn_name, grid_name in self._TAB_GRID_MAP.items():
            button = self.buttons.get(btn_name)
            if not button or not button.element:
                continue
            if self._button_region_has_active_color(frame_bgr, button):
                self._active_panel_grid = grid_name
                return grid_name

        # Nothing matched — clear so the last tab doesn't linger
        self._active_panel_grid = None
        return None

    def update_active_tab(self, screen) -> Optional[str]:
        """
        Determine the active tab-gated grid for use in the detection loop.

        Detection order:
          1. Template-based: check ``_TAB_OPEN_MAP`` buttons — if any is marked
             visible (open-state template matched), that grid is active.
          2. Colour-based fallback: search each ``_TAB_GRID_MAP`` button region
             for the reddish active-tab highlight via ScreenService.find_color.

        Args:
            screen: ScreenService instance (used for colour fallback only).

        Returns:
            Grid name of the active tab panel, or None if undetermined.
        """
        # 1. Template-based (most reliable)
        for btn_name, grid_name in self._TAB_OPEN_MAP.items():
            button = self.buttons.get(btn_name)
            if not button or not button.visible:
                continue
            open_conf = button.last_confidence
            closed_btn_name = self._TAB_OPEN_CLOSED_PAIR.get(btn_name)
            if closed_btn_name:
                closed_btn = self.buttons.get(closed_btn_name)
                closed_conf = closed_btn.last_confidence if closed_btn else 0.0
                if open_conf <= closed_conf:
                    continue  # Closed template matches better — tab is not open
            self._active_panel_grid = grid_name
            return grid_name

        # 2. Colour-based fallback for tabs without open-state templates
        tb, tg, tr = self._TAB_ACTIVE_BGR  # BGR → RGB hex
        active_hex = f"#{tr:02x}{tg:02x}{tb:02x}"
        for btn_name, grid_name in self._TAB_GRID_MAP.items():
            button = self.buttons.get(btn_name)
            if not button or not button.element:
                continue
            x0, y0, x1, y1 = button.element.bbox
            try:
                match = screen.find_color(
                    active_hex,
                    tolerance=self._TAB_COLOR_TOL,
                    region=(x0, y0, x1 - x0, y1 - y0),
                )
                if match:
                    self._active_panel_grid = grid_name
                    return grid_name
            except Exception:
                continue
        self._active_panel_grid = None
        return None

    def get_active_panel_grid(self) -> Optional[str]:
        """
        Return the name of the currently active tab-gated grid
        (inventory / equipment / prayer / spellbook), or None if unknown.

        Updated automatically each live-view frame, or explicitly via
        ``update_active_tab(screen)``.
        """
        return self._active_panel_grid

    def _build_visible_grids_filter(self) -> Dict[str, bool]:
        """
        Return a visible_grids dict for draw_debug_overlay.

        Tab-gated grids (from both _TAB_OPEN_MAP and _TAB_GRID_MAP) are only
        shown when their tab is active. Non-tab grids (minimap, chat) are always shown.
        """
        tab_grids = set(self._TAB_OPEN_MAP.values()) | set(self._TAB_GRID_MAP.values())
        return {
            name: (name not in tab_grids or name == self._active_panel_grid)
            for name in self.grids
        }

    # ── Live overlay ───────────────────────────────────────────────────────────

    def register_live_overlay(self, live_view_service) -> None:
        """
        Register UIManager's visualisation with LiveViewService.

        Each frame the overlay:
          1. Samples tab-button pixel colours to determine the active panel.
          2. Draws only the active tab-gated grid (inventory/equipment/prayer/spellbook).
          3. Always draws non-tab grids (minimap, chat) and static regions.

        Zero extra screen captures — pixels are sampled from the frame already
        in the live-view pipeline.
        """
        def _ui_overlay_callback(frame_bgr: np.ndarray) -> np.ndarray:
            self._detect_active_tab_from_frame(frame_bgr)
            return self.draw_debug_overlay(
                frame_bgr,
                show_labels=False,
                visible_grids=self._build_visible_grids_filter(),
            )

        live_view_service.register_overlay("ui_manager", _ui_overlay_callback)
        logger.info("UIManager registered live overlay with LiveViewService")

