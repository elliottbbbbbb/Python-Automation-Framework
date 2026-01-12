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
    FIND_TARGET = "find_target"
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
            StateTransition(NPCKillerStates.IDLE, NPCKillerStates.FIND_TARGET),
            StateTransition(NPCKillerStates.FIND_TARGET, NPCKillerStates.ATTACK),
            StateTransition(NPCKillerStates.ATTACK, NPCKillerStates.COMBAT),
            StateTransition(NPCKillerStates.COMBAT, NPCKillerStates.LOOT),
            StateTransition(NPCKillerStates.LOOT, NPCKillerStates.FIND_TARGET),
            # Completion
            StateTransition(NPCKillerStates.FIND_TARGET, NPCKillerStates.COMPLETE),
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
                },
                NPCKillerStates.FIND_TARGET: {
                    "name": "Find Target",
                    "description": "Search for NPC to attack",
                    "max_retries": 5,
                    "timeout": 30.0,
                },
                NPCKillerStates.ATTACK: {
                    "name": "Attack",
                    "description": "Click NPC to attack",
                    "max_retries": 3,
                    "timeout": 10.0,
                },
                NPCKillerStates.COMBAT: {
                    "name": "Combat",
                    "description": "Wait for combat to finish",
                    "max_retries": 1,
                    "timeout": 60.0,
                },
                NPCKillerStates.LOOT: {
                    "name": "Loot",
                    "description": "Pick up loot",
                    "max_retries": 2,
                    "timeout": 15.0,
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

    def _find_npc(self) -> tuple:
        """
        Find nearest NPC using configured detection method.

        Uses either color detection or template matching based on
        npc_detection_method setting.

        Returns:
            (x, y) coordinates of NPC, or None if not found
        """
        if self.npc_detection_method == "color":
            return self._find_npc_by_color()
        elif self.npc_detection_method == "template":
            return self._find_npc_by_template()
        else:
            logger.error(f"Unknown detection method: {self.npc_detection_method}")
            return None

    def _find_npc_by_color(self) -> tuple:
        """
        Find NPC using color detection (RuneLite highlighting).

        Returns:
            (x, y) coordinates of NPC, or None if not found
        """
        try:
            # Find all NPCs with target color
            npc_match = self.actions.screen.find_color(
                self.npc_color,
                tolerance=15,  # Allow some color variance
                find_all=False,  # Just find first one
            )

            if npc_match:
                logger.debug(
                    f"[COLOR] Found NPC at ({npc_match.x}, {npc_match.y}), "
                    f"confidence={npc_match.confidence:.2f}"
                )
                return (npc_match.x, npc_match.y)

            logger.debug("[COLOR] No NPC found on screen")
            return None

        except Exception as e:
            logger.error(f"[COLOR] Failed to find NPC: {e}", exc_info=True)
            return None

    def _find_npc_by_template(self) -> tuple:
        """
        Find NPC using template matching.

        Returns:
            (x, y) coordinates of NPC center, or None if not found
        """
        try:
            # Use template matching service
            result = self.actions.template_service.find_template(
                template_path=self.npc_template,
                threshold=0.7,  # 70% confidence
            )

            if result:
                # Calculate center of template match
                center_x = result.x + result.width // 2
                center_y = result.y + result.height // 2

                logger.debug(
                    f"[TEMPLATE] Found NPC at ({center_x}, {center_y}), "
                    f"confidence={result.confidence:.2f}"
                )
                return (center_x, center_y)

            logger.debug("[TEMPLATE] No NPC found on screen")
            return None

        except Exception as e:
            logger.error(f"[TEMPLATE] Failed to find NPC: {e}", exc_info=True)
            return None

    def _is_in_combat(self) -> bool:
        """
        Check if player is in combat.

        Returns:
            True if in combat
        """
        try:
            return self.state.in_combat()
        except Exception as e:
            logger.debug(f"Combat check failed: {e}")
            return False

    # ==================== State Handlers ====================

    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        """IDLE state - initial checks."""
        self._check_exit_requested()
        self._update_ui("IDLE", "Starting NPC killer...")

        self._run_count += 1
        logger.info(
            f"Bot started (run {self._run_count}): "
            f"Kills: {self._kills}, Loots: {self._loots_picked}"
        )

        # Check if inventory already full
        if self._check_inventory_full():
            logger.info("Inventory already full, completing")
            return StateResult.SUCCESS  # Will transition to COMPLETE via manual override

        return StateResult.SUCCESS

    def _handle_find_target(self, context: StateExecutionContext) -> StateResult:
        """FIND_TARGET state - search for NPC."""
        self._check_exit_requested()
        self._update_ui("FIND_TARGET", f"Looking for NPC (kills: {self._kills})...")

        # Check inventory first
        if self._check_inventory_full():
            logger.info("Inventory full, stopping bot")
            # Manually transition to COMPLETE
            self._current_state = NPCKillerStates.COMPLETE
            return StateResult.SUCCESS

        # Find NPC
        npc_pos = self._find_npc()

        if not npc_pos:
            logger.debug("No NPC found, retrying...")
            self.actions.wait("short")
            return StateResult.RETRY

        # Store NPC position for attack state
        self._target_pos = npc_pos
        logger.info(f"Found NPC at {npc_pos}")
        return StateResult.SUCCESS

    def _handle_attack(self, context: StateExecutionContext) -> StateResult:
        """ATTACK state - click NPC to attack."""
        self._check_exit_requested()
        self._update_ui("ATTACK", f"Attacking NPC (kills: {self._kills})...")

        # Get stored target position
        if not hasattr(self, "_target_pos") or not self._target_pos:
            logger.error("No target position stored")
            return StateResult.FAILURE

        npc_x, npc_y = self._target_pos

        # Record action for anti-ban
        if self.actions.anti_ban:
            self.actions.anti_ban.record_action("attack_npc")

        # Convert relative coordinates to absolute screen coordinates
        abs_x, abs_y = self.actions._to_absolute(npc_x, npc_y)
        logger.info(f"Clicking NPC at relative ({npc_x}, {npc_y}) -> absolute ({abs_x}, {abs_y})")
        success = self.actions.mouse.click_at(abs_x, abs_y, move_style="curved")

        if not success:
            logger.warning("Failed to click NPC")
            return StateResult.RETRY

        # Wait for attack to register
        self.actions.wait("medium")

        # Verify we're in combat
        if not self._is_in_combat():
            logger.warning("Not in combat after clicking NPC, retrying")
            return StateResult.RETRY

        logger.info("Attack successful, entering combat")
        return StateResult.SUCCESS

    def _handle_combat(self, context: StateExecutionContext) -> StateResult:
        """COMBAT state - wait for combat to finish."""
        self._check_exit_requested()
        self._update_ui("COMBAT", f"Fighting NPC (kills: {self._kills})...")

        # Wait while in combat
        import time

        max_combat_time = 60  # Max 60 seconds per kill
        start_time = time.time()

        while self._is_in_combat():
            # Check exit request
            self._check_exit_requested()

            # Check timeout
            if time.time() - start_time > max_combat_time:
                logger.warning("Combat timeout, moving to loot phase")
                break

            # Update UI periodically
            elapsed = int(time.time() - start_time)
            self._update_ui("COMBAT", f"Fighting... ({elapsed}s, kills: {self._kills})")

            # Wait a bit
            self.actions.wait("medium")

            # Occasionally check HP (if available)
            if random.random() < 0.1:  # 10% chance
                try:
                    hp = self.state.get_hp()
                    if hp and hp < 20:
                        logger.warning(f"Low HP detected: {hp}")
                        # Could add eating logic here
                except:
                    pass

        # Combat finished
        self._kills += 1
        logger.info(f"Combat finished! Total kills: {self._kills}")

        # Wait for loot to appear
        self.actions.wait("long")

        return StateResult.SUCCESS

    def _handle_loot(self, context: StateExecutionContext) -> StateResult:
        """LOOT state - pick up loot."""
        self._check_exit_requested()
        self._update_ui(
            "LOOT", f"Looting... (kills: {self._kills}, loots: {self._loots_picked})"
        )

        # Try to pick up loot multiple times
        max_loot_attempts = 5
        loots_this_kill = 0

        for attempt in range(max_loot_attempts):
            # Check if inventory full
            if self._check_inventory_full():
                logger.info("Inventory full during looting, stopping")
                self._current_state = NPCKillerStates.COMPLETE
                return StateResult.SUCCESS

            # Record action for anti-ban
            if self.actions.anti_ban:
                self.actions.anti_ban.record_action("pickup_loot")

            # Try to pick up loot
            loot_found = self.actions.pickup_loot(tolerance=30)

            if not loot_found:
                # No more loot
                logger.debug(f"No loot found (attempt {attempt + 1}/{max_loot_attempts})")
                break

            # Picked up loot
            loots_this_kill += 1
            self._loots_picked += 1
            logger.info(f"Picked up loot! Total loots: {self._loots_picked}")

            # Wait between loot pickups
            self.actions.wait("short")

        if loots_this_kill > 0:
            logger.info(f"Looted {loots_this_kill} items this kill")
        else:
            logger.info("No loot found this kill")

        # Check inventory one more time before next kill
        if self._check_inventory_full():
            logger.info("Inventory full after looting, completing")
            self._current_state = NPCKillerStates.COMPLETE
            return StateResult.SUCCESS

        return StateResult.SUCCESS

    def _handle_complete(self, context: StateExecutionContext) -> StateResult:
        """COMPLETE state - bot finished."""
        self._update_ui(
            "COMPLETE",
            f"Finished! Kills: {self._kills}, Loots: {self._loots_picked}",
        )

        logger.info(
            f"Bot completed! Total kills: {self._kills}, Total loots: {self._loots_picked}"
        )

        return StateResult.SUCCESS
