"""
Fletching item tier definitions.

Maps Fletching levels to the best bow to string at each tier.
Used by FletchingBot and menu.py to auto-select items based on player level.

Stringing levels from the OSRS Wiki:
  5 shortbow, 10 longbow, 20 oak short, 25 oak long,
  35 willow short, 40 willow long, 50 maple short, 55 maple long,
  65 yew short, 70 yew long, 80 magic short, 85 magic long.
"""

# Ordered highest-first so get_best_tier() returns the best available.
FLETCHING_TIERS = [
    {
        "min_level": 85,
        "tool_name": "bow string",
        "material_name": "magic longbow (u)",
        "product_name": "magic longbow",
    },
    {
        "min_level": 80,
        "tool_name": "bow string",
        "material_name": "magic shortbow (u)",
        "product_name": "magic shortbow",
    },
    {
        "min_level": 70,
        "tool_name": "bow string",
        "material_name": "yew longbow (u)",
        "product_name": "yew longbow",
    },
    {
        "min_level": 65,
        "tool_name": "bow string",
        "material_name": "yew shortbow (u)",
        "product_name": "yew shortbow",
    },
    {
        "min_level": 55,
        "tool_name": "bow string",
        "material_name": "maple longbow (u)",
        "product_name": "maple longbow",
    },
    {
        "min_level": 50,
        "tool_name": "bow string",
        "material_name": "maple shortbow (u)",
        "product_name": "maple shortbow",
    },
    {
        "min_level": 40,
        "tool_name": "bow string",
        "material_name": "willow longbow (u)",
        "product_name": "willow longbow",
    },
    {
        "min_level": 35,
        "tool_name": "bow string",
        "material_name": "willow shortbow (u)",
        "product_name": "willow shortbow",
    },
    {
        "min_level": 25,
        "tool_name": "bow string",
        "material_name": "oak longbow (u)",
        "product_name": "oak longbow",
    },
    {
        "min_level": 20,
        "tool_name": "bow string",
        "material_name": "oak shortbow (u)",
        "product_name": "oak shortbow",
    },
    {
        "min_level": 10,
        "tool_name": "bow string",
        "material_name": "longbow (u)",
        "product_name": "longbow",
    },
    {
        "min_level": 5,
        "tool_name": "bow string",
        "material_name": "shortbow (u)",
        "product_name": "shortbow",
    },
]


def get_best_tier(level: int) -> dict | None:
    """
    Return the highest bow tier the player can string.

    Args:
        level: Player's Fletching level.

    Returns:
        Tier dict with tool_name, material_name, product_name keys,
        or None if level is below 5.
    """
    for tier in FLETCHING_TIERS:
        if level >= tier["min_level"]:
            return tier
    return None
