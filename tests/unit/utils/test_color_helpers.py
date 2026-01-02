"""
Unit tests for color_helpers utility functions.

Tests RGB/hex conversion, color distance calculation, and color matching.
"""


from osrsbot.utils.color_helpers import (
    color_distance,
    colors_match,
    hex_to_rgb,
    rgb_to_hex,
)


class TestHexToRgb:
    """Test hex to RGB conversion."""

    def test_hex_with_hash(self):
        """Test conversion with leading #."""
        assert hex_to_rgb("#FF0000") == (255, 0, 0)

    def test_hex_without_hash(self):
        """Test conversion without leading #."""
        assert hex_to_rgb("FF0000") == (255, 0, 0)

    def test_lowercase_hex(self):
        """Test conversion with lowercase hex."""
        assert hex_to_rgb("#ff0000") == (255, 0, 0)

    def test_mixed_case(self):
        """Test conversion with mixed case hex."""
        assert hex_to_rgb("#Ff00Aa") == (255, 0, 170)


class TestRgbToHex:
    """Test RGB to hex conversion."""

    def test_basic_conversion(self):
        """Test basic RGB to hex conversion."""
        assert rgb_to_hex(255, 0, 0) == "#FF0000"

    def test_zero_values(self):
        """Test conversion with all zeros (black)."""
        assert rgb_to_hex(0, 0, 0) == "#000000"

    def test_max_values(self):
        """Test conversion with max values (white)."""
        assert rgb_to_hex(255, 255, 255) == "#FFFFFF"


class TestColorDistance:
    """Test Euclidean color distance calculation."""

    def test_identical_colors(self):
        """Test distance between identical colors is 0."""
        assert color_distance((255, 0, 0), (255, 0, 0)) == 0.0

    def test_black_white_distance(self):
        """Test maximum distance (black to white)."""
        distance = color_distance((0, 0, 0), (255, 255, 255))
        # sqrt(255^2 + 255^2 + 255^2) ≈ 441.67
        assert 441 < distance < 442

    def test_similar_colors(self):
        """Test distance between similar colors is small."""
        distance = color_distance((255, 0, 0), (250, 5, 5))
        # sqrt(5^2 + 5^2 + 5^2) ≈ 8.66
        assert distance < 10


class TestColorsMatch:
    """Test color matching with tolerance."""

    def test_exact_match(self):
        """Test exact color match (no tolerance needed)."""
        assert colors_match((255, 0, 0), (255, 0, 0), tolerance=10)

    def test_within_tolerance(self):
        """Test colors within tolerance match."""
        # Difference: 5 units per channel, tolerance: 10
        assert colors_match((255, 0, 0), (250, 5, 5), tolerance=10)

    def test_outside_tolerance(self):
        """Test colors outside tolerance don't match."""
        # Difference: 15 units per channel, tolerance: 10
        assert not colors_match((255, 0, 0), (240, 0, 0), tolerance=10)
