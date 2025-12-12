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

import time
import random
import logging
from typing import Optional, Dict, List, TYPE_CHECKING
from dataclasses import dataclass, field
from collections import deque

from osrsbot.models.config import Config
from osrsbot.constants import ANTI_BAN

if TYPE_CHECKING:
    from osrsbot.services.mouse_service import MouseService
    from osrsbot.commands.game_actions import GameActions

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """Tracks current session metrics and behavioral variance."""

    session_start_time: float = field(default_factory=time.time)
    actions_performed: int = 0
    last_break_time: float = field(default_factory=time.time)
    next_break_time: float = 0.0
    last_idle_action_time: float = field(default_factory=time.time)

    # Session-specific multipliers (generated once per session)
    timing_variance: float = 1.0
    mouse_speed_variance: float = 1.0

    # Activity tracking for pattern detection
    recent_actions: deque = field(default_factory=lambda: deque(maxlen=10))


class BreakScheduler:
    """Manages scheduled break timing with randomization."""

    def __init__(self, config: Config):
        self.config = config
        self.enabled = config.get("anti_ban.breaks.enabled", default=ANTI_BAN.enable_breaks)

        # Get interval range from config
        interval_config = config.get("anti_ban.breaks.interval_seconds", default=None)
        if isinstance(interval_config, (list, tuple)) and len(interval_config) == 2:
            self.interval_min, self.interval_max = interval_config
        else:
            self.interval_min = ANTI_BAN.break_interval_range[0]
            self.interval_max = ANTI_BAN.break_interval_range[1]

        # Get duration range from config
        duration_config = config.get("anti_ban.breaks.duration_seconds", default=None)
        if isinstance(duration_config, (list, tuple)) and len(duration_config) == 2:
            self.duration_min, self.duration_max = duration_config
        else:
            self.duration_min = ANTI_BAN.break_duration_range[0]
            self.duration_max = ANTI_BAN.break_duration_range[1]

    def schedule_next_break(self) -> float:
        """
        Schedule the next break time.

        Returns:
            Unix timestamp when next break should occur
        """
        if not self.enabled:
            return time.time() + 999999  # Never break if disabled

        interval = random.uniform(self.interval_min, self.interval_max)
        next_break = time.time() + interval

        logger.debug(
            f"Next break scheduled in {interval/60:.1f} minutes "
            f"(at {time.strftime('%H:%M:%S', time.localtime(next_break))})"
        )
        return next_break

    def is_break_time(self, next_break_time: float) -> bool:
        """Check if it's time for a scheduled break."""
        if not self.enabled:
            return False
        return time.time() >= next_break_time

    def get_break_duration(self) -> float:
        """Get randomized break duration in seconds."""
        duration = random.uniform(self.duration_min, self.duration_max)
        logger.info(f"Break duration: {duration/60:.1f} minutes")
        return duration


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
            "anti_ban.micro_breaks.enabled",
            default=ANTI_BAN.enable_micro_breaks
        )
        self.session_variance_enabled = config.get(
            "anti_ban.session_variance.enabled",
            default=ANTI_BAN.enable_session_variance
        )
        self.idle_actions_enabled = config.get(
            "anti_ban.idle_actions.enabled",
            default=ANTI_BAN.enable_idle_actions
        )

        # Micro-break configuration
        self.micro_break_chance = config.get(
            "anti_ban.micro_breaks.chance",
            default=ANTI_BAN.micro_break_chance
        )
        micro_break_duration_config = config.get(
            "anti_ban.micro_breaks.duration_seconds",
            default=None
        )
        if isinstance(micro_break_duration_config, (list, tuple)) and len(micro_break_duration_config) == 2:
            self.micro_break_duration_range = tuple(micro_break_duration_config)
        else:
            self.micro_break_duration_range = ANTI_BAN.micro_break_duration_range

        # Idle action configuration
        self.idle_action_interval = config.get(
            "anti_ban.idle_actions.interval_seconds",
            default=ANTI_BAN.idle_action_interval
        )
        mouse_jitter_config = config.get(
            "anti_ban.idle_actions.mouse_jitter_pixels",
            default=None
        )
        if isinstance(mouse_jitter_config, (list, tuple)) and len(mouse_jitter_config) == 2:
            self.mouse_jitter_range = tuple(mouse_jitter_config)
        else:
            self.mouse_jitter_range = ANTI_BAN.mouse_jitter_range

        # Initialize session
        self._initialize_session()

        logger.info(
            f"AntiBanService initialized (enabled={self.enabled}, "
            f"breaks={self.break_scheduler.enabled}, "
            f"micro_breaks={self.micro_breaks_enabled}, "
            f"session_variance={self.session_variance_enabled})"
        )

    def _initialize_session(self):
        """Initialize session-specific variance multipliers."""
        if not self.session_variance_enabled:
            self.session.timing_variance = 1.0
            self.session.mouse_speed_variance = 1.0
            return

        # Get variance ranges from config
        timing_range = self.config.get(
            "anti_ban.session_variance.timing_multiplier",
            default=ANTI_BAN.timing_variance_range
        )
        if isinstance(timing_range, (list, tuple)) and len(timing_range) == 2:
            self.session.timing_variance = random.uniform(timing_range[0], timing_range[1])
        else:
            self.session.timing_variance = 1.0

        mouse_speed_range = self.config.get(
            "anti_ban.session_variance.mouse_speed_multiplier",
            default=getattr(ANTI_BAN, 'mouse_speed_variance_range', (0.9, 1.1))
        )
        if isinstance(mouse_speed_range, (list, tuple)) and len(mouse_speed_range) == 2:
            self.session.mouse_speed_variance = random.uniform(mouse_speed_range[0], mouse_speed_range[1])
        else:
            self.session.mouse_speed_variance = 1.0

        # Schedule first break
        self.session.next_break_time = self.break_scheduler.schedule_next_break()

        logger.info(
            f"Session initialized: timing_variance={self.session.timing_variance:.3f}, "
            f"mouse_speed_variance={self.session.mouse_speed_variance:.3f}"
        )

    def should_take_break(self) -> bool:
        """
        Check if it's time for a scheduled break.

        Returns:
            True if break should be taken now
        """
        if not self.enabled or not self.break_scheduler.enabled:
            return False

        return self.break_scheduler.is_break_time(self.session.next_break_time)

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
        """Execute a scheduled break with logging."""
        if not self.enabled:
            return

        duration = self.break_scheduler.get_break_duration()

        logger.info(f"===== TAKING SCHEDULED BREAK ({duration/60:.1f} minutes) =====")
        logger.info(
            f"Session stats: {self.session.actions_performed} actions performed, "
            f"uptime: {(time.time() - self.session.session_start_time)/3600:.1f} hours"
        )

        time.sleep(duration)

        self.session.last_break_time = time.time()
        self.session.next_break_time = self.break_scheduler.schedule_next_break()

        logger.info("===== BREAK COMPLETE, RESUMING =====")

    def execute_micro_break(self):
        """Execute a short micro-break (0.5-2s)."""
        if not self.enabled or not self.micro_breaks_enabled:
            return

        duration = random.uniform(
            self.micro_break_duration_range[0],
            self.micro_break_duration_range[1]
        )

        logger.debug(f"Micro-break: {duration:.2f}s")
        time.sleep(duration)

    def get_timing_variance(self) -> float:
        """
        Get session-specific timing multiplier.

        Returns:
            Timing multiplier (0.85-1.15, typically)
        """
        if not self.enabled or not self.session_variance_enabled:
            return 1.0
        return self.session.timing_variance

    def get_mouse_speed_variance(self) -> float:
        """
        Get session-specific mouse speed multiplier.

        Returns:
            Mouse speed multiplier (0.9-1.1, typically)
        """
        if not self.enabled or not self.session_variance_enabled:
            return 1.0
        return self.session.mouse_speed_variance

    def record_action(self, action_type: str):
        """
        Record an action for pattern detection.

        Args:
            action_type: Type of action performed (e.g., "attack", "loot", "bank")
        """
        if not self.enabled:
            return

        self.session.actions_performed += 1
        self.session.recent_actions.append({
            "type": action_type,
            "timestamp": time.time()
        })

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
        mouse: Optional['MouseService'] = None,
        actions: Optional['GameActions'] = None
    ):
        """
        Perform a random idle action (mouse jitter or stats check).

        Args:
            mouse: MouseService for jitter movements
            actions: GameActions for stats checking
        """
        if not self.enabled or not self.idle_actions_enabled:
            return

        # Choose random idle action
        available_actions = []
        if mouse:
            available_actions.append("mouse_jitter")
        if actions:
            available_actions.append("stats_check")

        if not available_actions:
            return

        action = random.choice(available_actions)

        if action == "mouse_jitter" and mouse:
            self._mouse_jitter(mouse)
        elif action == "stats_check" and actions:
            self._stats_check(actions)

        self.session.last_idle_action_time = time.time()

    def _mouse_jitter(self, mouse: 'MouseService'):
        """Perform small random mouse movements."""
        import pyautogui

        current_x, current_y = pyautogui.position()

        # Random jitter
        jitter_x = random.randint(self.mouse_jitter_range[0], self.mouse_jitter_range[1])
        jitter_y = random.randint(self.mouse_jitter_range[0], self.mouse_jitter_range[1])

        # Random direction
        if random.random() < 0.5:
            jitter_x = -jitter_x
        if random.random() < 0.5:
            jitter_y = -jitter_y

        new_x = current_x + jitter_x
        new_y = current_y + jitter_y

        logger.debug(f"Idle action: mouse jitter ({jitter_x}, {jitter_y})")
        mouse.move_to(new_x, new_y, move_style="curved")

        # Small pause
        time.sleep(random.uniform(0.2, 0.8))

    def _stats_check(self, actions: 'GameActions'):
        """Simulate checking stats (placeholder for now)."""
        logger.debug("Idle action: stats check (simulated)")
        # Could be implemented with UI button clicks if needed
        time.sleep(random.uniform(0.5, 1.5))

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
            "last_break_ago_seconds": time.time() - self.session.last_break_time
        }
