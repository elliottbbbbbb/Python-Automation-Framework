"""
Construction Training Bot - Chair Building Strategy

Trains construction by repeatedly building and removing crude wooden/wooden/rocking chairs
in player-owned house using Phials for note exchange in Rimmington.

Prerequisites:
- House set to Rimmington
- Teleport to house scrolls in inventory
- Money (10-100k coins) for exchange fees
- Iron nails (100-1000) in inventory
- Noted planks (100-1000) in inventory
- Hammer in inventory
- Saw in inventory
- Chair hotspot already built in parlour

Strategy:
1. Teleport to house using scroll
2. Exit house portal to Rimmington
3. Exchange noted planks with Phials NPC (press 3 for exchange)
4. Re-enter house portal
5. Build highest level chair available (rocking > wooden > crude)
6. Remove chair and repeat until supplies exhausted

Architecture:
Follows NMZ bot state machine pattern with 11 states, retry logic,
and failover recovery. Uses template matching for items/NPCs/objects,
keyboard input for dialogue interactions, and color detection for
object state changes.
"""

# NOTE: TEMPLATE_REQUIRED - User must create template images before running
# See documentation in plan file for required templates

import logging
import random
import time
from enum import Enum
from typing import Dict, List, Optional, Tuple

import cv2 as cv
import numpy as np

from osrsbot.core.state_helpers import build_metadata_dict
from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_types import (
    StateExecutionContext,
    StateMetadata,
    StateResult,
    StateTransition,
)
from osrsbot.services.keyboard_service import KeyboardService

logger = logging.getLogger(__name__)


class ConstructionStates(Enum):
    """State definitions for Construction Training bot."""

    IDLE = "idle"
    CHECK_SUPPLIES = "check_supplies"
    TELEPORT_TO_HOUSE = "teleport_to_house"
    EXIT_HOUSE = "exit_house"
    FIND_PHIALS = "find_phials"
    EXCHANGE_NOTES = "exchange_notes"
    ENTER_HOUSE = "enter_house"
    FIND_CHAIR_SPACE = "find_chair_space"
    BUILD_CHAIR = "build_chair"
    REMOVE_CHAIR = "remove_chair"
    RECOVERY = "recovery"


class ConstructionTrainingBot(StateMachineBot):
    """
    Construction training bot using state machine framework.

    Implements chair building strategy with Phials note exchange in Rimmington.
    Prioritizes highest level chair available (rocking > wooden > crude wooden).
    """

    def __init__(self, **kwargs):
        """Initialize construction training bot."""
        super().__init__(**kwargs, script_name="Construction Training (Chairs)")

        # Initialize keyboard service for dialogue interactions
        self.keyboard = KeyboardService()

        # Template paths for items
        self._init_item_templates()

        # Template paths for construction objects
        self._init_construction_templates()

        # Configuration constants
        self._init_config_constants()

        # Session tracking variables
        self._chairs_built = 0
        self._cycles_completed = 0
        self._planks_used = 0
        self._exchanges_completed = 0

        # State tracking
        self._last_chair_type = None
        self._needs_more_planks = False  # Used for conditional state transitions
        self._consecutive_recoveries = 0
        self._chair_already_built = False  # Used for conditional FIND_CHAIR_SPACE transitions
        self._is_inside_house = False  # Track if inside house to skip TELEPORT_TO_HOUSE

        logger.info("Construction training bot initialized")
        logger.info("Target: Build highest level chair (rocking > wooden > crude)")

    def _init_item_templates(self):
        """Initialize item template paths."""
        # Items in inventory
        self.TELEPORT_SCROLL_TEMPLATE = "images/bot/items/teleport_to_house.png"
        # Use multi-template for planks (different lighting in different inventory positions)
        # plank.png = upper-left positions, plank_br.png = bottom-right positions
        self.PLANK_TEMPLATES = [
            "images/bot/items/plank.png",
            "images/bot/construction/plank_br.png",
        ]
        self.PLANK_TEMPLATE = self.PLANK_TEMPLATES[0]  # Backward compat
        self.PLANK_NOTED_TEMPLATE = "images/bot/items/plank_noted.png"
        self.IRON_NAILS_TEMPLATE = "images/bot/items/iron_nails.png"
        self.HAMMER_TEMPLATE = "images/bot/items/hammer.png"
        self.SAW_TEMPLATE = "images/bot/items/saw.png"
        self.COINS_TEMPLATE = "images/bot/items/coins.png"

    def _init_construction_templates(self):
        """Initialize construction object template paths."""
        # Portal templates for location detection (multi-template matching)
        # Inside house = thin purple exit portal
        self.HOUSE_PORTAL_TEMPLATES = [
            "images/bot/construction/house_portal.png",
            "images/bot/construction/house_portal_2.png",
        ]

        # Outside house = rocky entrance portal with purple glow
        # Multiple templates for different angles/lighting conditions
        self.OUTSIDE_PORTAL_TEMPLATES = [
            "images/bot/construction/outside_portal.png",
            "images/bot/construction/outside_portal_2.png",
            "images/bot/construction/outside_portal_3.png",
            "images/bot/construction/outside_portal_4.png",
        ]

        # Note: Chair hotspot detection now uses cyan tile markers instead of templates

        # Built chairs (different types) - use lists for multi-template matching
        self.BUILT_CHAIR_CRUDE_TEMPLATES = [
            "images/bot/construction/built_chair_crude.png",
        ]
        self.BUILT_CHAIR_WOODEN_TEMPLATES = [
            "images/bot/construction/built_chair_wooden.png",
        ]
        self.BUILT_CHAIR_ROCKING_TEMPLATES = [
            "images/bot/construction/built_chair_rocking.png",
            "images/bot/construction/built_chair_rocking_2.png",
            "images/bot/construction/built_chair_rocking_3.png",
            "images/bot/construction/built_chair_rocking_4.png",
            "images/bot/construction/built_chair_rocking_5.png",
        ]

        # UI elements
        self.RED_CROSS_TEMPLATE = "images/bot/construction/red_cross.png"
        self.CONSTRUCTION_SKILL_POPUP_TEMPLATE = "images/bot/ui_templates/construction_skill_icon.png"

        # Right-click menu options
        self.BUILD_CHAIR_SPACE_TEMPLATE = "images/bot/construction/build_chair_space.png"
        self.REMOVE_CHAIR_TEMPLATE = "images/bot/construction/remove_chair.png"

        # Chair option templates in construction interface (for clicking the correct chair type)
        self.CHAIR_OPTION_ROCKING_TEMPLATE = "images/bot/construction/chair_option_rocking.png"
        self.CHAIR_OPTION_WOODEN_TEMPLATE = "images/bot/construction/chair_option_wooden.png"
        self.CHAIR_OPTION_CRUDE_TEMPLATE = "images/bot/construction/chair_option_crude.png"

        # Chair option templates when UNAVAILABLE (with red cross overlay)
        # Used to detect when we're out of materials or don't have the level
        self.CHAIR_OPTION_ROCKING_UNAVAILABLE_TEMPLATE = "images/bot/construction/chair_option_rocking_unavailable.png"
        self.CHAIR_OPTION_WOODEN_UNAVAILABLE_TEMPLATE = "images/bot/construction/chair_option_wooden_unavailable.png"
        self.CHAIR_OPTION_CRUDE_UNAVAILABLE_TEMPLATE = "images/bot/construction/chair_option_crude_unavailable.png"

        # Chair type → template mappings (avoids repeating dict literals)
        self.CHAIR_AVAILABLE_TEMPLATE_MAP = {
            "rocking": self.CHAIR_OPTION_ROCKING_TEMPLATE,
            "wooden": self.CHAIR_OPTION_WOODEN_TEMPLATE,
            "crude_wooden": self.CHAIR_OPTION_CRUDE_TEMPLATE,
        }
        self.CHAIR_UNAVAILABLE_TEMPLATE_MAP = {
            "rocking": self.CHAIR_OPTION_ROCKING_UNAVAILABLE_TEMPLATE,
            "wooden": self.CHAIR_OPTION_WOODEN_UNAVAILABLE_TEMPLATE,
            "crude_wooden": self.CHAIR_OPTION_CRUDE_UNAVAILABLE_TEMPLATE,
        }

    def _init_config_constants(self):
        """Initialize configuration constants."""
        # Right-click menu offsets (pixels from click position)
        self.MENU_OFFSET_BUILD_CHAIR_SPACE = 40  # "Build Chair Space" option
        self.MENU_OFFSET_REMOVE_CHAIR = 55  # "Remove" option

        # Minimum plank count before re-exchange
        # Use all planks before restocking (threshold=1 means restock when 0 planks)
        self.MIN_PLANKS_THRESHOLD = 1

        # Chair positions in construction interface (relative coordinates)
        # These are approximate and may need adjustment based on actual interface
        self.CHAIR_POSITIONS = {
            "crude_wooden": (150, 200),  # Leftmost option
            "wooden": (250, 200),        # Middle option
            "rocking": (350, 200),       # Rightmost option
        }

        # Red cross detection regions (relative to chair options)
        # Format: (x_offset, y_offset, width, height) from chair position
        self.RED_CROSS_REGION_OFFSET = (-10, -10, 20, 20)

        # Skill popup region (top-right corner)
        self.SKILL_POPUP_REGION = (450, 50, 60, 60)

        # House portal color detection (more reliable than template matching)
        # Dark purple color of the portal - works for both inside and outside
        self.HOUSE_PORTAL_COLOR = "#34114D"
        self.HOUSE_PORTAL_COLOR_TOLERANCE = 15

        # Cyan tile marker - for walking to/from Phials area
        self.TILE_MARKER_COLOR = "#00FFFF"
        self.TILE_MARKER_TOLERANCE = 15

        # Phials NPC highlight (gold) - for targeting when exchanging planks
        self.PHIALS_COLOR = "#FFD700"
        self.PHIALS_COLOR_TOLERANCE = 30

        # Template matching thresholds
        self.THRESHOLD_PORTAL = 0.4
        self.THRESHOLD_REMOVE_MENU = 0.35
        self.THRESHOLD_GHOSTLY_CHAIR = 0.5
        self.THRESHOLD_CHAIR_OPTION = 0.6
        self.THRESHOLD_MENU_OPTION = 0.7
        self.THRESHOLD_BUILT_CHAIR = 0.75
        self.THRESHOLD_PLANK_ITEM = 0.5

        # Viewport region constants
        self.VIEWPORT_EDGE_THRESHOLD_X = 450
        self.VIEWPORT_EXCLUDE_RIGHT_PX = 100
        self.GHOSTLY_SEARCH_HEIGHT = 400
        self.CHAIR_SEARCH_HEIGHT = 150

    # ==================== STATE MACHINE CONFIGURATION ====================

    def define_states(self) -> type[Enum]:
        """Define state machine states."""
        return ConstructionStates

    def define_transitions(self) -> List[StateTransition]:
        """Define valid state transitions."""
        return [
            # Initial setup
            StateTransition(ConstructionStates.IDLE, ConstructionStates.CHECK_SUPPLIES),

            # Main training loop - full cycle
            StateTransition(ConstructionStates.CHECK_SUPPLIES, ConstructionStates.TELEPORT_TO_HOUSE),
            StateTransition(ConstructionStates.TELEPORT_TO_HOUSE, ConstructionStates.EXIT_HOUSE),
            StateTransition(ConstructionStates.EXIT_HOUSE, ConstructionStates.FIND_PHIALS),
            StateTransition(ConstructionStates.FIND_PHIALS, ConstructionStates.EXCHANGE_NOTES),
            StateTransition(ConstructionStates.EXCHANGE_NOTES, ConstructionStates.ENTER_HOUSE),
            StateTransition(ConstructionStates.ENTER_HOUSE, ConstructionStates.FIND_CHAIR_SPACE),

            # FIND_CHAIR_SPACE transitions - conditional based on whether chair is already built
            # If chair already built - go remove it first
            StateTransition(
                ConstructionStates.FIND_CHAIR_SPACE,
                ConstructionStates.REMOVE_CHAIR,
                condition=lambda: self._chair_already_built
            ),
            # Chair not built - proceed to build
            StateTransition(
                ConstructionStates.FIND_CHAIR_SPACE,
                ConstructionStates.BUILD_CHAIR,
                condition=lambda: not self._chair_already_built
            ),

            # BUILD_CHAIR transitions - conditional based on material availability
            # If material shortage detected (red cross on rocking chair), exit house to get more
            StateTransition(
                ConstructionStates.BUILD_CHAIR,
                ConstructionStates.EXIT_HOUSE,
                condition=lambda: self._needs_more_planks
            ),
            # Normal flow - remove the chair we just built
            StateTransition(
                ConstructionStates.BUILD_CHAIR,
                ConstructionStates.REMOVE_CHAIR,
                condition=lambda: not self._needs_more_planks
            ),

            # Build/remove loop (stay in house until need re-exchange)
            # Use conditional transitions based on plank count
            StateTransition(
                ConstructionStates.REMOVE_CHAIR,
                ConstructionStates.FIND_CHAIR_SPACE,
                condition=lambda: not self._needs_more_planks
            ),
            # When inside house and needs planks, go directly to EXIT_HOUSE
            # (skip CHECK_SUPPLIES and TELEPORT_TO_HOUSE since we're already inside)
            StateTransition(
                ConstructionStates.REMOVE_CHAIR,
                ConstructionStates.EXIT_HOUSE,
                condition=lambda: self._needs_more_planks and self._is_inside_house
            ),
            # When outside and needs planks, go through normal flow
            StateTransition(
                ConstructionStates.REMOVE_CHAIR,
                ConstructionStates.CHECK_SUPPLIES,
                condition=lambda: self._needs_more_planks and not self._is_inside_house
            ),

            # Recovery path
            StateTransition(ConstructionStates.RECOVERY, ConstructionStates.IDLE),
        ]

    def define_state_metadata(self) -> Dict[Enum, StateMetadata]:
        """Define state metadata with retry limits and timeouts."""
        return build_metadata_dict(
            ConstructionStates,
            {
                ConstructionStates.IDLE: {
                    "name": "Idle",
                    "description": "Initial state, verify setup",
                    "max_retries": 2,
                    "timeout": 10.0,
                },
                ConstructionStates.CHECK_SUPPLIES: {
                    "name": "Check Supplies",
                    "description": "Verify inventory has required items",
                    "max_retries": 1,
                    "timeout": 5.0,
                    "failover": ConstructionStates.RECOVERY,
                },
                ConstructionStates.TELEPORT_TO_HOUSE: {
                    "name": "Teleport to House",
                    "description": "Use teleport to house scroll",
                    "max_retries": 3,
                    "timeout": 15.0,
                    "failover": ConstructionStates.RECOVERY,
                },
                ConstructionStates.EXIT_HOUSE: {
                    "name": "Exit House",
                    "description": "Click portal and exit to Rimmington",
                    "max_retries": 3,
                    "timeout": 10.0,
                    "failover": ConstructionStates.RECOVERY,
                },
                ConstructionStates.FIND_PHIALS: {
                    "name": "Find Phials",
                    "description": "Locate and click NPC Phials",
                    "max_retries": 5,
                    "timeout": 15.0,
                    "failover": ConstructionStates.RECOVERY,
                },
                ConstructionStates.EXCHANGE_NOTES: {
                    "name": "Exchange Notes",
                    "description": "Trade noted planks for planks with Phials",
                    "max_retries": 3,
                    "timeout": 20.0,
                    "failover": ConstructionStates.RECOVERY,
                },
                ConstructionStates.ENTER_HOUSE: {
                    "name": "Enter House",
                    "description": "Enter house portal",
                    "max_retries": 3,
                    "timeout": 20.0,
                    "failover": ConstructionStates.RECOVERY,
                },
                ConstructionStates.FIND_CHAIR_SPACE: {
                    "name": "Find Chair Space",
                    "description": "Locate chair build hotspot",
                    "max_retries": 5,
                    "timeout": 10.0,
                    "failover": ConstructionStates.RECOVERY,
                },
                ConstructionStates.BUILD_CHAIR: {
                    "name": "Build Chair",
                    "description": "Select and build highest level chair",
                    "max_retries": 3,
                    "timeout": 15.0,
                    "failover": ConstructionStates.RECOVERY,
                },
                ConstructionStates.REMOVE_CHAIR: {
                    "name": "Remove Chair",
                    "description": "Remove built chair",
                    "max_retries": 3,
                    "timeout": 10.0,
                    "failover": ConstructionStates.FIND_CHAIR_SPACE,
                },
                ConstructionStates.RECOVERY: {
                    "name": "Recovery",
                    "description": "Error recovery state",
                    "max_retries": 2,
                    "timeout": 10.0,
                },
            }
        )

    def get_initial_state(self) -> Enum:
        """Start in IDLE state."""
        return ConstructionStates.IDLE

    # ==================== STATE HANDLERS ====================

    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        """
        IDLE state - Initial validation and setup.

        Logs session start and configuration.

        Transitions:
        - SUCCESS → CHECK_SUPPLIES
        """
        logger.info("[IDLE] Starting construction training session")
        logger.info(f"IDLE: Session stats - Chairs built: {self._chairs_built}, Cycles: {self._cycles_completed}")

        # Log configuration
        logger.debug("IDLE: Chair priority: rocking (lvl 14) > wooden (lvl 8) > crude wooden (lvl 1)")
        logger.debug(f"IDLE: Min plank threshold: {self.MIN_PLANKS_THRESHOLD}")

        return StateResult.SUCCESS

    def _handle_check_supplies(self, context: StateExecutionContext) -> StateResult:
        """
        CHECK_SUPPLIES state - Verify inventory has required items.

        Critical checks:
        - Teleport to house scrolls
        - Noted planks (for Phials exchange)
        - Iron nails
        - Coins (for exchange fee)
        - Hammer and saw

        Transitions:
        - SUCCESS if all items present → TELEPORT_TO_HOUSE
        - FAILURE if missing critical items → END SCRIPT
        """
        logger.info("[CHECK_SUPPLIES] Verifying inventory items...")

        # Ensure inventory tab is open before template matching
        self.actions.ensure_inventory_open()

        # Debug: save inventory region for visual verification
        self._debug_save_inventory_region()

        # Check for teleport scroll
        has_teleport = self._has_item(self.TELEPORT_SCROLL_TEMPLATE, "teleport to house scroll")
        if not has_teleport:
            logger.error("CHECK_SUPPLIES: ERROR - Out of teleport to house scrolls")
            self._log_session_stats()
            raise RuntimeError("ERROR: Out of teleport to house scrolls")

        # Check for noted planks
        has_noted_planks = self._has_item(self.PLANK_NOTED_TEMPLATE, "noted planks")
        plank_count = self._count_item_slots(self.PLANK_TEMPLATE)

        if not has_noted_planks and plank_count < self.MIN_PLANKS_THRESHOLD:
            logger.error("CHECK_SUPPLIES: ERROR - Out of planks and noted planks")
            self._log_session_stats()
            raise RuntimeError("ERROR: Out of planks and noted planks")

        # Check for iron nails
        has_nails = self._has_item(self.IRON_NAILS_TEMPLATE, "iron nails")
        if not has_nails:
            logger.error("CHECK_SUPPLIES: ERROR - Out of iron nails")
            self._log_session_stats()
            raise RuntimeError("ERROR: Out of iron nails")

        # Check for coins
        has_coins = self._has_item(self.COINS_TEMPLATE, "coins")
        if not has_coins:
            logger.error("CHECK_SUPPLIES: ERROR - Out of coins for exchange")
            self._log_session_stats()
            raise RuntimeError("ERROR: Out of coins for exchange")

        # Check for tools
        has_hammer = self._has_item(self.HAMMER_TEMPLATE, "hammer")
        # Use lower threshold for saw (template quality issue - matches at ~0.34)
        saw_result = self._find_template_in_inventory(self.SAW_TEMPLATE, threshold=0.3)
        has_saw = saw_result is not None

        if not has_hammer or not has_saw:
            missing_tools = []
            if not has_hammer:
                missing_tools.append("hammer")
            if not has_saw:
                missing_tools.append("saw")
            error_msg = f"ERROR: Missing tools - {', '.join(missing_tools)}"
            logger.error(f"CHECK_SUPPLIES: {error_msg}")
            self._log_session_stats()
            raise RuntimeError(error_msg)

        # All items present
        logger.info("CHECK_SUPPLIES: All required items present")
        logger.info(f"CHECK_SUPPLIES: Current plank count: {plank_count}")

        return StateResult.SUCCESS

    def _handle_teleport_to_house(self, context: StateExecutionContext) -> StateResult:
        """
        TELEPORT_TO_HOUSE state - Use teleport to house scroll.

        Clicks teleport scroll in inventory and waits for teleport animation.
        Uses dual template detection to determine location:
        - Inside portal (thin) = we're inside house, skip teleport
        - Outside portal (rocky) = we're in Rimmington, need to teleport

        IMPORTANT: Check INSIDE portal first here because if we're inside,
        we should skip teleporting. Different from ENTER_HOUSE logic.

        Transitions:
        - SUCCESS → EXIT_HOUSE
        - FAILURE if scroll not found → RETRY
        """
        logger.info("[TELEPORT_TO_HOUSE] Checking current location...")

        # Priority 1: Check for INSIDE portal template (thin purple beam)
        # If we see the thin exit portal, we're already inside
        inside_portal = self.state.find_multi_template(
            self.HOUSE_PORTAL_TEMPLATES,
            threshold=0.5
        )

        if inside_portal:
            center_x, center_y, confidence, template_name = inside_portal
            logger.info(
                f"TELEPORT_TO_HOUSE: Inside portal detected (matched '{template_name}' "
                f"at ({center_x}, {center_y}), confidence={confidence:.2f})"
            )
            logger.info("TELEPORT_TO_HOUSE: Already inside house, skipping teleport")
            return StateResult.SUCCESS

        # Priority 2: Check for OUTSIDE portal template (rocky entrance)
        outside_portal = self.state.find_multi_template(
            self.OUTSIDE_PORTAL_TEMPLATES,
            threshold=0.4  # Low threshold - rocky portal varies
        )

        if outside_portal:
            center_x, center_y, confidence, template_name = outside_portal
            logger.info(
                f"TELEPORT_TO_HOUSE: Outside portal detected (matched '{template_name}' "
                f"at ({center_x}, {center_y}), confidence={confidence:.2f})"
            )
            logger.info("TELEPORT_TO_HOUSE: In Rimmington, need to teleport to house")
        else:
            # No portal template matched - location unknown, teleport to be safe
            logger.info("TELEPORT_TO_HOUSE: No portal detected, teleporting to house")

        # Find and click teleport scroll (restricted to inventory region)
        # Try template matching first, fall back to slot 1 after retries
        teleport_clicked = self._click_template_in_inventory(
            self.TELEPORT_SCROLL_TEMPLATE,
            "teleport to house scroll",
            threshold=0.7  # Higher threshold to avoid mismatches with similar scrolls
        )

        if not teleport_clicked:
            # Fallback: click inventory slot 1 (where teleport scroll should be)
            logger.warning("TELEPORT_TO_HOUSE: Template not found, using slot 1 fallback")
            if not self._click_inventory_slot(0):  # Slot 0 = first slot
                logger.warning("TELEPORT_TO_HOUSE: Slot 1 fallback also failed")
                return StateResult.FAILURE

        logger.info("TELEPORT_TO_HOUSE: Teleport scroll clicked, waiting for animation...")

        # Wait for teleport animation (long delay)
        self.actions.wait("long")
        self.actions.wait("medium")  # Extra time to ensure loaded

        logger.info("TELEPORT_TO_HOUSE: Teleport complete")

        return StateResult.SUCCESS

    def _handle_exit_house(self, context: StateExecutionContext) -> StateResult:
        """
        EXIT_HOUSE state - Exit house portal to Rimmington.

        Uses template matching to find the portal (more reliable than color detection).
        Falls back to color detection (#34114D) if template matching fails.
        Inside house portal only requires a single left click to exit.

        Transitions:
        - SUCCESS → FIND_PHIALS
        - FAILURE if portal not found → RETRY
        """
        logger.info("[EXIT_HOUSE] Exiting house to Rimmington...")

        # Clear stored chair location when leaving house
        # Get viewport region to exclude minimap/UI
        viewport_region = self.state.get_game_viewport_region()

        # Retry finding and clicking portal up to 3 times
        def find_and_click_portal():
            # Try template matching first (more reliable than color detection)
            inside_portal = self.state.find_multi_template(
                self.HOUSE_PORTAL_TEMPLATES,
                threshold=0.4
            )

            if inside_portal:
                center_x, center_y, confidence, template_name = inside_portal
                logger.info(f"EXIT_HOUSE: Portal found via template '{template_name}' at ({center_x}, {center_y}), confidence={confidence:.2f}")
            else:
                # Fallback to color detection if template matching fails
                portal_center = self._find_color_center(
                    self.HOUSE_PORTAL_COLOR,
                    tolerance=self.HOUSE_PORTAL_COLOR_TOLERANCE,
                    region=viewport_region
                )
                if not portal_center:
                    logger.warning("EXIT_HOUSE: Portal not found via template or color")
                    return None

                center_x, center_y = portal_center
                logger.info(f"EXIT_HOUSE: Portal found via color at ({center_x}, {center_y})")

            abs_x, abs_y = self.actions.coord_resolver.to_absolute(center_x, center_y)
            self.actions.mouse.click_at(abs_x, abs_y, move_style="curved")
            return True

        if not self._retry_action(find_and_click_portal, max_retries=2, action_name="EXIT_HOUSE portal click"):
            logger.warning("EXIT_HOUSE: Failed to find/click portal after retries")
            return StateResult.FAILURE

        logger.info("EXIT_HOUSE: Portal clicked, waiting for transition...")

        # Wait for loading screen (no dialogue inside house)
        self.actions.wait("long")
        self.actions.wait("medium")

        # Verify we actually exited
        location = self._verify_location()
        if location == "outside":
            logger.info("EXIT_HOUSE: Confirmed OUTSIDE, now in Rimmington")
            self._is_inside_house = False
            return StateResult.SUCCESS
        elif location == "inside":
            logger.error("EXIT_HOUSE: Still INSIDE house! Will retry.")
            return StateResult.FAILURE
        else:
            logger.warning("EXIT_HOUSE: Could not verify location - assuming failure")
            return StateResult.FAILURE

    def _handle_find_phials(self, context: StateExecutionContext) -> StateResult:
        """
        FIND_PHIALS state - Walk to Phials area by clicking cyan tile marker.

        Steps:
        1. Click cyan tile marker (#00FFFF) to walk closer to Phials
        2. Wait for player to arrive

        Transitions:
        - SUCCESS → EXCHANGE_NOTES
        - FAILURE if tile not found → RETRY
        """
        logger.info("[FIND_PHIALS] Walking toward Phials...")

        # Verify we're actually outside
        location = self._verify_location()
        if location == "inside":
            logger.error("FIND_PHIALS: ERROR - Still inside house! Cannot find Phials.")
            return StateResult.FAILURE
        logger.info(f"FIND_PHIALS: Location verified ({location})")

        # Get viewport region to exclude minimap/UI
        viewport_region = self.state.get_game_viewport_region()

        # Step 1: Click cyan tile center to walk closer (restricted to game viewport)
        tile_center = self._find_color_center(
            self.TILE_MARKER_COLOR,
            tolerance=self.TILE_MARKER_TOLERANCE,
            region=viewport_region
        )

        if not tile_center:
            logger.warning("FIND_PHIALS: Cyan tile marker not found")
            return StateResult.FAILURE

        center_x, center_y = tile_center
        logger.info(f"FIND_PHIALS: Tile marker center at ({center_x}, {center_y})")

        # Convert to absolute coordinates and click
        abs_x, abs_y = self.actions.coord_resolver.to_absolute(center_x, center_y)
        self.actions.mouse.click_at(abs_x, abs_y, move_style="curved")

        # Wait for player to walk to tile
        logger.info("FIND_PHIALS: Walking to tile, waiting...")
        self.actions.wait("long")
        self.actions.wait("long")  # Extra wait for walking

        logger.info("FIND_PHIALS: Arrived near Phials")
        return StateResult.SUCCESS

    def _handle_exchange_notes(self, context: StateExecutionContext) -> StateResult:
        """
        EXCHANGE_NOTES state - Exchange noted planks with Phials.

        Sequence:
        1. Click noted planks in inventory
        2. Move cursor to Phials NPC (triggers "Use item on" dialogue automatically)
        3. Press "3" key for exchange all option

        Transitions:
        - SUCCESS → ENTER_HOUSE
        - FAILURE if exchange fails → RETRY
        """
        logger.info("[EXCHANGE_NOTES] Exchanging noted planks with Phials...")

        # Verify we're actually outside
        location = self._verify_location()
        if location == "inside":
            logger.error("EXCHANGE_NOTES: ERROR - Still inside house! Cannot find Phials.")
            return StateResult.FAILURE
        logger.info(f"EXCHANGE_NOTES: Location verified ({location})")

        # Outer retry loop for entire exchange (in case Phials moves)
        for exchange_attempt in range(3):
            if exchange_attempt > 0:
                logger.info(f"EXCHANGE_NOTES: Retry attempt {exchange_attempt + 1}/3")

            # Step 1: Click noted planks
            if not self.actions.click_template(
                self.PLANK_NOTED_TEMPLATE,
                "noted planks",
                threshold=0.7
            ):
                logger.error("EXCHANGE_NOTES: No noted planks found in inventory")
                return StateResult.FAILURE

            logger.info("EXCHANGE_NOTES: Clicked noted planks in inventory")
            self.actions.wait("medium")

            viewport_region = self.state.get_game_viewport_region()

            # Step 2: Find and click Phials (with retry)
            def find_and_click_phials():
                phials_center = self._find_color_center(
                    self.PHIALS_COLOR,
                    tolerance=self.PHIALS_COLOR_TOLERANCE,
                    region=viewport_region
                )
                if not phials_center:
                    return None

                center_x, center_y = phials_center
                logger.info(f"EXCHANGE_NOTES: Phials center at ({center_x}, {center_y})")

                abs_x, abs_y = self.actions.coord_resolver.to_absolute(center_x, center_y)
                self.actions.mouse.click_at(abs_x, abs_y, move_style="curved")
                return True

            if not self._retry_action(find_and_click_phials, max_retries=2, action_name="EXCHANGE_NOTES Phials click"):
                logger.warning("EXCHANGE_NOTES: Failed to find/click Phials")
                continue  # Try whole exchange again

            logger.info("EXCHANGE_NOTES: Clicked on Phials, waiting for dialogue...")
            self.actions.wait("long")

            # Step 3: Press "3" for exchange
            logger.info("EXCHANGE_NOTES: Pressing '3' for exchange all")
            self.keyboard.press("3", mode="humanized")
            self.actions.wait("medium")

            # Step 4: Verify exchange
            logger.info("EXCHANGE_NOTES: Verifying exchange...")
            if self.state.find_template(self.PLANK_TEMPLATE, threshold=0.7):
                logger.info("EXCHANGE_NOTES: Exchange verified - unnoted planks found")
                self._exchanges_completed += 1
                self._consecutive_recoveries = 0
                return StateResult.SUCCESS

            logger.warning("EXCHANGE_NOTES: Exchange not verified, will retry...")

        logger.error("EXCHANGE_NOTES: Failed after 3 attempts")
        return StateResult.FAILURE

    def _handle_enter_house(self, context: StateExecutionContext) -> StateResult:
        """
        ENTER_HOUSE state - Walk back and re-enter player house in building mode.

        Uses dual template detection to determine location:
        - Outside portal (rocky) templates = we're outside Rimmington, need to enter
        - Inside portal (thin) templates = we're inside house, skip entering

        IMPORTANT: Check OUTSIDE portal FIRST because if we're outside and fail to
        detect it, we might false-positive on inside portal and skip entering.

        Steps:
        1. Check for outside portal template (rocky) - if found, click to enter
        2. Check for inside portal template (thin) - if found, already inside
        3. Neither found - walk to cyan tile and retry (no color fallback!)

        Transitions:
        - SUCCESS → FIND_CHAIR_SPACE
        - FAILURE if portal not found → RETRY
        """
        logger.info("[ENTER_HOUSE] Checking portal location...")

        # Clear stored chair location when entering house
        viewport_region = self.state.get_game_viewport_region()

        # Priority 1: Check for OUTSIDE portal template (rocky entrance)
        # Check this FIRST - if we're outside, entering is critical
        outside_portal = self.state.find_multi_template(
            self.OUTSIDE_PORTAL_TEMPLATES,
            threshold=0.4  # Low threshold - rocky portal varies a lot
        )

        if outside_portal:
            # We're OUTSIDE - check if portal is within clickable zone
            center_x, center_y, confidence, template_name = outside_portal
            logger.info(
                f"ENTER_HOUSE: Outside portal detected (matched '{template_name}' "
                f"at ({center_x}, {center_y}), confidence={confidence:.2f})"
            )

            # Check if portal is within clickable zone (not at screen edges)
            # If portal is at edge, clicking is unreliable - walk closer first
            MIN_X, MAX_X = 100, 450  # Reasonable center region
            MIN_Y, MAX_Y = 50, 400

            if center_x < MIN_X or center_x > MAX_X or center_y < MIN_Y or center_y > MAX_Y:
                logger.info(f"ENTER_HOUSE: Portal at edge ({center_x}, {center_y}), walking closer first...")

                # Walk to cyan tile to get closer
                tile_center = self._find_color_center(
                    self.TILE_MARKER_COLOR,
                    tolerance=self.TILE_MARKER_TOLERANCE,
                    region=viewport_region
                )

                if tile_center:
                    tile_x, tile_y = tile_center
                    logger.info(f"ENTER_HOUSE: Walking to cyan tile at ({tile_x}, {tile_y})")
                    abs_x, abs_y = self.actions.coord_resolver.to_absolute(tile_x, tile_y)
                    self.actions.mouse.click_at(abs_x, abs_y, move_style="curved")
                    self.actions.wait("long")
                    self.actions.wait("long")
                    return StateResult.FAILURE  # Retry after walking closer
                else:
                    logger.warning("ENTER_HOUSE: No cyan tile found to walk closer")

            # Portal is in clickable zone - click it
            logger.info("ENTER_HOUSE: We are OUTSIDE - clicking portal to enter")
            abs_x, abs_y = self.actions.coord_resolver.to_absolute(center_x, center_y)
            self.actions.mouse.click_at(abs_x, abs_y, move_style="curved")

            logger.info("ENTER_HOUSE: Portal clicked, waiting for dialogue...")
            self.actions.wait("long")

            logger.info("ENTER_HOUSE: Pressing '2' for building mode")
            self.keyboard.press("2", mode="humanized")

            self.actions.wait("long")
            self.actions.wait("medium")

            logger.info("ENTER_HOUSE: Entered house (building mode)")
            self._is_inside_house = True  # Track that we're inside
            return StateResult.SUCCESS

        # Priority 2: Check for INSIDE portal template (thin purple beam)
        inside_portal = self.state.find_multi_template(
            self.HOUSE_PORTAL_TEMPLATES,
            threshold=0.5  # Thin portal is more consistent
        )

        if inside_portal:
            center_x, center_y, confidence, template_name = inside_portal
            logger.info(
                f"ENTER_HOUSE: Inside portal detected (matched '{template_name}' "
                f"at ({center_x}, {center_y}), confidence={confidence:.2f})"
            )
            logger.info("ENTER_HOUSE: Already inside house, skipping")
            self._is_inside_house = True  # Track that we're inside
            return StateResult.SUCCESS

        # Priority 3: Neither portal template matched
        # DO NOT use color fallback - it can't distinguish inside vs outside!
        logger.warning("ENTER_HOUSE: No portal template matched - location uncertain")

        # Walk to cyan tile to get closer and retry
        tile_center = self._find_color_center(
            self.TILE_MARKER_COLOR,
            tolerance=self.TILE_MARKER_TOLERANCE,
            region=viewport_region
        )

        if tile_center:
            center_x, center_y = tile_center
            logger.info(f"ENTER_HOUSE: Walking to cyan tile at ({center_x}, {center_y}) to get closer...")
            abs_x, abs_y = self.actions.coord_resolver.to_absolute(center_x, center_y)
            self.actions.mouse.click_at(abs_x, abs_y, move_style="curved")

            logger.info("ENTER_HOUSE: Walking to tile...")
            self.actions.wait("long")
            self.actions.wait("long")

            return StateResult.FAILURE  # Retry to re-check for portal

        logger.warning("ENTER_HOUSE: No portal or tile found - retry")
        return StateResult.FAILURE

    def _handle_find_chair_space(self, context: StateExecutionContext) -> StateResult:
        """
        FIND_CHAIR_SPACE state - Locate chair build hotspot.

        Right-clicks chair hotspot and selects "Build Chair Space" option via template.

        Transitions:
        - SUCCESS → BUILD_CHAIR
        - FAILURE if hotspot not found → RETRY
        """
        logger.info("[FIND_CHAIR_SPACE] Locating chair build hotspot (cyan tile)...")

        # Always detect fresh - stored location doesn't work due to character movement
        # during build/remove animations (screen coordinates become stale)
        viewport_region = self.state.get_game_viewport_region()

        # FIRST: Check if chair is already BUILT
        # If chair is built, we need to remove it before we can build a new one
        # Use HIGH threshold (0.75) to avoid false positives on UI elements at viewport edges
        # Restrict to center portion of viewport (exclude rightmost 100px where UI may bleed in)
        SINGLE_CHAIR_TEMPLATE = "images/bot/construction/built_chair_rocking_5.png"

        # Restrict search region to avoid false positives at viewport edges
        center_region = (
            viewport_region[0],
            viewport_region[1],
            viewport_region[2] - self.VIEWPORT_EXCLUDE_RIGHT_PX,
            viewport_region[3]
        )

        built_check = self.state.find_template(
            SINGLE_CHAIR_TEMPLATE,
            threshold=0.75,  # Raised from 0.5 to avoid false positives
            region=center_region
        )

        if built_check:
            center_x, center_y, confidence = built_check
            # Additional sanity check: chair should NOT be at far right edge (UI area)
            if center_x > self.VIEWPORT_EDGE_THRESHOLD_X:
                logger.warning(f"FIND_CHAIR_SPACE: Ignoring edge detection at x={center_x} (likely UI false positive)")
                built_check = None  # Treat as not found
            else:
                logger.info(f"FIND_CHAIR_SPACE: Chair ALREADY BUILT at ({center_x}, {center_y}), conf={confidence:.2f}")
                logger.info("FIND_CHAIR_SPACE: Need to remove before building new - setting flag")
                # Set flag to trigger REMOVE_CHAIR instead of BUILD_CHAIR
                self._chair_already_built = True
                return StateResult.SUCCESS  # Will transition to REMOVE_CHAIR via condition

        # Chair not built - proceed with normal build flow
        self._chair_already_built = False

        # Search upper viewport only - excludes false positives below Y~500

        ghostly_search_region = (
            viewport_region[0],
            viewport_region[1],
            viewport_region[2] - self.VIEWPORT_EXCLUDE_RIGHT_PX,
            self.GHOSTLY_SEARCH_HEIGHT
        )

        # Try ghostly chair hotspot (matches at ~0.57 confidence)
        ghostly_check = self.state.find_template(
            SINGLE_CHAIR_TEMPLATE,
            threshold=0.5,  # Lower threshold to detect ghostly hotspot at ~0.57
            region=ghostly_search_region
        )

        if ghostly_check:
            center_x, center_y, confidence = ghostly_check
            if center_x <= self.VIEWPORT_EDGE_THRESHOLD_X:  # Not at UI edge
                logger.info(f"FIND_CHAIR_SPACE: Ghostly chair hotspot at ({center_x}, {center_y}), conf={confidence:.2f}")
                # Use template position directly for click (skip cyan tile detection)
                abs_x, abs_y = self.actions.coord_resolver.to_absolute(center_x, center_y)
                self.actions.mouse.click_at(abs_x, abs_y, button="right", move_style="curved")

                # Wait for menu to appear
                self.actions.wait("short")

                # Find and click "Build Chair Space" option
                if not self._find_and_click_build_menu():
                    logger.warning("FIND_CHAIR_SPACE: 'Build Chair Space' menu option not found (via ghostly template)")
                    return StateResult.FAILURE

                logger.info("FIND_CHAIR_SPACE: Build Chair Space option selected (via ghostly template)")

                # Wait for construction interface to open
                self.actions.wait("long")
                self.actions.wait("short")

                return StateResult.SUCCESS
            else:
                logger.warning(f"FIND_CHAIR_SPACE: Ignoring ghostly edge detection at x={center_x}")

        # FALLBACK: Cyan tile detection (if template matching fails)
        upper_region = (
            viewport_region[0],
            viewport_region[1],
            viewport_region[2],
            self.CHAIR_SEARCH_HEIGHT
        )

        tile_center = self._find_color_cluster_center(
            self.TILE_MARKER_COLOR,
            tolerance=self.TILE_MARKER_TOLERANCE,
            region=upper_region  # Restricted to upper viewport
        )

        if not tile_center:
            logger.warning("FIND_CHAIR_SPACE: Cyan tile marker not found in upper viewport (fallback)")
            return StateResult.FAILURE

        center_x, center_y = tile_center
        logger.info(f"FIND_CHAIR_SPACE: Chair hotspot tile at ({center_x}, {center_y}) (via cyan tile fallback)")

        # Step 2: Right-click on chair hotspot
        abs_x, abs_y = self.actions.coord_resolver.to_absolute(center_x, center_y)
        self.actions.mouse.click_at(abs_x, abs_y, button="right", move_style="curved")

        # Wait for menu to appear
        self.actions.wait("short")

        # Step 3: Find and click "Build Chair Space" option
        if not self._find_and_click_build_menu():
            logger.warning("FIND_CHAIR_SPACE: 'Build Chair Space' menu option not found")
            return StateResult.FAILURE

        logger.info("FIND_CHAIR_SPACE: Build Chair Space option selected")

        # Wait for construction interface to open (needs longer than "medium")
        self.actions.wait("long")
        self.actions.wait("short")  # Extra buffer for interface animation

        return StateResult.SUCCESS

    def _handle_build_chair(self, context: StateExecutionContext) -> StateResult:
        """
        BUILD_CHAIR state - Select and build highest level chair available.

        Uses combined detection approach:
        1. PRIMARY: Try to find AVAILABLE rocking chair template
        2. If found: Click it (we have materials)
        3. If not found: Check if menu is open (crude chair visible)
        4. If menu open but rocking not found: Use region-based red cross detection
        5. If red cross confirmed in rocking region: Exit to get more materials

        Transitions:
        - SUCCESS → REMOVE_CHAIR (normal flow)
        - SUCCESS → EXIT_HOUSE (if material shortage detected, via conditional transition)
        - FAILURE if build fails → RETRY or CHECK_SUPPLIES
        """
        logger.info("[BUILD_CHAIR] Building chair...")

        # PRIMARY: Try to find AVAILABLE rocking chair template
        available_result = self.state.find_template(
            self.CHAIR_OPTION_ROCKING_TEMPLATE,
            threshold=0.6
        )

        if available_result:
            # Rocking chair IS available - we have materials
            chair_type = "rocking"  # Set chair_type for later use
            center_x, center_y, confidence = available_result
            logger.info(f"BUILD_CHAIR: Rocking chair AVAILABLE at ({center_x}, {center_y}), conf={confidence:.2f}")
            self._needs_more_planks = False

            # Click to build the rocking chair
            abs_x, abs_y = self.actions.coord_resolver.to_absolute(center_x, center_y)
            self.actions.mouse.click_at(abs_x, abs_y, move_style="curved")
            logger.info("BUILD_CHAIR: Chair option clicked, waiting for build animation...")
        else:
            # Rocking chair template NOT found - check if menu is even open
            logger.debug("BUILD_CHAIR: Rocking chair template not found, checking if menu is open...")

            menu_open = self.state.find_template(
                self.CHAIR_OPTION_CRUDE_TEMPLATE,  # Crude should always be visible if menu is open
                threshold=0.5
            )

            if menu_open:
                # Menu IS open but rocking chair not found
                # This could mean: materials shortage OR template matching failed
                # Use region-based red cross detection as confirmation
                logger.info("BUILD_CHAIR: Menu is open (crude chair visible), checking rocking chair region...")

                if self._has_red_cross_at_chair("rocking", use_region=True):
                    # Confirmed: rocking chair has red cross in its specific region
                    logger.warning("BUILD_CHAIR: Rocking chair UNAVAILABLE (confirmed by region check)")
                    self._needs_more_planks = True
                    self.keyboard.escape()
                    self.actions.wait("short")
                    # Return SUCCESS so state machine transitions to EXIT_HOUSE
                    return StateResult.SUCCESS
                else:
                    # Red cross not found in rocking region - template matching might have failed
                    # Fall back to position-based click for rocking chair
                    chair_type = "rocking"  # Set chair_type for later use
                    logger.warning("BUILD_CHAIR: Rocking template not found, using position fallback")

                    # Calculate rocking chair position relative to crude chair
                    crude_x, crude_y, _ = menu_open
                    # Rocking chair is 2 rows below crude (each row ~45px)
                    rocking_x = crude_x
                    rocking_y = crude_y + 90  # 2 rows * 45px

                    abs_x, abs_y = self.actions.coord_resolver.to_absolute(rocking_x, rocking_y)
                    self.actions.mouse.click_at(abs_x, abs_y, move_style="curved")
                    logger.info(f"BUILD_CHAIR: Clicked rocking position at ({rocking_x}, {rocking_y})")
                    self._needs_more_planks = False
            else:
                # Menu not open - something went wrong
                logger.error("BUILD_CHAIR: Construction menu not detected (crude chair not visible)")
                return StateResult.FAILURE

        logger.info("BUILD_CHAIR: Chair option clicked, waiting for build animation...")

        # Wait for build animation to complete by polling for built chair templates
        # Building can take 1-5 seconds due to in-game failure mechanics
        chair_templates = self._get_built_chair_templates(chair_type)

        if not self._wait_for_built_chair(chair_templates, timeout=6.0):
            logger.warning("BUILD_CHAIR: Chair not detected after timeout, continuing anyway")
            # Continue anyway - chair might have been built but template didn't match
        else:
            logger.info("BUILD_CHAIR: Built chair detected")

        logger.info(f"BUILD_CHAIR: {chair_type.replace('_', ' ').title()} built successfully")

        self._chairs_built += 1
        self._planks_used += 1  # Each chair uses 1 plank
        self._last_chair_type = chair_type
        self._consecutive_recoveries = 0

        return StateResult.SUCCESS

    def _handle_remove_chair(self, context: StateExecutionContext) -> StateResult:
        """
        REMOVE_CHAIR state - Remove built chair.

        Sequence:
        1. Find built chair (template matching or color detection)
        2. Right-click chair
        3. Select "Remove" option
        4. Wait for dialogue "Really remove it?"
        5. Press "1" repeatedly to confirm
        6. Check if need to re-exchange planks

        Transitions:
        - SUCCESS if planks low → CHECK_SUPPLIES
        - SUCCESS if planks OK → FIND_CHAIR_SPACE (loop)
        - FAILURE → RETRY
        """
        logger.info("[REMOVE_CHAIR] Removing chair...")

        # Get viewport region to exclude minimap/UI
        viewport_region = self.state.get_game_viewport_region()

        # Find built chair using template matching (more accurate than cyan tile)
        # Use SINGLE template for testing (user's request to simplify debugging)
        SINGLE_CHAIR_TEMPLATE = "images/bot/construction/built_chair_rocking_5.png"

        chair_result = self.state.find_template(
            SINGLE_CHAIR_TEMPLATE,
            threshold=0.5,
            region=viewport_region
        )

        if not chair_result:
            # Fallback to cyan tile detection if template not found
            logger.warning("REMOVE_CHAIR: Chair template not found, trying cyan tile")
            tile_center = self._find_color_center(
                self.TILE_MARKER_COLOR,
                tolerance=self.TILE_MARKER_TOLERANCE,
                region=viewport_region
            )
            if not tile_center:
                logger.warning("REMOVE_CHAIR: Cyan tile marker not found either")
                return StateResult.FAILURE
            center_x, center_y = tile_center
            # Keep Y offset for tile-based detection
            center_y = center_y + 15
        else:
            center_x, center_y, confidence = chair_result
            logger.info(f"REMOVE_CHAIR: Chair found via template at ({center_x}, {center_y}), conf={confidence:.2f}")
            # NO Y offset needed - template center IS the chair center

        logger.info(f"REMOVE_CHAIR: Chair location at ({center_x}, {center_y})")

        # Right-click on chair
        abs_x, abs_y = self.actions.coord_resolver.to_absolute(center_x, center_y)
        self.actions.mouse.click_at(abs_x, abs_y, button="right", move_style="curved")

        # Wait for menu to appear
        self.actions.wait("short")

        # Find "Remove" option using template matching
        # CRITICAL: Restrict search to area near the right-click menu
        # Without this, template can match "Remove" text elsewhere on screen (e.g., chat area)
        # Menus appear centered on click X, extending below click Y
        menu_search_region = (
            max(0, center_x - 100),      # x: allow for menu width (menu centers on click)
            max(0, center_y - 30),       # y: slightly above click (for menu title)
            200,                          # width: typical menu width
            180                           # height: enough for menu options
        )

        # Lower threshold (0.35) because template only matches at ~0.389 due to lighting variations
        remove_result = self.state.find_template(
            self.REMOVE_CHAIR_TEMPLATE,
            threshold=0.35,
            region=menu_search_region  # Restrict to menu area only
        )

        if remove_result:
            menu_x, menu_y, _ = remove_result
            logger.info(f"REMOVE_CHAIR: 'Remove' option found at ({menu_x}, {menu_y})")
            abs_menu_x, abs_menu_y = self.actions.coord_resolver.to_absolute(menu_x, menu_y)
            self.actions.mouse.click_at(abs_menu_x, abs_menu_y, move_style="fast")
        else:
            # Fallback to menu offset if template not found
            logger.warning("REMOVE_CHAIR: 'Remove' template not found, using offset")
            menu_y = abs_y + self.MENU_OFFSET_REMOVE_CHAIR
            self.actions.mouse.click_at(abs_x, menu_y, move_style="fast")

        logger.info("REMOVE_CHAIR: Remove option selected, waiting for character to walk...")

        # Wait for character to walk to chair and dialogue to appear
        # Character needs 1-2 seconds to walk before "Really remove it?" dialogue shows
        self.actions.wait("long")   # ~2 seconds for walking
        self.actions.wait("short")  # Extra buffer for dialogue to appear

        # Press "1" repeatedly to confirm removal (dialogue: "Really remove it?")
        logger.info("REMOVE_CHAIR: Pressing '1' to confirm removal")
        for i in range(3):
            self.keyboard.press("1", mode="instant")
            time.sleep(0.1)

        # Wait for removal animation
        self.actions.wait("medium")
        self.actions.wait("short")  # Extra buffer for animation to complete

        # VERIFY: Check if built chair is still visible
        # If removal succeeded, the built chair should NOT be detectable
        # Use the last built chair type to get the right templates
        chair_type = self._last_chair_type if self._last_chair_type else "rocking"
        built_chair_templates = self._get_built_chair_templates(chair_type)

        # Restrict verification to viewport region to avoid false positives in UI/inventory
        viewport_region = self.state.get_game_viewport_region()
        verification_result = self.state.find_multi_template(
            built_chair_templates,
            threshold=0.7,  # Raised from 0.5 - ghostly hotspot matches at ~0.57, real chair at ~0.96
            region=viewport_region  # Restrict search to game viewport only
        )

        if verification_result:
            # Chair is still there - removal may have failed
            center_x, center_y, confidence, template_name = verification_result
            logger.warning(
                f"REMOVE_CHAIR: Chair still visible at ({center_x}, {center_y}), "
                f"conf={confidence:.2f}, template='{template_name}' - removal may have failed"
            )
            # Return FAILURE to retry the removal
            return StateResult.FAILURE

        logger.info("REMOVE_CHAIR: Chair removed (verified - not visible)")

        self._cycles_completed += 1

        # Check if need to re-exchange planks
        current_planks = self._count_item_slots(self.PLANK_TEMPLATE)

        logger.info(f"REMOVE_CHAIR: Current planks: {current_planks}")

        if current_planks < self.MIN_PLANKS_THRESHOLD:
            logger.info("REMOVE_CHAIR: Low on planks, will re-exchange at Phials")
            self._needs_more_planks = True  # Conditional transition will go to CHECK_SUPPLIES
        else:
            logger.info("REMOVE_CHAIR: Sufficient planks, continuing build loop")
            self._needs_more_planks = False  # Conditional transition will go to FIND_CHAIR_SPACE

        # Clear stored chair location since character has moved during removal animation
        # Next FIND_CHAIR_SPACE will re-detect the cyan tile fresh

        # No extra wait here - state already takes ~8-9s, near the 10s timeout limit

        return StateResult.SUCCESS

    def _handle_recovery(self, context: StateExecutionContext) -> StateResult:
        """
        RECOVERY state - Attempt to recover from errors.

        Actions:
        - Close any open interfaces (press ESC)
        - Wait for screen to settle
        - Log recovery attempt

        Transitions:
        - SUCCESS → IDLE
        """
        logger.warning("[RECOVERY] Attempting error recovery...")

        self._consecutive_recoveries += 1
        if self._consecutive_recoveries >= 3:
            logger.error("RECOVERY: 3 consecutive recoveries without progress — stopping bot")
            self._log_session_stats()
            raise RuntimeError("Too many consecutive recoveries — stopping bot")

        # Close interfaces
        self.keyboard.escape()
        self.actions.wait("short")

        # Press ESC again to be sure
        self.keyboard.escape()
        self.actions.wait("medium")

        logger.info(f"RECOVERY: Interfaces closed, returning to IDLE (recovery #{self._consecutive_recoveries})")

        return StateResult.SUCCESS

    # ==================== HELPER METHODS ====================

    # --- Item Detection ---

    def _has_item(self, template_path: str, item_name: str) -> bool:
        """
        Check if item exists in inventory using template matching (read-only).

        Follows NMZ pattern (_click_item_or_fail at line 128) for clean error handling.

        Args:
            template_path: Path to item template
            item_name: Name for logging

        Returns:
            True if item found, False otherwise
        """
        # Try using inventory detection service if available
        if hasattr(self.state, 'inventory') and self.state.inventory:
            # Extract item name from path for inventory service
            # e.g., "plank.png" -> "plank"
            item_key = template_path.split("/")[-1].replace(".png", "")

            try:
                if self.state.inventory.has_item(item_key):
                    logger.debug(f"Item '{item_name}' found via inventory detection")
                    return True
            except Exception:
                pass  # Fall through to template matching

        # Fallback: template matching restricted to inventory region
        result = self._find_template_in_inventory(template_path, threshold=0.6)
        if result is not None:
            logger.debug(f"Item '{item_name}' found via template matching in inventory")
            return True

        return False

    def _find_item_slot(self, template_path: str) -> Optional[int]:
        """
        Find first inventory slot containing item.r

        Args:
            template_path: Path to item template

        Returns:
            Slot number (1-28) if found, None otherwise
        """
        # Try inventory detection service
        if hasattr(self.state, 'inventory') and self.state.inventory:
            item_key = template_path.split("/")[-1].replace(".png", "")

            try:
                slots = self.state.inventory.find_item(item_key)
                if slots:
                    # Convert 0-indexed to 1-indexed
                    return slots[0] + 1
            except Exception as e:
                logger.debug(f"Inventory detection failed: {e}")

        # Fallback: return None (template matching more complex for slot finding)
        logger.debug("Could not find item slot")
        return None

    def _count_item_slots(self, template_path: str) -> int:
        """
        Count number of inventory slots containing item.

        Args:
            template_path: Path to item template

        Returns:
            Number of slots (0-28), or estimated count based on template presence
        """
        # Try inventory detection service
        if hasattr(self.state, 'inventory') and self.state.inventory:
            item_key = template_path.split("/")[-1].replace(".png", "")

            try:
                slots = self.state.inventory.find_item(item_key)
                if slots:
                    return len(slots)
            except Exception as e:
                logger.debug(f"Inventory detection failed: {e}")

        # Fallback: Use template matching to check if item is present
        # This doesn't count exact slots, but confirms presence
        inventory_region = self.state.get_inventory_region()

        if inventory_region:
            # Use multi-template matching for planks (different lighting positions)
            # Different inventory positions have different lighting - need multiple templates
            if "plank" in template_path.lower() and hasattr(self, 'PLANK_TEMPLATES'):
                result = self.state.find_multi_template(
                    self.PLANK_TEMPLATES,
                    threshold=0.5,
                    region=inventory_region
                )
                if result:
                    _, _, confidence, matched_template = result
                    logger.info(f"_count_item_slots: Plank found via multi-template (matched '{matched_template}', conf={confidence:.2f})")
                    return 20  # Assume plenty of items if template is visible
            else:
                # Single-template matching for other items
                result = self.state.find_template(
                    template_path,
                    threshold=0.5,
                    region=inventory_region
                )
                if result:
                    logger.info(f"_count_item_slots: Item found via template matching fallback")
                    return 20

        # No item found
        return 0

    # --- Inventory Template Matching Helpers ---

    def _find_template_in_inventory(
        self,
        template_path: str,
        threshold: float = 0.5  # Lowered from 0.7 for debugging
    ) -> Optional[Tuple[int, int, float]]:
        """
        Find a template only within the inventory region.

        Uses the screen service's get_inventory_region() to restrict search
        to inventory area, avoiding false positives from game world objects.

        Args:
            template_path: Path to template image
            threshold: Match confidence threshold

        Returns:
            (center_x, center_y, confidence) in screen coordinates, or None
        """
        # Get inventory region from screen service
        inventory_region = self.state.get_inventory_region()

        if inventory_region:
            logger.info(
                f"Inventory region: x={inventory_region[0]}, y={inventory_region[1]}, "
                f"w={inventory_region[2]}, h={inventory_region[3]}"
            )
            result = self.state.find_template(
                template_path,
                threshold=threshold,
                region=inventory_region
            )
            if result:
                logger.debug(f"Found template at ({result[0]}, {result[1]}) with confidence {result[2]:.2f}")
            else:
                logger.debug(f"Template not found in inventory region (threshold={threshold})")
            return result

        # Fallback: full screen search (should not happen in normal operation)
        logger.warning("Could not get inventory region, searching full screen")
        return self.state.find_template(template_path, threshold=threshold)

    def _debug_save_inventory_region(self):
        """Save inventory region as debug image for visual verification."""
        try:
            from pathlib import Path

            inventory_region = self.state.get_inventory_region()
            if not inventory_region:
                logger.warning("Could not get inventory region for debug")
                return

            # Capture inventory region
            screenshot = self.actions.screen.capture(region=inventory_region)
            if screenshot:
                img_np = cv.cvtColor(np.array(screenshot), cv.COLOR_RGB2BGR)
                debug_path = Path("debug_inventory_region.png")
                cv.imwrite(str(debug_path), img_np)
                logger.info(f"DEBUG: Saved inventory region screenshot: {debug_path.absolute()}")
        except Exception as e:
            logger.warning(f"Failed to save debug inventory image: {e}")

    def _click_template_in_inventory(
        self,
        template_path: str,
        item_name: str,
        threshold: float = 0.7
    ) -> bool:
        """
        Find and click a template only within the inventory region.

        Args:
            template_path: Path to template image
            item_name: Name for logging
            threshold: Match confidence threshold

        Returns:
            True if clicked successfully, False otherwise
        """
        result = self._find_template_in_inventory(template_path, threshold)

        if not result:
            logger.warning(f"{item_name} not found in inventory")
            return False

        center_x, center_y, confidence = result
        logger.debug(f"Found {item_name} at ({center_x}, {center_y}) with confidence {confidence:.2f}")

        abs_x, abs_y = self.actions.coord_resolver.to_absolute(center_x, center_y)
        return self.actions.mouse.click_at(abs_x, abs_y, move_style="curved")

    def _click_inventory_slot(self, slot_index: int) -> bool:
        """
        Click a specific inventory slot by index (0-27).

        Slot layout (4 columns x 7 rows):
        0  1  2  3
        4  5  6  7
        ...
        24 25 26 27

        Args:
            slot_index: 0-27 inventory slot index

        Returns:
            True if clicked successfully
        """
        if slot_index < 0 or slot_index > 27:
            logger.warning(f"Invalid slot index: {slot_index}")
            return False

        # Get inventory region
        inventory_region = self.state.get_inventory_region()
        if not inventory_region:
            logger.warning("Could not get inventory region for slot click")
            return False

        inv_x, inv_y, inv_w, inv_h = inventory_region

        # Border offsets: the inventory region includes padding around the actual item grid
        # These values account for the panel border/decoration
        BORDER_OFFSET_X = 17  # Pixels of padding on left (and right)
        BORDER_OFFSET_Y = 9   # Pixels of padding on top (and bottom)

        # Calculate actual grid dimensions (excluding borders)
        grid_x = inv_x + BORDER_OFFSET_X
        grid_y = inv_y + BORDER_OFFSET_Y
        grid_w = inv_w - (2 * BORDER_OFFSET_X)
        grid_h = inv_h - (2 * BORDER_OFFSET_Y)

        # Calculate slot dimensions (4 cols x 7 rows)
        slot_width = grid_w / 4
        slot_height = grid_h / 7

        # Calculate row and column
        col = slot_index % 4
        row = slot_index // 4

        # Calculate center of slot (using grid coordinates, not raw region)
        center_x = grid_x + (col * slot_width) + (slot_width / 2)
        center_y = grid_y + (row * slot_height) + (slot_height / 2)

        logger.info(f"Clicking inventory slot {slot_index} at ({center_x:.0f}, {center_y:.0f})")

        abs_x, abs_y = self.actions.coord_resolver.to_absolute(int(center_x), int(center_y))
        return self.actions.mouse.click_at(abs_x, abs_y, move_style="curved")

    # --- Menu Detection Helpers ---

    def _find_and_click_build_menu(self) -> bool:
        """Find 'Build Chair Space' menu option and click it.

        Returns:
            True if found and clicked, False otherwise
        """
        def find_menu_option():
            return self.state.find_template(
                self.BUILD_CHAIR_SPACE_TEMPLATE,
                threshold=self.THRESHOLD_MENU_OPTION
            )

        menu_result = self._retry_action(find_menu_option, max_retries=2, action_name="build chair space menu")
        if not menu_result:
            return False

        menu_x, menu_y, _ = menu_result
        logger.info(f"FIND_CHAIR_SPACE: Build option at ({menu_x}, {menu_y})")
        abs_menu_x, abs_menu_y = self.actions.coord_resolver.to_absolute(menu_x, menu_y)
        self.actions.mouse.click_at(abs_menu_x, abs_menu_y, move_style="curved")
        return True

    # --- Location Detection Helpers ---

    def _verify_location(self) -> str:
        """Determine player location by comparing portal template confidences.

        Returns:
            "inside", "outside", or "unknown"
        """
        outside_portal = self.state.find_multi_template(
            self.OUTSIDE_PORTAL_TEMPLATES,
            threshold=self.THRESHOLD_PORTAL
        )
        inside_portal = self.state.find_multi_template(
            self.HOUSE_PORTAL_TEMPLATES,
            threshold=self.THRESHOLD_PORTAL
        )

        outside_conf = outside_portal[2] if outside_portal else 0.0
        inside_conf = inside_portal[2] if inside_portal else 0.0

        logger.info(f"Location check: outside={outside_conf:.2f}, inside={inside_conf:.2f}")

        if outside_conf > inside_conf and outside_conf >= self.THRESHOLD_PORTAL:
            return "outside"
        elif inside_conf > outside_conf and inside_conf >= self.THRESHOLD_PORTAL:
            return "inside"
        elif outside_conf >= self.THRESHOLD_PORTAL:
            return "outside"
        return "unknown"

    # --- Color Detection Helpers ---

    def _find_color_center(
        self,
        hex_color: str,
        tolerance: int,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[Tuple[int, int]]:
        """
        Find center point of all pixels matching a color.

        Unlike find_color() which returns the first pixel, this finds ALL
        matching pixels and returns their centroid for more accurate clicking.

        Args:
            hex_color: Target color as hex string (e.g., "#FFD700")
            tolerance: Color matching tolerance
            region: Optional search region (x, y, width, height)

        Returns:
            (x, y) center coordinates, or None if no matches
        """
        matches = self.actions.screen.find_color(
            hex_color,
            tolerance=tolerance,
            region=region,
            find_all=True  # Get ALL matching pixels
        )

        if not matches:
            return None

        # Calculate centroid of all matching pixels
        total_x = sum(m.x for m in matches)
        total_y = sum(m.y for m in matches)
        center_x = total_x // len(matches)
        center_y = total_y // len(matches)

        return (center_x, center_y)

    def _find_color_cluster_center(
        self,
        hex_color: str,
        tolerance: int,
        region: Optional[Tuple[int, int, int, int]] = None,
        cell_size: int = 40
    ) -> Optional[Tuple[int, int]]:
        """
        Find centroid of the largest cluster of matching pixels.

        Unlike _find_color_center which averages ALL matching pixels,
        this groups pixels into spatial clusters and returns the centroid
        of the largest one. Prevents the click from being pulled off-target
        by secondary tile markers or stray color matches.

        Args:
            hex_color: Target color as hex string (e.g., "#00FFFF")
            tolerance: Color matching tolerance
            region: Optional search region (x, y, width, height)
            cell_size: Grid cell size in pixels for clustering

        Returns:
            (x, y) center coordinates of largest cluster, or None if no matches
        """
        matches = self.actions.screen.find_color(
            hex_color,
            tolerance=tolerance,
            region=region,
            find_all=True
        )

        if not matches:
            return None

        # Grid-based clustering: assign each pixel to a cell
        cells: dict = {}  # (cell_x, cell_y) -> list of (x, y)
        for m in matches:
            key = (m.x // cell_size, m.y // cell_size)
            cells.setdefault(key, []).append((m.x, m.y))

        # Flood fill to merge adjacent cells into clusters
        visited: set = set()
        clusters: list = []
        for key in cells:
            if key in visited:
                continue
            cluster_pixels: list = []
            stack = [key]
            while stack:
                k = stack.pop()
                if k in visited or k not in cells:
                    continue
                visited.add(k)
                cluster_pixels.extend(cells[k])
                cx, cy = k
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    stack.append((cx + dx, cy + dy))
            clusters.append(cluster_pixels)

        # Pick largest cluster
        largest = max(clusters, key=len)
        center_x = sum(x for x, y in largest) // len(largest)
        center_y = sum(y for x, y in largest) // len(largest)

        logger.info(
            f"Color cluster: {len(clusters)} cluster(s), "
            f"largest has {len(largest)} pixels, center=({center_x}, {center_y})"
        )

        return (center_x, center_y)

    # --- Retry Helper ---

    def _retry_action(
        self,
        action_func,
        max_retries: int = 2,
        action_name: str = "action"
    ):
        """
        Retry a single action multiple times before giving up.

        Args:
            action_func: Callable that returns truthy value on success, None/False on failure
            max_retries: Number of additional attempts after first failure
            action_name: Name for logging

        Returns:
            Result of action_func on success, None on all failures
        """
        for attempt in range(max_retries + 1):
            result = action_func()
            if result:
                if attempt > 0:
                    logger.info(f"{action_name}: Succeeded on attempt {attempt + 1}")
                return result

            if attempt < max_retries:
                logger.warning(f"{action_name}: Failed, retrying ({attempt + 1}/{max_retries + 1})...")
                self.actions.wait("short")

        logger.warning(f"{action_name}: Failed after {max_retries + 1} attempts")
        return None

    # --- Right-Click Menu Helpers ---

    def _right_click_and_select_option(
        self,
        template_path: str,
        object_name: str,
        menu_offset: int
    ) -> bool:
        """
        Right-click object and select menu option.

        Args:
            template_path: Path to object template
            object_name: Name for logging
            menu_offset: Y-offset in pixels for menu option

        Returns:
            True if successful, False otherwise
        """
        try:
            # Find object using template matching
            # Access bank_queries through actions.bank
            result = self.state.find_template(
                template_path,
                threshold=0.7
            )

            if not result:
                logger.debug(f"Could not find {object_name} for right-click")
                return False

            center_x, center_y, confidence = result

            # Convert to absolute coordinates
            abs_x, abs_y = self.actions.coord_resolver.to_absolute(center_x, center_y)

            # Right-click
            logger.debug(f"Right-clicking {object_name} at ({abs_x}, {abs_y})")

            success = self.actions.mouse.click_at(
                abs_x,
                abs_y,
                button="right",
                move_style="curved"
            )

            if not success:
                logger.warning(f"Failed to right-click {object_name}")
                return False

            # Wait for menu to appear
            self.actions.wait("short")

            # Click menu option (offset downward)
            menu_x = abs_x
            menu_y = abs_y + menu_offset

            logger.debug(f"Clicking menu option at offset {menu_offset}px")

            success = self.actions.mouse.click_at(
                menu_x,
                menu_y,
                button="left",
                move_style="linear"  # Fast click for menu
            )

            if success:
                logger.debug(f"Menu option selected for {object_name}")
                self.actions.wait("short")
                return True
            else:
                logger.warning(f"Failed to click menu option for {object_name}")
                return False

        except Exception as e:
            logger.error(f"Right-click failed for {object_name}: {e}")
            return False

    # --- Chair Selection Logic ---

    def _get_highest_available_chair(self) -> str:
        """
        Determine highest level chair player can build.

        Checks for red cross icons on each chair option.
        Priority: rocking (lvl 14) > wooden (lvl 8) > crude wooden (lvl 1)

        Returns:
            "rocking", "wooden", or "crude_wooden"
        """
        # Check rocking chair (highest level - level 14)
        if not self._has_red_cross_at_chair("rocking"):
            logger.debug("Rocking chair available (level 14)")
            return "rocking"

        # Check wooden chair (level 8)
        if not self._has_red_cross_at_chair("wooden"):
            logger.debug("Wooden chair available (level 8)")
            return "wooden"

        # Default: crude wooden chair (always available at level 1)
        logger.debug("Crude wooden chair available (level 1)")
        return "crude_wooden"

    def _has_red_cross_at_chair(self, chair_type: str, use_region: bool = False) -> bool:
        """
        Check if chair option has red cross (unavailable) using template matching.

        Args:
            chair_type: "rocking", "wooden", or "crude_wooden"
            use_region: If True, restrict search to the specific chair's region
                (anchored off crude chair position) to avoid false positives
                from other chairs with red crosses.

        Returns:
            True if red cross present (unavailable), False if available
        """
        template_path = self.CHAIR_UNAVAILABLE_TEMPLATE_MAP.get(chair_type)
        if not template_path:
            logger.warning(f"Unknown chair type: {chair_type}")
            return False

        region = None
        if use_region:
            # Find crude chair as anchor, then calculate target region
            crude_result = self.state.find_template(
                self.CHAIR_OPTION_CRUDE_TEMPLATE,
                threshold=0.5
            )
            if not crude_result:
                logger.debug("Red cross region check: Crude chair not found, cannot anchor")
                return False

            crude_x, crude_y, _ = crude_result
            # Menu layout (each row ~45px): crude=0, wooden=45, rocking=90
            CHAIR_Y_OFFSETS = {"crude_wooden": 0, "wooden": 45, "rocking": 90}
            y_offset = CHAIR_Y_OFFSETS.get(chair_type, 0)
            region = (
                int(crude_x - 50),
                int(crude_y + y_offset - 20),
                100,
                60
            )
            logger.debug(f"Red cross region check: {chair_type} in region {region}")

        result = self.state.find_template(
            template_path, threshold=self.THRESHOLD_CHAIR_OPTION, region=region
        )

        if result:
            logger.info(f"BUILD_CHAIR: {chair_type} UNAVAILABLE (confidence={result[2]:.2f})")
            return True

        logger.debug(f"No red cross detected on {chair_type} - available")
        return False

    def _click_chair_option(self, chair_type: str) -> bool:
        """
        Click chair option in construction interface using template matching.

        Args:
            chair_type: "rocking", "wooden", or "crude_wooden"

        Returns:
            True if clicked successfully
        """
        if chair_type not in self.CHAIR_AVAILABLE_TEMPLATE_MAP:
            logger.error(f"Unknown chair type: {chair_type}")
            return False

        template_path = self.CHAIR_AVAILABLE_TEMPLATE_MAP[chair_type]

        # Find chair option using template matching
        result = self.state.find_template(
            template_path,
            threshold=0.6
        )

        if not result:
            logger.warning(f"BUILD_CHAIR: Could not find {chair_type} option template")
            # Fall back to hardcoded position as last resort
            if chair_type in self.CHAIR_POSITIONS:
                rel_x, rel_y = self.CHAIR_POSITIONS[chair_type]
                logger.info(f"BUILD_CHAIR: Using fallback position ({rel_x}, {rel_y})")
                abs_x, abs_y = self.actions.coord_resolver.to_absolute(rel_x, rel_y)
            else:
                return False
        else:
            center_x, center_y, confidence = result
            logger.info(f"BUILD_CHAIR: Found {chair_type} option at ({center_x}, {center_y}), confidence={confidence:.2f}")
            abs_x, abs_y = self.actions.coord_resolver.to_absolute(center_x, center_y)

        # Click the chair option
        success = self.actions.mouse.click_at(
            abs_x,
            abs_y,
            move_style="curved"
        )

        if success:
            logger.debug(f"{chair_type} option clicked")
        else:
            logger.warning(f"Failed to click {chair_type} option")

        return success

    def _get_built_chair_templates(self, chair_type: Optional[str]) -> List[str]:
        """
        Get template paths for built chair based on type.

        Args:
            chair_type: "rocking", "wooden", or "crude_wooden"

        Returns:
            List of template paths for multi-template matching
        """
        if chair_type == "rocking":
            return self.BUILT_CHAIR_ROCKING_TEMPLATES
        elif chair_type == "wooden":
            return self.BUILT_CHAIR_WOODEN_TEMPLATES
        else:
            return self.BUILT_CHAIR_CRUDE_TEMPLATES

    def _wait_for_built_chair(self, template_paths: List[str], timeout: float = 6.0) -> bool:
        """
        Wait for built chair to appear by polling multi-template matching.

        Building animation takes 2-6 seconds due to in-game mechanics.

        Args:
            template_paths: List of paths to built chair templates
            timeout: Maximum time to wait in seconds

        Returns:
            True if chair detected, False if timeout
        """
        viewport_region = self.state.get_game_viewport_region()

        # Wait for construction menu to close before polling
        # Build animation starts after menu closes and takes 2-6 seconds
        # Without this wait, we get false positives from the menu icons
        MINIMUM_WAIT = 2.0  # Seconds to wait before first poll
        time.sleep(MINIMUM_WAIT)

        start_time = time.time()
        poll_interval = 0.3  # Check every 300ms

        while time.time() - start_time < timeout:
            # Check for built chair using multi-template matching
            result = self.state.find_multi_template(
                template_paths,
                threshold=0.5  # Lower threshold for multi-template
            )

            if result:
                x, y, confidence, template_name = result
                # Verify it's in the viewport region (not UI elements)
                if viewport_region:
                    vp_x, vp_y, vp_w, vp_h = viewport_region
                    if vp_x <= x <= vp_x + vp_w and vp_y <= y <= vp_y + vp_h:
                        logger.debug(f"Built chair found ('{template_name}') at ({x}, {y}) with confidence {confidence:.2f}")
                        return True
                else:
                    return True

            time.sleep(poll_interval)

        return False

    # --- Skill Popup Detection ---

    def _wait_for_skill_popup(self, timeout: float = 5.0) -> bool:
        """
        Wait for construction skill popup to appear (hammer & saw icon).

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if popup detected, False if timeout
        """
        # Check for construction skill icon color in top-right region
        skill_icon_color = self.config.get("colors", "construction_skill_icon")

        if not skill_icon_color:
            logger.debug("Construction skill icon color not configured")
            return False

        try:
            match = self.actions.screen.wait_for_color(
                skill_icon_color,
                timeout=timeout,
                region=self.SKILL_POPUP_REGION
            )

            if match:
                logger.debug("Construction skill popup detected")
                return True
            else:
                logger.debug("Skill popup not detected within timeout")
                return False
        except Exception as e:
            logger.debug(f"Skill popup detection failed: {e}")
            return False

    # --- Session Statistics ---

    def _log_session_stats(self):
        """Log session statistics."""
        logger.info("=" * 50)
        logger.info("CONSTRUCTION TRAINING SESSION STATS")
        logger.info("=" * 50)
        logger.info(f"Chairs Built: {self._chairs_built}")
        logger.info(f"Cycles Completed: {self._cycles_completed}")
        logger.info(f"Planks Used: {self._planks_used}")
        logger.info(f"Exchanges with Phials: {self._exchanges_completed}")
        if self._last_chair_type:
            logger.info(f"Last Chair Type: {self._last_chair_type.replace('_', ' ').title()}")
        logger.info("=" * 50)
