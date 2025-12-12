"""
Example showing the new click_inventory_slot() functionality.

Demonstrates:
- Automatic coordinate detection via template matching
- Fallback to config if template matching unavailable
- Works for all 28 slots (not just first 4)
"""
import logging
from osrsbot.models.config import Config
from osrsbot.queries.game_queries import GameState
from osrsbot.core.game_interface import GameInterface
<<<<<<< HEAD
from osrsbot.core.runner import ScriptRunner
=======
from osrsbot.controllers.runner import ScriptRunner
>>>>>>> origin/main

logger = logging.getLogger(__name__)


def example_old_way(config):
    """Old way: Only slots 1-4 and 28 work (hardcoded in config)."""
    print("\n=== Old Way (Config Only) ===")
    print("Only these slots have coordinates in config.json:")
    print("  - slot_1: (591, 257)")
    print("  - slot_2: (633, 256)")
    print("  - slot_3: (672, 257)")
    print("  - slot_4: (715, 258)")
    print("  - last_slot (28): (715, 470)")
    print("\nTrying to click slot 15:")
    print("  ❌ ERROR: No coordinates for slot 15")


def example_new_way_with_sync(actions, state):
    """
    New way: Template matching detects ALL 28 slots.

    Flow:
    1. Register inventory grid template
    2. Detect inventory (7x4 grid)
    3. Automatically subdivide into 28 slots
    4. Click any slot 1-28
    """
    print("\n=== New Way (Template Matching) ===")

    # First click will auto-sync if needed
    print("\n1. Clicking slot 15 (no sync yet)...")
    print("   - Inventory has no coordinates")
    print("   - Auto-sync triggered")
    print("   - Template matching detects inventory grid")
    print("   - Subdivides into 28 slots")
    print("   - Coordinates saved to all slots")
    print("   - Click successful! ✅")

    # actions.click_inventory_slot(15)  # Would work if game running

    print("\n2. Clicking slot 28 (already synced)...")
    print("   - Inventory already has coordinates")
    print("   - Direct click ✅")

    # actions.click_inventory_slot(28)

    print("\n3. Click any slot 1-28:")
    for slot in [1, 5, 10, 15, 20, 25, 28]:
        print(f"   - Slot {slot}: ✅ Coordinates available")


def example_manual_sync(state):
    """You can also manually sync inventory ahead of time."""
    print("\n=== Manual Sync (Proactive) ===")

    print("\n1. Manually sync inventory before clicking:")
    # state.sync_inventory_grid()
    print("   state.sync_inventory_grid()")
    print("   ✅ All 28 slots now have coordinates")

    print("\n2. Check inventory status:")
    inv = state.inventory
    print(f"   {inv}")

    print("\n3. Check specific slots:")
    for slot_num in [1, 15, 28]:
        slot = inv.get_slot(slot_num)
        if slot and slot.center:
            print(f"   Slot {slot_num}: {slot.center} ✅")
        else:
            print(f"   Slot {slot_num}: No coordinates ❌")


def example_fallback_behavior(actions):
    """If template matching fails, falls back to config."""
    print("\n=== Fallback Behavior ===")

    print("\n1. Template matching unavailable:")
    print("   - Inventory template not detected")
    print("   - OR inventory grid not visible")
    print("   - Falls back to config coordinates")

    print("\n2. Slots with config fallback:")
    print("   - Slot 1-4: ✅ (in config)")
    print("   - Slot 28: ✅ (in config)")
    print("   - Slot 5-27: ❌ (not in config)")

    print("\n3. To disable inventory system:")
    # actions.click_inventory_slot(1, use_inventory=False)
    print("   actions.click_inventory_slot(1, use_inventory=False)")
    print("   ✅ Forces config method")


def comparison_table():
    """Show side-by-side comparison."""
    print("\n" + "=" * 60)
    print("COMPARISON: Old vs New")
    print("=" * 60)

    print("\n┌─────────────────────────┬──────────────┬──────────────┐")
    print("│ Feature                 │ Old (Config) │ New (Inv.)   │")
    print("├─────────────────────────┼──────────────┼──────────────┤")
    print("│ Slots available         │ 5 slots      │ 28 slots     │")
    print("│ Setup required          │ Manual       │ Automatic    │")
    print("│ Window moves?           │ Still works  │ Still works  │")
    print("│ Zoom changes?           │ Breaks       │ Still works  │")
    print("│ Inventory position?     │ Hardcoded    │ Detected     │")
    print("│ Fallback if fails?      │ N/A          │ Uses config  │")
    print("└─────────────────────────┴──────────────┴──────────────┘")


def how_it_works():
    """Explain the internals."""
    print("\n" + "=" * 60)
    print("HOW IT WORKS")
    print("=" * 60)

    print("\nWhen you call: actions.click_inventory_slot(15)")
    print("\n1. Check if Inventory system available:")
    print("   └─ state.inventory exists? ✓")

    print("\n2. Get slot from Inventory:")
    print("   └─ slot = state.inventory.get_slot(15)")

    print("\n3. Check if slot has coordinates:")
    print("   ├─ If YES:")
    print("   │  └─ click_at(slot.center_x, slot.center_y) ✓")
    print("   │")
    print("   └─ If NO:")
    print("      ├─ Try sync: state.sync_inventory_grid()")
    print("      │  ├─ Register inventory template")
    print("      │  ├─ Detect in screenshot")
    print("      │  ├─ Subdivide 7x4 grid → 28 slots")
    print("      │  └─ Save coordinates to all slots")
    print("      │")
    print("      ├─ Retry: slot = inventory.get_slot(15)")
    print("      │  └─ Now has coordinates! ✓")
    print("      │")
    print("      └─ If still no coords:")
    print("         └─ Fallback to config coordinates")

    print("\n4. Template Matching Details:")
    print("   ├─ Detects ONE template (full inventory grid)")
    print("   ├─ Calculates cell size: width/4, height/7")
    print("   ├─ Creates 28 UIElements (one per cell)")
    print("   └─ Each has center coordinates for clicking")


def main():
    """Run examples."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    config = Config()
    window_title = config.get_window_title()

    print("\n" + "=" * 60)
    print("CLICK INVENTORY SLOT - NEW SYSTEM")
    print("=" * 60)

    # Show comparison
    comparison_table()

    # Show examples (without actual game)
    example_old_way(config)

    print("\n" + "─" * 60)

    # Would need game running for these:
    # interface = GameInterface(window_title)
    # runner = ScriptRunner(window_title)
    # example_new_way_with_sync(runner.actions, runner.state)
    # example_manual_sync(runner.state)
    # example_fallback_behavior(runner.actions)

    print("\n\n📝 Note: To test with actual game:")
    print("   1. Start RuneLite")
    print("   2. Create inventory template: templates/inventory_grid.png")
    print("   3. Run bot script")
    print("   4. click_inventory_slot() works for ALL 28 slots!")

    # Show internals
    how_it_works()


if __name__ == "__main__":
    main()
