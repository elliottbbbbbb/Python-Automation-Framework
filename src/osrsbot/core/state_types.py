"""
State machine data types and structures.

This module defines the core types used by the state machine framework:
- StateResult: Outcomes of state execution
- StateMetadata: Configuration for individual states
- StateTransition: Defines allowed state transitions
- StateHistoryEntry: Tracks state execution history
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class StateResult(Enum):
    """
    Result of executing a state.

    Determines the next action the state machine should take.
    """

    SUCCESS = "success"  # State completed successfully, proceed to next state
    FAILURE = "failure"  # State failed, may retry or transition to failover
    RETRY = "retry"  # State should be retried immediately
    SKIP = "skip"  # State skipped (condition not met), proceed to next
    TIMEOUT = "timeout"  # State timed out, transition to failover


@dataclass
class StateMetadata:
    """
    Metadata and configuration for a single state.

    Defines retry behavior, timeouts, and failover logic for a state.
    """

    name: str
    description: str = ""
    max_retries: int = 3  # Max retry attempts before failover
    timeout: Optional[float] = None  # Max execution time in seconds (None = no timeout)
    failover_state: Optional[Enum] = None  # State to transition to on repeated failures

    def __post_init__(self):
        """Validate metadata after initialization."""
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {self.max_retries}")
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError(f"timeout must be > 0 or None, got {self.timeout}")


@dataclass
class StateTransition:
    """
    Defines a transition between states.

    Includes optional condition function to determine if transition should occur.
    """

    from_state: Enum
    to_state: Enum
    condition: Optional[Callable[[], bool]] = (
        None  # If provided, must return True to transition
    )

    def can_transition(self) -> bool:
        """
        Check if transition is allowed.

        Returns:
            True if no condition or condition evaluates to True
        """
        if self.condition is None:
            return True
        try:
            return bool(self.condition())
        except Exception:
            # If condition fails, don't allow transition
            return False


@dataclass
class StateHistoryEntry:
    """
    Records execution of a single state.

    Tracks timing, result, and retry information for analysis and debugging.
    """

    state: Enum
    result: StateResult
    duration: float  # Execution time in seconds
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0
    error_message: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        """Check if state execution succeeded."""
        return self.result == StateResult.SUCCESS

    @property
    def failed(self) -> bool:
        """Check if state execution failed."""
        return self.result in (StateResult.FAILURE, StateResult.TIMEOUT)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "state": (
                self.state.name if isinstance(self.state, Enum) else str(self.state)
            ),
            "result": self.result.value,
            "duration": self.duration,
            "timestamp": self.timestamp,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


@dataclass
class StateExecutionContext:
    """
    Context passed to state execution handlers.

    Provides access to bot services and current execution state.
    """

    current_state: Enum
    retry_count: int = 0
    start_time: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since state started."""
        return time.time() - self.start_time

    def has_timed_out(self, timeout: Optional[float]) -> bool:
        """
        Check if state has exceeded timeout.

        Args:
            timeout: Timeout in seconds (None = no timeout)

        Returns:
            True if timed out, False otherwise
        """
        if timeout is None:
            return False
        return self.elapsed_time >= timeout
