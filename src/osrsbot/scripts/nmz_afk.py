"""
NMZ AFK Bot - Nightmare Zone 1 HP Absorption Strategy

This bot maintains 1 HP using absorption potions and locator orb.
Safe for AFK training with minimal ban risk (no prayer flicking).

Strategy:
1. Drink overload potion (boosts stats, deals 50 damage)
2. Lower HP to 1 using dwarven rock cake
3. Drink absorption potions (6 doses)
4. Monitor HP and use locator orb when HP >= 2 (SAFE - prevents death)
5. Re-dose overload every 5 minutes
6. Re-dose absorption every 5 minutes

Requirements:
- Start inside NMZ dream (manual entry)
- Inventory: Overload potions, Absorption potions, Dwarven rock cake, Locator orb
- No prayer flicking (uses locator orb instead)
- Ignores power-ups
"""

import logging
import time
from enum import Enum, auto
from typing import Optional

from osrsbot.core.state_machine_bot import StateMachineBot, StateResult

logger = logging.getLogger(__name__)


class NMZStates(Enum):
    """State definitions for NMZ AFK bot."""

    IDLE = auto()
    DRINK_OVERLOAD = auto()
    WAIT_FOR_DAMAGE = auto()
    LOWER_HP = auto()
    DRINK_ABSORPTION = auto()
    COMBAT_LOOP = auto()
    RECOVERY = auto()


class NMZAfkBot(StateMachineBot):
    """
    NMZ AFK bot using 1 HP absorption strategy.

    Uses locator orb instead of prayer flicking (safer for ban detection).
    Timer-based potion management for overload and absorption.
    """

    def __init__(self, **kwargs):
        """Initialize NMZ AFK bot with state machine."""
        super().__init__(**kwargs)

        # Timer tracking (in seconds)
        self._overload_timer: float = 0.0
        self._absorption_timer: float = 0.0
        self._last_overload_time: float = 0.0
        self._last_absorption_time: float = 0.0

        # Constants
        self.OVERLOAD_DURATION = 300  # 5 minutes
        self.ABSORPTION_DURATION = 300  # 5 minutes
        self.OVERLOAD_DAMAGE = 50  # Overload deals 50 damage
        self.TARGET_HP = 1  # Maintain 1 HP

        # Item template names (defined in config.json templates section)
        self.OVERLOAD_TEMPLATE = "overload_potion"
        self.ABSORPTION_TEMPLATE = "absorption_potion"
        self.ROCK_CAKE_TEMPLATE = "dwarven_rock_cake"
        self.LOCATOR_ORB_TEMPLATE = "locator_orb"

    def define_states(self) -> dict:
        """
        Define state machine with automatic retry and failover.

        States:
        - IDLE: Initial state, checks if setup is needed
        - DRINK_OVERLOAD: Drinks overload potion
        - WAIT_FOR_DAMAGE: Waits for overload damage to lower HP
        - LOWER_HP: Uses rock cake to lower HP to 1
        - DRINK_ABSORPTION: Drinks 6 doses of absorption
        - COMBAT_LOOP: Main AFK loop (monitors HP, re-doses timers)
        - RECOVERY: Error recovery state
        """
        return {
            NMZStates.IDLE: {
                "handler": self._idle_state,
                "max_retries": 2,
                "failover": NMZStates.RECOVERY,
            },
            NMZStates.DRINK_OVERLOAD: {
                "handler": self._drink_overload_state,
                "max_retries": 3,
                "failover": NMZStates.RECOVERY,
            },
            NMZStates.WAIT_FOR_DAMAGE: {
                "handler": self._wait_for_damage_state,
                "max_retries": 2,
                "failover": NMZStates.RECOVERY,
            },
            NMZStates.LOWER_HP: {
                "handler": self._lower_hp_state,
                "max_retries": 3,
                "failover": NMZStates.RECOVERY,
            },
            NMZStates.DRINK_ABSORPTION: {
                "handler": self._drink_absorption_state,
                "max_retries": 3,
                "failover": NMZStates.RECOVERY,
            },
            NMZStates.COMBAT_LOOP: {
                "handler": self._combat_loop_state,
                "max_retries": 3,
                "failover": NMZStates.RECOVERY,
            },
            NMZStates.RECOVERY: {
                "handler": self._recovery_state,
                "max_retries": 2,
                "failover": NMZStates.IDLE,
            },
        }

    def get_initial_state(self) -> Enum:
        """Start in IDLE state."""
        return NMZStates.IDLE

    # ==================== HELPER METHODS ====================

    def _get_hp(self) -> Optional[int]:
        """
        Get current HP using template OCR (fast).

        Returns:
            Current HP value or None if detection fails
        """
        hp = self.state.get_hp(force=True)
        if hp is None:
            logger.warning("Failed to read HP value")
        return hp

    def _needs_overload(self) -> bool:
        """Check if overload needs to be re-dosed (every 5 minutes)."""
        if self._last_overload_time == 0.0:
            return True  # First dose
        elapsed = time.time() - self._last_overload_time
        return elapsed >= self.OVERLOAD_DURATION

    def _needs_absorption(self) -> bool:
        """Check if absorption needs to be re-dosed (every 5 minutes)."""
        if self._last_absorption_time == 0.0:
            return True  # First dose
        elapsed = time.time() - self._last_absorption_time
        return elapsed >= self.ABSORPTION_DURATION

    def _reset_timers(self) -> None:
        """Reset all potion timers."""
        self._last_overload_time = 0.0
        self._last_absorption_time = 0.0
        logger.info("Timers reset")

    def _use_locator_orb_safe(self) -> bool:
        """
        SAFELY use locator orb to lower HP to 1.

        CRITICAL SAFETY CHECK:
        - Locator orb removes 10 HP
        - Must have HP >= 2 or player dies
        - Returns False if HP is too low

        Returns:
            True if orb was used successfully, False otherwise
        """
        current_hp = self._get_hp()
        if current_hp is None:
            logger.error("Cannot use locator orb - HP detection failed")
            return False

        if current_hp < 2:
            logger.warning(
                f"SAFETY CHECK: HP too low ({current_hp}) - "
                "cannot use locator orb (would die)"
            )
            return False

        logger.info(f"Using locator orb (current HP: {current_hp})")
        if not self.actions.click_item_template(self.LOCATOR_ORB_TEMPLATE):
            logger.error("Failed to click locator orb")
            return False

        self.actions.wait("medium")
        return True

    # ==================== STATE HANDLERS ====================

    def _idle_state(self) -> StateResult:
        """
        IDLE state - Check if initial setup is needed.

        Transitions:
        - DRINK_OVERLOAD: If overload timer expired or first run
        - COMBAT_LOOP: If timers are active and valid
        """
        logger.info("[IDLE] Checking potion timers...")

        # Check if we need to start the initial setup
        if self._needs_overload():
            logger.info("IDLE: Overload timer expired, starting setup")
            return self.transition(NMZStates.DRINK_OVERLOAD)

        # If timers are valid, go straight to combat loop
        logger.info("IDLE: Timers active, entering combat loop")
        return self.transition(NMZStates.COMBAT_LOOP)

    def _drink_overload_state(self) -> StateResult:
        """
        DRINK_OVERLOAD state - Drink overload potion.

        Overload deals 50 damage over ~20 seconds.

        Transitions:
        - WAIT_FOR_DAMAGE: After drinking overload
        """
        logger.info("[DRINK_OVERLOAD] Drinking overload potion...")

        # Click overload potion in inventory
        if not self.actions.click_item_template(self.OVERLOAD_TEMPLATE):
            logger.error("DRINK_OVERLOAD: Failed to find overload potion")
            return StateResult.FAILURE

        # Update timer
        self._last_overload_time = time.time()
        logger.info("DRINK_OVERLOAD: Overload timer started")

        self.actions.wait("medium")
        return self.transition(NMZStates.WAIT_FOR_DAMAGE)

    def _wait_for_damage_state(self) -> StateResult:
        """
        WAIT_FOR_DAMAGE state - Wait for overload to deal damage.

        Overload deals 50 damage over ~20 seconds.
        We wait until HP drops below the overload damage threshold.

        Transitions:
        - LOWER_HP: After HP drops from overload
        """
        logger.info("[WAIT_FOR_DAMAGE] Waiting for overload damage...")

        # Wait up to 30 seconds for HP to drop
        max_wait = 30
        start_time = time.time()

        while time.time() - start_time < max_wait:
            current_hp = self._get_hp()
            if current_hp is None:
                logger.warning("WAIT_FOR_DAMAGE: HP detection failed, waiting...")
                self.actions.wait("medium")
                continue

            logger.info(f"WAIT_FOR_DAMAGE: Current HP: {current_hp}")

            # If HP dropped significantly, overload is working
            if current_hp <= 60:  # Arbitrary threshold
                logger.info("WAIT_FOR_DAMAGE: HP dropped, overload is working")
                return self.transition(NMZStates.LOWER_HP)

            self.actions.wait("long")

        logger.warning("WAIT_FOR_DAMAGE: Timeout waiting for damage")
        return self.transition(NMZStates.LOWER_HP)

    def _lower_hp_state(self) -> StateResult:
        """
        LOWER_HP state - Use rock cake to lower HP to 1.

        Rock cake (guzzle) lowers HP to 1 HP instantly.

        Transitions:
        - DRINK_ABSORPTION: After HP is at 1
        """
        logger.info("[LOWER_HP] Lowering HP to 1 with rock cake...")

        current_hp = self._get_hp()
        if current_hp is None:
            logger.error("LOWER_HP: Cannot detect HP")
            return StateResult.FAILURE

        if current_hp <= 1:
            logger.info("LOWER_HP: Already at 1 HP, skipping")
            return self.transition(NMZStates.DRINK_ABSORPTION)

        # Click rock cake to guzzle
        logger.info(f"LOWER_HP: Current HP: {current_hp}, using rock cake")
        if not self.actions.click_item_template(self.ROCK_CAKE_TEMPLATE):
            logger.error("LOWER_HP: Failed to find rock cake")
            return StateResult.FAILURE

        self.actions.wait("medium")

        # Verify HP is at 1
        new_hp = self._get_hp()
        if new_hp is None or new_hp > 1:
            logger.warning(f"LOWER_HP: HP not at 1 (current: {new_hp}), retrying")
            return StateResult.FAILURE

        logger.info("LOWER_HP: HP successfully lowered to 1")
        return self.transition(NMZStates.DRINK_ABSORPTION)

    def _drink_absorption_state(self) -> StateResult:
        """
        DRINK_ABSORPTION state - Drink absorption potions.

        Drinks absorption potion 6 times (full inventory).
        Each dose provides absorption points.

        Transitions:
        - COMBAT_LOOP: After drinking absorption
        """
        logger.info("[DRINK_ABSORPTION] Drinking absorption potions...")

        # Click absorption potion 6 times (6 doses)
        num_doses = 6
        for i in range(1, num_doses + 1):
            logger.info(f"DRINK_ABSORPTION: Dose {i}/{num_doses}")
            if not self.actions.click_item_template(self.ABSORPTION_TEMPLATE):
                logger.warning(
                    f"DRINK_ABSORPTION: Failed to find absorption potion (dose {i})"
                )
                # Continue anyway - might have run out
                break

            self.actions.wait("short")

        # Update timer
        self._last_absorption_time = time.time()
        logger.info("DRINK_ABSORPTION: Absorption timer started")

        return self.transition(NMZStates.COMBAT_LOOP)

    def _combat_loop_state(self) -> StateResult:
        """
        COMBAT_LOOP state - Main AFK loop.

        Monitors:
        1. HP level (use locator orb if HP >= 2)
        2. Overload timer (re-dose every 5 minutes)
        3. Absorption timer (re-dose every 5 minutes)

        Transitions:
        - DRINK_OVERLOAD: If overload timer expired
        - DRINK_ABSORPTION: If absorption timer expired (but overload is valid)
        - COMBAT_LOOP: Loop continues
        """
        logger.info("[COMBAT_LOOP] Monitoring HP and timers...")

        # Check HP first (safety critical)
        current_hp = self._get_hp()
        if current_hp is None:
            logger.warning("COMBAT_LOOP: HP detection failed")
            return StateResult.FAILURE

        logger.info(f"COMBAT_LOOP: Current HP: {current_hp}")

        # SAFETY CHECK: Use locator orb if HP >= 2
        if current_hp >= 2:
            logger.warning(f"COMBAT_LOOP: HP is {current_hp}, using locator orb")
            if not self._use_locator_orb_safe():
                logger.error("COMBAT_LOOP: Failed to use locator orb")
                return StateResult.FAILURE

        # Check overload timer
        if self._needs_overload():
            logger.info("COMBAT_LOOP: Overload timer expired, re-dosing")
            return self.transition(NMZStates.DRINK_OVERLOAD)

        # Check absorption timer
        if self._needs_absorption():
            logger.info("COMBAT_LOOP: Absorption timer expired, re-dosing")
            return self.transition(NMZStates.DRINK_ABSORPTION)

        # Calculate time remaining on timers
        overload_remaining = (
            self.OVERLOAD_DURATION - (time.time() - self._last_overload_time)
        )
        absorption_remaining = (
            self.ABSORPTION_DURATION - (time.time() - self._last_absorption_time)
        )

        logger.info(
            f"COMBAT_LOOP: Overload: {overload_remaining:.0f}s, "
            f"Absorption: {absorption_remaining:.0f}s"
        )

        # Wait before next check
        self.actions.wait("long")
        return StateResult.SUCCESS  # Stay in COMBAT_LOOP

    def _recovery_state(self) -> StateResult:
        """
        RECOVERY state - Handle errors and reset.

        Attempts to recover from errors by resetting timers.

        Transitions:
        - IDLE: After recovery attempt
        """
        logger.warning("[RECOVERY] Attempting to recover from error...")

        # Reset timers to force re-setup
        self._reset_timers()

        # Wait a bit before retrying
        self.actions.wait("long")

        logger.info("RECOVERY: Timers reset, returning to IDLE")
        return self.transition(NMZStates.IDLE)
