"""
Zulrah Boss Bot

Complete implementation using color-coded tile markers for positioning
and computer vision for combat management.

Uses hybrid approach:
- Tile markers for safe spot positioning
- CV for form detection and combat
- Config-driven rotation data
"""

import logging
from enum import Enum
from typing import Dict, List, Optional

from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_types import StateMetadata, StateResult, StateTransition, StateExecutionContext

from osrsbot.scripts.bosses.zulrah_detector import ZulrahDetector
from osrsbot.scripts.bosses.zulrah_navigator import ZulrahNavigator
from osrsbot.scripts.bosses.zulrah_combat_manager import ZulrahCombatManager

logger = logging.getLogger(__name__)


# --- Zulrah Phase Tracking ---

class ZulrahPhase(str, Enum):
    """Zulrah phase types for rotation tracking."""
    SERP_MID = "serp_middle"
    SERP_EAST = "serp_east"
    SERP_WEST = "serp_west"
    SERP_SOUTH = "serp_south"
    SERP_NORTH = "serp_north"
    MAGMA_MID = "magma_middle"
    TANZ_MID = "tanz_middle"
    TANZ_EAST = "tanz_east"
    TANZ_WEST = "tanz_west"
    TANZ_SOUTH = "tanz_south"
    TANZ_NORTH = "tanz_north"
    JAD_WEST = "jad_west"
    JAD_EAST = "jad_east"


class ZulrahRotation(str, Enum):
    """Zulrah rotation patterns."""
    ROTATION_1 = "rotation_1"
    ROTATION_2 = "rotation_2"
    ROTATION_3 = "rotation_3"
    ROTATION_4 = "rotation_4"


class ZulrahFightManager:
    """
    Tracks rotation and phase progression.
    Uses existing rotation detection logic.
    """

    def __init__(self):
        self.current_rotation: Optional[int] = None
        self.current_phase_index: int = 0
        self.observed_phases: List[ZulrahPhase] = []

        # Rotation sequences for detection
        self.sequences = {
            1: [
                ZulrahPhase.SERP_MID, ZulrahPhase.TANZ_SOUTH, ZulrahPhase.SERP_WEST,
                ZulrahPhase.TANZ_SOUTH, ZulrahPhase.MAGMA_MID, ZulrahPhase.TANZ_WEST,
                ZulrahPhase.SERP_MID, ZulrahPhase.TANZ_EAST, ZulrahPhase.TANZ_MID,
                ZulrahPhase.JAD_WEST
            ],
            2: [
                ZulrahPhase.TANZ_MID, ZulrahPhase.SERP_NORTH, ZulrahPhase.SERP_WEST,
                ZulrahPhase.TANZ_SOUTH, ZulrahPhase.SERP_MID, ZulrahPhase.SERP_WEST,
                ZulrahPhase.TANZ_WEST, ZulrahPhase.SERP_MID, ZulrahPhase.TANZ_EAST,
                ZulrahPhase.SERP_MID, ZulrahPhase.JAD_EAST
            ],
            3: [
                ZulrahPhase.SERP_MID, ZulrahPhase.SERP_WEST, ZulrahPhase.TANZ_SOUTH,
                ZulrahPhase.SERP_MID, ZulrahPhase.TANZ_EAST, ZulrahPhase.SERP_NORTH,
                ZulrahPhase.TANZ_WEST, ZulrahPhase.SERP_MID, ZulrahPhase.TANZ_WEST,
                ZulrahPhase.SERP_MID, ZulrahPhase.JAD_WEST
            ],
            4: [
                ZulrahPhase.TANZ_MID, ZulrahPhase.SERP_EAST, ZulrahPhase.TANZ_SOUTH,
                ZulrahPhase.SERP_WEST, ZulrahPhase.TANZ_EAST, ZulrahPhase.MAGMA_MID,
                ZulrahPhase.SERP_WEST, ZulrahPhase.TANZ_EAST, ZulrahPhase.SERP_MID,
                ZulrahPhase.TANZ_WEST, ZulrahPhase.JAD_EAST
            ]
        }

    def detect_phase_type(self, form: str, position: str) -> Optional[ZulrahPhase]:
        """Map form + position to phase type."""
        # Normalize inputs
        form = form.lower() if form else ""
        position = position.lower() if position else ""

        # Handle form name variations
        if "serpentine" in form or "serp" in form:
            form = "serp"
        elif "tanzanite" in form or "tanz" in form:
            form = "tanz"
        elif "magma" in form:
            form = "magma"

        # Create mapping
        mapping = {
            ("serp", "middle"): ZulrahPhase.SERP_MID,
            ("serp", "east"): ZulrahPhase.SERP_EAST,
            ("serp", "west"): ZulrahPhase.SERP_WEST,
            ("serp", "south"): ZulrahPhase.SERP_SOUTH,
            ("serp", "north"): ZulrahPhase.SERP_NORTH,
            ("magma", "middle"): ZulrahPhase.MAGMA_MID,
            ("tanz", "middle"): ZulrahPhase.TANZ_MID,
            ("tanz", "east"): ZulrahPhase.TANZ_EAST,
            ("tanz", "west"): ZulrahPhase.TANZ_WEST,
            ("tanz", "south"): ZulrahPhase.TANZ_SOUTH,
            ("tanz", "north"): ZulrahPhase.TANZ_NORTH,
        }

        return mapping.get((form, position))

    def update_rotation(self, phase_type: ZulrahPhase):
        """
        Update rotation based on observed phase.
        Identifies rotation after 2-4 phases.
        """
        if not phase_type:
            return

        self.observed_phases.append(phase_type)
        phase_count = len(self.observed_phases)

        if self.current_rotation:
            return  # Already identified

        # Try to identify rotation based on observed phases
        if phase_count == 2:
            # Check second phase
            if phase_type == ZulrahPhase.SERP_EAST:
                self.current_rotation = 4
                logger.info("Rotation 4 identified (SERP_EAST at phase 2)")
            elif phase_type == ZulrahPhase.SERP_NORTH:
                self.current_rotation = 2
                logger.info("Rotation 2 identified (SERP_NORTH at phase 2)")
            elif phase_type == ZulrahPhase.SERP_WEST:
                self.current_rotation = 3
                logger.info("Rotation 3 identified (SERP_WEST at phase 2)")
            elif phase_type == ZulrahPhase.TANZ_SOUTH:
                self.current_rotation = 1
                logger.info("Rotation 1 identified (TANZ_SOUTH at phase 2)")

        elif phase_count >= 4 and not self.current_rotation:
            # Fallback identification at phase 4
            logger.warning("Rotation not identified by phase 2, using fallback")
            # Default to rotation 1
            self.current_rotation = 1


# --- State Machine Implementation ---

class ZulrahStates(Enum):
    """Zulrah bot states."""
    # Pre-fight
    START = "start"
    BANK = "bank"
    TRAVEL_TO_ZULRAH = "travel"

    # Rotation identification
    IDENTIFY_ROTATION = "identify_rotation"

    # Combat loop
    POSITION_FOR_PHASE = "position_for_phase"
    SWITCH_GEAR_PRAYER = "switch_gear_prayer"
    ATTACK_ZULRAH = "attack_zulrah"
    KILL_SNAKELINGS = "kill_snakelings"

    # Survival
    EAT_FOOD = "eat_food"
    DRINK_PRAYER = "drink_prayer"

    # End states
    LOOT = "loot"
    DEATH_RECOVERY = "death_recovery"
    TELEPORT_OUT = "teleport_out"
    END = "end"


class ZulrahBot(StateMachineBot):
    """
    Zulrah boss bot using hybrid CV + tile marker approach.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize helper classes
        self.fight_manager = ZulrahFightManager()
        self.detector = ZulrahDetector(
            self.screen,
            self.template_service,
            self.config
        )
        self.navigator = ZulrahNavigator(
            self.mouse,
            self.detector,
            self.actions
        )
        self.combat_manager = ZulrahCombatManager(
            self.actions,
            self.queries,
            self.screen,
            self.config
        )

        # Track kills
        self.kills = 0

    def define_states(self):
        return ZulrahStates

    def define_state_metadata(self) -> Dict[Enum, StateMetadata]:
        return {
            ZulrahStates.START: StateMetadata(max_retries=1, timeout=5),
            ZulrahStates.IDENTIFY_ROTATION: StateMetadata(max_retries=10, timeout=30),
            ZulrahStates.POSITION_FOR_PHASE: StateMetadata(max_retries=3, timeout=5),
            ZulrahStates.SWITCH_GEAR_PRAYER: StateMetadata(max_retries=2, timeout=3),
            ZulrahStates.ATTACK_ZULRAH: StateMetadata(max_retries=20, timeout=30),
            ZulrahStates.KILL_SNAKELINGS: StateMetadata(max_retries=5, timeout=10),
            ZulrahStates.EAT_FOOD: StateMetadata(max_retries=2, timeout=2),
            ZulrahStates.DRINK_PRAYER: StateMetadata(max_retries=2, timeout=2),
            ZulrahStates.LOOT: StateMetadata(max_retries=3, timeout=10),
            ZulrahStates.DEATH_RECOVERY: StateMetadata(max_retries=1, timeout=5),
            ZulrahStates.END: StateMetadata(max_retries=0, timeout=1),
        }

    def define_transitions(self) -> List[StateTransition]:
        # Simplified - using dynamic transitions instead
        return [
            StateTransition(ZulrahStates.START, ZulrahStates.IDENTIFY_ROTATION),
        ]

    def get_initial_state(self):
        return ZulrahStates.START

    # --- State Handlers ---

    def _handle_start(self, context: StateExecutionContext) -> StateResult:
        """Initialize fight."""
        logger.info("=" * 60)
        logger.info("Zulrah Boss Bot Started")
        logger.info("=" * 60)

        # Reset fight manager
        self.fight_manager = ZulrahFightManager()

        return StateResult.SUCCESS

    def _handle_identify_rotation(self, context: StateExecutionContext) -> StateResult:
        """
        Observe first 2-4 phases to identify rotation.
        """
        # Detect current Zulrah form and position
        form = self.detector.detect_zulrah_form()
        position = self.detector.detect_zulrah_position()

        if not form or not position:
            logger.debug("Waiting for Zulrah to appear...")
            self.actions.wait("short")
            return StateResult.RETRY

        # Update fight manager with observed phase
        phase_type = self.fight_manager.detect_phase_type(form, position)

        if phase_type:
            self.fight_manager.update_rotation(phase_type)
            logger.info(f"Observed phase: {phase_type}")

        # Check if rotation identified
        if self.fight_manager.current_rotation:
            logger.info(f"✓ Rotation {self.fight_manager.current_rotation} identified!")
            self.fight_manager.current_phase_index = 0  # Reset for combat loop
            return StateResult.SUCCESS

        # Need more observations
        logger.debug(f"Phases observed: {len(self.fight_manager.observed_phases)}")
        self.actions.wait("medium")
        return StateResult.RETRY

    def _handle_position_for_phase(self, context: StateExecutionContext) -> StateResult:
        """Move to safe spot for current phase."""
        # Get current phase data from config
        current_phase = self._get_current_phase_data()

        if not current_phase:
            logger.error("No phase data available!")
            return StateResult.FAILURE

        # Get safe position name
        safe_position = current_phase.get("safe_position")
        if not safe_position:
            logger.error("No safe_position in phase data!")
            return StateResult.FAILURE

        # Look up tile color
        tile_colors = self.config.get("zulrah", {}).get("tile_colors", {})
        tile_color = tile_colors.get(safe_position)

        if not tile_color:
            logger.error(f"No tile color for position: {safe_position}")
            return StateResult.FAILURE

        # Navigate to safe spot
        logger.info(f"Moving to {safe_position} (color: {tile_color})")
        success = self.navigator.move_to_safe_spot(tile_color)

        if success:
            logger.info(f"✓ Reached safe spot: {safe_position}")
            return StateResult.SUCCESS
        else:
            logger.warning("Failed to find tile marker, trying emergency move")
            self.navigator.emergency_move()
            return StateResult.RETRY

    def _handle_switch_gear_prayer(self, context: StateExecutionContext) -> StateResult:
        """Switch gear and prayer for current phase."""
        current_phase = self._get_current_phase_data()

        if not current_phase:
            return StateResult.FAILURE

        # Switch prayer (CRITICAL)
        prayer = current_phase.get("prayer")
        if prayer:
            prayer_success = self.combat_manager.switch_prayer(prayer)
            if not prayer_success:
                logger.error(f"Failed to switch prayer to {prayer}")
                return StateResult.RETRY

        # Switch gear (less critical)
        attack_style = current_phase.get("attack_style")
        if attack_style:
            self.combat_manager.switch_gear(attack_style)

        logger.info(f"✓ Gear/Prayer set for phase {self.fight_manager.current_phase_index}")
        return StateResult.SUCCESS

    def _handle_attack_zulrah(self, context: StateExecutionContext) -> StateResult:
        """Attack Zulrah until phase complete."""
        # Check if user pressed 'q' to exit
        self._check_exit_requested()

        # Check if Zulrah submerged (phase transition)
        if not self.detector.is_zulrah_visible():
            logger.info("Zulrah submerged - phase complete")
            self._advance_phase()
            return StateResult.SUCCESS

        # Attack
        if self.combat_manager.attack_zulrah():
            logger.debug("Attacking Zulrah")
            self.actions.wait("short")
            return StateResult.RETRY
        else:
            logger.warning("Could not target Zulrah")
            self.actions.wait("short")
            return StateResult.RETRY

    def _handle_kill_snakelings(self, context: StateExecutionContext) -> StateResult:
        """Handle snakeling spawns."""
        snakelings = self.detector.detect_snakelings()

        if not snakelings:
            logger.debug("No snakelings detected")
            return StateResult.SUCCESS

        # Attack first snakeling
        snakeling_pos = snakelings[0]
        logger.info(f"Attacking snakeling ({len(snakelings)} total)")

        if self.combat_manager.attack_snakeling(snakeling_pos):
            self.actions.wait("medium")
            return StateResult.RETRY  # Check for more

        return StateResult.SUCCESS

    def _handle_eat_food(self, context: StateExecutionContext) -> StateResult:
        """Eat food if HP low."""
        if self.combat_manager.check_needs_food():
            if self.combat_manager.eat_food():
                logger.info("✓ Ate food")
                self.actions.wait("short")
                return StateResult.SUCCESS
            else:
                logger.error("Failed to eat food!")
                return StateResult.FAILURE

        return StateResult.SUCCESS

    def _handle_drink_prayer(self, context: StateExecutionContext) -> StateResult:
        """Drink prayer potion if prayer low."""
        if self.combat_manager.check_needs_prayer_potion():
            if self.combat_manager.drink_prayer_potion():
                logger.info("✓ Drank prayer potion")
                self.actions.wait("short")
                return StateResult.SUCCESS
            else:
                logger.error("Failed to drink prayer!")
                return StateResult.FAILURE

        return StateResult.SUCCESS

    def _handle_loot(self, context: StateExecutionContext) -> StateResult:
        """Loot Zulrah drops."""
        logger.info("=" * 60)
        logger.info(f"Zulrah Kill #{self.kills + 1} Complete!")
        logger.info("=" * 60)

        self.kills += 1

        # Simplified loot logic - just wait for now
        self.actions.wait("long")

        # Check if we should continue or end
        # For now, just end
        return StateResult.SUCCESS

    def _handle_death_recovery(self, context: StateExecutionContext) -> StateResult:
        """Handle player death."""
        logger.error("Player died! Recovering...")
        # Implement death recovery logic
        return StateResult.SUCCESS

    def _handle_end(self, context: StateExecutionContext) -> StateResult:
        """End of script."""
        logger.info("=" * 60)
        logger.info(f"Zulrah Bot Ended - Total Kills: {self.kills}")
        logger.info("=" * 60)
        return StateResult.SUCCESS

    # --- Helper Methods ---

    def _get_current_phase_data(self) -> Optional[Dict]:
        """Get config data for current phase."""
        if not self.fight_manager.current_rotation:
            return None

        rotation_id = str(self.fight_manager.current_rotation)
        phase_num = self.fight_manager.current_phase_index

        # Get from config
        rotation_config = self.config.get("zulrah", {}).get("rotations", {}).get(rotation_id)

        if not rotation_config:
            logger.error(f"No config for rotation {rotation_id}")
            return None

        phases = rotation_config.get("phases", [])

        if phase_num >= len(phases):
            logger.warning(f"Phase {phase_num} exceeds rotation length")
            return None

        return phases[phase_num]

    def _advance_phase(self):
        """Move to next phase."""
        self.fight_manager.current_phase_index += 1

        logger.info(f"Advanced to phase {self.fight_manager.current_phase_index}")

        # Check if fight complete
        if self._is_fight_complete():
            logger.info("All phases complete - Zulrah defeated!")
            self.transition_to(ZulrahStates.LOOT)

    def _is_fight_complete(self) -> bool:
        """Check if all phases completed."""
        rotation_id = str(self.fight_manager.current_rotation)
        rotation_config = self.config.get("zulrah", {}).get("rotations", {}).get(rotation_id)

        if not rotation_config:
            return False

        total_phases = len(rotation_config.get("phases", []))
        return self.fight_manager.current_phase_index >= total_phases

    def _get_next_state(self, current_state: ZulrahStates, result: StateResult) -> ZulrahStates:
        """
        Dynamic state transitions based on game conditions.

        Priority:
        1. Survival (HP/Prayer)
        2. Snakelings
        3. Phase progression
        4. Normal flow
        """
        # Always check survival first
        if self.combat_manager.check_needs_food():
            return ZulrahStates.EAT_FOOD

        if self.combat_manager.check_needs_prayer_potion():
            return ZulrahStates.DRINK_PRAYER

        # Check for snakelings (phase-specific)
        current_phase = self._get_current_phase_data()
        if current_phase and current_phase.get("spawns_snakelings"):
            if self.detector.detect_snakelings():
                return ZulrahStates.KILL_SNAKELINGS

        # Normal combat flow
        if current_state == ZulrahStates.START:
            return ZulrahStates.IDENTIFY_ROTATION

        elif current_state == ZulrahStates.IDENTIFY_ROTATION:
            if result == StateResult.SUCCESS:
                return ZulrahStates.POSITION_FOR_PHASE

        elif current_state == ZulrahStates.POSITION_FOR_PHASE:
            if result == StateResult.SUCCESS:
                return ZulrahStates.SWITCH_GEAR_PRAYER

        elif current_state == ZulrahStates.SWITCH_GEAR_PRAYER:
            if result == StateResult.SUCCESS:
                return ZulrahStates.ATTACK_ZULRAH

        elif current_state == ZulrahStates.ATTACK_ZULRAH:
            if result == StateResult.SUCCESS:
                # Phase complete - restart combat loop
                return ZulrahStates.POSITION_FOR_PHASE

        elif current_state == ZulrahStates.KILL_SNAKELINGS:
            if result == StateResult.SUCCESS:
                return ZulrahStates.ATTACK_ZULRAH

        elif current_state in [ZulrahStates.EAT_FOOD, ZulrahStates.DRINK_PRAYER]:
            # Return to previous combat state
            return ZulrahStates.ATTACK_ZULRAH

        elif current_state == ZulrahStates.LOOT:
            return ZulrahStates.END

        # Default: retry current state
        return current_state
