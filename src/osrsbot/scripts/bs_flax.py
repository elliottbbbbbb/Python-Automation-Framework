"""
Manual Cleaning Bankstander - Simplified using BankstanderBot base class.

Cleans grimy toadflax by clicking each inventory slot.

This is the simplified version that uses the reusable BankstanderBot base class.
All banking logic is handled by the base class - we just define item processing!
"""

import logging
import random
import time
from pathlib import Path

from osrsbot.core.state_types import StateExecutionContext, StateResult
from osrsbot.core.base_bankstander import BankstanderBot

logger = logging.getLogger(__name__)


class grimy_flax(BankstanderBot):
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

            # Click each inventory slot (1-28) to clean herbs
            herbs_this_cycle = 0

            for slot in range(1, 29):
                # Check for exit request
                self._check_exit_requested()

                # Update UI
                self._update_ui("CLEAN_HERBS", f"Cleaning herb {slot}/28...")

                logger.debug(f"PROCESS: Clicking slot {slot}")

                # Click the inventory slot
                if actions.click_inventory_slot(slot, move_style="curved"):
                    herbs_this_cycle += 1
                    # Random delay for human-like behavior (50-150ms)
                    time.sleep(random.uniform(0.05, 0.15))
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
