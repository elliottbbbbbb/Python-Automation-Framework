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
from osrsbot.constants import (
    OCR_PREPROCESSING,
    SHAPE_DETECTION,
    OCR_SMOOTHING,
    TESSERACT_CONFIG,
    OCR_CHAR_REPLACEMENTS
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
        self._window_getter = window_getter
        self.debug = debug

        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            logger.info(f"Using Tesseract from: {tesseract_path}")

        self._caches = {}  # region_name -> deque of readings
        self._last_valid = {}  # region_name -> last valid value
        self._last_read_time = {}  # region_name -> timestamp

    def get_window_position(self) -> Optional[Tuple[int, int, int, int]]:
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
        window_size: Optional[int] = None,
        ttl: Optional[float] = None
    ) -> Optional[int]:
        """
        Read a numeric value from a screen region.

        Args:
            region: OCRRegion defining where to read
            min_value: Minimum valid value
            max_value: Maximum valid value
            smooth: Whether to smooth results over time
            window_size: Number of readings to keep for smoothing
                        (defaults to OCR_SMOOTHING.default_window_size)
            ttl: Cache time-to-live in seconds
                (defaults to OCR_SMOOTHING.default_ttl_seconds)

        Returns:
            Numeric value or None if OCR failed
        """
        if window_size is None:
            window_size = OCR_SMOOTHING.default_window_size
        if ttl is None:
            ttl = OCR_SMOOTHING.default_ttl_seconds

        if smooth:
            now = time.time()
            if region.name in self._last_read_time:
                if (now - self._last_read_time[region.name]) < ttl:
                    cached = self._last_valid.get(region.name)
                    if cached is not None:
                        logger.debug(f"read_number({region.name}): returning cached {cached}")
                        return cached

        raw_value = self._get_raw_number(region, min_value, max_value)

        if raw_value is None:
            return self._last_valid.get(region.name)

        if not smooth:
            self._last_valid[region.name] = raw_value
            self._last_read_time[region.name] = time.time()
            return raw_value

        if region.name not in self._caches:
            self._caches[region.name] = deque(maxlen=window_size)

        self._caches[region.name].append(raw_value)

        if len(self._caches[region.name]) > 0:
            counter = Counter(self._caches[region.name])
            smoothed_value, count = counter.most_common(1)[0]

            # Reject sudden jumps as likely OCR errors
            # Use threshold from OCR_SMOOTHING configuration
            last_valid = self._last_valid.get(region.name)
            jump_size = abs(smoothed_value - last_valid) if last_valid is not None else 0
            if last_valid is not None and jump_size > OCR_SMOOTHING.max_suspicious_jump:
                logger.warning(
                    f"{region.name}: Suspicious jump detected: {last_valid} -> {smoothed_value} "
                    f"(jump={jump_size}, max={OCR_SMOOTHING.max_suspicious_jump})"
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
        window_position = self.get_window_position()
        if not window_position:
            logger.debug(f"_get_raw_number({region.name}): no window position found")
            return None

        win_x, win_y, _, _ = window_position

        abs_region = (
            win_x + region.x,
            win_y + region.y,
            region.width,
            region.height
        )

        screenshot = pyautogui.screenshot(region=abs_region)
        strategies = self._preprocess_for_numbers(screenshot)

        if self.debug:
            os.makedirs("ocr_debug", exist_ok=True)
            for i, processed_img in enumerate(strategies):
                fname = os.path.join("ocr_debug", f"{region.name}_strategy_{i}.png")
                try:
                    processed_img.save(fname)
                except Exception:
                    logger.debug(f"Failed to save debug image {fname}", exc_info=True)

        configs = [TESSERACT_CONFIG.get_config_string()]
        all_results = []

        for i, processed_img in enumerate(strategies):
            for config in configs:
                try:
                    text = pytesseract.image_to_string(processed_img, config=config)
                    cleaned_text = self._clean_ocr_text(text)
                    logger.debug(
                        f"OCR {region.name} strategy {i} -> "
                        f"raw:'{text.strip()}' cleaned:'{cleaned_text}'"
                    )

                    numbers = re.findall(r'\d+', cleaned_text)
                    if numbers:
                        value = int(numbers[0])
                        if min_value <= value <= max_value:
                            all_results.append(value)
                except Exception:
                    logger.exception(f"Tesseract failed on {region.name} processed image")

        if not all_results:
            return None

        ocr_consensus = Counter(all_results).most_common(1)[0][0]

        # Special handling: OCR often misreads 9 as 4
        if ocr_consensus == 4:
            ocr_consensus = self._check_for_nine(strategies, all_results, region.name)

        return ocr_consensus

    def _preprocess_for_numbers(self, screenshot: Image.Image) -> List[Image.Image]:
        """
        Apply multiple preprocessing strategies to improve OCR accuracy.

        Different strategies work better for different digits (e.g., 9 vs 11).
        Uses configuration from constants.OCR_PREPROCESSING.
        """
        strategies = []

        for strategy in OCR_PREPROCESSING.get_all_strategies():
            img = screenshot.convert('L')
            img = ImageOps.invert(img)
            img = img.resize((
                img.width * strategy.resize_multiplier,
                img.height * strategy.resize_multiplier
            ))
            enhancer = ImageEnhance.Contrast(img)
            img_processed = enhancer.enhance(strategy.contrast_level)
            img_processed = img_processed.point(
                lambda p: 255 if p > strategy.threshold else 0
            )
            strategies.append(img_processed)

            logger.debug(f"Applied preprocessing strategy: {strategy}")

        return strategies

    def _check_for_nine(
        self,
        strategies: List[Image.Image],
        all_results: List[int],
        region_name: str
    ) -> int:
        """
        Special handling for OCR confusion between 4 and 9.

        Uses shape detection heuristics from constants.SHAPE_DETECTION.

        Args:
            strategies: List of preprocessed images
            all_results: All OCR results from different strategies
            region_name: Name of the region being analyzed (for logging)

        Returns:
            9 if shape analysis confirms it's a nine, otherwise 4
        """
        try:
            nine_votes = 0
            diagnostics = []

            for idx, proc_img in enumerate(strategies):
                try:
                    bw = preprocess_for_shape_detection(
                        proc_img,
                        size=SHAPE_DETECTION.shape_detection_size
                    )
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

            threshold_met = nine_votes >= SHAPE_DETECTION.min_nine_votes_for_correction
            ocr_agrees = (
                SHAPE_DETECTION.trust_ocr_with_single_vote and
                nine_votes >= 1 and
                9 in all_results
            )

            if threshold_met or ocr_agrees:
                logger.info(
                    f"{region_name}: Correcting OCR 4 -> 9 based on "
                    f"multi-strategy shape heuristic (votes={nine_votes})"
                )
                return 9
        except Exception:
            logger.exception(f"{region_name}: Shape-checking error")

        return 4

    @staticmethod
    def _clean_ocr_text(text: str) -> str:
        cleaned = text or ""
        for old, new in OCR_CHAR_REPLACEMENTS.replacements.items():
            cleaned = cleaned.replace(old, new)
        return cleaned

    def reset_cache(self, region_name: Optional[str] = None):
        if region_name:
            self._caches.pop(region_name, None)
            self._last_valid.pop(region_name, None)
            self._last_read_time.pop(region_name, None)
        else:
            self._caches.clear()
            self._last_valid.clear()
            self._last_read_time.clear()
