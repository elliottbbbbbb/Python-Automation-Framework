"""
State Machine Test Bot - Simple bot to validate Phase 1 state machine.

This bot demonstrates the state machine framework by clicking yellow NPCs.
Used for testing state transitions, retry logic, and state history tracking.

States:
    IDLE - Initial state, safety checks
    CLICK_NPC - Click yellow NPC repeatedly
    COMPLETE - Final state (cycle complete)
"""
import logging
import time
from enum import Enum
from typing import Dict, List

from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_types import (
    StateResult,
    StateMetadata,
    StateTransition,
    StateExecutionContext
)

logger = logging.getLogger(__name__)


class TestBotStates(Enum):
    """States for test bot."""
    IDLE = "idle"
    CLICK_NPC = "click_npc"
    COMPLETE = "complete"


class StateMachineTestBot(StateMachineBot):
    """
    Simple test bot that clicks yellow NPCs.

    Demonstrates state machine framework:
    - State transitions
    - Retry logic (keeps clicking NPCs)
    - State history tracking
    - Cycle completion
    """

    def __init__(self, *args, **kwargs):
        """Initialize test bot."""
        super().__init__(*args, **kwargs, script_name="State Machine Test Bot")

        # Track number of kills for demo
        self._click_count = 0
        self._target_clicks = 60  # Kill 15 goblins then complete

        # Track timeout for no targets found
        self._no_targets_start_time = None

    # ==================== State Machine Configuration ====================

    def define_states(self) -> type[Enum]:
        """Define states for this bot."""
        return TestBotStates

    def define_state_metadata(self) -> Dict[Enum, StateMetadata]:
        """
        Define metadata for each state.
        """
        return {
            TestBotStates.IDLE: StateMetadata(
                name="Idle",
                description="Initial state, safety checks",
                max_retries=1,
                timeout=None,
                failover_state=None
            ),
            TestBotStates.CLICK_NPC: StateMetadata(
                name="Kill Goblins",
                description="Kill goblins until target reached (only attacks when not in combat)",
                max_retries=30,  # Increased for 15 kills (was 10 for 5 clicks)
                timeout=120.0,  # 2 minutes timeout (was 30s)
                failover_state=TestBotStates.COMPLETE  # If fails, just complete
            ),
            TestBotStates.COMPLETE: StateMetadata(
                name="Complete",
                description="Final state, cycle complete",
                max_retries=1,
                timeout=None,
                failover_state=None
            )
        }

    def define_transitions(self) -> List[StateTransition]:
        """
        Define allowed state transitions.

        Flow: IDLE → CLICK_NPC → COMPLETE
        """
        return [
            StateTransition(
                TestBotStates.IDLE,
                TestBotStates.CLICK_NPC
            ),
            StateTransition(
                TestBotStates.CLICK_NPC,
                TestBotStates.COMPLETE
            )
        ]

    def get_initial_state(self) -> Enum:
        """Get initial state (always start at IDLE)."""
        return TestBotStates.IDLE

    # ==================== State Handlers ====================

    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        """
        Handle IDLE state - safety checks before starting.

        Returns:
            StateResult.SUCCESS to proceed
        """
        logger.info("IDLE: Starting test bot")
        logger.info(f"IDLE: Will click {self._target_clicks} yellow NPCs")

        # Reset click counter
        self._click_count = 0

        # Clear any previous click tracking when starting
        self.actions.reset_click_tracking()
        logger.debug("IDLE: Click tracking reset")

        logger.info("IDLE: Ready to start")
        return StateResult.SUCCESS

    def _handle_click_npc(self, context: StateExecutionContext) -> StateResult:
        """
        Handle CLICK_NPC state - kill goblins until target reached.

        Only attacks when NOT in combat (waits for current fight to finish).

        Returns:
            StateResult.RETRY to continue killing
            StateResult.SUCCESS when target kills reached
            StateResult.FAILURE if click fails
        """
        logger.info(f"CLICK_NPC: Kill {self._click_count + 1}/{self._target_clicks}")

        try:
            # Check if we've reached target kills
            if self._click_count >= self._target_clicks:
                logger.info("CLICK_NPC: Target kills reached, completing")
                return StateResult.SUCCESS

            # Check HP and eat if low (before attacking)
            # TODO: Uncomment when food is in inventory
            # current_hp = self.state.get_hp(force=True)
            # if current_hp is not None and current_hp < 8:
            #     logger.warning(f"CLICK_NPC: HP is low ({current_hp}), eating food...")

            #     # Try to eat food (look for manta ray or sandwich)
            #     food_clicked = (
            #         self.actions.click_color("manta_ray", move_style="instant") or
            #         self.actions.click_color("sandwich", move_style="instant")
            #     )

            #     if food_clicked:
            #         logger.info("CLICK_NPC: Ate food, waiting for HP to update...")
            #         self.actions.wait("short")

            #         # Wait for HP to increase
            #         for _ in range(5):
            #             self.actions.wait("short")
            #             new_hp = self.state.get_hp(force=True)
            #             if new_hp and new_hp > current_hp:
            #                 logger.info(f"CLICK_NPC: HP recovered to {new_hp}")
            #                 break
            #     else:
            #         logger.error("CLICK_NPC: No food found in inventory!")

            #     # Don't attack this cycle, retry next time
            #     return StateResult.RETRY

            # Only attack if NOT in combat
            if not self.state.in_combat():
                logger.debug("CLICK_NPC: Not in combat, attacking cow")

                # Use smart clicking with all features enabled
                import time

                # Get player position for distance-based selection
                player_pos = self.actions._get_player_position()

                # Define search region (game viewport only, exclude right UI panel)
                # This speeds up color detection significantly
                _, _, width, height = self.actions.interface.get_bounds()
                game_viewport_region = (0, 0, int(width * 0.65), height)  # Left 65% of screen

                # Smart click with target locking, stuck detection, and blacklisting
                # Single click is now fast enough with optimized color detection
                clicked = self.actions.click_color_smart(
                    "blue_tile_marker",
                    player_position=player_pos,
                    move_style="instant",
                    enable_target_lock=True,
                    enable_stuck_detection=True,
                    enable_blacklist=True,
                    region=game_viewport_region
                )

                # Handle no targets found
                if not clicked:
                    if self._no_targets_start_time is None:
                        self._no_targets_start_time = time.time()
                        logger.warning("CLICK_NPC: No valid NPCs found, starting timeout timer...")
                    elif time.time() - self._no_targets_start_time > 45.0:
                        logger.error("CLICK_NPC: No targets for 45+ seconds, ending")
                        return StateResult.FAILURE
                    logger.warning("CLICK_NPC: No valid NPCs found, retrying...")
                    self.actions.wait("short")
                    return StateResult.RETRY

                # Reset timeout when target found
                self._no_targets_start_time = None

                logger.info(f"CLICK_NPC: Clicked cow, waiting for combat to start...")

                # Wait for combat to actually start (up to 3 seconds)
                combat_started = False
                for _ in range(6):  # 6 attempts * 0.5s = 3 seconds max
                    self.actions.wait("short")
                    if self.state.in_combat():
                        combat_started = True
                        logger.debug("CLICK_NPC: Combat started")
                        break

                if combat_started:
                    # Wait for combat to finish
                    logger.debug("CLICK_NPC: Waiting for combat to finish...")
                    combat_ended_count = 0
                    for _ in range(30):  # 30 attempts * 0.5s = 15 seconds max
                        self.actions.wait("short")

                        # Require 3 consecutive frames without combat to confirm kill
                        if not self.state.in_combat():
                            combat_ended_count += 1
                            if combat_ended_count >= 3:
                                # Combat definitely finished, count the kill
                                self._click_count += 1
                                logger.info(f"CLICK_NPC: Kill complete! ({self._click_count}/{self._target_clicks})")
                                logger.info(self.state.get_hp())

                                # Wait 1-2 seconds after combat ends before attacking next NPC
                                # This prevents clicking too early when combat indicator disappears
                                logger.debug("CLICK_NPC: Combat ended, waiting before next attack...")
                                time.sleep(1.0 + (time.time() % 1.0))  # 1-2 second delay
                                logger.debug("CLICK_NPC: Ready for next attack")
                                break
                        else:
                            # Still in combat, reset counter
                            combat_ended_count = 0
                else:
                    logger.warning("CLICK_NPC: Combat didn't start, goblin may have moved")
            else:
                # In combat, wait for fight to finish
                logger.debug("CLICK_NPC: In combat, waiting...")
                self.actions.wait("short")

            # Continue killing
            return StateResult.RETRY

        except Exception as e:
            logger.error(f"CLICK_NPC: Error - {e}")
            return StateResult.FAILURE

    def _handle_complete(self, context: StateExecutionContext) -> StateResult:
        """
        Handle COMPLETE state - cycle complete.

        Returns:
            StateResult.SUCCESS (ends cycle)
        """
        logger.info(f"COMPLETE: Test bot finished! Clicked {self._click_count} NPCs")
        logger.info("COMPLETE: Check state history for execution details")

        # Print state history
        history = self.get_state_history()
        logger.info(f"\nState History ({len(history)} entries):")
        for entry in history:
            logger.info(
                f"  {entry.state.name}: {entry.result.value} "
                f"({entry.duration:.2f}s, retries: {entry.retry_count})"
            )

        return StateResult.SUCCESS
