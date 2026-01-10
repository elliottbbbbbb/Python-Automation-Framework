"""
CLI tool to scrape OSRS item images from wiki.

Usage:
    python tools/scrape_items.py --items "Shark,Lobster,Tuna"
    python tools/scrape_items.py --file items_list.txt
    python tools/scrape_items.py --common-food  # Scrape common food items
    python tools/scrape_items.py --common-potions  # Scrape common potions

Examples:
    # Scrape specific items
    python tools/scrape_items.py --items "Shark,Lobster,Tuna,Swordfish"

    # Scrape from file (one item per line, format: "id,name")
    python tools/scrape_items.py --file tools/common_items.txt

    # Scrape common food items
    python tools/scrape_items.py --common-food

    # Scrape common potions
    python tools/scrape_items.py --common-potions
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from osrsbot.scrapers.wiki_item_scraper import WikiItemScraper


# Predefined common items
COMMON_FOOD = [
    (385, "Shark"),
    (373, "Swordfish"),
    (379, "Lobster"),
    (361, "Tuna"),
    (329, "Salmon"),
    (333, "Trout"),
    (7946, "Monkfish"),
    (385, "Manta ray"),
    (3144, "Karambwan"),
]

COMMON_POTIONS = [
    (2428, "Attack potion"),
    (113, "Strength potion"),
    (2432, "Defence potion"),
    (3024, "Super attack"),
    (157, "Super strength"),
    (163, "Super defence"),
    (2436, "Super restore"),
    (3040, "Prayer potion"),
    (139, "Antifire potion"),
    (2444, "Ranging potion"),
    (3034, "Super ranging"),
    (3042, "Magic potion"),
    (121, "Energy potion"),
    (3010, "Super energy"),
    (3018, "Stamina potion"),
]

COMMON_COMBAT_GEAR = [
    (4587, "Dragon scimitar"),
    (11806, "Saradomin godsword"),
    (11732, "Dragon boots"),
    (6570, "Fire cape"),
    (1079, "Rune platebody"),
    (1127, "Rune platelegs"),
    (1163, "Rune full helm"),
]

COMMON_TOOLS = [
    (1265, "Bronze pickaxe"),
    (1351, "Bronze axe"),
    (303, "Fishing rod"),
    (307, "Lobster pot"),
    (309, "Fishing net"),
    (311, "Harpoon"),
]


def main():
    parser = argparse.ArgumentParser(
        description="Scrape OSRS item images from wiki",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--items", help='Comma-separated item names (e.g., "Shark,Lobster,Tuna")'
    )
    parser.add_argument(
        "--file", help="File containing item IDs and names (format: id,name per line)"
    )
    parser.add_argument(
        "--common-food", action="store_true", help="Scrape common food items"
    )
    parser.add_argument(
        "--common-potions", action="store_true", help="Scrape common potions"
    )
    parser.add_argument(
        "--common-combat", action="store_true", help="Scrape common combat gear"
    )
    parser.add_argument(
        "--common-tools", action="store_true", help="Scrape common tools"
    )
    parser.add_argument(
        "--all-common", action="store_true", help="Scrape all common items"
    )
    parser.add_argument(
        "--output-dir",
        default="src/osrsbot/images/items/auto",
        help="Output directory for images (default: src/osrsbot/images/items/auto)",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    # Initialize scraper
    scraper = WikiItemScraper(output_dir=args.output_dir)

    # Build item list
    item_list = []

    if args.items:
        # Parse comma-separated items
        items = [item.strip() for item in args.items.split(",")]
        # Auto-generate IDs (starting from 1000 for manual items)
        for i, item_name in enumerate(items):
            item_list.append((1000 + i, item_name))

    elif args.file:
        # Read from file
        with open(args.file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "," in line:
                    item_id, item_name = line.split(",", 1)
                    item_list.append((int(item_id), item_name.strip()))

    elif args.common_food:
        item_list = COMMON_FOOD

    elif args.common_potions:
        item_list = COMMON_POTIONS

    elif args.common_combat:
        item_list = COMMON_COMBAT_GEAR

    elif args.common_tools:
        item_list = COMMON_TOOLS

    elif args.all_common:
        item_list = COMMON_FOOD + COMMON_POTIONS + COMMON_COMBAT_GEAR + COMMON_TOOLS

    else:
        parser.print_help()
        print("\nError: Must specify --items, --file, or one of the --common-* options")
        return 1

    # Scrape items
    print(f"Scraping {len(item_list)} items...")
    results = scraper.scrape_batch(item_list, rate_limit=args.rate_limit)

    # Print summary
    successful = sum(1 for v in results.values() if v)
    print(f"\n=== Scraping Complete ===")
    print(f"Successful: {successful}/{len(item_list)}")
    print(f"Output directory: {args.output_dir}")

    # List failed items
    failed = [name for name, success in results.items() if not success]
    if failed:
        print(f"\nFailed items:")
        for name in failed:
            print(f"  - {name}")

    return 0 if successful == len(item_list) else 1


if __name__ == "__main__":
    sys.exit(main())
