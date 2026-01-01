"""
Test script to click all template-matched UI elements.

This script:
1. Detects all UI grids (inventory, minimap, chat) using template matching
2. Detects all UI buttons (logout, autoretal, good clicks) using template matching
3. Subdivides grids into individual slots and clicks them
4. Clicks detected button centers
5. Useful for testing template matching and mouse precision
"""

import logging
import time

from osrsbot.core.game_interface import GameInterface
from osrsbot.models.config import Config
from osrsbot.services.mouse_service import MouseConfig, MouseService
from osrsbot.services.screen_service import ScreenService
from osrsbot.services.template_match_service import TemplateMatchService

logger = logging.getLogger(__name__)


def test_inventory_clicks():
    """
    Click all template-matched UI elements.

    Returns:
        True if test completed successfully, False otherwise
    """
    # Load config to get window title
    config = Config("config.json")
    window_title = config.get("window_title")

    if not window_title:
        logger.error("No window_title in config")
        return False

    logger.info("=" * 60)
    logger.info("TEMPLATE MATCHING CLICK TEST")
    logger.info("=" * 60)

    # Initialize services
    logger.info("Initializing services...")
    interface = GameInterface(config)

    mouse_config_dict = config.get("mouse", default={})
    mouse_config = MouseConfig(
        min_speed=mouse_config_dict.get("min_speed", 0.2),
        max_speed=mouse_config_dict.get("max_speed", 0.6),
        overshoot_chance=mouse_config_dict.get("overshoot_chance", 0.15),
        overshoot_distance=mouse_config_dict.get("overshoot_distance", 20),
        click_variance=mouse_config_dict.get("click_variance", 3),
        post_click_delay=(
            mouse_config_dict.get("post_click_delay_min", 0.05),
            mouse_config_dict.get("post_click_delay_max", 0.15),
        ),
    )

    mouse = MouseService(mouse_config)
    screen = ScreenService(window_getter=interface.get_bounds)
    template_service = TemplateMatchService()

    # Register templates from config
    try:
        template_service.register_from_config(config)
        logger.info("Templates registered from config")
    except Exception as e:
        logger.error(f"Failed to register templates: {e}")
        return False

    # Capture screenshot for detection
    logger.info("Capturing screenshot...")
    screenshot = screen.capture_grayscale()
    if screenshot is None:
        logger.error("Failed to capture screenshot")
        return False

    # Get window position to convert relative coords to absolute
    window_pos = interface.get_window_position()
    if not window_pos:
        logger.error("Failed to get window position!")
        return False

    win_x, win_y, _, _ = window_pos
    logger.info(f"Window position: ({win_x}, {win_y})")
    logger.info("")

    total_clicks = 0
    successful_detections = 0

    try:
        # Detect all UI grids (but only click inventory)
        logger.info("=" * 60)
        logger.info("DETECTING UI GRIDS")
        logger.info("=" * 60)

        grid_names = [
            "inventory",
            "equipment",
            "prayer",
            "spellbook",
            "minimap",
            "chat",
        ]
        for grid_name in grid_names:
            logger.info(f"\n--- Detecting {grid_name.upper()} grid ---")

            detected = template_service.detect_grid(grid_name, screenshot)

            if not detected:
                logger.warning(
                    f"❌ {grid_name} grid not detected (might not be visible)"
                )
                continue

            grid = template_service.get_grid(grid_name)
            if not grid:
                logger.warning(f"❌ {grid_name} grid object not found")
                continue

            successful_detections += 1
            elements = grid.elements
            logger.info(f"✓ {grid_name} detected with {len(elements)} elements")

            if grid.detected_bbox:
                x, y, w, h = grid.detected_bbox
                logger.info(f"✓ Region: ({x}, {y}) {w}x{h} (relative to window)")

        # Detect all UI buttons (but don't click them)
        logger.info("")
        logger.info("=" * 60)
        logger.info("DETECTING UI BUTTONS")
        logger.info("=" * 60)

        button_names = [
            "inventory_tab",
            "equipment_tab",
            "prayer_tab",
            "spellbook_tab",
            "skills_tab",
            "logout_tab",
            "logout",
            "settings_collapse",
            "bank_presets",
            "autoretal_on",
            "autoretal_off",
            "good_click_1",
            "good_click_2",
            "good_click_3",
            "good_click_4",
        ]

        for button_name in button_names:
            logger.info(f"\n--- Detecting {button_name.upper()} button ---")

            detected = template_service.detect_button(button_name, screenshot)

            if not detected:
                logger.warning(
                    f"❌ {button_name} button not detected (might not be visible)"
                )
                continue

            button = template_service.get_button(button_name)
            if not button or not button.element:
                logger.warning(f"❌ {button_name} button object not found")
                continue

            successful_detections += 1
            element = button.element
            logger.info(f"✓ {button_name} detected")
            logger.info(
                f"✓ Region: ({
                    element.x0}, {
                    element.y0}) {
                    element.width}x{
                    element.height}"
            )

        # Click the inventory tab to open it
        logger.info("")
        logger.info("=" * 60)
        logger.info("OPENING INVENTORY TAB")
        logger.info("=" * 60)

        # Detect inventory tab button
        inventory_tab_detected = template_service.detect_button(
            "inventory_tab", screenshot
        )
        if not inventory_tab_detected:
            logger.warning("❌ Inventory tab button not detected")
            logger.warning("Attempting to click inventory slots anyway...")
        else:
            inventory_tab_button = template_service.get_button("inventory_tab")
            if inventory_tab_button and inventory_tab_button.element:
                tab_element = inventory_tab_button.element
                tab_rel_x, tab_rel_y = tab_element.center_x, tab_element.center_y
                tab_abs_x = win_x + tab_rel_x
                tab_abs_y = win_y + tab_rel_y

                logger.info(
                    f"✓ Inventory tab button detected at ({tab_rel_x}, {tab_rel_y})"
                )
                logger.info("Clicking inventory tab button...")
                mouse.click(tab_abs_x, tab_abs_y)
                total_clicks += 1
                time.sleep(1.0)  # Wait for tab to open

                # Re-capture screenshot after opening tab
                logger.info("Re-capturing screenshot after opening inventory tab...")
                screenshot = screen.capture_grayscale()
                if screenshot is None:
                    logger.error("Failed to re-capture screenshot")
                    return False

                # Re-detect inventory grid
                logger.info("Re-detecting inventory grid...")
                template_service.detect_grid("inventory", screenshot, force=True)

        # Now click the inventory slots
        logger.info("")
        logger.info("=" * 60)
        logger.info("CLICKING INVENTORY SLOTS")
        logger.info("=" * 60)

        inventory_grid = template_service.get_grid("inventory")
        if not inventory_grid or not inventory_grid.visible:
            logger.error("Inventory grid not detected! Cannot click slots.")
            return False

        slots = inventory_grid.elements
        total_slots = len(slots)

        logger.info(f"Starting to click all {total_slots} inventory slots...")
        logger.info("(Press Ctrl+C to stop)")
        logger.info("")

        for i, slot in enumerate(slots, 1):
            rel_x, rel_y = slot.center_x, slot.center_y
            abs_x = win_x + rel_x
            abs_y = win_y + rel_y

            logger.info(
                f"Clicking slot {
                    i:2d}/{total_slots} at relative ({
                    rel_x:4d}, {
                    rel_y:4d}) -> absolute ({
                    abs_x:4d}, {
                        abs_y:4d})"
            )
            mouse.click(abs_x, abs_y)
            total_clicks += 1
            time.sleep(0.5)

        # Click other tab buttons to verify they work
        logger.info("")
        logger.info("=" * 60)
        logger.info("TESTING OTHER TAB BUTTONS")
        logger.info("=" * 60)

        other_tabs = [
            ("equipment_tab", "equipment"),
            ("prayer_tab", "prayer"),
            ("spellbook_tab", "spellbook"),
        ]

        for tab_button_name, grid_name in other_tabs:
            logger.info(f"\n--- Testing {tab_button_name.upper()} ---")

            # Detect the tab button
            tab_detected = template_service.detect_button(tab_button_name, screenshot)
            if not tab_detected:
                logger.warning(f"❌ {tab_button_name} button not detected, skipping")
                continue

            tab_button = template_service.get_button(tab_button_name)
            if not tab_button or not tab_button.element:
                logger.warning(
                    f"❌ {tab_button_name} button object not found, skipping"
                )
                continue

            # Click the tab button
            tab_element = tab_button.element
            tab_rel_x, tab_rel_y = tab_element.center_x, tab_element.center_y
            tab_abs_x = win_x + tab_rel_x
            tab_abs_y = win_y + tab_rel_y

            logger.info(f"✓ {tab_button_name} detected at ({tab_rel_x}, {tab_rel_y})")
            logger.info(f"Clicking {tab_button_name}...")
            mouse.click(tab_abs_x, tab_abs_y)
            total_clicks += 1
            time.sleep(1.0)

            # Re-capture screenshot and verify grid is visible
            logger.info(f"Verifying {grid_name} grid is now visible...")
            screenshot_after = screen.capture_grayscale()
            if screenshot_after is None:
                logger.warning("Failed to capture screenshot after tab click")
                continue

            grid_detected = template_service.detect_grid(
                grid_name, screenshot_after, force=True
            )
            if grid_detected:
                grid = template_service.get_grid(grid_name)
                if grid:
                    logger.info(
                        f"✓ {grid_name} grid now visible with {len(grid.elements)} elements"
                    )
                    successful_detections += 1
            else:
                logger.warning(f"❌ {grid_name} grid not detected after clicking tab")

        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ Test completed successfully!")
        logger.info(f"✓ Detected {successful_detections} UI elements")
        logger.info(f"✓ Performed {total_clicks} clicks")
        logger.info("=" * 60)
        return True

    except KeyboardInterrupt:
        logger.info("")
        logger.warning("Test interrupted by user")
        logger.info(f"Completed {total_clicks} clicks before interruption")
        return False
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    # Run the test
    success = test_inventory_clicks()

    # Exit with appropriate code
    exit(0 if success else 1)
