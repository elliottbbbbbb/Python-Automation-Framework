import logging
import time
from osrsbot.core.base_bot import Bot

logger = logging.getLogger(__name__)


class GreenDragonsBot(Bot):
    """
    Script-specific bot for Green Dragons, inheriting core logic from Bot.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, script_name="Green Dragons Bot")
        self.hp_threshold = self.config.get("hp_threshold", default=70)

    def _navigation_and_potions(self) -> None:
        """Handles the initial movement and potion usage phase."""
        actions = self.actions
        
        logger.debug("Teleporting and navigating to dragons")
        actions.click_inventory_slot(28)

        actions.wait("long")

        # ADDED FOR TESTING REMEMBER TO REMOVE
        actions.click_inventory_slot(1)
        logger.info("Clicking at inventory slot 1")
        actions.wait("long")
        logger.info("Clicking at inventory slot 3")
        actions.click_inventory_slot(3)

        for _ in range(2):
            logger.info("Walking to yellow tile marker")
           # actions.walk_to_marker("yellow_tile_marker")
            actions.click_color("yellow_tile_marker")
        actions.wait("long")

        actions.click_minimap("green_dragons")
        actions.wait("medium")

        actions.use_item("extended_antifire")
        actions.wait("medium")
        actions.use_item("super_combat")
        actions.wait("long")

    def _combat_loop_phase(self) -> None:
        """Handles the combat loop until the inventory is full."""
        state = self.state
        actions = self.actions

        logger.debug("Starting combat loop")
        kills = 0

        while not state.inventory_full():
            hp = state.get_health()
            if hp and hp < self.hp_threshold:
                logger.info(f"HP low: {hp}, eating")
                actions.eat("manta_ray")
                actions.wait("medium")

            if not state.in_combat():
                if actions.attack_npc("green_dragon"):
                    kills += 1
                    if kills % 5 == 0:
                        logger.debug(f"Kills: {kills}")

            time.sleep(1)

        logger.info(f"Inventory full, kills: {kills}")

    def run_cycle(self, bank_location: str, run_number: int) -> None:
        """
        Implements the main logic for a single run cycle.
        This is the method required by the parent Bot class.
        """
        # 1. Setup and Navigation State
        self._navigation_and_potions()

        # 2. Combat Loop State
        self._combat_loop_phase()

        # 3. Banking State
        self._teleport_and_bank(bank_location)
