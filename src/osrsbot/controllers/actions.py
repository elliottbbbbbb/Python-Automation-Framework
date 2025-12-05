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
from typing import Optional, Tuple

from osrsbot.services.mouse_service import MouseService, MovementStyle
from osrsbot.services.screen_service import ScreenService
from osrsbot.core.game_interface import GameInterface
from osrsbot.models.config import Config

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
        config: Config
    ):
        """
        Initialize game actions.

        Args:
            mouse: MouseService instance
            screen: ScreenService instance
            interface: GameInterface for window bounds
            config: Configuration instance
        """
        self.mouse = mouse
        self.screen = screen
        self.interface = interface
        self.config = config

    def wait(self, timing_type: str) -> None:
        delay = self.config.get("timings", timing_type, default=1.0)

        if not isinstance(delay, (int, float)):
            logger.warning(f"Invalid timing for '{timing_type}', using 1.0s")
            delay = 1.0

        time.sleep(float(delay))

    def _to_absolute(self, x: int, y: int) -> Tuple[int, int]:
        """
        Convert relative coords to absolute, refreshing window bounds first.

        Args:
            x: X coordinate relative to window
            y: Y coordinate relative to window

        Returns:
            (abs_x, abs_y) absolute screen coordinates
        """
        # Refresh bounds from interface and update screen service
        bounds = self.interface.get_bounds()
        self.screen.set_window_bounds(*bounds)
        return self.screen.relative_to_absolute(x, y)

    def click_inventory_slot(
        self,
        slot_num: int,
        move_style: MovementStyle = "curved"
    ) -> bool:
        if not 1 <= slot_num <= 28:
            logger.error(f"Invalid slot: {slot_num}, must be 1-28")
            return False

        coord = self.config.get("coordinates", "inventory", f"slot_{slot_num}")

        if not coord or "x" not in coord or "y" not in coord:
            logger.error(f"No coordinates for slot {slot_num}")
            return False

        x, y = coord["x"], coord["y"]
        abs_x, abs_y = self._to_absolute(x, y)

        logger.debug(f"Clicking inventory slot {slot_num} at relative ({x}, {y}) -> absolute ({abs_x}, {abs_y})")
        return self.mouse.click_at(abs_x, abs_y, move_style=move_style)

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
            tolerance = self.config.get("tolerances", "color_match", default=10)

        # Refresh window bounds BEFORE taking screenshot
        bounds = self.interface.get_bounds()
        self.screen.set_window_bounds(*bounds)

        match = self.screen.find_color(hex_color, tolerance, region)
        logger.debug(f"Found match: {match}")
        if not match:
            logger.debug(f"Color '{color_name}' ({hex_color}) not found")
            return False
        # This is where we go from relative coordinates to click -> absolute coordinates
        # Otherwise we click out of bounds. The position of the OSRS window is updated for each new click.
        abs_x, abs_y = self._to_absolute(match.x, match.y)
        logger.debug(f"Found '{color_name}' at relative ({match.x}, {match.y}) -> absolute ({abs_x}, {abs_y})")
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
        logger.debug(f"Clicking coordinate {coord_path} at relative ({x}, {y}) -> absolute ({abs_x}, {abs_y})")
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
        for _ in range(2):
            if not self.click_inventory_slot(2):
                logger.error("Failed to click Varrock teleport")
                return False
            self.wait("short")

        self.wait("teleport")
        return True

    def teleport_item(self, item_color_name: str) -> bool:
        for _ in range(2):
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
