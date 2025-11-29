import time
import pyautogui
import logging
from osrsbot.game_interface import GameInterface
from osrsbot.game_state import GameState
from osrsbot.config import Config
from osrsbot.actions import Actions

logger = logging.getLogger(__name__)


def green_dragons_script(interface: GameInterface, state: GameState,
                         actions: Actions, config: Config,
                         bank_location: str = "varrock", runs: int = 10) -> None:
    """Green Dragons farming script with combat and banking."""
    logger.info(f"Starting Green Dragons script: {runs} runs, bank: {bank_location}")
    print(f"\nðŸ‰ Green Dragons Script ({runs} runs)")

    hp_threshold = config.get("hp_threshold", default=70)

    for run in range(runs):
        try:
            logger.info(f"Run {run + 1}/{runs} starting")
            print(f"\n=== Run {run + 1}/{runs} ===")

            # Setup
            logger.debug("Teleporting and navigating to dragons")
            actions.click_slot(1)
            actions.wait("long")

            for _ in range(2):
                actions.walk_marker("yellow_tile_marker")
            actions.wait("long")

            actions.click_minimap("green_dragons")
            actions.wait("medium")

            # Use potions
            actions.use_item("extended_antifire")
            actions.wait("medium")
            actions.use_item("super_combat")
            actions.wait("long")

            # Combat loop
            logger.debug("Starting combat loop")
            kills = 0

            while not state.inventory_full():
                hp = state.get_health()
                if hp and hp < hp_threshold:
                    logger.info(f"HP low: {hp}, eating")
                    actions.eat("manta_ray")
                    actions.wait("medium")

                if not state.in_combat():
                    if actions.attack("green_dragon"):
                        kills += 1
                        if kills % 5 == 0:
                            logger.debug(f"Kills: {kills}")

                time.sleep(1)

            logger.info(f"Inventory full, kills: {kills}")

            # Banking
            if bank_location == "varrock":
                logger.debug("Banking at Varrock")
                actions.teleport_ge()
                actions.wait("long")

                fountain_coord = config.get("coordinates", "world", "varrock_fountain")
                if fountain_coord:
                    interface.click_coord(fountain_coord)
                else:
                    logger.warning("varrock_fountain coord not in config")

                actions.wait("teleport")

                for _ in range(2):
                    actions.walk_marker("yellow_tile_marker")
                actions.wait("long")

                for _ in range(2):
                    coord = config.get("coordinates", "world", "bank_booth")
                    if coord:
                        interface.click_coord(coord)
                actions.wait("long")

                # Deposit loot
                for _ in range(12):
                    color = config.get("colors", "purple_item_outline")
                    if color:
                        interface.click_color(color)
                    actions.wait("short")

                # Withdraw food
                actions.wait("medium")
                quantity_coord = config.get("coordinates", "ui", "bank_quantity")
                if quantity_coord:
                    interface.click_coord(quantity_coord)

                actions.wait("medium")
                actions.bank_search("manta ray")

                food_coord = config.get("coordinates", "ui", "bank_food_slot")
                if food_coord:
                    interface.click_coord(food_coord)

                actions.wait("long")
                pyautogui.press('escape')

        except KeyboardInterrupt:
            logger.warning("Script interrupted by user")
            raise
        except Exception as e:
            logger.error(f"Run {run + 1} failed: {e}", exc_info=True)
            print(f"âŒ Run {run + 1} failed: {e}")

    logger.info("Green Dragons script complete")
    print("\nâœ… Script complete!")