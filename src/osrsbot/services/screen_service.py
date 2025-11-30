"""
ScreenService - Handles all screen capture and visual detection.

Separates screen interaction from mouse/click logic.
"""
import logging
import pyautogui
from typing import Tuple, Optional, List
from PIL import Image
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ColorMatch:
    """Represents a found color match"""
    x: int
    y: int
    confidence: float
    color: Tuple[int, int, int]


class ScreenService:
    """
    Handles all screen capture and color detection operations.

    Keeps screen logic separate from mouse/click operations.
    """

    def __init__(self, window_bounds: Optional[Tuple[int, int, int, int]] = None):
        """
        Args:
            window_bounds: (left, top, width, height) of game window
                          If None, uses full screen
        """
        self.window_bounds = window_bounds

    def set_window_bounds(self, left: int, top: int, width: int, height: int):
        """Update the window bounds for relative coordinates."""
        self.window_bounds = (left, top, width, height)
        logger.debug(f"Window bounds set to: {self.window_bounds}")

    def capture(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        relative: bool = True
    ) -> Image.Image:
        """
        Capture screenshot of region.

        Args:
            region: (x, y, width, height) to capture
                   If None, captures entire window/screen
            relative: If True, region is relative to window_bounds
                     If False, region is absolute screen coordinates

        Returns:
            PIL Image of captured region
        """
        if region is None:
            if self.window_bounds:
                left, top, width, height = self.window_bounds
                screenshot = pyautogui.screenshot(region=(left, top, width, height))
            else:
                screenshot = pyautogui.screenshot()
        else:
            x, y, w, h = region

            if relative and self.window_bounds:
                win_left, win_top, _, _ = self.window_bounds
                screenshot = pyautogui.screenshot(
                    region=(win_left + x, win_top + y, w, h)
                )
            else:
                screenshot = pyautogui.screenshot(region=(x, y, w, h))

        return screenshot

    def find_color(
        self,
        hex_color: str,
        tolerance: int = 10,
        region: Optional[Tuple[int, int, int, int]] = None,
        find_all: bool = False
    ) -> Optional[List[ColorMatch]] if False else Optional[ColorMatch]:
        """
        Find pixel(s) matching a color.

        Args:
            hex_color: Color to find (e.g., "#FF0000")
            tolerance: How close the color needs to match (0-255)
            region: Region to search (x, y, width, height)
            find_all: If True, return all matches; if False, return first match

        Returns:
            ColorMatch or List[ColorMatch] or None
        """
        target_rgb = self._hex_to_rgb(hex_color)
        screenshot = self.capture(region=region)

        pixels = screenshot.load()
        if pixels is None:
            logger.error("Failed to load screenshot pixels")
            return None

        matches = []

        for x in range(screenshot.width):
            for y in range(screenshot.height):
                pixel = pixels[x, y][:3]

                if self._color_matches(pixel, target_rgb, tolerance):
                    match = ColorMatch(
                        x=x,
                        y=y,
                        confidence=self._color_similarity(pixel, target_rgb),
                        color=pixel
                    )

                    if not find_all:
                        return match

                    matches.append(match)

        return matches if find_all else None

    def get_pixel_color(
        self,
        x: int,
        y: int,
        relative: bool = True
    ) -> Tuple[int, int, int]:
        """
        Get RGB color at specific coordinate.

        Args:
            x: X coordinate
            y: Y coordinate
            relative: If True, coordinates are relative to window

        Returns:
            (R, G, B) tuple
        """
        if relative and self.window_bounds:
            win_left, win_top, _, _ = self.window_bounds
            abs_x = win_left + x
            abs_y = win_top + y
        else:
            abs_x = x
            abs_y = y

        return pyautogui.pixel(abs_x, abs_y)

    def find_image(
        self,
        template_path: str,
        confidence: float = 0.8,
        region: Optional[Tuple[int, int, int, int]] = None,
        grayscale: bool = False
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Find template image on screen using template matching.

        Args:
            template_path: Path to template image
            confidence: Match confidence (0.0 to 1.0)
            region: Region to search in
            grayscale: Convert to grayscale before matching (faster)

        Returns:
            (x, y, width, height) of match or None
        """
        try:
            location = pyautogui.locate(
                template_path,
                self.capture(region=region),
                confidence=confidence,
                grayscale=grayscale
            )

            if location:
                return (location.left, location.top, location.width, location.height)

            return None

        except Exception as e:
            logger.error(f"Image search failed: {e}", exc_info=True)
            return None

    def wait_for_color(
        self,
        hex_color: str,
        timeout: float = 10.0,
        check_interval: float = 0.5,
        tolerance: int = 10,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[ColorMatch]:
        """
        Wait for a color to appear on screen.

        Args:
            hex_color: Color to wait for
            timeout: Maximum seconds to wait
            check_interval: Seconds between checks
            tolerance: Color match tolerance
            region: Region to search

        Returns:
            ColorMatch if found, None if timeout
        """
        import time
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            match = self.find_color(hex_color, tolerance, region)
            if match:
                return match

            time.sleep(check_interval)

        logger.warning(f"Color {hex_color} not found within {timeout}s")
        return None

    def wait_for_image(
        self,
        template_path: str,
        timeout: float = 10.0,
        check_interval: float = 0.5,
        confidence: float = 0.8,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Wait for an image to appear on screen.

        Args:
            template_path: Path to template image
            timeout: Maximum seconds to wait
            check_interval: Seconds between checks
            confidence: Match confidence
            region: Region to search

        Returns:
            (x, y, width, height) if found, None if timeout
        """
        import time
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            location = self.find_image(template_path, confidence, region)
            if location:
                return location

            time.sleep(check_interval)

        logger.warning(f"Image {template_path} not found within {timeout}s")
        return None

    def color_exists(
        self,
        hex_color: str,
        tolerance: int = 10,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> bool:
        """
        Check if a color exists anywhere on screen.

        Faster than find_color since it returns immediately on first match.
        """
        return self.find_color(hex_color, tolerance, region) is not None

    def image_exists(
        self,
        template_path: str,
        confidence: float = 0.8,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> bool:
        """
        Check if an image exists on screen.
        """
        return self.find_image(template_path, confidence, region) is not None

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def _color_matches(
        color1: Tuple[int, int, int],
        color2: Tuple[int, int, int],
        tolerance: int
    ) -> bool:
        """Check if two colors match within tolerance."""
        return all(abs(c1 - c2) <= tolerance for c1, c2 in zip(color1, color2))

    @staticmethod
    def _color_similarity(
        color1: Tuple[int, int, int],
        color2: Tuple[int, int, int]
    ) -> float:
        """
        Calculate color similarity (0.0 to 1.0).

        Returns 1.0 for perfect match, 0.0 for completely different.
        """
        distance = sum((c1 - c2) ** 2 for c1, c2 in zip(color1, color2)) ** 0.5
        max_distance = (255 ** 2 * 3) ** 0.5
        return 1.0 - (distance / max_distance)
