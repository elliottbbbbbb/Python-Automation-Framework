"""
Fletching Bankstander - GE bow-stringing workflow using BankstanderBot base class.

Workflow:
1. Right-click tagged banker (color) -> select "Bank Banker"
2. Deposit all finished products, withdraw 14 bowstrings + 14 unstrung bows from tab
3. Close bank, click bowstring on unstrung bow in inventory
4. Press Space for Make All, monitor for level-ups
5. Detect completion via template matching (no more raw materials in inventory)
6. Loop

Uses a pre-configured bank tab with withdraw quantity set to 14.
"""

import logging
from pathlib import Path
from typing import Optional

from osrsbot.core.base_bankstander import BankstanderBot
from osrsbot.core.state_types import StateExecutionContext, StateResult
from osrsbot.scripts.bankstanding.fletching_items import get_best_tier, FLETCHING_TIERS
from osrsbot.scripts.bankstanding import craft_helpers
from osrsbot.scripts.bankstanding.craft_helpers import (
    glob_templates,
    load_item_templates,
    open_bank_via_color,
    wait_for_menu,
    monitor_craft_loop,
    find_best_available_tier,
)

logger = logging.getLogger(__name__)

MAX_NO_MATERIALS = 3
WOM_CHECK_INTERVAL = 5


class FletchingBot(BankstanderBot):
    """GE bow-stringing bankstander."""

    def __init__(self, *args, **kwargs):
        config = kwargs.get("config")
        starting_level = 20
        images_dir = Path(__file__).resolve().parent.parent.parent / "images" / "bot"

        # Determine starting level: config override > WOM > default
        if config:
            manual = config.get("fletching_starting_level", default="")
            if manual:
                try:
                    starting_level = int(manual)
                    logger.info(f"CONFIG: Manual starting level {starting_level}")
                except (ValueError, TypeError):
                    pass
            else:
                wom = self._initial_wom_lookup(config, "fletching")
                if wom is not None:
                    starting_level = wom

        tier = get_best_tier(starting_level)
        tool_name = tier["tool_name"] if tier else "bow string"
        material_name = tier["material_name"] if tier else "oak shortbow (u)"
        product_name = tier["product_name"] if tier else "oak shortbow"

        logger.info(f"Fletching level {starting_level} -> crafting {product_name}")

        # Load templates
        # Bowstring is shared across all tiers (tool_is_shared)
        tool_template = (
            glob_templates(images_dir, "items/bowstring*.png")
            or [str(images_dir / "items" / "bowstring.png")]
        )
        material_template = load_item_templates(images_dir, material_name)

        super().__init__(
            item_name=material_name,
            item_search_text="",
            item_template=material_template[0],
            item_search_threshold=0.75,
            processed_item_name=product_name,
            *args, **kwargs,
            script_name="Fletching (GE Bow Stringing)",
        )

        # Item state
        self._tool_name = tool_name
        self._tool_template = tool_template
        self._material_name = material_name
        self._material_template = material_template
        self._product_name = product_name
        self._current_level = starting_level
        self._images_dir = images_dir
        self._banker_color = "ge_banker"
        self._x_quantity_set = False
        self._no_materials_count = 0

        # UI templates
        self._menu_templates = (
            glob_templates(images_dir, "ui_templates/fletching_menu*.png")
            or [str(images_dir / "ui_templates" / "fletching_menu.png")]
        )
        self._bank_x_templates = (
            glob_templates(images_dir, "ui_templates/bank_button_x*.png")
            or [str(images_dir / "ui_templates" / "bank_button_x.png")]
        )
        self._deposit_templates = (
            glob_templates(images_dir, "ui_templates/bank_deposit_inventory*.png")
            or [str(images_dir / "ui_templates" / "bank_deposit_inventory.png")]
        )
        self._product_template = load_item_templates(images_dir, product_name)
        self._levelup_templates = (
            glob_templates(images_dir, "ui_templates/fletching_level_up*.png")
            or [str(images_dir / "ui_templates" / "fletching_level_up.png")]
        )
        self._bank_menu_templates = glob_templates(
            images_dir, "ui_templates/bank_banker_menu*.png"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _initial_wom_lookup(config, skill: str) -> Optional[int]:
        """One-time WOM lookup at init (before state/actions are available)."""
        from osrsbot.services.wom_service import get_skill_level

        window_title = config.get("window_title", default="")
        rsn = window_title.replace("RuneLite - ", "").strip() if window_title else ""
        if not rsn:
            return None
        try:
            import requests
            requests.post(
                f"https://api.wiseoldman.net/v2/players/{rsn}",
                headers={"User-Agent": "OSRSAutomationFramework"},
                timeout=10,
            )
        except Exception:
            pass
        return get_skill_level(rsn, skill)

    def _reload_templates(self, tier: dict) -> None:
        """Reload material + product templates after tier switch."""
        old = self._material_name
        self._material_name = tier["material_name"]
        self._product_name = tier["product_name"]
        # Bowstring stays the same (tool_is_shared)
        self._material_template = load_item_templates(self._images_dir, tier["material_name"])
        self._product_template = load_item_templates(self._images_dir, tier["product_name"])
        logger.info(f"TIER: Switched from {old} to {tier['material_name']}")

    def _open_bank(self) -> bool:
        return open_bank_via_color(self, self._banker_color, self._bank_menu_templates)

    def _wom_level_check(self) -> None:
        """Periodic WOM re-check to confirm/correct level counter."""
        if self._cycles % WOM_CHECK_INTERVAL != 0 or self._cycles == 0:
            return
        wom_level = self.state.get_skill_level_from_wom("fletching", force_update=True)
        if wom_level is not None and wom_level > self._current_level:
            logger.info(f"WOM CHECK: Correcting level {self._current_level} -> {wom_level}")
            self._current_level = wom_level
            tier = get_best_tier(self._current_level)
            if tier and tier["material_name"] != self._material_name:
                self._reload_templates(tier)

    # ------------------------------------------------------------------
    # State handlers
    # ------------------------------------------------------------------

    def _handle_banking(self, context: StateExecutionContext) -> StateResult:
        self._check_exit_requested()
        self._update_ui("BANKING", f"Opening bank for {self._tool_name} + {self._material_name}...")
        actions = self.actions

        try:
            if not self._bank_open:
                actions.close_interface()
                actions.wait("short")
                if not self._open_bank():
                    return StateResult.FAILURE
                self._bank_open = True

                # Verify bank opened
                if not self.state.find_multi_template(self._bank_x_templates, threshold=0.6):
                    logger.warning("BANKING: Bank not detected after click")
                    self._bank_open = False
                    self._x_quantity_set = False
                    return StateResult.FAILURE

                # Deposit leftovers
                actions.click_template(self._deposit_templates, "deposit inventory", threshold=0.7)
                actions.wait("short")

            # Set X quantity on first cycle
            if not self._x_quantity_set:
                if actions.click_template(self._bank_x_templates, "bank X button", threshold=0.6):
                    self._x_quantity_set = True
                actions.wait("short")

            # Check for best tier
            best = find_best_available_tier(
                self, FLETCHING_TIERS, self._images_dir,
                self._current_level, self._material_name,
                tool_is_shared=True,
            )
            if best and best["material_name"] != self._material_name:
                self._reload_templates(best)

            # Withdraw tool (bowstring)
            if not actions.click_template(self._tool_template, self._tool_name, threshold=0.8):
                logger.error(f"BANKING: {self._tool_name} not found in bank")
                self._bank_open = False
                self._x_quantity_set = False
                return StateResult.FAILURE
            actions.wait("short")

            # Withdraw material
            if not actions.click_template(self._material_template, self._material_name, threshold=0.8):
                # Fallback: try next best tier
                fallback = find_best_available_tier(
                    self, FLETCHING_TIERS, self._images_dir,
                    self._current_level, self._material_name,
                    exclude_current=True, tool_is_shared=True,
                )
                if fallback:
                    self._reload_templates(fallback)
                    if not actions.click_template(self._material_template, self._material_name, threshold=0.8):
                        self._bank_open = False
                        self._x_quantity_set = False
                        return StateResult.FAILURE
                else:
                    self._no_materials_count += 1
                    if self._no_materials_count >= MAX_NO_MATERIALS:
                        logger.info("BANKING: No materials at any tier, stopping")
                        self._exit_requested = True
                    self._bank_open = False
                    self._x_quantity_set = False
                    return StateResult.FAILURE
            actions.wait("short")

            # Verify withdrawals
            has_tool = self.state.find_multi_template(self._tool_template, threshold=0.85)
            has_mat = self.state.find_multi_template(self._material_template, threshold=0.85)
            if not has_tool or not has_mat:
                logger.error("BANKING: Withdrawal verification failed")
                self._bank_open = False
                self._x_quantity_set = False
                return StateResult.FAILURE

            self._no_materials_count = 0
            actions.close_interface()
            actions.wait("short")

            if actions.anti_ban:
                actions.anti_ban.record_action("bank_withdraw")

            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"BANKING: Failed - {e}")
            self._bank_open = False
            self._x_quantity_set = False
            return StateResult.FAILURE

    def process_items(self, context: StateExecutionContext) -> StateResult:
        try:
            actions = self.actions
            if not actions.ensure_inventory_open():
                return StateResult.FAILURE
            actions.wait("short")

            # Click tool in inventory
            tool_match = self.state.find_multi_template(self._tool_template, threshold=0.7)
            if not tool_match:
                logger.error(f"PROCESS: {self._tool_name} not found in inventory")
                return StateResult.FAILURE
            cx, cy, _, _ = tool_match
            ax, ay = actions.coord_resolver.to_absolute(cx, cy)
            actions.mouse.click_at(ax, ay, move_style="curved")
            actions.wait("short")

            # Click material in inventory
            mat_match = self.state.find_multi_template(self._material_template, threshold=0.7)
            if not mat_match:
                logger.error(f"PROCESS: {self._material_name} not found in inventory")
                return StateResult.FAILURE
            cx, cy, _, _ = mat_match
            ax, ay = actions.coord_resolver.to_absolute(cx, cy)
            actions.mouse.click_at(ax, ay, move_style="curved")

            # Wait for Make All menu and press Space
            wait_for_menu(self, self._menu_templates)
            actions.press_key("space")

            # Monitor crafting loop
            def on_level_up():
                self._current_level += 1
                logger.info(f"Level-up! Now level {self._current_level}")

            level_ups = monitor_craft_loop(
                self,
                self._tool_template,
                self._material_template,
                self._levelup_templates,
                on_level_up,
            )

            if actions.anti_ban:
                actions.anti_ban.record_action("fletch_cycle")

            self._items_processed += 14
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"PROCESS: Failed - {e}")
            return StateResult.FAILURE

    def _handle_deposit(self, context: StateExecutionContext) -> StateResult:
        self._check_exit_requested()
        self._update_ui("DEPOSIT", f"Depositing {self._product_name}...")

        try:
            actions = self.actions
            if not self._open_bank():
                return StateResult.FAILURE
            self._bank_open = True

            actions.click_template(self._deposit_templates, "deposit inventory", threshold=0.7)

            # Verify deposit
            inv_region = self.state.get_inventory_region()
            for _ in range(2):
                actions.wait("short")
                if not self.state.find_multi_template(self._product_template, threshold=0.8, region=inv_region):
                    break
                actions.click_template(self._deposit_templates, "deposit inventory", threshold=0.7)

            self._cycles += 1
            logger.info(f"DEPOSIT: Cycle {self._cycles} (~{self._items_processed} items total)")
            self._wom_level_check()
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"DEPOSIT: Failed - {e}")
            self._bank_open = False
            self._x_quantity_set = False
            return StateResult.FAILURE
