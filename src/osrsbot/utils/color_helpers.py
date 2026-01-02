"""
Color utility functions for RGB/Hex conversion and color matching.

Provides shared color manipulation utilities used across services and queries.
"""

from typing import Tuple


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """
    Convert hex color string to RGB tuple.

    Args:
        hex_color: Hex color string (e.g., "#FF0000" or "FF0000")

    Returns:
        RGB tuple (r, g, b) with values 0-255

    Example:
        >>> hex_to_rgb("#FF0000")
        (255, 0, 0)
        >>> hex_to_rgb("00FF00")
        (0, 255, 0)
    """
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """
    Convert RGB values to hex color string.

    Args:
        r: Red value (0-255)
        g: Green value (0-255)
        b: Blue value (0-255)

    Returns:
        Hex color string with leading #

    Example:
        >>> rgb_to_hex(255, 0, 0)
        '#FF0000'
    """
    return f"#{r:02X}{g:02X}{b:02X}"


def color_distance(color1: Tuple[int, int, int], color2: Tuple[int, int, int]) -> float:
    """
    Calculate Euclidean distance between two RGB colors.

    Args:
        color1: First RGB tuple
        color2: Second RGB tuple

    Returns:
        Distance value (0 = identical colors, ~441 = max distance)

    Example:
        >>> color_distance((255, 0, 0), (255, 0, 0))
        0.0
        >>> color_distance((0, 0, 0), (255, 255, 255))
        441.67...
    """
    return sum((c1 - c2) ** 2 for c1, c2 in zip(color1, color2)) ** 0.5


def colors_match(
    color1: Tuple[int, int, int], color2: Tuple[int, int, int], tolerance: int = 10
) -> bool:
    """
    Check if two colors match within tolerance.

    Args:
        color1: First RGB tuple
        color2: Second RGB tuple
        tolerance: Maximum allowed difference per channel (0-255)

    Returns:
        True if colors match within tolerance

    Example:
        >>> colors_match((255, 0, 0), (250, 5, 5), tolerance=10)
        True
        >>> colors_match((255, 0, 0), (200, 0, 0), tolerance=10)
        False
    """
    return all(abs(c1 - c2) <= tolerance for c1, c2 in zip(color1, color2))
