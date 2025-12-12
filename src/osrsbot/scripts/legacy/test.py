"""
TEST BOT - LEGACY VERSION (DEPRECATED)

⚠️ DEPRECATED: This is the legacy function-based implementation.
⚠️ Use test_state_machine_bot.py (state machine version) instead.

This file is kept for reference only.
The function-based approach is harder to maintain and test.
New bots should use the StateMachineBot framework.

See: src/osrsbot/scripts/test_state_machine_bot.py
"""
import time
import logging
from osrsbot.queries.game_queries import GameState
from osrsbot.models.config import Config
<<<<<<< HEAD
from osrsbot.commands.game_actions import GameActions as Actions
=======
from osrsbot.controllers.actions import GameActions as Actions
>>>>>>> origin/main
from osrsbot.constants import GAME_TIMING

logger = logging.getLogger(__name__)


def test_script(
    interface,
    state: GameState,
    actions: Actions,
    config: Config,
    bank_location: str = "GE",
    runs: int = 10
) -> None:
    """
    Test template matching by clicking all 28 inventory slots.

    This validates:
    - Inventory grid detection
    - Slot position calculation
    - Coordinate conversion (relative → absolute)
    - Template caching
    """
    print(f"\n{'='*60}")
    print("TEMPLATE MATCHING TEST - CLICK ALL 28 INVENTORY SLOTS")
    print(f"{'='*60}")
    print("\n📋 This test will:")
    print("  1. Detect the inventory grid using template matching")
    print("  2. Calculate all 28 slot positions mathematically")
    print("  3. Click each slot in order (1-28)")
    print("  4. Show ✅/❌ for each slot\n")
    print("⚠️  Make sure your OSRS window is visible and inventory is open!")
    print(f"   Runs: {runs}\n")

    input("Press ENTER to start...")

    for run in range(runs):
        print(f"\n{'='*60}")
        print(f"RUN {run + 1}/{runs}")
        print(f"{'='*60}\n")

        for slot in range(1, 29):
            try:
                logger.info(f"Run {run + 1}/{runs} - Clicking slot {slot}/28")
                print(f"  📍 Slot {slot:02d}/28", end="", flush=True)

                success = actions.click_inventory_slot_detected(slot)

                if success:
                    print(" ✅")
                else:
                    print(" ❌ (detection failed)")
                    logger.warning(f"Failed to click slot {slot}")

                time.sleep(GAME_TIMING.test_click_delay)

            except Exception as e:
                logger.error(f"Error clicking slot {slot}: {e}", exc_info=True)
                print(f" ❌ Error: {e}")

        if run < runs - 1:
            delay = GAME_TIMING.test_run_delay
            print(f"\n⏸️  Run {run + 1} complete. Next run in {delay} seconds...")
            time.sleep(delay)

    print(f"\n{'='*60}")
    print("✅ TEST COMPLETE!")
    print(f"{'='*60}\n")


