# osrsbot/services/screen_service.py
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import cv2 as cv
import numpy as np
import pyautogui
from PIL import Image

from osrsbot.constants import COLOR_DETECTION
from osrsbot.utils.color_helpers import hex_to_rgb

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

    # ==================== Bounds Helpers ====================
    def _get_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        """Get fresh window bounds from GameInterface."""
        if self.window_getter is None:
            return None
        try:
            return self.window_getter()
        except Exception:
            logger.exception("Failed to get window bounds from window_getter")
            return None

    def get_viewport_dimensions(self) -> Optional[Tuple[int, int]]:
        """
        Get viewport dimensions (width, height).

        Returns the game window dimensions for calculating viewport regions.
        Used by queries/commands that need to know game window size.

        Returns:
            (width, height) tuple or None if window unavailable

        Example:
            >>> dims = screen_service.get_viewport_dimensions()
            >>> if dims:
            >>>     width, height = dims
            >>>     viewport_region = (0, 0, int(width * 0.70), height)
        """
        bounds = self._get_bounds()
        if bounds:
            _, _, width, height = bounds
            return (width, height)
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

    # ==================== Capture Helpers ====================
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

    # ==================== Color Helpers ====================
    def _color_matches(
        self, color1: Tuple[int, int, int], color2: Tuple[int, int, int], tolerance: int
    ) -> bool:
        return all(abs(c1 - c2) <= tolerance for c1, c2 in zip(color1, color2))

    def _color_similarity(
        self, color1: Tuple[int, int, int], color2: Tuple[int, int, int]
    ) -> float:
        distance = sum((c1 - c2) ** 2 for c1, c2 in zip(color1, color2)) ** 0.5
        max_distance = (
            COLOR_DETECTION.max_rgb_value**2 * COLOR_DETECTION.rgb_channels
        ) ** 0.5
        return COLOR_DETECTION.perfect_match - (distance / max_distance)

    def find_color(
        self,
        hex_color: str,
        tolerance: int = COLOR_DETECTION.default_tolerance,
        region: Optional[Tuple[int, int, int, int]] = None,
        find_all: bool = False,
    ) -> Optional[Union[ColorMatch, List[ColorMatch]]]:
        """
        Find pixel(s) matching a color in the given region (or full window).

        Uses NumPy vectorized operations for 10-100x speed improvement over pixel iteration.
        """
        target = hex_to_rgb(hex_color)
        try:
            screenshot = self.capture(region=region)
            # Convert PIL image to NumPy array (much faster than pixel access)
            img_array = np.array(screenshot)

            # Calculate region offset for coordinate correction
            region_offset_x = region[0] if region else 0
            region_offset_y = region[1] if region else 0

            # Vectorized color matching using NumPy broadcasting
            # Compare all pixels at once instead of nested loops
            r_match = np.abs(img_array[:, :, 0].astype(int) - target[0]) <= tolerance
            g_match = np.abs(img_array[:, :, 1].astype(int) - target[1]) <= tolerance
            b_match = np.abs(img_array[:, :, 2].astype(int) - target[2]) <= tolerance

            # Combine RGB matches (all channels must match)
            color_mask = r_match & g_match & b_match

            # Get coordinates of matching pixels
            # Note: np.where returns (y_coords, x_coords) so we need to swap
            y_coords, x_coords = np.where(color_mask)

            if len(x_coords) == 0:
                return None if not find_all else []

            matches: List[ColorMatch] = []

            # If find_all is False, just return first match
            if not find_all:
                x, y = int(x_coords[0]), int(y_coords[0])
                pixel_rgb = tuple(img_array[y, x, :3].tolist())
                return ColorMatch(
                    x=x + region_offset_x,  # Correct for region offset
                    y=y + region_offset_y,
                    confidence=self._color_similarity(pixel_rgb, target),
                    color=pixel_rgb,  # type: ignore
                )

            # Build all matches
            for x_coord, y_coord in zip(x_coords, y_coords):
                x, y = int(x_coord), int(y_coord)
                pixel_rgb = tuple(img_array[y, x, :3].tolist())
                matches.append(
                    ColorMatch(
                        x=x + region_offset_x,  # Correct for region offset
                        y=y + region_offset_y,
                        confidence=self._color_similarity(pixel_rgb, target),
                        color=pixel_rgb,  # type: ignore
                    )
                )

            return matches
        except Exception:
            logger.exception("find_color failed")
            return None

    def find_color_with_distance(
        self,
        hex_color: str,
        reference_point: Tuple[int, int],
        tolerance: int = COLOR_DETECTION.default_tolerance,
        region: Optional[Tuple[int, int, int, int]] = None,
        blacklist_checker: Optional[Any] = None,
    ) -> List[Tuple[ColorMatch, float]]:
        """
        Find all color matches sorted by distance from reference point.

        Args:
            hex_color: Target color as hex string
            reference_point: (x, y) to calculate distance from (relative coords)
            tolerance: Color matching tolerance
            region: Optional search region (x, y, width, height)
            blacklist_checker: Optional callable(x, y) -> bool to filter blacklisted

        Returns:
            List of (ColorMatch, distance) tuples, sorted by distance (closest first)
        """
        # Find all color matches
        matches = self.find_color(
            hex_color=hex_color, tolerance=tolerance, region=region, find_all=True
        )

        if not matches or not isinstance(matches, list):
            return []

        # Calculate distance from reference point for each match
        matches_with_distance: List[Tuple[ColorMatch, float]] = []
        ref_x, ref_y = reference_point

        for match in matches:
            # Filter out blacklisted locations if checker provided
            if blacklist_checker and blacklist_checker(match.x, match.y):
                continue

            # Calculate Euclidean distance from reference point
            distance = ((match.x - ref_x) ** 2 + (match.y - ref_y) ** 2) ** 0.5
            matches_with_distance.append((match, distance))

        # Sort by distance (ascending - closest first)
        matches_with_distance.sort(key=lambda item: item[1])

        logger.debug(
            f"Found {len(matches_with_distance)} color matches "
            f"sorted by distance from ({ref_x}, {ref_y})"
        )

        return matches_with_distance

    def get_pixel_color(
        self, x: int, y: int, relative: bool = True
    ) -> Tuple[int, int, int]:
        """Return absolute RGB pixel color (uses pyautogui.pixel)."""
        bounds = self._get_bounds()
        if relative and bounds:
            left, top, _, _ = bounds
            abs_x = left + x
            abs_y = top + y
        else:
            abs_x, abs_y = x, y
        return pyautogui.pixel(abs_x, abs_y)

    # ==================== Image Helpers ====================
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
            location = pyautogui.locate(
                template_path,
                needle_screenshot,
                confidence=confidence,
                grayscale=grayscale,
            )
            if location:
                return (location.left, location.top, location.width, location.height)
            return None
        except Exception:
            logger.exception("find_image failed")
            return None

    # ==================== Vision Wrappers ====================
    def detect_inventory(self, force: bool = False) -> bool:
        """
        Capture current window and forward to vision.detect_inventory.
        Returns False if vision not injected or capture failed.
        """
        if self.vision is None:
            logger.debug(
                "No vision instance injected; detect_inventory returning False"
            )
            return False
        frame = self.capture_grayscale()
        if frame is None:
            return False
        return self.vision.detect_inventory(frame, force=force)

    def detect_items(self) -> Dict[Tuple[int, int], str]:
        """
        Capture frame and forward to vision.detect_items.

        Returns empty dict if no vision or capture fails.
        """
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

    def wait_for_color(
        self,
        hex_color: str,
        timeout: float = 10.0,
        check_interval: float = 0.5,
        tolerance: int = COLOR_DETECTION.default_tolerance,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> Optional[ColorMatch]:
        """
        Wait for a color to appear on screen within a timeout period.

        Args:
            hex_color: Target color in hex format (e.g., "#FF0000")
            timeout: Maximum time to wait in seconds
            check_interval: Time between checks in seconds
            tolerance: Color matching tolerance
            region: Optional region to search within (x, y, w, h)

        Returns:
            ColorMatch if found within timeout, None otherwise
        """
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            match = self.find_color(hex_color, tolerance, region)
            if match:
                logger.debug(f"Color {hex_color} found at ({match.x}, {match.y})")
                return match

            time.sleep(check_interval)

        logger.debug(f"Color {hex_color} not found within {timeout}s")
        return None
