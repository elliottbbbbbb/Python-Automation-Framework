import logging
from enum import Enum
from typing import Dict, List, Optional
from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_types import StateMetadata, StateResult, StateTransition, StateExecutionContext

logger = logging.getLogger(__name__)

# --- Helper Logic for Zulrah Mechanics ---

class ZulrahPhase(str, Enum):
    SERP_MID = "serp_middle"
    SERP_EAST = "serp_east"
    SERP_WEST = "serp_west"
    SERP_SOUTH = "serp_south"
    MAGMA_MID = "magma_middle"
    TANZ_MID = "tanz_middle"
    TANZ_EAST = "tanz_east"
    TANZ_WEST = "tanz_west"
    JAD_WEST = "jad_west" 
    JAD_EAST = "jad_east"

class ZulrahRotation(str, Enum):
    ROTATION_1 = "rotation_1"
    ROTATION_2 = "rotation_2"
    ROTATION_3 = "rotation_3"
    ROTATION_4 = "rotation_4"

class ZulrahFightManager:
    def __init__(self):
        self.rotation: Optional[ZulrahRotation] = None
        self.current_phase_index: int = 0
        
        self.sequences = {
            ZulrahRotation.ROTATION_1: [
                ZulrahPhase.SERP_MID, ZulrahPhase.MAGMA_MID, ZulrahPhase.TANZ_MID, 
                ZulrahPhase.SERP_SOUTH, ZulrahPhase.MAGMA_MID, ZulrahPhase.TANZ_WEST, 
                ZulrahPhase.SERP_SOUTH, ZulrahPhase.TANZ_MID, ZulrahPhase.JAD_WEST, 
                ZulrahPhase.MAGMA_MID
            ],
            ZulrahRotation.ROTATION_2: [
                ZulrahPhase.SERP_MID, ZulrahPhase.MAGMA_MID, ZulrahPhase.TANZ_MID, 
                ZulrahPhase.SERP_WEST, ZulrahPhase.TANZ_MID, ZulrahPhase.MAGMA_MID, 
                ZulrahPhase.SERP_EAST, ZulrahPhase.TANZ_MID, ZulrahPhase.JAD_EAST, 
                ZulrahPhase.MAGMA_MID
            ],
            ZulrahRotation.ROTATION_3: [
                ZulrahPhase.SERP_MID, ZulrahPhase.SERP_EAST, ZulrahPhase.MAGMA_MID, 
                ZulrahPhase.TANZ_WEST, ZulrahPhase.SERP_SOUTH, ZulrahPhase.TANZ_EAST, 
                ZulrahPhase.SERP_MID, ZulrahPhase.SERP_WEST, ZulrahPhase.TANZ_MID, 
                ZulrahPhase.JAD_EAST, ZulrahPhase.TANZ_MID
            ],
            ZulrahRotation.ROTATION_4: [
                ZulrahPhase.SERP_MID, ZulrahPhase.TANZ_EAST, ZulrahPhase.SERP_SOUTH, 
                ZulrahPhase.TANZ_WEST, ZulrahPhase.MAGMA_MID, ZulrahPhase.SERP_EAST, 
                ZulrahPhase.SERP_SOUTH, ZulrahPhase.TANZ_WEST, ZulrahPhase.SERP_MID, 
                ZulrahPhase.TANZ_MID, ZulrahPhase.JAD_EAST, ZulrahPhase.TANZ_MID
            ]
        }

    def detect_phase_type(self, form: str, pos: str) -> ZulrahPhase:
        mapping = {
            ("serp", "middle"): ZulrahPhase.SERP_MID, ("serp", "east"): ZulrahPhase.SERP_EAST,
            ("serp", "west"): ZulrahPhase.SERP_WEST, ("serp", "south"): ZulrahPhase.SERP_SOUTH,
            ("magma", "middle"): ZulrahPhase.MAGMA_MID, ("tanz", "middle"): ZulrahPhase.TANZ_MID,
            ("tanz", "east"): ZulrahPhase.TANZ_EAST, ("tanz", "west"): ZulrahPhase.TANZ_WEST,
        }
        return mapping.get((form.lower(), pos.lower()))

    def update_rotation(self, current_form: str, current_pos: str):
        phase = self.detect_phase_type(current_form, current_pos)
        self.current_phase_index += 1

        if not self.rotation:
            if self.current_phase_index == 2:
                if phase == ZulrahPhase.SERP_EAST: self.rotation = ZulrahRotation.ROTATION_3
                elif phase == ZulrahPhase.TANZ_EAST: self.rotation = ZulrahRotation.ROTATION_4
            elif self.current_phase_index == 4:
                if phase == ZulrahPhase.SERP_SOUTH: self.rotation = ZulrahRotation.ROTATION_1
                elif phase == ZulrahPhase.SERP_WEST: self.rotation = ZulrahRotation.ROTATION_2

    def get_next_phase_prediction(self) -> Optional[ZulrahPhase]:
        if self.rotation:
            seq = self.sequences[self.rotation]
            next_idx = self.current_phase_index # Index is already incremented in update
            if next_idx >= len(seq): return seq[0]
            return seq[next_idx]
        return None

# --- State Machine Bot Implementation ---

class ZulrahStates(Enum):
    START = "start"
    MOVE_TO_SAFE_SPOT = "move_to_safe_spot"
    ATTACK_MELEE = "attack_melee"
    ATTACK_RANGE = "attack_range"
    ATTACK_MAGE = "attack_mage"
    SWITCH_PRAYER = "switch_prayer"
    EAT_FOOD = "eat_food"
    DEAD = "dead"
    END = "end"

class ZulrahBot(StateMachineBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = ZulrahFightManager()

    def define_states(self):
        return ZulrahStates

    def define_state_metadata(self) -> Dict[Enum, StateMetadata]:
        return {
            ZulrahStates.START: StateMetadata(max_retries=1, timeout=5),
            ZulrahStates.MOVE_TO_SAFE_SPOT: StateMetadata(max_retries=3, timeout=3),
            ZulrahStates.ATTACK_MELEE: StateMetadata(max_retries=3, timeout=2),
            ZulrahStates.ATTACK_RANGE: StateMetadata(max_retries=3, timeout=2),
            ZulrahStates.ATTACK_MAGE: StateMetadata(max_retries=3, timeout=2),
            ZulrahStates.SWITCH_PRAYER: StateMetadata(max_retries=1, timeout=1),
            ZulrahStates.EAT_FOOD: StateMetadata(max_retries=2, timeout=1),
            ZulrahStates.DEAD: StateMetadata(max_retries=1, timeout=1, failover_state=ZulrahStates.END),
            ZulrahStates.END: StateMetadata(max_retries=0, timeout=1),
        }

    def define_transitions(self) -> List[StateTransition]:
        return [
            StateTransition(ZulrahStates.START, ZulrahStates.MOVE_TO_SAFE_SPOT),
            StateTransition(ZulrahStates.MOVE_TO_SAFE_SPOT, ZulrahStates.SWITCH_PRAYER),
            StateTransition(ZulrahStates.SWITCH_PRAYER, ZulrahStates.ATTACK_RANGE), # Example branch
            StateTransition(ZulrahStates.ATTACK_RANGE, ZulrahStates.EAT_FOOD),
            StateTransition(ZulrahStates.ATTACK_MAGE, ZulrahStates.EAT_FOOD),
            StateTransition(ZulrahStates.ATTACK_MELEE, ZulrahStates.EAT_FOOD),
            StateTransition(ZulrahStates.EAT_FOOD, ZulrahStates.MOVE_TO_SAFE_SPOT),
            StateTransition(ZulrahStates.DEAD, ZulrahStates.END),
        ]

    def get_initial_state(self):
        return ZulrahStates.START

    def _handle_start(self, context: StateExecutionContext) -> StateResult:
        logger.info("Zulrah encounter started.")
        return StateResult.SUCCESS

    def _handle_move_to_safe_spot(self, context: StateExecutionContext) -> StateResult:
        # Logic: Check predicted phase from self.manager to find coordinate
        prediction = self.manager.get_next_phase_prediction()
        logger.info(f"MOVE_TO_SAFE_SPOT - Next Phase predicted: {prediction}")
        return StateResult.SUCCESS

    def _handle_attack_melee(self, context: StateExecutionContext) -> StateResult:
        logger.info("Executing Melee Attack (if applicable)")
        return StateResult.SUCCESS

    def _handle_attack_range(self, context: StateExecutionContext) -> StateResult:
        logger.info("Executing Ranged Attack")
        return StateResult.SUCCESS

    def _handle_attack_mage(self, context: StateExecutionContext) -> StateResult:
        logger.info("Executing Magic Attack")
        return StateResult.SUCCESS

    def _handle_switch_prayer(self, context: StateExecutionContext) -> StateResult:
        # Logic: Switch prayer based on current Zulrah form
        logger.info("SWITCH_PRAYER - Selecting best protection")
        return StateResult.SUCCESS

    def _handle_eat_food(self, context: StateExecutionContext) -> StateResult:
        # Logic: Check current HP via context and eat if necessary
        logger.info("EAT_FOOD - Checking health")
        return StateResult.SUCCESS

    def _handle_dead(self, context: StateExecutionContext) -> StateResult:
        logger.warning("Player or Zulrah is DEAD")
        return StateResult.SUCCESS

    def _handle_end(self, context: StateExecutionContext) -> StateResult:
        logger.info("Zulrah fight script terminated.")
        return StateResult.SUCCESS