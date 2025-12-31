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


class VorkathStates(enum):
    START = "start"
    TELEPORT_TO_VORKATH = "teleport_to_vorkath"
    NAVIGATE_TO_VORKATH = "fight_vorkath"
    BANK_AT_VARROCK = "bank_at_varrock"
    WALK_TO_BANK = "walk_to_bank"
    WALK_TO_VORKATH = "walk_to_vorkath"
    END = "end"
    RECOVERY = "recovery"


class VorkathBot(StateMachineBot):
    """
    A bot that fights Vorkath using a state machine architecture.
    """

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

    def define_states(self):
        return VorkathStates
    

    def define_state_metadata(self):
        return build_metadata_dict(VorkathStates, {
            VorkathStates.IDLE: {
                "name": "Idle",
                "description": "Idle state, waiting to start",
                "max_retries": 1,
            },
            VorkathStates.TELEPORT_TO_VORKATH: {
                "name": "Teleport to Vorkath",
                "description": "Teleports to Vorkath using the appropriate method",
                "max_retries": 2,
                "timeout": 30.0,
                "failover": VorkathStates.RECOVERY
            },
        })