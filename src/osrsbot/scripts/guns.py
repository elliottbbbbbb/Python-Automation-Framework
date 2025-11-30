import logging

from osrsbot.models.state import GameState
from osrsbot.models.config import Config
from osrsbot.controllers.actions import GameActions as Actions

logger = logging.getLogger(__name__)


def guns_script(interface, state: GameState,
                actions: Actions, config: Config,
                bank_location: str = "GE", runs: int = 10) -> None:
    """Pickpocketing script with GE selling."""
    logger.info(f"Starting Guns script: {runs} runs, bank: {bank_location}")
    print(f"\nðŸ’° Guns Script ({runs} runs)")

    for run in range(runs):
        try:
            logger.info(f"Run {run + 1}/{runs} starting")
            print(f"\n=== Run {run + 1}/{runs} ===")

            # Setup
            actions.click_slot(1)
            actions.wait("long")

            # Walk to location
            walk_coord = config.get(
                "coordinates", "minimap", "pickpocket_location")
            if walk_coord:
                actions.click_coord(walk_coord)
            else:
                logger.warning("pickpocket_location coord not in config")

            actions.wait("teleport")

            # Pickpocket loop
            logger.debug("Starting pickpocket loop")
            pickpockets = 0

            while not state.inventory_full():
                if actions.attack("guns_npc"):
                    pickpockets += 1
                    if pickpockets % 10 == 0:
                        logger.debug(f"Pickpockets: {pickpockets}")
                actions.wait("short")

            logger.info(f"Inventory full, pickpockets: {pickpockets}")

            # Handle food
            actions.use_item("red_outline")
            actions.wait("medium")

            # Banking
            if bank_location == "GE":
                logger.debug("Selling at GE")
                actions.teleport_ge()

                actions.walk_marker("yellow_tile_marker")
                actions.wait("long")

                # Click GE clerk
                for _ in range(2):
                    actions.click_coordinate(("world", "ge_clerk"))
                actions.wait("medium")

                # Collect GP
                actions.click_coordinate(("ui", "ge_collect"))
                actions.wait("short")

                # Select items
                actions.click_color("red_outline")
                actions.wait("short")

                # Set quantity
                actions.click_coordinate(("ui", "ge_quantity_all"))
                actions.wait("medium")

                # Lower price
                actions.click_coordinate(("ui", "ge_lower_price"))
                actions.wait("medium")

                # Confirm
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
