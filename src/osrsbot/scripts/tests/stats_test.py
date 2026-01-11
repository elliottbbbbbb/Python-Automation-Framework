"""
Stats Test Bot - Tests _get_all_stats() functionality

A simple bot that continuously reads all player stats (HP, Prayer, Run Energy, Special Attack)
and displays them in real-time. This tests the stat reading functionality with the game interface.

Requirements:
- OSRS client must be open and visible
- Player must be logged in
- Game interface must be accessible

Usage:
- The bot will read stats every 2 seconds
- Press Ctrl+C to stop
"""

import logging
import time
from enum import Enum
from typing import Dict, Optional

from osrsbot.core.state_helpers import build_metadata_dict
from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_types import (
    StateExecutionContext,
    StateMetadata,
    StateResult,
    StateTransition,
)

logger = logging.getLogger(__name__)


class StatsTestStates(Enum):
    """States for stats test bot."""

    IDLE = "idle"
    READING_STATS = "reading_stats"
    COMPLETE = "complete"


class StatsTestBot(StateMachineBot):
    """
    Test bot that reads all player stats using _get_all_stats() pattern.

    Tests HP, Prayer, Run Energy, and Special Attack reading.
    """

    def __init__(self, *args, **kwargs):
        """Initialize stats test bot."""
        super().__init__(*args, **kwargs, script_name="Stats Test Bot")

        # Tracking
        self.total_reads = 0
        self.successful_reads = {
            'hp': 0,
            'prayer': 0,
            'run': 0,
            'spec': 0
        }
        self.failed_reads = {
            'hp': 0,
            'prayer': 0,
            'run': 0,
            'spec': 0
        }

    # ==================== State Machine Configuration ====================

    def define_states(self) -> type[Enum]:
        """Define states for this bot."""
        return StatsTestStates

    def define_state_metadata(self) -> Dict[Enum, StateMetadata]:
        """Define metadata for each state."""
        return build_metadata_dict(
            StatsTestStates,
            {
                StatsTestStates.IDLE: {
                    "name": "Idle",
                    "description": "Initialize stats test",
                    "max_retries": 1,
                },
                StatsTestStates.READING_STATS: {
                    "name": "Reading Stats",
                    "description": "Read all player stats continuously",
                    "max_retries": 999999,  # Read indefinitely
                    "timeout": 3600.0,  # 1 hour timeout
                },
                StatsTestStates.COMPLETE: {
                    "name": "Complete",
                    "description": "Show final statistics",
                    "max_retries": 1,
                },
            },
        )

    def define_transitions(self) -> list[StateTransition]:
        """Define allowed state transitions."""
        return [
            StateTransition(StatsTestStates.IDLE, StatsTestStates.READING_STATS),
            StateTransition(StatsTestStates.READING_STATS, StatsTestStates.COMPLETE),
        ]

    def get_initial_state(self) -> Enum:
        """Get initial state."""
        return StatsTestStates.IDLE

    # ==================== Helper Methods ====================

    def _get_all_stats(self) -> dict[str, Optional[int]]:
        """
        Get all player stats (HP, prayer, run energy, special attack) using template OCR.

        Returns:
            Dictionary with keys: 'hp', 'prayer', 'run', 'spec'
            Values are integers or None if detection fails

        Example:
            {'hp': 99, 'prayer': 70, 'run': 100, 'spec': 55}
        """
        stats = {}

        # Get HP
        stats['hp'] = self.state.get_hp(force=True)

        # Get Prayer
        stats['prayer'] = self.state.get_prayer(force=True)

        # Get Run Energy
        stats['run'] = self.state.get_run_energy(force=True)

        # Get Special Attack
        stats['spec'] = self.state.get_special_attack_percentage(force=True)

        return stats

    # ==================== State Handlers ====================

    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        """
        Handle IDLE state - initialize tracking.

        Returns:
            StateResult.SUCCESS to start reading stats
        """
        logger.info("=" * 70)
        logger.info("STATS TEST BOT - Testing _get_all_stats() functionality")
        logger.info("=" * 70)
        logger.info("Requirements:")
        logger.info("  - OSRS client must be open and visible")
        logger.info("  - Player must be logged in")
        logger.info("  - Game interface must be accessible")
        logger.info("")
        logger.info("This bot will read stats every 2 seconds.")
        logger.info("Press Ctrl+C to stop.")
        logger.info("=" * 70)
        logger.info("")

        # Reset tracking
        self.total_reads = 0
        for stat_name in ['hp', 'prayer', 'run', 'spec']:
            self.successful_reads[stat_name] = 0
            self.failed_reads[stat_name] = 0

        return StateResult.SUCCESS

    def _handle_reading_stats(self, context: StateExecutionContext) -> StateResult:
        """
        Handle READING_STATS state - read all stats continuously.

        Returns:
            StateResult.RETRY to continue reading
            StateResult.SUCCESS when done (user stops)
        """
        try:
            self.total_reads += 1

            # Read all stats using _get_all_stats()
            stats = self._get_all_stats()

            # Update tracking
            for stat_name, stat_value in stats.items():
                if stat_value is not None:
                    self.successful_reads[stat_name] += 1
                else:
                    self.failed_reads[stat_name] += 1

            # Format output
            hp_str = f"{stats['hp']:>3}" if stats['hp'] is not None else " XX"
            prayer_str = f"{stats['prayer']:>3}" if stats['prayer'] is not None else " XX"
            run_str = f"{stats['run']:>3}" if stats['run'] is not None else " XX"
            spec_str = f"{stats['spec']:>3}" if stats['spec'] is not None else " XX"

            # Display current stats
            logger.info(
                f"[{self.total_reads:3d}] HP: {hp_str} | Prayer: {prayer_str} | "
                f"Run: {run_str} | Spec: {spec_str}"
            )

            # Show statistics every 10 reads
            if self.total_reads % 10 == 0:
                self._show_statistics()

            # Wait before next read (2 seconds)
            time.sleep(2.0)

            return StateResult.RETRY

        except KeyboardInterrupt:
            logger.info("\n\nUser stopped test, showing final statistics...")
            return StateResult.SUCCESS
        except Exception as e:
            logger.error(f"Error reading stats: {e}")
            import traceback
            traceback.print_exc()
            return StateResult.RETRY

    def _handle_complete(self, context: StateExecutionContext) -> StateResult:
        """
        Handle COMPLETE state - show final statistics.

        Returns:
            StateResult.SUCCESS
        """
        self._show_statistics(final=True)
        return StateResult.SUCCESS

    def _show_statistics(self, final: bool = False) -> None:
        """
        Display statistics about stat reading success rates.

        Args:
            final: If True, show final statistics with more detail
        """
        if self.total_reads == 0:
            return

        prefix = "\n" + "=" * 80 + "\n"
        title = "FINAL STATISTICS" if final else f"STATISTICS (after {self.total_reads} reads)"
        suffix = "=" * 80 + "\n"

        logger.info(prefix + title)
        logger.info("-" * 80)

        for stat_name in ['hp', 'prayer', 'run', 'spec']:
            success_count = self.successful_reads[stat_name]
            fail_count = self.failed_reads[stat_name]
            success_rate = (100 * success_count / self.total_reads) if self.total_reads > 0 else 0

            logger.info(
                f"{stat_name.upper():7} - Success: {success_count:3}/{self.total_reads} "
                f"({success_rate:5.1f}%) | Failed: {fail_count:3}"
            )

        # Overall success rate
        total_successes = sum(self.successful_reads.values())
        total_possible = self.total_reads * 4  # 4 stats per read
        overall_rate = (100 * total_successes / total_possible) if total_possible > 0 else 0

        logger.info("-" * 80)
        logger.info(
            f"OVERALL - {total_successes}/{total_possible} "
            f"({overall_rate:.1f}% success rate)"
        )
        logger.info(suffix)
