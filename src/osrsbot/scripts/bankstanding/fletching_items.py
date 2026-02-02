"""
Fletching item tier definitions.

Maps Fletching levels to the best bow to string at each tier.
Used by FletchingBot and menu.py to auto-select items based on player level.
"""

# Ordered highest-first so get_best_tier() returns the best available.
FLETCHING_TIERS = [
    {
        "min_level": 50,
        "tool_name": "bow string",
        "material_name": "maple shortbow (u)",
        "product_name": "maple shortbow",
    },
    {
        "min_level": 35,
        "tool_name": "bow string",
        "material_name": "willow shortbow (u)",
        "product_name": "willow shortbow",
    },
    {
        "min_level": 20,
        "tool_name": "bow string",
        "material_name": "oak shortbow (u)",
        "product_name": "oak shortbow",
    },
]


def get_best_tier(level: int) -> dict | None:
    """
    Return the highest bow tier the player can string.

    Args:
        level: Player's Fletching level.

    Returns:
        Tier dict with tool_name, material_name, product_name keys,
        or None if level is below 20.
    """
    for tier in FLETCHING_TIERS:
        if level >= tier["min_level"]:
            return tier
    return None
