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

# NOTE KNOWN_GOOD / PRODUCTION

import logging
import random
import time
from enum import Enum, auto
from typing import Optional

from osrsbot.core.state_machine_bot import StateMachineBot, StateResult
from osrsbot.core.state_helpers import build_metadata_dict
from osrsbot.core.state_types import (
    StateExecutionContext,
    StateMetadata,
    StateResult,
    StateTransition
)

logger = logging.getLogger(__name__)


class NMZStates(Enum):
    """State definitions for NMZ AFK bot."""

    IDLE = "idle"
    DRINK_OVERLOAD = "drink_overload"
    WAIT_FOR_DAMAGE = "wait_for_damage"
    LOWER_HP = "lower_hp"
    DRINK_ABSORPTION = "drink_absorption"
    COMBAT_LOOP = "combat_loop"
    RECOVERY = "recovery"


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

        # Track actual click time (for safety windows)
        self._actual_overload_click_time: float = 0.0
        self._actual_absorption_click_time: float = 0.0

        # Variance for current dose (set once per dose, not every loop)
        self._overload_variance: float = 0.0
        self._absorption_variance: float = 0.0

        # Constants
        self.OVERLOAD_DURATION = 300  # 5 minutes
        self.ABSORPTION_DURATION = 390  # 6 minutes 30 seconds
        self.OVERLOAD_DAMAGE = 50  # Overload deals 50 damage
        self.TARGET_HP = 1  # Maintain 1 HP

        # NOTE: Lazily hardcoded template paths for now.
        # Should be moved to TemplateMatchService/config once this bot is stable.
        # Item template names (defined in config.json templates section)
        self.OVERLOAD_TEMPLATE = "src/osrsbot/images/bot/items/overload_potion.png"
        self.ABSORPTION_TEMPLATE = "src/osrsbot/images/bot/items/absorption_potion.png"
        self.ROCK_CAKE_TEMPLATE = "src/osrsbot/images/bot/items/dwarven_rock_cake.png"
        self.LOCATOR_ORB_TEMPLATE = "src/osrsbot/images/bot/items/locator_orb.png"

    def define_states(self) -> type[Enum]:
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
        return NMZStates
        

    def define_transitions(self) -> list[StateTransition]:
        return [
            StateTransition(NMZStates.IDLE, NMZStates.DRINK_OVERLOAD),
            StateTransition(NMZStates.DRINK_OVERLOAD, NMZStates.WAIT_FOR_DAMAGE),
            StateTransition(NMZStates.WAIT_FOR_DAMAGE, NMZStates.LOWER_HP),
            StateTransition(NMZStates.LOWER_HP, NMZStates.DRINK_ABSORPTION),
            StateTransition(NMZStates.DRINK_ABSORPTION, NMZStates.COMBAT_LOOP),
            StateTransition(NMZStates.COMBAT_LOOP, NMZStates.DRINK_OVERLOAD),
            StateTransition(NMZStates.COMBAT_LOOP, NMZStates.DRINK_ABSORPTION),
            StateTransition(NMZStates.COMBAT_LOOP, NMZStates.COMBAT_LOOP),
            StateTransition(NMZStates.RECOVERY, NMZStates.IDLE),
        ]


    def define_state_metadata(self) -> dict[Enum, StateMetadata]:
        return build_metadata_dict(
            NMZStates,
            {
                NMZStates.IDLE: {
                    "name": "Idle",
                    "description": "Check if initial setup is needed.",
                    "max_retries": 3,
                },
                NMZStates.DRINK_OVERLOAD: {
                    "name": "Drink Overload",
                    "description": "Drink overload potion to boost stats.",
                    "max_retries": 2,
                },
                NMZStates.WAIT_FOR_DAMAGE: {
                    "name": "Wait for Damage",
                    "description": "Wait for overload to deal damage.",
                    "max_retries": 3,
                },
                NMZStates.LOWER_HP: {
                    "name": "Lower HP",
                    "description": "Use locator orb to lower HP to 1.",
                    "max_retries": 6,
                },
                NMZStates.DRINK_ABSORPTION: {
                    "name": "Drink Absorption",
                    "description": "Drink absorption potions.",
                    "max_retries": 2,
                },
                NMZStates.COMBAT_LOOP: {
                    "name": "Combat Loop",
                    "description": "Main AFK loop monitoring HP and timers.",
                    "max_retries": 5,
                },
                NMZStates.RECOVERY: {
                    "name": "Recovery",
                    "description": "Attempt to recover from errors.",
                    "max_retries": 1,
                },
            }
        )

    def get_initial_state(self) -> Enum:
        """Start in IDLE state."""
        return NMZStates.IDLE

    # ==================== HELPER METHODS ====================

    def _get_all_stats(self) -> dict[str, Optional[int]]:
        """
        Get all player stats using template OCR.

        Returns:
            dict with keys: hp, prayer, run, spec
        """
        return self.state.get_all_stats(force=True)

    def _get_special_attack_percentage(self) -> Optional[int]:
        """
        Get current special attack percentage using template OCR (fast).

        Returns:
            Current special attack percentage or None if detection fails
        """
        spec = self.state.get_special_attack_percentage(force=True)
        if spec is None:
            logger.warning("Failed to read special attack percentage")
        return spec

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
        
        if not self.actions.click_template(self.LOCATOR_ORB_TEMPLATE, "locator_orb"):
            logger.error("Failed to click locator orb")
            return False

        self.actions.wait("medium")
        return True

    # ==================== STATE HANDLERS ====================

    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
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
            return StateResult.SUCCESS# Go to DRINK_OVERLOAD

        # If timers are valid, go straight to combat loop
        logger.info("IDLE: Timers active, entering combat loop")
        return StateResult.SUCCESS  # Go to COMBAT_LOOP

    def _handle_drink_overload(self, context: StateExecutionContext) -> StateResult:
        """
        DRINK_OVERLOAD state - Drink overload potion.

        Overload deals 50 damage over ~20 seconds.

        Transitions:
        - WAIT_FOR_DAMAGE: After drinking overload
        """
        logger.info("[DRINK_OVERLOAD] Drinking overload potion...")

        # Record action for anti-ban pattern detection
        if hasattr(self.actions, 'anti_ban') and self.actions.anti_ban:
            self.actions.anti_ban.record_action("drink_overload")

        # Click overload potion in inventory
        if not self.actions.click_template(self.OVERLOAD_TEMPLATE, "overload_potion"):
            logger.error("DRINK_OVERLOAD: Failed to find overload potion")
            return StateResult.FAILURE

        # Update timers (both scheduled and actual click time)
        current_time = time.time()
        self._last_overload_time = current_time
        self._actual_overload_click_time = current_time
        logger.info("DRINK_OVERLOAD: Overload timer started")

        self.actions.wait("medium")
        return StateResult.SUCCESS  # Go to WAIT_FOR_DAMAGE

    def _handle_wait_for_damage(self, context: StateExecutionContext) -> StateResult:
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
            if current_hp <= 50:  # Arbitrary threshold
                logger.info("WAIT_FOR_DAMAGE: HP dropped, overload is working")
                self.actions.wait("long")
                return StateResult.SUCCESS  # Go to LOWER_HP

            self.actions.wait("long")

        logger.warning("WAIT_FOR_DAMAGE: Timeout waiting for damage")
        return StateResult.FAILURE

    def _handle_lower_hp(self, context: StateExecutionContext) -> StateResult:
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
            return StateResult.SUCCESS  # Go to DRINK_ABSORPTION

        #Click rock cake to guzzle
        logger.info(f"LOWER_HP: Current HP: {current_hp}, using locator orb")

        # Record action for anti-ban pattern detection
        if hasattr(self.actions, 'anti_ban') and self.actions.anti_ban:
            self.actions.anti_ban.record_action("use_locator_orb")

        if not self.actions.click_template(self.LOCATOR_ORB_TEMPLATE, "locator_orb"):
            logger.error("LOWER_HP: Failed to find locator orb")
            return StateResult.FAILURE

        self.actions.wait("medium")

        # Verify HP is at 1
        new_hp = self._get_hp()
        if new_hp is None or new_hp > 1:
            logger.warning(f"LOWER_HP: HP not at 1 (current: {new_hp}), retrying")
            return StateResult.FAILURE

        logger.info("LOWER_HP: HP successfully lowered to 1")
        return StateResult.SUCCESS  # Go to DRINK_ABSORPTION 

    def _handle_drink_absorption(self, context: StateExecutionContext) -> StateResult:
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

            # Record action for anti-ban pattern detection
            if hasattr(self.actions, 'anti_ban') and self.actions.anti_ban:
                self.actions.anti_ban.record_action("drink_absorption")

            if not self.actions.click_template(self.ABSORPTION_TEMPLATE, "absorption_potion"):
                logger.warning(
                    f"DRINK_ABSORPTION: Failed to find absorption potion (dose {i})"
                )
                # Continue anyway - might have run out
                break

            self.actions.wait("short")

        # Update timer
        self._last_absorption_time = time.time()
        logger.info("DRINK_ABSORPTION: Absorption timer started")

        return StateResult.SUCCESS  # Go to COMBAT_LOOP

    def _handle_combat_loop(self, context: StateExecutionContext) -> StateResult:

    # Loop for the duration of overload timer
        while True:
            current_hp = self._get_hp()
            if current_hp is None:
                logger.warning("COMBAT_LOOP: HP detection failed, retrying...")
                self.actions.wait("medium")
                continue

            logger.info(f"COMBAT_LOOP: Current HP: {current_hp}")

            # Check timers
            overload_elapsed = time.time() - self._last_overload_time
            absorption_elapsed = time.time() - self._last_absorption_time

            # Generate HP threshold once per session (player personality)
            if not hasattr(self, '_hp_threshold_preference'):
                self._hp_threshold_preference = random.randint(2, 6)
                logger.info(f"Session HP threshold preference: {self._hp_threshold_preference}")

            # Use preference with occasional variance
            hp_threshold = self._hp_threshold_preference
            if random.random() < 0.15:  # 15% chance to vary
                hp_threshold = random.randint(2, 9)

            # Check if overload needs redose (with variance)
            # Set variance once per dose cycle, not every loop iteration
            if self._overload_variance == 0.0 and overload_elapsed >= 290:
                # Generate variance when approaching redose time (humans react slightly late, not early)
                self._overload_variance = random.uniform(0, 20)
                logger.debug(f"COMBAT_LOOP: Set overload variance to {self._overload_variance:.0f}s")

            if overload_elapsed >= (self.OVERLOAD_DURATION + self._overload_variance):
                logger.info(f"COMBAT_LOOP: Overload re-dose (elapsed: {overload_elapsed:.0f}s, variance: {self._overload_variance:.0f}s)")

                # Add pre-click pause (human reaction time)
                self.actions.wait("micro")

                # Record action for anti-ban pattern detection
                if hasattr(self.actions, 'anti_ban') and self.actions.anti_ban:
                    self.actions.anti_ban.record_action("redose_overload")

                self.actions.click_template(self.OVERLOAD_TEMPLATE, "overload_potion")

                # Track actual click time for safety windows AND timer tracking
                self._actual_overload_click_time = time.time()

                # Reset timer to actual click time (when overload effect actually started)
                # This prevents desync between scheduled time and actual effect duration
                self._last_overload_time = self._actual_overload_click_time

                # Reset variance for next dose
                self._overload_variance = 0.0

                # Post-click pause
                self.actions.wait("short")

            # Check if HP needs to be lowered
            # SAFETY: Don't use locator orb near overload redose times
            # - 10s AFTER drinking overload (damage still ticking)
            # - 10s BEFORE needing to redose (HP needs to be 50+)

            # Use ACTUAL click time for safety window, not scheduled timer
            time_since_actual_overload = time.time() - self._actual_overload_click_time if self._actual_overload_click_time > 0 else 999
            time_until_overload = self.OVERLOAD_DURATION - overload_elapsed

            if current_hp >= hp_threshold:
                # Too soon after overload? (damage still happening)
                if time_since_actual_overload < 10:
                    logger.debug(f"Skipping orb: only {time_since_actual_overload:.0f}s since actual overload click (need 10s)")
                # Too close to next overload? (need HP to stay high)
                elif time_until_overload < 10:
                    logger.debug(f"Skipping orb: only {time_until_overload:.0f}s until overload (need 10s)")
                else:
                    # Safe to use orb
                    logger.warning(f"COMBAT_LOOP: HP is {current_hp}, using locator orb (threshold: {hp_threshold})")

                    # Add pre-action pause (human reaction time)
                    self.actions.wait("micro")

                    # Record action for anti-ban pattern detection
                    if hasattr(self.actions, 'anti_ban') and self.actions.anti_ban:
                        self.actions.anti_ban.record_action("use_locator_orb_combat")

                    self._use_locator_orb_safe()

                    # Post-action pause
                    self.actions.wait("short")
            
            # NOTE: not needed for now - absorption should outlast overload
            # Check if absorption needs redose
            #time_until_actual_absorption = self.ABSORPTION_DURATION - (time.time() - self._actual_absorption_click_time) if self._actual_absorption_click_time > 0 else 999
            #time_until_absorption = self.ABSORPTION_DURATION - self.ABSORPTION_DURATION - absorption_elapsed

            # Check if absorption needs redose (with variance)
            # Set variance once per dose cycle, not every loop iteration
            if self._absorption_variance == 0.0 and absorption_elapsed >= 370:
                # Generate variance when approaching redose time (humans react slightly late, not early)
                self._absorption_variance = random.uniform(0, 30)
                logger.debug(f"COMBAT_LOOP: Set absorption variance to {self._absorption_variance:.0f}s")

            if absorption_elapsed >= (self.ABSORPTION_DURATION + self._absorption_variance):
                logger.info(f"COMBAT_LOOP: Absorption re-dose (elapsed: {absorption_elapsed:.0f}s, variance: {self._absorption_variance:.0f}s)")

                # Pre-action pause
                self.actions.wait("micro")

                # Vary number of doses (4-6 instead of exactly 5)
                DOSES = random.randint(4, 6)
                for _ in range(1, DOSES + 1):
                    # Record action for anti-ban pattern detection
                    if hasattr(self.actions, 'anti_ban') and self.actions.anti_ban:
                        self.actions.anti_ban.record_action("redose_absorption")

                    self.actions.click_template(self.ABSORPTION_TEMPLATE, "absorption_potion")
                    self._actual_absorption_click_time = time.time()
                    # Small variance between clicks
                    self.actions.wait("micro")

                # Reset timer to when it SHOULD have been reset (prevents timer drift)
                # If we clicked at 410s (390 + 20s variance), set timer to 390s mark
                self._last_absorption_time = self._actual_absorption_click_time 

                # Reset variance for next dose
                self._absorption_variance = 0.0



            # Log time remaining
            overload_remaining = self.OVERLOAD_DURATION - overload_elapsed
            absorption_remaining = self.ABSORPTION_DURATION - absorption_elapsed
            
            logger.info(
                f"COMBAT_LOOP: Overload Remaining Time: {overload_remaining:.0f}s,\n Absorption Remaining Time: {absorption_remaining:.0f}s"
                        )

            logger.info(f"COMBAT LOOP: Overload Elapsed Time: {overload_elapsed:.0f}s,\nAbsorption Elapsed Time: {absorption_elapsed:.0f}s"
                        )

            # Occasionally perform idle action (3% chance per loop iteration)
            if random.random() < 0.03:
                idle_action = random.choice(["check_spec", "mini_pause"])

                if idle_action == "check_spec":
                    # Check special attack percentage (use existing method)
                    logger.debug("COMBAT_LOOP: Idle action - checking spec")
                    try:
                        spec = self._get_special_attack_percentage()
                        logger.debug(f"COMBAT_LOOP: Spec: {spec}%")
                        self.actions.wait("short")
                    except Exception as e:
                        logger.debug(f"COMBAT_LOOP: Spec check failed - {e}")

                elif idle_action == "mini_pause":
                    # Brief freeze (checking phone, looking away)
                    logger.debug("COMBAT_LOOP: Idle action - mini pause")
                    # Use framework's wait system with custom timing range
                    self.actions.wait((1.5, 4.0))

            # Wait before next loop iteration
            self.actions.wait("medium")


    def _handle_recovery(self, context: StateExecutionContext) -> StateResult:
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
        return StateResult.SUCCESS  # Go to IDLE