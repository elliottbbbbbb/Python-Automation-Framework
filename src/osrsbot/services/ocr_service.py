"""
OCRService - Reusable OCR pipeline for reading game UI elements.

Supports configurable regions for HP, prayer, run energy, and other stats.
"""
import re
import os
import logging
import time
import pyautogui
import pytesseract
from PIL import ImageEnhance, ImageOps, Image
from collections import Counter, deque
from typing import Optional, Tuple, List, Callable
from dataclasses import dataclass

from osrsbot.utils.ocr_helpers import (
    preprocess_for_shape_detection,
    count_holes_and_tail,
    looks_like_nine
)

logger = logging.getLogger(__name__)


@dataclass
class OCRRegion:
    """Defines a region to perform OCR on."""
    x: int
    y: int
    width: int
    height: int
    name: str = "unknown"


@dataclass
class OCRResult:
    """Result of OCR operation."""
    value: Optional[int]
    confidence: float
    raw_readings: List[int]
    timestamp: float


class OCRService:
    """
    Reusable OCR service for reading numeric values from game UI.

    Supports multiple preprocessing strategies to handle difficult
    characters like 9, 11, etc.
    """

    def __init__(
        self,
        window_getter: Optional[Callable[[], Optional[Tuple[int, int, int, int]]]] = None,
        tesseract_path: Optional[str] = None,
        debug: bool = True
    ):
        """
        Initialize OCR service.

        Args:
            window_getter: Function that returns (x, y, width, height) of game window
            tesseract_path: Path to tesseract executable
            debug: Whether to save debug images
        """
        self._window_getter = window_getter
        self.debug = debug

        # Set up Tesseract
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            logger.info(f"Using Tesseract from: {tesseract_path}")

        # Cache for smoothing results
        self._caches = {}  # region_name -> deque of readings
        self._last_valid = {}  # region_name -> last valid value
        self._last_read_time = {}  # region_name -> timestamp

    def get_window_position(self) -> Optional[Tuple[int, int, int, int]]:
        """Get current game window position."""
        if self._window_getter is not None:
            try:
                pos = self._window_getter()
                if pos:
                    return pos
            except Exception:
                logger.exception("window_getter raised an exception")

        logger.warning("No window_getter provided to OCRService")
        return None

    def read_number(
        self,
        region: OCRRegion,
        min_value: int = 1,
        max_value: int = 99,
        smooth: bool = True,
        window_size: int = 5,
        ttl: float = 0.5
    ) -> Optional[int]:
        """
        Read a numeric value from a screen region.

        Args:
            region: OCRRegion defining where to read
            min_value: Minimum valid value
            max_value: Maximum valid value
            smooth: Whether to smooth results over time
            window_size: Number of readings to keep for smoothing
            ttl: Cache time-to-live in seconds

        Returns:
            Numeric value or None if OCR failed
        """
        # Check cache if smoothing enabled
        if smooth:
            now = time.time()
            if region.name in self._last_read_time:
                if (now - self._last_read_time[region.name]) < ttl:
                    cached = self._last_valid.get(region.name)
                    if cached is not None:
                        logger.debug(f"read_number({region.name}): returning cached {cached}")
                        return cached

        # Get raw reading
        raw_value = self._get_raw_number(region, min_value, max_value)

        if raw_value is None:
            # Return last valid value if available
            return self._last_valid.get(region.name)

        if not smooth:
            self._last_valid[region.name] = raw_value
            self._last_read_time[region.name] = time.time()
            return raw_value

        # Initialize cache for this region if needed
        if region.name not in self._caches:
            self._caches[region.name] = deque(maxlen=window_size)

        # Add to history
        self._caches[region.name].append(raw_value)

        # Get most common value from history
        if len(self._caches[region.name]) > 0:
            counter = Counter(self._caches[region.name])
            smoothed_value, count = counter.most_common(1)[0]

            # Reject sudden jumps >30 as likely OCR errors
            last_valid = self._last_valid.get(region.name)
            if last_valid is not None and abs(smoothed_value - last_valid) > 30:
                logger.warning(
                    f"{region.name}: Suspicious jump: {last_valid} -> {smoothed_value}"
                )
                return last_valid

            self._last_valid[region.name] = smoothed_value
            self._last_read_time[region.name] = time.time()

            confidence = (count / len(self._caches[region.name])) * 100
            logger.info(
                f"{region.name}: {smoothed_value} "
                f"(confidence: {confidence:.0f}%, history: {list(self._caches[region.name])})"
            )
            return smoothed_value
        else:
            self._last_valid[region.name] = raw_value
            self._last_read_time[region.name] = time.time()
            logger.debug(f"{region.name} (building history): {raw_value}")
            return raw_value

    def _get_raw_number(
        self,
        region: OCRRegion,
        min_value: int,
        max_value: int
    ) -> Optional[int]:
        """
        Perform raw OCR on a region.

        Uses multiple preprocessing strategies to handle difficult digits.
        """
        window_position = self.get_window_position()
        if not window_position:
            logger.debug(f"_get_raw_number({region.name}): no window position found")
            return None

        win_x, win_y, _, _ = window_position

        # Calculate absolute screen region
        abs_region = (
            win_x + region.x,
            win_y + region.y,
            region.width,
            region.height
        )

        # Capture screenshot
        screenshot = pyautogui.screenshot(region=abs_region)

        # Apply multiple preprocessing strategies
        strategies = self._preprocess_for_numbers(screenshot)

        # Save debug images if enabled
        if self.debug:
            os.makedirs("ocr_debug", exist_ok=True)
            for i, processed_img in enumerate(strategies):
                fname = os.path.join("ocr_debug", f"{region.name}_strategy_{i}.png")
                try:
                    processed_img.save(fname)
                except Exception:
                    logger.debug(f"Failed to save debug image {fname}", exc_info=True)

        # OCR config
        configs = [r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789']
        all_results = []

        # Try each strategy
        for i, processed_img in enumerate(strategies):
            for config in configs:
                try:
                    text = pytesseract.image_to_string(processed_img, config=config)
                    cleaned_text = self._clean_ocr_text(text)
                    logger.debug(
                        f"OCR {region.name} strategy {i} -> "
                        f"raw:'{text.strip()}' cleaned:'{cleaned_text}'"
                    )

                    # Extract numbers
                    numbers = re.findall(r'\d+', cleaned_text)
                    if numbers:
                        value = int(numbers[0])
                        if min_value <= value <= max_value:
                            all_results.append(value)
                except Exception:
                    logger.exception(f"Tesseract failed on {region.name} processed image")

        if not all_results:
            return None

        # Get consensus value (most common)
        ocr_consensus = Counter(all_results).most_common(1)[0][0]

        # Special handling: OCR often misreads 9 as 4
        if ocr_consensus == 4:
            ocr_consensus = self._check_for_nine(strategies, all_results, region.name)

        return ocr_consensus

    def _preprocess_for_numbers(self, screenshot: Image.Image) -> List[Image.Image]:
        """
        Apply multiple preprocessing strategies to improve OCR accuracy.

        Different strategies work better for different digits (e.g., 9 vs 11).
        """
        strategies = []

        # Strategy 1: High contrast, threshold 61
        img = screenshot.convert('L')
        img = ImageOps.invert(img)
        img = img.resize((img.width * 5, img.height * 5))
        enhancer = ImageEnhance.Contrast(img)
        img1 = enhancer.enhance(4)
        img1 = img1.point(lambda p: 255 if p > 61 else 0)
        strategies.append(img1)

        # Strategy 2: Medium contrast, lower threshold
        img = screenshot.convert('L')
        img = ImageOps.invert(img)
        img = img.resize((img.width * 6, img.height * 6))
        enhancer = ImageEnhance.Contrast(img)
        img2 = enhancer.enhance(3)
        img2 = img2.point(lambda p: 255 if p > 40 else 0)
        strategies.append(img2)

        # Strategy 3: Medium-high contrast
        img = screenshot.convert('L')
        img = ImageOps.invert(img)
        img = img.resize((img.width * 4, img.height * 4))
        enhancer = ImageEnhance.Contrast(img)
        img3 = enhancer.enhance(3.5)
        img3 = img3.point(lambda p: 255 if p > 65 else 0)
        strategies.append(img3)

        # Strategy 4: Very high contrast
        img = screenshot.convert('L')
        img = ImageOps.invert(img)
        img = img.resize((img.width * 5, img.height * 5))
        enhancer = ImageEnhance.Contrast(img)
        img4 = enhancer.enhance(5)
        img4 = img4.point(lambda p: 255 if p > 70 else 0)
        strategies.append(img4)

        # Strategy 5: High threshold
        img = screenshot.convert('L')
        img = ImageOps.invert(img)
        img = img.resize((img.width * 5, img.height * 5))
        enhancer = ImageEnhance.Contrast(img)
        img5 = enhancer.enhance(4)
        img5 = img5.point(lambda p: 255 if p > 100 else 0)
        strategies.append(img5)

        return strategies

    def _check_for_nine(
        self,
        strategies: List[Image.Image],
        all_results: List[int],
        region_name: str
    ) -> int:
        """
        Check if OCR misread a 9 as a 4.

        Uses shape detection heuristics.
        """
        try:
            nine_votes = 0
            diagnostics = []

            for idx, proc_img in enumerate(strategies):
                try:
                    bw = preprocess_for_shape_detection(proc_img, size=(140, 140))
                    hc, tf, asp = count_holes_and_tail(bw)
                except Exception:
                    hc, tf, asp = 0, 0.0, 0.0
                diagnostics.append((idx, hc, tf, asp))

                try:
                    if looks_like_nine(proc_img):
                        nine_votes += 1
                except Exception:
                    pass

            if nine_votes > 0 or 9 in all_results:
                logger.debug(
                    f"{region_name} 4->9_check: nine_votes={nine_votes}, "
                    f"raw_votes_has9={9 in all_results}, per-strategy={diagnostics}"
                )

            if nine_votes >= 2 or (nine_votes >= 1 and 9 in all_results):
                logger.info(
                    f"{region_name}: Correcting OCR 4 -> 9 based on "
                    "multi-strategy shape heuristic"
                )
                return 9
        except Exception:
            logger.exception(f"{region_name}: Shape-checking error")

        return 4

    @staticmethod
    def _clean_ocr_text(text: str) -> str:
        """Clean OCR output by replacing common misread characters."""
        replacements = {
            'i': '1', 'I': '1', 'l': '1', '|': '1',
            'o': '0', 'O': '0', 'Q': '0',
            'S': '5', 's': '5',
            'Z': '2', 'z': '2',
            'B': '8', 'g': '9', 'G': '6',
            ' ': '', '\n': '', '\r': '', '\t': '',
            'D': '0', 'd': '0', 'q': '9', 'a': '4'
        }
        cleaned = text or ""
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        return cleaned

    def reset_cache(self, region_name: Optional[str] = None):
        """
        Reset cached values for a region or all regions.

        Args:
            region_name: Region to reset, or None to reset all
        """
        if region_name:
            self._caches.pop(region_name, None)
            self._last_valid.pop(region_name, None)
            self._last_read_time.pop(region_name, None)
        else:
            self._caches.clear()
            self._last_valid.clear()
            self._last_read_time.clear()
