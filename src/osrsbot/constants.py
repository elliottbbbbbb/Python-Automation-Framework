"""
Constants and configuration values for OSRSbot.

This module centralizes magic numbers and configuration.
"""
from dataclasses import dataclass, field
from typing import Tuple, Dict


@dataclass(frozen=True)
class PreprocessingStrategy:
    """
    Configuration for a single OCR preprocessing strategy.

    Each strategy applies different image transformations to optimize
    OCR accuracy for different digit characteristics.

    Frozen to allow use as dataclass default values.
    """
    name: str
    resize_multiplier: int
    contrast_level: float
    threshold: int

    def __str__(self) -> str:
        return (
            f"{self.name}: "
            f"resize={self.resize_multiplier}x, "
            f"contrast={self.contrast_level}, "
            f"threshold={self.threshold}"
        )


@dataclass
class OCRPreprocessingConfig:
    """
    OCR preprocessing configuration with multiple strategies.

    Multiple preprocessing strategies are used because different approaches
    work better for different digits (especially 9, 11, and similar shapes).

    Strategy selection rationale:
    - Strategy 1 (High Contrast, Threshold 61): Best for crisp, clear digits
    - Strategy 2 (Medium Contrast, Low Threshold 40): Handles faded/thin text
    - Strategy 3 (Medium-High Contrast, Threshold 65): Balanced approach
    - Strategy 4 (Very High Contrast, Threshold 70): Handles noisy backgrounds
    - Strategy 5 (High Threshold 100): Eliminates artifacts, very clean digits only

    Values were empirically determined through testing with OSRS UI screenshots.
    """

    # Strategy 1: High contrast with medium threshold
    # Best for: Standard digits with good visibility
    # Resize: 5x for good detail preservation
    # Contrast: 4.0 for strong edges
    # Threshold: 61 (empirically determined optimal value)
    strategy_1: PreprocessingStrategy = PreprocessingStrategy(
        name="High Contrast",
        resize_multiplier=5,
        contrast_level=4.0,
        threshold=61
    )

    # Strategy 2: Medium contrast with low threshold
    # Best for: Faded or thin digits (e.g., when HP is low and text color changes)
    # Resize: 6x for maximum detail on thin strokes
    # Contrast: 3.0 for gentler enhancement
    # Threshold: 40 (lower to catch faint pixels)
    strategy_2: PreprocessingStrategy = PreprocessingStrategy(
        name="Medium Contrast Low Threshold",
        resize_multiplier=6,
        contrast_level=3.0,
        threshold=40
    )

    # Strategy 3: Medium-high contrast
    # Best for: Balanced detection across different digit types
    # Resize: 4x for speed while maintaining quality
    # Contrast: 3.5 for moderate enhancement
    # Threshold: 65 (slightly higher than strategy 1)
    strategy_3: PreprocessingStrategy = PreprocessingStrategy(
        name="Medium-High Contrast",
        resize_multiplier=4,
        contrast_level=3.5,
        threshold=65
    )

    # Strategy 4: Very high contrast
    # Best for: Noisy backgrounds or difficult lighting conditions
    # Resize: 5x for detail
    # Contrast: 5.0 for maximum edge detection
    # Threshold: 70 (higher to eliminate noise)
    strategy_4: PreprocessingStrategy = PreprocessingStrategy(
        name="Very High Contrast",
        resize_multiplier=5,
        contrast_level=5.0,
        threshold=70
    )

    # Strategy 5: High threshold for clean extraction
    # Best for: Eliminating artifacts and ensuring only clear digits pass
    # Resize: 5x for consistency
    # Contrast: 4.0 for strong definition
    # Threshold: 100 (very high to get only the clearest pixels)
    strategy_5: PreprocessingStrategy = PreprocessingStrategy(
        name="High Threshold Clean",
        resize_multiplier=5,
        contrast_level=4.0,
        threshold=100
    )

    def get_all_strategies(self) -> Tuple[PreprocessingStrategy, ...]:
        """Get all strategies as a tuple."""
        return (
            self.strategy_1,
            self.strategy_2,
            self.strategy_3,
            self.strategy_4,
            self.strategy_5
        )

    def get_strategy(self, index: int) -> PreprocessingStrategy:
        """
        Get a specific strategy by index (0-based).

        Args:
            index: Strategy index (0-4)

        Returns:
            PreprocessingStrategy

        Raises:
            IndexError: If index is out of range
        """
        strategies = self.get_all_strategies()
        if not 0 <= index < len(strategies):
            raise IndexError(
                f"Strategy index {index} out of range (0-{len(strategies)-1})"
            )
        return strategies[index]


# Global OCR preprocessing configuration instance
OCR_PREPROCESSING = OCRPreprocessingConfig()


# Shape detection constants for distinguishing problematic digits
@dataclass
class ShapeDetectionConfig:
    """
    Configuration for shape-based digit detection heuristics.

    Used to distinguish digits that OCR commonly confuses (especially 9 vs 4).
    """

    # Standard preprocessing size for shape detection
    # Larger size preserves shape details better
    shape_detection_size: Tuple[int, int] = (140, 140)

    # Hole detection thresholds
    # A "hole" is a closed white region surrounded by black (e.g., center of 9, 8, 6, 0)
    min_hole_count_for_nine: int = 1  # 9 has at least 1 hole (the circular part)

    # Tail fraction threshold
    # The "tail" is the bottom vertical stroke of a 9
    # Measured as fraction of total height
    min_tail_fraction_for_nine: float = 0.20  # 20% of height should be tail

    # Aspect ratio threshold
    # 9 is typically taller than it is wide
    min_aspect_ratio_for_nine: float = 1.0  # Height >= width

    # Consensus voting thresholds
    # How many strategies must agree for a "9" verdict
    min_nine_votes_for_correction: int = 2  # Majority of strategies

    # If OCR returned 9 in raw results and we have >=1 vote, trust it
    trust_ocr_with_single_vote: bool = True


# Global shape detection configuration
SHAPE_DETECTION = ShapeDetectionConfig()


# OCR smoothing and caching constants
@dataclass
class OCRSmoothingConfig:
    """Configuration for OCR result smoothing and caching."""

    # Default window size for consensus voting
    # Keeps last N readings and returns most common value
    default_window_size: int = 5

    # Default TTL (time-to-live) for cached OCR results in seconds
    # Prevents redundant OCR calls for rapidly repeated checks
    default_ttl_seconds: float = 0.5

    # Maximum allowed jump between readings
    # If new reading differs by more than this, it's likely an OCR error
    max_suspicious_jump: int = 30  # HP can't change by 30+ in one reading

    # Confidence threshold for logging
    # Log confidence percentage when it falls below this
    min_confidence_for_warning: float = 0.5  # 50%


# Global OCR smoothing configuration
OCR_SMOOTHING = OCRSmoothingConfig()


# Tesseract OCR configuration
@dataclass
class TesseractConfig:
    """Configuration for Tesseract OCR engine."""

    # OEM (OCR Engine Mode)
    # 3 = Default, based on what is available
    oem: int = 3

    # PSM (Page Segmentation Mode)
    # 7 = Treat the image as a single text line
    psm: int = 7

    # Character whitelist - only allow digits
    char_whitelist: str = "0123456789"

    def get_config_string(self) -> str:
        """Generate Tesseract config string."""
        return (
            f"--oem {self.oem} "
            f"--psm {self.psm} "
            f"-c tessedit_char_whitelist={self.char_whitelist}"
        )


# Global Tesseract configuration
TESSERACT_CONFIG = TesseractConfig()


# ============================================================================
# MOUSE & MOVEMENT CONSTANTS
# ============================================================================

@dataclass
class BezierCurveConfig:
    """Configuration for Bezier curve mouse movement."""

    # Control point randomization range
    # Control points are randomly offset by this amount to create natural curves
    control_point_offset_min: int = -100  # pixels
    control_point_offset_max: int = 100   # pixels

    # Minimum steps for smooth curve
    # Lower = faster but choppier, higher = smoother but slower
    min_steps: int = 10

    # Steps per second for curve interpolation
    # Higher = smoother movement, lower = faster
    steps_per_second: int = 60

    # Curve formula exponents (cubic Bezier)
    # Don't change these unless you understand Bezier mathematics
    cubic_power: int = 3
    quadratic_coefficient: int = 3


@dataclass
class MouseMovementConfig:
    """Configuration for mouse movement behavior."""

    # Speed multiplier for distance-based duration calculation
    # Movement time = base_speed * (1 + distance / distance_factor)
    distance_factor: int = 1000  # pixels

    # Overshoot behavior (human-like correction)
    overshoot_distance_min: int = 5   # pixels
    overshoot_distance_max: int = 20  # pixels
    overshoot_duration_fraction: float = 0.7  # Use 70% of time for overshoot
    correction_duration_fraction: float = 0.3  # Use 30% for correction
    correction_delay: float = 0.02  # seconds between overshoot and correction

    # Post-movement delays
    post_move_delay_min: float = 0.05  # seconds
    post_move_delay_max: float = 0.15  # seconds

    # Random movement radius for idle actions
    random_movement_radius: int = 50  # pixels


# Global mouse configuration instances
BEZIER_CURVE = BezierCurveConfig()
MOUSE_MOVEMENT = MouseMovementConfig()


# ============================================================================
# SCREEN & COLOR DETECTION CONSTANTS
# ============================================================================

@dataclass
class ColorDetectionConfig:
    """Configuration for color matching and detection."""

    # Default tolerance for color matching
    # How close a color needs to match (0 = exact, 255 = any color)
    default_tolerance: int = 10

    # Color similarity constants
    # Used for calculating how similar two colors are
    perfect_match: float = 1.0   # 100% match
    no_match: float = 0.0         # 0% match
    max_rgb_value: int = 255      # Maximum RGB channel value
    rgb_channels: int = 3         # Number of color channels (R, G, B)

    # Hex color conversion
    hex_base: int = 16  # Hexadecimal base
    hex_chunk_size: int = 2  # Bytes per color channel


# Global color detection configuration
COLOR_DETECTION = ColorDetectionConfig()


# ============================================================================
# GAME TIMING & LOOP CONSTANTS
# ============================================================================

@dataclass
class GameTimingConfig:
    """Configuration for game action timings and loops."""

    # Default wait times (seconds)
    # These are defaults when timing_type is not in config
    default_wait: float = 1.0

    # Default number of runs for scripts
    default_runs: int = 10

    # Banking loop constants
    deposit_items_max_attempts: int = 12  # Max items to deposit (inventory size)
    teleport_double_click_count: int = 2  # Double-click for teleport
    bank_click_attempts: int = 2          # Retries for bank booth click
    walk_to_marker_attempts: int = 2      # Walk retries

    # Menu/UI constants
    menu_banner_width: int = 60           # Character width for menu banners
    default_menu_runs: int = 10           # Default runs if user doesn't specify
    dev_mode_runs: int = 500              # Runs for dev/testing mode


# Global game timing configuration
GAME_TIMING = GameTimingConfig()


# ============================================================================
# COORDINATE & BOUNDS CONSTANTS
# ============================================================================

@dataclass
class CoordinateConfig:
    """Configuration for coordinate systems and bounds checking."""

    # Coordinate origin
    origin_x: int = 0
    origin_y: int = 0

    # Window array indexing
    first_window_index: int = 0  # Use first window if multiple found

    # Tuple unpacking indices
    r_index: int = 0  # Red channel index
    g_index: int = 1  # Green channel index
    b_index: int = 2  # Blue channel index

    # Pixel array slicing
    rgb_slice_end: int = 3  # Take first 3 channels (RGB, ignore alpha)


# Global coordinate configuration
COORDINATES = CoordinateConfig()


# ============================================================================
# OCR TEXT CLEANING CONSTANTS
# ============================================================================

def _get_default_ocr_replacements() -> Dict[str, str]:
    """Factory function for OCR character replacements."""
    return {
        # Misread as 1
        'i': '1', 'I': '1', 'l': '1', '|': '1',
        # Misread as 0
        'o': '0', 'O': '0', 'Q': '0', 'D': '0', 'd': '0',
        # Misread as 5
        'S': '5', 's': '5',
        # Misread as 2
        'Z': '2', 'z': '2',
        # Misread as 8
        'B': '8',
        # Misread as 9
        'g': '9', 'q': '9',
        # Misread as 6
        'G': '6',
        # Misread as 4
        'a': '4',
        # Whitespace removal
        ' ': '', '\n': '', '\r': '', '\t': '',
    }


@dataclass
class OCRCharacterReplacements:
    """Character replacements for OCR text cleaning."""

    # Common OCR misreads -> correct digit
    replacements: Dict[str, str] = field(default_factory=_get_default_ocr_replacements)


# Global OCR character replacements
OCR_CHAR_REPLACEMENTS = OCRCharacterReplacements()


# ============================================================================
# EXIT CODES
# ============================================================================

@dataclass
class ExitCodes:
    """Standard exit codes for the application."""

    success: int = 0
    config_error: int = 1
    window_error: int = 1
    script_error: int = 1
    user_interrupt: int = 0  # Keyboard interrupt is not an error


# Global exit codes
EXIT_CODES = ExitCodes()


# ============================================================================
# VALIDATION RANGES
# ============================================================================

@dataclass
class ValidationRanges:
    """Valid ranges for various game values."""

    # HP/Prayer/Energy ranges
    min_stat_value: int = 0
    max_stat_value: int = 99
    max_run_energy: int = 100  # Run energy goes to 100%

    # Color channel validation
    min_rgb_value: int = 0
    max_rgb_value: int = 255


# Global validation ranges
VALIDATION = ValidationRanges()


# ============================================================================
# TEMPLATE MATCHING CONSTANTS
# ============================================================================

@dataclass
class TemplateMatchingConfig:
    """Configuration for OpenCV template matching of UI elements."""

    # Directory containing template images
    templates_dir: str = "templates"

    # Default template matching threshold (0.0-1.0)
    # Higher = more strict matching, lower = more lenient
    default_threshold: float = 0.68

    # Default padding in pixels when subdividing grids
    # Prevents clicking too close to element edges
    default_padding: int = 4

    # Default TTL (time-to-live) for cached detections in seconds
    # For sticky elements like inventory that don't move
    default_ttl_seconds: float = 5.0

    # Inventory grid dimensions
    # OSRS inventory is 7 rows × 4 columns = 28 total slots
    inventory_rows: int = 7
    inventory_cols: int = 4
    inventory_total_slots: int = 28

    # Prayer tab grid dimensions
    # OSRS prayer tab is 6 rows × 5 columns = 30 total prayers
    prayer_rows: int = 6
    prayer_cols: int = 5
    prayer_total_slots: int = 30


# Global template matching configuration
TEMPLATE_MATCHING = TemplateMatchingConfig()