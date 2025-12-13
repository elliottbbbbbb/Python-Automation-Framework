"""
GUNS SCRIPT - LEGACY VERSION (DEPRECATED)

⚠️ DEPRECATED: This is the legacy function-based implementation.

This file is kept for reference only.
The function-based approach is harder to maintain and test.
New bots should use the StateMachineBot framework.

See: src/osrsbot/core/state_machine_bot.py for framework reference
"""
import logging

from osrsbot.queries.game_queries import GameState
from osrsbot.models.config import Config
from osrsbot.commands.game_actions import GameActions as Actions
from osrsbot.constants import GAME_TIMING

logger = logging.getLogger(__name__)


def guns_script(interface, state: GameState,
                actions: Actions, config: Config,
                bank_location: str = "GE", runs: int = 10) -> None:
    logger.info(f"Starting Guns script: {runs} runs, bank: {bank_location}")
    print(f"\nðŸ’° Guns Script ({runs} runs)")

    for run in range(runs):
        try:
            logger.info(f"Run {run + 1}/{runs} starting")
            print(f"\n=== Run {run + 1}/{runs} ===")

            actions.click_inventory_slot(1)
            actions.wait("long")

            actions.click_minimap("pickpocket_location")
            actions.wait("teleport")

            logger.debug("Starting pickpocket loop")
            pickpockets = 0

            while not state.inventory_full():
                if actions.attack_npc("guns_npc"):
                    pickpockets += 1
                    if pickpockets % 10 == 0:
                        logger.debug(f"Pickpockets: {pickpockets}")
                actions.wait("short")

            logger.info(f"Inventory full, pickpockets: {pickpockets}")

            actions.use_item("red_outline")
            actions.wait("medium")

            if bank_location == "GE":
                logger.debug("Selling at GE")
                actions.teleport_varrock()

                actions.walk_to_marker("yellow_tile_marker")
                actions.wait("long")

                for _ in range(GAME_TIMING.teleport_double_click_count):
                    actions.click_coordinate(("world", "ge_clerk"))
                actions.wait("medium")

                actions.click_coordinate(("ui", "ge_collect"))
                actions.wait("short")

                actions.click_color("red_outline")
                actions.wait("short")

                actions.click_coordinate(("ui", "ge_quantity_all"))
                actions.wait("medium")

                actions.click_coordinate(("ui", "ge_lower_price"))
                actions.wait("medium")

                actions.click_coordinate(("ui", "ge_confirm"))
                actions.wait("medium")

                actions.close_interface()
                actions.wait("medium")

        except KeyboardInterrupt:
            logger.warning("Script interrupted by user")
            raise
        except Exception as e:
            logger.error(f"Run {run + 1} failed: {e}", exc_info=True)
            print(f"âŒ Run {run + 1} failed: {e}")

    logger.info("Guns script complete")
    print("\nâœ… Script complete!")
