"""
Anti-Ban Service - Behavioral randomization and break scheduling.

Provides comprehensive anti-detection features:
- Scheduled breaks with randomized timing and duration
- Micro-breaks between actions (random pauses)
- Session-level behavioral variance (timing/speed multipliers)
- Idle actions (mouse jitter, stats checking)
- Activity pattern tracking for detection avoidance

All features are configurable via config.json and constants.py.
"""

import logging
import math
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from osrsbot.constants import ANTI_BAN
from osrsbot.models.config import Config

if TYPE_CHECKING:
    from osrsbot.commands.game_actions import GameActions
    from osrsbot.services.mouse_service import MouseService

logger = logging.getLogger(__name__)


@dataclass
class BreakSegment:
    """A single play/break cycle in the session schedule."""

    play_minutes: float
    break_minutes: float
    pattern: str  # "short", "medium", "long_break", "extended"
    scheduled_play_end: float = 0.0
    actual_play_start: float = 0.0
    actual_break_start: float = 0.0
    ratio_enforced: bool = False

    def __str__(self) -> str:
        enforced = " [RATIO-ENFORCED]" if self.ratio_enforced else ""
        return (
            f"{self.pattern}: Play {self.play_minutes:.0f}m "
            f"-> Break {self.break_minutes:.0f}m{enforced}"
        )


@dataclass
class SessionState:
    """Tracks current session metrics and behavioral variance."""

    session_start_time: float = field(default_factory=time.time)
    actions_performed: int = 0
    last_break_time: float = field(default_factory=time.time)
    next_break_time: float = 0.0
    last_idle_action_time: float = field(default_factory=time.time)

    # Session-specific multipliers (drift over time via random walk)
    timing_variance: float = 1.0
    mouse_speed_variance: float = 1.0

    # Variance drift tracking
    variance_last_drift_time: float = 0.0
    variance_drift_interval: float = 300.0  # Randomized each drift

    # Activity tracking for pattern detection
    recent_actions: deque = field(default_factory=lambda: deque(maxlen=10))

    # Break schedule tracking
    break_schedule: list = field(default_factory=list)
    current_segment_index: int = 0
    cumulative_play_seconds: float = 0.0
    cumulative_break_seconds: float = 0.0


class BreakScheduler:
    """
    Human-like break scheduling with weighted pattern variety and ratio enforcement.

    Patterns:
        short      — 20-40m play, 5-10m break  (40%)
        medium     — 45-75m play, 15-25m break  (25%)
        long_break — 20-35m play, 60-120m break (10%)
        extended   — 90-180m play, 15-30m break (25%)

    Constraints enforced during schedule generation:
        - 3-hour hard cap on continuous play
        - Play:break ratio kept below ceiling (default 6:1)
        - Cumulative counters reset after long breaks (>60m)
    """

    # Pattern names in fixed order for weight alignment
    PATTERN_NAMES = ("short", "medium", "long_break", "extended")

    def __init__(self, config: Config):
        self.config = config
        self.enabled = config.get(
            "anti_ban.breaks.enabled", default=ANTI_BAN.enable_breaks
        )

        # Pattern ranges: (play_min, play_max, break_min, break_max) in minutes
        self.patterns: Dict[str, Tuple[float, float, float, float]] = {
            "short": ANTI_BAN.break_pattern_short,
            "medium": ANTI_BAN.break_pattern_medium,
            "long_break": ANTI_BAN.break_pattern_long_break,
            "extended": ANTI_BAN.break_pattern_extended,
        }

        # Weights in the same order as PATTERN_NAMES
        self.weights: List[float] = [
            ANTI_BAN.break_pattern_weight_short,
            ANTI_BAN.break_pattern_weight_medium,
            ANTI_BAN.break_pattern_weight_long_break,
            ANTI_BAN.break_pattern_weight_extended,
        ]

        # Hard limits
        self.max_continuous_play = ANTI_BAN.max_continuous_play_minutes
        self.min_break_after_cap = ANTI_BAN.min_break_after_cap_minutes
        self.target_ratio = ANTI_BAN.target_play_break_ratio
        self.ratio_ceiling = ANTI_BAN.ratio_enforcement_ceiling
        self.segments_count = ANTI_BAN.segments_to_pregenerate

    # ------------------------------------------------------------------ #
    #  Schedule generation
    # ------------------------------------------------------------------ #

    def generate_schedule(self) -> List[BreakSegment]:
        """Pre-generate a full session schedule with constraint enforcement."""
        segments: List[BreakSegment] = []
        cum_play = 0.0  # cumulative play minutes since last reset
        cum_break = 0.0  # cumulative break minutes since last reset
        hit_cap = False

        for _ in range(self.segments_count):
            pattern_name = self._pick_pattern()
            play_min, play_max, brk_min, brk_max = self.patterns[pattern_name]
            play = random.uniform(play_min, play_max)
            brk = random.uniform(brk_min, brk_max)
            ratio_enforced = False

            # --- 3-hour hard cap ---
            if cum_play + play > self.max_continuous_play:
                play = max(5.0, self.max_continuous_play - cum_play)
                brk = max(brk, random.uniform(*self.min_break_after_cap))
                ratio_enforced = True
                hit_cap = True

            cum_play += play
            cum_break += brk

            # --- Ratio enforcement ---
            if cum_break > 0:
                ratio = cum_play / cum_break
                if ratio > self.ratio_ceiling:
                    needed = (cum_play / self.target_ratio) - cum_break
                    if needed > 0:
                        brk += needed
                        cum_break += needed
                        ratio_enforced = True

            segment = BreakSegment(
                play_minutes=round(play, 1),
                break_minutes=round(brk, 1),
                pattern=pattern_name,
                ratio_enforced=ratio_enforced,
            )
            segments.append(segment)

            # Reset cumulative counters after long breaks or 3-hour cap
            if brk >= 60.0 or hit_cap:
                cum_play = 0.0
                cum_break = 0.0
                hit_cap = False

        return segments

    def initialize_schedule(self, session: SessionState) -> None:
        """Generate the schedule, stamp the first segment, and log it."""
        if not self.enabled:
            logger.info("Break scheduler disabled")
            return

        session.break_schedule = self.generate_schedule()
        session.current_segment_index = 0

        if session.break_schedule:
            first = session.break_schedule[0]
            first.actual_play_start = time.time()
            first.scheduled_play_end = time.time() + first.play_minutes * 60

        self._log_schedule(session.break_schedule)

    # ------------------------------------------------------------------ #
    #  Runtime queries
    # ------------------------------------------------------------------ #

    def is_break_time(self, session: SessionState) -> bool:
        """Check whether the current segment's play window has elapsed."""
        if not self.enabled:
            return False

        seg = self._current_segment(session)
        if seg is None:
            return False

        # Auto-extend if running low
        remaining = len(session.break_schedule) - session.current_segment_index
        if remaining <= 2:
            self._extend_schedule(session)

        return time.time() >= seg.scheduled_play_end

    def get_current_break_duration(self, session: SessionState) -> float:
        """Return break duration **in seconds** for the current segment."""
        seg = self._current_segment(session)
        if seg is None:
            return 300.0  # 5-min fallback
        return seg.break_minutes * 60.0

    def advance_segment(self, session: SessionState) -> None:
        """Move to the next segment after a break completes."""
        seg = self._current_segment(session)
        if seg is not None:
            # Record actual durations
            actual_play = (seg.actual_break_start - seg.actual_play_start) if seg.actual_play_start else 0.0
            actual_break = (time.time() - seg.actual_break_start) if seg.actual_break_start else 0.0
            session.cumulative_play_seconds += actual_play
            session.cumulative_break_seconds += actual_break

        session.current_segment_index += 1
        nxt = self._current_segment(session)
        if nxt is not None:
            nxt.actual_play_start = time.time()
            nxt.scheduled_play_end = time.time() + nxt.play_minutes * 60
            logger.info(
                f"Advanced to segment {session.current_segment_index + 1}: {nxt}"
            )

        # Log cumulative stats
        play_h = session.cumulative_play_seconds / 3600
        brk_h = session.cumulative_break_seconds / 3600
        ratio = (
            session.cumulative_play_seconds / session.cumulative_break_seconds
            if session.cumulative_break_seconds > 0
            else 0.0
        )
        logger.info(
            f"Session totals: {play_h:.2f}h play, {brk_h:.2f}h break "
            f"(ratio {ratio:.1f}:1)"
        )

    # ------------------------------------------------------------------ #
    #  Internals
    # ------------------------------------------------------------------ #

    def _current_segment(self, session: SessionState) -> Optional[BreakSegment]:
        idx = session.current_segment_index
        if 0 <= idx < len(session.break_schedule):
            return session.break_schedule[idx]
        return None

    def _pick_pattern(self) -> str:
        return random.choices(list(self.PATTERN_NAMES), weights=self.weights, k=1)[0]

    def _extend_schedule(self, session: SessionState) -> None:
        """Append more segments when the schedule is nearly exhausted."""
        new_segments = self.generate_schedule()
        session.break_schedule.extend(new_segments)
        logger.info(
            f"Schedule extended by {len(new_segments)} segments "
            f"(total: {len(session.break_schedule)})"
        )

    def _log_schedule(self, schedule: List[BreakSegment]) -> None:
        logger.info("=" * 70)
        logger.info("BREAK SCHEDULE GENERATED")
        logger.info("=" * 70)

        cum_play = 0.0
        cum_break = 0.0
        for i, seg in enumerate(schedule):
            cum_play += seg.play_minutes
            cum_break += seg.break_minutes
            ratio = cum_play / cum_break if cum_break > 0 else 0.0
            reset_note = " | Reset after long break" if seg.break_minutes >= 60 else ""
            logger.info(
                f"  Segment {i + 1}: {seg} | "
                f"Cumulative: {cum_play:.0f}m/{cum_break:.0f}m "
                f"({ratio:.1f}:1){reset_note}"
            )
            if seg.break_minutes >= 60:
                cum_play = 0.0
                cum_break = 0.0

        total_play = sum(s.play_minutes for s in schedule)
        total_break = sum(s.break_minutes for s in schedule)
        total = total_play + total_break
        overall_ratio = total_play / total_break if total_break > 0 else 0.0
        logger.info("=" * 70)
        logger.info(
            f"TOTAL: {total_play:.0f}m play + {total_break:.0f}m break "
            f"= {total:.0f}m ({total / 60:.1f}h) | Ratio: {overall_ratio:.1f}:1"
        )
        logger.info("=" * 70)


class AntiBanService:
    """
    Core anti-ban service providing behavioral randomization and break management.

    Features:
    - Scheduled breaks with random intervals (30-60 min) and durations (2-5 min)
    - Micro-breaks: 5% chance of short pause (0.5-2s) after actions
    - Session variance: Randomize timing/speed multipliers per session (±15%)
    - Idle actions: Random mouse movements, stats checking
    - Pattern detection: Track action sequences to avoid repetitive behavior
    """

    def __init__(self, config: Config):
        self.config = config
        self.session = SessionState()
        self.break_scheduler = BreakScheduler(config)

        # Load configuration
        self.enabled = config.get("anti_ban.enabled", default=True)
        self.micro_breaks_enabled = config.get(
            "anti_ban.micro_breaks.enabled", default=ANTI_BAN.enable_micro_breaks
        )
        self.session_variance_enabled = config.get(
            "anti_ban.session_variance.enabled",
            default=ANTI_BAN.enable_session_variance,
        )
        self.idle_actions_enabled = config.get(
            "anti_ban.idle_actions.enabled", default=ANTI_BAN.enable_idle_actions
        )

        # Micro-break configuration
        self.micro_break_chance = config.get(
            "anti_ban.micro_breaks.chance", default=ANTI_BAN.micro_break_chance
        )
        micro_break_duration_config = config.get(
            "anti_ban.micro_breaks.duration_seconds", default=None
        )
        if (
            isinstance(micro_break_duration_config, (list, tuple))
            and len(micro_break_duration_config) == 2
        ):
            self.micro_break_duration_range = tuple(micro_break_duration_config)
        else:
            self.micro_break_duration_range = ANTI_BAN.micro_break_duration_range

        # Idle action configuration
        self.idle_action_interval = config.get(
            "anti_ban.idle_actions.interval_seconds",
            default=ANTI_BAN.idle_action_interval,
        )
        mouse_jitter_config = config.get(
            "anti_ban.idle_actions.mouse_jitter_pixels", default=None
        )
        if (
            isinstance(mouse_jitter_config, (list, tuple))
            and len(mouse_jitter_config) == 2
        ):
            self.mouse_jitter_range = tuple(mouse_jitter_config)
        else:
            self.mouse_jitter_range = ANTI_BAN.mouse_jitter_range

        # Variance drift configuration
        self.variance_drift_enabled = config.get(
            "anti_ban.session_variance.drift_enabled",
            default=ANTI_BAN.enable_variance_drift,
        )

        # Initialize session
        self._initialize_session()

        logger.info(
            f"AntiBanService initialized (enabled={self.enabled}, "
            f"breaks={self.break_scheduler.enabled}, "
            f"micro_breaks={self.micro_breaks_enabled}, "
            f"session_variance={self.session_variance_enabled})"
        )

    def _initialize_session(self):
        """Initialize session-specific variance multipliers and break schedule."""
        if self.session_variance_enabled:
            timing_range = self.config.get(
                "anti_ban.session_variance.timing_multiplier",
                default=ANTI_BAN.timing_variance_range,
            )
            if isinstance(timing_range, (list, tuple)) and len(timing_range) == 2:
                self.session.timing_variance = random.uniform(
                    timing_range[0], timing_range[1]
                )

            mouse_speed_range = self.config.get(
                "anti_ban.session_variance.mouse_speed_multiplier",
                default=getattr(ANTI_BAN, "mouse_speed_variance_range", (0.9, 1.1)),
            )
            if isinstance(mouse_speed_range, (list, tuple)) and len(mouse_speed_range) == 2:
                self.session.mouse_speed_variance = random.uniform(
                    mouse_speed_range[0], mouse_speed_range[1]
                )

        # Initialize drift tracking
        now = time.time()
        self.session.variance_last_drift_time = now
        self.session.variance_drift_interval = random.uniform(
            *ANTI_BAN.variance_drift_interval_range
        )

        # Generate break schedule (independent of session variance)
        self.break_scheduler.initialize_schedule(self.session)

        drift_status = "on" if self.variance_drift_enabled else "off"
        logger.info(
            f"Session initialized: timing_variance={self.session.timing_variance:.3f}, "
            f"mouse_speed_variance={self.session.mouse_speed_variance:.3f}, "
            f"drift={drift_status}"
        )

    def should_take_break(self) -> bool:
        """
        Check if it's time for a scheduled break.

        Returns:
            True if break should be taken now
        """
        if not self.enabled or not self.break_scheduler.enabled:
            return False

        return self.break_scheduler.is_break_time(self.session)

    def should_micro_break(self) -> bool:
        """
        Check if micro-break should occur (random chance).

        Returns:
            True if micro-break should happen
        """
        if not self.enabled or not self.micro_breaks_enabled:
            return False

        return random.random() < self.micro_break_chance

    def execute_break(self):
        """Execute a scheduled break using the current segment's duration."""
        if not self.enabled:
            return

        segment = self.break_scheduler._current_segment(self.session)
        duration = self.break_scheduler.get_current_break_duration(self.session)

        # Mark break start on the segment
        if segment is not None:
            segment.actual_break_start = time.time()

        logger.info("=" * 70)
        logger.info(
            f"TAKING SCHEDULED BREAK: {duration / 60:.1f} minutes"
        )
        if segment is not None:
            logger.info(f"  Pattern: {segment.pattern}")
            if segment.actual_play_start:
                actual_play = (time.time() - segment.actual_play_start) / 60
                logger.info(
                    f"  Played: {actual_play:.1f}m "
                    f"(scheduled: {segment.play_minutes:.0f}m)"
                )
        logger.info(
            f"  Session: {self.session.actions_performed} actions, "
            f"uptime {(time.time() - self.session.session_start_time) / 3600:.1f}h"
        )
        logger.info("=" * 70)

        time.sleep(duration)

        self.session.last_break_time = time.time()
        self.break_scheduler.advance_segment(self.session)
        self._reset_drift_after_break()

        logger.info("=" * 70)
        logger.info("BREAK COMPLETE, RESUMING")
        logger.info("=" * 70)

    def execute_micro_break(self):
        """Execute a short micro-break (0.5-2s)."""
        if not self.enabled or not self.micro_breaks_enabled:
            return

        duration = random.uniform(
            self.micro_break_duration_range[0], self.micro_break_duration_range[1]
        )

        logger.debug(f"Micro-break: {duration:.2f}s")
        time.sleep(duration)

    def get_timing_variance(self) -> float:
        """
        Get session timing multiplier (drifts over time with fatigue bias).

        Returns:
            Timing multiplier (0.85-1.15 range, drifts toward slower over session)
        """
        if not self.enabled or not self.session_variance_enabled:
            return 1.0
        self._maybe_drift()
        return self.session.timing_variance

    def get_mouse_speed_variance(self) -> float:
        """
        Get session mouse speed multiplier (drifts over time).

        Returns:
            Mouse speed multiplier (0.9-1.1 range)
        """
        if not self.enabled or not self.session_variance_enabled:
            return 1.0
        # Drift is handled by get_timing_variance / _maybe_drift;
        # no need to call again if both are read in the same tick.
        return self.session.mouse_speed_variance

    # ------------------------------------------------------------------ #
    #  Variance drift (random walk with fatigue bias)
    # ------------------------------------------------------------------ #

    def _maybe_drift(self) -> None:
        """Check if enough time has passed and apply one drift step."""
        if not self.variance_drift_enabled:
            return

        now = time.time()
        elapsed = now - self.session.variance_last_drift_time
        if elapsed < self.session.variance_drift_interval:
            return

        self._drift_variance()
        self.session.variance_last_drift_time = now
        # Randomize next drift interval
        self.session.variance_drift_interval = random.uniform(
            *ANTI_BAN.variance_drift_interval_range
        )

    def _drift_variance(self) -> None:
        """Apply one random-walk step to both variance multipliers."""
        session_minutes = (
            time.time() - self.session.session_start_time
        ) / 60.0

        # --- Timing variance drift ---
        # Fatigue bias: center drifts toward 1.0+bias over fatigue_ramp_minutes
        fatigue_bias = min(
            session_minutes / ANTI_BAN.fatigue_ramp_minutes, 1.0
        ) * ANTI_BAN.fatigue_max_bias
        fatigue_center = 1.0 + fatigue_bias

        # Gaussian random step
        step = random.gauss(0, ANTI_BAN.timing_drift_step_sigma)
        # Mean reversion toward fatigue-adjusted center
        pull = (
            (fatigue_center - self.session.timing_variance)
            * ANTI_BAN.drift_mean_reversion_strength
        )

        new_timing = self.session.timing_variance + step + pull
        lo, hi = ANTI_BAN.timing_variance_range
        self.session.timing_variance = max(lo, min(hi, new_timing))

        # --- Mouse speed variance drift ---
        # Mouse speed has no fatigue bias (center stays at 1.0)
        step_m = random.gauss(0, ANTI_BAN.mouse_drift_step_sigma)
        pull_m = (
            (1.0 - self.session.mouse_speed_variance)
            * ANTI_BAN.drift_mean_reversion_strength
        )

        new_mouse = self.session.mouse_speed_variance + step_m + pull_m
        lo_m, hi_m = ANTI_BAN.mouse_speed_variance_range
        self.session.mouse_speed_variance = max(lo_m, min(hi_m, new_mouse))

        logger.debug(
            f"Variance drift: timing={self.session.timing_variance:.3f} "
            f"(center={fatigue_center:.3f}, session={session_minutes:.0f}m), "
            f"mouse={self.session.mouse_speed_variance:.3f}"
        )

    def _reset_drift_after_break(self) -> None:
        """Pull variance multipliers back toward 1.0 after a break (refreshed)."""
        # Strong pull toward 1.0 but don't snap exactly
        self.session.timing_variance = (
            self.session.timing_variance * 0.3 + 1.0 * 0.7
        )
        self.session.mouse_speed_variance = (
            self.session.mouse_speed_variance * 0.3 + 1.0 * 0.7
        )
        self.session.variance_last_drift_time = time.time()
        logger.debug(
            f"Post-break variance reset: timing={self.session.timing_variance:.3f}, "
            f"mouse={self.session.mouse_speed_variance:.3f}"
        )

    def record_action(self, action_type: str):
        """
        Record an action for pattern detection.

        Args:
            action_type: Type of action performed (e.g., "attack", "loot", "bank")
        """
        if not self.enabled:
            return

        self.session.actions_performed += 1
        self.session.recent_actions.append(
            {"type": action_type, "timestamp": time.time()}
        )

    def should_idle_action(self) -> bool:
        """
        Check if an idle action should be performed.

        Returns:
            True if enough time has passed since last idle action
        """
        if not self.enabled or not self.idle_actions_enabled:
            return False

        elapsed = time.time() - self.session.last_idle_action_time
        return elapsed >= self.idle_action_interval

    def execute_idle_action(
        self,
        mouse: Optional["MouseService"] = None,
        actions: Optional["GameActions"] = None,
    ):
        """
        Perform a weighted-random idle action to simulate human AFK behaviour.

        Available actions (weights from config):
            mouse_jitter      (30%) — Small curved mouse movement
            camera_nudge       (25%) — Briefly rotate camera via arrow keys
            check_skills_tab   (20%) — Open skills tab, hover, return to inventory
            check_equipment_tab(15%) — Open equipment tab, hover, return to inventory
            mouse_off_game     (10%) — Move mouse to edge of window, pause, return

        Args:
            mouse: MouseService for movement actions
            actions: GameActions for tab-based actions
        """
        if not self.enabled or not self.idle_actions_enabled:
            return

        # Build available actions with their config weights
        action_names = [
            "mouse_jitter",
            "camera_nudge",
            "check_skills_tab",
            "check_equipment_tab",
            "mouse_off_game",
        ]
        weights = list(ANTI_BAN.idle_action_weights)

        # Filter out actions whose dependencies are missing
        available = []
        avail_weights = []
        for name, w in zip(action_names, weights):
            if name == "mouse_jitter" and mouse:
                available.append(name)
                avail_weights.append(w)
            elif name == "camera_nudge":
                # Keyboard is always available
                available.append(name)
                avail_weights.append(w)
            elif name in ("check_skills_tab", "check_equipment_tab") and actions:
                available.append(name)
                avail_weights.append(w)
            elif name == "mouse_off_game" and mouse:
                available.append(name)
                avail_weights.append(w)

        if not available:
            return

        chosen = random.choices(available, weights=avail_weights, k=1)[0]

        try:
            if chosen == "mouse_jitter":
                self._idle_mouse_jitter(mouse)
            elif chosen == "camera_nudge":
                self._idle_camera_nudge()
            elif chosen == "check_skills_tab" and actions:
                self._idle_check_tab(actions, "skills_tab")
            elif chosen == "check_equipment_tab" and actions:
                self._idle_check_tab(actions, "equipment_tab")
            elif chosen == "mouse_off_game" and mouse:
                self._idle_mouse_off_game(mouse)
        except Exception:
            logger.debug(f"Idle action '{chosen}' failed, ignoring", exc_info=True)

        self.session.last_idle_action_time = time.time()

    # ------------------------------------------------------------------ #
    #  Individual idle action implementations
    # ------------------------------------------------------------------ #

    def _idle_mouse_jitter(self, mouse: "MouseService") -> None:
        """Perform small curved mouse movement (5-25px)."""
        import pyautogui

        current_x, current_y = pyautogui.position()

        jitter_x = random.randint(
            self.mouse_jitter_range[0], self.mouse_jitter_range[1]
        )
        jitter_y = random.randint(
            self.mouse_jitter_range[0], self.mouse_jitter_range[1]
        )
        if random.random() < 0.5:
            jitter_x = -jitter_x
        if random.random() < 0.5:
            jitter_y = -jitter_y

        new_x = current_x + jitter_x
        new_y = current_y + jitter_y

        logger.debug(f"Idle: mouse jitter ({jitter_x}, {jitter_y})")
        mouse.move_to(new_x, new_y, style="curved")
        time.sleep(random.uniform(0.2, 0.8))

    def _idle_camera_nudge(self) -> None:
        """Briefly rotate camera via arrow keys, then rotate back."""
        from osrsbot.services.keyboard_service import KeyboardService

        kb = KeyboardService()
        direction = random.choice(["left", "right"])
        opposite = "right" if direction == "left" else "left"

        hold = random.uniform(*ANTI_BAN.camera_nudge_duration_range)
        pause = random.uniform(*ANTI_BAN.camera_nudge_pause_range)

        logger.debug(f"Idle: camera nudge {direction} ({hold:.1f}s)")
        kb.press_and_hold(direction, hold)
        time.sleep(pause)
        # Undo the rotation (approximately)
        kb.press_and_hold(opposite, hold * random.uniform(0.85, 1.15))

    def _idle_check_tab(
        self, actions: "GameActions", tab_name: str
    ) -> None:
        """Click a UI tab, hover briefly, then return to inventory."""
        logger.debug(f"Idle: checking {tab_name}")

        button_pos = actions.coord_resolver.resolve_ui_button(
            tab_name, force_detect=True
        )
        if not button_pos:
            logger.debug(f"Idle: {tab_name} button not found, skipping")
            return

        rel_x, rel_y = button_pos
        abs_x, abs_y = actions.coord_resolver.to_absolute(rel_x, rel_y)
        actions.mouse.click_at(
            abs_x, abs_y,
            speed_multiplier=actions.timing.get_mouse_speed_multiplier(),
        )

        # Hover for a moment (simulating reading)
        time.sleep(random.uniform(1.0, 3.0))

        # Return to inventory tab
        inv_pos = actions.coord_resolver.resolve_ui_button(
            "inventory_tab", force_detect=True
        )
        if inv_pos:
            inv_rel_x, inv_rel_y = inv_pos
            inv_abs_x, inv_abs_y = actions.coord_resolver.to_absolute(
                inv_rel_x, inv_rel_y
            )
            actions.mouse.click_at(
                inv_abs_x, inv_abs_y,
                speed_multiplier=actions.timing.get_mouse_speed_multiplier(),
            )

    def _idle_mouse_off_game(self, mouse: "MouseService") -> None:
        """Move mouse to edge of screen and back (simulating looking away)."""
        import pyautogui

        current_x, current_y = pyautogui.position()
        screen_w, screen_h = pyautogui.size()

        # Pick a random edge
        edge = random.choice(["right", "bottom"])
        if edge == "right":
            target_x = screen_w - random.randint(5, 30)
            target_y = current_y + random.randint(-100, 100)
        else:
            target_x = current_x + random.randint(-100, 100)
            target_y = screen_h - random.randint(5, 30)

        # Clamp
        target_x = max(0, min(screen_w - 1, target_x))
        target_y = max(0, min(screen_h - 1, target_y))

        logger.debug(f"Idle: mouse off-game to ({target_x}, {target_y})")
        mouse.move_to(target_x, target_y, style="curved")
        time.sleep(random.uniform(1.0, 4.0))
        # Move back
        mouse.move_to(current_x, current_y, style="curved")

    # ==================== ADVANCED ANTI-BAN METHODS (REUSABLE) ====================

    def get_rhythm_delay(self, action_index: int, base_delay: float) -> float:
        """
        Generate rhythm-varied delay for repetitive actions (dropping, banking).

        Models human click rhythm: slight acceleration in the middle of a
        sequence, occasional long pauses (checking phone, adjusting), and
        per-click gaussian jitter.

        Args:
            action_index: 0-based index within the current repetitive sequence
            base_delay: Base inter-action delay in seconds

        Returns:
            Adjusted delay in seconds (always >= base_delay * 0.5)
        """
        # Occasional longer pause (distracted)
        if random.random() < ANTI_BAN.rhythm_long_pause_chance:
            mult = random.uniform(*ANTI_BAN.rhythm_long_pause_multiplier)
            return base_delay * mult

        # Sine-wave rhythm: slow → fast → slow across the sequence
        amplitude = ANTI_BAN.rhythm_wave_amplitude
        phase = math.sin(action_index * 0.15) * amplitude

        # Per-click gaussian jitter
        jitter = random.gauss(0, base_delay * ANTI_BAN.rhythm_jitter_sigma)

        return max(base_delay * 0.5, base_delay * (1.0 - phase) + jitter)

    def get_human_action_variance(self, action_name: str = "action") -> float:
        """
        Generate realistic human timing variance for any timer-based action.

        IMPORTANT: Cannot perform actions early in OSRS - variance must be >= 0

        Args:
            action_name: Name of action (for logging)

        Returns:
            Variance in seconds to add to base duration (always >= 0)
        """
        roll = random.random()

        if roll < 0.20:  # 20% on-time (wider variance than bot)
            variance = random.uniform(0, 15)
            logger.debug(f"ANTI-BAN: {action_name} variance = {variance:.0f}s (on-time)")
        else:  # 80% late (distracted/forgot)
            variance = random.uniform(5, 60)
            logger.debug(f"ANTI-BAN: {action_name} variance = {variance:.0f}s (late)")

        return variance

    def should_miss_action(self, chance: float = 0.04) -> bool:
        """
        Random chance to completely miss an action (simulate stepping away).

        Args:
            chance: Probability of missing (default 4%)

        Returns:
            True if action should be missed
        """
        return random.random() < chance

    def get_missed_action_delay(self, min_delay: float = 90, max_delay: float = 180) -> float:
        """
        Delay for missed action (simulates AFK period).

        Args:
            min_delay: Minimum delay in seconds (default 90s)
            max_delay: Maximum delay in seconds (default 180s)

        Returns:
            Delay in seconds
        """
        return random.uniform(min_delay, max_delay)

    def initialize_attention_fatigue(self):
        """
        Initialize attention fatigue tracking.

        Should be called once when bot starts. Tracks session duration
        and zone-out periods for realistic attention degradation.
        """
        if not hasattr(self.session, 'attention_fatigue_start'):
            self.session.attention_fatigue_start = time.time()
            self.session.last_zone_out = time.time()
            logger.debug("ANTI-BAN: Attention fatigue initialized")

    def get_fatigue_multiplier(self) -> float:
        """
        Get reaction time multiplier based on session duration.

        Simulates human attention degradation:
        - Fresh (0-20min): 0.8-1.0 (faster reactions)
        - Medium (20-45min): 1.0-1.3 (normal to slower)
        - Tired (45min+): 1.2-1.8 (noticeably slower)

        Returns:
            Multiplier for reaction times (>1.0 = slower, <1.0 = faster)
        """
        self.initialize_attention_fatigue()
        session_minutes = (time.time() - self.session.attention_fatigue_start) / 60

        if session_minutes < 20:
            mult = random.uniform(0.8, 1.0)
        elif session_minutes < 45:
            mult = random.uniform(1.0, 1.3)
        else:
            mult = random.uniform(1.2, 1.8)

        logger.debug(f"ANTI-BAN: Fatigue multiplier = {mult:.2f}x (session: {session_minutes:.0f}m)")
        return mult

    def should_zone_out(self, min_interval_minutes: float = 10, chance_per_second: float = 0.0005) -> bool:
        """
        Check if should have attention lapse (30-90s AFK burst).

        Args:
            min_interval_minutes: Minimum time between zone-outs (default 10 min)
            chance_per_second: Probability per second (~3% per minute default)

        Returns:
            True if should zone out
        """
        self.initialize_attention_fatigue()
        time_since_last = (time.time() - self.session.last_zone_out) / 60

        if time_since_last < min_interval_minutes:
            return False

        # ~3% chance per minute (0.05% per second)
        if random.random() < chance_per_second:
            self.session.last_zone_out = time.time()
            logger.debug("ANTI-BAN: Zone-out triggered")
            return True
        return False

    def get_zone_out_duration(self, min_duration: float = 30, max_duration: float = 90) -> float:
        """
        Get random duration for zone-out / AFK burst.

        Args:
            min_duration: Minimum duration in seconds (default 30s)
            max_duration: Maximum duration in seconds (default 90s)

        Returns:
            Duration in seconds
        """
        return random.uniform(min_duration, max_duration)

    # ==================== SESSION STATISTICS ====================

    def get_session_stats(self) -> Dict:
        """
        Get current session statistics.

        Returns:
            Dictionary with session metrics
        """
        uptime = time.time() - self.session.session_start_time
        time_to_break = max(0, self.session.next_break_time - time.time())

        return {
            "uptime_seconds": uptime,
            "actions_performed": self.session.actions_performed,
            "time_to_break_seconds": time_to_break,
            "timing_variance": self.session.timing_variance,
            "mouse_speed_variance": self.session.mouse_speed_variance,
            "last_break_ago_seconds": time.time() - self.session.last_break_time,
        }
