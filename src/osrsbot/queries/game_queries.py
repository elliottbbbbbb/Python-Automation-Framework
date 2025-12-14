import logging
import os
import pytesseract
from typing import Optional, Any, TYPE_CHECKING, Tuple, Dict

from osrsbot.services.ocr_service import OCRService, OCRRegion
from osrsbot.models.config import Config
from osrsbot.utils.color_helpers import hex_to_rgb
from osrsbot.constants import COLOR_DETECTION

if TYPE_CHECKING:
    from osrsbot.services.screen_service import ScreenService
    from osrsbot.services.template_match_service import TemplateMatchService
    from osrsbot.queries.inventory_queries import InventoryState

logger = logging.getLogger(__name__)


class GameState:
    """
    Manages game state checks like HP and combat status.

    Uses OCRService for reading stats from the game UI.
    """

    def __init__(
            self,
            interface: Any,
            config: Config,
            ocr_service: Any,
            screen_service: Optional["ScreenService"] = None,
            template_service: Optional[Any] = None) -> None:
        self.interface = interface
        self.config = config
        self.ocr_service = ocr_service
        self.screen: Optional["ScreenService"] = screen_service
        self.template_service = template_service

        # Initialize inventory detection if services available
        if template_service and screen_service:
            from osrsbot.queries.inventory_queries import InventoryState
            self.inventory: Optional["InventoryState"] = InventoryState(
                template_service, screen_service, config
            )
            logger.debug("InventoryState initialized successfully")
        else:
            self.inventory: Optional["InventoryState"] = None
            logger.debug("InventoryState not initialized (missing services)")

        self._hp_ttl = float(self.config.get("ocr", "hp_ttl", default=0.5))
        self._ocr_window_size = self.config.get(
            "ocr", "window_size", default=5)

    def _verify_click_color_is_red(self, button_name: str) -> bool:
        """
        Verify that a detected click is actually red (not yellow).

        After grayscale template matching detects a click, this checks
        the actual color to distinguish red clicks (interaction) from
        yellow clicks (movement).

        Args:
            button_name: Name of the button that was detected

        Returns:
            True if the detected region contains red color, False if yellow/other
        """
        if not self.template_service:
            return False

        if not self.screen:
            return False

        button = self.template_service.get_button(button_name)
        if not button or not button.visible or not button.element:
            return False

        # Sample a few pixels from the detected click region
        center_x, center_y = button.element.center

        # Sample pixels around the center of the detected click
        # Use a larger sampling area since the click cursor is very small
        sample_offsets = [
            (0, 0),    # Center
            (-3, -3), (-3, 0), (-3, 3),  # Left column
            (0, -3), (0, 3),              # Top and bottom center
            (3, -3), (3, 0), (3, 3),      # Right column
            (-5, 0), (5, 0), (0, -5), (0, 5)  # Far edges
        ]
        red_pixels = 0
        yellow_pixels = 0

        for dx, dy in sample_offsets:
            x = center_x + dx
            y = center_y + dy

            try:
                color = self.screen.get_pixel_color(x, y, relative=True)

                # Red click: high red, low green, low blue
                # Yellow click: high red, high green, low blue
                r, g, b = color

                # Log the actual color values for debugging
                logger.info(f"Sampled pixel at ({x}, {y}): RGB({r}, {g}, {b})")

                # Distinguish red from yellow by checking green channel
                if r > COLOR_DETECTION.red_channel_min and b < COLOR_DETECTION.blue_channel_max:
                    if g < COLOR_DETECTION.green_channel_max_red:
                        red_pixels += 1
                        logger.info(
                            f"  → Classified as RED "
                            f"(r={r} > {COLOR_DETECTION.red_channel_min}, "
                            f"g={g} < {COLOR_DETECTION.green_channel_max_red}, "
                            f"b={b} < {COLOR_DETECTION.blue_channel_max})"
                        )
                    elif g > COLOR_DETECTION.green_channel_min_yellow:
                        yellow_pixels += 1
                        logger.info(
                            f"  → Classified as YELLOW "
                            f"(r={r} > {COLOR_DETECTION.red_channel_min}, "
                            f"g={g} > {COLOR_DETECTION.green_channel_min_yellow}, "
                            f"b={b} < {COLOR_DETECTION.blue_channel_max})"
                        )
                else:
                    logger.info(f"  → Not red or yellow (r={r}, g={g}, b={b})")

            except Exception as e:
                logger.debug(f"Error sampling pixel at ({x}, {y}): {e}")
                continue

        # Click cursor is very small - use majority vote
        # If we found more red than yellow = red click (combat/interaction)
        # If we found more yellow than red = yellow click (movement/miss)
        # If we found only red and no yellow = definitely red click
        # If we found neither = background only, reject
        if red_pixels > yellow_pixels:
            is_red = True  # Mostly red pixels = combat click
        else:
            is_red = False  # Mostly yellow, or no color data

        logger.info(
            f"Color verification for {button_name}: "
            f"red_pixels={red_pixels}, yellow_pixels={yellow_pixels}, is_red={is_red}"
        )
        return is_red

    def click_success(self, tries: int = 3) -> bool:
        """
        Check if a click was detected using template matching.

        Retries across multiple frames and uses majority vote.
        Uses red click templates to detect successful interactions.

        Args:
            tries: Number of frames to check (default 3)

        Returns:
            True if click template detected in majority of frames, False otherwise
        """
        if not self.template_service:
            logger.warning("Template service not available for click check")
            return False

        if not self.screen:
            logger.warning("Screen service not available for click check")
            return False

        # We have 4 different red click templates to handle variations
        buttons = ["good_click_1", "good_click_2", "good_click_3", "good_click_4"]
        detections = 0

        for attempt in range(tries):
            # Refresh image each try
            img_gray = self.screen.capture_grayscale()
            if img_gray is None:
                logger.debug(f"Click check attempt {attempt + 1}: Failed to capture screenshot")
                continue

            # Check if ANY of the red click templates match
            for button_name in buttons:
                if self.template_service.detect_button(button_name, img_gray, force=True):
                    detections += 1
                    logger.debug(f"Click check attempt {attempt + 1}: Click template '{button_name}' detected")
                    break

            # Early exit if we already have majority
            if detections > tries // 2:
                logger.info(f"Click success confirmed ({detections}/{attempt + 1} frames)")
                return True

        # Return True if majority of attempts detected a click
        success = detections > tries // 2
        logger.info(f"Click check complete: {detections}/{tries} frames detected click (success={success})")
        return success

    def in_combat(self) -> bool:
        """
        Check if player is in combat by detecting the combat indicator.

        Uses template matching to detect the NPC HP bar in the top left.
        Falls back to pixel-based detection if template matching unavailable.

        Returns:
            True if in combat, False otherwise
        """
        # Try template matching first (preferred method)
        if self.template_service:
            img_gray = self.screen.capture_grayscale()
            if img_gray is None:
                logger.warning("Failed to capture screenshot for combat check")
                return False

            # Detect combat indicator template
            detected = self.template_service.detect_button(
                "combat_indicator",
                img_gray,
                force=True  # Always fresh detection (combat changes rapidly)
            )

            # Validate position - combat indicator should be in top-left corner
            # Expected position is around (24-30, 65-85)
            if detected:
                button = self.template_service.get_button("combat_indicator")
                if button and button.element:
                    x, y = button.element.center
                    # Only accept detections in the top-left area
                    if x > 100 or y > 120:
                        logger.debug(f"Combat indicator detected at invalid position ({x}, {y}), ignoring")
                        return False
                    logger.debug(f"Combat indicator detected at valid position ({x}, {y})")
                    return True

            return detected

        # Fallback to pixel-based detection (legacy method)
        logger.debug("Template service unavailable, using pixel-based combat check")
        coord = self.config.get("coordinates", "checks", "combat_indicator")
        if not coord:
            logger.error("combat check coordinates were not found in config.")
            return False

        if not self.screen:
            logger.error("ScreenService not available for combat check")
            return False

        color = self.screen.get_pixel_color(
            coord['x'], coord['y'], relative=True)

        combat_green_hex = self.config.get("colors", "combat_indicator_green")
        combat_red_hex = self.config.get("colors", "combat_indicator_red")

        if combat_green_hex and combat_red_hex:
            combat_colors = [
                hex_to_rgb(combat_green_hex),
                hex_to_rgb(combat_red_hex)
            ]
        else:
            logger.warning(
                "Combat indicator colors not in config, using fallback")
            combat_colors = [(7, 139, 54), (99, 21, 19)]

        tolerance = self.config.get("tolerances", "color_match", default=10)

        return any(
            all(abs(color[i] - cc[i]) <= tolerance for i in range(3))
            for cc in combat_colors
        )

    def get_hp(self, force: bool = False) -> Optional[int]:
        """
        Args:
            force: If True, bypass cache and force new OCR reading

        Returns:
            Current HP value or None if OCR failed
        """
        hp_region_config = self.config.get("coordinates", "ocr", "hp_region")
        if not hp_region_config:
            logger.error("hp_region not in config")
            return None

        hp_region = OCRRegion(
            x=hp_region_config["x"],
            y=hp_region_config["y"],
            width=hp_region_config["width"],
            height=hp_region_config["height"],
            name="hp"
        )

        hp = self.ocr_service.read_number(
            region=hp_region,
            min_value=1,
            max_value=99,
            smooth=not force,
            window_size=self._ocr_window_size,
            ttl=self._hp_ttl if not force else 0
        )

        if hp is None:
            logger.debug("get_hp: OCR returned None")
        else:
            logger.debug(f"get_hp: {hp}")

        return hp

    def get_health(self, force: bool = False) -> Optional[int]:
        """Alias for get_hp() for backward compatibility."""
        return self.get_hp(force=force)

    def get_prayer(self, force: bool = False) -> Optional[int]:
        """
        Args:
            force: If True, bypass cache and force new OCR reading

        Returns:
            Current prayer points or None if OCR failed
        """
        prayer_region_config = self.config.get(
            "coordinates", "ocr", "prayer_region")
        if not prayer_region_config:
            logger.warning("prayer_region not in config")
            return None

        prayer_region = OCRRegion(
            x=prayer_region_config["x"],
            y=prayer_region_config["y"],
            width=prayer_region_config["width"],
            height=prayer_region_config["height"],
            name="prayer"
        )

        prayer = self.ocr_service.read_number(
            region=prayer_region,
            min_value=0,
            max_value=99,
            smooth=not force,
            window_size=self._ocr_window_size,
            ttl=self._hp_ttl if not force else 0
        )

        if prayer is None:
            logger.debug("get_prayer: OCR returned None")
        else:
            logger.debug(f"get_prayer: {prayer}")

        return prayer

    def get_run_energy(self, force: bool = False) -> Optional[int]:
        """
        Args:
            force: If True, bypass cache and force new OCR reading

        Returns:
            Current run energy (0-100) or None if OCR failed
        """
        run_region_config = self.config.get(
            "coordinates", "ocr", "run_energy_region")
        if not run_region_config:
            logger.warning("run_energy_region not in config")
            return None

        run_region = OCRRegion(
            x=run_region_config["x"],
            y=run_region_config["y"],
            width=run_region_config["width"],
            height=run_region_config["height"],
            name="run_energy"
        )

        energy = self.ocr_service.read_number(
            region=run_region,
            min_value=0,
            max_value=100,
            smooth=not force,
            window_size=self._ocr_window_size,
            ttl=self._hp_ttl if not force else 0
        )

        if energy is None:
            logger.debug("get_run_energy: OCR returned None")
        else:
            logger.debug(f"get_run_energy: {energy}")

        return energy

    def inventory_full(self, threshold: int = 27) -> bool:
        """
        Check if inventory has >= threshold items.

        Delegates to InventoryState for detection. Falls back to legacy
        implementation if InventoryState unavailable (backward compatibility).

        Args:
            threshold: Number of items to consider "full" (default 27 out of 28)

        Returns:
            True if inventory has >= threshold items, False otherwise
        """
        # Use new InventoryState system if available
        if self.inventory:
            try:
                return self.inventory.is_full(threshold=threshold)
            except Exception as e:
                logger.error(f"InventoryState check failed: {e}", exc_info=True)
                # Fall through to legacy method

        # Legacy fallback (backward compatibility)
        if not self.template_service:
            logger.warning("TemplateMatchService not available, assuming inventory full")
            return True  # Conservative: assume full if can't check

        if not self.screen:
            logger.warning("ScreenService not available, assuming inventory full")
            return True  # Conservative: assume full if can't check

        try:
            # Capture screenshot for template matching
            img_gray = self.screen.capture_grayscale()

            # Detect inventory grid
            inventory_detected = self.template_service.detect_grid("inventory", img_gray)

            if not inventory_detected:
                logger.debug("Inventory grid not detected, assuming inventory full")
                return True  # Conservative: assume full if can't detect

            # Count filled inventory slots by checking pixel color
            # Purple item outlines indicate items in slots
            filled_slots = 0
            grid = self.template_service.get_grid("inventory")

            if not grid or not grid.visible:
                logger.debug("Inventory grid not visible, assuming inventory full")
                return True

            # Check each of the 28 inventory slots for items
            purple_hex = self.config.get("colors", "purple_item_outline", default="#ff00ff")
            purple_rgb = hex_to_rgb(purple_hex)
            tolerance = self.config.get("tolerances", "color_match", default=10)

            for slot_idx in range(28):  # 28 inventory slots
                element = grid.get_element(slot_idx)
                if element:
                    # Check center pixel of slot for purple outline
                    pixel_color = self.screen.get_pixel_color(
                        element.center_x,
                        element.center_y,
                        relative=True
                    )

                    # Check if pixel matches purple (item present)
                    if all(abs(pixel_color[i] - purple_rgb[i]) <= tolerance for i in range(3)):
                        filled_slots += 1

            is_full = filled_slots >= threshold
            logger.debug(f"Inventory check (legacy): {filled_slots}/28 slots filled (threshold: {threshold}, full: {is_full})")
            return is_full

        except Exception as e:
            logger.error(f"Error checking inventory_full: {e}", exc_info=True)
            return True  # Conservative: assume full on error

    # ==================== Debug/Diagnostic Methods ====================
    # These methods expose diagnostic capabilities for testing and debugging.
    # They bypass caching and provide direct access to underlying detection systems.

    def debug_get_viewport_dimensions(self) -> Optional[Tuple[int, int]]:
        """
        Get viewport dimensions for diagnostic purposes.

        Returns width and height of game window viewport.
        Used by test code to calculate game viewport region.

        Returns:
            (width, height) tuple or None if interface unavailable

        Example:
            >>> width, height = self.state.debug_get_viewport_dimensions()
            >>> viewport_region = (0, 0, int(width * 0.70), height)
        """
        try:
            _, _, width, height = self.interface.get_bounds()
            logger.debug(f"Viewport dimensions: {width}x{height}")
            return (width, height)
        except Exception as e:
            logger.error(f"Failed to get viewport dimensions: {e}")
            return None

    def debug_capture_screen(self, grayscale: bool = True) -> Optional[Any]:
        """
        Capture current screen for diagnostic purposes.

        Bypasses caching and provides direct screen capture capability.
        Used by test code to verify template detection.

        Args:
            grayscale: If True, return grayscale numpy array; if False, return PIL Image

        Returns:
            Grayscale numpy array, PIL Image, or None if capture fails

        Example:
            >>> img_gray = self.state.debug_capture_screen()
            >>> if img_gray is not None:
            >>>     # Perform custom analysis
        """
        if not self.screen:
            logger.warning("ScreenService not available for debug capture")
            return None

        try:
            if grayscale:
                img = self.screen.capture_grayscale()
                logger.debug(f"Debug screen capture: grayscale {'success' if img is not None else 'failed'}")
                return img
            else:
                img = self.screen.capture()
                logger.debug("Debug screen capture: color success")
                return img
        except Exception as e:
            logger.error(f"Debug screen capture failed: {e}")
            return None

    def debug_detect_inventory_grid(self, force: bool = True) -> bool:
        """
        Detect inventory grid for diagnostic purposes.

        Forces fresh template detection and returns success status.
        Used by test code to verify template matching system.

        Args:
            force: Force fresh detection (default True for diagnostics)

        Returns:
            True if inventory grid detected, False otherwise

        Example:
            >>> if self.state.debug_detect_inventory_grid():
            >>>     logger.info("Template matching working correctly")
        """
        if not self.template_service:
            logger.warning("TemplateMatchService not available for debug detection")
            return False

        if not self.screen:
            logger.warning("ScreenService not available for debug detection")
            return False

        try:
            img_gray = self.screen.capture_grayscale()
            if img_gray is None:
                logger.warning("Debug detection: screen capture failed")
                return False

            detected = self.template_service.detect_grid("inventory", img_gray, force=force)
            logger.debug(f"Debug inventory detection: {'detected' if detected else 'not found'}")
            return detected
        except Exception as e:
            logger.error(f"Debug inventory detection failed: {e}")
            return False

    def debug_get_inventory_grid_info(self) -> Optional[Dict[str, Any]]:
        """
        Get inventory grid information for diagnostic purposes.

        Returns detailed information about detected inventory grid.
        Used by test code to verify grid structure and element count.

        Returns:
            Dictionary with grid info or None if not available:
            {
                "visible": bool,
                "total_elements": int,
                "num_rows": int,
                "num_cols": int,
                "bounds": (x, y, width, height) or None
            }

        Example:
            >>> grid_info = self.state.debug_get_inventory_grid_info()
            >>> if grid_info and grid_info["visible"]:
            >>>     logger.info(f"Grid has {grid_info['total_elements']} elements")
        """
        if not self.template_service:
            logger.warning("TemplateMatchService not available")
            return None

        try:
            grid = self.template_service.get_grid("inventory")
            if not grid:
                logger.debug("Debug: No inventory grid available")
                return None

            info = {
                "visible": grid.visible,
                "total_elements": len(grid.elements),
                "num_rows": grid.num_rows,
                "num_cols": grid.num_cols,
                "bounds": None
            }

            if grid.element:
                info["bounds"] = (
                    grid.element.x,
                    grid.element.y,
                    grid.element.width,
                    grid.element.height
                )

            logger.debug(f"Debug grid info: visible={info['visible']}, elements={info['total_elements']}")
            return info
        except Exception as e:
            logger.error(f"Failed to get grid info: {e}")
            return None
