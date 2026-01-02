"""
Stats Tracker Bot - Tracks HP, Prayer, Run Energy, and Special Attack using both OCR methods.

A simple bot that continuously monitors game stats and compares Tesseract OCR vs Template Matching OCR.
Shows real-time statistics and accuracy comparison.
"""

import logging
from enum import Enum
from typing import Dict, List

from osrsbot.core.state_helpers import build_metadata_dict
from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_types import (
    StateExecutionContext,
    StateMetadata,
    StateResult,
    StateTransition,
)

logger = logging.getLogger(__name__)


class HPTrackerStates(Enum):
    """States for stats tracking bot."""

    IDLE = "idle"
    TRACKING = "tracking"
    COMPLETE = "complete"


class HPTrackerBot(StateMachineBot):
    """
    Simple bot that tracks HP, Prayer, Run Energy, and Special Attack using both OCR methods.

    Compares Tesseract OCR vs Template Matching OCR in real-time.
    Shows statistics every 10 reads.
    """

    def __init__(self, *args, **kwargs):
        """Initialize stats tracker bot."""
        super().__init__(*args, **kwargs, script_name="Stats Tracker Bot")

        # Tracking stats for each stat type
        self.total_reads = 0

        # Per-stat tracking
        self.stats = {
            "hp": {
                "tess_success": 0,
                "temp_success": 0,
                "matches": 0,
                "mismatches": 0,
                "tess_fail": 0,
                "temp_fail": 0,
                "recent_tess": [],
                "recent_temp": [],
            },
            "prayer": {
                "tess_success": 0,
                "temp_success": 0,
                "matches": 0,
                "mismatches": 0,
                "tess_fail": 0,
                "temp_fail": 0,
                "recent_tess": [],
                "recent_temp": [],
            },
            "run": {
                "tess_success": 0,
                "temp_success": 0,
                "matches": 0,
                "mismatches": 0,
                "tess_fail": 0,
                "temp_fail": 0,
                "recent_tess": [],
                "recent_temp": [],
            },
            "spec": {
                "tess_success": 0,
                "temp_success": 0,
                "matches": 0,
                "mismatches": 0,
                "tess_fail": 0,
                "temp_fail": 0,
                "recent_tess": [],
                "recent_temp": [],
            },
        }

    # ==================== State Machine Configuration ====================

    def define_states(self) -> type[Enum]:
        """Define states for this bot."""
        return HPTrackerStates

    def define_state_metadata(self) -> Dict[Enum, StateMetadata]:
        """Define metadata for each state."""
        return build_metadata_dict(
            HPTrackerStates,
            {
                HPTrackerStates.IDLE: {
                    "name": "Idle",
                    "description": "Initialize HP tracking",
                    "max_retries": 1,
                },
                HPTrackerStates.TRACKING: {
                    "name": "Tracking HP",
                    "description": "Monitor HP with both OCR methods",
                    "max_retries": 999999,  # Track indefinitely
                    "timeout": 3600.0,  # 1 hour timeout per state execution
                },
                HPTrackerStates.COMPLETE: {
                    "name": "Complete",
                    "description": "Show final statistics",
                    "max_retries": 1,
                },
            },
        )

    def define_transitions(self) -> List[StateTransition]:
        """Define allowed state transitions."""
        return [
            StateTransition(HPTrackerStates.IDLE, HPTrackerStates.TRACKING),
            StateTransition(HPTrackerStates.TRACKING, HPTrackerStates.COMPLETE),
        ]

    def get_initial_state(self) -> Enum:
        """Get initial state."""
        return HPTrackerStates.IDLE

    # ==================== State Handlers ====================

    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        """
        Handle IDLE state - initialize tracking.

        Returns:
            StateResult.SUCCESS to start tracking
        """
        logger.info("=" * 70)
        logger.info("STATS TRACKER BOT - Template Matching OCR")
        logger.info("=" * 70)
        logger.info("Tracks: HP, Prayer, Run Energy, Special Attack")
        logger.info("Statistics shown every 10 reads.")
        logger.info("Press Ctrl+C to stop.")
        logger.info("=" * 70)
        logger.info("")

        # Reset all stats
        self.total_reads = 0
        for stat in self.stats.values():
            stat["temp_success"] = 0
            stat["temp_fail"] = 0
            stat["recent_temp"] = []

        return StateResult.SUCCESS

    def _handle_tracking(self, context: StateExecutionContext) -> StateResult:
        """
        Handle TRACKING state - read all stats with both methods and compare.

        Returns:
            StateResult.RETRY to continue tracking
            StateResult.SUCCESS when done (user stops)
        """
        try:
            import cv2
            import numpy as np

            from osrsbot.services.template_ocr_service import (
                ORB_GREEN,
                ORB_RED,
                get_template_ocr_service,
            )

            template_ocr = get_template_ocr_service()
            self.total_reads += 1

            # Track all stats
            regions = {
                "hp": ("hp_region", self.state.get_hp, ORB_GREEN, ORB_RED),
                "prayer": ("prayer_region", self.state.get_prayer, ORB_GREEN, ORB_RED),
                "run": ("run_energy_region", None, ORB_GREEN, ORB_RED),
                "spec": ("special_attack_region", None, ORB_GREEN, ORB_RED),
            }

            results = {}
            for stat_name, (region_key, tess_func, *colors) in regions.items():
                # Tesseract read (if available)
                tess_val = tess_func(force=True) if tess_func else None

                # Template matching read using ScreenService
                temp_val = None
                region_config = self.config.get("coordinates", "ocr", region_key)
                if region_config:
                    try:
                        # Use ScreenService.capture with relative coordinates
                        x = region_config["x"]
                        y = region_config["y"]
                        w = region_config["width"]
                        h = region_config["height"]

                        # Capture using relative coordinates (ScreenService handles
                        # conversion)
                        pil_img = self.state.screen.capture(
                            region=(x, y, w, h), relative=True
                        )
                        img_np = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

                        # Save debug images for first 3 reads
                        if self.total_reads <= 3:
                            import os

                            os.makedirs("ocr_debug", exist_ok=True)
                            cv2.imwrite(
                                f"ocr_debug/{stat_name}_raw_{self.total_reads}.png",
                                img_np,
                            )

                        temp_val = template_ocr.extract_number(
                            img_np,
                            font_name="plain11",
                            colors=colors,
                            correlation_threshold=0.98,
                        )
                    except Exception as e:
                        logger.debug(f"{stat_name} template OCR failed: {e}")

                # Update stats
                stat = self.stats[stat_name]
                if tess_val is not None:
                    stat["tess_success"] += 1
                    stat["recent_tess"].append(tess_val)
                    if len(stat["recent_tess"]) > 5:
                        stat["recent_tess"].pop(0)
                else:
                    stat["tess_fail"] += 1

                if temp_val is not None:
                    stat["temp_success"] += 1
                    stat["recent_temp"].append(temp_val)
                    if len(stat["recent_temp"]) > 5:
                        stat["recent_temp"].pop(0)
                else:
                    stat["temp_fail"] += 1

                # Compare
                if tess_val is not None and temp_val is not None:
                    if tess_val == temp_val:
                        stat["matches"] += 1
                    else:
                        stat["mismatches"] += 1

                results[stat_name] = (tess_val, temp_val)

            # Display
            hp_t, hp_tm = results["hp"]
            pr_t, pr_tm = results["prayer"]
            run_t, run_tm = results["run"]
            spec_t, spec_tm = results["spec"]

            logger.info(
                f"[{self.total_reads:3d}] - "
                f"HP:/{hp_tm or 'XX':>3} - "
                f"PR:/{pr_tm or 'XX':>3} - "
                f"RUN: {run_tm or 'XX':>3} - "
                f"SPEC:/{spec_tm or 'XX':>3} - "
            )

            # Stats every 10 reads
            if self.total_reads % 10 == 0:
                logger.info("\n" + "=" * 80)
                logger.info(f"STATISTICS (after {self.total_reads} reads)")
                logger.info("-" * 80)
                for name, stat in self.stats.items():
                    tess_rate = (
                        (100 * stat["tess_success"] / self.total_reads)
                        if self.total_reads > 0
                        else 0
                    )
                    temp_rate = (
                        (100 * stat["temp_success"] / self.total_reads)
                        if self.total_reads > 0
                        else 0
                    )
                    logger.info(
                        f"{name.upper():6} - Tess:{stat['tess_success']:3}/{self.total_reads} ({tess_rate:5.1f}%) "
                        f"Temp:{stat['temp_success']:3}/{self.total_reads} ({temp_rate:5.1f}%) "
                        f"Match:{stat['matches']:3} Mismatch:{stat['mismatches']:3}"
                    )
                logger.info("=" * 80 + "\n")

            self.actions.wait("short")
            return StateResult.RETRY

        except KeyboardInterrupt:
            logger.info("\n\nUser stopped tracking, showing final statistics...")
            return StateResult.SUCCESS
        except Exception as e:
            logger.error(f"Tracking error: {e}")
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
        logger.info("FINAL STATISTICS")
        logger.info("=" * 80)
        logger.info(f"Total Reads: {self.total_reads}")
        logger.info("-" * 80)

        for name, stat in self.stats.items():
            if self.total_reads > 0:
                tess_rate = 100 * stat["tess_success"] / self.total_reads
                temp_rate = 100 * stat["temp_success"] / self.total_reads

                logger.info(f"\n{name.upper()}:")
                logger.info(
                    f"  Tesseract: {stat['tess_success']:3}/{self.total_reads} ({tess_rate:5.1f}%)"
                )
                logger.info(
                    f"  Template:  {stat['temp_success']:3}/{self.total_reads} ({temp_rate:5.1f}%)"
                )
                logger.info(f"  Matches:   {stat['matches']:3}")
                logger.info(f"  Mismatches:{stat['mismatches']:3}")

                if temp_rate > tess_rate:
                    diff = temp_rate - tess_rate
                    logger.info(f"  → Template was {diff:.1f}% more reliable")
                elif tess_rate > temp_rate:
                    diff = tess_rate - temp_rate
                    logger.info(f"  → Tesseract was {diff:.1f}% more reliable")

        logger.info("\n" + "=" * 80)
        return StateResult.SUCCESS
