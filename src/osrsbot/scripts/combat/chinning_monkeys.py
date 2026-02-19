"""
Chinning Monkeys Bot - Maniacal Monkey AoE Training

Uses chinchompas or burst spells to AoE train on maniacal monkeys in MM2 caves.
Stacks monkeys by clicking 2 colored tile markers, then auto-retaliates.

Strategy:
1. Click tile 1 (stack tile) to lure monkeys
2. Click tile 2 (attack position) to group them
3. Attack once to start auto-retaliate
4. AFK while monitoring prayer
5. Re-stack every X seconds when monkeys spread out
6. Reset aggro after ~10 minutes

Setup Requirements:
1. RuneLite tile markers: 2 tiles for stacking (different colors recommended)
2. Protect from Melee prayer active
3. Auto-retaliate enabled
4. Chinchompas equipped OR burst/barrage runes in inventory
5. Prayer potions for extended trips
6. Minimap fully zoomed OUT (for consistent aggro reset walks)

Config colors:
- chinning_stack_tile_1: First stacking tile (e.g., cyan)
- chinning_stack_tile_2: Second stacking tile / attack position (e.g., pink)
"""

import logging
import random
import time
from enum import Enum
from typing import List, Optional, Tuple

from osrsbot.core.state_helpers import build_metadata_dict
from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_types import (
    StateExecutionContext,
    StateMetadata,
    StateResult,
    StateTransition,
)

logger = logging.getLogger(__name__)


class ChinningStates(Enum):
    """States for chinning monkeys bot."""

    IDLE = "idle"
    STACK_MONKEYS = "stack_monkeys"
    ATTACK = "attack"
    COMBAT_LOOP = "combat_loop"
    RESTACK = "restack"
    CHECK_PRAYER = "check_prayer"
    DRINK_PRAYER = "drink_prayer"
    RESET_AGGRO = "reset_aggro"
    RECOVERY = "recovery"


class ChinningMonkeysBot(StateMachineBot):
    """
    Maniacal monkey chinning/bursting bot.

    Uses colored tile markers to stack monkeys for AoE damage.
    Timer-based restacking ensures optimal XP rates.
    """

    def __init__(self, **kwargs):
        super().__init__(
            **kwargs,
            script_name="Chinning Monkeys",
            enable_exit_key=True,
            enable_status_ui=True,
        )

        # Config color keys (set in config.json)
        self.stack_tile_1_color = "chinning_stack_tile_1"
        self.stack_tile_2_color = "chinning_stack_tile_2"
        self.rope_color_key = "chinning_rope_color"

        # Aggro reset templates
        self.CAVE_ENTRANCE_TEMPLATE = "images/bot/chinning/cave_entrance.png"

        # Timing configuration
        self.RESTACK_INTERVAL = self.config.get("chinning", "restack_interval", default=120)  # seconds
        self.PRAYER_CHECK_INTERVAL = 30  # seconds
        self.AGGRO_RESET_INTERVAL = 10  # TESTING: 10 seconds (change back to 300 for production)
        self.MIN_PRAYER_THRESHOLD_LOW = 25  # Drink prayer pot below random(25-35)
        self.MIN_PRAYER_THRESHOLD_HIGH = 35

        # Prayer potion template (user's custom screenshot)
        self.PRAYER_POTION_TEMPLATE = "images/bot/items/prayer_potion.png"

        # Timer tracking
        self._last_stack_time: float = 0.0
        self._last_prayer_check_time: float = 0.0
        self._last_aggro_reset_time: float = 0.0
        self._combat_start_time: float = 0.0

        # State flags
        self._needs_restack: bool = False
        self._needs_prayer: bool = False
        self._needs_aggro_reset: bool = False
        self._initial_setup_done: bool = False

        # Stats
        self._restack_count: int = 0
        self._prayer_doses: int = 0
        self._aggro_resets: int = 0

        logger.info(
            f"ChinningMonkeysBot initialized: "
            f"restack_interval={self.RESTACK_INTERVAL}s, "
            f"prayer_check={self.PRAYER_CHECK_INTERVAL}s, "
            f"aggro_reset={self.AGGRO_RESET_INTERVAL}s"
        )

    # ==================== State Machine Configuration ====================

    def define_states(self) -> type[Enum]:
        return ChinningStates

    def define_transitions(self) -> List[StateTransition]:
        return [
            # Initial setup: IDLE -> STACK_MONKEYS
            StateTransition(ChinningStates.IDLE, ChinningStates.STACK_MONKEYS),

            # Stacking flow: STACK -> ATTACK -> COMBAT_LOOP
            StateTransition(ChinningStates.STACK_MONKEYS, ChinningStates.ATTACK),
            StateTransition(ChinningStates.ATTACK, ChinningStates.COMBAT_LOOP),

            # Combat loop exits based on conditions
            StateTransition(
                ChinningStates.COMBAT_LOOP, ChinningStates.RESTACK,
                condition=lambda: self._needs_restack,
            ),
            StateTransition(
                ChinningStates.COMBAT_LOOP, ChinningStates.CHECK_PRAYER,
                condition=lambda: self._needs_prayer,
            ),
            StateTransition(
                ChinningStates.COMBAT_LOOP, ChinningStates.RESET_AGGRO,
                condition=lambda: self._needs_aggro_reset,
            ),
            StateTransition(
                ChinningStates.COMBAT_LOOP, ChinningStates.COMBAT_LOOP,
                condition=lambda: not (self._needs_restack or self._needs_prayer or self._needs_aggro_reset),
            ),

            # Restack -> back to combat
            StateTransition(ChinningStates.RESTACK, ChinningStates.COMBAT_LOOP),

            # Prayer check -> drink if needed -> back to combat
            StateTransition(
                ChinningStates.CHECK_PRAYER, ChinningStates.DRINK_PRAYER,
                condition=lambda: self._needs_prayer,
            ),
            StateTransition(
                ChinningStates.CHECK_PRAYER, ChinningStates.COMBAT_LOOP,
                condition=lambda: not self._needs_prayer,
            ),
            StateTransition(ChinningStates.DRINK_PRAYER, ChinningStates.COMBAT_LOOP),

            # Aggro reset -> back to stacking
            StateTransition(ChinningStates.RESET_AGGRO, ChinningStates.STACK_MONKEYS),

            # Recovery
            StateTransition(ChinningStates.RECOVERY, ChinningStates.IDLE),
        ]

    def define_state_metadata(self) -> dict[Enum, StateMetadata]:
        return build_metadata_dict(
            ChinningStates,
            {
                ChinningStates.IDLE: {
                    "name": "Idle",
                    "description": "Initial setup and validation.",
                    "max_retries": 2,
                    "failover": ChinningStates.RECOVERY,
                },
                ChinningStates.STACK_MONKEYS: {
                    "name": "Stack Monkeys",
                    "description": "Click tile markers to stack monkeys.",
                    "max_retries": 3,
                    "timeout": 90.0,
                    "failover": ChinningStates.RECOVERY,
                },
                ChinningStates.ATTACK: {
                    "name": "Attack",
                    "description": "Initiate attack to start auto-retaliate.",
                    "max_retries": 2,
                    "timeout": 10.0,
                    "failover": ChinningStates.STACK_MONKEYS,
                },
                ChinningStates.COMBAT_LOOP: {
                    "name": "Combat Loop",
                    "description": "AFK combat with timer monitoring.",
                    "max_retries": 999,
                    "timeout": 3600.0,
                    "failover": ChinningStates.RECOVERY,
                },
                ChinningStates.RESTACK: {
                    "name": "Restack",
                    "description": "Re-stack monkeys that spread out.",
                    "max_retries": 3,
                    "timeout": 90.0,
                    "failover": ChinningStates.COMBAT_LOOP,
                },
                ChinningStates.CHECK_PRAYER: {
                    "name": "Check Prayer",
                    "description": "Check prayer points level.",
                    "max_retries": 1,
                    "failover": ChinningStates.COMBAT_LOOP,
                },
                ChinningStates.DRINK_PRAYER: {
                    "name": "Drink Prayer",
                    "description": "Drink prayer potion.",
                    "max_retries": 2,
                    "failover": ChinningStates.COMBAT_LOOP,
                },
                ChinningStates.RESET_AGGRO: {
                    "name": "Reset Aggro",
                    "description": "Walk away and back to reset aggro timer.",
                    "max_retries": 2,
                    "timeout": 60.0,
                    "failover": ChinningStates.RECOVERY,
                },
                ChinningStates.RECOVERY: {
                    "name": "Recovery",
                    "description": "Error recovery.",
                    "max_retries": 3,
                },
            },
        )

    def get_initial_state(self) -> Enum:
        return ChinningStates.IDLE

    # ==================== Helper Methods ====================

    def _find_color_center(
        self,
        hex_color: str,
        tolerance: int = 15,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> Optional[Tuple[int, int]]:
        """
        Find center point of all pixels matching a color.

        Returns centroid of all matching pixels for more accurate clicking.

        Args:
            hex_color: Target color as hex string (e.g., "#04A5FF")
            tolerance: Color matching tolerance
            region: Optional search region (x, y, width, height)

        Returns:
            (x, y) center coordinates, or None if no matches
        """
        matches = self.actions.screen.find_color(
            hex_color,
            tolerance=tolerance,
            region=region,
            find_all=True,
        )

        if not matches:
            return None

        total_x = sum(m.x for m in matches)
        total_y = sum(m.y for m in matches)
        center_x = total_x // len(matches)
        center_y = total_y // len(matches)

        return (center_x, center_y)

    def _click_tile_color(self, color_key: str, tolerance: int = 15) -> bool:
        """
        Find a colored tile marker and click it.

        Args:
            color_key: Config color key name (e.g., "chinning_stack_tile_1")
            tolerance: Color matching tolerance

        Returns:
            True if found and clicked, False if not found
        """
        hex_color = self.config.get("colors", color_key)
        if not hex_color:
            logger.warning(f"Color '{color_key}' not configured in config.json")
            return False

        viewport_region = self.state.get_game_viewport_region()
        center = self._find_color_center(hex_color, tolerance=tolerance, region=viewport_region)

        if center is None:
            logger.debug(f"Color {hex_color} ({color_key}) not found in viewport")
            return False

        cx, cy = center
        logger.info(f"Found tile {color_key} at ({cx}, {cy}), clicking...")

        abs_x, abs_y = self.actions.coord_resolver.to_absolute(cx, cy)
        self.actions.mouse.click_at(
            abs_x, abs_y,
            move_style="instant",
            speed_multiplier=0.1,  # Fast direct movement
        )
        return True

    def _get_prayer_points(self) -> Optional[int]:
        """Get current prayer points using OCR."""
        prayer = self.state.get_prayer(force=True)
        if prayer is None:
            logger.warning("Failed to read prayer points")
        return prayer

    def _needs_restack_check(self) -> bool:
        """Check if it's time to restack monkeys."""
        if self._last_stack_time == 0.0:
            return False
        elapsed = time.time() - self._last_stack_time
        return elapsed >= self.RESTACK_INTERVAL

    def _needs_prayer_check(self) -> bool:
        """Check if it's time to check prayer."""
        if self._last_prayer_check_time == 0.0:
            return True
        elapsed = time.time() - self._last_prayer_check_time
        return elapsed >= self.PRAYER_CHECK_INTERVAL

    def _needs_aggro_reset_check(self) -> bool:
        """Check if it's time to reset aggro (10 min timer)."""
        if self._last_aggro_reset_time == 0.0:
            return False
        elapsed = time.time() - self._last_aggro_reset_time
        return elapsed >= self.AGGRO_RESET_INTERVAL

    # ==================== State Handlers ====================

    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        """Validate setup and prepare for chinning."""
        logger.info("=" * 60)
        logger.info("[IDLE] Chinning Monkeys Bot starting...")
        logger.info("=" * 60)

        # Check config colors
        tile1_color = self.config.get("colors", self.stack_tile_1_color)
        tile2_color = self.config.get("colors", self.stack_tile_2_color)

        if not tile1_color:
            logger.error(f"IDLE: Stack tile 1 color '{self.stack_tile_1_color}' not configured!")
            return StateResult.FAILURE

        if not tile2_color:
            logger.error(f"IDLE: Stack tile 2 color '{self.stack_tile_2_color}' not configured!")
            return StateResult.FAILURE

        logger.info("-" * 60)
        logger.info("  CONFIGURATION SUMMARY")
        logger.info(f"  Stack tile 1:      {tile1_color}")
        logger.info(f"  Stack tile 2:      {tile2_color}")
        logger.info(f"  Aggro reset:       minimap click (ensure zoomed out)")
        logger.info(f"  Restack interval:  {self.RESTACK_INTERVAL}s")
        logger.info(f"  Prayer threshold:  {self.MIN_PRAYER_THRESHOLD_LOW}-{self.MIN_PRAYER_THRESHOLD_HIGH}")
        logger.info(f"  Aggro reset timer: {self.AGGRO_RESET_INTERVAL}s")
        logger.info("-" * 60)

        # Verify tiles are visible
        viewport_region = self.state.get_game_viewport_region()

        tile1_visible = self._find_color_center(tile1_color, tolerance=15, region=viewport_region)
        tile2_visible = self._find_color_center(tile2_color, tolerance=15, region=viewport_region)

        if not tile1_visible:
            logger.warning(f"IDLE: Stack tile 1 ({tile1_color}) not visible - make sure you're in position!")
        else:
            logger.info(f"IDLE: Stack tile 1 visible at {tile1_visible}")

        if not tile2_visible:
            logger.warning(f"IDLE: Stack tile 2 ({tile2_color}) not visible - make sure you're in position!")
        else:
            logger.info(f"IDLE: Stack tile 2 visible at {tile2_visible}")

        # Initialize timers
        current_time = time.time()
        self._last_aggro_reset_time = current_time
        self._combat_start_time = current_time

        logger.info("IDLE: Setup complete, starting stacking sequence...")
        return StateResult.SUCCESS

    def _handle_stack_monkeys(self, context: StateExecutionContext) -> StateResult:
        """Alternate between tile markers to stack monkeys (25 clicks)."""
        logger.info("[STACK_MONKEYS] Clicking tiles to stack monkeys...")

        # Stacking config
        TOTAL_CLICKS = 35  # total alternating clicks
        CLICK_INTERVAL = 0.35  # seconds between clicks

        click_count = 0
        current_tile = 1  # Start with tile 1

        while click_count < TOTAL_CLICKS:
            self._check_exit_requested()

            # Alternate between tiles
            if current_tile == 1:
                if self._click_tile_color(self.stack_tile_1_color):
                    click_count += 1
                    logger.debug(f"STACK_MONKEYS: Clicked tile 1 (click #{click_count})")
                else:
                    logger.warning("STACK_MONKEYS: Could not find stack tile 1!")
                    click_count += 1  # Still count to avoid infinite loop
                current_tile = 2
            else:
                if self._click_tile_color(self.stack_tile_2_color):
                    click_count += 1
                    logger.debug(f"STACK_MONKEYS: Clicked tile 2 (click #{click_count})")
                else:
                    logger.warning("STACK_MONKEYS: Could not find stack tile 2!")
                    click_count += 1  # Still count to avoid infinite loop
                current_tile = 1

            # Wait before next click (with slight randomness)
            if click_count < TOTAL_CLICKS:
                time.sleep(CLICK_INTERVAL + random.uniform(-0.1, 0.1))

        # Update stack timer
        self._last_stack_time = time.time()
        self._restack_count += 1
        self._needs_restack = False

        logger.info(f"STACK_MONKEYS: Stacking complete - {click_count}/{TOTAL_CLICKS} clicks (restack #{self._restack_count})")
        return StateResult.SUCCESS

    def _handle_attack(self, context: StateExecutionContext) -> StateResult:
        """Wait for monkeys to auto-aggro and start combat."""
        logger.info("[ATTACK] Waiting for monkeys to auto-aggro...")

        # Monkeys auto-aggro when stacked, just wait briefly
        time.sleep(random.uniform(1.5, 2.5))

        if self.state.in_combat():
            logger.info("ATTACK: Combat confirmed - monkeys auto-aggroed!")
        else:
            logger.info("ATTACK: Combat not detected yet, but auto-retaliate will handle it")

        self._initial_setup_done = True
        return StateResult.SUCCESS

    def _handle_combat_loop(self, context: StateExecutionContext) -> StateResult:
        """Main AFK loop - monitor timers and conditions."""
        logger.info("[COMBAT_LOOP] AFK chinning in progress...")

        # Reset condition flags
        self._needs_restack = False
        self._needs_prayer = False
        self._needs_aggro_reset = False

        loop_iterations = 0
        MAX_LOOP_ITERATIONS = 100  # Safety limit per state execution

        while loop_iterations < MAX_LOOP_ITERATIONS:
            self._check_exit_requested()
            loop_iterations += 1

            current_time = time.time()

            # Check restack timer
            if self._needs_restack_check():
                restack_elapsed = current_time - self._last_stack_time
                logger.info(
                    f"COMBAT_LOOP: Restack timer expired "
                    f"({restack_elapsed:.0f}s >= {self.RESTACK_INTERVAL}s)"
                )
                self._needs_restack = True
                return StateResult.SUCCESS

            # Check aggro reset timer
            if self._needs_aggro_reset_check():
                aggro_elapsed = current_time - self._last_aggro_reset_time
                logger.info(
                    f"COMBAT_LOOP: Aggro reset timer expired "
                    f"({aggro_elapsed:.0f}s >= {self.AGGRO_RESET_INTERVAL}s)"
                )
                self._needs_aggro_reset = True
                return StateResult.SUCCESS

            # Check prayer periodically
            if self._needs_prayer_check():
                self._last_prayer_check_time = current_time
                prayer_points = self._get_prayer_points()

                if prayer_points is not None:
                    prayer_threshold = random.randint(self.MIN_PRAYER_THRESHOLD_LOW, self.MIN_PRAYER_THRESHOLD_HIGH)
                    logger.info(f"COMBAT_LOOP: Prayer check - {prayer_points} points (threshold: {prayer_threshold})")
                    if prayer_points < prayer_threshold:
                        logger.warning(
                            f"COMBAT_LOOP: Prayer low! "
                            f"({prayer_points} < {prayer_threshold})"
                        )
                        self._needs_prayer = True
                        return StateResult.SUCCESS

            # Log status periodically
            if loop_iterations % 10 == 0:
                time_since_stack = current_time - self._last_stack_time
                time_since_aggro = current_time - self._last_aggro_reset_time
                logger.info(
                    f"COMBAT_LOOP: [STATUS] "
                    f"stack_timer={time_since_stack:.0f}/{self.RESTACK_INTERVAL}s, "
                    f"aggro_timer={time_since_aggro:.0f}/{self.AGGRO_RESET_INTERVAL}s, "
                    f"restacks={self._restack_count}, "
                    f"prayer_doses={self._prayer_doses}"
                )

            # Anti-ban: occasional idle actions
            if random.random() < 0.05:
                pause = random.uniform(0.5, 2.0)
                logger.debug(f"COMBAT_LOOP: Anti-ban pause ({pause:.1f}s)")
                time.sleep(pause)

            # Main loop wait
            time.sleep(random.uniform(1.5, 3.0))

        logger.info("COMBAT_LOOP: Max iterations reached, cycling state")
        return StateResult.SUCCESS

    def _handle_restack(self, context: StateExecutionContext) -> StateResult:
        """Re-stack monkeys by alternating between tiles (25 clicks)."""
        logger.info("[RESTACK] Re-stacking monkeys...")

        # Same alternating pattern as initial stacking
        TOTAL_CLICKS = 25
        CLICK_INTERVAL = 0.9  # seconds between clicks

        click_count = 0
        current_tile = 1

        while click_count < TOTAL_CLICKS:
            self._check_exit_requested()

            if current_tile == 1:
                if self._click_tile_color(self.stack_tile_1_color):
                    click_count += 1
                else:
                    click_count += 1  # Still count to avoid infinite loop
                current_tile = 2
            else:
                if self._click_tile_color(self.stack_tile_2_color):
                    click_count += 1
                else:
                    click_count += 1  # Still count to avoid infinite loop
                current_tile = 1

            if click_count < TOTAL_CLICKS:
                time.sleep(CLICK_INTERVAL + random.uniform(-0.1, 0.1))

        self._last_stack_time = time.time()
        self._restack_count += 1
        self._needs_restack = False

        logger.info(f"RESTACK: Complete - {click_count} clicks (total restacks: {self._restack_count})")
        return StateResult.SUCCESS

    def _handle_check_prayer(self, context: StateExecutionContext) -> StateResult:
        """Check prayer points and set flag if low."""
        logger.info("[CHECK_PRAYER] Checking prayer points...")

        prayer_points = self._get_prayer_points()

        if prayer_points is None:
            logger.warning("CHECK_PRAYER: Could not read prayer points")
            self._needs_prayer = False
            return StateResult.SUCCESS

        prayer_threshold = random.randint(self.MIN_PRAYER_THRESHOLD_LOW, self.MIN_PRAYER_THRESHOLD_HIGH)
        logger.info(f"CHECK_PRAYER: Prayer points = {prayer_points} (threshold: {prayer_threshold})")

        if prayer_points < prayer_threshold:
            logger.warning(f"CHECK_PRAYER: Prayer low ({prayer_points} < {prayer_threshold}), need to drink")
            self._needs_prayer = True
        else:
            logger.info(f"CHECK_PRAYER: Prayer OK ({prayer_points} >= {prayer_threshold})")
            self._needs_prayer = False

        return StateResult.SUCCESS

    def _handle_drink_prayer(self, context: StateExecutionContext) -> StateResult:
        """Drink a prayer potion."""
        logger.info("[DRINK_PRAYER] Drinking prayer potion...")

        if self.actions.click_template(self.PRAYER_POTION_TEMPLATE, "prayer_potion"):
            self._prayer_doses += 1
            logger.info(f"DRINK_PRAYER: Drank prayer potion (total doses: {self._prayer_doses})")
            self.actions.wait("medium")
        else:
            logger.warning("DRINK_PRAYER: Could not find prayer potion!")

        self._needs_prayer = False
        return StateResult.SUCCESS

    def _handle_reset_aggro(self, context: StateExecutionContext) -> StateResult:
        """Reset aggro by climbing rope to exit and re-entering the cave."""
        logger.warning("=" * 60)
        logger.warning("[RESET_AGGRO] Resetting aggro timer (10 min mechanic)...")
        logger.warning("=" * 60)

        # Step 1: Navigate to exit via minimap clicks
        # These coordinates are relative to the RuneLite window (minimap zoomed out)
        minimap_clicks = [
            (654, 184),  # First waypoint
            (641, 179),  # Second waypoint
            (659, 120),  # Near exit/rope
        ]

        logger.info("RESET_AGGRO: Navigating to exit via minimap...")
        for i, (mx, my) in enumerate(minimap_clicks, 1):
            self._check_exit_requested()
            logger.info(f"RESET_AGGRO: Clicking minimap waypoint {i}/3 at ({mx}, {my})")

            # Click on minimap (coordinates are already window-relative)
            if self.actions.coord_resolver:
                abs_x, abs_y = self.actions.coord_resolver.to_absolute(mx, my)
                self.actions.mouse.click_at(abs_x, abs_y, move_style="instant", speed_multiplier=0.2)

            # Wait for movement between clicks (long walk distance)
            time.sleep(random.uniform(14.0, 16.0))

        # Extra wait to ensure we've arrived near the rope
        logger.info("RESET_AGGRO: Waiting to arrive near rope...")
        time.sleep(random.uniform(4.5, 5.5))

        # Step 2: Find and click the rope to exit (use same method as tiles)
        logger.info("RESET_AGGRO: Looking for rope to climb out...")
        if not self._click_tile_color(self.rope_color_key, tolerance=20):
            logger.error(f"RESET_AGGRO: Could not find/click rope!")
            return StateResult.FAILURE

        # Wait for climb animation and screen transition
        logger.info("RESET_AGGRO: Waiting for exit (climb animation)...")
        time.sleep(random.uniform(3.0, 4.0))

        # Step 2: Find and click cave entrance to re-enter
        logger.info("RESET_AGGRO: Looking for cave entrance to re-enter...")

        # Try multiple times to find the entrance (might need camera adjustment)
        max_attempts = 5
        for attempt in range(max_attempts):
            self._check_exit_requested()

            if self.actions.click_template(self.CAVE_ENTRANCE_TEMPLATE, "cave_entrance", threshold=0.7):
                logger.info("RESET_AGGRO: Clicked cave entrance, waiting for re-entry...")
                break
            else:
                logger.warning(f"RESET_AGGRO: Cave entrance not found (attempt {attempt + 1}/{max_attempts})")
                time.sleep(1.0)
        else:
            logger.error("RESET_AGGRO: Failed to find cave entrance after all attempts!")
            return StateResult.FAILURE

        # Wait for re-entry animation
        time.sleep(random.uniform(3.0, 4.0))

        # Step 3: Wait a moment for the area to load
        logger.info("RESET_AGGRO: Re-entered cave, waiting for area to load...")
        time.sleep(random.uniform(1.5, 2.5))

        # Reset timers
        self._last_aggro_reset_time = time.time()
        self._last_stack_time = 0.0  # Force restack after aggro reset
        self._needs_aggro_reset = False
        self._aggro_resets += 1

        logger.info(f"RESET_AGGRO: Complete (total aggro resets: {self._aggro_resets})")
        logger.warning("=" * 60)

        return StateResult.SUCCESS

    def _handle_recovery(self, context: StateExecutionContext) -> StateResult:
        """Recovery state - reset and return to IDLE."""
        logger.warning("=" * 60)
        logger.warning("[RECOVERY] Recovering from error...")
        logger.warning(
            f"RECOVERY: [BOT STATS] "
            f"restacks={self._restack_count}, "
            f"prayer_doses={self._prayer_doses}, "
            f"aggro_resets={self._aggro_resets}"
        )
        logger.warning("=" * 60)

        # Reset state
        self._needs_restack = False
        self._needs_prayer = False
        self._needs_aggro_reset = False
        self._initial_setup_done = False

        self.actions.wait("long")

        logger.info("RECOVERY: Returning to IDLE")
        return StateResult.SUCCESS
