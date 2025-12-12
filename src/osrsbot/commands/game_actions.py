"""
GameActions - High-level game actions using service layer.

Provides game-specific operations that combine multiple services.
Uses MouseService, ScreenService, TemplateMatchService, etc.

Organization:
- Initialization: Setup with service dependencies
- Utility & Timing: Wait, coordinate conversion, tracking
- Inventory & UI Management: Slot clicking, inventory detection
- Core Clicking & Color Detection: Smart clicking, color-based actions
- Coordinate-Based Actions: Config-driven clicking
- Game-Specific Actions: Combat, items, movement
- Banking Actions: Deposit, search
- Food/Potion Actions: Eating, drinking

Command-Query Separation:
- GameActions = Commands (actions that change state)
- GameState = Queries (read-only state checks)
"""
import time
import random
import logging
import pyautogui
from typing import Optional, Tuple, Any

from osrsbot.services.mouse_service import MouseService, MovementStyle
from osrsbot.services.screen_service import ScreenService
from osrsbot.services.template_match_service import TemplateMatchService
from osrsbot.services.click_target_tracker import ClickTargetTracker
from osrsbot.core.game_interface import GameInterface
from osrsbot.models.config import Config
from osrsbot.constants import COLOR_DETECTION, GAME_TIMING, TARGET_SELECTION

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

    # ==================== Initialization ====================

    def __init__(
        self,
        mouse: MouseService,
        screen: ScreenService,
        interface: GameInterface,
        config: Config,
        template_service: Optional[TemplateMatchService] = None,
        anti_ban_service: Optional[Any] = None
    ):
        """
        Initialize game actions (Commands in CQRS).

        Args:
            mouse: MouseService instance
            screen: ScreenService instance
            interface: GameInterface for window bounds
            config: Configuration instance
            template_service: Optional TemplateMatchService for UI detection
            anti_ban_service: Optional AntiBanService for behavioral randomization

        Note:
            GameActions implements the Command side of CQRS (actions that change state).
            For reading game state, use GameState (Query side) directly.
        """
        self.mouse = mouse
        self.screen = screen
        self.interface = interface
        self.config = config
        self.template_service = template_service
        self.anti_ban = anti_ban_service
        self._target_tracker = ClickTargetTracker()

    # ==================== Utility & Timing ====================

    def wait(self, timing_type: str) -> None:
        delay = self.config.get("timings", timing_type, default=GAME_TIMING.default_wait)

        # Handle tuple/list ranges for variance (Phase 0 anti-detection)
        if isinstance(delay, (list, tuple)) and len(delay) == 2:
            min_delay, max_delay = delay
            actual_delay = random.uniform(float(min_delay), float(max_delay))
            logger.debug(f"Wait '{timing_type}': {actual_delay:.2f}s (range: {min_delay}-{max_delay}s)")
        elif isinstance(delay, (int, float)):
            actual_delay = float(delay)
        else:
            logger.warning(
                f"Invalid timing for '{timing_type}', "
                f"using {GAME_TIMING.default_wait}s"
            )
            actual_delay = GAME_TIMING.default_wait

        # Apply session variance if anti-ban enabled
        if self.anti_ban:
            variance = self.anti_ban.get_timing_variance()
            actual_delay *= variance
            logger.debug(f"Applied session variance ({variance:.3f}): {actual_delay:.2f}s")

        time.sleep(actual_delay)

        # Check for micro-break after delay
        if self.anti_ban and self.anti_ban.should_micro_break():
            self.anti_ban.execute_micro_break()

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

    def _get_player_position(self) -> Tuple[int, int]:
        """
        Get player position in relative window coordinates.

        In OSRS, the player is always at the center of the game window.

        Returns:
            (x, y) relative coordinates of player position
        """
        _, _, width, height = self.interface.get_bounds()
        return (width // 2, height // 2)

    def reset_click_tracking(self) -> None:
        """Clear click history, target locks, and blacklist."""
        self._target_tracker.reset()
        logger.debug("Click tracking reset")

    # ==================== Inventory & UI Management ====================

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

    # ==================== Core Clicking & Color Detection ====================

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

    def click_color_smart(
        self,
        color_name: str,
        player_position: Optional[Tuple[int, int]] = None,
        move_style: MovementStyle = "curved",
        tolerance: Optional[int] = None,
        enable_target_lock: bool = True,
        enable_stuck_detection: bool = True,
        enable_blacklist: bool = True,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> bool:
        """
        Intelligently click a color with distance-based selection, stuck detection,
        target locking, and blacklisting.

        Features:
        - Selects closest match to player position
        - Detects stuck clicking (3 attempts at same location)
        - Locks onto targets and follows them as they move
        - Temporarily blacklists inaccessible locations

        Args:
            color_name: Color name from config
            player_position: Player position (x, y) relative to window.
                           Defaults to window center if None.
            move_style: Mouse movement style
            tolerance: Color matching tolerance (uses config default if None)
            enable_target_lock: Enable target locking to follow moving NPCs
            enable_stuck_detection: Enable stuck detection and auto-blacklisting
            enable_blacklist: Enable blacklist filtering
            region: Optional search region (x, y, width, height)

        Returns:
            True if clicked successfully, False if no valid targets found
        """
        # Get color from config
        hex_color = self.config.get("colors", color_name)
        if not hex_color:
            logger.warning(f"Color '{color_name}' not in config")
            return False

        # Get tolerance from config if not specified
        if tolerance is None:
            tolerance = self.config.get(
                "tolerances", "color_match", default=COLOR_DETECTION.default_tolerance
            )
            # Ensure tolerance is always an int
            if tolerance is None:
                tolerance = COLOR_DETECTION.default_tolerance

        # Get player position (default to window center)
        if player_position is None:
            player_position = self._get_player_position()

        # Check for existing target lock
        search_region = region
        target_lock = None
        if enable_target_lock:
            target_lock = self._target_tracker.get_target_lock()
            if target_lock:
                # Search near last locked position
                logger.debug(
                    f"Target locked at ({target_lock.x}, {target_lock.y}), "
                    f"searching within {target_lock.search_radius}px"
                )
                # Create search region around locked target
                search_region = (
                    max(0, target_lock.x - target_lock.search_radius),
                    max(0, target_lock.y - target_lock.search_radius),
                    target_lock.search_radius * 2,
                    target_lock.search_radius * 2
                )

        # Find all color matches sorted by distance from player
        blacklist_checker = None
        if enable_blacklist:
            blacklist_checker = self._target_tracker.is_blacklisted

        matches_with_distance = self.screen.find_color_with_distance(
            hex_color=hex_color,
            reference_point=player_position,
            tolerance=tolerance,
            region=search_region,
            blacklist_checker=blacklist_checker
        )

        # Handle no matches found
        if not matches_with_distance:
            if target_lock:
                # Lock expired or target moved out of search radius
                logger.debug("No matches near locked target, clearing lock and retrying")
                self._target_tracker.clear_target_lock()
                # Retry without lock constraint
                return self.click_color_smart(
                    color_name=color_name,
                    player_position=player_position,
                    move_style=move_style,
                    tolerance=tolerance,
                    enable_target_lock=False,  # Disable lock for retry
                    enable_stuck_detection=enable_stuck_detection,
                    enable_blacklist=enable_blacklist,
                    region=region
                )
            logger.debug(f"No valid targets found for '{color_name}'")
            return False

        # Select best target (closest to player)
        best_match, distance = matches_with_distance[0]
        logger.debug(
            f"Selected target at ({best_match.x}, {best_match.y}), "
            f"distance: {distance:.1f}px from player"
        )

        # Check for stuck clicking (before clicking)
        if enable_stuck_detection and self._target_tracker.is_stuck(
            window=TARGET_SELECTION.stuck_detection_window,
            threshold_pixels=TARGET_SELECTION.stuck_threshold_pixels
        ):
            # Blacklist this location and retry with next best target
            logger.warning(
                f"Stuck detected at ({best_match.x}, {best_match.y}), blacklisting"
            )
            self._target_tracker.blacklist_location(
                best_match.x,
                best_match.y,
                duration=TARGET_SELECTION.blacklist_duration,
                radius=TARGET_SELECTION.blacklist_radius
            )
            # Clear target lock since we're switching targets
            self._target_tracker.clear_target_lock()
            # Retry with blacklist active
            return self.click_color_smart(
                color_name=color_name,
                player_position=player_position,
                move_style=move_style,
                tolerance=tolerance,
                enable_target_lock=enable_target_lock,
                enable_stuck_detection=enable_stuck_detection,
                enable_blacklist=True,  # Ensure blacklist is active
                region=region
            )

        # Click the target
        abs_x, abs_y = self._to_absolute(best_match.x, best_match.y)
        logger.debug(
            f"Clicking '{color_name}' at relative ({best_match.x}, {best_match.y}) -> "
            f"absolute ({abs_x}, {abs_y})"
        )

        success = self.mouse.click_at(abs_x, abs_y, move_style=move_style)
        if not success:
            return False

        # Record click in history
        self._target_tracker.add_click(best_match.x, best_match.y)

        # Update target lock
        if enable_target_lock:
            self._target_tracker.set_target_lock(
                best_match.x,
                best_match.y,
                search_radius=TARGET_SELECTION.target_lock_search_radius,
                max_age=TARGET_SELECTION.target_lock_max_age
            )

        return True

    # ==================== Coordinate-Based Actions ====================

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

    # ==================== Game-Specific Actions ====================

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

    # ==================== Banking Actions ====================

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
