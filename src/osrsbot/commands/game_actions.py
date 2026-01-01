"""
Game Actions Facade - CQRS Command layer.

BACKWARD COMPATIBILITY FACADE:
This class maintains the original GameActions API while delegating
to focused modules (InventoryActions, CombatActions, etc.).

All existing bot code continues to work unchanged.

New code should prefer using focused modules directly:
- InventoryActions for inventory operations
- CombatActions for combat operations

Migration path:
1. Old code uses this facade (works unchanged)
2. New code uses focused modules
3. Eventually deprecate facade in favor of focused modules
"""

import time
import random
import logging
import pyautogui
from typing import Optional, Tuple, Any, List

from osrsbot.services.mouse_service import MouseService, MovementStyle
from osrsbot.services.screen_service import ScreenService
from osrsbot.services.template_match_service import TemplateMatchService
from osrsbot.core.game_interface import GameInterface
from osrsbot.models.config import Config
from osrsbot.constants import GAME_TIMING, MINIMAP_NAVIGATION

# Import new focused modules
from osrsbot.commands.inventory_actions import InventoryActions
from osrsbot.commands.combat_actions import CombatActions
from osrsbot.utils.coordinate_helpers import CoordinateResolver
from osrsbot.utils.timing_helpers import TimingHelper

logger = logging.getLogger(__name__)


class GameActions:
    """
    High-level game actions facade (BACKWARD COMPATIBILITY).

    Delegates to focused action modules while maintaining original API.
    """

    def __init__(
        self,
        mouse: MouseService,
        screen: ScreenService,
        interface: GameInterface,
        config: Config,
        template_service: Optional[TemplateMatchService] = None,
        anti_ban_service: Optional[Any] = None,
        loot_detection_service: Optional[Any] = None,
        walker: Optional[Any] = None
    ):
        """Initialize actions with services."""
        # Services (keep for backward compatibility and delegation)
        self.mouse = mouse
        self.screen = screen
        self.interface = interface
        self.config = config
        self.template_service = template_service
        self.anti_ban = anti_ban_service
        self.loot_detection = loot_detection_service
        self.walker = walker

        # Initialize shared utilities
        self.coord_resolver = CoordinateResolver(screen, config, template_service)
        self.timing = TimingHelper(config, anti_ban_service)

        # Initialize focused modules
        self.inventory = InventoryActions(
            mouse, self.coord_resolver, self.timing, anti_ban_service
        )
        self.combat = CombatActions(
            mouse, screen, self.coord_resolver, self.timing, config, anti_ban_service
        )

    # ==================== Backward Compatibility Methods ====================
    # These delegate to new modules while maintaining exact same API

    # --- Timing/Wait (delegates to TimingHelper) ---
    def wait(self, timing_type: str) -> None:
        """Wait for configured duration with anti-ban variance."""
        self.timing.wait(timing_type)

    # --- Private helper methods (keep for backward compatibility) ---
    def _to_absolute(self, x: int, y: int) -> Tuple[int, int]:
        """Convert relative coords to absolute screen coords."""
        return self.coord_resolver.to_absolute(x, y)

    def _get_player_position(self) -> Tuple[int, int]:
        """Get player position (center of window)."""
        return self.coord_resolver.get_player_position()

    def _get_mouse_speed_multiplier(self) -> float:
        """Get anti-ban mouse speed variance."""
        return self.timing.get_mouse_speed_multiplier()

    # --- Inventory Methods (delegate to InventoryActions) ---
    def click_inventory_slot(
        self,
        slot_num: int,
        move_style: MovementStyle = "curved"
    ) -> bool:
        """Click inventory slot (1-28) using config coords."""
        return self.inventory.click_slot(slot_num, move_style)

    def click_inventory_slot_detected(
        self,
        slot_num: int,
        move_style: MovementStyle = "curved",
        force_detect: bool = False
    ) -> bool:
        """Click inventory slot using template matching."""
        # Ensure inventory open first
        if not self.inventory.ensure_open():
            return False
        return self.inventory.click_slot(slot_num, move_style)

    def ensure_inventory_open(self) -> bool:
        """Ensure inventory is open."""
        return self.inventory.ensure_open()

    def drop_item(self, slot: int, shift_drop: bool = False) -> bool:
        """Drop item from inventory slot."""
        return self.inventory.drop_item(slot, shift_drop)

    def drop_all_except(self, keep_slots: Optional[list[int]] = None) -> int:
        """Drop all items except specified slots."""
        return self.inventory.drop_all_except(keep_slots)

    def drop_until_empty_slots(self, target_empty: int, keep_slots: Optional[list[int]] = None) -> int:
        """Drop items until we have N empty slots."""
        return self.inventory.drop_until_empty_slots(target_empty, keep_slots)

    # --- Combat Methods (delegate to CombatActions) ---
    def attack_npc(self, npc_color_name: str) -> bool:
        """Attack NPC by color."""
        return self.combat.attack_npc(npc_color_name)

    def eat_food(self, food_color_name: str) -> bool:
        """Eat food."""
        return self.combat.eat(food_color_name)

    def drink_potion(self, potion_color_name: str) -> bool:
        """Drink potion."""
        return self.combat.drink_potion(potion_color_name)

    def open_prayer_tab(self) -> bool:
        """Open prayer tab."""
        return self.combat.open_prayer_tab()

    def toggle_prayer(self, prayer_name: str) -> bool:
        """Toggle prayer on/off."""
        return self.combat.toggle_prayer(prayer_name)

    def activate_protect_from_melee(self) -> bool:
        """Activate Protect from Melee prayer."""
        return self.combat.activate_protect_from_melee()

    def activate_protect_from_magic(self) -> bool:
        """Activate Protect from Magic prayer."""
        return self.combat.activate_protect_from_magic()

    def activate_protect_from_ranged(self) -> bool:
        """Activate Protect from Ranged prayer."""
        return self.combat.activate_protect_from_ranged()

    def click_color(
        self,
        color_name: str,
        move_style: MovementStyle = "curved",
        tolerance: Optional[int] = None,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> bool:
        """Click color."""
        return self.combat.click_color(color_name, move_style, tolerance, region)

    def click_color_smart(
        self,
        color_name: str,
        player_position: Optional[Tuple[int, int]] = None,
        move_style: MovementStyle = "curved",
        tolerance: Optional[int] = None,
        enable_stuck_detection: bool = True,
        enable_blacklist: bool = True,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> bool:
        """Click color with smart targeting."""
        return self.combat.click_color_smart(
            color_name, player_position, move_style, tolerance,
            enable_stuck_detection, enable_blacklist, region
        )

    def reset_click_tracking(self) -> None:
        """Reset target tracking."""
        self.combat.reset_targeting()

    # --- Legacy methods that stay in facade (not refactored yet) ---

    def click_ui_button_detected(
        self,
        button_name: str,
        move_style: MovementStyle = "curved",
        force_detect: bool = False
    ) -> bool:
        """Click UI button using template matching."""
        button_pos = self.coord_resolver.resolve_ui_button(button_name, force_detect)
        if not button_pos:
            return False

        rel_x, rel_y = button_pos
        abs_x, abs_y = self.coord_resolver.to_absolute(rel_x, rel_y)

        return self.mouse.click_at(abs_x, abs_y, move_style=move_style, speed_multiplier=self.timing.get_mouse_speed_multiplier())

    def pickup_loot(
        self,
        player_pos: Optional[Tuple[int, int]] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        tolerance: int = 30
    ) -> bool:
        """Pickup nearest loot item (purple highlight from RuneLite)."""
        if self.loot_detection is None:
            logger.error("LootDetectionService not initialized - cannot pickup loot")
            return False

        if player_pos is None:
            player_pos = (654, 111)

        loot_pos = self.loot_detection.detect_nearest_loot(
            player_pos=player_pos,
            region=region,
            tolerance=tolerance
        )

        if not loot_pos:
            logger.debug("No loot found on screen")
            return False

        loot_x, loot_y = loot_pos
        abs_x, abs_y = self._to_absolute(loot_x, loot_y)

        logger.info(f"Picking up loot at ({loot_x}, {loot_y})")
        self.mouse.click_at(
            abs_x, abs_y,
            move_style="curved",
            speed_multiplier=self._get_mouse_speed_multiplier()
        )

        pickup_delay = random.uniform(0.5, 0.7)
        if self.anti_ban:
            pickup_delay *= self.anti_ban.get_timing_variance()
        time.sleep(pickup_delay)

        if self.anti_ban:
            self.anti_ban.record_action("pickup_loot")

        return True

    def click_coordinate(
        self,
        coord_path: Tuple[str, ...],
        move_style: MovementStyle = "curved"
    ) -> bool:
        """Click config coordinate path."""
        pos = self.coord_resolver.resolve_coordinate_path(*coord_path)
        if not pos:
            return False

        x, y = pos
        abs_x, abs_y = self._to_absolute(x, y)
        logger.debug(f"Clicking coordinate {coord_path} at relative ({x}, {y}) -> absolute ({abs_x}, {abs_y})")
        return self.mouse.click_at(abs_x, abs_y, move_style=move_style, speed_multiplier=self._get_mouse_speed_multiplier())

    def use_item(self, item_color_name: str) -> bool:
        """Use item by color."""
        return self.click_color(item_color_name)

    def walk_to_marker(self, marker_color_name: str) -> bool:
        """Walk to marker by color."""
        return self.click_color(marker_color_name)

    def click_minimap(self, location_name: str) -> bool:
        """Click minimap location from config."""
        return self.click_coordinate(("minimap", location_name))

    def walk_tiles(
        self,
        direction: str,
        tiles: int = 1,
        move_style: str = "random",
        wait_time: Optional[float] = None
    ) -> bool:
        """Walk N tiles in a direction on minimap (up/down/left/right)."""
        if direction not in MINIMAP_NAVIGATION.tile_movements:
            logger.error(f"Invalid direction: {direction}. Use up/down/left/right")
            return False

        dx, dy = MINIMAP_NAVIGATION.tile_movements[direction]
        target_x = MINIMAP_NAVIGATION.player_center_x + (dx * tiles)
        target_y = MINIMAP_NAVIGATION.player_center_y + (dy * tiles)

        logger.info(f"Walking {tiles} tile(s) {direction} to minimap ({target_x}, {target_y})")

        abs_x, abs_y = self._to_absolute(target_x, target_y)
        success = self.mouse.click_at(abs_x, abs_y, move_style=move_style, speed_multiplier=self._get_mouse_speed_multiplier())

        if success:
            actual_wait = wait_time if wait_time is not None else MINIMAP_NAVIGATION.default_wait_time
            variance = time.time() % 1.0
            total_wait = actual_wait + variance

            logger.debug(f"Waiting {total_wait:.2f}s after minimap click")
            time.sleep(total_wait)

            if self.anti_ban:
                self.anti_ban.record_action(f"walk_{direction}_{tiles}")

        return success

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
        """Teleport using item by color."""
        for _ in range(GAME_TIMING.teleport_double_click_count):
            if not self.use_item(item_color_name):
                logger.error(f"Failed to use {item_color_name}")
                return False
            self.wait("short")

        self.wait("teleport")
        return True

    def bank_deposit_all(self) -> bool:
        """Click bank deposit all button."""
        if not self.click_coordinate(("ui", "bank_deposit_all")):
            logger.error("Failed to click deposit all")
            return False

        self.wait("medium")
        return True

    def bank_search(self, item_name: str) -> bool:
        """Search for item in bank."""
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

    def close_interface(self) -> bool:
        """Close interface with ESC (may not work with dialog boxes)."""
        pyautogui.press('escape')
        self.wait("short")
        return True

    def wait_for_color(
        self,
        color_name: str,
        timeout: float = 10.0,
        check_interval: float = 0.5
    ) -> bool:
        """Wait for color to appear on screen."""
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

    def walk_to_world_coordinate(
        self,
        x: int,
        y: int,
        move_style: MovementStyle = "curved"
    ) -> bool:
        """Walk to world tile coordinates using advanced walker."""
        if not self.walker:
            logger.error("WalkerService not initialized. Ensure Status Socket plugin is enabled.")
            return False

        return self.walker.walk_to(x, y, move_style=move_style)

    def walk_path(
        self,
        waypoints: List[Tuple[int, int]],
        move_style: MovementStyle = "random"
    ) -> bool:
        """Follow a predefined path of world coordinates."""
        if not self.walker:
            logger.error("WalkerService not initialized. Ensure Status Socket plugin is enabled.")
            return False

        return self.walker.walk_path(waypoints, move_style=move_style)
