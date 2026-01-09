"""
Template-based OCR service using cv2.matchTemplate.
Based on OS-Bot-COLOR's OCR implementation - much faster and more accurate than Tesseract.

Uses template matching with correlation threshold instead of machine learning OCR.
"""

import logging
import pathlib
from operator import itemgetter
from typing import Dict, List, Optional

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class Color:
    """
    Color range for cv2.inRange filtering.

    Converts RGB colors to BGR to satisfy OpenCV's color format.
    Colors are specified in RGB but reversed to BGR internally.
    """

    def __init__(self, lower: tuple, upper: tuple = None):
        # Reverse RGB to BGR for OpenCV
        self.lower = np.array(lower[::-1], dtype=np.uint8)
        self.upper = np.array(upper[::-1] if upper else lower[::-1], dtype=np.uint8)


# OSRS Orb colors (defined in RGB format, auto-converted to BGR by Color class)
# ORB_GREEN covers green to yellow (high to medium HP)
ORB_GREEN = Color(lower=(0, 255, 0), upper=(255, 255, 0))
# ORB_RED covers red to yellow (low to medium HP)
ORB_RED = Color(lower=(255, 0, 0), upper=(255, 255, 0))
# YELLOW for general UI text
YELLOW = Color(lower=(255, 255, 0), upper=(255, 255, 0))
# CYAN for prayer points
CYAN = Color(lower=(0, 255, 255), upper=(0, 255, 255))
# WHITE for white text
WHITE = Color(lower=(200, 200, 200), upper=(255, 255, 255))
# GRAY for dimmer text (like coordinates)
GRAY = Color(lower=(150, 150, 150), upper=(255, 255, 255))
# LIGHT_GRAY for very dim text (like world coordinates - RGB ~70-255)
LIGHT_GRAY = Color(lower=(70, 70, 60), upper=(255, 255, 255))


def isolate_colors(image: np.ndarray, colors: List[Color]) -> np.ndarray:
    """
    Isolates specified colors from an image using cv2.inRange.

    Args:
        image: Input image (BGR format)
        colors: List of Color objects to isolate

    Returns:
        Binary mask where isolated colors are white (255)
    """
    if not isinstance(colors, list):
        colors = [colors]

    masks = [cv2.inRange(image, color.lower, color.upper) for color in colors]

    h, w = image.shape[:2]
    mask = np.zeros([h, w, 1], dtype=np.uint8)
    for mask_ in masks:
        mask = cv2.bitwise_or(mask, mask_)

    return mask


def load_font(font_name: str, font_dir: pathlib.Path) -> Dict[str, np.ndarray]:
    """
    Loads a font's alphabet from BMP files into a dictionary.

    Args:
        font_name: Name of the font directory
        font_dir: Path to fonts directory

    Returns:
        Dictionary of {"char": image} pairs
    """
    font_path = font_dir / font_name
    if not font_path.exists():
        logger.warning(f"Font directory not found: {font_path}")
        return {}

    alphabet = {}
    for path in font_path.glob("*.bmp"):
        try:
            name = int(path.stem)
            key = chr(name)
            value = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if value is not None:
                alphabet[key] = value
        except (ValueError, OSError) as e:
            logger.debug(f"Failed to load font character {path}: {e}")

    logger.info(f"Loaded {len(alphabet)} characters for font {font_name}")
    return alphabet


class TemplateOCRService:
    """
    Template-based OCR service using cv2.matchTemplate.
    Much faster and more accurate than Tesseract for fixed-width game fonts.
    """

    def __init__(self, fonts_dir: Optional[str] = None):
        """
        Initialize the template OCR service.

        Args:
            fonts_dir: Path to fonts directory. If None, uses src/osrsbot/fonts
        """
        if fonts_dir is None:
            # Default to src/osrsbot/fonts
            fonts_dir = pathlib.Path(__file__).parent.parent / "fonts"
        else:
            fonts_dir = pathlib.Path(fonts_dir)

        self.fonts_dir = fonts_dir

        # Load fonts (lazy loading - only load when needed)
        self._fonts = {}
        self._font_names = {
            "plain11": "Plain11",
            "plain12": "Plain12",
            "bold12": "Bold12",
        }

    def _get_font(self, font_name: str) -> Dict[str, np.ndarray]:
        """Get or load a font."""
        if font_name not in self._fonts:
            actual_name = self._font_names.get(font_name, font_name)
            self._fonts[font_name] = load_font(actual_name, self.fonts_dir)
        return self._fonts[font_name]

    def extract_text(
        self,
        image: np.ndarray,
        font_name: str = "plain11",
        colors: Optional[List[Color]] = None,
        correlation_threshold: float = 0.98,
    ) -> str:
        """
        Extracts text from an image using template matching.

        Args:
            image: Input image (can be PIL Image or numpy array)
            font_name: Font to use ("plain11", "plain12", "bold12")
            colors: List of Color objects to isolate (if None, uses image as-is)
            correlation_threshold: Minimum correlation for a match (default 0.98)

        Returns:
            Extracted text string
        """
        # Convert PIL Image to numpy array if needed
        if isinstance(image, Image.Image):
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Isolate colors if specified
        if colors is not None:
            image = isolate_colors(image, colors)

        # Get font templates
        font = self._get_font(font_name)
        if not font:
            logger.warning(f"Font {font_name} not loaded, cannot extract text")
            return ""

        # Template match each character
        char_list = []
        for key, template in font.items():
            if key == " ":
                continue

            # Skip first row for most fonts, first 2 rows for PLAIN_12
            if font_name == "plain12":
                template_slice = template[2:]
            else:
                template_slice = template[1:]

            try:
                correlation = cv2.matchTemplate(
                    image, template_slice, cv2.TM_CCOEFF_NORMED
                )
                y_mins, x_mins = np.where(correlation >= correlation_threshold)

                # Add each instance of this character
                for x, y in zip(x_mins, y_mins):
                    char_list.append([key, x, y])
            except cv2.error as e:
                logger.debug(f"Template matching failed for '{key}': {e}")
                continue

        # Sort by position (top-left to bottom-right)
        char_list = sorted(char_list, key=itemgetter(2, 1))

        # Join into string
        result = "".join(letter for letter, _, _ in char_list)
        return result

    def extract_number(
        self,
        image: np.ndarray,
        font_name: str = "plain11",
        colors: Optional[List[Color]] = None,
        correlation_threshold: float = 0.98,
    ) -> Optional[int]:
        """
        Extracts a number from an image.

        Args:
            image: Input image
            font_name: Font to use
            colors: List of Color objects to isolate
            correlation_threshold: Minimum correlation for a match

        Returns:
            Extracted number or None if extraction failed
        """
        text = self.extract_text(image, font_name, colors, correlation_threshold)

        # Extract digits only
        digits = "".join(c for c in text if c.isdigit())

        if not digits:
            return None

        try:
            return int(digits)
        except ValueError:
            return None


# Singleton instance
_template_ocr_service = None


def get_template_ocr_service(fonts_dir: Optional[str] = None) -> TemplateOCRService:
    """Get or create the singleton TemplateOCRService instance."""
    global _template_ocr_service
    if _template_ocr_service is None:
        _template_ocr_service = TemplateOCRService(fonts_dir)
    return _template_ocr_service
