"""Helper utilities for state machine bot development."""

import logging
from enum import Enum
from typing import Dict, Optional
from functools import wraps

from osrsbot.core.state_types import StateMetadata, StateResult, StateExecutionContext

logger = logging.getLogger(__name__)


def create_state_metadata(
    name: str,
    description: str = "",
    max_retries: int = 3,
    timeout: Optional[float] = None,
    failover_state: Optional[Enum] = None
) -> StateMetadata:
    """
    Create StateMetadata with less boilerplate.

    Provides sensible defaults while allowing customization.

    Args:
        name: Display name for the state
        description: Brief description of what the state does
        max_retries: Maximum retry attempts (default: 3)
        timeout: Maximum time in seconds before failover (default: None = no timeout)
        failover_state: State to transition to on failure (default: None)

    Returns:
        StateMetadata instance

    Example:
        metadata = create_state_metadata(
            name="Combat",
            description="Fight enemies",
            timeout=600.0,
            failover_state=MyStates.RECOVERY
        )
    """
    return StateMetadata(
        name=name,
        description=description,
        max_retries=max_retries,
        timeout=timeout,
        failover_state=failover_state
    )


def build_metadata_dict(
    states_enum: type[Enum],
    configs: Dict[Enum, dict]
) -> Dict[Enum, StateMetadata]:
    """
    Build state metadata dictionary from compact configuration.

    Reduces boilerplate by allowing compact dict-based configuration
    instead of verbose StateMetadata() calls for each state.

    Args:
        states_enum: The states enum class (unused, kept for clarity)
        configs: Dict mapping state enum to config dict with keys:
            - name (required): Display name for the state
            - description (optional, default=""): Brief description
            - max_retries (optional, default=3): Maximum retry attempts
            - timeout (optional, default=None): Timeout in seconds
            - failover (optional, default=None): Failover state enum

    Returns:
        Dict mapping states to StateMetadata objects

    Example:
        metadata = build_metadata_dict(MyStates, {
            MyStates.IDLE: {
                "name": "Idle",
                "description": "Safety checks",
                "max_retries": 1,
            },
            MyStates.COMBAT: {
                "name": "Combat",
                "description": "Fight enemies",
                "timeout": 600.0,
                "failover": MyStates.TELEPORT,
            }
        })
    """
    result = {}
    for state, config in configs.items():
        if "name" not in config:
            raise ValueError(f"State {state} config missing required 'name' field")

        result[state] = create_state_metadata(
            name=config["name"],
            description=config.get("description", ""),
            max_retries=config.get("max_retries", 3),
            timeout=config.get("timeout", None),
            failover_state=config.get("failover", None)
        )
    return result


def log_state_execution(func):
    """
    Decorator to automatically log state handler entry/exit.

    Adds consistent debug logging to state handlers without manual logger calls.
    Logs state entry and completion status based on return value.

    Usage:
        @log_state_execution
        def _handle_combat(self, context: StateExecutionContext) -> StateResult:
            # No need for logger.info("COMBAT: Starting...")
            # Just implement logic
            return StateResult.SUCCESS

    Logs:
        - "COMBAT: Starting..." on entry (debug level)
        - "COMBAT: Complete" on SUCCESS (debug level)
        - "COMBAT: Failed" on FAILURE (debug level)
        - "COMBAT: Retrying..." on RETRY (debug level)

    Note:
        This decorator is optional and can be used selectively per state handler.
        Some handlers may prefer custom logging for more detailed context.
    """
    @wraps(func)
    def wrapper(self, context: StateExecutionContext) -> StateResult:
        state_name = context.current_state.name.upper()

        logger.debug(f"{state_name}: Starting...")

        result = func(self, context)

        if result == StateResult.SUCCESS:
            logger.debug(f"{state_name}: Complete")
        elif result == StateResult.FAILURE:
            logger.debug(f"{state_name}: Failed")
        elif result == StateResult.RETRY:
            logger.debug(f"{state_name}: Retrying...")

        return result

    return wrapper
