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

        # Item template paths from config (override in config.json)
        self.OVERLOAD_TEMPLATE = self.config.get("templates", "overload_potion")
        self.ABSORPTION_TEMPLATE = self.config.get("templates", "absorption_potion")
        self.ROCK_CAKE_TEMPLATE = self.config.get("templates", "dwarven_rock_cake")
        self.LOCATOR_ORB_TEMPLATE = self.config.get("templates", "locator_orb")

    # ==================== NMZ-SPECIFIC ANTI-BAN HELPERS ====================

    def _anti_ban_call(self, method: str, fallback, *args, **kwargs):
        """
        Call anti-ban service method with fallback if unavailable.

        Args:
            method: Name of the anti-ban service method to call
            fallback: Value or callable to use if anti-ban service unavailable
            *args, **kwargs: Arguments to pass to the anti-ban method

        Returns:
            Result from anti-ban method or fallback value
        """
        if hasattr(self.actions, 'anti_ban') and self.actions.anti_ban:
            return getattr(self.actions.anti_ban, method)(*args, **kwargs)
        return fallback() if callable(fallback) else fallback

    def _is_in_missed_dose_recovery(self) -> bool:
        """
        Check if currently in missed dose state (waiting for HP recovery).

        This is NMZ-specific state tracking (not in AntiBanService).

        Returns:
            True if in missed dose recovery mode
        """
        return hasattr(self, '_missed_dose_recovery') and self._missed_dose_recovery

    def _record_action(self, action: str) -> None:
        """Record action for anti-ban pattern tracking."""
        if hasattr(self.actions, 'anti_ban') and self.actions.anti_ban:
            self.actions.anti_ban.record_action(action)

    def _click_item_or_fail(self, template: str, item_name: str) -> bool:
        """
        Click item template with error logging.

        Args:
            template: Path to template image
            item_name: Name of item for logging

        Returns:
            True if click successful, False otherwise
        """
        if self.actions.click_template(template, item_name):
            return True
        logger.error(f"Failed to find {item_name}")
        return False

    def _assign_dose_variance(self, variance_attr: str, dose_type: str, elapsed_threshold: float, elapsed: float) -> None:
        """
        Assign human-like variance for potion redosing.

        Args:
            variance_attr: Name of variance attribute to set (e.g., '_overload_variance')
            dose_type: Type of dose for logging (e.g., 'overload', 'absorption')
            elapsed_threshold: Seconds before starting to assign variance
            elapsed: Current elapsed time since last dose
        """
        if getattr(self, variance_attr) == 0.0 and elapsed >= elapsed_threshold:
            # Check for missed dose simulation (4% chance)
            if self._anti_ban_call('should_miss_action', False, chance=0.04):
                variance = self._anti_ban_call('get_missed_action_delay', lambda: random.uniform(90, 180), min_delay=90, max_delay=180)
                setattr(self, variance_attr, variance)
                self._missed_dose_recovery = True
                logger.info(f"ANTI-BAN: Missed {dose_type} dose - will redose in {variance:.0f}s (simulating AFK)")
            else:
                # Generate human-like variance (80% late, 20% on-time)
                variance = self._anti_ban_call('get_human_action_variance', lambda: random.uniform(0, 20), dose_type)
                setattr(self, variance_attr, variance)
                logger.debug(f"COMBAT_LOOP: Set {dose_type} variance to {variance:.0f}s")

    # ==================== STATE MACHINE METHODS ====================

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
        Get all player stats (HP, prayer, run energy, special attack) using template OCR.

        Returns:
            Dictionary with keys: 'hp', 'prayer', 'run', 'spec'
            Values are integers or None if detection fails

        Example:
            {'hp': 99, 'prayer': 70, 'run': 100, 'spec': 55}
        """
        stats = {}

        # Get HP
        stats['hp'] = self.state.get_hp(force=True)

        # Get Prayer
        stats['prayer'] = self.state.get_prayer(force=True)

        # Get Run Energy
        stats['run'] = self.state.get_run_energy(force=True)

        # Get Special Attack
        stats['spec'] = self.state.get_special_attack_percentage(force=True)

        return stats

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

    def _needs_redose(self, last_time: float, duration: int) -> bool:
        """Check if potion needs to be re-dosed based on timer."""
        if last_time == 0.0:
            return True  # First dose
        return time.time() - last_time >= duration

    def _needs_overload(self) -> bool:
        """Check if overload needs to be re-dosed (every 5 minutes)."""
        return self._needs_redose(self._last_overload_time, self.OVERLOAD_DURATION)

    def _needs_absorption(self) -> bool:
        """Check if absorption needs to be re-dosed (every 6.5 minutes)."""
        return self._needs_redose(self._last_absorption_time, self.ABSORPTION_DURATION)

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
            logger.warning(f"SAFETY CHECK: HP too low ({current_hp}) - cannot use locator orb (would die)")
            return False

        logger.info(f"Using locator orb (current HP: {current_hp})")

        if not self._click_item_or_fail(self.LOCATOR_ORB_TEMPLATE, "locator orb"):
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

        if self._needs_overload():
            logger.info("IDLE: Overload timer expired, starting setup")
            return StateResult.SUCCESS

        logger.info("IDLE: Timers active, entering combat loop")
        return StateResult.SUCCESS

    def _handle_drink_overload(self, context: StateExecutionContext) -> StateResult:
        """
        DRINK_OVERLOAD state - Drink overload potion.

        Overload deals 50 damage over ~20 seconds.

        Transitions:
        - WAIT_FOR_DAMAGE: After drinking overload
        """
        logger.info("[DRINK_OVERLOAD] Drinking overload potion...")

        self._record_action("drink_overload")

        if not self._click_item_or_fail(self.OVERLOAD_TEMPLATE, "overload potion"):
            return StateResult.FAILURE

        current_time = time.time()
        self._last_overload_time = current_time
        self._actual_overload_click_time = current_time
        logger.info("DRINK_OVERLOAD: Overload timer started")

        self.actions.wait("medium")
        return StateResult.SUCCESS

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
            return StateResult.SUCCESS

        logger.info(f"LOWER_HP: Current HP: {current_hp}, using locator orb")

        self._record_action("use_locator_orb")

        if not self._click_item_or_fail(self.LOCATOR_ORB_TEMPLATE, "locator orb"):
            return StateResult.FAILURE

        self.actions.wait("medium")

        new_hp = self._get_hp()
        if new_hp is None or new_hp > 1:
            logger.warning(f"LOWER_HP: HP not at 1 (current: {new_hp}), retrying")
            return StateResult.FAILURE

        logger.info("LOWER_HP: HP successfully lowered to 1")
        return StateResult.SUCCESS 

    def _handle_drink_absorption(self, context: StateExecutionContext) -> StateResult:
        """
        DRINK_ABSORPTION state - Drink absorption potions.

        Drinks absorption potion 6 times (full inventory).
        Each dose provides absorption points.

        Transitions:
        - COMBAT_LOOP: After drinking absorption
        """
        logger.info("[DRINK_ABSORPTION] Drinking absorption potions...")

        num_doses = 6
        for i in range(1, num_doses + 1):
            logger.info(f"DRINK_ABSORPTION: Dose {i}/{num_doses}")
            self._record_action("drink_absorption")

            if not self.actions.click_template(self.ABSORPTION_TEMPLATE, "absorption_potion"):
                logger.warning(f"DRINK_ABSORPTION: Failed to find absorption potion (dose {i})")
                break

            self.actions.wait("short")

        self._last_absorption_time = time.time()
        logger.info("DRINK_ABSORPTION: Absorption timer started")

        return StateResult.SUCCESS

    def _handle_combat_loop(self, context: StateExecutionContext) -> StateResult:

    # Loop for the duration of overload timer
        while True:
            # Check if user pressed 'q' to exit
            self._check_exit_requested()

            # ANTI-BAN: Check for zone-out (attention lapse)
            if self._anti_ban_call('should_zone_out', False, min_interval_minutes=10, chance_per_second=0.0005):
                zone_duration = random.uniform(30, 90)
                logger.info(f"ANTI-BAN: Zone-out / AFK burst ({zone_duration:.0f}s)")
                time.sleep(zone_duration)

            current_hp = self._get_hp()
            if current_hp is None:
                logger.warning("COMBAT_LOOP: HP detection failed, retrying...")
                self.actions.wait("medium")
                continue

            logger.info(f"COMBAT_LOOP: Current HP: {current_hp}")

            overload_elapsed = time.time() - self._last_overload_time
            absorption_elapsed = time.time() - self._last_absorption_time

            # Dynamic HP threshold (changes every 3-8 loops for realism)
            if not hasattr(self, '_hp_threshold_change_counter'):
                self._hp_threshold_change_counter = 0
                self._hp_threshold_preference = random.randint(1, 10)
                logger.info(f"Initial HP threshold preference: {self._hp_threshold_preference}")

            self._hp_threshold_change_counter += 1
            if self._hp_threshold_change_counter >= random.randint(3, 8):
                self._hp_threshold_preference = random.randint(1, 10)
                self._hp_threshold_change_counter = 0
                logger.debug(f"ANTI-BAN: HP threshold changed to: {self._hp_threshold_preference}")

            hp_threshold = self._hp_threshold_preference

            self._assign_dose_variance('_overload_variance', 'overload', 290, overload_elapsed)

            if overload_elapsed >= (self.OVERLOAD_DURATION + self._overload_variance):
                logger.info(f"COMBAT_LOOP: Overload re-dose (elapsed: {overload_elapsed:.0f}s, variance: {self._overload_variance:.0f}s)")

                # ANTI-BAN: Apply fatigue-based reaction delay
                fatigue_mult = self._anti_ban_call('get_fatigue_multiplier', 1.0)
                reaction_delay = random.uniform(0.3, 0.8) * fatigue_mult
                logger.debug(f"ANTI-BAN: Reaction delay = {reaction_delay:.2f}s (fatigue: {fatigue_mult:.2f}x)")
                time.sleep(reaction_delay)

                self._record_action("redose_overload")
                self.actions.click_template(self.OVERLOAD_TEMPLATE, "overload_potion")

                self._actual_overload_click_time = time.time()
                self._last_overload_time = self._actual_overload_click_time
                self._overload_variance = 0.0

                if hasattr(self, '_missed_dose_recovery'):
                    self._missed_dose_recovery = False
                    logger.debug("ANTI-BAN: Missed dose recovery complete")

                self.actions.wait("short")

            # Check if HP needs to be lowered
            # SAFETY: Don't use locator orb near overload redose times
            # - 10s AFTER drinking overload (damage still ticking)
            # - 10s BEFORE needing to redose (HP needs to be 50+)

            # Use ACTUAL click time for safety window, not scheduled timer
            time_since_actual_overload = time.time() - self._actual_overload_click_time if self._actual_overload_click_time > 0 else 999
            time_until_overload = self.OVERLOAD_DURATION - overload_elapsed

            if current_hp >= hp_threshold:
                safety_after = random.uniform(8, 15)
                safety_before = random.uniform(8, 15)

                if self._is_in_missed_dose_recovery():
                    logger.debug(f"Skipping orb: In missed dose recovery, waiting for HP to recover naturally (HP: {current_hp})")
                elif time_since_actual_overload < safety_after:
                    logger.debug(f"Skipping orb: {time_since_actual_overload:.0f}s < {safety_after:.0f}s since overload")
                elif time_until_overload < safety_before:
                    logger.debug(f"Skipping orb: {time_until_overload:.0f}s < {safety_before:.0f}s until overload")
                else:
                    if random.random() < 0.05:
                        logger.debug("ANTI-BAN: Violating safety window (human error)")

                    logger.warning(f"COMBAT_LOOP: HP is {current_hp}, using locator orb (threshold: {hp_threshold})")

                    self.actions.wait("micro")
                    self._record_action("use_locator_orb_combat")
                    self._use_locator_orb_safe()
                    self.actions.wait("short")

            self._assign_dose_variance('_absorption_variance', 'absorption', 370, absorption_elapsed)

            if absorption_elapsed >= (self.ABSORPTION_DURATION + self._absorption_variance):
                logger.info(f"COMBAT_LOOP: Absorption re-dose (elapsed: {absorption_elapsed:.0f}s, variance: {self._absorption_variance:.0f}s)")

                # ANTI-BAN: Apply fatigue-based reaction delay
                fatigue_mult = self._anti_ban_call('get_fatigue_multiplier', 1.0)
                reaction_delay = random.uniform(0.3, 0.8) * fatigue_mult
                logger.debug(f"ANTI-BAN: Reaction delay = {reaction_delay:.2f}s (fatigue: {fatigue_mult:.2f}x)")
                time.sleep(reaction_delay)

                DOSES = random.randint(4, 6)
                for _ in range(1, DOSES + 1):
                    self._record_action("redose_absorption")
                    self.actions.click_template(self.ABSORPTION_TEMPLATE, "absorption_potion")
                    self._actual_absorption_click_time = time.time()
                    self.actions.wait("micro")

                self._last_absorption_time = self._actual_absorption_click_time
                self._absorption_variance = 0.0


            overload_remaining = self.OVERLOAD_DURATION - overload_elapsed
            absorption_remaining = self.ABSORPTION_DURATION - absorption_elapsed
            logger.info(f"COMBAT_LOOP: Overload Remaining: {overload_remaining:.0f}s, Absorption Remaining: {absorption_remaining:.0f}s")
            logger.info(f"COMBAT LOOP: Overload Elapsed: {overload_elapsed:.0f}s, Absorption Elapsed: {absorption_elapsed:.0f}s")

            # ANTI-BAN: Enhanced idle actions (20% chance per loop - more realistic fidgeting)
            if random.random() < 0.20:
                idle_action = random.choice(["check_spec", "mini_pause"])
                logger.debug(f"ANTI-BAN: Idle action '{idle_action}'")

                if idle_action == "check_spec":
                    try:
                        spec = self._get_special_attack_percentage()
                        logger.debug(f"COMBAT_LOOP: Spec: {spec}%")
                        self.actions.wait("short")
                    except Exception as e:
                        logger.debug(f"COMBAT_LOOP: Spec check failed - {e}")
                elif idle_action == "mini_pause":
                    self.actions.wait((1.5, 4.0))  # Brief freeze (checking phone, looking away)

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