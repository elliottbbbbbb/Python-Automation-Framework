"""
Debug script to visualize the game viewport region.

This script shows where the bot will search for NPCs (green area)
and which areas are excluded (red overlay - minimap, inventory, etc.).

Usage:
    python debug_viewport.py
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from osrsbot.core.game_interface import GameInterface
from osrsbot.models.config import Config
from osrsbot.services.screen_service import ScreenService


def main():
    print("=" * 60)
    print("OSRS Bot - Viewport Debug Visualization")
    print("=" * 60)
    print()
    print("This will show you the game viewport region:")
    print("  - GREEN area: Where the bot searches for NPCs")
    print("  - RED overlay: UI area excluded from NPC search")
    print()
    print("Instructions:")
    print("  1. Make sure RuneLite is open and visible")
    print("  2. A debug window will pop up showing the viewport")
    print("  3. Press any key to close the debug window")
    print()

    try:
        # Load config
        print("Loading configuration...")
        config = Config()

        # Initialize game interface
        print("Finding RuneLite window...")
        game_interface = GameInterface(config)

        if not game_interface.is_runelite_active():
            print("ERROR: RuneLite window not found!")
            print("Please start RuneLite and try again.")
            return 1

        print(f"✓ Found RuneLite window")

        # Get window bounds
        bounds = game_interface.get_window_bounds()
        if bounds:
            left, top, width, height = bounds
            print(f"  Window size: {width}x{height}")
            print(f"  Position: ({left}, {top})")

        # Initialize screen service
        screen_service = ScreenService(
            window_getter=game_interface.get_window_bounds
        )

        # Get viewport region
        region = screen_service.get_game_viewport_region()
        if region:
            x, y, vp_width, vp_height = region
            print(f"  Viewport size: {vp_width}x{vp_height}")
            print(f"  UI excluded: {width - vp_width}px wide")
            print()

        # Show debug visualization
        print("Showing viewport debug visualization...")
        print("(Press any key in the debug window to close)")
        print()

        screen_service.debug_show_viewport(duration=30)

        print()
        print("✓ Debug visualization closed")
        print()
        print("Viewport Configuration:")
        print(f"  - {(vp_width / width) * 100:.0f}% of window width is searchable")
        print(f"  - {((width - vp_width) / width) * 100:.0f}% is excluded (UI area)")
        print()
        print("The bot will only click NPCs in the GREEN area.")
        print("NPCs on the minimap (RED area) will be ignored.")

        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
