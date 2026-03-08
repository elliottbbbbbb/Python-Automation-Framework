"""
Debug UI - Real-time terminal interface for bot state monitoring.

Provides live-updating terminal display showing:
- Current state and progress
- Recent events/actions
- Session statistics
- Anti-ban status

Uses rich.live for non-blocking terminal updates.
"""

import logging
import threading
import time
from typing import TYPE_CHECKING, Optional

from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

if TYPE_CHECKING:
    from osrsbot.core.state_machine_bot import StateMachineBot

logger = logging.getLogger(__name__)


class DebugUI:
    """
    Real-time terminal debug UI for bot state monitoring.

    Uses rich.live for non-blocking terminal updates showing:
    - Current state and progress
    - Recent events/actions
    - Session statistics
    - Anti-ban status
    """

    def __init__(self, bot_instance: "StateMachineBot", update_interval: float = 0.5):
        """
        Initialize debug UI.

        Args:
            bot_instance: StateMachineBot instance to monitor
            update_interval: UI refresh rate in seconds (default 0.5)
        """
        self.bot = bot_instance
        self.update_interval = update_interval
        self.enabled = False
        self.live: Optional[Live] = None
        self.update_thread: Optional[threading.Thread] = None
        self._original_handlers = []

    def start(self):
        if self.enabled:
            logger.warning("Debug UI already running")
            return

        # Redirect logging to file to prevent console interference
        self._redirect_logging_to_file()

        self.enabled = True
        self.live = Live(self._build_layout(), refresh_per_second=2, screen=True)

        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)

        self.live.start()
        self.update_thread.start()

        logger.info("Debug UI started")

    def stop(self):
        if not self.enabled:
            return

        self.enabled = False

        # Wait for update thread to finish
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1.0)

        if self.live:
            self.live.stop()

        # Restore logging to console
        self._restore_logging()

        logger.info("Debug UI stopped")

    def _build_layout(self) -> Layout:
        layout = Layout()

        layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        layout["body"].split_row(Layout(name="left"), Layout(name="right"))

        layout["left"].split(
            Layout(name="current_state", ratio=2), Layout(name="events", ratio=3)
        )

        layout["right"].split(
            Layout(name="stats", ratio=1), Layout(name="anti_ban", ratio=1)
        )

        layout["header"].update(Panel("OSRS Bot Debug UI", style="bold cyan"))
        layout["current_state"].update(self._render_current_state())
        layout["events"].update(self._render_recent_events())
        layout["stats"].update(self._render_session_stats())
        layout["anti_ban"].update(self._render_anti_ban_status())
        layout["footer"].update(Panel("Press Ctrl+C to stop bot", style="dim"))

        return layout

    def _render_current_state(self) -> Panel:
        """Render current state panel with progress and status."""
        if not hasattr(self.bot, "_current_state") or self.bot._current_state is None:
            return Panel(
                "Bot not started",
                style="dim",
                title="Current State",
                border_style="cyan",
            )

        state = self.bot.get_current_state()
        retry_count = self.bot.get_retry_count(state)
        metadata = self.bot._state_metadata.get(state)

        status_color = "yellow" if retry_count > 0 else "green"
        status_text = Text()
        status_text.append("State: ", style="bold")
        status_text.append(f"{state.name}", style=f"bold {status_color}")

        if metadata:
            status_text.append(
                f" ({retry_count}/{metadata.max_retries} retries)", style="dim"
            )

        if metadata and metadata.description:
            status_text.append(f"\n{metadata.description}", style="dim italic")

        if hasattr(self.bot, "state"):
            try:
                hp = self.bot.state.get_hp()
                combat = self.bot.state.is_in_combat()

                status_text.append("\n\n")
                status_text.append(f"HP: {hp if hp else '?'}/31  ", style="cyan")
                status_text.append(
                    f"Combat: {'✓' if combat else '✗'}  ",
                    style="green" if combat else "red",
                )

                # Inventory status
                if hasattr(self.bot.state, "inventory"):
                    inv_full = self.bot.state.inventory.is_full()
                    filled = self.bot.state.inventory.get_filled_slot_count()
                    status_text.append(
                        f"Inventory: {filled}/28",
                        style="yellow" if inv_full else "white",
                    )
            except Exception as e:
                logger.debug(f"Error reading game state: {e}")

        return Panel(status_text, title="Current State", border_style="cyan")

    def _render_recent_events(self) -> Panel:
        """Render last 10 events from state history and anti-ban actions."""
        events = []

        try:
            history = self.bot.get_state_history(10)

            for entry in reversed(history):
                # Format timestamp
                timestamp = time.strftime("%H:%M:%S", time.localtime(entry.timestamp))

                # Color based on result
                if entry.succeeded:
                    symbol = "✓"
                    color = "green"
                elif entry.failed:
                    symbol = "✗"
                    color = "red"
                else:
                    symbol = "↻"
                    color = "yellow"

                events.append(
                    f"[{color}]{symbol}[/{color}] "
                    f"[dim]{timestamp}[/dim] "
                    f"{entry.state.name} "
                    f"[dim]({entry.duration:.1f}s)[/dim]"
                )

                if entry.failed and entry.error_message:
                    events.append(f"  [red]↳ {entry.error_message}[/red]")

            if hasattr(self.bot, "actions") and self.bot.actions.anti_ban:
                recent_actions = list(self.bot.actions.anti_ban.session.recent_actions)
                for action in reversed(recent_actions[-5:]):
                    timestamp = time.strftime(
                        "%H:%M:%S", time.localtime(action["timestamp"])
                    )
                    events.append(
                        f"[cyan]↻[/cyan] "
                        f"[dim]{timestamp}[/dim] "
                        f"[cyan]{action['type']}[/cyan]"
                    )
        except Exception as e:
            events.append(f"[red]Error loading events: {e}[/red]")
            logger.debug(f"Error rendering events: {e}")

        # Limit to last 10 and join
        events_text = "\n".join(events[:10]) if events else "[dim]No events yet[/dim]"

        return Panel(events_text, title="Recent Events (Last 10)", border_style="blue")

    def _render_session_stats(self) -> Panel:
        """Render session statistics panel."""
        stats_text = Text()

        try:
            if hasattr(self.bot, "actions") and self.bot.actions.anti_ban:
                stats = self.bot.actions.anti_ban.get_session_stats()

                # Format uptime
                uptime = int(stats["uptime_seconds"])
                hours, remainder = divmod(uptime, 3600)
                minutes, seconds = divmod(remainder, 60)
                uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                stats_text.append("Uptime: ", style="bold")
                stats_text.append(f"{uptime_str}\n", style="cyan")

                stats_text.append("Actions: ", style="bold")
                stats_text.append(f"{stats['actions_performed']}\n", style="white")

                # State history count
                if hasattr(self.bot, "_state_history"):
                    stats_text.append("States: ", style="bold")
                    stats_text.append(
                        f"{len(self.bot._state_history)}\n", style="white"
                    )
            else:
                stats_text.append("[dim]No session stats available[/dim]")

        except Exception as e:
            stats_text.append(f"[red]Error: {e}[/red]")
            logger.debug(f"Error rendering stats: {e}")

        return Panel(stats_text, title="Session Stats", border_style="green")

    def _render_anti_ban_status(self) -> Panel:
        """Render anti-ban status panel."""
        status_text = Text()

        try:
            if hasattr(self.bot, "actions") and self.bot.actions.anti_ban:
                stats = self.bot.actions.anti_ban.get_session_stats()

                # Next break
                time_to_break = int(stats["time_to_break_seconds"])
                break_mins, break_secs = divmod(time_to_break, 60)

                status_text.append("Next Break: ", style="bold")
                status_text.append(f"{break_mins}m {break_secs}s\n", style="yellow")

                # Timing variance
                status_text.append("Timing: ", style="bold")
                status_text.append(f"{stats['timing_variance']:.2f}x\n", style="white")

                # Mouse speed variance
                status_text.append("Mouse Speed: ", style="bold")
                status_text.append(
                    f"{stats['mouse_speed_variance']:.2f}x\n", style="white"
                )

                # Status indicator
                status_text.append("\n", style="white")
                status_text.append("Anti-Ban: ", style="bold")
                status_text.append("✓ Active", style="green")
            else:
                status_text.append("[yellow]Anti-ban not available[/yellow]")

        except Exception as e:
            status_text.append(f"[red]Error: {e}[/red]")
            logger.debug(f"Error rendering anti-ban status: {e}")

        return Panel(status_text, title="Anti-Ban Status", border_style="magenta")

    def _update_loop(self):
        """Continuously update UI at specified interval."""
        while self.enabled:
            try:
                if self.live:
                    self.live.update(self._build_layout())
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Debug UI update error: {e}")
                time.sleep(1.0)

    def _redirect_logging_to_file(self):
        """Redirect all logging to file to prevent console interference."""
        import logging as log_module

        root_logger = log_module.getLogger()
        self._original_handlers = root_logger.handlers.copy()

        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        file_handler = log_module.FileHandler("bot_debug.log", mode="a")
        file_handler.setLevel(log_module.DEBUG)
        formatter = log_module.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        logger.info("Logging redirected to bot_debug.log (Debug UI active)")

    def _restore_logging(self):
        """Restore original logging handlers."""
        import logging as log_module

        root_logger = log_module.getLogger()

        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        for handler in self._original_handlers:
            root_logger.addHandler(handler)

        logger.info("Logging restored to console")
