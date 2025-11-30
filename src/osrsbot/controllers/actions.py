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
from typing import Dict, Any, Optional, Tuple

from osrsbot.services.mouse_service import MouseService, MovementStyle
from osrsbot.services.screen_service import ScreenService
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
        config: Config
    ):
        """
        Initialize game actions.

        Args:
            mouse: MouseService instance
            screen: ScreenService instance
            config: Configuration instance
        """
        self.mouse = mouse
        self.screen = screen
        self.config = config

    def wait(self, timing_type: str) -> None:
        """
        Wait for configured duration.

        Args:
            timing_type: Key from config["timings"]
        """
        delay = self.config.get("timings", timing_type, default=1.0)

        if not isinstance(delay, (int, float)):
            logger.warning(f"Invalid timing for '{timing_type}', using 1.0s")
            delay = 1.0

        time.sleep(float(delay))

    def click_slot(
        self,
        slot_num: int,
        move_style: MovementStyle = "curved"
    ) -> bool:
        """
        Click an inventory slot (backward compatible with old API).

        Args:
            slot_num: Slot number (1-28)
            move_style: How to move mouse to slot

        Returns:
            True if successful
        """
        return self.click_inventory_slot(slot_num, move_style)

    def click_inventory_slot(
        self,
        slot_num: int,
        move_style: MovementStyle = "curved"
    ) -> bool:
        """
        Click an inventory slot.

        Args:
            slot_num: Slot number (1-28)
            move_style: How to move mouse to slot

        Returns:
            True if successful
        """
        if not 1 <= slot_num <= 28:
            logger.error(f"Invalid slot: {slot_num}, must be 1-28")
            return False

        coord = self.config.get("coordinates", "inventory", f"slot_{slot_num}")

        if not coord or "x" not in coord or "y" not in coord:
            logger.error(f"No coordinates for slot {slot_num}")
            return False

        x, y = coord["x"], coord["y"]

        logger.debug(f"Clicking inventory slot {slot_num} at ({x}, {y})")
        return self.mouse.click_at(x, y, move_style=move_style)

    def click_color(
        self,
        color_name: str,
        move_style: MovementStyle = "curved",
        tolerance: Optional[int] = None,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> bool:
        """
        Find and click a color from config.

        Args:
            color_name: Name of color in config["colors"]
            move_style: How to move to target
            tolerance: Color match tolerance (uses config default if None)
            region: Optional region to search in

        Returns:
            True if color found and clicked
        """
        hex_color = self.config.get("colors", color_name)

        if not hex_color:
            logger.warning(f"Color '{color_name}' not in config")
            return False

        if tolerance is None:
            tolerance = self.config.get("tolerances", "color_match", default=10)

        match = self.screen.find_color(hex_color, tolerance, region)

        if not match:
            logger.debug(f"Color '{color_name}' ({hex_color}) not found")
            return False

        logger.debug(f"Found '{color_name}' at ({match.x}, {match.y})")
        return self.mouse.click_at(match.x, match.y, move_style=move_style)

    def click_coordinate(
        self,
        coord_path: Tuple[str, ...],
        move_style: MovementStyle = "curved"
    ) -> bool:
        """
        Click a coordinate from config.

        Args:
            coord_path: Path to coordinate (e.g., ("ui", "bank_deposit_all"))
            move_style: How to move to target

        Returns:
            True if successful
        """
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
        return self.mouse.click_at(x, y, move_style=move_style)

    def click_coord(self, coord: dict, button: str = 'left') -> bool:
        """
        Click using config coordinate dict (backward compatible).

        Args:
            coord: Dictionary with 'x' and 'y' keys
            button: Mouse button to use

        Returns:
            True if successful
        """
        if not coord or "x" not in coord or "y" not in coord:
            logger.error("Invalid coordinate dict")
            return False

        x, y = coord["x"], coord["y"]
        return self.mouse.click_at(x, y, button=button)

    def use_item(self, item_color_name: str) -> bool:
        """
        Click an item in inventory by its outline color.

        Args:
            item_color_name: Name of item color in config

        Returns:
            True if item found and clicked
        """
        return self.click_color(item_color_name)

    def attack(self, npc_color_name: str) -> bool:
        """
        Attack an NPC by its outline color (backward compatible).

        Args:
            npc_color_name: Name of NPC color in config

        Returns:
            True if NPC found and clicked
        """
        return self.attack_npc(npc_color_name)

    def attack_npc(self, npc_color_name: str) -> bool:
        """
        Attack an NPC by its outline color.

        Args:
            npc_color_name: Name of NPC color in config

        Returns:
            True if NPC found and clicked
        """
        logger.debug(f"Attacking NPC: {npc_color_name}")
        return self.click_color(npc_color_name)

    def walk_marker(self, marker_color_name: str) -> bool:
        """
        Walk to a tile marker (backward compatible).

        Args:
            marker_color_name: Name of marker color in config

        Returns:
            True if marker found and clicked
        """
        return self.walk_to_marker(marker_color_name)

    def walk_to_marker(self, marker_color_name: str) -> bool:
        """
        Walk to a tile marker.

        Args:
            marker_color_name: Name of marker color in config

        Returns:
            True if marker found and clicked
        """
        return self.click_color(marker_color_name)

    def click_minimap(self, location_name: str) -> bool:
        """
        Click a location on minimap from config.

        Args:
            location_name: Name of minimap location

        Returns:
            True if successful
        """
        return self.click_coordinate(("minimap", location_name))

    def teleport_ge(self) -> bool:
        """
        Use Varrock teleport tab (backward compatible).

        Double-clicks to handle RuneLite menu behavior.
        """
        return self.teleport_varrock()

    def teleport_varrock(self) -> bool:
        """
        Use Varrock teleport tab (slot 2).

        Double-clicks to handle RuneLite menu behavior.
        """
        for _ in range(2):
            if not self.click_inventory_slot(2):
                logger.error("Failed to click Varrock teleport")
                return False
            self.wait("short")

        self.wait("teleport")
        return True

    def teleport_item(self, item_color_name: str) -> bool:
        """
        Teleport using an item (like mythical cape, ardy cloak).

        Args:
            item_color_name: Color name of teleport item

        Returns:
            True if successful
        """
        for _ in range(2):
            if not self.use_item(item_color_name):
                logger.error(f"Failed to use {item_color_name}")
                return False
            self.wait("short")

        self.wait("teleport")
        return True

    def teleport_myth_cape(self) -> bool:
        """Teleport using mythical cape (backward compatible)."""
        return self.teleport_item("mythical_cape")

    def teleport_ardy(self) -> bool:
        """Teleport using Ardougne cloak (backward compatible)."""
        return self.teleport_item("ardy_cloak")

    def deposit_all(self) -> bool:
        """
        Click the 'Deposit All' button in bank (backward compatible).
        """
        return self.bank_deposit_all()

    def bank_deposit_all(self) -> bool:
        """Click the 'Deposit All' button in bank."""
        if not self.click_coordinate(("ui", "bank_deposit_all")):
            logger.error("Failed to click deposit all")
            return False

        self.wait("medium")
        return True

    def bank_search(self, item_name: str) -> bool:
        """
        Search for an item in bank.

        Args:
            item_name: Name to type in search box

        Returns:
            True if successful
        """
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

    def eat(self, food_color_name: str) -> bool:
        """
        Eat food from inventory (backward compatible).

        Args:
            food_color_name: Color name of food item

        Returns:
            True if food found and eaten
        """
        return self.eat_food(food_color_name)

    def eat_food(self, food_color_name: str) -> bool:
        """
        Eat food from inventory.

        Args:
            food_color_name: Color name of food item

        Returns:
            True if food found and eaten
        """
        logger.info("Eating food")
        return self.use_item(food_color_name)

    def drink_potion(self, potion_color_name: str) -> bool:
        """
        Drink a potion from inventory.

        Args:
            potion_color_name: Color name of potion

        Returns:
            True if potion found and drunk
        """
        logger.info(f"Drinking potion: {potion_color_name}")
        return self.use_item(potion_color_name)

    def close_interface(self) -> bool:
        """Close current interface with ESC key."""
        pyautogui.press('escape')
        self.wait("short")
        return True

    def wait_for_color(
        self,
        color_name: str,
        timeout: float = 10.0,
        check_interval: float = 0.5
    ) -> bool:
        """
        Wait for a color to appear.

        Args:
            color_name: Name of color in config
            timeout: Maximum seconds to wait
            check_interval: Seconds between checks

        Returns:
            True if color appeared
        """
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
