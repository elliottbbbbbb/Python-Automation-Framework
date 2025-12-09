# osrsbot/services/screen_service.py
from __future__ import annotations
import logging
import pyautogui
import cv2 as cv
import numpy as np
from typing import Tuple, Optional, List, Union, Dict, Any, Callable
from PIL import Image
from dataclasses import dataclass
from pathlib import Path

from osrsbot.constants import COLOR_DETECTION

logger = logging.getLogger(__name__)


@dataclass
class ColorMatch:
    x: int
    y: int
    confidence: float
    color: Tuple[int, int, int]


class ScreenService:
    """
    ScreenService: captures pixels and forwards frames to an injected Vision instance.
    Gets window bounds dynamically from GameInterface (single source of truth).
    Does NOT perform clicks — it returns absolute coords.
    """

    def __init__(
        self,
        window_getter: Optional[Callable[[], Tuple[int, int, int, int]]] = None,
        vision: Optional[Any] = None,
    ):
        """
        Initialize ScreenService.

        Args:
            window_getter: Callable that returns (left, top, width, height) when called.
                          Should get bounds from GameInterface for single source of truth.
            vision: Optional vision service for semantic detection
        """
        self.window_getter = window_getter
        self.vision = vision

    # ---------------- bounds helpers ----------------
    def _get_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        """Get fresh window bounds from GameInterface."""
        if self.window_getter is None:
            return None
        try:
            return self.window_getter()
        except Exception:
            logger.exception("Failed to get window bounds from window_getter")
            return None

    def relative_to_absolute(self, x: int, y: int) -> Tuple[int, int]:
        """
        Convert coordinates relative to window to absolute screen coordinates.
        If window_bounds is None, returns the inputs unchanged.
        """
        bounds = self._get_bounds()
        if bounds:
            left, top, _, _ = bounds
            return (left + x, top + y)
        return (x, y)

    # ---------------- capture helpers ----------------
    def capture(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        relative: bool = True,
    ) -> Image.Image:
        """
        Capture a PIL Image for the given region.
        region: (x, y, w, h). If relative=True, it's relative to window_bounds.
        If no bounds are set and relative=True, falls back to absolute capture.
        """
        bounds = self._get_bounds()

        if region is None:
            if bounds:
                left, top, width, height = bounds
                return pyautogui.screenshot(region=(left, top, width, height))
            return pyautogui.screenshot()

        x, y, w, h = region
        if relative and bounds:
            win_left, win_top, _, _ = bounds
            return pyautogui.screenshot(region=(win_left + x, win_top + y, w, h))
        return pyautogui.screenshot(region=(x, y, w, h))

    def capture_grayscale(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        relative: bool = True,
    ) -> Optional[np.ndarray]:
        """
        Capture screenshot and return a grayscale numpy array.
        Returns None if capture fails.
        """
        try:
            img = self.capture(region=region, relative=relative)
            arr = np.array(img)
            # PIL returns image in RGB order
            gray = cv.cvtColor(arr, cv.COLOR_RGB2GRAY)
            return gray
        except Exception:
            logger.exception("Failed to capture grayscale image")
            return None

    # ---------------- color helpers ----------------
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        hex_color = hex_color.lstrip("#")
        chunk_size = COLOR_DETECTION.hex_chunk_size
        return tuple(int(hex_color[i : i + chunk_size], COLOR_DETECTION.hex_base) for i in (0, 2, 4))

    def _color_matches(self, color1: Tuple[int, int, int], color2: Tuple[int, int, int], tolerance: int) -> bool:
        return all(abs(c1 - c2) <= tolerance for c1, c2 in zip(color1, color2))

    def _color_similarity(self, color1: Tuple[int, int, int], color2: Tuple[int, int, int]) -> float:
        distance = sum((c1 - c2) ** 2 for c1, c2 in zip(color1, color2)) ** 0.5
        max_distance = (COLOR_DETECTION.max_rgb_value ** 2 * COLOR_DETECTION.rgb_channels) ** 0.5
        return COLOR_DETECTION.perfect_match - (distance / max_distance)

    def find_color(
        self,
        hex_color: str,
        tolerance: int = COLOR_DETECTION.default_tolerance,
        region: Optional[Tuple[int, int, int, int]] = None,
        find_all: bool = False,
    ) -> Optional[Union[ColorMatch, List[ColorMatch]]]:
        """Find pixel(s) matching a color in the given region (or full window)."""
        target = self._hex_to_rgb(hex_color)
        try:
            screenshot = self.capture(region=region)
            pixels = screenshot.load()
            if pixels is None:
                logger.error("Failed to load screenshot pixels")
                return None

            matches: List[ColorMatch] = []
            for x in range(screenshot.width):
                for y in range(screenshot.height):
                    pixel = pixels[x, y][:3]  # type: ignore
                    if self._color_matches(pixel, target, tolerance):
                        cm = ColorMatch(x=x, y=y, confidence=self._color_similarity(pixel, target), color=pixel)  # type: ignore
                        if not find_all:
                            return cm
                        matches.append(cm)

            return matches if find_all else None
        except Exception:
            logger.exception("find_color failed")
            return None

    def get_pixel_color(self, x: int, y: int, relative: bool = True) -> Tuple[int, int, int]:
        """Return absolute RGB pixel color (uses pyautogui.pixel)."""
        bounds = self._get_bounds()
        if relative and bounds:
            left, top, _, _ = bounds
            abs_x = left + x
            abs_y = top + y
        else:
            abs_x, abs_y = x, y
        return pyautogui.pixel(abs_x, abs_y)

    # ---------------- image helpers ----------------
    def find_image(
        self,
        template_path: str,
        confidence: float = 0.8,
        region: Optional[Tuple[int, int, int, int]] = None,
        grayscale: bool = False,
    ) -> Optional[Tuple[int, int, int, int]]:
        """Small wrapper around pyautogui.locate that accepts relative regions."""
        try:
            needle_screenshot = self.capture(region=region)
            location = pyautogui.locate(template_path, needle_screenshot, confidence=confidence, grayscale=grayscale)
            if location:
                return (location.left, location.top, location.width, location.height)
            return None
        except Exception:
            logger.exception("find_image failed")
            return None

    # ---------------- vision wrappers ----------------
    def detect_inventory(self, force: bool = False) -> bool:
        """
        Capture current window and forward to vision.detect_inventory.
        Returns False if vision not injected or capture failed.
        """
        if self.vision is None:
            logger.debug("No vision instance injected; detect_inventory returning False")
            return False
        frame = self.capture_grayscale()
        if frame is None:
            return False
        return self.vision.detect_inventory(frame, force=force)

    def detect_items(self) -> Dict[Tuple[int, int], str]:
        """Capture frame and forward to vision.detect_items; returns empty dict if no vision or capture fail."""
        if self.vision is None:
            return {}
        frame = self.capture_grayscale()
        if frame is None:
            return {}
        return self.vision.detect_items(frame)

    def detect_ui_element(self, name: str, force: bool = False) -> bool:
        """Capture and forward UI element detection; returns False if missing."""
        if self.vision is None:
            return False
        frame = self.capture_grayscale()
        if frame is None:
            return False
        return self.vision.detect_ui_element(name, frame, force=force)

    def get_slot_absolute(self, index: int) -> Optional[Tuple[int, int]]:
        """
        Return absolute screen coordinates for the given slot index, or None.
        Vision returns coords relative to the captured frame; this converts to absolute.
        """
        if self.vision is None:
            return None
        pos = self.vision.get_slot_position(index)
        if pos is None:
            return None
        return self.relative_to_absolute(pos[0], pos[1])

    def invalidate_vision_cache(self) -> None:
        if self.vision is not None:
            try:
                self.vision.invalidate_cache()
            except Exception:
                logger.exception("invalidate_vision_cache failed")

