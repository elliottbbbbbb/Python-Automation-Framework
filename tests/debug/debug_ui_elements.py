"""
Debug UI Element Detection

This script visualizes detected UI elements with colored boxes overlaid on the game window.
It helps you see exactly what the bot is detecting and where clickable regions are.

Features:
- Colored boxes around all detected grids (green=inventory, red=spellbook, blue=prayer, purple=equipment)
- Thin boxes around each individual grid slot
- Colored dots showing center points for clicking
- Labels showing element names and confidence scores
- Saves annotated screenshots to ui_debug/ folder
- Toggle individual grids on/off

Usage:
    python debug_ui_elements.py

Controls:
    - Press 'q' to capture a new screenshot and refresh detection
    - Press ESC to exit
    - Press 's' to toggle slot boxes
    - Press 'g' to toggle grid boxes
    - Press 'l' to toggle labels
    - Press 'b' to toggle button boxes
    - Press '1' to toggle inventory grid
    - Press '2' to toggle spellbook grid
    - Press '3' to toggle prayer grid
    - Press '4' to toggle equipment grid
    - Press 'a' to show all grids
    - Press 'n' to hide all grids
"""

import cv2 as cv
import logging
import numpy as np
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from osrsbot.models.config import Config
from osrsbot.core.game_interface import GameInterface
from osrsbot.services.screen_service import ScreenService
from osrsbot.services.template_match_service import TemplateMatchService
from osrsbot.services.ui_manager_service import UIManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    print("=" * 80)
    print("UI ELEMENT DEBUG VISUALIZER")
    print("=" * 80)
    print()
    print("This tool shows all detected UI elements with red boxes.")
    print()
    print("Controls:")
    print("  - Press 'q' to capture new screenshot and refresh")
    print("  - Press ESC to exit")
    print("  - Press 's' to toggle slot numbers")
    print("  - Press 'g' to toggle grid boxes")
    print("  - Press 'b' to toggle button boxes")
    print()
    print("=" * 80)
    print()

    try:
        # Load config
        logger.info("Loading configuration...")
        config = Config()

        # Initialize game interface
        logger.info("Attaching to game window...")
        interface = GameInterface(config)
        logger.info(f"Attached to: {interface.get_title()}")

        # Initialize screen service
        screen = ScreenService(window_getter=interface.get_bounds)

        # Initialize template matching service
        logger.info("Initializing template matching service...")
        template_service = TemplateMatchService()

        # Register all UI grids manually (using inventory_empty.PNG for all)
        logger.info("Registering UI grids...")

        # Inventory grid (7x4 = 28 slots)
        template_service.register_grid(
            name="inventory",
            template_path="src/osrsbot/images/bot/ui_templates/inventory_empty.PNG",
            num_rows=7,
            num_cols=4,
            threshold=0.30,
            sticky=True,
            padding=0,
            border_offset=20
        )

        # Equipment grid (7x2 = 14 slots)
        template_service.register_grid(
            name="equipment",
            template_path="src/osrsbot/images/bot/ui_templates/inventory_empty.PNG",
            num_rows=7,
            num_cols=2,
            threshold=0.30,
            sticky=True,
            padding=0,
            border_offset=13
        )

        # Prayer grid (6x5 = 30 prayers)
        template_service.register_grid(
            name="prayer",
            template_path="src/osrsbot/images/bot/ui_templates/inventory_empty.PNG",
            num_rows=6,
            num_cols=5,
            threshold=0.30,
            sticky=True,
            padding=0,
            border_offset=13
        )

        # Spellbook grid (10x7 = 70 spells)
        template_service.register_grid(
            name="spellbook",
            template_path="src/osrsbot/images/bot/ui_templates/inventory_empty.PNG",
            num_rows=10,
            num_cols=7,
            threshold=0.30,
            sticky=True,
            padding=2,
            border_offset=15,
            border_offset_x=22,
            border_offset_y=12
        )

        # Initialize UI manager
        logger.info("Initializing UI manager...")
        ui_manager = UIManager(template_service)
        ui_manager.sync_from_template_service()
        ui_manager.enable_debug()

        # Print registered elements
        print(f"\nRegistered UI Elements:")
        print(f"  - Grids: {len(ui_manager.grids)}")
        for name in ui_manager.grids.keys():
            print(f"    * {name}")
        print(f"  - Buttons: {len(ui_manager.buttons)}")
        for name in ui_manager.buttons.keys():
            print(f"    * {name}")
        print()

        # Display settings
        show_grids = True
        show_buttons = True
        show_slots = True
        show_labels = True

        # Grid visibility toggles
        visible_grids = {
            "inventory": True,
            "spellbook": True,
            "prayer": True,
            "equipment": True
        }

        # Main loop
        print("Starting visualization loop...")
        print("Press 'q' to capture/refresh, ESC to exit")
        print("Press '1' for inventory, '2' for spellbook, '3' for prayer, '4' for equipment")
        print("Press 'a' to show all grids, 'n' to hide all grids")
        print()

        while True:
            try:
                # Capture screenshot
                logger.info("Capturing screenshot...")
                img_gray = screen.capture_grayscale()

                # Capture color image and convert PIL to BGR numpy array
                img_pil = screen.capture()
                img_color = cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)

                # Detect all UI elements
                logger.info("Detecting UI elements...")
                detection_results = template_service.detect_all(img_gray, force=True)

                # Print detection summary
                visible = ui_manager.get_visible_elements()
                print("\n" + "=" * 80)
                print(f"DETECTION RESULTS")
                print("=" * 80)
                print(f"Visible Grids ({len(visible['grids'])}):")
                for grid_name in visible['grids']:
                    grid = ui_manager.get_grid(grid_name)
                    print(f"  ✓ {grid_name}: {grid.num_rows}x{grid.num_cols} = {len(grid.elements)} slots, confidence={grid.last_confidence:.3f}")

                print(f"\nVisible Buttons ({len(visible['buttons'])}):")
                for button_name in visible['buttons']:
                    button = ui_manager.get_button(button_name)
                    print(f"  ✓ {button_name}: confidence={button.last_confidence:.3f}")

                print(f"\nNot Detected:")
                all_grids = set(ui_manager.grids.keys())
                all_buttons = set(ui_manager.buttons.keys())
                hidden_grids = all_grids - set(visible['grids'])
                hidden_buttons = all_buttons - set(visible['buttons'])

                if hidden_grids:
                    for name in hidden_grids:
                        print(f"  ✗ Grid: {name}")
                if hidden_buttons:
                    for name in hidden_buttons:
                        print(f"  ✗ Button: {name}")

                print("=" * 80)

                # Draw debug overlay
                logger.info("Drawing debug overlay...")
                img_debug = ui_manager.draw_debug_overlay(
                    img_color,
                    show_grids=show_grids,
                    show_buttons=show_buttons,
                    show_slots=show_slots,
                    show_labels=show_labels,
                    visible_grids=visible_grids
                )

                # Save debug image
                saved_path = ui_manager.save_debug_image(
                    img_color,
                    prefix="ui_detection",
                    show_grids=show_grids,
                    show_buttons=show_buttons,
                    show_slots=show_slots,
                    show_labels=show_labels,
                    visible_grids=visible_grids
                )
                if saved_path:
                    print(f"\n✓ Saved debug image: {saved_path}")

                # Resize for display if too large
                display_img = img_debug
                max_height = 900
                if display_img.shape[0] > max_height:
                    scale = max_height / display_img.shape[0]
                    new_width = int(display_img.shape[1] * scale)
                    display_img = cv.resize(display_img, (new_width, max_height))

                # Show image
                window_name = "UI Debug - Press 'q' to refresh, ESC to exit"
                cv.imshow(window_name, display_img)

                print("\nPress 'q' to refresh, ESC to exit")
                print("Toggles: 's'=slots, 'g'=grids, 'b'=buttons, 'l'=labels")
                print("Grids: '1'=inventory, '2'=spellbook, '3'=prayer, '4'=equipment")
                print("All grids: 'a'=show all, 'n'=hide all")

                # Helper function to redraw and display
                def redraw_display():
                    nonlocal display_img
                    # Always redraw from original img_color
                    debug_img = ui_manager.draw_debug_overlay(
                        img_color, show_grids, show_buttons, show_slots, show_labels, visible_grids
                    )
                    # Resize if needed
                    if debug_img.shape[0] > max_height:
                        scale = max_height / debug_img.shape[0]
                        new_width = int(debug_img.shape[1] * scale)
                        display_img = cv.resize(debug_img, (new_width, max_height))
                    else:
                        display_img = debug_img
                    cv.imshow(window_name, display_img)

                # Wait for key press
                while True:
                    key = cv.waitKey(100) & 0xFF

                    if key == 27:  # ESC
                        print("\nExiting...")
                        cv.destroyAllWindows()
                        return
                    elif key == ord('q'):  # Refresh
                        print("\nRefreshing detection...")
                        break
                    elif key == ord('1'):  # Toggle inventory
                        visible_grids["inventory"] = not visible_grids.get("inventory", True)
                        print(f"\nInventory: {'ON' if visible_grids['inventory'] else 'OFF'}")
                        redraw_display()
                    elif key == ord('2'):  # Toggle spellbook
                        visible_grids["spellbook"] = not visible_grids.get("spellbook", True)
                        print(f"\nSpellbook: {'ON' if visible_grids['spellbook'] else 'OFF'}")
                        redraw_display()
                    elif key == ord('3'):  # Toggle prayer
                        visible_grids["prayer"] = not visible_grids.get("prayer", True)
                        print(f"\nPrayer: {'ON' if visible_grids['prayer'] else 'OFF'}")
                        redraw_display()
                    elif key == ord('4'):  # Toggle equipment
                        visible_grids["equipment"] = not visible_grids.get("equipment", True)
                        print(f"\nEquipment: {'ON' if visible_grids['equipment'] else 'OFF'}")
                        redraw_display()
                    elif key == ord('a'):  # Show all grids
                        for grid_name in visible_grids.keys():
                            visible_grids[grid_name] = True
                        print("\nAll grids: ON")
                        redraw_display()
                    elif key == ord('n'):  # Hide all grids
                        for grid_name in visible_grids.keys():
                            visible_grids[grid_name] = False
                        print("\nAll grids: OFF")
                        redraw_display()
                    elif key == ord('s'):  # Toggle slots
                        show_slots = not show_slots
                        print(f"\nSlot numbers: {'ON' if show_slots else 'OFF'}")
                        redraw_display()
                    elif key == ord('g'):  # Toggle grids
                        show_grids = not show_grids
                        print(f"\nGrid boxes: {'ON' if show_grids else 'OFF'}")
                        redraw_display()
                    elif key == ord('b'):  # Toggle buttons
                        show_buttons = not show_buttons
                        print(f"\nButton boxes: {'ON' if show_buttons else 'OFF'}")
                        redraw_display()
                    elif key == ord('l'):  # Toggle labels
                        show_labels = not show_labels
                        print(f"\nLabels: {'ON' if show_labels else 'OFF'}")
                        redraw_display()

            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                cv.destroyAllWindows()
                break
            except Exception as e:
                logger.error(f"Error in visualization loop: {e}", exc_info=True)
                print(f"\nError: {e}")
                print("Press 'q' to try again or ESC to exit")

                while True:
                    key = cv.waitKey(100) & 0xFF
                    if key == 27:  # ESC
                        cv.destroyAllWindows()
                        return
                    elif key == ord('q'):
                        break

    except Exception as e:
        logger.error(f"Failed to initialize: {e}", exc_info=True)
        print(f"\nError: {e}")
        print("\nMake sure:")
        print("  1. The game window is open")
        print("  2. config.json has the correct window_title")
        print("  3. Template images exist in src/osrsbot/images/bot/")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
