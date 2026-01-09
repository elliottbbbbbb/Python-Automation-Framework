"""
Manual Cleaning Bankstander - Simplified using BankstanderBot base class.

Cleans grimy toadflax by clicking each inventory slot.

This is the simplified version that uses the reusable BankstanderBot base class.
All banking logic is handled by the base class - we just define item processing!
"""

# NOTE KNOWN_GOOD / PRODUCTION

import logging
import random
import time
from pathlib import Path

from osrsbot.core.state_types import StateExecutionContext, StateResult
from osrsbot.core.base_bankstander import BankstanderBot

logger = logging.getLogger(__name__)


class GrimyFlaxBot(BankstanderBot):
    """
    Bankstander that cleans grimy toadflax by clicking each inventory slot.

    Uses BankstanderBot base class for all banking logic - only implements
    the item processing logic specific to cleaning herbs.
    """

    def __init__(self, *args, **kwargs):
        """Initialize manual cleaning bankstander."""
        # Setup template path for grimy toadflax
        images_dir = Path(__file__).parent.parent / "images" / "bot" / "items"
        grimy_toadflax_template = str(images_dir / "grimy_toadflax.PNG")

        # Pass item config to base class - that's it!
        # Base class handles ALL the banking logic
        super().__init__(
            item_name="grimy toadflax",
            item_search_text="toadflax",
            item_template=grimy_toadflax_template,
            item_search_threshold=0.75,
            processed_item_name="cleaned toadflax",
            *args,
            **kwargs,
            script_name="Manual Cleaning Bankstander",
        )

    def process_items(self, context: StateExecutionContext) -> StateResult:
        """
        Process the items - clean herbs by clicking each inventory slot.

        This is the ONLY method we need to implement!
        Everything else (banking, depositing, state management) is handled
        by the BankstanderBot base class.
        """
        try:
            actions = self.actions

            # Open inventory
            logger.info("PROCESS: Opening inventory")
            if not actions.ensure_inventory_open():
                logger.error("PROCESS: Failed to open inventory")
                return StateResult.FAILURE

            actions.wait("short")

            # Choose processing pattern for anti-ban variety
            pattern_choice = random.random()

            if pattern_choice < 0.60:
                # 60% - Normal sequential (1→2→3...28)
                slot_order = list(range(1, 29))
                logger.debug("PROCESS: Using sequential pattern")
            elif pattern_choice < 0.90:
                # 30% - Randomized order
                slot_order = list(range(1, 29))
                random.shuffle(slot_order)
                logger.debug("PROCESS: Using randomized pattern")
            else:
                # 10% - Columns (process column by column)
                slot_order = []
                for col in range(4):  # 4 columns
                    for row in range(7):  # 7 rows
                        slot_num = row * 4 + col + 1
                        if slot_num <= 28:
                            slot_order.append(slot_num)
                logger.debug("PROCESS: Using column pattern")

            # Click each inventory slot to clean herbs
            herbs_this_cycle = 0
            # NOTE: Lazily implemented - to be moved to game actions later
            for slot in slot_order:
                # Check for exit request
                self._check_exit_requested()

                # Update UI
                self._update_ui("CLEAN_HERBS", f"Cleaning herb {slot}/28...")

                logger.debug(f"PROCESS: Clicking slot {slot}")

                # Record action for anti-ban pattern detection
                if hasattr(actions, 'anti_ban') and actions.anti_ban:
                    actions.anti_ban.record_action("clean_herb")

                # Click the inventory slot
                if actions.click_inventory_slot(slot, move_style="curved"):
                    herbs_this_cycle += 1
                    # Use existing wait system (already has anti-ban variance)
                    actions.wait("micro")
                else:
                    logger.warning(f"PROCESS: Failed to click slot {slot}")

            # Update total processed count
            self._items_processed += herbs_this_cycle
            logger.info(
                f"PROCESS: Cleaned {herbs_this_cycle} herbs "
                f"(total: {self._items_processed})"
            )

            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"PROCESS: Failed - {e}")
            return StateResult.FAILURE
