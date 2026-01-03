"""
Base Bankstander Bot - Reusable template for all bankstander scripts.

This base class handles all common bankstander logic:
- Opening bank
- Searching and withdrawing items
- Depositing items
- Exit key ('q') support
- Status UI updates
- Bank state tracking

To create a new bankstander script, just:
1. Inherit from BankstanderBot
2. Override process_items() to define what to do with the items
3. Pass item config to __init__

See bankstander_flax.py for a complete example.
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from osrsbot.core.state_helpers import build_metadata_dict
from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_types import (
    StateExecutionContext,
    StateMetadata,
    StateResult,
    StateTransition,
)

logger = logging.getLogger(__name__)


class BankstanderStates(Enum):
    """States for bankstanding bots."""

    IDLE = "idle"
    BANKING = "banking"
    PROCESS = "process"
    DEPOSIT = "deposit"
    RECOVERY = "recovery"


class BankstanderBot(StateMachineBot):
    """
    Base class for bankstander scripts.

    Handles all common banking logic - you just define what to do with the items.
    """

    def __init__(
        self,
        item_name: str,
        item_search_text: str,
        item_template: str,
        item_search_threshold: float = 0.75,
        processed_item_name: Optional[str] = None,
        *args,
        **kwargs,
    ):
        """
        Initialize bankstander bot.

        Args:
            item_name: Display name of item (e.g., "grimy toadflax")
            item_search_text: Text to type in bank search (e.g., "toadflax")
            item_template: Path to item template image
            item_search_threshold: Confidence threshold for finding item (0.0-1.0)
            processed_item_name: Name of processed item (e.g., "cleaned toadflax")
                                If None, will use item_name
        """
        # Enable exit key and status UI
        super().__init__(
            *args,
            **kwargs,
            enable_exit_key=True,
            enable_status_ui=True,
        )

        # Item configuration
        self._item_name = item_name
        self._item_search_text = item_search_text
        self._item_template = item_template
        self._item_search_threshold = item_search_threshold
        self._processed_item_name = processed_item_name or item_name

        # Banker templates (multiple for better accuracy)
        images_dir = Path(__file__).parent.parent / "images" / "bot" / "bank"
        self._banker_templates = [
            str(images_dir / "banker_santa_hat.PNG"),
            str(images_dir / "banker_2.PNG"),
            str(images_dir / "banker_3_zoomed_out.PNG"),
        ]
        self._bank_search_template = str(images_dir / "bank_search_button.PNG")

        # State tracking
        self._bank_open = False
        self._cycles = 0
        self._items_processed = 0

    # ==================== State Machine Configuration ====================

    def define_states(self) -> type[Enum]:
        """Define the states for this bot."""
        return BankstanderStates

    def define_transitions(self) -> List[StateTransition]:
        """Define state transitions."""
        return [
            StateTransition(BankstanderStates.IDLE, BankstanderStates.BANKING),
            StateTransition(BankstanderStates.BANKING, BankstanderStates.PROCESS),
            StateTransition(BankstanderStates.PROCESS, BankstanderStates.DEPOSIT),
            StateTransition(BankstanderStates.DEPOSIT, BankstanderStates.BANKING),
            # Recovery failovers
            StateTransition(
                BankstanderStates.BANKING,
                BankstanderStates.RECOVERY,
            ),
            StateTransition(
                BankstanderStates.PROCESS,
                BankstanderStates.RECOVERY,
            ),
            StateTransition(
                BankstanderStates.DEPOSIT,
                BankstanderStates.RECOVERY,
            ),
            StateTransition(BankstanderStates.RECOVERY, BankstanderStates.IDLE),
        ]

    def define_state_metadata(self) -> Dict[Enum, StateMetadata]:
        """
        Define metadata for each state.

        Configures retry limits, timeouts, and failover behavior.
        """
        return build_metadata_dict(
            BankstanderStates,
            {
                BankstanderStates.IDLE: {
                    "name": "Idle",
                    "description": "Initial state, safety checks",
                    "max_retries": 1,
                },
                BankstanderStates.BANKING: {
                    "name": "Banking",
                    "description": "Open bank, withdraw herbs",
                    "max_retries": 3,
                    "timeout": 30.0,
                    "failover": BankstanderStates.RECOVERY,
                },
                BankstanderStates.PROCESS: {
                    "name": "Process Items",
                    "description": "Click each item to process it",
                    "max_retries": 2,
                    "timeout": 120.0,
                    "failover": BankstanderStates.RECOVERY,
                },
                BankstanderStates.DEPOSIT: {
                    "name": "Deposit",
                    "description": "Deposit cleaned toadflax",
                    "max_retries": 3,
                    "timeout": 30.0,
                    "failover": BankstanderStates.RECOVERY,
                },
                BankstanderStates.RECOVERY: {
                    "name": "Recovery",
                    "description": "Failover state for error recovery",
                    "max_retries": 2,
                },
            },
        )

    def get_initial_state(self) -> Enum:
        """Get initial state (always start at IDLE)."""
        return BankstanderStates.IDLE

    # ==================== State Handlers ====================

    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        """Handle IDLE state - safety checks before starting."""
        self._check_exit_requested()
        self._update_ui("IDLE", "Performing safety checks...")
        logger.info("IDLE: Performing safety checks")

        # Child classes can override this for custom safety checks

        logger.info("IDLE: Safety checks passed, proceeding")
        return StateResult.SUCCESS

    def _handle_banking(self, context: StateExecutionContext) -> StateResult:
        """Handle BANKING state - open bank and withdraw items."""
        self._check_exit_requested()
        self._update_ui("BANKING", f"Opening bank and withdrawing {self._item_name}...")
        logger.info(f"BANKING: Opening bank and withdrawing {self._item_name}")

        try:
            actions = self.actions

            # Check if bank is open
            if not actions.is_bank_open(self._bank_search_template):
                logger.info("BANKING: Bank not detected as open, clicking banker")
                self._bank_open = False

                # Close any dialogue boxes that might be blocking
                logger.info("BANKING: Closing any dialogue boxes with ESC")
                actions.close_interface()  # Presses ESC key and waits

                if not actions.click_banker(
                    self._banker_templates, threshold=0.7
                ):
                    logger.error("BANKING: Failed to find banker")
                    return StateResult.FAILURE
                actions.wait("long")
                self._bank_open = True
                logger.info("BANKING: Bank opened successfully")
            else:
                logger.info("BANKING: Bank already open, skipping banker click")

            # Search for and withdraw item
            self._update_ui("BANKING", f"Searching for {self._item_name}...")
            if not actions.bank_search_and_withdraw(
                search_button_template=self._bank_search_template,
                item_template=self._item_template,
                item_name=self._item_name,
                search_text=self._item_search_text,
                item_threshold=self._item_search_threshold,
            ):
                # If search failed, banker may have opened dialogue
                logger.warning(
                    "BANKING: Bank search failed - "
                    "banker may have opened dialogue instead of bank interface"
                )

                # Close any dialogue boxes that might be blocking the bank interface
                logger.info("BANKING: Closing any dialogue boxes with ESC")
                actions.close_interface()  # Presses ESC key and waits

                logger.info("BANKING: Retrying - clicking banker again")

                # Retry
                if not actions.click_banker(
                    self._banker_templates, threshold=0.7
                ):
                    logger.error("BANKING: Failed to find banker on retry")
                    self._bank_open = False
                    return StateResult.FAILURE

                actions.wait("long")

                # Try search and withdraw again
                self._update_ui("BANKING", f"Retrying search for {self._item_name}...")
                if not actions.bank_search_and_withdraw(
                    search_button_template=self._bank_search_template,
                    item_template=self._item_template,
                    item_name=self._item_name,
                    search_text=self._item_search_text,
                    item_threshold=self._item_search_threshold,
                ):
                    logger.error("BANKING: Failed to withdraw after retry")
                    self._bank_open = False
                    return StateResult.FAILURE

            logger.info("BANKING: Banking complete")
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"BANKING: Failed - {e}")
            self._bank_open = False
            return StateResult.FAILURE

    def _handle_process(self, context: StateExecutionContext) -> StateResult:
        """
        Handle PROCESS state - process the withdrawn items.

        Override this method in child classes to define custom item processing.
        """
        self._check_exit_requested()
        self._update_ui("PROCESS", f"Processing {self._item_name}...")
        logger.info(f"PROCESS: Processing {self._item_name}")

        # Call the child class's processing logic
        return self.process_items(context)

    def _handle_deposit(self, context: StateExecutionContext) -> StateResult:
        """Handle DEPOSIT state - deposit processed items."""
        self._check_exit_requested()
        self._update_ui("DEPOSIT", f"Depositing {self._processed_item_name}...")
        logger.info(f"DEPOSIT: Depositing {self._processed_item_name}")

        try:
            actions = self.actions

            # Check if bank is open
            if not actions.is_bank_open(self._bank_search_template):
                self._update_ui("DEPOSIT", "Reopening bank...")
                logger.warning("DEPOSIT: Bank is not open, need to reopen")
                self._bank_open = False

                # Close any dialogue boxes that might be blocking
                logger.info("DEPOSIT: Closing any dialogue boxes with ESC")
                actions.close_interface()  # Presses ESC key and waits

                # Click banker to reopen bank
                logger.info("DEPOSIT: Clicking banker to reopen bank")
                if not actions.click_banker(
                    self._banker_templates, threshold=0.7
                ):
                    logger.error("DEPOSIT: Failed to find banker")
                    return StateResult.FAILURE

                actions.wait("long")
                self._bank_open = True
                logger.info("DEPOSIT: Bank reopened successfully")
            else:
                logger.info("DEPOSIT: Bank is open, proceeding with deposit")

            # Deposit all items
            self._update_ui("DEPOSIT", "Depositing all items...")
            if not actions.bank_deposit_all():
                logger.error("DEPOSIT: Failed to deposit inventory")
                return StateResult.FAILURE

            actions.wait("medium")

            self._cycles += 1
            self._update_ui(
                "DEPOSIT",
                f"Cycle {self._cycles} complete! Total processed: {self._items_processed}",
            )
            if self._cycles % 10 == 0:
                logger.info(f"DEPOSIT: Completed {self._cycles} cycles")

            logger.info("DEPOSIT: Deposit complete, ready for next cycle")
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"DEPOSIT: Failed - {e}")
            self._bank_open = False
            return StateResult.FAILURE

    def _handle_recovery(self, context: StateExecutionContext) -> StateResult:
        """Handle RECOVERY state - recover from errors."""
        logger.warning("RECOVERY: Entering recovery state")
        self._bank_open = False  # Reset bank state
        return StateResult.SUCCESS

    # ==================== Abstract Method for Child Classes ====================

    def process_items(self, context: StateExecutionContext) -> StateResult:
        """
        Process the items withdrawn from the bank.

        Override this method in child classes to define custom processing logic.

        Args:
            context: State execution context

        Returns:
            StateResult.SUCCESS if processing complete
            StateResult.FAILURE if processing failed

        Example:
            def process_items(self, context):
                # Click each inventory slot to clean herbs
                for slot in range(1, 29):
                    self.actions.click_inventory_slot(slot)
                    time.sleep(random.uniform(0.05, 0.15))
                return StateResult.SUCCESS
        """
        raise NotImplementedError(
            "Child classes must implement process_items() method"
        )
