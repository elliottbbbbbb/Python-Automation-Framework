import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from osrsbot.commands.game_actions import GameActions as Actions
from osrsbot.constants import GAME_TIMING
from osrsbot.models.config import Config
from osrsbot.queries.game_queries import GameState

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
        script_name: str = "Base Bot",
        enable_exit_key: bool = False,
        enable_status_ui: bool = False,
    ):
        self.interface = interface
        self.state = state
        self.actions = actions
        self.config = config
        self.script_name = script_name

        # Optional features
        self._exit_requested = False
        self._enable_exit_key = enable_exit_key
        self._enable_status_ui = enable_status_ui

        # UI state tracking
        self._ui_state = "STARTING"
        self._ui_action = "Initializing..."

        # Start optional features
        if self._enable_exit_key:
            self._start_keyboard_listener()

    def _start_keyboard_listener(self):

        def on_press(key):
            try:
                if hasattr(key, "char") and key.char == "q":
                    self._exit_requested = True
                    logger.info("Exit requested by user (pressed 'q')")
                    print("\n🛑 Exit requested... finishing current action...\n")
                    return False  # Stop listener
            except Exception as e:
                logger.error(f"Error in keyboard listener: {e}")

        try:
            from pynput import keyboard as kb

            listener = kb.Listener(on_press=on_press)
            listener.daemon = True
            listener.start()
            logger.info("Keyboard listener started (press 'q' to exit)")

            # Print UI instructions
            print("\n" + "=" * 60)
            print(f"{self.script_name.upper()} - CONTROLS")
            print("=" * 60)
            print("Press 'q' at any time to gracefully exit")
            print("=" * 60 + "\n")
        except ImportError:
            logger.warning("pynput not installed, 'q' exit feature disabled")
            print("⚠️  Install pynput for 'q' to exit: pip install pynput\n")

    def _check_exit_requested(self) -> None:
        """Check if user requested exit via 'q' key and raise KeyboardInterrupt if so."""
        if self._exit_requested:
            logger.info("Exit check: User requested exit")
            raise KeyboardInterrupt("User requested exit via 'q' key")

    def _update_ui(self, state: str, action: str) -> None:
        """
        Update the console UI with current state and action.

        Only updates if status UI is enabled.

        Args:
            state: Current state name (e.g., "BANKING", "COMBAT")
            action: Current action description (e.g., "Withdrawing items...")
        """
        if not self._enable_status_ui:
            return

        self._ui_state = state
        self._ui_action = action

        # Simple console UI - just print updates
        status_line = f"[{state}] {action}"
        print(f"\r{status_line:<80}", end="", flush=True)

    @abstractmethod
    def run_cycle(self, bank_location: str, run_number: int) -> None:
        """
        Abstract method representing one full cycle (e.g., combat + banking).

        Must be implemented by child classes.

        Args:
            bank_location: The bank location to use for this cycle
            run_number: The current run number (0-indexed)
        """

    def run(
        self, bank_location: str = "varrock", runs: int = GAME_TIMING.default_runs
    ) -> None:
        """
        The main execution loop, handling iterations, logging, and error control.
        """
        logger.info(f"Starting {self.script_name}: {runs} runs, bank: {bank_location}")
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
                logger.error(f"Run {run + 1} failed: {e}", exc_info=True)
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

        actions.wait("medium")
        actions.click_coordinate(("ui", "bank_quantity"))
        actions.wait("medium")
        actions.bank_search("manta ray")
        actions.click_coordinate(("ui", "bank_food_slot"))
        actions.wait("long")
        actions.close_interface()
