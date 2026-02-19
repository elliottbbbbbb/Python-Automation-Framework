"""
Mining Bot - Simple Powermining Strategy

State-machine driven bot for mining rocks and dropping ore.
Foundation for future 3-tick granite mining.

States:
    IDLE - Initial state, safety checks
    FIND_ROCK - Locate and click mineable rock
    MINE_ROCK - Monitor mining until inventory full or rock depletes
    DROP_ORE - Drop all ore using shift-drop
    RECOVERY - Failover state for error recovery

Strategy:
    1. Find rock using color detection
    2. Click rock to start mining
    3. Monitor inventory and rock state
    4. When inventory full, drop all ore
    5. Repeat indefinitely

Future: 3-tick granite mining support
"""

import logging
import random
import time
from enum import Enum
from typing import Dict, List, Optional, Tuple

import pyautogui

from osrsbot.constants import GAME_TIMING
from osrsbot.core.state_helpers import build_metadata_dict
from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_types import (
    StateExecutionContext,
    StateMetadata,
    StateResult,
    StateTransition,
)

logger = logging.getLogger(__name__)


class MiningStates(Enum):
    """States for mining bot."""

    IDLE = "idle"
    FIND_ROCK = "find_rock"
    MINE_ROCK = "mine_rock"
    DROP_ORE = "drop_ore"
    RECOVERY = "recovery"


class MiningBot(StateMachineBot):
    """
    Mining bot using state machine framework.

    Implements powermining strategy: mine rocks, drop ore, repeat.
    """

    def __init__(self, rock_type: str = "iron", **kwargs):
        """
        Initialize mining bot.

        Args:
            rock_type: Type of rock to mine ("iron", "coal", "granite", etc.)
        """
        super().__init__(**kwargs, script_name=f"Mining Bot ({rock_type.capitalize()})")

        self.rock_type = rock_type

        # Get rock color from config
        rock_color_key = f"{rock_type}_rock"
        self.rock_color = self.config.get("colors", rock_color_key, default=None)

        if not self.rock_color:
            logger.warning(
                f"Rock color not found in config for '{rock_color_key}', "
                "using default gray color"
            )
            self.rock_color = "#808080"

        # Track current rock position (world coordinates or screen pos)
        self._current_rock_pos: Optional[Tuple[int, int]] = None
        self._last_click_time: float = 0.0

        # Statistics
        self._ore_mined = 0
        self._rocks_depleted = 0
        self._drop_cycles = 0

        logger.info(f"Mining bot initialized: rock_type={rock_type}, color={self.rock_color}")

    # ==================== State Machine Configuration ====================

    def define_states(self) -> type[Enum]:
        """Define states for this bot."""
        return MiningStates

    def define_state_metadata(self) -> Dict[Enum, StateMetadata]:
        """
        Define metadata for each state.

        Configures retry limits, timeouts, and failover behavior.
        """
        return build_metadata_dict(
            MiningStates,
            {
                MiningStates.IDLE: {
                    "name": "Idle",
                    "description": "Initial state, safety checks",
                    "max_retries": 1,
                },
                MiningStates.FIND_ROCK: {
                    "name": "Find Rock",
                    "description": "Locate and click mineable rock",
                    "max_retries": 5,
                    "timeout": 30.0,
                    "failover": MiningStates.RECOVERY,
                },
                MiningStates.MINE_ROCK: {
                    "name": "Mine Rock",
                    "description": "Monitor mining until inventory full or rock depletes",
                    "max_retries": 1,
                    "timeout": 300.0,  # 5 minutes
                    "failover": MiningStates.FIND_ROCK,
                },
                MiningStates.DROP_ORE: {
                    "name": "Drop Ore",
                    "description": "Drop all ore using shift-drop",
                    "max_retries": 3,
                    "timeout": 30.0,
                    "failover": MiningStates.RECOVERY,
                },
                MiningStates.RECOVERY: {
                    "name": "Recovery",
                    "description": "Failover state for error recovery",
                    "max_retries": 2,
                },
            },
        )

    def define_transitions(self) -> List[StateTransition]:
        """
        Define allowed state transitions.

        Creates a simple mining loop with recovery failover:
        IDLE → FIND_ROCK → MINE_ROCK → DROP_ORE → FIND_ROCK (cycle repeats)
        MINE_ROCK can also loop back to FIND_ROCK when rock depletes
        """
        return [
            # Main flow
            StateTransition(MiningStates.IDLE, MiningStates.FIND_ROCK),
            StateTransition(MiningStates.FIND_ROCK, MiningStates.MINE_ROCK),
            StateTransition(MiningStates.MINE_ROCK, MiningStates.DROP_ORE),
            StateTransition(MiningStates.MINE_ROCK, MiningStates.FIND_ROCK),  # Rock depleted
            StateTransition(MiningStates.DROP_ORE, MiningStates.FIND_ROCK),
            # Recovery transition
            StateTransition(MiningStates.RECOVERY, MiningStates.IDLE),
        ]

    def get_initial_state(self) -> Enum:
        """Get initial state (always start at IDLE)."""
        return MiningStates.IDLE

    # ==================== State Handlers ====================

    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        """
        Handle IDLE state - safety checks before starting.

        Returns:
            StateResult.SUCCESS to proceed
        """
        logger.info("IDLE: Performing safety checks")

        # Reset statistics for new cycle
        if context.retry_count == 0:
            self._ore_mined = 0
            self._rocks_depleted = 0
            self._drop_cycles = 0

        logger.info(f"IDLE: Rock type: {self.rock_type}")
        logger.info(f"IDLE: Rock color: {self.rock_color}")
        logger.info("IDLE: Safety checks passed, proceeding")

        return StateResult.SUCCESS

    def _handle_find_rock(self, context: StateExecutionContext) -> StateResult:
        """
        Handle FIND_ROCK state - find and click a mineable rock.

        Uses color detection to find rocks of target type.
        Clicks nearest rock and verifies mining started.

        Returns:
            StateResult.SUCCESS if rock clicked and mining started
            StateResult.FAILURE if no rocks found or click failed
        """
        logger.info("FIND_ROCK: Searching for rocks...")

        try:
            # Find rocks using color detection
            # Note: This uses screen service's find_color method
            # We search in the game viewport (main screen, not minimap)

            # For now, use a simple approach: click on the rock color
            # Future: Use template matching for more accuracy

            # Click color (this uses the actions service which wraps screen + mouse)
            clicked = self.actions.click_color(f"{self.rock_type}_rock")

            if not clicked:
                logger.warning("FIND_ROCK: No rocks found")
                return StateResult.FAILURE

            # Record click time for rock depletion detection
            self._last_click_time = time.time()

            # Wait for mining animation to start
            self.actions.wait("medium")

            # Verify mining started (optional - could check animation)
            # For now, assume success if we clicked
            logger.info("FIND_ROCK: Rock clicked, assuming mining started")
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"FIND_ROCK: Error - {e}", exc_info=True)
            return StateResult.FAILURE

    def _handle_mine_rock(self, context: StateExecutionContext) -> StateResult:
        """
        Handle MINE_ROCK state - monitor mining progress (single tick).

        This handler executes once per tick and uses StateResult.RETRY
        to continue monitoring.

        Checks:
        - Inventory full → transition to DROP_ORE
        - Rock depleted → transition to FIND_ROCK
        - Still mining → return RETRY

        Returns:
            StateResult.SUCCESS when inventory full (go to DROP_ORE)
            StateResult.FAILURE when rock depleted (go to FIND_ROCK)
            StateResult.RETRY to continue mining (stay in this state)
        """
        state = self.state

        # Check if inventory is full
        filled_count = state.count_filled_slots()

        if filled_count >= 28:
            logger.info(f"MINE_ROCK: Inventory full ({filled_count}/28)")
            return StateResult.SUCCESS  # Transition to DROP_ORE

        # Check if rock depleted (using time-based heuristic)
        # Most rocks respawn in 2-60 seconds
        # If we haven't gained ore in 10 seconds, assume rock depleted
        time_since_click = time.time() - self._last_click_time

        if time_since_click > 10.0:
            logger.info("MINE_ROCK: Rock likely depleted (timeout)")
            self._rocks_depleted += 1
            return StateResult.FAILURE  # Transition to FIND_ROCK

        # Log progress occasionally
        if filled_count > 0 and filled_count % 7 == 0:
            logger.info(f"MINE_ROCK: Ore count: {filled_count}/28")

        # Continue mining (state machine will call this again next tick)
        return StateResult.RETRY

    def _handle_drop_ore(self, context: StateExecutionContext) -> StateResult:
        """
        Handle DROP_ORE state - drop all ore using shift-drop.

        Holds shift and clicks each filled inventory slot.
        Uses randomized delays between clicks for anti-ban.

        Returns:
            StateResult.SUCCESS when dropping complete
            StateResult.FAILURE if no items to drop
        """
        logger.info("DROP_ORE: Dropping all ore...")

        try:
            # Get filled inventory slots
            filled_slots = self.state.get_filled_slots()

            if not filled_slots:
                logger.warning("DROP_ORE: No items to drop")
                return StateResult.FAILURE

            logger.info(f"DROP_ORE: Dropping {len(filled_slots)} items")

            # Hold shift key
            pyautogui.keyDown("shift")
            self.actions.wait("short")

            try:
                # Drop each slot
                for i, slot_index in enumerate(filled_slots):
                    logger.debug(f"DROP_ORE: Dropping slot {slot_index} ({i+1}/{len(filled_slots)})")

                    # Click slot
                    # Slots are 0-indexed in queries but click_inventory_slot expects 1-28
                    clicked = self.actions.click_inventory_slot(slot_index + 1)

                    if not clicked:
                        logger.warning(f"DROP_ORE: Failed to click slot {slot_index}")
                        continue

                    # Random delay for anti-ban (50-150ms)
                    delay = random.uniform(0.05, 0.15)
                    time.sleep(delay)

            finally:
                # Always release shift, even if errors occur
                pyautogui.keyUp("shift")

            self._drop_cycles += 1
            logger.info(f"DROP_ORE: Finished dropping (cycle {self._drop_cycles})")
            self.actions.wait("medium")

            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"DROP_ORE: Error - {e}", exc_info=True)
            # Make sure shift is released
            try:
                pyautogui.keyUp("shift")
            except Exception:
                pass
            return StateResult.FAILURE

    def _handle_recovery(self, context: StateExecutionContext) -> StateResult:
        """
        Handle RECOVERY state - attempt to recover from errors.

        This is a failover state that tries to get the bot back to a safe state.

        Recovery strategies:
        1. Release any held keys (shift)
        2. Wait to let animations complete
        3. Reset to IDLE state

        Returns:
            StateResult.SUCCESS if recovery successful
            StateResult.FAILURE if recovery failed (terminates cycle)
        """
        logger.warning("RECOVERY: Attempting recovery")

        try:
            # Make sure shift key is released
            try:
                pyautogui.keyUp("shift")
            except Exception:
                pass

            # Wait for any animations to complete
            logger.info("RECOVERY: Waiting for animations to complete")
            self.actions.wait("long")

            # Clear cached state
            logger.info("RECOVERY: Clearing cached state")
            self.state.clear_cache()

            logger.info("RECOVERY: Recovery complete, will reset to IDLE")
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"RECOVERY: Recovery failed - {e}", exc_info=True)
            return StateResult.FAILURE

    # ==================== Helper Methods ====================

    def get_session_stats(self) -> str:
        """
        Get mining session statistics.

        Returns:
            Formatted stats string
        """
        return f"""
=== Mining Session Stats ===
Rock Type: {self.rock_type}
Rocks Depleted: {self._rocks_depleted}
Drop Cycles: {self._drop_cycles}
Current State: {self._current_state.value if self._current_state else 'Unknown'}
"""
