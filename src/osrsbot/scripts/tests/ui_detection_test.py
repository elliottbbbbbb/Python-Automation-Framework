"""
UI Detection Test - shows everything the bot can currently "see".

Detects and outlines in the live view window:
  - All template-matched UI grids (inventory, minimap, chat, etc.)
  - All template-matched buttons
  - OCR stat scan regions (HP, Prayer, Run, Spec) — always visible boxes
  - Current OCR stat values drawn beside each region

Usage:
  Select from the menu, or run directly:
    python -m osrsbot.scripts.tests.ui_detection_test
  Press Ctrl+C to stop.
"""

import logging
import threading
import time
from typing import Dict, Optional

import cv2 as cv
import numpy as np

from osrsbot.core.game_interface import GameInterface
from osrsbot.models.config import Config
from osrsbot.queries.stat_queries import StatQueries
from osrsbot.services.live_view_service import LiveViewService
from osrsbot.services.screen_service import ScreenService
from osrsbot.services.template_match_service import TemplateMatchService
from osrsbot.services.template_ocr_service import TemplateOCRService
from osrsbot.services.ui_manager_service import UIManager

logger = logging.getLogger(__name__)

# OCR region config keys + display colours (BGR)
_OCR_REGIONS = [
    ("hp",     "hp_region",             (0,  255,   0)),   # green
    ("prayer", "prayer_region",          (255, 200,   0)),   # cyan
    ("run",    "run_energy_region",      (0,  200, 255)),   # orange
    ("spec",   "special_attack_region",  (0,  100, 255)),   # yellow
]


def run_ui_detection() -> None:
    config = Config()

    # ── Services ──────────────────────────────────────────────────────────────
    interface = GameInterface(config)
    screen    = ScreenService(window_getter=interface.get_bounds)
    ocr       = TemplateOCRService()

    template_service = TemplateMatchService()
    try:
        template_service.register_from_config(config)
    except Exception as e:
        logger.error(f"Failed to register templates: {e}")
        return

    ui_manager = UIManager(template_service)
    ui_manager.sync_from_template_service()

    stat_queries = StatQueries(screen, ocr, config)

    # ── Register OCR regions as always-on static overlays ─────────────────────
    for stat_name, config_key, color in _OCR_REGIONS:
        region_cfg = config.get("coordinates", "ocr", config_key)
        if region_cfg:
            ui_manager.register_static_region(
                name=stat_name,
                x=region_cfg["x"],
                y=region_cfg["y"],
                w=region_cfg["width"],
                h=region_cfg["height"],
                color=color,
                label=stat_name,
            )
        else:
            logger.warning(f"No config for OCR region '{config_key}' — skipping overlay")

    # ── Shared state: stat values written by detection loop, read by overlay ──
    stat_values: Dict[str, Optional[int]] = {n: None for n, _, _ in _OCR_REGIONS}
    stat_lock = threading.Lock()

    # ── Live view ──────────────────────────────────────────────────────────────
    live_view_cfg = config.get("live_view", default={})
    live_view = LiveViewService(
        screen_service=screen,
        fps=live_view_cfg.get("fps", 10),
    )

    # Overlay 1: template-matched grids + buttons + static OCR boxes
    ui_manager.register_live_overlay(live_view)

    # Overlay 2: current stat values drawn next to their scan regions
    def _stat_value_overlay(frame_bgr: np.ndarray) -> np.ndarray:
        with stat_lock:
            current = dict(stat_values)
        out = frame_bgr  # draw in-place; UIManager already copied
        for stat_name, config_key, color in _OCR_REGIONS:
            region_cfg = config.get("coordinates", "ocr", config_key)
            if not region_cfg:
                continue
            val = current.get(stat_name)
            text = f"{val}" if val is not None else "??"
            rx = region_cfg["x"] + region_cfg["width"] + 4
            ry = region_cfg["y"] + region_cfg["height"] // 2 + 5
            cv.putText(out, text, (rx, ry), cv.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        return out

    live_view.register_overlay("stat_values", _stat_value_overlay)
    live_view.start()
    logger.info("Live view started. Detecting all UI elements — press Ctrl+C to stop.")

    # ── Detection loop ─────────────────────────────────────────────────────────
    try:
        iteration = 0
        while True:
            iteration += 1

            # Template detection (grids + buttons)
            screenshot = screen.capture_grayscale()
            if screenshot is not None:
                results = template_service.detect_all(screenshot, force=True)
                visible = sorted(k for k, v in results.items() if v)
                logger.info(
                    f"[{iteration}] Visible elements: {', '.join(visible) if visible else 'none'}"
                )

            # Update active tab (also cached in ui_manager._active_panel_grid)
            active_grid = ui_manager.update_active_tab(screen)
            logger.info(f"[{iteration}] Active panel grid: {active_grid or 'unknown'}")

            # OCR stats
            all_stats = stat_queries.get_all_stats()
            with stat_lock:
                stat_values.update(all_stats)

            hp     = all_stats.get("hp")
            prayer = all_stats.get("prayer")
            run    = all_stats.get("run")
            spec   = all_stats.get("spec")
            logger.info(
                f"[{iteration}] HP: {hp} | Prayer: {prayer} | Run: {run} | Spec: {spec}"
            )

            time.sleep(1.0)

    except KeyboardInterrupt:
        logger.info("Stopped by user.")
    finally:
        live_view.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    run_ui_detection()