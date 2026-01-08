"""
Example Bot with UI Debug Visualization

This example demonstrates how to integrate UI debug visualization into your bot scripts.
It shows you exactly what the bot sees with red boxes around detected UI elements.

This is useful for:
- Debugging detection issues
- Verifying template matching works correctly
- Understanding bot behavior
- Creating new scripts
"""

import logging
import sys
from pathlib import Path

import cv2 as cv
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from osrsbot.core.runner import ScriptRunner
from osrsbot.core.base_bot import Bot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class ExampleUIDebugBot(Bot):
    """
    Example bot that demonstrates UI debug visualization.

    This bot doesn't do anything useful - it just captures screenshots
    and saves debug images showing detected UI elements.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.script_name = "UI Debug Example Bot"

    def run_cycle(self, bank_location: str, run_number: int):
        """
        One cycle: capture screenshot, detect UI, save debug image.
        """
        logger.info(f"Starting cycle {run_number + 1}")

        # Enable UI debug if available
        if self.actions.ui_manager:
            self.actions.ui_manager.enable_debug("ui_debug/example_bot")
            logger.info("UI debug enabled")
        else:
            logger.warning("UIManager not available")

        # Wait a moment for UI to be ready
        self.actions.wait("short")

        # Capture screenshots
        logger.info("Capturing screenshots...")
        img_gray = self.state.screen.capture_grayscale()

        # Capture color image and convert PIL to BGR numpy array
        img_pil = self.state.screen.capture()
        img_color = cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)

        # Detect all UI elements (force fresh detection)
        logger.info("Detecting UI elements...")
        if self.actions.template_service:
            detection_results = self.actions.template_service.detect_all(
                img_gray, force=True
            )
            logger.info(f"Detection completed: {len(detection_results)} elements checked")
        else:
            logger.warning("TemplateMatchService not available")

        # Get visible elements
        if self.actions.ui_manager:
            visible = self.actions.ui_manager.get_visible_elements()

            print("\n" + "=" * 80)
            print(f"CYCLE {run_number + 1} - UI DETECTION RESULTS")
            print("=" * 80)

            # Print detected grids
            if visible['grids']:
                print(f"\nDetected Grids ({len(visible['grids'])}):")
                for grid_name in visible['grids']:
                    grid = self.actions.ui_manager.get_grid(grid_name)
                    print(f"  ✓ {grid_name:15s} - {grid.num_rows}×{grid.num_cols} "
                          f"({len(grid.elements):2d} slots) - "
                          f"confidence: {grid.last_confidence:.3f}")
            else:
                print("\nNo grids detected!")

            # Print detected buttons
            if visible['buttons']:
                print(f"\nDetected Buttons ({len(visible['buttons'])}):")
                for button_name in visible['buttons']:
                    button = self.actions.ui_manager.get_button(button_name)
                    print(f"  ✓ {button_name:30s} - "
                          f"confidence: {button.last_confidence:.3f}")
            else:
                print("\nNo buttons detected!")

            # Print not detected elements
            all_grids = set(self.actions.ui_manager.grids.keys())
            all_buttons = set(self.actions.ui_manager.buttons.keys())
            hidden_grids = all_grids - set(visible['grids'])
            hidden_buttons = all_buttons - set(visible['buttons'])

            if hidden_grids or hidden_buttons:
                print(f"\nNot Detected:")
                for name in sorted(hidden_grids):
                    grid = self.actions.ui_manager.get_grid(name)
                    print(f"  ✗ Grid: {name:15s} - threshold: {grid.threshold}")
                for name in sorted(hidden_buttons):
                    button = self.actions.ui_manager.get_button(name)
                    print(f"  ✗ Button: {name:30s} - threshold: {button.threshold}")

            print("=" * 80)

            # Save debug image
            logger.info("Saving debug image...")
            saved_path = self.actions.ui_manager.save_debug_image(
                img_color,
                prefix=f"cycle_{run_number + 1:03d}",
                show_grids=True,
                show_buttons=True,
                show_slots=True,
                show_labels=True
            )

            if saved_path:
                print(f"\n✓ Saved debug image: {saved_path}")
                print("  Open this image to see red boxes around detected UI elements")
            print()

            # Example: Check specific elements
            logger.info("Checking specific UI elements...")

            # Check if inventory is visible
            inventory = self.actions.ui_manager.get_grid("inventory")
            if inventory and inventory.visible:
                print("Inventory Details:")
                print(f"  - Visible: Yes")
                print(f"  - Size: {inventory.num_rows}×{inventory.num_cols}")
                print(f"  - Total slots: {len(inventory.elements)}")
                print(f"  - Confidence: {inventory.last_confidence:.3f}")
                print(f"  - Bounding box: {inventory.detected_bbox}")

                # Example: Get position of first slot (slot 0)
                if len(inventory.elements) > 0:
                    slot_0 = inventory.elements[0]
                    print(f"  - Slot 0 center: {slot_0.center}")
                    print(f"  - Slot 0 bounds: {slot_0.bbox}")
            else:
                print("Inventory: Not detected")

            # Check if prayer tab is visible
            prayer_tab = self.actions.ui_manager.get_button("prayer_tab")
            if prayer_tab and prayer_tab.visible:
                print("\nPrayer Tab Details:")
                print(f"  - Visible: Yes")
                print(f"  - Center: {prayer_tab.element.center}")
                print(f"  - Confidence: {prayer_tab.last_confidence:.3f}")
            else:
                print("\nPrayer Tab: Not detected")

            print()

        # Wait before next cycle
        logger.info(f"Cycle {run_number + 1} complete. Waiting before next cycle...")
        self.actions.wait("medium")


def main():
    """Main entry point."""
    print("=" * 80)
    print("EXAMPLE UI DEBUG BOT")
    print("=" * 80)
    print()
    print("This bot demonstrates UI debug visualization.")
    print("It will:")
    print("  1. Capture screenshots of the game")
    print("  2. Detect all UI elements (grids and buttons)")
    print("  3. Draw red boxes around detected elements")
    print("  4. Save annotated images to ui_debug/example_bot/")
    print()
    print("Check the console output to see detection results.")
    print("Check the saved images to see visual annotations.")
    print()
    print("=" * 80)
    print()

    try:
        # Initialize runner
        print("Initializing bot...")
        runner = ScriptRunner(
            window_title="RuneLite",  # Change this to match your window
            config_file="config.json"
        )
        print("Bot initialized successfully!")
        print()

        # Create bot instance
        bot = ExampleUIDebugBot(
            interface=runner.interface,
            state=runner.state,
            actions=runner.actions,
            config=runner.config,
            script_name="UI Debug Example",
            enable_exit_key=True,  # Press 'q' to exit
            enable_status_ui=True
        )

        # Run bot for a few cycles
        print("Starting bot... (Press 'q' to exit)")
        print()
        bot.run(
            bank_location="varrock",
            runs=3  # Run 3 cycles to capture multiple screenshots
        )

        print()
        print("=" * 80)
        print("Bot completed successfully!")
        print()
        print("Check the following locations:")
        print("  - Console output: Detection results for each cycle")
        print("  - ui_debug/example_bot/: Annotated screenshots with red boxes")
        print()
        print("=" * 80)

    except KeyboardInterrupt:
        print("\n\nBot interrupted by user")
    except Exception as e:
        logger.error(f"Bot failed: {e}", exc_info=True)
        print(f"\nError: {e}")
        print("\nMake sure:")
        print("  1. RuneLite (or your game client) is open")
        print("  2. config.json has correct window_title")
        print("  3. Template images exist in src/osrsbot/images/bot/")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
