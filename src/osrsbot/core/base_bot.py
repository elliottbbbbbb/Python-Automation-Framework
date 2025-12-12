import time
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from osrsbot.queries.game_queries import GameState
from osrsbot.models.config import Config
from osrsbot.controllers.actions import GameActions as Actions
from osrsbot.constants import GAME_TIMING

if TYPE_CHECKING:
    from osrsbot.core.game_interface import GameInterface

logger = logging.getLogger(__name__)


class Bot(ABC):
    """
    Abstract base class for all bot scripts.

    Provides core orchestration, dependency injection, and run loop.
    Child classes must implement the abstract run_cycle() method.
    """

    def __init__(
        self,
        interface: "GameInterface",
        state: GameState,
        actions: Actions,
        config: Config,
        script_name: str = "Base Bot"
    ):
        self.interface = interface
        self.state = state
        self.actions = actions
        self.config = config
        self.script_name = script_name

    @abstractmethod
    def run_cycle(self, bank_location: str, run_number: int) -> None:
        """
        Abstract method representing one full cycle (e.g., combat + banking).

        Must be implemented by child classes.

        Args:
            bank_location: The bank location to use for this cycle
            run_number: The current run number (0-indexed)
        """
        pass

    def run(self, bank_location: str = "varrock", runs: int = GAME_TIMING.default_runs) -> None:
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

    # ==================== Common Reusable Methods ====================

    def _teleport_and_bank(self, bank_location: str) -> None:
        """Centralized banking logic to reduce duplication across scripts."""
        if bank_location == "varrock":
            self._bank_at_varrock()
        else:
            logger.error(f"Unknown bank location: {bank_location}")

    def _bank_at_varrock(self) -> None:
        """Handles the specific steps for Varrock banking."""
        actions = self.actions
        actions.teleport_varrock()
        actions.wait("long")

        actions.click_coordinate(("world", "varrock_fountain"))
        actions.wait("teleport")

        for _ in range(GAME_TIMING.walk_to_marker_attempts):
            actions.walk_to_marker("yellow_tile_marker")
        actions.wait("long")

        for _ in range(GAME_TIMING.bank_click_attempts):
            actions.click_coordinate(("world", "bank_booth"))
        actions.wait("long")

        for _ in range(GAME_TIMING.deposit_items_max_attempts):
            actions.click_color("purple_item_outline")
            actions.wait("short")

        # TODO: Generalize food withdrawal logic beyond Manta Ray
        actions.wait("medium")
        actions.click_coordinate(("ui", "bank_quantity"))
        actions.wait("medium")
        actions.bank_search("manta ray")
        actions.click_coordinate(("ui", "bank_food_slot"))
        actions.wait("long")
        actions.close_interface()
