"""
Stats Reader Test - Tests the _get_all_stats() functionality.

A simple test bot that continuously reads HP, Prayer, Run Energy, and Special Attack
using the same method implemented in NMZ bot. Shows real-time statistics to verify
the functionality works correctly.
"""

import logging
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
    """States for stats reader test bot."""

    IDLE = "idle"
    READING = "reading"
    COMPLETE = "complete"


class StatsReaderTestBot(StateMachineBot):
    """
    Test bot that reads all stats using _get_all_stats() method.

    Tests the same functionality used in NMZ bot to ensure it works correctly.
    """

    def __init__(self, *args, **kwargs):
        """Initialize stats reader test bot."""
        super().__init__(*args, **kwargs, script_name="Stats Reader Test")

        self.total_reads = 0
        self.successful_reads = 0
        self.failed_reads = 0

        # Track success rate per stat
        self.stat_success = {
            "hp": 0,
            "prayer": 0,
            "run": 0,
            "spec": 0,
        }

    # ==================== Helper Method (Same as NMZ) ====================

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
                    "description": "Initialize stats reader test",
                    "max_retries": 1,
                },
                StatsTestStates.READING: {
                    "name": "Reading Stats",
                    "description": "Continuously read all stats",
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
            StateTransition(StatsTestStates.IDLE, StatsTestStates.READING),
            StateTransition(StatsTestStates.READING, StatsTestStates.COMPLETE),
        ]

    def get_initial_state(self) -> Enum:
        """Get initial state."""
        return StatsTestStates.IDLE

    # ==================== State Handlers ====================

    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        """
        Handle IDLE state - initialize test.

        Returns:
            StateResult.SUCCESS to start reading
        """
        logger.info("=" * 80)
        logger.info("STATS READER TEST - Testing _get_all_stats() Method")
        logger.info("=" * 80)
        logger.info("This test reads: HP, Prayer, Run Energy, Special Attack")
        logger.info("Uses the same _get_all_stats() method as NMZ bot")
        logger.info("Statistics shown every 10 reads")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 80)
        logger.info("")

        # Reset counters
        self.total_reads = 0
        self.successful_reads = 0
        self.failed_reads = 0
        for key in self.stat_success:
            self.stat_success[key] = 0

        return StateResult.SUCCESS

    def _handle_reading(self, context: StateExecutionContext) -> StateResult:
        """
        Handle READING state - read all stats using _get_all_stats().

        Returns:
            StateResult.RETRY to continue reading
            StateResult.SUCCESS when done (user stops)
        """
        try:
            self.total_reads += 1

            # Call _get_all_stats() method (same as NMZ bot)
            stats = self._get_all_stats()

            # Track success for each stat
            all_successful = True
            for stat_name, value in stats.items():
                if value is not None:
                    self.stat_success[stat_name] += 1
                else:
                    all_successful = False

            if all_successful:
                self.successful_reads += 1
            else:
                self.failed_reads += 1

            # Display current reading
            hp = stats['hp'] or '??'
            prayer = stats['prayer'] or '??'
            run = stats['run'] or '??'
            spec = stats['spec'] or '??'

            # Color-code the output
            status = "✓ SUCCESS" if all_successful else "✗ PARTIAL"

            logger.info(
                f"[{self.total_reads:3d}] {status:10} - "
                f"HP: {hp:>3}  |  "
                f"Prayer: {prayer:>3}  |  "
                f"Run: {run:>3}  |  "
                f"Spec: {spec:>3}"
            )

            # Show statistics every 10 reads
            if self.total_reads % 10 == 0:
                logger.info("\n" + "=" * 80)
                logger.info(f"STATISTICS (after {self.total_reads} reads)")
                logger.info("-" * 80)

                success_rate = (100 * self.successful_reads / self.total_reads) if self.total_reads > 0 else 0
                logger.info(f"Complete Reads: {self.successful_reads}/{self.total_reads} ({success_rate:.1f}%)")
                logger.info(f"Partial Reads:  {self.failed_reads}/{self.total_reads}")
                logger.info("")

                logger.info("Per-Stat Success Rates:")
                for stat_name in ["hp", "prayer", "run", "spec"]:
                    success_count = self.stat_success[stat_name]
                    rate = (100 * success_count / self.total_reads) if self.total_reads > 0 else 0
                    logger.info(f"  {stat_name.upper():8} - {success_count:3}/{self.total_reads} ({rate:5.1f}%)")

                logger.info("=" * 80 + "\n")

            # Wait before next read
            self.actions.wait("short")
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
        logger.info("\n" + "=" * 80)
        logger.info("FINAL TEST RESULTS")
        logger.info("=" * 80)
        logger.info(f"Total Reads: {self.total_reads}")
        logger.info("")

        if self.total_reads > 0:
            success_rate = 100 * self.successful_reads / self.total_reads
            fail_rate = 100 * self.failed_reads / self.total_reads

            logger.info("Overall Performance:")
            logger.info(f"  Complete Reads: {self.successful_reads:3}/{self.total_reads} ({success_rate:5.1f}%)")
            logger.info(f"  Partial Reads:  {self.failed_reads:3}/{self.total_reads} ({fail_rate:5.1f}%)")
            logger.info("")

            logger.info("Per-Stat Success Rates:")
            for stat_name in ["hp", "prayer", "run", "spec"]:
                success_count = self.stat_success[stat_name]
                rate = 100 * success_count / self.total_reads
                logger.info(f"  {stat_name.upper():8} - {success_count:3}/{self.total_reads} ({rate:5.1f}%)")
            logger.info("")

            # Verdict
            if success_rate >= 95:
                logger.info("✓ TEST PASSED - _get_all_stats() is working excellently!")
            elif success_rate >= 80:
                logger.info("⚠ TEST WARNING - _get_all_stats() working but some detection issues")
            else:
                logger.info("✗ TEST FAILED - _get_all_stats() has significant detection problems")

        logger.info("=" * 80)
        return StateResult.SUCCESS
