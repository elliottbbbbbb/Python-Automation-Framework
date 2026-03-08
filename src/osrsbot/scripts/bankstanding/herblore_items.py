"""
Herblore potion tier definitions.

Maps Herblore levels to the best potion to make at each tier.
Used by HerbloreBot and menu.py to auto-select items based on player level.

Potion recipes from the OSRS Wiki — combining unfinished potions with
secondary ingredients:
  3 attack potion, 5 antipoison, 12 strength potion, 22 restore potion,
  26 energy potion, 34 agility potion, 36 combat potion, 38 prayer potion,
  45 super attack, 48 superantipoison, 50 fishing potion, 52 super energy,
  53 hunter potion, 55 super strength, 63 super restore, 66 super defence,
  69 antifire potion, 72 ranging potion, 76 magic potion, 78 zamorak brew,
  81 saradomin brew.
"""

# Ordered highest-first so get_best_tier() returns the best available.
HERBLORE_TIERS = [
    {
        "min_level": 81,
        "tool_name": "toadflax potion (unf)",
        "material_name": "crushed nest",
        "product_name": "saradomin brew",
    },
    {
        "min_level": 78,
        "tool_name": "torstol potion (unf)",
        "material_name": "jangerberries",
        "product_name": "zamorak brew",
    },
    {
        "min_level": 76,
        "tool_name": "lantadyme potion (unf)",
        "material_name": "potato cactus",
        "product_name": "magic potion",
    },
    {
        "min_level": 72,
        "tool_name": "dwarf weed potion (unf)",
        "material_name": "wine of zamorak",
        "product_name": "ranging potion",
    },
    {
        "min_level": 69,
        "tool_name": "lantadyme potion (unf)",
        "material_name": "dragon scale dust",
        "product_name": "antifire potion",
    },
    {
        "min_level": 66,
        "tool_name": "cadantine potion (unf)",
        "material_name": "white berries",
        "product_name": "super defence",
    },
    {
        "min_level": 63,
        "tool_name": "snapdragon potion (unf)",
        "material_name": "red spiders eggs",
        "product_name": "super restore",
    },
    {
        "min_level": 55,
        "tool_name": "kwuarm potion (unf)",
        "material_name": "limpwurt root",
        "product_name": "super strength",
    },
    {
        "min_level": 53,
        "tool_name": "avantoe potion (unf)",
        "material_name": "kebbit teeth dust",
        "product_name": "hunter potion",
    },
    {
        "min_level": 52,
        "tool_name": "avantoe potion (unf)",
        "material_name": "mort myre fungus",
        "product_name": "super energy",
    },
    {
        "min_level": 50,
        "tool_name": "avantoe potion (unf)",
        "material_name": "snape grass",
        "product_name": "fishing potion",
    },
    {
        "min_level": 48,
        "tool_name": "irit potion (unf)",
        "material_name": "unicorn horn dust",
        "product_name": "superantipoison",
    },
    {
        "min_level": 45,
        "tool_name": "irit potion (unf)",
        "material_name": "eye of newt",
        "product_name": "super attack",
    },
    {
        "min_level": 38,
        "tool_name": "ranarr potion (unf)",
        "material_name": "snape grass",
        "product_name": "prayer potion",
    },
    {
        "min_level": 36,
        "tool_name": "harralander potion (unf)",
        "material_name": "goat horn dust",
        "product_name": "combat potion",
    },
    {
        "min_level": 34,
        "tool_name": "toadflax potion (unf)",
        "material_name": "toad legs",
        "product_name": "agility potion",
    },
    {
        "min_level": 26,
        "tool_name": "harralander potion (unf)",
        "material_name": "chocolate dust",
        "product_name": "energy potion",
    },
    {
        "min_level": 22,
        "tool_name": "harralander potion (unf)",
        "material_name": "red spiders eggs",
        "product_name": "restore potion",
    },
    {
        "min_level": 12,
        "tool_name": "tarromin potion (unf)",
        "material_name": "limpwurt root",
        "product_name": "strength potion",
    },
    {
        "min_level": 5,
        "tool_name": "marrentill potion (unf)",
        "material_name": "unicorn horn dust",
        "product_name": "antipoison",
    },
    {
        "min_level": 3,
        "tool_name": "guam potion (unf)",
        "material_name": "eye of newt",
        "product_name": "attack potion",
    },
]


def get_best_tier(level: int) -> dict | None:
    """
    Return the highest potion tier the player can make.

    Args:
        level: Player's Herblore level.

    Returns:
        Tier dict with tool_name, material_name, product_name keys,
        or None if level is below 3.
    """
    for tier in HERBLORE_TIERS:
        if level >= tier["min_level"]:
            return tier
    return None
