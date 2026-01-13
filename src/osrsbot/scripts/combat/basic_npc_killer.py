"""
Basic NPC Killer - Simple combat bot that kills NPCs and loots until inventory full.

Features:
- Kills NPCs using color detection (RuneLite NPC highlighting)
- Loots items using purple ground item highlights
- Stops when inventory is full
- Uses state machine for robust error handling

Setup Requirements:
1. RuneLite with NPC Indicators plugin enabled
2. Highlight target NPCs with a specific color (e.g., cyan #00FFFF)
3. Ground Items plugin highlighting valuable loot in purple
4. Configure NPC color in config.json under "colors.npc_target"

Usage:
    python -m osrsbot
    # Select "Basic NPC Killer" from menu
"""

import logging
import random
from enum import Enum
from typing import Dict, List
from time import sleep, time

from osrsbot.core.state_helpers import build_metadata_dict
from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_types import (
    StateExecutionContext,
    StateMetadata,
    StateResult,
    StateTransition,
)

logger = logging.getLogger(__name__)


class NPCKillerStates(Enum):
    """States for basic NPC killer bot."""

    IDLE = "idle"
    ATTACK = "attack"
    COMBAT = "combat"
    LOOT = "loot"
    COMPLETE = "complete"


class BasicNPCKiller(StateMachineBot):
    """
    Basic NPC killer that attacks NPCs and loots until inventory full.

    Uses color detection for NPC targeting and loot pickup.
    Stops automatically when inventory is full.
    """

    def __init__(
        self,
        npc_detection_method: str = "color",
        npc_template: str = None,
        npc_color: str = None,
        loot_color: str = "#ff00dc",
        inventory_threshold: int = 27,
        *args,
        **kwargs,
    ):
        """
        Initialize Basic NPC Killer.

        Args:
            npc_detection_method: "color" or "template" (default: color)
            npc_template: Path to NPC template image (required if method="template")
            npc_color: Hex color for NPC highlighting (default from config)
            loot_color: Hex color for loot highlighting (default purple)
            inventory_threshold: Stop when inventory has >= this many items (default 27)
        """
        super().__init__(
            *args,
            **kwargs,
            script_name="Basic NPC Killer",
            enable_exit_key=True,
            enable_status_ui=True,
        )

        # NPC detection configuration
        self.npc_detection_method = npc_detection_method
        self.npc_template = npc_template
        self._npc_clicked = False

        # Get NPC color from parameter or config
        self.npc_color = npc_color or self.config.get(
            "colors.npc_target", default="#00FFFF"  # Default cyan
        )

        self.loot_color = loot_color
        self.inventory_threshold = inventory_threshold

        # Validate configuration
        if self.npc_detection_method == "template" and not self.npc_template:
            raise ValueError("npc_template required when using template detection")

        # Stats tracking
        self._kills = 0
        self._loots_picked = 0
        self._last_attack_time = 0.0
        self._run_count = 0

        logger.info(
            f"BasicNPCKiller initialized: method={self.npc_detection_method}, "
            f"npc_color={self.npc_color}, npc_template={self.npc_template}, "
            f"loot_color={self.loot_color}, inventory_threshold={self.inventory_threshold}"
        )

    # ==================== State Machine Configuration ====================

    def define_states(self) -> type[Enum]:
        """Define bot states."""
        return NPCKillerStates

    def define_transitions(self) -> List[StateTransition]:
        """Define state transitions."""
        return [
            # Normal flow
            StateTransition(NPCKillerStates.IDLE, NPCKillerStates.ATTACK),
            StateTransition(NPCKillerStates.ATTACK, NPCKillerStates.COMBAT),
            StateTransition(NPCKillerStates.COMBAT, NPCKillerStates.LOOT),
            StateTransition(NPCKillerStates.LOOT, NPCKillerStates.ATTACK),
            # Completion
            StateTransition(NPCKillerStates.LOOT, NPCKillerStates.COMPLETE),
        ]

    def define_state_metadata(self) -> Dict[Enum, StateMetadata]:
        """Define state configuration."""
        return build_metadata_dict(
            NPCKillerStates,
            {
                NPCKillerStates.IDLE: {
                    "name": "Idle",
                    "description": "Initial checks",
                    "max_retries": 1,
                    "failover": NPCKillerStates.ATTACK,  # If idle fails, try attacking anyway
                },
                NPCKillerStates.ATTACK: {
                    "name": "Attack",
                    "description": "Click NPC to attack",
                    "max_retries": 25,  # Increased retries for finding NPCs
                    "timeout": 105.0,
                    "failover": NPCKillerStates.ATTACK,  # Keep retrying attacks if NPCs not found
                },
                NPCKillerStates.COMBAT: {
                    "name": "Combat",
                    "description": "Wait for combat to finish",
                    "max_retries": 1,
                    "timeout": 60.0,
                    "failover": NPCKillerStates.ATTACK,  # If combat fails/times out, try new attack
                },
                NPCKillerStates.LOOT: {
                    "name": "Loot",
                    "description": "Pick up loot",
                    "max_retries": 2,
                    "timeout": 15.0,
                    "failover": NPCKillerStates.ATTACK,  # If looting fails, go back to attacking
                },
                NPCKillerStates.COMPLETE: {
                    "name": "Complete",
                    "description": "Bot finished",
                    "max_retries": 0,
                },
            },
        )

    def get_initial_state(self) -> Enum:
        """Start at IDLE state."""
        return NPCKillerStates.IDLE

    # ==================== Helper Methods ====================

    def _check_inventory_full(self) -> bool:
        """
        Check if inventory is full or above threshold.

        Returns:
            True if inventory has >= threshold items
        """
        try:
            is_full = self.state.inventory_full(threshold=self.inventory_threshold)
            if is_full:
                logger.info(
                    f"Inventory at threshold ({self.inventory_threshold} items), stopping"
                )
            return is_full
        except Exception as e:
            logger.error(f"Failed to check inventory: {e}", exc_info=True)
            # Conservative: assume full if check fails
            return True

    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        """
        Initial state for setup and checks.

        Can be used to show debug viewport on first run.
        """
        # Uncomment to see viewport debug visualization:
        # self.screen.debug_show_viewport(duration=5)

        return StateResult.SUCCESS

    
    def _handle_attack(self, context: StateExecutionContext) -> StateResult:
        """
        Attack NPC and verify combat engagement.

        Clicks NPC once, polls for combat start with early exit.
        If combat doesn't start within timeout, returns FAILURE to retry.
        """
        # First attempt - click the NPC
        if not self.actions.click_color_smart(color_name="blue_outline"):
            logger.warning("No NPC found to attack")
            return StateResult.FAILURE

        logger.info("Clicked NPC, checking for combat engagement...")

        # Poll for combat start with early exit (max 2 seconds, check every 0.3s)
        max_wait = 4
        check_interval = 0.3
        elapsed = 0.0

        while elapsed < max_wait:
            if self.state.in_combat():
                logger.info(f"Combat started after {elapsed:.1f}s")
                self.actions.wait("small")
                return StateResult.SUCCESS

            sleep(check_interval)
            elapsed += check_interval

        # Combat didn't start within timeout
        logger.warning(f"Combat didn't start after {max_wait}s - NPC may be inaccessible")
        return StateResult.FAILURE
        
    def _handle_combat(self, context: StateExecutionContext) -> StateResult:
        """
        Wait for combat to finish.

        Polls combat state efficiently with sleep intervals to avoid CPU waste.
        """
        logger.debug("Waiting for combat to finish...")

        while self.state.in_combat():
            sleep(0.6)  # Check every game tick (0.6s)

        logger.info("Combat finished")

        # Small delay to let loot appear before transitioning to loot state
        sleep(0.1)

        return StateResult.SUCCESS

        
    def _handle_loot(self, context: StateExecutionContext) -> StateResult:
        return StateResult.SUCCESS
        
    def _handle_complete(self, context: StateExecutionContext) -> StateResult:
        logger.info("Bot run complete")
        return StateResult.SUCCESS