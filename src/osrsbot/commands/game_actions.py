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

import logging
import random
import time
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

import cv2 as cv
import numpy as np
import pyautogui  # Fallback for keyboard input when KeyboardService not injected

from osrsbot.commands.bank_actions import BankActions
from osrsbot.commands.combat_actions import CombatActions
from osrsbot.commands.inventory_actions import InventoryActions
from osrsbot.constants import GAME_TIMING, LOOT_DETECTION, MINIMAP_NAVIGATION, MovementStyle

# Type hints only - actual instances injected by runner
if TYPE_CHECKING:
    from osrsbot.core.game_interface import GameInterface
    from osrsbot.models.config import Config
    from osrsbot.services.mouse_service import MouseService
    from osrsbot.services.screen_service import ScreenService
    from osrsbot.services.template_match_service import TemplateMatchService

logger = logging.getLogger(__name__)


class GameActions:
    """
    High-level game actions facade (BACKWARD COMPATIBILITY).

    Delegates to focused action modules while maintaining original API.
    """

    def __init__(
        self,
        mouse: "MouseService",
        screen: "ScreenService",
        interface: "GameInterface",
        config: "Config",
        template_service: Optional["TemplateMatchService"] = None,
        anti_ban_service: Optional[Any] = None,
        loot_detection_service: Optional[Any] = None,
        coord_resolver: Optional[Any] = None,
        timing_helper: Optional[Any] = None,
        walker: Optional[Any] = None,
        ui_manager: Optional[Any] = None,
        inventory_state: Optional[Any] = None,
        keyboard_service: Optional[Any] = None,
    ):
        """Initialize actions with services (all injected via DI)."""
        # Services (injected by runner)
        self.mouse = mouse
        self.screen = screen
        self.interface = interface
        self.config = config
        self.template_service = template_service
        self.anti_ban = anti_ban_service
        self.loot_detection = loot_detection_service
        self.walker = walker
        self.ui_manager = ui_manager
        self.keyboard = keyboard_service

        # Utility helpers (injected by runner)
        self.coord_resolver = coord_resolver
        self.timing = timing_helper

        # Initialize focused modules
        self.inventory = InventoryActions(
            mouse, self.coord_resolver, self.timing, anti_ban_service,
            inventory_state=inventory_state,
        )
        self.combat = CombatActions(
            mouse, screen, self.coord_resolver, self.timing, config, anti_ban_service
        )
        self.bank = BankActions(mouse, self.coord_resolver, self.timing)

    # ==================== Backward Compatibility Methods ====================
    # These delegate to new modules while maintaining exact same API

    # --- Timing/Wait (delegates to TimingHelper) ---
    def wait(self, timing_type: str) -> None:
        """Wait for configured duration with anti-ban variance."""
        self.timing.wait(timing_type)

    # --- Keyboard Methods (delegates to KeyboardService) ---
    def press_key(self, key: str, mode: str = "humanized") -> bool:
        """Press a key using KeyboardService (falls back to pyautogui)."""
        if self.keyboard:
            return self.keyboard.press(key, mode=mode)
        pyautogui.press(key)
        return True

    def type_text(self, text: str, mode: str = "humanized") -> bool:
        """Type text using KeyboardService (falls back to pyautogui)."""
        if self.keyboard:
            return self.keyboard.write(text, mode=mode)
        pyautogui.write(text, interval=0.05)
        return True

    def hotkey(self, *keys: str) -> bool:
        """Press key combination using KeyboardService (falls back to pyautogui)."""
        if self.keyboard:
            return self.keyboard.hotkey(*keys)
        pyautogui.hotkey(*keys)
        return True

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
        self, slot_num: int, move_style: MovementStyle = "curved"
    ) -> bool:
        """Click inventory slot (1-28) using config coords."""
        return self.inventory.click_slot(slot_num, move_style)

    def click_inventory_slot_detected(
        self,
        slot_num: int,
        move_style: MovementStyle = "curved",
        force_detect: bool = False,
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

    def drop_until_empty_slots(
        self, target_empty: int, keep_slots: Optional[list[int]] = None
    ) -> int:
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
        region: Optional[Tuple[int, int, int, int]] = None,
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
        region: Optional[Tuple[int, int, int, int]] = None,
        restrict_to_viewport: bool = True,
    ) -> bool:
        """Click color with smart targeting."""
        return self.combat.click_color_smart(
            color_name,
            player_position,
            move_style,
            tolerance,
            enable_stuck_detection,
            enable_blacklist,
            region,
            restrict_to_viewport,
        )

    def reset_click_tracking(self) -> None:
        """Reset target tracking."""
        self.combat.reset_targeting()

    def mark_last_attack_failed(self) -> None:
        """
        Mark the most recent attack click as failed.

        Call this when an attack click doesn't result in combat starting.
        Enables automatic blacklisting of inaccessible NPCs.
        """
        self.combat.mark_last_attack_failed()

    # --- Legacy methods that stay in facade (not refactored yet) ---

    def click_ui_button_detected(
        self,
        button_name: str,
        move_style: MovementStyle = "curved",
        force_detect: bool = False,
    ) -> bool:
        """Click UI button using template matching."""
        button_pos = self.coord_resolver.resolve_ui_button(button_name, force_detect)
        if not button_pos:
            return False

        rel_x, rel_y = button_pos
        abs_x, abs_y = self.coord_resolver.to_absolute(rel_x, rel_y)

        return self.mouse.click_at(
            abs_x,
            abs_y,
            move_style=move_style,
            speed_multiplier=self.timing.get_mouse_speed_multiplier(),
        )

    def pickup_loot(
        self,
        player_pos: Optional[Tuple[int, int]] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        tolerance: int = 30,
    ) -> bool:
        """Pickup nearest loot item (purple highlight from RuneLite)."""
        if self.loot_detection is None:
            logger.error("LootDetectionService not initialized - cannot pickup loot")
            return False

        if player_pos is None:
            player_pos = (
                MINIMAP_NAVIGATION.player_center_x,
                MINIMAP_NAVIGATION.player_center_y,
            )

        loot_pos = self.loot_detection.detect_nearest_loot(
            player_pos=player_pos, region=region, tolerance=tolerance
        )

        if not loot_pos:
            logger.debug("No loot found on screen")
            return False

        loot_x, loot_y = loot_pos
        abs_x, abs_y = self._to_absolute(loot_x, loot_y)

        logger.info(f"Picking up loot at ({loot_x}, {loot_y})")
        self.mouse.click_at(
            abs_x,
            abs_y,
            move_style="curved",
            speed_multiplier=self._get_mouse_speed_multiplier(),
        )

        # Use framework's wait system with pickup delay range
        self.wait(LOOT_DETECTION.pickup_delay_range)

        if self.anti_ban:
            self.anti_ban.record_action("pickup_loot")

        return True

    def click_coordinate(
        self, coord_path: Tuple[str, ...], move_style: MovementStyle = "curved"
    ) -> bool:
        """Click config coordinate path."""
        pos = self.coord_resolver.resolve_coordinate_path(*coord_path)
        if not pos:
            return False

        x, y = pos
        abs_x, abs_y = self._to_absolute(x, y)
        logger.debug(
            f"Clicking coordinate {coord_path} at relative ({x}, {y}) -> absolute ({abs_x}, {abs_y})"
        )
        return self.mouse.click_at(
            abs_x,
            abs_y,
            move_style=move_style,
            speed_multiplier=self._get_mouse_speed_multiplier(),
        )

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
        wait_time: Optional[float] = None,
    ) -> bool:
        """Walk N tiles in a direction on minimap (up/down/left/right)."""
        if direction not in MINIMAP_NAVIGATION.tile_movements:
            logger.error(f"Invalid direction: {direction}. Use up/down/left/right")
            return False

        dx, dy = MINIMAP_NAVIGATION.tile_movements[direction]
        target_x = MINIMAP_NAVIGATION.player_center_x + (dx * tiles)
        target_y = MINIMAP_NAVIGATION.player_center_y + (dy * tiles)

        logger.info(
            f"Walking {tiles} tile(s) {direction} to minimap ({target_x}, {target_y})"
        )

        abs_x, abs_y = self._to_absolute(target_x, target_y)
        success = self.mouse.click_at(
            abs_x,
            abs_y,
            move_style=move_style,
            speed_multiplier=self._get_mouse_speed_multiplier(),
        )

        if success:
            # Use framework's wait system
            if wait_time is not None:
                self.wait(wait_time)
            else:
                # Use default minimap wait with slight variance
                base_wait = MINIMAP_NAVIGATION.default_wait_time
                self.wait((base_wait * 0.9, base_wait * 1.1))

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
        if not self.click_template(
            "images/bot/ui_templates/bank_deposit_all_button.PNG", "bank_deposit_all_button", threshold=0.7
        ):
            logger.error("Failed to click bank deposit all")
            return False


        self.wait("medium")
        return True

    def bank_search(self, item_name: str) -> bool:
        """Search for item in bank."""
        if not item_name:
            logger.error("Item name cannot be empty")
            return False

        if not self.click_template(
            "templates/ui/bank_search_box.png", "bank search box", threshold=0.7
        ):
            logger.error("Failed to focus bank search box")
            return False

        self.wait("short")

        self.type_text(item_name)
        self.wait("short")

        return True

    def close_interface(self) -> bool:
        """Close interface with ESC (may not work with dialog boxes)."""
        self.press_key("escape")
        self.wait("short")
        return True

    def wait_for_color(
        self, color_name: str, timeout: float = 10.0, check_interval: float = 0.5
    ) -> bool:
        """Wait for color to appear on screen."""
        hex_color = self.config.get("colors", color_name)

        if not hex_color:
            logger.error(f"Color '{color_name}' not in config")
            return False

        match = self.screen.wait_for_color(
            hex_color, timeout=timeout, check_interval=check_interval
        )

        return match is not None

    def walk_to_world_coordinate(
        self, x: int, y: int, move_style: MovementStyle = "curved"
    ) -> bool:
        """Walk to world tile coordinates using advanced walker."""
        if not self.walker:
            logger.error(
                "WalkerService not initialized. Ensure Status Socket plugin is enabled."
            )
            return False

        return self.walker.walk_to(x, y, move_style=move_style)

    def walk_path(
        self, waypoints: List[Tuple[int, int]], move_style: MovementStyle = "random"
    ) -> bool:
        """Follow a predefined path of world coordinates."""
        if not self.walker:
            logger.error(
                "WalkerService not initialized. Ensure Status Socket plugin is enabled."
            )
            return False

        return self.walker.walk_path(waypoints, move_style=move_style)

    # ==================== Template Matching + Click Methods ====================
    # These use screen capture + OpenCV directly (no Queries layer import).
    # resolve_template_path is imported from utils layer.

    def _find_template_on_screen(
        self,
        template_paths: List[str],
        threshold: float = 0.7,
        label: str = "template",
    ) -> Optional[Tuple[int, int, float]]:
        """
        Find best matching template on screen using OpenCV.

        Args:
            template_paths: List of template image paths to try
            threshold: Minimum confidence threshold
            label: Name for logging

        Returns:
            (center_x, center_y, confidence) if found, None otherwise
        """
        from osrsbot.utils.template_helpers import resolve_template_path

        screenshot = self.screen.capture()
        if screenshot is None:
            logger.error("Failed to capture screenshot")
            return None

        img_np = cv.cvtColor(np.array(screenshot), cv.COLOR_RGB2BGR)

        best_center = None
        best_confidence = 0.0

        for path in template_paths:
            try:
                resolved = resolve_template_path(path)
                template = cv.imread(str(resolved), cv.IMREAD_COLOR)
                if template is None:
                    logger.warning(f"Failed to load template: {path}")
                    continue

                result = cv.matchTemplate(img_np, template, cv.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv.minMaxLoc(result)

                if max_val > best_confidence:
                    best_confidence = max_val
                    h, w = template.shape[:2]
                    best_center = (max_loc[0] + w // 2, max_loc[1] + h // 2)
            except Exception as e:
                logger.warning(f"Error matching template {path}: {e}")
                continue

        template_name = Path(template_paths[0]).name if template_paths else "unknown"
        logger.info(
            f"Template match '{label}': best_confidence={best_confidence:.3f}, "
            f"threshold={threshold}"
        )

        if best_center and best_confidence >= threshold:
            return (*best_center, best_confidence)

        return None

    def is_bank_open(self, search_button_template: str, threshold: float = 0.7) -> bool:
        """Check if bank interface is open by detecting the search button."""
        result = self._find_template_on_screen(
            [search_button_template], threshold, label="bank_open_check"
        )
        is_open = result is not None
        logger.debug(f"Bank open check: {'YES' if is_open else 'NO'}")
        return is_open

    def click_banker(
        self, banker_templates: List[str], threshold: float = 0.7
    ) -> bool:
        """Find and click banker using multiple templates."""
        result = self._find_template_on_screen(banker_templates, threshold, label="banker")

        if result is None:
            logger.warning(f"Banker not found (threshold: {threshold})")
            return False

        center_x, center_y, confidence = result
        logger.info(f"Found banker at ({center_x}, {center_y}) with confidence {confidence:.3f}")

        abs_x, abs_y = self._to_absolute(center_x, center_y)
        return self.mouse.click_at(
            abs_x, abs_y, move_style="curved", speed_multiplier=self._get_mouse_speed_multiplier()
        )

    def click_template(
        self, template_path, item_name: str, threshold: float = 0.7
    ) -> bool:
        """
        Find and click template on screen.

        Args:
            template_path: Single path (str) or multiple paths (List[str])
            item_name: Name for logging
            threshold: Match confidence (0.0-1.0)
        """
        paths = [template_path] if isinstance(template_path, str) else template_path

        if not isinstance(paths, list):
            logger.error(f"Invalid template_path type: {type(template_path)}")
            return False

        result = self._find_template_on_screen(paths, threshold, label=item_name)

        if result is None:
            logger.warning(f"{item_name} not found (threshold: {threshold})")
            return False

        center_x, center_y, confidence = result
        logger.info(f"Found {item_name} at ({center_x}, {center_y}) with confidence {confidence:.3f}")

        abs_x, abs_y = self._to_absolute(center_x, center_y)
        success = self.mouse.click_at(
            abs_x, abs_y, move_style="curved", speed_multiplier=self._get_mouse_speed_multiplier()
        )

        if success:
            logger.info(f"Successfully clicked {item_name}")
        else:
            logger.warning(f"Failed to click {item_name}")

        return success

    def bank_search_and_withdraw(
        self,
        search_button_template: str,
        item_template: str,
        item_name: str,
        search_text: str,
        item_threshold: float = 0.7,
    ) -> bool:
        """Search for an item in bank and withdraw it."""
        try:
            if not self.click_template(search_button_template, "bank search button", threshold=0.7):
                logger.error("Failed to find bank search button")
                return False

            self.wait("medium")

            logger.info(f"Typing '{search_text}' in bank search")
            self.type_text(search_text)
            self.wait("long")

            if not self.click_template(item_template, item_name, threshold=item_threshold):
                logger.error(f"Failed to find {item_name} in bank")
                self.press_key("escape")
                return False

            self.wait("medium")

            self.press_key("escape")
            self.wait("medium")

            return True

        except Exception as e:
            logger.error(f"Error in bank search and withdraw: {e}")
            try:
                self.press_key("escape")
            except Exception:
                pass
            return False

    # ==================== ANTI-BAN: Pre-Action Behaviors ====================

    def hover_template(
        self, template_path: str, template_name: str = "item"
    ) -> bool:
        """Hover mouse over template match without clicking."""
        try:
            result = self._find_template_on_screen(
                [template_path], threshold=0.7, label=template_name
            )
            if not result:
                logger.debug(f"Template '{template_name}' not found for hover")
                return False

            center_x, center_y, _ = result
            abs_x, abs_y = self.coord_resolver.to_absolute(center_x, center_y)

            hover_duration = random.uniform(0.3, 1.0)
            success = self.mouse.hover_at(abs_x, abs_y, duration=hover_duration)

            if success:
                logger.debug(f"Hovered over {template_name} for {hover_duration:.2f}s")

            return success

        except Exception as e:
            logger.error(f"Failed to hover over template '{template_name}': {e}")
            return False

    def open_skills_tab(self) -> bool:
        """
        Open the skills tab.

        Returns:
            True if opened successfully, False otherwise
        """
        logger.debug("Opening skills tab")

        try:
            button_pos = self.coord_resolver.resolve_ui_button("skills_tab", force_detect=True)
            if not button_pos:
                logger.error("Failed to detect skills tab button")
                return False

            rel_x, rel_y = button_pos
            abs_x, abs_y = self.coord_resolver.to_absolute(rel_x, rel_y)

            success = self.mouse.click_at(
                abs_x,
                abs_y,
                speed_multiplier=self.timing.get_mouse_speed_multiplier()
            )

            if success:
                self.timing.wait("short")
                logger.debug("Skills tab opened")

            return success

        except Exception as e:
            logger.error(f"Failed to open skills tab: {e}")
            return False

    def right_click_template(
        self, template_path: str, template_name: str = "item"
    ) -> bool:
        """
        Right-click on template match (for examine/cancel actions).

        Args:
            template_path: Path to template image
            template_name: Name for logging

        Returns:
            True if right-click successful, False if template not found
        """
        try:
            result = self._find_template_on_screen(
                [template_path], threshold=0.7, label=template_name
            )
            if not result:
                logger.debug(f"Template '{template_name}' not found for right-click")
                return False

            center_x, center_y, _ = result
            abs_x, abs_y = self.coord_resolver.to_absolute(center_x, center_y)

            success = self.mouse.click(abs_x, abs_y, button="right", variance=True)

            if success:
                logger.debug(f"Right-clicked on {template_name}")

            return success

        except Exception as e:
            logger.error(f"Failed to right-click template '{template_name}': {e}")
            return False

    def random_camera_movement(self) -> None:
        """
        Simulate looking around by moving mouse (simulates camera movement).

        Note: This is a simplified version. For actual camera control,
        you would use arrow keys or middle mouse drag.
        """
        logger.debug("ANTI-BAN: Random camera movement")

        try:
            current_x, current_y = pyautogui.position()

            # Move to random location near minimap area
            minimap_x = random.randint(600, 750)
            minimap_y = random.randint(50, 200)

            self.mouse.move_to(minimap_x, minimap_y, style="curved")
            time.sleep(random.uniform(0.3, 0.8))

            # Return near original position (with variance)
            variance_x = random.randint(-30, 30)
            variance_y = random.randint(-30, 30)
            self.mouse.move_to(
                current_x + variance_x,
                current_y + variance_y,
                style="curved"
            )

        except Exception as e:
            logger.error(f"Failed random camera movement: {e}")
