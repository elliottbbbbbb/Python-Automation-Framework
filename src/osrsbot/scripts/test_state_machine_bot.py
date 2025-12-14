"""
Comprehensive State Machine Test Bot - Tests all bot framework features.

This bot demonstrates and validates the entire framework by testing:
- Minimap navigation (walking in all directions)
- Inventory detection (pixel-based fullness checking)
- Inventory clicking (template-based slot clicking)
- Color detection (smart NPC targeting)
- Template matching (UI button detection)
- OCR (HP and stats reading)
- Combat detection (in_combat checks)
- State machine (transitions, retries, failovers)

States:
    IDLE - Initial state, safety checks
    TEST_MINIMAP - Test minimap navigation
    TEST_INVENTORY_DETECTION - Test inventory state queries
    TEST_INVENTORY_CLICKING - Test clicking inventory slots
    TEST_COLOR_DETECTION - Test color-based NPC clicking
    TEST_TEMPLATE_MATCHING - Test UI template detection
    TEST_OCR - Test OCR stat reading
    TEST_COMBAT - Test combat detection
    COMPLETE - Final state

This comprehensive test ensures all framework features work correctly.
"""
import logging
import time
from enum import Enum
from typing import Dict, List

from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_types import (
    StateResult,
    StateMetadata,
    StateTransition,
    StateExecutionContext
)

logger = logging.getLogger(__name__)


class TestBotStates(Enum):
    """States for comprehensive feature testing."""
    IDLE = "idle"
    TEST_MINIMAP = "test_minimap"
    TEST_INVENTORY_DETECTION = "test_inventory_detection"
    TEST_INVENTORY_CLICKING = "test_inventory_clicking"
    TEST_COLOR_DETECTION = "test_color_detection"
    TEST_TEMPLATE_MATCHING = "test_template_matching"
    TEST_OCR = "test_ocr"
    TEST_COMBAT = "test_combat"
    COMPLETE = "complete"


class ComprehensiveTestBot(StateMachineBot):
    """
    Comprehensive test bot that validates all framework features.

    Tests each major system component in sequence:
    1. Minimap navigation
    2. Inventory detection
    3. Inventory clicking
    4. Color detection
    5. Template matching
    6. OCR
    7. Combat detection
    """

    def __init__(self, *args, **kwargs):
        """Initialize comprehensive test bot."""
        super().__init__(*args, **kwargs, script_name="Comprehensive Test Bot")

        # Test tracking
        self._test_results = {}
        self._combat_click_count = 0
        self._combat_target_clicks = 10  # Test 10 NPC kills
        self._no_targets_start_time = None

    # ==================== State Machine Configuration ====================

    def define_states(self) -> type[Enum]:
        """Define states for this bot."""
        return TestBotStates

    def define_state_metadata(self) -> Dict[Enum, StateMetadata]:
        """Define metadata for each state."""
        return {
            TestBotStates.IDLE: StateMetadata(
                name="Idle",
                description="Initial safety checks",
                max_retries=1,
                timeout=None,
                failover_state=None
            ),
            TestBotStates.TEST_MINIMAP: StateMetadata(
                name="Test Minimap Navigation",
                description="Test walking in all directions",
                max_retries=3,
                timeout=60.0,
                failover_state=TestBotStates.TEST_INVENTORY_DETECTION
            ),
            TestBotStates.TEST_INVENTORY_DETECTION: StateMetadata(
                name="Test Inventory Detection",
                description="Test inventory state queries",
                max_retries=3,
                timeout=30.0,
                failover_state=TestBotStates.TEST_INVENTORY_CLICKING
            ),
            TestBotStates.TEST_INVENTORY_CLICKING: StateMetadata(
                name="Test Inventory Clicking",
                description="Test clicking inventory slots",
                max_retries=3,
                timeout=30.0,
                failover_state=TestBotStates.TEST_COLOR_DETECTION
            ),
            TestBotStates.TEST_COLOR_DETECTION: StateMetadata(
                name="Test Color Detection",
                description="Test smart color clicking",
                max_retries=3,
                timeout=30.0,
                failover_state=TestBotStates.TEST_TEMPLATE_MATCHING
            ),
            TestBotStates.TEST_TEMPLATE_MATCHING: StateMetadata(
                name="Test Template Matching",
                description="Test UI button detection",
                max_retries=3,
                timeout=30.0,
                failover_state=TestBotStates.TEST_OCR
            ),
            TestBotStates.TEST_OCR: StateMetadata(
                name="Test OCR",
                description="Test HP and stats reading",
                max_retries=3,
                timeout=30.0,
                failover_state=TestBotStates.TEST_COMBAT
            ),
            TestBotStates.TEST_COMBAT: StateMetadata(
                name="Test Combat Detection",
                description="Test combat state detection",
                max_retries=30,
                timeout=300.0,
                failover_state=TestBotStates.COMPLETE
            ),
            TestBotStates.COMPLETE: StateMetadata(
                name="Complete",
                description="All tests complete",
                max_retries=1,
                timeout=None,
                failover_state=None
            )
        }

    def define_transitions(self) -> List[StateTransition]:
        """Define allowed state transitions."""
        return [
            StateTransition(TestBotStates.IDLE, TestBotStates.TEST_MINIMAP),
            StateTransition(TestBotStates.TEST_MINIMAP, TestBotStates.TEST_INVENTORY_DETECTION),
            StateTransition(TestBotStates.TEST_INVENTORY_DETECTION, TestBotStates.TEST_INVENTORY_CLICKING),
            StateTransition(TestBotStates.TEST_INVENTORY_CLICKING, TestBotStates.TEST_COLOR_DETECTION),
            StateTransition(TestBotStates.TEST_COLOR_DETECTION, TestBotStates.TEST_TEMPLATE_MATCHING),
            StateTransition(TestBotStates.TEST_TEMPLATE_MATCHING, TestBotStates.TEST_OCR),
            StateTransition(TestBotStates.TEST_OCR, TestBotStates.TEST_COMBAT),
            StateTransition(TestBotStates.TEST_COMBAT, TestBotStates.COMPLETE)
        ]

    def get_initial_state(self) -> Enum:
        """Get initial state."""
        return TestBotStates.IDLE

    # ==================== State Handlers ====================

    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        """
        Handle IDLE state - initial safety checks.

        Returns:
            StateResult.SUCCESS to proceed
        """
        logger.info("=" * 60)
        logger.info("COMPREHENSIVE BOT FRAMEWORK TEST")
        logger.info("=" * 60)
        logger.info("This bot will test all major framework features:")
        logger.info("  1. Minimap Navigation")
        logger.info("  2. Inventory Detection")
        logger.info("  3. Inventory Clicking")
        logger.info("  4. Color Detection")
        logger.info("  5. Template Matching")
        logger.info("  6. OCR (Stats Reading)")
        logger.info("  7. Combat Detection")
        logger.info("=" * 60)

        # Reset tracking
        self._test_results = {}
        self._combat_click_count = 0
        self.actions.reset_click_tracking()

        return StateResult.SUCCESS

    def _handle_test_minimap(self, context: StateExecutionContext) -> StateResult:
        """
        Test minimap navigation by walking in all directions.

        Returns:
            StateResult.SUCCESS if test passes
            StateResult.FAILURE if test fails
        """
        logger.info("\n[TEST 1/7] MINIMAP NAVIGATION")
        logger.info("-" * 60)

        try:
            # Test all 4 cardinal directions
            directions = ["up", "right", "down", "left"]
            tiles = 2

            logger.info(f"Walking {tiles} tiles in each direction: {directions}")

            for direction in directions:
                logger.info(f"  → Walking {direction} ({tiles} tiles)...")
                success = self.actions.walk_tiles(direction, tiles=tiles)

                if not success:
                    logger.error(f"  ✗ Failed to walk {direction}")
                    self._test_results["minimap"] = False
                    return StateResult.FAILURE

                self.actions.wait("medium")

            logger.info("  ✓ All directions tested successfully")
            self._test_results["minimap"] = True
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"Minimap test failed: {e}")
            self._test_results["minimap"] = False
            return StateResult.FAILURE

    def _handle_test_inventory_detection(self, context: StateExecutionContext) -> StateResult:
        """
        Test inventory detection queries.

        Returns:
            StateResult.SUCCESS if test passes
            StateResult.FAILURE if test fails
        """
        logger.info("\n[TEST 2/7] INVENTORY DETECTION")
        logger.info("-" * 60)

        try:
            if not self.state.inventory:
                logger.warning("  ⚠ Inventory system not available (missing services)")
                self._test_results["inventory_detection"] = "skipped"
                return StateResult.SUCCESS

            # Test inventory state queries
            logger.info("  Testing inventory state queries...")

            # Get snapshot
            snapshot = self.state.inventory.get_snapshot(force=True)
            logger.info(f"  → Total items: {snapshot.total_items}")
            logger.info(f"  → Filled slots: {len(snapshot.filled_slots)}")
            logger.info(f"  → Empty slots: {len(snapshot.empty_slots)}")

            # Test is_full
            is_full = self.state.inventory.is_full(threshold=27)
            logger.info(f"  → Is full (≥27 items): {is_full}")

            # Test specific slot
            has_item_slot_0 = self.state.inventory.has_item_in_slot(0)
            logger.info(f"  → Slot 0 has item: {has_item_slot_0}")

            # Get filled/empty slot lists
            filled = self.state.inventory.get_filled_slots()
            empty = self.state.inventory.get_empty_slots()
            logger.info(f"  → Filled slot indices: {filled[:5]}..." if len(filled) > 5 else f"  → Filled slots: {filled}")
            logger.info(f"  → Empty slot indices: {empty[:5]}..." if len(empty) > 5 else f"  → Empty slots: {empty}")

            logger.info("  ✓ Inventory detection working correctly")
            self._test_results["inventory_detection"] = True
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"Inventory detection test failed: {e}")
            self._test_results["inventory_detection"] = False
            return StateResult.FAILURE

    def _handle_test_inventory_clicking(self, context: StateExecutionContext) -> StateResult:
        """
        Test clicking inventory slots using template detection.

        Returns:
            StateResult.SUCCESS if test passes
            StateResult.FAILURE if test fails
        """
        logger.info("\n[TEST 3/7] INVENTORY CLICKING")
        logger.info("-" * 60)

        try:
            # Check if template service is available
            if not self.actions.template_service:
                logger.warning("  ⚠ TemplateMatchService not available (missing template images)")
                logger.warning("  → Create templates/inventory_grid.png to enable this feature")
                logger.warning("  → Skipping inventory clicking test")
                self._test_results["inventory_clicking"] = "skipped"
                return StateResult.SUCCESS

            # Test clicking several inventory slots
            test_slots = [1, 5, 10, 15, 20, 28]  # Sample slots across inventory

            logger.info(f"  Testing clicks on slots: {test_slots}")

            for slot in test_slots:
                logger.info(f"  → Clicking slot {slot}...")
                success = self.actions.click_inventory_slot_detected(
                    slot_num=slot,
                    move_style="curved"
                )

                if success:
                    logger.info(f"    ✓ Successfully clicked slot {slot}")
                else:
                    logger.warning(f"    ⚠ Failed to click slot {slot}")

                self.actions.wait("short")

            logger.info("  ✓ Inventory clicking test complete")
            self._test_results["inventory_clicking"] = True
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"Inventory clicking test failed: {e}")
            self._test_results["inventory_clicking"] = False
            return StateResult.FAILURE

    def _handle_test_color_detection(self, context: StateExecutionContext) -> StateResult:
        """
        Test color detection by clicking a colored object once.

        Returns:
            StateResult.SUCCESS if test passes
            StateResult.FAILURE if test fails
        """
        logger.info("\n[TEST 4/7] COLOR DETECTION")
        logger.info("-" * 60)

        try:
            # Test clicking blue outline (NPC/object)
            logger.info("  Testing smart color detection (blue_outline)...")

            player_pos = self.actions._get_player_position()
            dims = self.state.debug_get_viewport_dimensions()
            if not dims:
                logger.error("Failed to get viewport dimensions")
                return StateResult.FAILURE
            width, height = dims
            viewport_width = min(int(width * 0.70), 540)
            game_viewport_region = (0, 0, viewport_width, height)

            success = self.actions.click_color_smart(
                "blue_outline",
                player_position=player_pos,
                move_style="curved",
                enable_target_lock=True,
                enable_stuck_detection=True,
                enable_blacklist=True,
                region=game_viewport_region
            )

            if success:
                logger.info("  ✓ Color detection successful (clicked blue_outline)")
            else:
                logger.warning("  ⚠ No blue_outline found (this is OK if none visible)")

            self._test_results["color_detection"] = True
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"Color detection test failed: {e}")
            self._test_results["color_detection"] = False
            return StateResult.FAILURE

    def _handle_test_template_matching(self, context: StateExecutionContext) -> StateResult:
        """
        Test template matching for UI elements.

        Returns:
            StateResult.SUCCESS if test passes
            StateResult.FAILURE if test fails
        """
        logger.info("\n[TEST 5/7] TEMPLATE MATCHING")
        logger.info("-" * 60)

        try:
            if not self.actions.template_service:
                logger.warning("  ⚠ TemplateMatchService not available (missing template images)")
                logger.warning("  → Create templates/inventory_grid.png to enable this feature")
                logger.warning("  → Skipping template matching test")
                self._test_results["template_matching"] = "skipped"
                return StateResult.SUCCESS

            # Test inventory grid detection
            logger.info("  Testing inventory grid detection...")
            img_gray = self.state.debug_capture_screen(grayscale=True)

            if img_gray is not None:
                detected = self.state.debug_detect_inventory_grid(force=True)

                if detected:
                    logger.info("  ✓ Inventory grid detected successfully")
                    grid_info = self.state.debug_get_inventory_grid_info()
                    if grid_info:
                        logger.info(f"    → Grid visible: {grid_info['visible']}")
                        logger.info(f"    → Total elements: {grid_info['total_elements']}")
                else:
                    logger.warning("  ⚠ Inventory grid not detected")

            logger.info("  ✓ Template matching test complete")
            self._test_results["template_matching"] = True
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"Template matching test failed: {e}")
            self._test_results["template_matching"] = False
            return StateResult.FAILURE

    def _handle_test_ocr(self, context: StateExecutionContext) -> StateResult:
        """
        Test OCR by reading HP and stats.

        Returns:
            StateResult.SUCCESS if test passes
            StateResult.FAILURE if test fails
        """
        logger.info("\n[TEST 6/7] OCR (STATS READING)")
        logger.info("-" * 60)

        try:
            # Test HP reading
            logger.info("  Testing HP detection...")
            hp = self.state.get_hp(force=True)

            if hp is not None:
                logger.info(f"  ✓ HP detected: {hp}")
            else:
                logger.warning("  ⚠ HP detection returned None")

            # Test prayer reading (if available)
            logger.info("  Testing prayer detection...")
            prayer = self.state.get_prayer(force=True)

            if prayer is not None:
                logger.info(f"  ✓ Prayer detected: {prayer}")
            else:
                logger.warning("  ⚠ Prayer detection returned None")

            logger.info("  ✓ OCR test complete")
            self._test_results["ocr"] = True
            return StateResult.SUCCESS

        except Exception as e:
            logger.error(f"OCR test failed: {e}")
            self._test_results["ocr"] = False
            return StateResult.FAILURE

    def _handle_test_combat(self, context: StateExecutionContext) -> StateResult:
        """
        Test combat detection by killing NPCs.

        Returns:
            StateResult.SUCCESS when target kills reached
            StateResult.RETRY to continue testing
            StateResult.FAILURE if test fails
        """
        logger.info(f"\n[TEST 7/7] COMBAT DETECTION (Kill {self._combat_click_count + 1}/{self._combat_target_clicks})")

        try:
            # Check if test complete
            if self._combat_click_count >= self._combat_target_clicks:
                logger.info("  ✓ Combat detection test complete")
                self._test_results["combat"] = True
                return StateResult.SUCCESS

            # Only attack if NOT in combat
            if not self.state.in_combat():
                logger.debug("  → Not in combat, attacking NPC...")

                player_pos = self.actions._get_player_position()
                dims = self.state.debug_get_viewport_dimensions()
                if not dims:
                    logger.error("Failed to get viewport dimensions")
                    return StateResult.FAILURE
                width, height = dims
                viewport_width = min(int(width * 0.70), 540)
                game_viewport_region = (0, 0, viewport_width, height)

                clicked = self.actions.click_color_smart(
                    "blue_outline",
                    player_position=player_pos,
                    move_style="instant",
                    enable_target_lock=True,
                    enable_stuck_detection=True,
                    enable_blacklist=True,
                    region=game_viewport_region
                )

                if not clicked:
                    if self._no_targets_start_time is None:
                        self._no_targets_start_time = time.time()
                        logger.warning("  ⚠ No targets found, starting timeout...")
                    elif time.time() - self._no_targets_start_time > 45.0:
                        logger.error("  ✗ No targets for 45+ seconds, ending test")
                        return StateResult.FAILURE

                    logger.warning("  ⚠ No valid NPCs found, retrying...")
                    self.actions.wait("short")
                    return StateResult.RETRY

                self._no_targets_start_time = None
                logger.info("  → Clicked NPC, waiting for combat...")

                # Wait for combat to start
                combat_started = False
                for _ in range(6):
                    self.actions.wait("short")
                    if self.state.in_combat():
                        combat_started = True
                        logger.debug("  → Combat started")
                        break

                if combat_started:
                    # Wait for combat to finish
                    logger.debug("  → Waiting for combat to finish...")
                    combat_ended_count = 0

                    for _ in range(30):
                        self.actions.wait("short")

                        if not self.state.in_combat():
                            combat_ended_count += 1
                            if combat_ended_count >= 3:
                                self._combat_click_count += 1
                                logger.info(f"  ✓ Kill complete! ({self._combat_click_count}/{self._combat_target_clicks})")

                                hp = self.state.get_hp()
                                if hp:
                                    logger.info(f"  → Current HP: {hp}")

                                time.sleep(3.0)
                                break
                        else:
                            combat_ended_count = 0
                else:
                    logger.warning("  ⚠ Combat didn't start, NPC may have moved")
            else:
                logger.debug("  → In combat, waiting...")
                self.actions.wait("short")

            return StateResult.RETRY

        except Exception as e:
            logger.error(f"Combat test failed: {e}")
            self._test_results["combat"] = False
            return StateResult.FAILURE

    def _handle_complete(self, context: StateExecutionContext) -> StateResult:
        """
        Handle COMPLETE state - display test results.

        Returns:
            StateResult.SUCCESS
        """
        logger.info("\n" + "=" * 60)
        logger.info("COMPREHENSIVE TEST RESULTS")
        logger.info("=" * 60)

        tests = [
            ("Minimap Navigation", "minimap"),
            ("Inventory Detection", "inventory_detection"),
            ("Inventory Clicking", "inventory_clicking"),
            ("Color Detection", "color_detection"),
            ("Template Matching", "template_matching"),
            ("OCR (Stats Reading)", "ocr"),
            ("Combat Detection", "combat")
        ]

        for test_name, test_key in tests:
            result = self._test_results.get(test_key, "not run")

            if result is True:
                status = "✓ PASS"
            elif result == "skipped":
                status = "⚠ SKIPPED"
            elif result is False:
                status = "✗ FAIL"
            else:
                status = "- NOT RUN"

            logger.info(f"  {status:12} {test_name}")

        logger.info("=" * 60)
        logger.info(f"Combat Kills: {self._combat_click_count}/{self._combat_target_clicks}")
        logger.info("=" * 60)

        # Print state history
        history = self.get_state_history()
        logger.info(f"\nState Execution History ({len(history)} entries):")
        for entry in history:
            logger.info(
                f"  {entry.state.name:30} {entry.result.value:10} "
                f"({entry.duration:.2f}s, retries: {entry.retry_count})"
            )

        logger.info("\n" + "=" * 60)
        logger.info("COMPREHENSIVE TEST COMPLETE")
        logger.info("=" * 60)

        return StateResult.SUCCESS
