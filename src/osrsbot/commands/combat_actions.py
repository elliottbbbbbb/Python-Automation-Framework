"""
Combat Actions - CQRS Command for combat interactions.

Handles:
- Attacking NPCs (color-based and smart targeting)
- Eating food
- Drinking potions
- Prayer switching
- Combat utility methods

Responsibilities:
- Execute combat write operations
- Target selection and blacklisting
- Prayer tab management
- Anti-ban integration
"""

import logging
from typing import Any, Optional, Tuple

from osrsbot.constants import COLOR_DETECTION, MovementStyle, TARGET_SELECTION
from osrsbot.models.config import Config
from osrsbot.services.click_target_tracker import ClickTargetTracker
from osrsbot.services.mouse_service import MouseService
from osrsbot.services.screen_service import ScreenService
from osrsbot.utils.coordinate_helpers import CoordinateResolver
from osrsbot.utils.timing_helpers import TimingHelper

logger = logging.getLogger(__name__)


class CombatActions:
    """
    Combat action commands.

    Focused on combat operations (attacking, eating, prayers).
    """

    def __init__(
        self,
        mouse: MouseService,
        screen: ScreenService,
        coord_resolver: CoordinateResolver,
        timing: TimingHelper,
        config: Config,
        anti_ban_service: Optional[Any] = None,
    ):
        self.mouse = mouse
        self.screen = screen
        self.coords = coord_resolver
        self.timing = timing
        self.config = config
        self.anti_ban = anti_ban_service
        self._target_tracker = ClickTargetTracker()

    def attack_npc(self, npc_color_name: str, use_smart_targeting: bool = True) -> bool:
        """
        Attack NPC by color.

        Args:
            npc_color_name: Color name from config
            use_smart_targeting: Use distance-based targeting with blacklisting

        Returns:
            True if clicked successfully
        """
        logger.debug(f"Attacking NPC: {npc_color_name}")

        if use_smart_targeting:
            return self.click_color_smart(npc_color_name)
        else:
            return self.click_color(npc_color_name)

    def eat(self, food_color_name: str) -> bool:
        """
        Eat food by clicking inventory item.

        Args:
            food_color_name: Color name from config

        Returns:
            True if clicked successfully
        """
        logger.info("Eating food")
        return self.click_color(food_color_name)

    def drink_potion(self, potion_color_name: str) -> bool:
        """
        Drink potion by clicking inventory item.

        Args:
            potion_color_name: Color name from config

        Returns:
            True if clicked successfully
        """
        logger.info(f"Drinking potion: {potion_color_name}")
        return self.click_color(potion_color_name)

    def open_prayer_tab(self) -> bool:
        """
        Open prayer tab.

        Returns:
            True if opened successfully
        """
        logger.debug("Opening prayer tab")

        button_pos = self.coords.resolve_ui_button("prayer_tab", force_detect=True)
        if not button_pos:
            logger.error("Failed to detect prayer tab")
            return False

        rel_x, rel_y = button_pos
        abs_x, abs_y = self.coords.to_absolute(rel_x, rel_y)

        success = self.mouse.click_at(
            abs_x, abs_y, speed_multiplier=self.timing.get_mouse_speed_multiplier()
        )
        if success:
            self.timing.wait("short")

        return success

    def toggle_prayer(self, prayer_name: str) -> bool:
        """
        Toggle prayer on/off.

        Args:
            prayer_name: Prayer button name (e.g., "protect_from_melee")

        Returns:
            True if toggled successfully
        """
        logger.info(f"Toggling prayer: {prayer_name}")

        button_pos = self.coords.resolve_ui_button(prayer_name, force_detect=True)
        if not button_pos:
            logger.error(f"Failed to detect prayer: {prayer_name}")
            return False

        rel_x, rel_y = button_pos
        abs_x, abs_y = self.coords.to_absolute(rel_x, rel_y)

        success = self.mouse.click_at(
            abs_x, abs_y, speed_multiplier=self.timing.get_mouse_speed_multiplier()
        )
        if success:
            self.timing.wait("short")

        return success

    def activate_protect_from_melee(self) -> bool:
        """Activate Protect from Melee prayer."""
        return self.toggle_prayer("protect_from_melee")

    def activate_protect_from_magic(self) -> bool:
        """Activate Protect from Magic prayer."""
        return self.toggle_prayer("protect_from_magic")

    def activate_protect_from_ranged(self) -> bool:
        """Activate Protect from Ranged prayer."""
        return self.toggle_prayer("protect_from_ranged")

    def click_color(
        self,
        color_name: str,
        move_style: MovementStyle = "curved",
        tolerance: Optional[int] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> bool:
        """
        Click first occurrence of color.

        Args:
            color_name: Color name from config
            move_style: Mouse movement style
            tolerance: Color tolerance (default from config)
            region: Search region (x, y, w, h)

        Returns:
            True if color found and clicked
        """
        hex_color = self.config.get("colors", color_name)
        if not hex_color:
            logger.warning(f"Color '{color_name}' not in config")
            return False

        if tolerance is None:
            tolerance = self.config.get(
                "tolerances", "color_match", default=COLOR_DETECTION.default_tolerance
            )

        match = self.screen.find_color(hex_color, tolerance, region)
        if not match:
            logger.debug(f"Color '{color_name}' ({hex_color}) not found")
            return False

        abs_x, abs_y = self.coords.to_absolute(match.x, match.y)
        logger.debug(
            f"Found '{color_name}' at ({match.x}, {match.y}) -> ({abs_x}, {abs_y})"
        )

        return self.mouse.click_at(
            abs_x,
            abs_y,
            move_style=move_style,
            speed_multiplier=self.timing.get_mouse_speed_multiplier(),
        )

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
        """
        Click color with distance-based selection, stuck detection, and blacklisting.

        Selects nearest valid target to player position.
        Blacklists stuck locations automatically.

        Args:
            color_name: Color name from config
            player_position: Player position (x, y), defaults to center
            move_style: Mouse movement style
            tolerance: Color tolerance
            enable_stuck_detection: Enable stuck detection
            enable_blacklist: Enable location blacklisting
            region: Search region (if None and restrict_to_viewport=True, uses game viewport)
            restrict_to_viewport: If True, restricts search to game viewport (excludes UI)

        Returns:
            True if clicked successfully
        """
        hex_color = self.config.get("colors", color_name)
        if not hex_color:
            logger.warning(f"Color '{color_name}' not in config")
            return False

        if tolerance is None:
            tolerance = self.config.get(
                "tolerances", "color_match", default=COLOR_DETECTION.default_tolerance
            )
            if tolerance is None:
                tolerance = COLOR_DETECTION.default_tolerance

        if player_position is None:
            player_position = self.coords.get_player_position()

        # Use game viewport region if no specific region provided and restrict_to_viewport is True
        if region is None and restrict_to_viewport:
            region = self.screen.get_game_viewport_region()
            if region:
                logger.debug(f"Restricting search to game viewport: {region}")

        blacklist_checker = None
        if enable_blacklist:
            blacklist_checker = self._target_tracker.is_blacklisted

        matches_with_distance = self.screen.find_color_with_distance(
            hex_color=hex_color,
            reference_point=player_position,
            tolerance=tolerance,
            region=region,
            blacklist_checker=blacklist_checker,
        )

        if not matches_with_distance:
            logger.debug(f"No valid targets found for '{color_name}'")
            return False

        best_match, distance = matches_with_distance[0]
        logger.debug(
            f"Selected target at ({
                best_match.x}, {
                best_match.y}), distance: {
                distance:.1f}px"
        )

        # Check for stuck clicking
        if enable_stuck_detection and self._target_tracker.is_stuck(
            window=TARGET_SELECTION.stuck_detection_window,
            threshold_pixels=TARGET_SELECTION.stuck_threshold_pixels,
        ):
            logger.warning(
                f"Stuck detected at ({best_match.x}, {best_match.y}), blacklisting"
            )
            self._target_tracker.blacklist_location(
                best_match.x,
                best_match.y,
                duration=TARGET_SELECTION.blacklist_duration,
                radius=TARGET_SELECTION.blacklist_radius,
            )
            # Retry with blacklist
            return self.click_color_smart(
                color_name=color_name,
                player_position=player_position,
                move_style=move_style,
                tolerance=tolerance,
                enable_stuck_detection=enable_stuck_detection,
                enable_blacklist=True,
                region=region,
                restrict_to_viewport=restrict_to_viewport,
            )

        # Use instant movement for combat clicks to minimize delay
        # NPCs can move between detection and click, so speed matters
        combat_move_style = "instant" if move_style == "curved" else move_style

        abs_x, abs_y = self.coords.to_absolute(best_match.x, best_match.y)
        success = self.mouse.click_at(
            abs_x,
            abs_y,
            move_style=combat_move_style,
            speed_multiplier=self.timing.get_mouse_speed_multiplier(),
        )

        if success:
            self._target_tracker.add_click(best_match.x, best_match.y)

            if self.anti_ban:
                self.anti_ban.record_action(f"click_{color_name}")

        return success

    # NOTE: The good click templates do not currently work.
    def mark_last_attack_failed(self) -> None:
        """
        Mark the most recent attack click as failed.

        Call this when an attack click doesn't result in combat starting.
        Enables automatic blacklisting of inaccessible NPCs.
        """
        if self._target_tracker._click_history:
            last_click = self._target_tracker._click_history[-1]
            last_click.success = False
            logger.debug(
                f"Marked last click at ({last_click.x}, {last_click.y}) as failed"
            )

            # Check for repeated failures and blacklist if needed
            if self._target_tracker.has_repeated_failures(
                window=6, failure_threshold=3, radius_pixels=100
            ):
                logger.warning("Repeated attack failures detected, blacklisting area")
                self._target_tracker.blacklist_location(
                    last_click.x,
                    last_click.y,
                    duration=TARGET_SELECTION.blacklist_duration,
                    radius=TARGET_SELECTION.blacklist_radius,
                )

    def reset_targeting(self) -> None:
        """Clear target tracking and blacklist."""
        self._target_tracker.reset()
        logger.debug("Target tracking reset")
