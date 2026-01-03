"""
Example Bankstander - Shows how easy it is to create a new bankstander script.

This example shows processing any item - just pass the item details to the base class!
"""

import logging
import random
import time
from pathlib import Path

from osrsbot.core.state_types import StateExecutionContext, StateResult
from osrsbot.core.base_bankstander import BankstanderBot

logger = logging.getLogger(__name__)


class ExampleBankstanderBot(BankstanderBot):
    """
    Example bankstander - processes items by clicking each inventory slot.

    To create a new bankstander for a different item, just:
    1. Copy this file
    2. Change the item name and template path in __init__
    3. Optionally customize process_items() if needed
    """

    def __init__(self, *args, **kwargs):
        """Initialize example bankstander."""
        # Setup item template path
        images_dir = Path(__file__).parent.parent / "images" / "bot" / "items"
        item_template = str(images_dir / "my_item.PNG")  # Change this!

        # Pass item config to base class - that's it!
        super().__init__(
            item_name="my item",  # Display name
            item_search_text="my item",  # What to type in bank search
            item_template=item_template,  # Path to item image
            item_search_threshold=0.75,  # How strict the matching is
            processed_item_name="processed item",  # Name after processing (optional)
            *args,
            **kwargs,
            script_name="Example Bankstander",  # Bot name
        )

    def process_items(self, context: StateExecutionContext) -> StateResult:
        """
        Process the items - this is the only method you need to implement!

        This example clicks each inventory slot to process items.
        Customize this for your specific needs.
        """
        try:
            actions = self.actions

            # Open inventory
            if not actions.ensure_inventory_open():
                logger.error("PROCESS: Failed to open inventory")
                return StateResult.FAILURE

            actions.wait("short")

            # Click each inventory slot (1-28)
            items_this_cycle = 0
            for slot in range(1, 29):
                self._check_exit_requested()
                self._update_ui("PROCESS", f"Processing item {slot}/28...")

                # Click the inventory slot
                if actions.click_inventory_slot(slot, move_style="curved"):
                    items_this_cycle += 1
                    # Random delay for human-like behavior
                    time.sleep(random.uniform(0.05, 0.15))
                else:
                    logger.warning(f"PROCESS: Failed to click slot {slot}")

            self._items_processed += items_this_cycle
            logger.info(
                f"PROCESS: Processed {items_this_cycle} items "
                f"(total: {self._items_processed})"
            )

            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"PROCESS: Failed - {e}")
            return StateResult.FAILURE
