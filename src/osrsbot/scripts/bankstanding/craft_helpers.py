"""
Shared bankstanding craft helpers.

Standalone functions that take the bot instance as first parameter.
Uses bot.state (queries) and bot.actions (commands) — proper architecture.

No direct service imports. All access goes through the bot's DI-provided
actions and state facades.
"""

import logging
import random
import time
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template path helpers
# ---------------------------------------------------------------------------

def make_slug(name: str) -> str:
    """Convert item name to filesystem slug: 'oak shortbow (u)' -> 'oak_shortbow_u'."""
    return name.replace(" ", "_").replace("(", "").replace(")", "")


def glob_templates(images_dir: Path, pattern: str) -> List[str]:
    """Glob for template images and return sorted path list as strings."""
    paths = sorted(images_dir.glob(pattern))
    return [str(p) for p in paths]


def load_item_templates(images_dir: Path, item_name: str) -> List[str]:
    """Load all template variants for an item name."""
    slug = make_slug(item_name)
    templates = glob_templates(images_dir, f"items/{slug}*.png")
    if not templates:
        templates = [str(images_dir / "items" / f"{slug}.png")]
    return templates


# ---------------------------------------------------------------------------
# Bank interaction
# ---------------------------------------------------------------------------

def open_bank_via_color(
    bot,
    banker_color: str,
    bank_menu_templates: List[str],
    menu_offset: int = 45,
) -> bool:
    """
    Find tagged banker by color, right-click, and select 'Bank Banker'.

    Args:
        bot: Bot instance (must have .actions, .state, .config)
        banker_color: Config color key for the banker (e.g. 'ge_banker')
        bank_menu_templates: Template paths for the 'Bank Banker' menu option
        menu_offset: Fallback pixel offset if no menu templates available

    Returns:
        True if bank was opened successfully
    """
    actions = bot.actions

    banker_hex = bot.config.get("colors", banker_color)
    if not banker_hex:
        logger.error(f"Banker color '{banker_color}' not found in config")
        return False

    viewport_region = actions.screen.get_game_viewport_region()
    matches = actions.screen.find_color(
        banker_hex, tolerance=10, region=viewport_region, find_all=True
    )
    if not matches:
        logger.error("Could not find banker color on screen")
        return False

    # Centroid of all matching pixels
    total_x = sum(m.x for m in matches)
    total_y = sum(m.y for m in matches)
    center_x = total_x // len(matches)
    center_y = total_y // len(matches)

    abs_x, abs_y = actions.coord_resolver.to_absolute(center_x, center_y)
    logger.info(
        f"Found banker centroid at ({center_x}, {center_y}) "
        f"from {len(matches)} pixels"
    )

    # Right-click banker
    if not actions.mouse.click_at(abs_x, abs_y, button="right", move_style="curved"):
        logger.error("Failed to right-click banker")
        return False

    actions.wait("short")

    # Verify and click 'Bank Banker' menu option
    if bank_menu_templates:
        menu_result = bot.state.find_multi_template(bank_menu_templates, threshold=0.7)
        if menu_result is None:
            logger.warning("'Bank Banker' menu not found — wrong NPC?")
            actions.press_key("escape")
            actions.wait("short")
            return False

        menu_x, menu_y, conf, _ = menu_result
        abs_menu_x, abs_menu_y = actions.coord_resolver.to_absolute(menu_x, menu_y)
        logger.info(f"Found 'Bank Banker' menu at ({menu_x}, {menu_y}) conf={conf:.2f}")
        if not actions.mouse.click_at(abs_menu_x, abs_menu_y, button="left", move_style="linear"):
            logger.error("Failed to click Bank Banker menu option")
            return False
    else:
        menu_y = abs_y + menu_offset
        if not actions.mouse.click_at(abs_x, menu_y, button="left", move_style="linear"):
            logger.error("Failed to click Bank Banker menu option")
            return False

    actions.wait("long")
    return True


# ---------------------------------------------------------------------------
# Crafting menu & level-up handling
# ---------------------------------------------------------------------------

def wait_for_menu(
    bot,
    menu_templates: List[str],
    timeout: float = 5.0,
    poll_interval: float = 0.3,
) -> bool:
    """Poll for the Make All / crafting menu to appear."""
    start = time.time()
    while time.time() - start < timeout:
        result = bot.state.find_multi_template(menu_templates, threshold=0.6)
        if result:
            logger.info(f"Make All menu detected (conf={result[2]:.2f})")
            return True
        time.sleep(poll_interval)
    logger.warning("Make All menu not detected within timeout")
    return False


def dismiss_level_up(bot) -> None:
    """Dismiss level-up popup + 'items unlocked' dialog with two space presses."""
    bot.actions.press_key("space")
    time.sleep(2.0)
    bot.actions.press_key("space")
    time.sleep(0.5)


def reinitiate_craft(
    bot,
    tool_templates: List[str],
    material_templates: List[str],
) -> bool:
    """Re-click tool on material and press Space for Make All."""
    actions = bot.actions

    tool_match = bot.state.find_multi_template(tool_templates, threshold=0.7)
    if not tool_match:
        logger.warning("Can't find tool for re-initiation")
        return False

    cx, cy, _, _ = tool_match
    ax, ay = actions.coord_resolver.to_absolute(cx, cy)
    actions.mouse.click_at(ax, ay, move_style="curved")
    actions.wait("short")

    mat_match = bot.state.find_multi_template(material_templates, threshold=0.7)
    if not mat_match:
        logger.warning("Can't find material for re-initiation")
        actions.press_key("escape")  # Cancel 'use item on' mode
        return False

    cx, cy, _, _ = mat_match
    ax, ay = actions.coord_resolver.to_absolute(cx, cy)
    actions.mouse.click_at(ax, ay, move_style="curved")
    time.sleep(2.0)
    actions.press_key("space")
    logger.info("Craft re-initiated")
    return True


# ---------------------------------------------------------------------------
# Main crafting wait loop
# ---------------------------------------------------------------------------

def monitor_craft_loop(
    bot,
    tool_templates: List[str],
    material_templates: List[str],
    levelup_templates: List[str],
    on_level_up,
    craft_timeout: float = 90.0,
    min_reinitiate: float = 25.0,
    space_interval: float = 5.0,
) -> int:
    """
    Main crafting wait loop: watch for completion, level-ups, re-initiation.

    Args:
        bot: Bot instance
        tool_templates: Templates for the tool item
        material_templates: Templates for the material item
        levelup_templates: Templates for level-up popup detection
        on_level_up: Callback fn() called when level-up detected (update level, etc.)
        craft_timeout: Max seconds to wait
        min_reinitiate: Seconds before considering re-initiation
        space_interval: Base polling interval

    Returns:
        Number of level-ups detected during this loop
    """
    start_time = time.time()
    last_craft_start = time.time()
    level_ups = 0

    def _has_tool():
        return bot.state.find_multi_template(tool_templates, threshold=0.85) is not None

    def _has_material():
        return bot.state.find_multi_template(material_templates, threshold=0.85) is not None

    while True:
        bot._check_exit_requested()
        elapsed = time.time() - start_time

        if elapsed > craft_timeout:
            logger.warning(f"Craft timeout after {elapsed:.0f}s")
            break

        # Wait with jitter
        jitter = random.uniform(-0.5, 1.0)
        sleep_time = max(1.0, space_interval + jitter)
        bot._update_ui("PROCESS", f"Crafting... ({elapsed:.0f}s elapsed)")
        time.sleep(sleep_time)

        # Check completion (materials depleted)
        if not _has_tool() or not _has_material():
            logger.info(f"Materials depleted — crafting complete after {elapsed:.0f}s")
            break

        # Check for level-up popup
        levelup_result = bot.state.find_multi_template(levelup_templates, threshold=0.7)
        if levelup_result:
            level_ups += 1
            on_level_up()
            dismiss_level_up(bot)
            reinitiate_craft(bot, tool_templates, material_templates)
            last_craft_start = time.time()
            continue

        # Re-initiation check after min time
        time_since_craft = time.time() - last_craft_start
        if time_since_craft > min_reinitiate:
            if _has_tool() and _has_material():
                time.sleep(1.5)
                if _has_tool() and _has_material():
                    # Double-check for level-up
                    levelup_result2 = bot.state.find_multi_template(
                        levelup_templates, threshold=0.7
                    )
                    if levelup_result2:
                        level_ups += 1
                        on_level_up()
                        dismiss_level_up(bot)
                        reinitiate_craft(bot, tool_templates, material_templates)
                        last_craft_start = time.time()
                    else:
                        logger.info("Crafting appears stopped, re-initiating")
                        bot._update_ui("PROCESS", "Re-initiating craft after interruption...")
                        reinitiate_craft(bot, tool_templates, material_templates)
                        last_craft_start = time.time()

    return level_ups


# ---------------------------------------------------------------------------
# Tier management
# ---------------------------------------------------------------------------

def find_best_available_tier(
    bot,
    tier_list: list,
    images_dir: Path,
    current_level: int,
    current_material: str,
    exclude_current: bool = False,
    tool_is_shared: bool = True,
) -> Optional[dict]:
    """
    Scan open bank for the highest tier with available materials.

    Args:
        bot: Bot instance
        tier_list: Ordered (highest first) list of tier dicts
        images_dir: Path to images/bot directory
        current_level: Player's current skill level
        current_material: Current material name (for exclude_current)
        exclude_current: Skip the current tier
        tool_is_shared: If True (fletching), only check material. If False
                        (herblore), check both tool and material.
    """
    for tier in tier_list:
        if tier["min_level"] > current_level:
            continue

        if exclude_current and tier["material_name"] == current_material:
            continue

        mat_templates = load_item_templates(images_dir, tier["material_name"])
        mat_result = bot.state.find_multi_template(mat_templates, threshold=0.8)
        if mat_result is None:
            continue

        if not tool_is_shared:
            tool_templates = load_item_templates(images_dir, tier["tool_name"])
            tool_result = bot.state.find_multi_template(tool_templates, threshold=0.8)
            if tool_result is None:
                continue

        return tier

    return None
