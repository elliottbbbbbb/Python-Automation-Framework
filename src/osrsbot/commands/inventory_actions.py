"""
Inventory Actions - CQRS Command for inventory interactions.

Handles:
- Clicking inventory slots (config-based and template-detected)
- Dropping items (shift-drop and right-click)
- Batch operations (drop all except, drop until empty)
- Opening inventory tab

Responsibilities:
- Execute inventory write operations
- Coordinate resolution (template-first, config fallback)
- Anti-ban integration (timing, tracking)
"""

import logging
import random
import time
from typing import Any, Optional

import keyboard
import pyautogui

from osrsbot.constants import INVENTORY, INVENTORY_ACTIONS
from osrsbot.services.mouse_service import MouseService, MovementStyle
from osrsbot.utils.coordinate_helpers import CoordinateResolver
from osrsbot.utils.timing_helpers import TimingHelper

logger = logging.getLogger(__name__)


class InventoryActions:
    """
    Inventory action commands.

    Focused on inventory manipulation operations.
    """

    def __init__(
        self,
        mouse: MouseService,
        coord_resolver: CoordinateResolver,
        timing: TimingHelper,
        anti_ban_service: Optional[Any] = None,
    ):
        self.mouse = mouse
        self.coords = coord_resolver
        self.timing = timing
        self.anti_ban = anti_ban_service

    def click_slot(self, slot_num: int, move_style: MovementStyle = "curved") -> bool:
        """
        Click inventory slot (1-28) using template detection with config fallback.

        Args:
            slot_num: Slot number (1-28)
            move_style: Mouse movement style

        Returns:
            True if clicked successfully
        """
        if not 1 <= slot_num <= INVENTORY.total_slots:
            logger.error(f"Invalid slot: {slot_num}. Must be 1-{INVENTORY.total_slots}")
            return False

        # Resolve coordinates (template-first, config fallback)
        pos = self.coords.resolve_inventory_slot(slot_num)
        if not pos:
            logger.error(f"Failed to resolve slot {slot_num}")
            return False

        rel_x, rel_y = pos
        abs_x, abs_y = self.coords.to_absolute(rel_x, rel_y)

        logger.debug(
            f"Clicking slot {slot_num} at ({rel_x}, {rel_y}) -> ({abs_x}, {abs_y})"
        )

        return self.mouse.click_at(
            abs_x,
            abs_y,
            move_style=move_style,
            speed_multiplier=self.timing.get_mouse_speed_multiplier(),
        )

    def ensure_open(self) -> bool:
        """
        Ensure inventory tab is open.

        Returns:
            True if inventory is open or successfully opened
        """
        # Try to click inventory tab button
        button_pos = self.coords.resolve_ui_button("inventory_tab", force_detect=True)
        if button_pos:
            rel_x, rel_y = button_pos
            abs_x, abs_y = self.coords.to_absolute(rel_x, rel_y)

            success = self.mouse.click_at(
                abs_x, abs_y, speed_multiplier=self.timing.get_mouse_speed_multiplier()
            )
            if success:
                self.timing.wait("short")
                return True
            else:
                logger.warning("Failed to click inventory tab")
                return False

        # Try alternative inventory button
        button_pos = self.coords.resolve_ui_button(
            "inventory_button", force_detect=True
        )
        if button_pos:
            rel_x, rel_y = button_pos
            abs_x, abs_y = self.coords.to_absolute(rel_x, rel_y)

            success = self.mouse.click_at(
                abs_x, abs_y, speed_multiplier=self.timing.get_mouse_speed_multiplier()
            )
            if success:
                self.timing.wait("short")
                return True

        # Fallback: press ESC
        logger.warning("Inventory tab not found, pressing ESC as fallback")
        pyautogui.press("escape")
        self.timing.wait("short")
        return True

    def drop_item(self, slot: int, shift_drop: bool = False) -> bool:
        """
        Drop item from inventory slot.

        Args:
            slot: Slot number (1-28)
            shift_drop: Use shift-drop (requires RuneLite plugin)

        Returns:
            True if dropped successfully
        """
        if not 1 <= slot <= INVENTORY.total_slots:
            logger.error(f"Invalid slot: {slot}. Must be 1-{INVENTORY.total_slots}")
            return False

        # Resolve slot position (template-first, config fallback)
        pos = self.coords.resolve_inventory_slot(slot)
        if not pos:
            return False

        rel_x, rel_y = pos
        abs_x, abs_y = self.coords.to_absolute(rel_x, rel_y)

        if shift_drop:
            # Shift-drop method
            keyboard.press("shift")
            time.sleep(random.uniform(*INVENTORY_ACTIONS.shift_drop_key_delay))

            self.mouse.click_at(
                abs_x,
                abs_y,
                move_style="curved",
                speed_multiplier=self.timing.get_mouse_speed_multiplier(),
            )

            time.sleep(random.uniform(*INVENTORY_ACTIONS.shift_drop_key_delay))
            keyboard.release("shift")

            delay = random.uniform(*INVENTORY_ACTIONS.shift_drop_delay_range)
            if self.anti_ban:
                delay *= self.anti_ban.get_timing_variance()
            time.sleep(delay)
        else:
            # Right-click drop
            pyautogui.rightClick(abs_x, abs_y)
            time.sleep(random.uniform(*INVENTORY_ACTIONS.right_click_delay))

            drop_offset_y = random.uniform(*INVENTORY_ACTIONS.drop_menu_offset_y)
            pyautogui.click(abs_x, abs_y + drop_offset_y)

            delay = random.uniform(*INVENTORY_ACTIONS.drop_delay_range)
            if self.anti_ban:
                delay *= self.anti_ban.get_timing_variance()
            time.sleep(delay)

        logger.debug(
            f"Dropped item from slot {slot} ({
                'shift-drop' if shift_drop else 'right-click'})"
        )

        if self.anti_ban:
            self.anti_ban.record_action(f"drop_slot_{slot}")

        return True

    def drop_all_except(self, keep_slots: Optional[list[int]] = None) -> int:
        """
        Drop all items except specified slots (randomized order).

        Args:
            keep_slots: List of slot numbers to keep (1-28)

        Returns:
            Number of items dropped
        """
        if keep_slots is None:
            keep_slots = []

        all_slots = list(range(1, INVENTORY.total_slots + 1))
        drop_slots = [slot for slot in all_slots if slot not in keep_slots]
        random.shuffle(drop_slots)

        dropped = 0
        for slot in drop_slots:
            # Small chance of anti-ban misclick
            if random.random() < INVENTORY_ACTIONS.misclick_chance:
                wrong_slot = random.choice([s for s in drop_slots if s != slot])
                logger.debug(f"Anti-ban: Misclick on slot {wrong_slot}")
                # Just move mouse there, don't actually click
                pos = self.coords.resolve_inventory_slot(wrong_slot)
                if pos:
                    abs_x, abs_y = self.coords.to_absolute(pos[0], pos[1])
                    pyautogui.moveTo(
                        abs_x,
                        abs_y,
                        duration=random.uniform(
                            *INVENTORY_ACTIONS.misclick_movement_duration
                        ),
                    )
                    time.sleep(random.uniform(*INVENTORY_ACTIONS.misclick_delay_range))

            if self.drop_item(slot, shift_drop=False):
                dropped += 1

        logger.info(f"Dropped {dropped} items (kept slots: {keep_slots})")
        return dropped

    def drop_until_empty_slots(
        self, target_empty: int, keep_slots: Optional[list[int]] = None
    ) -> int:
        """
        Drop items until we have N empty slots.

        Args:
            target_empty: Number of empty slots desired
            keep_slots: List of slot numbers to keep (1-28)

        Returns:
            Number of items dropped
        """
        if keep_slots is None:
            keep_slots = []

        total_slots = INVENTORY.total_slots
        current_filled = total_slots - 0  # TODO: Implement inventory detection
        current_empty = total_slots - current_filled

        if current_empty >= target_empty:
            logger.debug(
                f"Already have {current_empty} empty slots (target: {target_empty})"
            )
            return 0

        to_drop = target_empty - current_empty

        all_slots = list(range(1, INVENTORY.total_slots + 1))
        drop_slots = [slot for slot in all_slots if slot not in keep_slots]
        random.shuffle(drop_slots)

        dropped = 0
        for slot in drop_slots[:to_drop]:
            if self.drop_item(slot, shift_drop=False):
                dropped += 1

        logger.info(f"Dropped {dropped} items to reach {target_empty} empty slots")
        return dropped
