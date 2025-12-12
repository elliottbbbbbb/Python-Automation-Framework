"""
State Machine Bot - Base class for state-machine driven bots.

Provides a state machine framework for bot scripts with:
- Explicit state management
- Retry logic and failover
- State history tracking
- Transition guards
- Recovery mechanisms
"""
import time
import logging
from abc import abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Callable
from collections import deque

from osrsbot.core.base_bot import Bot
from osrsbot.core.state_types import (
    StateResult,
    StateMetadata,
    StateTransition,
    StateHistoryEntry,
    StateExecutionContext
)

logger = logging.getLogger(__name__)


class StateMachineBot(Bot):
    """
    Base class for state-machine driven bots.

    Extends Bot with state machine capabilities. Child classes define:
    - States (enum)
    - State metadata (retry limits, timeouts, failover)
    - State transitions (allowed paths through state machine)
    - State handlers (implementation of each state)

    Example:
        class MyBotStates(Enum):
            IDLE = "idle"
            WORKING = "working"
            BANKING = "banking"

        class MyBot(StateMachineBot):
            def define_states(self):
                return MyBotStates

            def define_state_metadata(self):
                return {
                    MyBotStates.IDLE: StateMetadata("Idle", max_retries=1),
                    MyBotStates.WORKING: StateMetadata("Working", max_retries=3, timeout=60),
                    MyBotStates.BANKING: StateMetadata("Banking", max_retries=2)
                }

            def define_transitions(self):
                return [
                    StateTransition(MyBotStates.IDLE, MyBotStates.WORKING),
                    StateTransition(MyBotStates.WORKING, MyBotStates.BANKING),
                    StateTransition(MyBotStates.BANKING, MyBotStates.IDLE)
                ]

            def get_initial_state(self):
                return MyBotStates.IDLE

            def _handle_working(self, context: StateExecutionContext) -> StateResult:
                # Implementation
                return StateResult.SUCCESS
    """

    def __init__(self, *args, **kwargs):
        """Initialize state machine bot."""
        super().__init__(*args, **kwargs)

        # State machine configuration (set by child class)
        self._states: Optional[type[Enum]] = None
        self._state_metadata: Dict[Enum, StateMetadata] = {}
        self._transitions: List[StateTransition] = []
        self._current_state: Optional[Enum] = None

        # State execution tracking
        self._state_history: deque = deque(maxlen=100)  # Limit history for memory efficiency and cycle detection
        self._retry_counts: Dict[Enum, int] = {}
        self._transition_map: Dict[Enum, List[StateTransition]] = {}

        # Flags
        self._initialized = False

    # ==================== Abstract Methods (Child Must Implement) ====================

    @abstractmethod
    def define_states(self) -> type[Enum]:
        """
        Define the state enum for this bot.

        Returns:
            Enum class containing all states

        Example:
            class MyStates(Enum):
                IDLE = "idle"
                WORKING = "working"
            return MyStates
        """
        pass

    @abstractmethod
    def define_state_metadata(self) -> Dict[Enum, StateMetadata]:
        """
        Define metadata for each state.

        Returns:
            Dictionary mapping state → StateMetadata

        Example:
            return {
                MyStates.IDLE: StateMetadata(
                    name="Idle",
                    max_retries=1,
                    timeout=None
                ),
                MyStates.WORKING: StateMetadata(
                    name="Working",
                    max_retries=3,
                    timeout=60.0,
                    failover_state=MyStates.RECOVERY
                )
            }
        """
        pass

    @abstractmethod
    def define_transitions(self) -> List[StateTransition]:
        """
        Define allowed state transitions.

        Returns:
            List of StateTransition objects

        Example:
            return [
                StateTransition(MyStates.IDLE, MyStates.WORKING),
                StateTransition(MyStates.WORKING, MyStates.BANKING),
                StateTransition(MyStates.BANKING, MyStates.IDLE)
            ]
        """
        pass

    @abstractmethod
    def get_initial_state(self) -> Enum:
        """
        Get the initial state for the state machine.

        Returns:
            Starting state

        Example:
            return MyStates.IDLE
        """
        pass

    # ==================== State Machine Core ====================

    def initialize_state_machine(self) -> None:
        """
        Initialize state machine configuration.

        Calls abstract methods to get states, metadata, and transitions.
        Must be called before run_cycle().
        """
        if self._initialized:
            logger.warning("State machine already initialized, skipping")
            return

        logger.info(f"Initializing state machine for {self.script_name}")

        # Get configuration from child class
        self._states = self.define_states()
        self._state_metadata = self.define_state_metadata()
        self._transitions = self.define_transitions()
        self._current_state = self.get_initial_state()

        # Build transition map for fast lookup
        self._transition_map = {}
        for transition in self._transitions:
            if transition.from_state not in self._transition_map:
                self._transition_map[transition.from_state] = []
            self._transition_map[transition.from_state].append(transition)

        # Validate configuration
        self._validate_state_machine()

        self._initialized = True
        logger.info(
            f"State machine initialized: "
            f"{len(self._state_metadata)} states, "
            f"{len(self._transitions)} transitions, "
            f"starting at {self._current_state.name}"
        )

    def _validate_state_machine(self) -> None:
        """Validate state machine configuration."""
        # Check all states have metadata
        for state in self._states:
            if state not in self._state_metadata:
                raise ValueError(f"State {state} missing metadata")

        # Check initial state exists
        if self._current_state not in self._states:
            raise ValueError(f"Initial state {self._current_state} not in states enum")

        # Check transitions reference valid states
        for transition in self._transitions:
            if transition.from_state not in self._states:
                raise ValueError(f"Transition from_state {transition.from_state} not in states enum")
            if transition.to_state not in self._states:
                raise ValueError(f"Transition to_state {transition.to_state} not in states enum")

    def run_cycle(self, bank_location: str, run_number: int) -> None:
        """
        Execute one full cycle of the state machine.

        Overrides Bot.run_cycle() to provide state machine execution.

        Args:
            bank_location: Bank location for this cycle
            run_number: Current run number
        """
        if not self._initialized:
            self.initialize_state_machine()

        logger.info(f"Starting state machine cycle {run_number + 1}")

        # Reset retry counts for new cycle
        self._retry_counts.clear()

        # Execute state machine until completion or max states reached
        max_states = 50  # Safety limit to prevent infinite loops
        states_executed = 0

        while states_executed < max_states:
            result = self._execute_state(self._current_state)

            # Get next state based on result
            next_state = self._get_next_state(self._current_state, result)

            if next_state is None:
                # No more transitions, cycle complete
                logger.info(f"State machine cycle complete after {states_executed + 1} states")
                break

            # Transition to next state
            logger.info(f"Transitioning: {self._current_state.name} → {next_state.name}")
            self._current_state = next_state
            states_executed += 1

        if states_executed >= max_states:
            logger.error(f"State machine exceeded max states ({max_states}), terminating cycle")

    # ==================== State Execution ====================

    def _execute_state(self, state: Enum) -> StateResult:
        """
        Execute a single state with retry logic and timeout handling.

        Args:
            state: State to execute

        Returns:
            Final StateResult after retries
        """
        metadata = self._state_metadata[state]
        retry_count = self._retry_counts.get(state, 0)

        logger.info(
            f"Executing state: {state.name} "
            f"(attempt {retry_count + 1}/{metadata.max_retries + 1})"
        )

        # Create execution context
        context = StateExecutionContext(
            current_state=state,
            retry_count=retry_count
        )

        start_time = time.time()
        result = StateResult.FAILURE
        error_message = None

        try:
            # Get state handler method
            handler = self._get_state_handler(state)

            # Execute state with timeout check
            while not context.has_timed_out(metadata.timeout):
                result = handler(context)

                # Check if state completed
                if result != StateResult.RETRY:
                    break

                # Retry delay
                time.sleep(0.5)

            # Check for timeout
            if context.has_timed_out(metadata.timeout):
                logger.warning(f"State {state.name} timed out after {metadata.timeout}s")
                result = StateResult.TIMEOUT
                error_message = f"Timeout after {metadata.timeout}s"

        except Exception as e:
            logger.error(f"Error executing state {state.name}: {e}", exc_info=True)
            result = StateResult.FAILURE
            error_message = str(e)

        duration = time.time() - start_time

        # Record history
        history_entry = StateHistoryEntry(
            state=state,
            result=result,
            duration=duration,
            retry_count=retry_count,
            error_message=error_message
        )
        self._state_history.append(history_entry)

        # Log result
        logger.info(
            f"State {state.name} completed: {result.value} "
            f"(duration: {duration:.2f}s, retries: {retry_count})"
        )

        # Handle retry logic
        if result in (StateResult.FAILURE, StateResult.RETRY, StateResult.TIMEOUT):
            if retry_count < metadata.max_retries:
                # Retry state
                self._retry_counts[state] = retry_count + 1
                logger.info(f"Retrying state {state.name} (attempt {retry_count + 2}/{metadata.max_retries + 1})")
                return self._execute_state(state)  # Recursive retry
            else:
                # Max retries reached, check for failover
                if metadata.failover_state:
                    logger.warning(
                        f"State {state.name} failed after {metadata.max_retries + 1} attempts, "
                        f"failing over to {metadata.failover_state.name}"
                    )
                    self._current_state = metadata.failover_state
                    self._retry_counts[state] = 0  # Reset retry count
                    return StateResult.FAILURE  # Return failure, next cycle will execute failover
                else:
                    logger.error(f"State {state.name} failed with no failover state defined")

        # Reset retry count on success
        if result == StateResult.SUCCESS:
            self._retry_counts[state] = 0

        return result

    def _get_state_handler(self, state: Enum) -> Callable[[StateExecutionContext], StateResult]:
        """
        Get the handler method for a state.

        Handler methods are named _handle_{state_name_lowercase}.

        Args:
            state: State to get handler for

        Returns:
            Handler callable

        Raises:
            AttributeError: If handler method not found
        """
        handler_name = f"_handle_{state.value.lower()}"
        handler = getattr(self, handler_name, None)

        if handler is None:
            raise AttributeError(
                f"State handler '{handler_name}' not found for state {state.name}. "
                f"Please implement this method in {self.__class__.__name__}"
            )

        return handler

    def _get_next_state(self, current_state: Enum, result: StateResult) -> Optional[Enum]:
        """
        Determine next state based on current state and result.

        Args:
            current_state: Current state
            result: Result of current state execution

        Returns:
            Next state to execute, or None if no valid transition
        """
        # Get possible transitions from current state
        possible_transitions = self._transition_map.get(current_state, [])

        if not possible_transitions:
            # No transitions defined, end cycle
            return None

        # Find first valid transition
        for transition in possible_transitions:
            if transition.can_transition():
                return transition.to_state

        # No valid transition found
        logger.warning(f"No valid transition from {current_state.name}, ending cycle")
        return None

    # ==================== State History & Debugging ====================

    def get_state_history(self, last_n: Optional[int] = None) -> List[StateHistoryEntry]:
        """
        Get state execution history.

        Args:
            last_n: Return last N entries (None = all)

        Returns:
            List of StateHistoryEntry
        """
        if last_n is None:
            return list(self._state_history)
        return list(self._state_history)[-last_n:]

    def get_current_state(self) -> Optional[Enum]:
        """Get current state."""
        return self._current_state

    def get_retry_count(self, state: Enum) -> int:
        """Get current retry count for a state."""
        return self._retry_counts.get(state, 0)

    def reset_state_machine(self) -> None:
        """Reset state machine to initial state."""
        self._current_state = self.get_initial_state()
        self._retry_counts.clear()
        logger.info(f"State machine reset to {self._current_state.name}")
