# OSRS Item Templates

This directory contains item templates for inventory item detection.

## Statistics

**Total Items Downloaded:** 365 out of 375 attempted (97.3% success rate)

## Failed Items (12)

These items could not be found on the wiki with the specified names:
- Super ranging(4), Super ranging(3), Super ranging(2), Super ranging(1)
- Super antipoison(4), Super antipoison(3), Super antipoison(2), Super antipoison(1)
- Skill cape
- Rune bolts
- Dragon bolts(e)
- Oak seed

**Note:** These items may have different names on the wiki. You can manually download them and place them in the `manual/` directory.

## Directory Structure

- `auto/` - Items scraped from the OSRS wiki (365 items)
- `manual/` - Manual override templates (checked first by ItemDetectionService)

## Categories Included

- ✅ Food (cooked and raw) - 20+ items
- ✅ Potions (all types, 4-dose to 1-dose) - 100+ items  
- ✅ Weapons (melee, ranged, magic) - 40+ items
- ✅ Armour (helmets, bodies, legs, shields, boots, gloves, capes, amulets, rings) - 50+ items
- ✅ Runes (elemental and combination) - 20+ items
- ✅ Arrows and Bolts - 15+ items
- ✅ Tools (mining, woodcutting, fishing, misc) - 20+ items
- ✅ Herbs (grimy and clean) - 24 items
- ✅ Seeds (herb, tree, fruit tree) - 25+ items
- ✅ Logs - 7 items
- ✅ Ores and Bars - 15+ items
- ✅ Gems - 7 items
- ✅ Misc (coins, scales, shards) - 10+ items

## Usage

Enable item detection in `config.json`:
```json
"item_detection": {
  "enabled": true,
  "items_dir": "src/osrsbot/images/items",
  "threshold": 0.75
}
```

## Manual Overrides

If a template doesn't match well or is missing, you can:
1. Screenshot the item from your game client (36×32 pixels)
2. Save as `{item_name}.png` (lowercase, underscores)
3. Place in `manual/` directory
4. ItemDetectionService will use your manual template instead

Example: `manual/shark.png` will override `auto/385_shark.png`

## Re-scraping

To re-scrape all items:
```bash
python tools/scrape_items.py --file tools/osrs_items_list.txt
```

To scrape specific categories:
```bash
python tools/scrape_items.py --common-food
python tools/scrape_items.py --common-potions
python tools/scrape_items.py --common-combat
```
