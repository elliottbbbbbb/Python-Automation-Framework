import logging
import time
import pyautogui

from osrsbot.game_interface import GameInterface
from osrsbot.game_state import GameState
from osrsbot.config import Config
from osrsbot.actions import Actions

logger = logging.getLogger(__name__)


def guns_script(interface: GameInterface, state: GameState,
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
                interface.click_coord(walk_coord)
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
                time.sleep(0.8)

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
                coord = config.get("coordinates", "world", "ge_clerk")
                for _ in range(2):
                    if coord:
                        interface.click_coord(coord)
                actions.wait("medium")

                # Collect GP
                collect_coord = config.get("coordinates", "ui", "ge_collect")
                if collect_coord:
                    interface.click_coord(collect_coord)
                actions.wait("short")

                # Select items
                color = config.get("colors", "red_outline")
                if color:
                    interface.click_color(color)
                actions.wait("short")

                # Set quantity
                qty_coord = config.get("coordinates", "ui", "ge_quantity_all")
                if qty_coord:
                    interface.click_coord(qty_coord)
                actions.wait("medium")

                # Lower price
                price_coord = config.get("coordinates", "ui", "ge_lower_price")
                if price_coord:
                    interface.click_coord(price_coord)
                actions.wait("medium")

                # Confirm
                confirm_coord = config.get("coordinates", "ui", "ge_confirm")
                if confirm_coord:
                    interface.click_coord(confirm_coord)
                actions.wait("medium")

                pyautogui.press('escape')
                actions.wait("medium")

        except KeyboardInterrupt:
            logger.warning("Script interrupted by user")
            raise
        except Exception as e:
            logger.error(f"Run {run + 1} failed: {e}", exc_info=True)
            print(f"âŒ Run {run + 1} failed: {e}")

    logger.info("Guns script complete")
    print("\nâœ… Script complete!")
