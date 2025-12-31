"""
Vorkath Bot - State Machine Implementation

State-machine driven bot for vorkath.

States:
    IDLE - Initial state, safety checks
    Teleporting to house and then exiting (Must be located in rekella)
    Navigate to vorkath from house portal. (I think this should include before and after we travel to vorkaths island.)
    COMBAT - This is going to be a bit more complex, the combat phase is going to have subphases which can be triggered depending on what phase of the boss we are in.
    Do we want to implement the phases sequentially? I don't remember if vorkath is similar to zulrah in the sense that the possible phases you can go through depend on external factors. If so, their might need to be some sort of subphase for combat as in combat(dodging the 1 shot abiity, dodging the green posion on the floor)
    I would also need to figure out whether or not we would allow multiple states to exists at once. For example if we need to dodge green posion and then idk attack - `probably not tho thinking about it.
    BANKING - Teleport to house, navigate towards house glorypoh.

"""

import logging
import time
import random
from enum import Enum
from typing import Dict, List

from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_helpers import build_metadata_dict
from osrsbot.core.state_types import (
    StateResult,
    StateMetadata,
    StateTransition,
    StateExecutionContext
)
from osrsbot.constants import GAME_TIMING

logger = logging.getLogger(__name__)


class VorkathStates(Enum):
    """States for vorkath farming bot"""
    IDLE = 'IDLE'
    NAVIGATE_TO_VORKATH = "navigate_to_vorkath" # This is going to include tp and walking
    COMBAT = "combat"
    NAVIGATE_TO_BANK = "naviage_to_bank"
    BANKING = "banking"
    RECOVERY = "recovery"


class VorkathStateMachineBot(StateMachineBot):
    """
    Vorkath bot using state machine framework
    """
    def __init__(self, *args, debug_ui = False, **kwargs):
        super().__init__(*args, debug_ui=debug_ui, **kwargs, script_name = "Vorkath (State Machine)")

        base_threshold = self.config.get("hp_threshold", default=70)
        self.hp_threshold = self._apply_threshold_variance(base_threshold)
        logger.info(f"HP threshold set to {self.hp_threshold}")

        self._kills = 0

        def define_states(self) -> type[Enum]:
            return VorkathStates
        
        def define_state_metadata(self) -> Dict[Enum, StateMetadata]:
            return build_metadata_dict(VorkathStates, {
                VorkathStates.IDLE: {
                    "name": "Idle",
                    "description": "Initial state, safety checks",
                    "max_retries": 1,
                },
                VorkathStates.NAVIGATE_TO_VORKATH: {
                    "name": "Navigate to Vorkath",
                    "description": "Navigate to vorkath from house portal (includes teleporting to house)",
                    "max_retries": 3,
                    "timeout": 30.0,
                    "failover": VorkathStates.RECOVERY,
                },
                VorkathStates.COMBAT: {
                    "name": "Combat",
                    "description": "Engage in combat with Vorkath",
                    "max_retries": 1,
                    "timeout": 300.0,
                    "failover": VorkathStates.RECOVERY,
                },
                VorkathStates.NAVIGATE_TO_BANK: {
                    "name": "Navigate to Bank",
                    "description": "Navigate to bank from Vorkath island",
                    "max_retries": 3,
                    "timeout": 30.0,
                    "failover": VorkathStates.RECOVERY,
                },
                VorkathStates.BANKING: {
                    "name": "Banking",
                    "description": "Bank supplies and loot",
                    # Not sure about max retries here
                    "timeout": 60.0,
                    "failover": VorkathStates.RECOVERY,
                },
                VorkathStates.RECOVERY: {
                    "name": "Recovery",
                    "description": "Handle recovery from failures",
                    "max_retries": 2,
                }, 
            }) 

        
        def define_state_transitions(self) -> List[StateTransition]:
            return [
                StateTransition(VorkathStates.IDLE, VorkathStates.NAVIGATE_TO_VORKATH),
                StateTransition(VorkathStates.NAVIGATE_TO_VORKATH, VorkathStates.COMBAT),
                StateTransition(VorkathStates.COMBAT, VorkathStates.NAVIGATE_TO_BANK),
                StateTransition(VorkathStates.NAVIGATE_TO_BANK, VorkathStates.BANKING),
                StateTransition(VorkathStates.BANKING, VorkathStates.IDLE),
                StateTransition(VorkathStates.RECOVERY, VorkathStates.IDLE),
            ]
