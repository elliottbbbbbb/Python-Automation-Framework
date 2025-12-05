import time
import logging
from typing import Callable, Optional
from osrsbot.models.state import GameState
from osrsbot.models.config import Config
from osrsbot.controllers.actions import GameActions as Actions

logger = logging.getLogger(__name__)

class Bot:
    """
    Base Bot Class providing the core orchestration, dependency injection,
    and run loop for all individual bot scripts.
    """

    def __init__(
        self,
        interface: object, # Assuming interface is an object for window management
        state: GameState,
        actions: Actions,
        config: Config,
        script_name: str = "Base Bot"
    ):
        """Initializes the bot with all necessary dependencies."""
        self.interface = interface
        self.state = state
        self.actions = actions
        self.config = config
        self.script_name = script_name

    def run_cycle(self, bank_location: str, run_number: int) -> None:
        """
        Abstract method representing one full cycle (e.g., combat + banking).
        Must be implemented by child classes.
        """
        raise NotImplementedError(
            "The 'run_cycle' method must be implemented by the child script class."
        )

    def run(self, bank_location: str = "varrock", runs: int = 10) -> None:
        """
        The main execution loop, handling iterations, logging, and error control.
        """
        logger.info(
            f"Starting {self.script_name}: {runs} runs, bank: {bank_location}"
        )
        print(f"\nðŸš€ {self.script_name} ({runs} runs)")

        for run in range(runs):
            try:
                logger.info(f"Run {run + 1}/{runs} starting")
                print(f"\n=== Run {run + 1}/{runs} ===")

                # Call the specific script logic implemented in the child class
                self.run_cycle(bank_location, run)

            except KeyboardInterrupt:
                logger.warning("Script interrupted by user")
                raise
            except Exception as e:
                logger.error(
                    f"Run {run + 1} failed: {e}", exc_info=True
                )
                print(f"âŒ Run {run + 1} failed: {e}")

        logger.info(f"{self.script_name} complete")
        print("\nâœ… Script complete!")

# --- Common Reusable Methods (optional, but good practice) ---

    def _teleport_and_bank(self, bank_location: str) -> None:
        """Centralized banking logic to reduce duplication across scripts."""
        if bank_location == "varrock":
            self._bank_at_varrock()
        # elif bank_location == "falador":
        #     self._bank_at_falador()
        else:
            logger.error(f"Unknown bank location: {bank_location}")
            
    def _bank_at_varrock(self):
        """Handles the specific steps for Varrock banking."""
        actions = self.actions
        actions.teleport_varrock()
        actions.wait("long")

        actions.click_coordinate(("world", "varrock_fountain"))
        actions.wait("teleport")

        for _ in range(2):
            actions.walk_to_marker("yellow_tile_marker")
        actions.wait("long")

        for _ in range(2):
            actions.click_coordinate(("world", "bank_booth"))
        actions.wait("long")

        # Deposit loot
        for _ in range(12):
            actions.click_color("purple_item_outline")
            actions.wait("short")

        # Withdraw food (Manta Ray specific logic - can be improved)
        actions.wait("medium")
        actions.click_coordinate(("ui", "bank_quantity"))
        actions.wait("medium")
        actions.bank_search("manta ray")
        actions.click_coordinate(("ui", "bank_food_slot"))
        actions.wait("long")
        actions.close_interface()