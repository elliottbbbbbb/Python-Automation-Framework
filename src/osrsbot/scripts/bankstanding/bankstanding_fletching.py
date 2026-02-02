"""
Fletching Bankstander - GE bow-stringing workflow using BankstanderBot base class.

Workflow:
1. Right-click tagged banker (color) → select "Bank Banker"
2. Deposit all finished products, withdraw 14 bowstrings + 14 unstrung bows from tab
3. Close bank, click bowstring on unstrung bow in inventory
4. Press Space for Make All, press Space every ~5s for level-up popups
5. Detect completion via template matching (no more raw materials in inventory)
6. Loop

Uses a pre-configured bank tab with withdraw quantity set to 14.
"""

import logging
import random
import time
from pathlib import Path
from typing import List, Optional, Tuple

from osrsbot.core.state_types import StateExecutionContext, StateResult
from osrsbot.core.base_bankstander import BankstanderBot
from osrsbot.services.keyboard_service import KeyboardService
from osrsbot.services.wom_service import get_skill_level
from osrsbot.scripts.bankstanding.fletching_items import get_best_tier

logger = logging.getLogger(__name__)


class FletchingBot(BankstanderBot):
    """
    GE bow-stringing bankstander.

    Right-clicks a color-tagged banker at the Grand Exchange,
    withdraws bowstrings and unstrung bows from a pre-made bank tab,
    combines them in inventory, and waits for fletching to complete.
    """

    # Menu offset from right-click position to "Bank Banker" option
    DEFAULT_BANK_MENU_OFFSET = 45

    # Safety timeout for fletching wait loop (seconds)
    FLETCHING_TIMEOUT = 90.0

    # Minimum seconds before considering re-initiation (fletching 14 items takes ~20-25s)
    MIN_TIME_BEFORE_REINITIATE = 15.0

    # Re-check WOM every N cycles to confirm/correct level counter
    WOM_CHECK_INTERVAL = 10

    def __init__(self, *args, **kwargs):
        """
        Initialize GE fletching bankstander.

        Auto-selects the best bow tier based on the player's Fletching level
        via the Wise Old Man API. Falls back to oak shortbow if lookup fails.
        """
        # Auto-select tier from WOM before setting up templates
        tool_name = "bow string"
        material_name = "oak shortbow (u)"
        product_name = "oak shortbow"
        starting_level = 20  # default if WOM lookup fails

        config = kwargs.get("config")
        if config:
            # Manual override takes priority over WOM
            manual_level = config.get("fletching_starting_level", default="")
            if manual_level:
                try:
                    starting_level = int(manual_level)
                    logger.info(f"CONFIG: Using manual starting level {starting_level}")
                except (ValueError, TypeError):
                    logger.warning(f"CONFIG: Invalid fletching_starting_level '{manual_level}', ignoring")
                    manual_level = ""

            window_title = config.get("window_title", default="")
            rsn = window_title.replace("RuneLite - ", "") if window_title.startswith("RuneLite - ") else ""
            if rsn and not manual_level:
                # Force WOM to refresh hiscores before fetching level
                try:
                    import requests
                    requests.post(
                        f"https://api.wiseoldman.net/v2/players/{rsn}",
                        headers={"User-Agent": "OSRSAutomationFramework"},
                        timeout=10,
                    )
                    logger.info(f"WOM: Forced hiscores update for {rsn}")
                except Exception:
                    pass  # Best-effort update

                level = get_skill_level(rsn, "fletching")
                if level is not None:
                    starting_level = level
                else:
                    logger.warning("WOM: Could not fetch stats, defaulting to oak shortbow")

            # Select tier based on starting level (from config, WOM, or default)
            tier = get_best_tier(starting_level)
            if tier:
                tool_name = tier["tool_name"]
                material_name = tier["material_name"]
                product_name = tier["product_name"]
                logger.info(
                    f"Fletching level {starting_level} -> "
                    f"crafting {product_name}"
                )
            elif starting_level > 0:
                logger.warning(
                    f"Fletching level {starting_level} too low, "
                    f"defaulting to oak shortbow"
                )

        images_dir = Path(__file__).parent.parent.parent / "images" / "bot"

        # Tool templates (bowstring - shared across all tiers)
        tool_templates = sorted(images_dir.glob("items/bowstring*.png"))
        tool_template = [str(p) for p in tool_templates] if tool_templates else [
            str(images_dir / "items" / "bowstring.png")
        ]

        # Material templates - derive glob from material_name
        # "oak shortbow (u)" -> "oak_shortbow_u"
        mat_slug = material_name.replace(" ", "_").replace("(", "").replace(")", "")
        material_templates = sorted(images_dir.glob(f"items/{mat_slug}*.png"))
        material_template = [str(p) for p in material_templates] if material_templates else [
            str(images_dir / "items" / f"{mat_slug}.png")
        ]

        # Base class handles state machine setup
        super().__init__(
            item_name=material_name,
            item_search_text="",
            item_template=material_template[0],
            item_search_threshold=0.75,
            processed_item_name=product_name,
            *args,
            **kwargs,
            script_name="Fletching (GE Bow Stringing)",
        )

        # Banker interaction config
        self._banker_color = "ge_banker"
        self._bank_menu_offset = self.DEFAULT_BANK_MENU_OFFSET

        # Item templates (used for both bank tab clicking and inventory detection)
        self._tool_name = tool_name
        self._tool_template = tool_template
        self._material_name = material_name
        self._material_template = material_template
        self._product_name = product_name

        # Level tracking for auto-upgrade
        self._current_level = starting_level
        self._images_dir = images_dir

        # Processing config
        self._space_interval = 5.0

        # Keyboard service for pressing Space (GameActions doesn't have one)
        self.keyboard = KeyboardService()

        # Track whether X quantity button has been clicked this session
        self._x_quantity_set = False

        # Fletching Make All menu template(s) for detection
        menu_templates = sorted(images_dir.glob("ui_templates/fletching_menu*.png"))
        self._fletching_menu_templates = (
            [str(p) for p in menu_templates] if menu_templates
            else [str(images_dir / "ui_templates" / "fletching_menu.png")]
        )

        # Bank X quantity button template(s)
        x_button_templates = sorted(images_dir.glob("ui_templates/bank_button_x*.png"))
        self._bank_x_button_templates = (
            [str(p) for p in x_button_templates] if x_button_templates
            else [str(images_dir / "ui_templates" / "bank_button_x.png")]
        )

        # Deposit inventory button template(s)
        deposit_templates = sorted(images_dir.glob("ui_templates/bank_deposit_inventory*.png"))
        self._deposit_inventory_templates = (
            [str(p) for p in deposit_templates] if deposit_templates
            else [str(images_dir / "ui_templates" / "bank_deposit_inventory.png")]
        )

        # Finished product template(s) for deposit verification
        prod_slug = product_name.replace(" ", "_")
        product_templates = sorted(images_dir.glob(f"items/{prod_slug}*.png"))
        self._product_template = (
            [str(p) for p in product_templates] if product_templates
            else [str(images_dir / "items" / f"{prod_slug}.png")]
        )

        # Level-up popup template(s) for detection
        levelup_templates = sorted(images_dir.glob("ui_templates/fletching_level_up*.png"))
        self._levelup_templates = (
            [str(p) for p in levelup_templates] if levelup_templates
            else [str(images_dir / "ui_templates" / "fletching_level_up.png")]
        )

        # Config reference for periodic WOM re-checks
        self._config = config

    def _upgrade_tier(self) -> bool:
        """Check if level crossed a tier threshold and upgrade templates."""
        tier = get_best_tier(self._current_level)
        if not tier or tier["material_name"] == self._material_name:
            return False

        old_name = self._material_name
        self._material_name = tier["material_name"]
        self._product_name = tier["product_name"]

        # Reload material templates
        mat_slug = self._material_name.replace(" ", "_").replace("(", "").replace(")", "")
        mat_paths = sorted(self._images_dir.glob(f"items/{mat_slug}*.png"))
        self._material_template = (
            [str(p) for p in mat_paths] if mat_paths
            else [str(self._images_dir / "items" / f"{mat_slug}.png")]
        )

        # Reload product templates
        prod_slug = self._product_name.replace(" ", "_")
        prod_paths = sorted(self._images_dir.glob(f"items/{prod_slug}*.png"))
        self._product_template = (
            [str(p) for p in prod_paths] if prod_paths
            else [str(self._images_dir / "items" / f"{prod_slug}.png")]
        )

        logger.info(
            f"UPGRADE: Level {self._current_level} - "
            f"switching from {old_name} to {self._material_name}"
        )
        return True

    def _get_wom_level(self, force_update: bool = True) -> Optional[int]:
        """Fetch current fletching level from WOM, optionally forcing a refresh."""
        if not self._config:
            return None

        window_title = self._config.get("window_title", default="")
        rsn = (
            window_title.replace("RuneLite - ", "")
            if window_title.startswith("RuneLite - ")
            else ""
        )
        if not rsn:
            return None

        if force_update:
            try:
                import requests
                requests.post(
                    f"https://api.wiseoldman.net/v2/players/{rsn}",
                    headers={"User-Agent": "OSRSAutomationFramework"},
                    timeout=10,
                )
            except Exception:
                pass  # Best-effort update

        return get_skill_level(rsn, "fletching")

    def _wom_level_check(self) -> None:
        """Periodic WOM re-check to confirm/correct level counter."""
        if self._cycles % self.WOM_CHECK_INTERVAL != 0 or self._cycles == 0:
            return

        wom_level = self._get_wom_level(force_update=True)
        if wom_level is not None and wom_level != self._current_level:
            logger.info(
                f"WOM CHECK: Correcting level "
                f"{self._current_level} -> {wom_level}"
            )
            self._current_level = wom_level
            self._upgrade_tier()
        elif wom_level is not None:
            logger.info(
                f"WOM CHECK: Level confirmed at {wom_level}"
            )

    def _open_bank_via_color(self) -> bool:
        """
        Find tagged banker by color, right-click, and select "Bank Banker".

        Returns:
            True if bank was opened successfully, False otherwise.
        """
        actions = self.actions

        # Get banker color hex from config
        banker_hex = self.config.get("colors", self._banker_color)
        if not banker_hex:
            logger.error(
                f"BANKING: Banker color '{self._banker_color}' not found in config"
            )
            return False

        # Find banker on screen by color (restrict to game viewport)
        viewport_region = actions.screen.get_game_viewport_region()
        matches = actions.screen.find_color(
            banker_hex, tolerance=10, region=viewport_region, find_all=True
        )
        if not matches:
            logger.error("BANKING: Could not find banker color on screen")
            return False

        # Compute centroid of all matching pixels for accurate clicking
        total_x = sum(m.x for m in matches)
        total_y = sum(m.y for m in matches)
        center_x = total_x // len(matches)
        center_y = total_y // len(matches)

        # Convert window-relative coords to absolute screen coords
        abs_x, abs_y = actions.coord_resolver.to_absolute(center_x, center_y)
        logger.info(
            f"BANKING: Found banker centroid at window=({center_x}, {center_y}) "
            f"abs=({abs_x}, {abs_y}) from {len(matches)} pixels"
        )

        # Right-click the banker (converted to absolute screen coords)
        if not actions.mouse.click_at(
            abs_x, abs_y, button="right", move_style="curved"
        ):
            logger.error("BANKING: Failed to right-click banker")
            return False

        actions.wait("short")

        # Click "Bank Banker" menu option at y-offset
        menu_y = abs_y + self._bank_menu_offset
        if not actions.mouse.click_at(
            abs_x, menu_y, button="left", move_style="linear"
        ):
            logger.error("BANKING: Failed to click Bank Banker menu option")
            return False

        actions.wait("long")
        return True

    def _handle_banking(self, context: StateExecutionContext) -> StateResult:
        """
        Handle BANKING state - open bank, deposit, and withdraw items.

        Combines deposit + withdraw into one bank session:
        1. Right-click banker → "Bank Banker"
        2. Deposit all (finished products from previous cycle)
        3. Click bowstring in bank tab (qty pre-set to 14)
        4. Click oak shortbow (u) in bank tab (qty pre-set to 14)
        5. Close bank
        """
        self._check_exit_requested()
        self._update_ui(
            "BANKING",
            f"Opening bank for {self._tool_name} and {self._material_name}...",
        )
        logger.info(
            f"BANKING: Opening bank for {self._tool_name} + {self._material_name}"
        )

        try:
            actions = self.actions

            # If bank is already open (left open by DEPOSIT), skip re-opening
            if self._bank_open:
                logger.info("BANKING: Bank already open from deposit, skipping open")
            else:
                # Close any open interfaces first
                actions.close_interface()
                actions.wait("short")

                # Right-click banker to open bank
                logger.info("BANKING: Right-clicking banker to open bank")
                if not self._open_bank_via_color():
                    logger.error("BANKING: Failed to open bank via color")
                    return StateResult.FAILURE

                self._bank_open = True

                # Verify bank actually opened (not collection box)
                # Use X button template since bank_search_button.PNG doesn't exist
                bank_check = self.state.find_multi_template(
                    self._bank_x_button_templates, threshold=0.6
                )
                if not bank_check:
                    logger.warning(
                        "BANKING: Bank not detected after clicking banker, retrying"
                    )
                    self._bank_open = False
                    self._x_quantity_set = False
                    return StateResult.FAILURE
                logger.info("BANKING: Bank verified open (X button detected)")

                # Deposit any leftover items before withdrawing
                # (only needed on fresh open — DEPOSIT already cleared inventory)
                self._update_ui("BANKING", "Depositing inventory...")
                logger.info("BANKING: Depositing all items before withdrawal")
                actions.click_template(
                    self._deposit_inventory_templates, "deposit inventory", threshold=0.7
                )
                actions.wait("short")

            # Click X quantity button only on first cycle (stays set for session)
            if not self._x_quantity_set:
                self._update_ui("BANKING", "Selecting X quantity...")
                logger.info("BANKING: Clicking X quantity button")
                if actions.click_template(
                    self._bank_x_button_templates, "bank X button", threshold=0.6
                ):
                    self._x_quantity_set = True
                else:
                    logger.warning("BANKING: Could not find X button, continuing anyway")

            actions.wait("short")

            # Step 1: Click tool (bowstring) in bank tab
            self._update_ui("BANKING", f"Withdrawing {self._tool_name}...")
            logger.info(f"BANKING: Clicking {self._tool_name} in bank tab")

            if not actions.click_template(
                self._tool_template, self._tool_name, threshold=0.6
            ):
                logger.error(
                    f"BANKING: Failed to find {self._tool_name} in bank tab"
                )
                self._bank_open = False
                self._x_quantity_set = False
                return StateResult.FAILURE

            actions.wait("short")

            # Step 2: Click material (oak shortbow u) in bank tab
            self._update_ui("BANKING", f"Withdrawing {self._material_name}...")
            logger.info(f"BANKING: Clicking {self._material_name} in bank tab")

            if not actions.click_template(
                self._material_template, self._material_name, threshold=0.6
            ):
                logger.error(
                    f"BANKING: Failed to find {self._material_name} in bank tab"
                )
                self._bank_open = False
                self._x_quantity_set = False
                return StateResult.FAILURE

            actions.wait("short")

            # Step 3: Close bank
            logger.info("BANKING: Closing bank interface")
            actions.close_interface()
            actions.wait("short")

            # Record action for anti-ban
            if hasattr(actions, "anti_ban") and actions.anti_ban:
                actions.anti_ban.record_action("bank_withdraw")

            logger.info("BANKING: Both items withdrawn successfully")
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"BANKING: Failed - {e}")
            self._bank_open = False
            self._x_quantity_set = False
            return StateResult.FAILURE

    def _handle_deposit(self, context: StateExecutionContext) -> StateResult:
        """
        Handle DEPOSIT state - open bank and deposit all finished products.

        After fletching completes, open the bank and deposit all oak shortbows.
        Leaves bank open so the next BANKING state can skip re-opening.
        """
        self._check_exit_requested()
        self._update_ui("DEPOSIT", f"Depositing {self._product_name}...")
        logger.info(f"DEPOSIT: Opening bank to deposit {self._product_name}")

        try:
            actions = self.actions

            # Open bank via right-click banker
            if not self._open_bank_via_color():
                logger.error("DEPOSIT: Failed to open bank via color")
                return StateResult.FAILURE

            self._bank_open = True

            # Deposit all items
            self._update_ui("DEPOSIT", "Depositing all items...")
            logger.info("DEPOSIT: Clicking deposit inventory")
            if not actions.click_template(
                self._deposit_inventory_templates, "deposit inventory", threshold=0.7
            ):
                logger.warning(
                    "DEPOSIT: Deposit inventory button not found, "
                    "continuing anyway"
                )

            # Verify deposit worked — retry if items still in inventory
            # Check for finished product (oak shortbow) in inventory region only
            inv_region = self.state.get_inventory_region()
            for retry in range(2):
                actions.wait("short")
                still_has_items = self.state.find_multi_template(
                    self._product_template, threshold=0.8, region=inv_region
                )
                if not still_has_items:
                    logger.info("DEPOSIT: Inventory cleared successfully")
                    break
                logger.warning(
                    f"DEPOSIT: Items still in inventory, "
                    f"retrying deposit (attempt {retry + 2})"
                )
                actions.click_template(
                    self._deposit_inventory_templates, "deposit inventory", threshold=0.7
                )

            # Leave bank open for next BANKING state to withdraw
            self._cycles += 1
            logger.info(
                f"DEPOSIT: Cycle {self._cycles} complete "
                f"(~{self._items_processed} items total)"
            )

            # Periodic WOM re-check to confirm/correct level counter
            self._wom_level_check()

            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"DEPOSIT: Failed - {e}")
            self._bank_open = False
            self._x_quantity_set = False
            return StateResult.FAILURE

    def _find_tool_in_inventory(self) -> bool:
        """Check if the tool (bowstring) is still visible in inventory."""
        result = self.state.find_multi_template(
            self._tool_template, threshold=0.7
        )
        return result is not None

    def process_items(self, context: StateExecutionContext) -> StateResult:
        """
        Process items - combine bowstring with unstrung bow, wait for fletching.

        Flow:
        1. Ensure inventory is open
        2. Find and click bowstring in inventory
        3. Find and click oak shortbow (u) in inventory
        4. Wait for Make All interface → press Space
        5. Press Space every ~5s (handles level-up popups)
        6. Detect completion: bowstring template no longer found in inventory
        """
        try:
            actions = self.actions

            # Open inventory
            if not actions.ensure_inventory_open():
                logger.error("PROCESS: Failed to open inventory")
                return StateResult.FAILURE

            actions.wait("short")

            # Step 1: Find and click the tool (bowstring) in inventory
            self._update_ui("PROCESS", f"Clicking {self._tool_name}...")
            logger.info(f"PROCESS: Finding {self._tool_name} in inventory")

            tool_match = self.state.find_multi_template(
                self._tool_template, threshold=0.7
            )
            if not tool_match:
                logger.error(
                    f"PROCESS: Could not find {self._tool_name} in inventory"
                )
                return StateResult.FAILURE

            center_x, center_y, confidence, _tmpl = tool_match
            abs_x, abs_y = actions.coord_resolver.to_absolute(center_x, center_y)
            logger.info(
                f"PROCESS: Found {self._tool_name} at ({center_x}, {center_y}) "
                f"conf={confidence:.2f}"
            )
            actions.mouse.click_at(abs_x, abs_y, move_style="curved")
            actions.wait("short")

            # Step 2: Find and click the material (oak shortbow u) in inventory
            self._update_ui("PROCESS", f"Using on {self._material_name}...")
            logger.info(f"PROCESS: Finding {self._material_name} in inventory")

            material_match = self.state.find_multi_template(
                self._material_template, threshold=0.7
            )
            if not material_match:
                logger.error(
                    f"PROCESS: Could not find {self._material_name} in inventory"
                )
                return StateResult.FAILURE

            center_x, center_y, confidence, _tmpl = material_match
            abs_x, abs_y = actions.coord_resolver.to_absolute(center_x, center_y)
            logger.info(
                f"PROCESS: Found {self._material_name} at ({center_x}, {center_y}) "
                f"conf={confidence:.2f}"
            )
            actions.mouse.click_at(abs_x, abs_y, move_style="curved")

            # Step 3: Wait for Make All interface to appear (poll with timeout)
            logger.info("PROCESS: Waiting for Make All interface...")
            self._update_ui("PROCESS", "Waiting for Make All menu...")
            menu_timeout = 5.0
            poll_interval = 0.3
            poll_start = time.time()
            menu_found = False

            while time.time() - poll_start < menu_timeout:
                result = self.state.find_multi_template(
                    self._fletching_menu_templates, threshold=0.6
                )
                if result:
                    logger.info(
                        f"PROCESS: Make All menu detected (conf={result[2]:.2f})"
                    )
                    menu_found = True
                    break
                time.sleep(poll_interval)

            if not menu_found:
                logger.warning(
                    "PROCESS: Make All menu not detected within timeout, "
                    "pressing Space anyway"
                )

            # Step 4: Press Space for Make All
            self._update_ui("PROCESS", "Pressing Space for Make All...")
            logger.info("PROCESS: Pressing Space for Make All")
            self.keyboard.press("space", mode="humanized")

            # Step 5: Fletching wait loop - press Space periodically, handle level-ups
            start_time = time.time()
            last_craft_start = time.time()
            space_count = 0

            while True:
                self._check_exit_requested()

                elapsed = time.time() - start_time

                # Safety timeout
                if elapsed > self.FLETCHING_TIMEOUT:
                    logger.warning(
                        f"PROCESS: Fletching timeout after {elapsed:.0f}s"
                    )
                    break

                # Wait for the space interval with some jitter
                jitter = random.uniform(-0.5, 1.0)
                sleep_time = max(1.0, self._space_interval + jitter)
                self._update_ui(
                    "PROCESS",
                    f"Fletching... ({elapsed:.0f}s elapsed)",
                )
                time.sleep(sleep_time)

                # Check if raw materials are gone (fletching complete)
                if not self._find_tool_in_inventory():
                    logger.info(
                        f"PROCESS: {self._tool_name} no longer in inventory - "
                        f"fletching complete after {elapsed:.0f}s"
                    )
                    break

                # Press Space to dismiss any level-up popup
                space_count += 1
                self.keyboard.press("space", mode="humanized")
                logger.info(
                    f"PROCESS: Space press #{space_count} at {elapsed:.0f}s"
                )

                # Brief pause then check if level-up popup is visible
                time.sleep(1.0)
                levelup_result = self.state.find_multi_template(
                    self._levelup_templates, threshold=0.7
                )
                if levelup_result:
                    wom_level = self._get_wom_level(force_update=True)
                    if wom_level is not None and wom_level > self._current_level:
                        logger.info(
                            f"PROCESS: Level-up detected! WOM says {wom_level} "
                            f"(was {self._current_level})"
                        )
                        self._current_level = wom_level
                    else:
                        self._current_level += 1
                        logger.info(
                            f"PROCESS: Level-up detected! Now level "
                            f"{self._current_level} (WOM: {wom_level})"
                        )
                    self._upgrade_tier()
                    # Dismiss popup and re-press Space for Make All
                    self.keyboard.press("space", mode="humanized")
                    time.sleep(1.0)
                    self.keyboard.press("space", mode="humanized")
                    continue

                # Only consider re-initiation after minimum time has passed
                # (during normal fletching, bowstrings are present and no
                # Make All menu — that's the expected state)
                time_since_craft = time.time() - last_craft_start
                if time_since_craft > self.MIN_TIME_BEFORE_REINITIATE:
                    if self._find_tool_in_inventory():
                        time.sleep(1.5)
                        if self._find_tool_in_inventory():
                            # Check if level-up popup appeared
                            levelup_result2 = self.state.find_multi_template(
                                self._levelup_templates, threshold=0.7
                            )
                            if levelup_result2:
                                wom_level = self._get_wom_level(force_update=True)
                                if wom_level is not None and wom_level > self._current_level:
                                    logger.info(
                                        f"PROCESS: Level-up detected (re-check)! "
                                        f"WOM says {wom_level} (was {self._current_level})"
                                    )
                                    self._current_level = wom_level
                                else:
                                    self._current_level += 1
                                    logger.info(
                                        f"PROCESS: Level-up detected (re-check)! "
                                        f"Now level {self._current_level} (WOM: {wom_level})"
                                    )
                                self._upgrade_tier()
                                self.keyboard.press("space", mode="humanized")
                                time.sleep(1.0)
                                self.keyboard.press("space", mode="humanized")
                                last_craft_start = time.time()
                            else:
                                # Fletching stopped — re-click items to restart
                                logger.info(
                                    "PROCESS: Fletching appears stopped, "
                                    "re-initiating craft"
                                )
                                self._update_ui(
                                    "PROCESS",
                                    "Re-initiating craft after interruption...",
                                )

                                tool_match = self.state.find_multi_template(
                                    self._tool_template, threshold=0.7
                                )
                                if not tool_match:
                                    logger.warning(
                                        "PROCESS: Can't find bowstring for "
                                        "re-initiation"
                                    )
                                    continue

                                cx, cy, conf, _ = tool_match
                                ax, ay = actions.coord_resolver.to_absolute(cx, cy)
                                actions.mouse.click_at(
                                    ax, ay, move_style="curved"
                                )
                                actions.wait("short")

                                mat_match = self.state.find_multi_template(
                                    self._material_template, threshold=0.7
                                )
                                if not mat_match:
                                    logger.warning(
                                        "PROCESS: Can't find material for "
                                        "re-initiation"
                                    )
                                    continue

                                cx, cy, conf, _ = mat_match
                                ax, ay = actions.coord_resolver.to_absolute(cx, cy)
                                actions.mouse.click_at(
                                    ax, ay, move_style="curved"
                                )

                                # Wait for Make All and press Space
                                time.sleep(2.0)
                                self.keyboard.press("space", mode="humanized")
                                last_craft_start = time.time()
                                logger.info(
                                    "PROCESS: Re-initiated craft, pressed Space"
                                )

            # Record action for anti-ban
            if hasattr(actions, "anti_ban") and actions.anti_ban:
                actions.anti_ban.record_action("fletch_cycle")

            self._items_processed += 14
            logger.info(
                f"PROCESS: Fletching cycle complete "
                f"(~{self._items_processed} items total)"
            )

            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"PROCESS: Failed - {e}")
            return StateResult.FAILURE
