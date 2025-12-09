"""
GameActions - High-level game actions using service layer.

This is where you write game-specific actions like:
- Banking
- Teleporting
- Attacking NPCs
- Using items

Each action uses the appropriate services (MouseService, ScreenService, etc.)
"""
import time
import logging
import pyautogui
from typing import Optional, Tuple, TYPE_CHECKING

from osrsbot.services.mouse_service import MouseService, MovementStyle
from osrsbot.services.screen_service import ScreenService
from osrsbot.services.template_match_service import TemplateMatchService
from osrsbot.core.game_interface import GameInterface
from osrsbot.models.config import Config
from osrsbot.constants import COLOR_DETECTION, GAME_TIMING

if TYPE_CHECKING:
    from osrsbot.models.state import GameState

logger = logging.getLogger(__name__)


class GameActions:
    """
    High-level game actions that combine services.

    This layer provides game-specific operations that encapsulate
    multiple service calls and domain logic. For state queries,
    use the GameState service directly.

    Command-Query Separation:
    - GameActions = Commands (actions that change state)
    - GameState = Queries (read-only state checks)
    """

    def __init__(
        self,
        mouse: MouseService,
        screen: ScreenService,
        interface: GameInterface,
        config: Config,
        state: Optional["GameState"] = None,
        template_service: Optional[TemplateMatchService] = None
    ):
        """
        Initialize game actions.

        Args:
            mouse: MouseService instance
            screen: ScreenService instance
            interface: GameInterface for window bounds
            config: Configuration instance
            state: Optional GameState instance (for inventory access)
            template_service: Optional TemplateMatchService for UI detection
        """
        self.mouse = mouse
        self.screen = screen
        self.interface = interface
        self.config = config
        self.state = state
        self.template_service = template_service

    def wait(self, timing_type: str) -> None:
        delay = self.config.get("timings", timing_type, default=GAME_TIMING.default_wait)

        if not isinstance(delay, (int, float)):
            logger.warning(
                f"Invalid timing for '{timing_type}', "
                f"using {GAME_TIMING.default_wait}s"
            )
            delay = GAME_TIMING.default_wait

        time.sleep(float(delay))

    def _to_absolute(self, x: int, y: int) -> Tuple[int, int]:
        """
        Convert relative coords to absolute screen coordinates.

        Args:
            x: X coordinate relative to window
            y: Y coordinate relative to window

        Returns:
            (abs_x, abs_y) absolute screen coordinates
        """
        return self.screen.relative_to_absolute(x, y)

    def click_inventory_slot(
        self,
        slot_num: int,
        move_style: MovementStyle = "curved"
    ) -> bool:
        """
        Click an inventory slot using config coordinates.

        Args:
            slot_num: Slot number (1-28)
            move_style: Mouse movement style

        Returns:
            True if clicked, False on error
        """
        coord = self.config.get("coordinates", "inventory", f"slot_{slot_num}")

        if not coord or "x" not in coord or "y" not in coord:
            logger.error(
                f"No coordinates for slot {slot_num} in config"
            )
            return False

        x, y = coord["x"], coord["y"]
        abs_x, abs_y = self._to_absolute(x, y)

        logger.debug(
            f"Clicking inventory slot {slot_num} at "
            f"relative ({x}, {y}) -> absolute ({abs_x}, {abs_y})"
        )
        return self.mouse.click_at(abs_x, abs_y, move_style=move_style)

    def click_inventory_slot_detected(
        self,
        slot_num: int,
        move_style: MovementStyle = "curved",
        force_detect: bool = False
    ) -> bool:
        """
        Click an inventory slot using template matching detection.

        This method detects the inventory grid position dynamically using
        OpenCV template matching, then calculates the slot position mathematically.
        It will attempt to open the inventory if it's closed.

        Args:
            slot_num: Slot number (1-28)
            move_style: Mouse movement style
            force_detect: Force re-detection even if cached

        Returns:
            True if clicked, False on error
        """
        if not self.template_service:
            logger.error(
                "TemplateMatchService not available. "
                "Use click_inventory_slot() for config-based clicking."
            )
            return False

        if not 1 <= slot_num <= 28:
            logger.error(f"Invalid slot number: {slot_num}. Must be 1-28.")
            return False

        if not self.ensure_inventory_open():
            logger.error("Could not open inventory")
            return False

        img_gray = self.screen.capture_grayscale()
        if img_gray is None:
            logger.error("Failed to capture screenshot")
            return False

        detected = self.template_service.detect_grid(
            "inventory",
            img_gray,
            force=force_detect
        )
        if not detected:
            logger.error("Failed to detect inventory grid")
            return False

        # Convert 1-indexed slot number to 0-indexed array position
        position = self.template_service.get_slot_position("inventory", slot_num - 1)
        if not position:
            logger.error(f"Failed to get position for slot {slot_num}")
            return False

        rel_x, rel_y = position
        abs_x, abs_y = self._to_absolute(rel_x, rel_y)

        logger.debug(
            f"Clicking inventory slot {slot_num} (detected) at "
            f"relative ({rel_x}, {rel_y}) -> absolute ({abs_x}, {abs_y})"
        )

        return self.mouse.click_at(abs_x, abs_y, move_style=move_style)

    def click_ui_button_detected(
        self,
        button_name: str,
        move_style: MovementStyle = "curved",
        force_detect: bool = False
    ) -> bool:
        """
        Click a UI button using template matching detection.

        This method detects UI buttons (prayer, run, logout, etc.) dynamically
        using OpenCV template matching.

        Args:
            button_name: Name of button to click (e.g., "prayer_button", "run_button")
            move_style: Mouse movement style
            force_detect: Force re-detection even if cached

        Returns:
            True if clicked, False on error
        """
        if not self.template_service:
            logger.error("TemplateMatchService not available")
            return False

        img_gray = self.screen.capture_grayscale()
        if img_gray is None:
            logger.error("Failed to capture screenshot")
            return False

        detected = self.template_service.detect_button(
            button_name,
            img_gray,
            force=force_detect
        )
        if not detected:
            logger.error(f"Failed to detect button: {button_name}")
            return False

        position = self.template_service.get_button_position(button_name)
        if not position:
            logger.error(f"Failed to get position for button: {button_name}")
            return False

        rel_x, rel_y = position
        abs_x, abs_y = self._to_absolute(rel_x, rel_y)

        logger.debug(
            f"Clicking button '{button_name}' (detected) at "
            f"relative ({rel_x}, {rel_y}) -> absolute ({abs_x}, {abs_y})"
        )

        return self.mouse.click_at(abs_x, abs_y, move_style=move_style)

    def ensure_inventory_open(self, max_attempts: int = 3) -> bool:
        """
        Ensure the inventory interface is open.

        Attempts to detect the inventory. If not detected, clicks the inventory
        button or presses ESC to close other interfaces, then retries.

        Args:
            max_attempts: Maximum number of attempts to open inventory

        Returns:
            True if inventory is open/detected, False otherwise
        """
        if not self.template_service:
            logger.warning(
                "TemplateMatchService not available. "
                "Cannot verify inventory state."
            )
            return True  # Assume open when detection unavailable

        for attempt in range(max_attempts):
            img_gray = self.screen.capture_grayscale()
            if img_gray is None:
                logger.error(f"Failed to capture screenshot (attempt {attempt + 1})")
                continue

            detected = self.template_service.detect_grid(
                "inventory",
                img_gray,
                force=True
            )
            if detected:
                logger.debug(f"Inventory detected on attempt {attempt + 1}")
                return True

            logger.debug(
                f"Inventory not detected (attempt {attempt + 1}/{max_attempts}). "
                "Attempting to open..."
            )

            # First attempt: click inventory button if available, else press ESC
            # Subsequent attempts: always press ESC to close competing interfaces
            if attempt == 0:
                if self.template_service.has_button("inventory_button"):
                    self.click_ui_button_detected("inventory_button", force_detect=True)
                else:
                    pyautogui.press('escape')
            else:
                pyautogui.press('escape')

            self.wait("short")

        logger.error(f"Failed to open inventory after {max_attempts} attempts")
        return False

    def click_color(
        self,
        color_name: str,
        move_style: MovementStyle = "curved",
        tolerance: Optional[int] = None,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> bool:
        hex_color = self.config.get("colors", color_name)

        if not hex_color:
            logger.warning(f"Color '{color_name}' not in config")
            return False

        if tolerance is None:
            tolerance = self.config.get(
                "tolerances", "color_match", default=COLOR_DETECTION.default_tolerance
            )

        match = self.screen.find_color(hex_color, tolerance, region)
        logger.debug(f"Found match: {match}")
        if not match:
            logger.debug(f"Color '{color_name}' ({hex_color}) not found")
            return False

        abs_x, abs_y = self._to_absolute(match.x, match.y)
        logger.debug(
            f"Found '{color_name}' at relative ({match.x}, {match.y}) -> "
            f"absolute ({abs_x}, {abs_y})"
        )
        return self.mouse.click_at(abs_x, abs_y, move_style=move_style)

    def click_coordinate(
        self,
        coord_path: Tuple[str, ...],
        move_style: MovementStyle = "curved"
    ) -> bool:
        current = self.config.get("coordinates")

        if not current:
            logger.error("No coordinates in config")
            return False

        for key in coord_path:
            current = current.get(key, {}) if isinstance(current, dict) else {}
            if not current:
                logger.error(f"Coordinate path {coord_path} not found")
                return False

        if "x" not in current or "y" not in current:
            logger.error(f"Invalid coordinate at {coord_path}")
            return False

        x, y = current["x"], current["y"]
        abs_x, abs_y = self._to_absolute(x, y)
        logger.debug(
            f"Clicking coordinate {coord_path} at relative ({x}, {y}) -> "
            f"absolute ({abs_x}, {abs_y})"
        )
        return self.mouse.click_at(abs_x, abs_y, move_style=move_style)

    def use_item(self, item_color_name: str) -> bool:
        return self.click_color(item_color_name)

    def attack_npc(self, npc_color_name: str) -> bool:
        logger.debug(f"Attacking NPC: {npc_color_name}")
        return self.click_color(npc_color_name)

    def walk_to_marker(self, marker_color_name: str) -> bool:
        return self.click_color(marker_color_name)

    def click_minimap(self, location_name: str) -> bool:
        return self.click_coordinate(("minimap", location_name))

    def teleport_varrock(self) -> bool:
        """Double-clicks to handle RuneLite menu behavior."""
        for _ in range(GAME_TIMING.teleport_double_click_count):
            if not self.click_inventory_slot(2):
                logger.error("Failed to click Varrock teleport")
                return False
            self.wait("short")

        self.wait("teleport")
        return True

    def teleport_item(self, item_color_name: str) -> bool:
        for _ in range(GAME_TIMING.teleport_double_click_count):
            if not self.use_item(item_color_name):
                logger.error(f"Failed to use {item_color_name}")
                return False
            self.wait("short")

        self.wait("teleport")
        return True

    def bank_deposit_all(self) -> bool:
        if not self.click_coordinate(("ui", "bank_deposit_all")):
            logger.error("Failed to click deposit all")
            return False

        self.wait("medium")
        return True

    def bank_search(self, item_name: str) -> bool:
        if not item_name:
            logger.error("Item name cannot be empty")
            return False

        if not self.click_coordinate(("ui", "bank_search")):
            logger.error("Failed to click bank search")
            return False

        self.wait("short")

        pyautogui.write(item_name)
        self.wait("short")

        return True

    def eat_food(self, food_color_name: str) -> bool:
        logger.info("Eating food")
        return self.use_item(food_color_name)

    def drink_potion(self, potion_color_name: str) -> bool:
        logger.info(f"Drinking potion: {potion_color_name}")
        return self.use_item(potion_color_name)

    def close_interface(self) -> bool:
        pyautogui.press('escape')
        self.wait("short")
        return True

    def wait_for_color(
        self,
        color_name: str,
        timeout: float = 10.0,
        check_interval: float = 0.5
    ) -> bool:
        hex_color = self.config.get("colors", color_name)

        if not hex_color:
            logger.error(f"Color '{color_name}' not in config")
            return False

        match = self.screen.wait_for_color(
            hex_color,
            timeout=timeout,
            check_interval=check_interval
        )

        return match is not None
