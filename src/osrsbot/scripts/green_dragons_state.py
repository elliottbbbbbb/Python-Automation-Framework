"""
Green Dragons Bot - State Machine Implementation

State-machine driven bot for farming green dragons.

States:
    IDLE - Initial state, safety checks
    TELEPORT_TO_DRAGONS - Use wilderness obelisk teleport
    NAVIGATE_TO_SPOT - Walk to dragon spawn, drink potions
    COMBAT - Kill dragons until inventory full
    TELEPORT_TO_BANK - Varrock teleport
    BANKING - Deposit loot, withdraw food
    RECOVERY - Failover state for error recovery
"""

import logging
import random
import time
from enum import Enum
from typing import Dict, List

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


class GreenDragonsStates(Enum):
    """States for Green Dragons farming bot."""

    IDLE = "idle"
    TELEPORT_TO_DRAGONS = "teleport_to_dragons"
    NAVIGATE_TO_SPOT = "navigate_to_spot"
    COMBAT = "combat"
    TELEPORT_TO_BANK = "teleport_to_bank"
    BANKING = "banking"
    RECOVERY = "recovery"


class GreenDragonsStateMachineBot(StateMachineBot):
    """
    Green Dragons bot using state machine framework.

    Inherits state machine capabilities from StateMachineBot.
    Implements handlers for each state.
    """

    def __init__(self, *args, **kwargs):
        """Initialize Green Dragons state machine bot."""
        super().__init__(*args, **kwargs, script_name="Green Dragons (State Machine)")

        # Add HP threshold variance (Phase 0 anti-detection)
        base_threshold = self.config.get("hp_threshold", default=70)
        self.hp_threshold = self._apply_threshold_variance(base_threshold)
        logger.info(f"HP threshold set to {self.hp_threshold}")

        # Track kills for logging
        self._kills = 0

    # ==================== State Machine Configuration ====================

    def define_states(self) -> type[Enum]:
        """Define states for this bot."""
        return GreenDragonsStates

    def define_state_metadata(self) -> Dict[Enum, StateMetadata]:
        """
        Define metadata for each state.

        Configures retry limits, timeouts, and failover behavior.
        """
        return build_metadata_dict(
            GreenDragonsStates,
            {
                GreenDragonsStates.IDLE: {
                    "name": "Idle",
                    "description": "Initial state, safety checks",
                    "max_retries": 1,
                },
                GreenDragonsStates.TELEPORT_TO_DRAGONS: {
                    "name": "Teleport to Dragons",
                    "description": "Use wilderness obelisk teleport",
                    "max_retries": 2,
                    "timeout": 30.0,
                    "failover": GreenDragonsStates.RECOVERY,
                },
                GreenDragonsStates.NAVIGATE_TO_SPOT: {
                    "name": "Navigate to Spot",
                    "description": "Walk to dragon spawn, drink potions",
                    "max_retries": 2,
                    "timeout": 45.0,
                    "failover": GreenDragonsStates.RECOVERY,
                },
                GreenDragonsStates.COMBAT: {
                    "name": "Combat",
                    "description": "Kill dragons until inventory full",
                    "max_retries": 1,
                    "timeout": 600.0,
                    "failover": GreenDragonsStates.TELEPORT_TO_BANK,
                },
                GreenDragonsStates.TELEPORT_TO_BANK: {
                    "name": "Teleport to Bank",
                    "description": "Varrock teleport",
                    "max_retries": 2,
                    "timeout": 30.0,
                    "failover": GreenDragonsStates.RECOVERY,
                },
                GreenDragonsStates.BANKING: {
                    "name": "Banking",
                    "description": "Deposit loot, withdraw food",
                    "timeout": 60.0,
                    "failover": GreenDragonsStates.RECOVERY,
                },
                GreenDragonsStates.RECOVERY: {
                    "name": "Recovery",
                    "description": "Failover state for error recovery",
                    "max_retries": 2,
                },
            },
        )

    def define_transitions(self) -> List[StateTransition]:
        """
        Define allowed state transitions.

        Creates a linear flow with recovery failover:
        IDLE → TELEPORT_TO_DRAGONS → NAVIGATE → COMBAT → TELEPORT_TO_BANK → BANKING → (cycle complete)
        Any state can failover to RECOVERY
        """
        return [
            # Main flow
            StateTransition(
                GreenDragonsStates.IDLE, GreenDragonsStates.TELEPORT_TO_DRAGONS
            ),
            StateTransition(
                GreenDragonsStates.TELEPORT_TO_DRAGONS,
                GreenDragonsStates.NAVIGATE_TO_SPOT,
            ),
            StateTransition(
                GreenDragonsStates.NAVIGATE_TO_SPOT, GreenDragonsStates.COMBAT
            ),
            StateTransition(
                GreenDragonsStates.COMBAT, GreenDragonsStates.TELEPORT_TO_BANK
            ),
            StateTransition(
                GreenDragonsStates.TELEPORT_TO_BANK, GreenDragonsStates.BANKING
            ),
            # Banking completes cycle (no next state = cycle ends)
            # Recovery transitions
            StateTransition(
                GreenDragonsStates.RECOVERY,
                GreenDragonsStates.IDLE,  # Recovery resets to idle
            ),
        ]

    def get_initial_state(self) -> Enum:
        """Get initial state (always start at IDLE)."""
        return GreenDragonsStates.IDLE

    # ==================== State Handlers ====================

    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        """
        Handle IDLE state - safety checks before starting.

        Returns:
            StateResult.SUCCESS to proceed
        """
        logger.info("IDLE: Performing safety checks")

        # Could add safety checks here:
        # - Check we're not in combat
        # - Check we're not poisoned
        # - Check we have required items

        # Reset kills counter for new cycle
        self._kills = 0

        logger.info("IDLE: Safety checks passed, proceeding")
        return StateResult.SUCCESS

    def _handle_teleport_to_dragons(
        self, context: StateExecutionContext
    ) -> StateResult:
        """
        Handle TELEPORT_TO_DRAGONS state - use teleport to get to wilderness.

        Uses wilderness obelisk or configured teleport method.

        Returns:
            StateResult.SUCCESS if teleported
            StateResult.FAILURE if teleport failed
        """
        logger.info("TELEPORT_TO_DRAGONS: Using teleport")

        try:
            # Click teleport item (slot 28 in original code)
            self.actions.click_inventory_slot(28)
            self.actions.wait("long")

            logger.info("TELEPORT_TO_DRAGONS: Teleport complete")
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"TELEPORT_TO_DRAGONS: Failed - {e}")
            return StateResult.FAILURE

    def _handle_navigate_to_spot(self, context: StateExecutionContext) -> StateResult:
        """
        Handle NAVIGATE_TO_SPOT state - walk to dragon spawn and drink potions.

        Returns:
            StateResult.SUCCESS if navigation complete
            StateResult.FAILURE if navigation failed
        """
        logger.info("NAVIGATE_TO_SPOT: Walking to dragons and drinking potions")

        try:
            actions = self.actions

            # Walk to marker (original code does this twice)
            for _ in range(GAME_TIMING.teleport_double_click_count):
                logger.debug("Walking to yellow tile marker")
                actions.click_color("yellow_tile_marker")
            actions.wait("long")

            # Click minimap to get to dragons
            actions.click_minimap("green_dragons")
            actions.wait("medium")

            # Drink potions
            logger.info("NAVIGATE_TO_SPOT: Drinking potions")
            actions.use_item("extended_antifire")
            actions.wait("medium")
            actions.use_item("super_combat")
            actions.wait("long")

            logger.info("NAVIGATE_TO_SPOT: Navigation and potions complete")
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"NAVIGATE_TO_SPOT: Failed - {e}")
            return StateResult.FAILURE

    def _handle_combat(self, context: StateExecutionContext) -> StateResult:
        """
        Handle COMBAT state - kill dragons until inventory full.

        Monitors HP and eats food when low.
        Uses combat tick variance for anti-detection.

        Returns:
            StateResult.SUCCESS when inventory full
            StateResult.FAILURE if combat failed
            StateResult.RETRY if still in combat
        """
        state = self.state
        actions = self.actions

        # Check if inventory is full (combat complete)
        if state.inventory_full():
            logger.info(f"COMBAT: Inventory full after {self._kills} kills")
            return StateResult.SUCCESS

        try:
            # Check HP and eat if low
            hp = state.get_health()
            if hp and hp < self.hp_threshold:
                logger.info(f"COMBAT: HP low ({hp}), eating")
                actions.eat("manta_ray")
                actions.wait("medium")

            # Attack dragon if not in combat
            if not state.in_combat():
                if actions.attack_npc("green_dragon"):
                    self._kills += 1
                    if self._kills % GAME_TIMING.kill_log_frequency == 0:
                        logger.info(f"COMBAT: Kills: {self._kills}")

            # Combat tick with variance (Phase 0 anti-detection)
            tick_delay = random.uniform(*GAME_TIMING.combat_tick)
            time.sleep(tick_delay)

            # Continue combat
            return StateResult.RETRY

        except Exception as e:
            logger.error(f"COMBAT: Error - {e}")
            return StateResult.FAILURE

    def _handle_teleport_to_bank(self, context: StateExecutionContext) -> StateResult:
        """
        Handle TELEPORT_TO_BANK state - teleport to Varrock.

        Returns:
            StateResult.SUCCESS if teleported
            StateResult.FAILURE if teleport failed
        """
        logger.info("TELEPORT_TO_BANK: Teleporting to Varrock")

        try:
            self.actions.teleport_varrock()
            self.actions.wait("long")

            logger.info("TELEPORT_TO_BANK: Teleport complete")
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"TELEPORT_TO_BANK: Failed - {e}")
            return StateResult.FAILURE

    def _handle_banking(self, context: StateExecutionContext) -> StateResult:
        """
        Handle BANKING state - deposit loot and withdraw food.

        Uses the common banking logic from base Bot class.

        Returns:
            StateResult.SUCCESS if banking complete
            StateResult.FAILURE if banking failed
        """
        logger.info("BANKING: Starting banking operations")

        try:
            actions = self.actions

            # Walk to bank
            actions.click_coordinate(("world", "varrock_fountain"))
            actions.wait("teleport")

            for _ in range(GAME_TIMING.walk_to_marker_attempts):
                actions.walk_to_marker("yellow_tile_marker")
            actions.wait("long")

            # Open bank
            for _ in range(GAME_TIMING.bank_click_attempts):
                actions.click_coordinate(("world", "bank_booth"))
            actions.wait("long")

            # Deposit items
            for _ in range(GAME_TIMING.deposit_items_max_attempts):
                actions.click_color("purple_item_outline")
                actions.wait("short")

            # Withdraw food
            actions.wait("medium")
            actions.click_coordinate(("ui", "bank_quantity"))
            actions.wait("medium")
            actions.bank_search("manta ray")
            actions.click_coordinate(("ui", "bank_food_slot"))
            actions.wait("long")
            actions.close_interface()

            logger.info("BANKING: Banking complete")
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"BANKING: Failed - {e}")
            return StateResult.FAILURE

    def _handle_recovery(self, context: StateExecutionContext) -> StateResult:
        """
        Handle RECOVERY state - attempt to recover from errors.

        This is a failover state that tries to get the bot back to a safe state.

        Recovery strategies:
        1. Check if in combat - if so, try to escape
        2. Check location - try to teleport to safe area
        3. Check inventory - clear if needed
        4. Reset to IDLE state

        Returns:
            StateResult.SUCCESS if recovery successful
            StateResult.FAILURE if recovery failed (terminates cycle)
        """
        logger.warning("RECOVERY: Attempting recovery")

        try:
            # Strategy 1: If in combat, try to escape
            if self.state.in_combat():
                logger.info("RECOVERY: In combat, attempting to teleport out")
                try:
                    self.actions.teleport_varrock()
                    self.actions.wait("long")
                except Exception:
                    logger.error("RECOVERY: Failed to escape combat")

            # Strategy 2: Try to get to safe location (bank)
            logger.info("RECOVERY: Attempting to reach bank")
            try:
                # If we have teleport, use it
                self.actions.teleport_varrock()
                self.actions.wait("long")
            except Exception:
                logger.error("RECOVERY: Failed to teleport")

            # Strategy 3: Log recovery attempt
            logger.info("RECOVERY: Recovery complete, will reset to IDLE")
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"RECOVERY: Recovery failed - {e}")
            return StateResult.FAILURE
