"""
Sand Crabs Combat Bot - AFK Beach Training

Finds dormant sand crab shells via template matching, walks over them to aggro
multiple crabs, then walks to a RuneLite tile marker AFK spot and auto-retaliates.

Strategy:
1. Template match dormant sand crab shells on the beach
2. Walk over each shell to trigger spawn (repeat until 2-3 crabs aggro'd)
3. Detect aggro via RuneLite NPC highlight color appearing on screen
4. Walk to AFK tile marker spot
5. Auto-retaliate until all crabs die
6. Repeat

Setup Requirements:
1. RuneLite tile marker placed at your AFK spot
2. RuneLite NPC Indicators: sand crabs highlighted with configured color
3. Sand crab shell template images in src/osrsbot/images/bot/combat/sand_crabs/
4. config.json colors: sand_crab_afk_marker, sand_crab_npc_highlight
"""

import logging
import random
import time
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from osrsbot.core.state_helpers import build_metadata_dict
from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_types import (
    StateExecutionContext,
    StateMetadata,
    StateResult,
    StateTransition,
)

logger = logging.getLogger(__name__)


class SandCrabStates(Enum):
    """States for sand crabs combat bot."""

    IDLE = "idle"
    NAVIGATE_TO_CRABS = "navigate_to_crabs"
    FIND_CRABS = "find_crabs"
    WALK_TO_CRAB = "walk_to_crab"
    CHECK_AGGRO = "check_aggro"
    AGGRO_MORE_CRABS = "aggro_more_crabs"
    WALK_TO_AFK_SPOT = "walk_to_afk_spot"
    HUNT_ACTIVE_CRABS = "hunt_active_crabs"
    COMBAT_LOOP = "combat_loop"
    RESET_AGGRO = "reset_aggro"
    RECOVERY = "recovery"


class SandCrabsCombatBot(StateMachineBot):
    """
    Sand crabs AFK combat bot.

    Uses template matching to find dormant sand crab shells, walks over them
    to trigger aggro on multiple crabs, then AFK fights at a tile marker spot.
    """

    # Default template image directory
    TEMPLATE_DIR = "src/osrsbot/images/bot/combat/sand_crabs"

    def __init__(self, **kwargs):
        super().__init__(
            **kwargs,
            script_name="Sand Crabs Combat",
            enable_exit_key=True,
            enable_status_ui=True,
        )

        # Load shell template paths from the images directory
        self.shell_templates = self._discover_shell_templates()


        # Config color names
        self.afk_marker_color = "sand_crab_afk_marker"
        self.npc_highlight_color = "sand_crab_npc_highlight"

        # How many crabs to aggro before walking to AFK spot
        self.target_aggro_count = 3

        # Combat grace period: seconds to wait after combat ends before finding new crabs
        self.combat_grace_period = 8.0

        # How long to wait for aggro after walking to a shell
        self.aggro_wait_timeout = 4.0

        # Last detected crab location (relative coords from template match)
        self._last_crab_x: int = 0
        self._last_crab_y: int = 0

        # Current aggro count for this cycle
        self._current_aggro_count: int = 0

        # Flag: True when enough crabs aggro'd and ready to fight at AFK spot
        # Used by WALK_TO_AFK_SPOT conditional transitions
        self._ready_for_combat: bool = False

        # Track visited shell locations to avoid re-matching the same shell
        self._visited_shells: List[Tuple[int, int]] = []

        # Aggro reset detection (10-min anti-farming mechanic)
        self._consecutive_no_combat_cycles: int = 0
        self._needs_aggro_reset: bool = False
        self.no_combat_cycle_threshold = 2  # Trigger reset after N consecutive no-combat cycles

        # Hunt active crabs phase
        self._hunt_complete: bool = False
        self._hunt_found_crabs: bool = False
        self._max_hunt_iterations: int = 5
        self._hunt_click_timeout: float = 4.0

        # Track consecutive failed hunts to detect anti-AFK timer expiry
        self._consecutive_failed_hunts: int = 0

        # Startup navigation
        self._at_crab_area: bool = False

        # Path waypoint colors (3-color system: pink far, green near, cyan destination)
        self.path_pink_color = "sand_crab_path_pink"
        self.path_green_color = "sand_crab_path_green"

        # Waypoint templates (ordered path: 1→6, then AFK destination)
        self.waypoint_templates = self._discover_waypoint_templates()

        # Stats
        self._combat_cycles = 0
        self._crabs_found = 0
        self._aggro_resets = 0
        self._cycle_start_time: Optional[float] = None
        self._combat_start_time: Optional[float] = None

        logger.info(
            f"SandCrabsCombatBot initialized: "
            f"{len(self.shell_templates)} shell templates, "
            f"target_aggro={self.target_aggro_count}, "
            f"afk_marker={self.afk_marker_color}, "
            f"npc_highlight={self.npc_highlight_color}"
        )

    def _discover_shell_templates(self) -> List[str]:
        """
        Find all sand crab shell template images in the template directory.

        Returns:
            List of template paths (relative from project root)
        """
        template_dir = Path(self.TEMPLATE_DIR)
        templates = []

        if template_dir.exists():
            for img_file in sorted(template_dir.glob("sand_crab_burrowed_*.png")):
                templates.append(str(img_file))
            logger.info(f"Found {len(templates)} shell templates in {template_dir}")
        else:
            logger.warning(
                f"Shell template directory not found: {template_dir}. "
                f"Create it and add sand crab shell screenshots."
            )

        if not templates:
            logger.warning(
                "No shell templates found! The bot cannot detect dormant crabs. "
                f"Add .png screenshots of sand crab shells to: {self.TEMPLATE_DIR}/"
            )

        return templates

    def _discover_waypoint_templates(self) -> List[List[str]]:
        """
        Load ordered waypoint template paths for navigation.

        Each waypoint can have multiple template variants (e.g. pathway_6.png
        and pathway_6_2.png) for better matching across different camera angles.

        Returns:
            List of waypoint entries, each a list of template variant paths.
            Walk order: pathway_1..6, then cyan_afk_tile.
        """
        template_dir = Path(self.TEMPLATE_DIR)
        waypoints = []

        # Ordered pathway templates (with optional variants like pathway_6_2.png)
        for i in range(1, 7):
            variants = []
            primary = template_dir / f"pathway_{i}.png"
            if primary.exists():
                variants.append(str(primary))
            # Additional variants (pathway_6_2.png, etc.)
            for variant_file in sorted(template_dir.glob(f"pathway_{i}_*.png")):
                variants.append(str(variant_file))
            if variants:
                waypoints.append(variants)
            else:
                logger.warning(f"Waypoint template missing: pathway_{i}")

        # AFK destination tile (with optional variants)
        afk_variants = []
        afk_path = template_dir / "cyan_afk_tile.png"
        if afk_path.exists():
            afk_variants.append(str(afk_path))
        for variant_file in sorted(template_dir.glob("cyan_afk_tile_*.png")):
            afk_variants.append(str(variant_file))
        if afk_variants:
            waypoints.append(afk_variants)
        else:
            logger.warning(f"AFK tile template missing: {afk_path}")

        total_variants = sum(len(v) for v in waypoints)
        logger.info(f"Found {len(waypoints)} waypoints ({total_variants} total templates)")
        return waypoints

    # ==================== State Machine Configuration ====================

    def define_states(self) -> type[Enum]:
        return SandCrabStates

    def define_transitions(self) -> List[StateTransition]:
        return [
            # Startup: if at crab area go to FIND_CRABS, otherwise navigate there first
            StateTransition(
                SandCrabStates.IDLE, SandCrabStates.FIND_CRABS,
                condition=lambda: self._at_crab_area,
            ),
            StateTransition(
                SandCrabStates.IDLE, SandCrabStates.NAVIGATE_TO_CRABS,
                condition=lambda: not self._at_crab_area,
            ),
            # After navigation, go to FIND_CRABS
            StateTransition(SandCrabStates.NAVIGATE_TO_CRABS, SandCrabStates.FIND_CRABS),
            # Normal flow: find shell -> walk to it -> check if aggro'd -> decide if more needed
            StateTransition(SandCrabStates.FIND_CRABS, SandCrabStates.WALK_TO_CRAB),
            StateTransition(SandCrabStates.WALK_TO_CRAB, SandCrabStates.CHECK_AGGRO),
            StateTransition(SandCrabStates.CHECK_AGGRO, SandCrabStates.AGGRO_MORE_CRABS),
            # Conditional: enough crabs (by count or name detection) -> AFK spot, otherwise -> find more
            StateTransition(
                SandCrabStates.AGGRO_MORE_CRABS, SandCrabStates.WALK_TO_AFK_SPOT,
                condition=lambda: self._ready_for_combat,
            ),
            StateTransition(
                SandCrabStates.AGGRO_MORE_CRABS, SandCrabStates.FIND_CRABS,
                condition=lambda: not self._ready_for_combat,
            ),
            # WALK_TO_AFK_SPOT: conditional routing based on _ready_for_combat
            StateTransition(
                SandCrabStates.WALK_TO_AFK_SPOT, SandCrabStates.HUNT_ACTIVE_CRABS,
                condition=lambda: self._ready_for_combat,
            ),
            StateTransition(
                SandCrabStates.WALK_TO_AFK_SPOT, SandCrabStates.FIND_CRABS,
                condition=lambda: not self._ready_for_combat,
            ),
            # HUNT_ACTIVE_CRABS: crabs found -> combat, repeated failures -> reset aggro, first failure -> find shells
            StateTransition(
                SandCrabStates.HUNT_ACTIVE_CRABS, SandCrabStates.COMBAT_LOOP,
                condition=lambda: self._hunt_found_crabs,
            ),
            StateTransition(
                SandCrabStates.HUNT_ACTIVE_CRABS, SandCrabStates.RESET_AGGRO,
                condition=lambda: not self._hunt_found_crabs and self._consecutive_failed_hunts >= 2,
            ),
            StateTransition(
                SandCrabStates.HUNT_ACTIVE_CRABS, SandCrabStates.FIND_CRABS,
                condition=lambda: not self._hunt_found_crabs and self._consecutive_failed_hunts < 2,
            ),
            # Combat loop: if aggro expired -> reset, otherwise -> hunt for more crabs
            StateTransition(
                SandCrabStates.COMBAT_LOOP, SandCrabStates.RESET_AGGRO,
                condition=lambda: self._needs_aggro_reset,
            ),
            StateTransition(
                SandCrabStates.COMBAT_LOOP, SandCrabStates.HUNT_ACTIVE_CRABS,
                condition=lambda: not self._needs_aggro_reset,
            ),
            # After aggro reset, go back to finding crabs
            StateTransition(SandCrabStates.RESET_AGGRO, SandCrabStates.FIND_CRABS),
            # Fallbacks
            StateTransition(SandCrabStates.CHECK_AGGRO, SandCrabStates.FIND_CRABS),
            StateTransition(SandCrabStates.FIND_CRABS, SandCrabStates.FIND_CRABS),
            # Recovery
            StateTransition(SandCrabStates.RECOVERY, SandCrabStates.IDLE),
        ]

    def define_state_metadata(self) -> Dict[Enum, StateMetadata]:
        return build_metadata_dict(
            SandCrabStates,
            {
                SandCrabStates.IDLE: {
                    "name": "Idle",
                    "description": "Initial setup and validation.",
                    "max_retries": 2,
                    "failover": SandCrabStates.RECOVERY,
                },
                SandCrabStates.NAVIGATE_TO_CRABS: {
                    "name": "Navigate To Crabs",
                    "description": "Walk along colored tile waypoints to reach crab area.",
                    "max_retries": 2,
                    "timeout": 120.0,
                    "failover": SandCrabStates.RECOVERY,
                },
                SandCrabStates.FIND_CRABS: {
                    "name": "Find Crabs",
                    "description": "Template match dormant sand crab shells.",
                    "max_retries": 10,
                    "timeout": 60.0,
                    "failover": SandCrabStates.RECOVERY,
                },
                SandCrabStates.WALK_TO_CRAB: {
                    "name": "Walk to Crab",
                    "description": "Click on detected shell to walk over it.",
                    "max_retries": 3,
                    "timeout": 10.0,
                    "failover": SandCrabStates.FIND_CRABS,
                },
                SandCrabStates.CHECK_AGGRO: {
                    "name": "Check Aggro",
                    "description": "Brief wait for crab spawn (informational).",
                    "max_retries": 0,
                    "timeout": 5.0,
                    "failover": SandCrabStates.FIND_CRABS,
                },
                SandCrabStates.AGGRO_MORE_CRABS: {
                    "name": "Aggro More Crabs",
                    "description": "Check if enough crabs are aggro'd.",
                    "max_retries": 0,
                    "failover": SandCrabStates.FIND_CRABS,
                },
                SandCrabStates.WALK_TO_AFK_SPOT: {
                    "name": "Walk to AFK Spot",
                    "description": "Walk to RuneLite tile marker AFK position.",
                    "max_retries": 5,
                    "timeout": 15.0,
                    "failover": SandCrabStates.COMBAT_LOOP,
                },
                SandCrabStates.HUNT_ACTIVE_CRABS: {
                    "name": "Hunt Active Crabs",
                    "description": "Scan for highlighted crabs, click to attack, lure to AFK tile.",
                    "max_retries": 0,
                    "timeout": 60.0,
                    "failover": SandCrabStates.COMBAT_LOOP,
                },
                SandCrabStates.COMBAT_LOOP: {
                    "name": "Combat Loop",
                    "description": "AFK fighting sand crabs.",
                    "max_retries": 999,
                    "timeout": 600.0,
                    "failover": SandCrabStates.FIND_CRABS,
                },
                SandCrabStates.RESET_AGGRO: {
                    "name": "Reset Aggro",
                    "description": "Walk along colored tile path to reset aggro timer.",
                    "max_retries": 2,
                    "timeout": 120.0,
                    "failover": SandCrabStates.RECOVERY,
                },
                SandCrabStates.RECOVERY: {
                    "name": "Recovery",
                    "description": "Error recovery.",
                    "max_retries": 3,
                },
            },
        )

    def get_initial_state(self) -> Enum:
        return SandCrabStates.IDLE

    # ==================== Helper Methods ====================

    def _cluster_color_matches(self, matches, cluster_radius: int = 25) -> List[Tuple[int, int]]:
        """
        Cluster nearby color match pixels into distinct tile center positions.

        Multiple pixels from the same tile marker get grouped into one (cx, cy) center.

        Args:
            matches: List of ColorMatch objects from find_color(find_all=True)
            cluster_radius: Max distance between pixels in same cluster

        Returns:
            List of (center_x, center_y) for each distinct tile
        """
        if not matches:
            return []

        clusters = []
        used = [False] * len(matches)

        for i, match in enumerate(matches):
            if used[i]:
                continue
            # Start new cluster
            cluster_points = [(match.x, match.y)]
            used[i] = True

            for j in range(i + 1, len(matches)):
                if used[j]:
                    continue
                dist = ((match.x - matches[j].x) ** 2 + (match.y - matches[j].y) ** 2) ** 0.5
                if dist < cluster_radius:
                    cluster_points.append((matches[j].x, matches[j].y))
                    used[j] = True

            # Average position as tile center
            cx = sum(p[0] for p in cluster_points) // len(cluster_points)
            cy = sum(p[1] for p in cluster_points) // len(cluster_points)
            clusters.append((cx, cy))

        return clusters

    def _find_color_center(
        self,
        hex_color: str,
        tolerance: int = 15,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> Optional[Tuple[int, int]]:
        """
        Find center point of all pixels matching a color.

        Returns centroid of all matching pixels for more accurate clicking
        than a single-pixel match. Follows construction_training.py pattern.

        Args:
            hex_color: Target color as hex string (e.g., "#04A5FF")
            tolerance: Color matching tolerance
            region: Optional search region (x, y, width, height)

        Returns:
            (x, y) center coordinates, or None if no matches
        """
        matches = self.actions.screen.find_color(
            hex_color,
            tolerance=tolerance,
            region=region,
            find_all=True,
        )

        if not matches:
            return None

        total_x = sum(m.x for m in matches)
        total_y = sum(m.y for m in matches)
        center_x = total_x // len(matches)
        center_y = total_y // len(matches)

        return (center_x, center_y)

    def _click_tile_centroid(self, hex_color: str, tolerance: int = 10) -> bool:
        """
        Find a color's centroid in the game viewport and click it.

        Args:
            hex_color: Target color as hex string (e.g., "#04A5FF")
            tolerance: Color matching tolerance

        Returns:
            True if found and clicked, False if not found
        """
        viewport_region = self.state.get_game_viewport_region()
        center = self._find_color_center(hex_color, tolerance=tolerance, region=viewport_region)

        if center is None:
            return False

        cx, cy = center
        abs_x, abs_y = self.actions.coord_resolver.to_absolute(cx, cy)
        self.actions.mouse.click_at(
            abs_x, abs_y,
            move_style="curved",
            speed_multiplier=self.actions._get_mouse_speed_multiplier(),
        )
        return True

    # ==================== State Handlers ====================

    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        """Verify setup: templates exist, config colors are set."""
        logger.info("=" * 60)
        logger.info("[IDLE] Sand Crabs Combat Bot starting...")
        logger.info("=" * 60)

        if not self.shell_templates:
            logger.error(
                f"IDLE: No shell templates found! Add .png files to {self.TEMPLATE_DIR}/"
            )
            return StateResult.FAILURE

        # Log each discovered template
        logger.info(f"IDLE: Discovered {len(self.shell_templates)} shell templates:")
        for i, tpl in enumerate(self.shell_templates):
            logger.info(f"  [{i+1}] {Path(tpl).name} -> {tpl}")

        afk_color = self.config.get("colors", self.afk_marker_color)
        npc_color = self.config.get("colors", self.npc_highlight_color)

        if not afk_color:
            logger.warning(
                f"IDLE: AFK marker color '{self.afk_marker_color}' not in config. "
                "Bot will skip walking to AFK spot."
            )
        if not npc_color:
            logger.warning(
                f"IDLE: NPC highlight color '{self.npc_highlight_color}' not in config. "
                "Bot will use combat indicator instead for aggro detection."
            )

        # Reset aggro counter at start
        self._current_aggro_count = 0
        self._hunt_complete = False
        self._hunt_found_crabs = False
        self._consecutive_failed_hunts = 0
        self._cycle_start_time = time.time()

        # Summary banner
        logger.info("-" * 60)
        logger.info("  CONFIGURATION SUMMARY")
        logger.info(f"  Templates:       {len(self.shell_templates)} loaded")
        total_variants = sum(len(v) for v in self.waypoint_templates)
        logger.info(f"  Waypoints:       {len(self.waypoint_templates)} loaded ({total_variants} templates)")
        logger.info(f"  AFK marker:      {afk_color or 'NOT SET'}")
        logger.info(f"  NPC highlight:   {npc_color or 'NOT SET'}")
        logger.info(f"  Target aggro:    {self.target_aggro_count} crabs")
        logger.info(f"  Grace period:    {self.combat_grace_period}s")
        logger.info(f"  Aggro timeout:   {self.aggro_wait_timeout}s")
        pink_color = self.config.get("colors", self.path_pink_color)
        green_color = self.config.get("colors", self.path_green_color)
        logger.info(f"  Path pink:       {pink_color or 'NOT SET'}")
        logger.info(f"  Path green:      {green_color or 'NOT SET'}")
        logger.info(f"  Reset threshold: {self.no_combat_cycle_threshold} no-combat cycles")
        logger.info(f"  Stats so far:    {self._combat_cycles} cycles, {self._crabs_found} crabs found, {self._aggro_resets} resets")
        logger.info("-" * 60)

        # V22: Load viewport config overrides from config.json
        from osrsbot.constants import GAME_VIEWPORT
        vp_config = self.config.get("viewport")
        if vp_config:
            if "x_offset" in vp_config:
                GAME_VIEWPORT.viewport_x_offset = vp_config["x_offset"]
            if "y_offset" in vp_config:
                GAME_VIEWPORT.viewport_y_offset = vp_config["y_offset"]
            if "width" in vp_config:
                GAME_VIEWPORT.viewport_width = vp_config["width"]
            if "height" in vp_config:
                GAME_VIEWPORT.viewport_height = vp_config["height"]
            logger.info("  Viewport config: loaded from config.json")
        else:
            logger.info("  Viewport config: using defaults")

        # V21: Viewport & color scan diagnostics
        viewport_region = self.state.get_game_viewport_region()
        try:
            bounds = self.actions.screen._get_bounds()
        except Exception:
            bounds = None
        logger.info("  SCREEN DIAGNOSTICS")
        logger.info(f"  Window bounds:   {bounds}")
        logger.info(f"  Viewport region: {viewport_region}")
        if viewport_region:
            logger.info(
                f"  Viewport covers: ({viewport_region[0]}, {viewport_region[1]}) to "
                f"({viewport_region[0] + viewport_region[2]}, {viewport_region[1] + viewport_region[3]})"
            )
            logger.info(
                f"  Viewport center: ({viewport_region[0] + viewport_region[2] // 2}, "
                f"{viewport_region[1] + viewport_region[3] // 2})"
            )

        # Quick color scan — verify each color is detectable right now
        for color_name, color_key in [
            ("PINK", self.path_pink_color),
            ("GREEN", self.path_green_color),
            ("CYAN", self.afk_marker_color),
        ]:
            hex_color = self.config.get("colors", color_key)
            if hex_color and viewport_region:
                matches = self.actions.screen.find_color(
                    hex_color, tolerance=25, region=viewport_region, find_all=True
                )
                count = len(matches) if matches else 0
                logger.info(f"  Color scan {color_name}: {hex_color} -> {count} pixels found")
            else:
                logger.info(f"  Color scan {color_name}: {'NOT SET' if not hex_color else 'no viewport'}")
        logger.info("-" * 60)

        # Check if we're already at the crab area (cyan AFK tile visible)
        if afk_color:
            afk_center = self._find_color_center(afk_color, tolerance=10, region=viewport_region)
            if afk_center is not None:
                logger.info("IDLE: Cyan AFK tile detected — already at crab area!")
                self._at_crab_area = True
            else:
                logger.info("IDLE: Cyan AFK tile NOT visible — need to navigate to crab area.")
                self._at_crab_area = False
        else:
            # No AFK color configured, assume we're at crabs
            logger.warning("IDLE: No AFK marker configured, assuming already at crab area.")
            self._at_crab_area = True

        return StateResult.SUCCESS

    def _walk_waypoints(
        self,
        label: str,
        reverse: bool = False,
        stop_before_afk: bool = False,
    ) -> int:
        """
        Walk along numbered waypoint templates in order (V27).

        Template-matches pathway_1 -> pathway_6 -> cyan_afk_tile sequentially.
        Each waypoint supports multiple template variants for reliability.
        Uses fixed wait timing between waypoint clicks.

        Args:
            label: Log prefix for context
            reverse: If True, walk waypoints in reverse order (6->1) for aggro reset
            stop_before_afk: If True, stop after pathway_6 (don't walk to AFK tile)

        Returns:
            Number of waypoints successfully walked.
        """
        MAX_SEARCH_ATTEMPTS = 5
        THRESHOLD = 0.60

        waypoints = list(self.waypoint_templates)
        if reverse:
            waypoints = list(reversed(waypoints))
        if stop_before_afk and not reverse:
            waypoints = [w for w in waypoints if not any("cyan_afk" in v for v in w)]

        viewport_region = self.state.get_game_viewport_region()
        walked = 0

        for wp_idx, wp_variants in enumerate(waypoints):
            self._check_exit_requested()
            wp_name = Path(wp_variants[0]).stem

            logger.info(
                f"{label}: Looking for waypoint [{wp_idx + 1}/{len(waypoints)}]: "
                f"{wp_name} ({len(wp_variants)} variant(s))"
            )

            found = False
            for attempt in range(MAX_SEARCH_ATTEMPTS):
                self._check_exit_requested()

                # Multi-template match for this waypoint's variants
                if len(wp_variants) == 1:
                    result = self.state.find_template(
                        wp_variants[0], threshold=THRESHOLD, region=viewport_region
                    )
                    if result:
                        cx, cy, confidence = result
                else:
                    multi_result = self.state.find_multi_template(
                        wp_variants, threshold=THRESHOLD, region=viewport_region
                    )
                    if multi_result:
                        cx, cy, confidence, _ = multi_result
                        result = multi_result
                    else:
                        result = None

                if result:
                    logger.info(
                        f"{label}: Found {wp_name} at ({cx}, {cy}) "
                        f"conf={confidence:.2f}, clicking..."
                    )

                    abs_x, abs_y = self.actions.coord_resolver.to_absolute(cx, cy)
                    self.actions.mouse.click_at(
                        abs_x, abs_y,
                        move_style="curved",
                        speed_multiplier=self.actions._get_mouse_speed_multiplier(),
                    )

                    # Fixed wait for walk animation
                    self.actions.wait("long")
                    self.actions.wait("long")

                    walked += 1
                    found = True
                    break
                else:
                    logger.debug(
                        f"{label}: {wp_name} not visible "
                        f"(attempt {attempt + 1}/{MAX_SEARCH_ATTEMPTS})"
                    )
                    self.actions.wait("medium")

            if not found:
                logger.info(
                    f"{label}: Skipping {wp_name} "
                    f"(not found after {MAX_SEARCH_ATTEMPTS} attempts). "
                    f"Walking forward to bring next waypoints into view."
                )
                # Walk in the travel direction so the next waypoint becomes visible
                viewport_region = self.state.get_game_viewport_region()
                if viewport_region:
                    vp_cx = viewport_region[0] + viewport_region[2] // 2
                    if reverse:
                        # Walking AWAY from crabs: click bottom of viewport
                        target_y = viewport_region[1] + viewport_region[3] - 50
                    else:
                        # Walking TOWARD crabs: click top of viewport
                        target_y = viewport_region[1] + 50
                    abs_x, abs_y = self.actions.coord_resolver.to_absolute(vp_cx, target_y)
                    self.actions.mouse.click_at(
                        abs_x, abs_y,
                        move_style="curved",
                        speed_multiplier=self.actions._get_mouse_speed_multiplier(),
                    )
                    self.actions.wait("long")
                    self.actions.wait("long")

        logger.info(
            f"{label}: Waypoint navigation complete. "
            f"{walked}/{len(waypoints)} waypoints walked."
        )
        return walked

    def _handle_navigate_to_crabs(self, context: StateExecutionContext) -> StateResult:
        """Walk to crab area via sequential waypoint template matching."""
        logger.info("=" * 60)
        logger.info("[NAVIGATE_TO_CRABS] Walking to crab area via waypoint templates...")
        logger.info("=" * 60)

        walk_steps = self._walk_waypoints("NAVIGATE_TO_CRABS")

        if walk_steps == 0:
            logger.warning("NAVIGATE_TO_CRABS: No waypoints found at all!")
            return StateResult.FAILURE

        logger.info(f"NAVIGATE_TO_CRABS: Navigation complete ({walk_steps} waypoints walked).")
        self._at_crab_area = True
        return StateResult.SUCCESS

    def _handle_find_crabs(self, context: StateExecutionContext) -> StateResult:
        """
        Use multi-template matching to find dormant sand crab shells on screen.
        Restricts search to the game viewport (excludes UI).
        """
        logger.info(
            f"[FIND_CRABS] Searching for shells... "
            f"(aggro'd so far: {self._current_aggro_count}/{self.target_aggro_count})"
        )

        viewport_region = self.state.get_game_viewport_region()
        logger.debug(
            f"FIND_CRABS: Viewport region={viewport_region}, "
            f"templates={[Path(t).name for t in self.shell_templates]}, "
            f"threshold=0.65"
        )

        # Get ALL matches above threshold, not just the best one
        matches = self.state.find_all_multi_template(
            self.shell_templates,
            threshold=0.65,
            region=viewport_region,
        )

        if not matches:
            logger.info("FIND_CRABS: No dormant shells found above threshold (0.65).")

            # Diagnostic: check best sub-threshold match so we can tune thresholds
            diag_result = self.state.find_multi_template(
                self.shell_templates,
                threshold=0.0,
                region=viewport_region,
            )
            if diag_result:
                dx, dy, d_conf, d_tpl = diag_result
                logger.info(
                    f"FIND_CRABS: [DIAGNOSTIC] Best sub-threshold match: "
                    f"template={d_tpl}, confidence={d_conf:.3f}, "
                    f"at ({dx}, {dy}) — needs >= 0.65 to pass"
                )
            else:
                logger.info("FIND_CRABS: [DIAGNOSTIC] No template matches at all (even threshold=0)")

            direction = random.choice(["up", "down", "left", "right"])
            tiles = random.randint(2, 4)
            logger.info(f"FIND_CRABS: Walking {tiles} tiles {direction} to search new area...")
            self.actions.walk_tiles(direction, tiles)
            self.actions.wait("long")

            return StateResult.FAILURE

        # Filter out matches too close to recently visited shells
        DEDUP_RADIUS = 60  # pixels
        valid_matches = []
        for match_x, match_y, confidence, template_name in matches:
            too_close = False
            for vx, vy in self._visited_shells:
                dist = ((match_x - vx) ** 2 + (match_y - vy) ** 2) ** 0.5
                if dist < DEDUP_RADIUS:
                    logger.debug(
                        f"FIND_CRABS: Filtering match at ({match_x}, {match_y}) — "
                        f"{dist:.0f}px from visited ({vx}, {vy})"
                    )
                    too_close = True
                    break
            if not too_close:
                valid_matches.append((match_x, match_y, confidence, template_name))

        if not valid_matches:
            logger.info(
                f"FIND_CRABS: Found {len(matches)} shells but all within "
                f"dedup radius of visited shells. Walking to find new area..."
            )
            direction = random.choice(["up", "down", "left", "right"])
            tiles = random.randint(2, 4)
            self.actions.walk_tiles(direction, tiles)
            self.actions.wait("long")
            return StateResult.FAILURE

        # Sort by distance to viewport center (player position), closest first
        cx = viewport_region[0] + viewport_region[2] // 2
        cy = viewport_region[1] + viewport_region[3] // 2
        valid_matches.sort(
            key=lambda m: (m[0] - cx) ** 2 + (m[1] - cy) ** 2
        )

        # Pick the closest valid shell
        center_x, center_y, confidence, template_name = valid_matches[0]
        dist_to_player = ((center_x - cx) ** 2 + (center_y - cy) ** 2) ** 0.5

        self._last_crab_x = center_x
        self._last_crab_y = center_y
        self._crabs_found += 1

        logger.info(
            f"FIND_CRABS: MATCH! Closest shell at ({center_x}, {center_y}) "
            f"confidence={confidence:.3f} template={template_name} "
            f"distance={dist_to_player:.0f}px from player "
            f"({len(valid_matches)} valid / {len(matches)} total found) "
            f"(total crabs found: {self._crabs_found})"
        )

        return StateResult.SUCCESS

    def _handle_walk_to_crab(self, context: StateExecutionContext) -> StateResult:
        """Click on the detected shell location to walk over it and trigger the crab."""
        logger.info(
            f"[WALK_TO_CRAB] Walking to shell at relative=({self._last_crab_x}, {self._last_crab_y})"
        )

        abs_x, abs_y = self.actions._to_absolute(self._last_crab_x, self._last_crab_y)
        logger.info(
            f"WALK_TO_CRAB: Clicking relative=({self._last_crab_x}, {self._last_crab_y}) "
            f"-> absolute=({abs_x}, {abs_y})"
        )

        walk_start = time.time()
        success = self.actions.mouse.click_at(
            abs_x, abs_y,
            move_style="curved",
            speed_multiplier=self.actions._get_mouse_speed_multiplier(),
        )

        if not success:
            logger.warning("WALK_TO_CRAB: Mouse click FAILED on shell location")
            return StateResult.FAILURE

        logger.info("WALK_TO_CRAB: Click successful, waiting for player to walk...")

        # Wait ~2 seconds for the player to walk there
        self.actions.wait("long")
        self.actions.wait("medium")

        walk_elapsed = time.time() - walk_start

        # Record this shell as visited and count toward aggro target
        self._visited_shells.append((self._last_crab_x, self._last_crab_y))
        self._current_aggro_count += 1
        logger.info(
            f"WALK_TO_CRAB: Arrived at shell (walk time: {walk_elapsed:.1f}s). "
            f"Shell visited. Aggro count: "
            f"{self._current_aggro_count}/{self.target_aggro_count} "
            f"(visited shells: {len(self._visited_shells)})"
        )
        return StateResult.SUCCESS

    def _handle_check_aggro(self, context: StateExecutionContext) -> StateResult:
        """
        Wait briefly for crab to spawn after walking over a shell.
        Polls in_combat() as the detection signal.
        Always returns SUCCESS so the state machine proceeds to AGGRO_MORE_CRABS.
        """
        logger.info("[CHECK_AGGRO] Waiting for crab spawn (2s)...")

        start_time = time.time()
        spawn_wait = 2.0
        check_interval = 0.4
        detected = False

        while time.time() - start_time < spawn_wait:
            if self.state.in_combat():
                logger.info("CHECK_AGGRO: Combat detected — crab confirmed spawned!")
                detected = True
                break
            time.sleep(check_interval)

        if not detected:
            logger.info(
                "CHECK_AGGRO: No combat detected after 2s. "
                "Crab may not have spawned from this shell."
            )

        return StateResult.SUCCESS

    def _handle_aggro_more_crabs(self, context: StateExecutionContext) -> StateResult:
        """
        Decision node: check if we have enough crabs aggro'd.
        Uses shell visit count only — in_combat() can't distinguish
        1 crab from 3, so it would always short-circuit after 1 shell.
        Always returns SUCCESS — conditional transitions handle routing:
        - enough shells visited -> WALK_TO_AFK_SPOT
        - need more -> FIND_CRABS
        """
        logger.info(
            f"[AGGRO_MORE_CRABS] Aggro count: "
            f"{self._current_aggro_count}/{self.target_aggro_count}"
        )

        if self._current_aggro_count >= self.target_aggro_count:
            self._ready_for_combat = True
            logger.info(
                f"AGGRO_MORE_CRABS: Target reached "
                f"({self._current_aggro_count} shells visited). "
                "Moving to AFK spot. (_ready_for_combat=True)"
            )
        else:
            self._ready_for_combat = False
            logger.info(
                f"AGGRO_MORE_CRABS: Need more crabs. "
                f"Shell visits: {self._current_aggro_count}/{self.target_aggro_count}. "
                f"Searching for another shell..."
            )

        return StateResult.SUCCESS

    def _handle_walk_to_afk_spot(self, context: StateExecutionContext) -> StateResult:
        """Walk to the RuneLite tile marker AFK spot (viewport-restricted)."""
        afk_color = self.config.get("colors", self.afk_marker_color)
        logger.info(
            f"[WALK_TO_AFK_SPOT] Walking to AFK tile marker "
            f"(color_key={self.afk_marker_color}, hex={afk_color or 'NOT SET'})"
        )

        if not afk_color:
            logger.info("WALK_TO_AFK_SPOT: No AFK marker configured, staying in place.")
            return StateResult.SUCCESS

        # Restrict search to game viewport (exclude minimap, inventory, chatbox)
        viewport_region = self.state.get_game_viewport_region()
        tile_center = self._find_color_center(
            afk_color, tolerance=10, region=viewport_region
        )

        if not tile_center:
            logger.warning(
                f"WALK_TO_AFK_SPOT: AFK tile marker color {afk_color} "
                "NOT visible in game viewport. Staying in place."
            )
            return StateResult.SUCCESS

        center_x, center_y = tile_center
        logger.info(f"WALK_TO_AFK_SPOT: AFK tile centroid at ({center_x}, {center_y})")

        walk_start = time.time()
        abs_x, abs_y = self.actions.coord_resolver.to_absolute(center_x, center_y)
        self.actions.mouse.click_at(
            abs_x, abs_y,
            move_style="curved",
            speed_multiplier=self.actions._get_mouse_speed_multiplier(),
        )

        logger.info("WALK_TO_AFK_SPOT: Clicked AFK marker, waiting for player to arrive...")

        # Wait ~2s for player to arrive at AFK spot
        self.actions.wait("long")
        self.actions.wait("short")

        walk_elapsed = time.time() - walk_start
        logger.info(f"WALK_TO_AFK_SPOT: Arrived at AFK spot (walk time: {walk_elapsed:.1f}s)")
        return StateResult.SUCCESS

    def _handle_hunt_active_crabs(self, context: StateExecutionContext) -> StateResult:
        """
        Scan for NPC-highlighted crabs, click nearest to attack,
        walk back to cyan AFK tile to lure. Repeat until none visible.
        """
        logger.info("[HUNT_ACTIVE_CRABS] Scanning for highlighted crabs to lure...")

        # Step 0: Check if in combat (crabs are attacking)
        if not self.state.in_combat():
            self._hunt_complete = True
            self._hunt_found_crabs = False
            self._consecutive_failed_hunts += 1
            logger.info(
                f"HUNT_ACTIVE_CRABS: Not in combat — no active crabs to hunt. "
                f"Consecutive failed hunts: {self._consecutive_failed_hunts}"
            )
            return StateResult.SUCCESS

        hex_color = self.config.get("colors", self.npc_highlight_color)
        afk_color = self.config.get("colors", self.afk_marker_color)
        viewport_region = self.state.get_game_viewport_region()

        if not hex_color:
            logger.warning("HUNT_ACTIVE_CRABS: No NPC highlight color configured, skipping.")
            self._hunt_complete = True
            return StateResult.SUCCESS

        crabs_lured = 0
        iteration = 0

        for iteration in range(self._max_hunt_iterations):
            self._check_exit_requested()

            # If already in combat, stop hunting — crabs are attacking
            if self.state.in_combat():
                logger.info(
                    f"HUNT_ACTIVE_CRABS: Already in combat! "
                    f"Stopping hunt after {crabs_lured} lures."
                )
                break

            # Step A: Find all NPC highlight pixels, cluster into crab positions
            matches = self.actions.screen.find_color(
                hex_color, tolerance=10, region=viewport_region, find_all=True
            )

            if not matches:
                logger.info(
                    f"HUNT_ACTIVE_CRABS: No highlighted crabs visible "
                    f"(iteration {iteration + 1}). Lured {crabs_lured} crabs."
                )
                break

            crab_positions = self._cluster_color_matches(matches, cluster_radius=30)
            if not crab_positions:
                logger.info("HUNT_ACTIVE_CRABS: Clustering returned no positions.")
                break

            # Step B: Pick nearest crab to viewport center, skip very close ones
            if viewport_region:
                cx = viewport_region[0] + viewport_region[2] // 2
                cy = viewport_region[1] + viewport_region[3] // 2
            else:
                cx, cy = 400, 300

            MIN_CRAB_DIST = 40
            distant_crabs = [
                (x, y) for x, y in crab_positions
                if ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 >= MIN_CRAB_DIST
            ]

            if not distant_crabs:
                logger.info(
                    f"HUNT_ACTIVE_CRABS: All {len(crab_positions)} crabs near player. "
                    "Already attacking. Hunt complete."
                )
                break

            distant_crabs.sort(
                key=lambda pos: ((pos[0] - cx) ** 2 + (pos[1] - cy) ** 2) ** 0.5
            )
            target_x, target_y = distant_crabs[0]
            target_dist = ((target_x - cx) ** 2 + (target_y - cy) ** 2) ** 0.5

            logger.info(
                f"HUNT_ACTIVE_CRABS: [{iteration + 1}/{self._max_hunt_iterations}] "
                f"Found {len(crab_positions)} crabs, {len(distant_crabs)} distant. "
                f"Clicking nearest at ({target_x}, {target_y}), dist={target_dist:.0f}px"
            )

            # Step C: Click crab to attack
            abs_x, abs_y = self.actions.coord_resolver.to_absolute(target_x, target_y)
            self.actions.mouse.click_at(
                abs_x, abs_y,
                move_style="curved",
                speed_multiplier=self.actions._get_mouse_speed_multiplier(),
            )
            time.sleep(self._hunt_click_timeout)
            self._check_exit_requested()

            # Step D: Walk back to cyan AFK tile to lure crab
            if afk_color:
                logger.info("HUNT_ACTIVE_CRABS: Walking back to AFK tile...")
                clicked = self._click_tile_centroid(afk_color, tolerance=10)
                if clicked:
                    self.actions.wait("long")
                    self.actions.wait("short")
                    crabs_lured += 1
                    logger.info(f"HUNT_ACTIVE_CRABS: Lured crab #{crabs_lured}.")
                else:
                    logger.warning("HUNT_ACTIVE_CRABS: AFK tile not visible. Stopping hunt.")
                    break
            else:
                crabs_lured += 1

            self.actions.wait("short")

        logger.info(
            f"HUNT_ACTIVE_CRABS: Complete. "
            f"Lured {crabs_lured} crabs in {iteration + 1} iterations."
        )
        self._hunt_complete = True
        self._hunt_found_crabs = crabs_lured > 0 or self.state.in_combat()
        if self._hunt_found_crabs:
            self._consecutive_failed_hunts = 0
        else:
            self._consecutive_failed_hunts += 1
            logger.info(
                f"HUNT_ACTIVE_CRABS: No crabs lured or in combat. "
                f"Consecutive failed hunts: {self._consecutive_failed_hunts}"
            )
        return StateResult.SUCCESS

    def _handle_combat_loop(self, context: StateExecutionContext) -> StateResult:
        """
        Main AFK combat loop.
        Auto-retaliate handles attacking. We just monitor combat state.
        Grace period after combat ends to catch respawns.
        """
        logger.info("[COMBAT_LOOP] AFK fighting sand crabs...")
        self._combat_start_time = time.time()

        no_combat_start: Optional[float] = None
        last_status_log = time.time()
        combat_ticks = 0
        idle_ticks = 0
        STATUS_LOG_INTERVAL = 5.0  # Log status every N seconds

        while True:
            self._check_exit_requested()

            in_combat = self.state.in_combat()

            if in_combat:
                no_combat_start = None
                combat_ticks += 1

                # Periodic status log while in combat
                now = time.time()
                if now - last_status_log >= STATUS_LOG_INTERVAL:
                    combat_elapsed = now - self._combat_start_time
                    logger.info(
                        f"COMBAT_LOOP: [STATUS] IN COMBAT for {combat_elapsed:.0f}s "
                        f"(combat_ticks={combat_ticks}, idle_ticks={idle_ticks})"
                    )
                    last_status_log = now

                time.sleep(0.6)
                continue

            # Not in combat
            idle_ticks += 1

            if no_combat_start is None:
                no_combat_start = time.time()
                combat_duration = no_combat_start - self._combat_start_time
                logger.info(
                    f"COMBAT_LOOP: Combat ended after {combat_duration:.1f}s. "
                    f"Starting grace period ({self.combat_grace_period}s)..."
                )

            grace_elapsed = time.time() - no_combat_start

            # Periodic grace period countdown
            now = time.time()
            if now - last_status_log >= 2.0:
                logger.info(
                    f"COMBAT_LOOP: [GRACE] {grace_elapsed:.1f}s / {self.combat_grace_period}s "
                    f"— waiting for combat to resume..."
                )
                last_status_log = now

            if grace_elapsed >= self.combat_grace_period:
                self._combat_cycles += 1
                # Reset for next cycle
                self._current_aggro_count = 0
                self._ready_for_combat = False
                self._hunt_complete = False
                self._hunt_found_crabs = False
                self._consecutive_failed_hunts = 0
                self._visited_shells.clear()

                total_time = time.time() - self._combat_start_time
                cycle_time = time.time() - self._cycle_start_time if self._cycle_start_time else 0

                logger.info(
                    f"COMBAT_LOOP: Grace period expired ({grace_elapsed:.1f}s). "
                    f"Crabs likely dead."
                )
                logger.info(
                    f"COMBAT_LOOP: [CYCLE STATS] "
                    f"cycle #{self._combat_cycles}, "
                    f"combat_phase={total_time:.1f}s, "
                    f"full_cycle={cycle_time:.1f}s, "
                    f"combat_ticks={combat_ticks}, idle_ticks={idle_ticks}, "
                    f"total_crabs_found={self._crabs_found}"
                )

                # Track no-combat cycles for aggro reset detection
                if combat_ticks == 0:
                    self._consecutive_no_combat_cycles += 1
                    logger.warning(
                        f"COMBAT_LOOP: NO COMBAT detected this cycle! "
                        f"Consecutive no-combat cycles: "
                        f"{self._consecutive_no_combat_cycles}/{self.no_combat_cycle_threshold}"
                    )
                    if self._consecutive_no_combat_cycles >= self.no_combat_cycle_threshold:
                        self._needs_aggro_reset = True
                        logger.warning(
                            "COMBAT_LOOP: Aggro likely expired (10-min mechanic)! "
                            "Triggering aggro reset path."
                        )
                else:
                    self._consecutive_no_combat_cycles = 0

                logger.info("COMBAT_LOOP: Going to find more crabs.")

                # Reset cycle timer for next cycle
                self._cycle_start_time = time.time()
                return StateResult.SUCCESS

            # Still in grace period
            time.sleep(0.6)

            # Anti-ban: occasional idle actions
            if random.random() < 0.05:
                pause = random.uniform(0.5, 2.0)
                logger.debug(f"COMBAT_LOOP: Anti-ban pause ({pause:.1f}s)")
                time.sleep(pause)

    def _handle_reset_aggro(self, context: StateExecutionContext) -> StateResult:
        """
        Walk away from crab area and back to reset the 10-minute aggro timer.

        V24: Uses template-matched waypoints in reverse (6->1) then forward (1->6->AFK).
        """
        logger.warning("=" * 60)
        logger.warning(
            f"[RESET_AGGRO] Aggro expired! Walking reset path "
            f"(consecutive no-combat cycles: {self._consecutive_no_combat_cycles})"
        )
        logger.warning("=" * 60)

        # ---- Phase 1: Walk Away (reverse waypoint order) ----
        logger.info("RESET_AGGRO: Phase 1 — Walking AWAY from crabs (reverse waypoints)...")
        walk_away_steps = self._walk_waypoints(
            "RESET_AGGRO_AWAY",
            reverse=True,
        )

        if walk_away_steps == 0:
            logger.warning(
                "RESET_AGGRO: No waypoints found at all! "
                "Cannot reset aggro. Check waypoint templates."
            )
            self._needs_aggro_reset = False
            self._consecutive_no_combat_cycles = 0
            return StateResult.FAILURE

        # ---- Phase 2: Pause at end of path ----
        pause_time = random.uniform(2.0, 4.0)
        logger.info(f"RESET_AGGRO: Phase 2 — Pausing at end of path ({pause_time:.1f}s)...")
        time.sleep(pause_time)

        # ---- Phase 3: Walk Back (forward waypoint order) ----
        logger.info("RESET_AGGRO: Phase 3 — Walking BACK toward crabs (forward waypoints)...")
        walk_back_steps = self._walk_waypoints("RESET_AGGRO_BACK")

        # ---- Phase 4: Cleanup ----
        self._needs_aggro_reset = False
        self._consecutive_no_combat_cycles = 0
        self._consecutive_failed_hunts = 0
        self._current_aggro_count = 0
        self._ready_for_combat = False
        self._visited_shells.clear()
        self._aggro_resets += 1

        logger.info(
            f"RESET_AGGRO: Complete! "
            f"Walked {walk_away_steps} tiles away, {walk_back_steps} tiles back. "
            f"Total aggro resets: {self._aggro_resets}. "
            f"Returning to FIND_CRABS."
        )
        logger.warning("=" * 60)

        return StateResult.SUCCESS

    def _handle_recovery(self, context: StateExecutionContext) -> StateResult:
        """Recovery state - wait and reset to IDLE."""
        logger.warning("=" * 60)
        logger.warning("[RECOVERY] Recovering from error...")
        logger.warning(
            f"RECOVERY: Resetting state — "
            f"aggro_count was {self._current_aggro_count}, setting to 0"
        )
        logger.warning(
            f"RECOVERY: [BOT STATS] "
            f"cycles={self._combat_cycles}, "
            f"crabs_found={self._crabs_found}, "
            f"aggro_resets={self._aggro_resets}, "
            f"templates={len(self.shell_templates)}"
        )
        logger.warning("=" * 60)

        self._current_aggro_count = 0
        self._ready_for_combat = False
        self._visited_shells.clear()
        self._needs_aggro_reset = False
        self._consecutive_no_combat_cycles = 0
        self._hunt_complete = False
        self._hunt_found_crabs = False
        self._consecutive_failed_hunts = 0
        self._cycle_start_time = time.time()
        self.actions.wait("long")

        logger.info("RECOVERY: Returning to IDLE")
        return StateResult.SUCCESS
