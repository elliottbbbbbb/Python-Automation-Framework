# Basic NPC Killer Bot - Setup & Usage Guide

A simple combat bot that kills NPCs and loots until inventory is full.

---

## Features

- ✅ **Two detection methods**: Color detection or template matching
- ✅ Finds and attacks NPCs automatically
- ✅ Waits for combat to finish automatically
- ✅ Picks up loot using purple ground item highlights
- ✅ Stops when inventory is full
- ✅ Exit anytime with 'q' key
- ✅ Tracks kills and loot statistics

---

## NPC Detection Methods

The bot supports two ways to find NPCs:

### Method 1: Color Detection (Default, Recommended)

**How it works:**
- Uses RuneLite NPC Indicators plugin
- Finds NPCs by their highlight color (default: cyan)
- Fast and flexible

**Pros:**
- ✅ Works with any NPC (just highlight them)
- ✅ Very fast (single color scan)
- ✅ Easy to configure (just change color)
- ✅ No templates needed

**Cons:**
- ❌ Requires RuneLite plugin
- ❌ Can get false positives if other highlighted objects nearby

**Best for:** General purpose, farming multiple NPC types

### Method 2: Template Matching

**How it works:**
- Matches a screenshot of the NPC
- Finds exact visual match on screen
- More accurate but slower

**Pros:**
- ✅ Very accurate (only clicks specific NPC)
- ✅ No plugin needed
- ✅ Works with vanilla client

**Cons:**
- ❌ Need template image for each NPC type
- ❌ Slower than color detection
- ❌ Breaks if NPC animates/rotates significantly
- ❌ Doesn't work at different zoom levels

**Best for:** Single specific NPC, high accuracy requirements

---

## Prerequisites

### 1. RuneLite Plugins (for color detection)

**NPC Indicators Plugin:**
- Enable in RuneLite plugin hub
- Configure to highlight your target NPCs
- Default color: Cyan (`#00FFFF`)
- **Where to find:** RuneLite → Configuration → NPC Indicators

**Ground Items Plugin:**
- Enable in RuneLite
- Configure to highlight valuable loot in purple/pink
- Default color: Purple (`#ff00dc`)
- **Where to find:** RuneLite → Configuration → Ground Items

### 2. Game Setup

- Stand in a safe combat area with target NPCs nearby
- Ensure you have:
  - Weapon equipped
  - Armor equipped (optional but recommended)
  - Food in inventory (optional, for safety)
  - Empty inventory slots for loot

---

## How to Run

### Step 1: Configure NPC Color (Optional)

If your NPCs are highlighted with a different color, add this to `config.json`:

```json
{
  "colors": {
    "npc_target": "#00FFFF"
  }
}
```

Common NPC highlight colors:
- Cyan: `#00FFFF` (default)
- Red: `#FF0000`
- Green: `#00FF00`
- Yellow: `#FFFF00`

### Step 2: Choose Detection Method

**Option A: Color Detection (default, recommended)**
```bash
# Uses RuneLite NPC highlighting
python -m osrsbot
# Select option 8: Basic NPC Killer
# Bot will use color detection automatically
```

**Option B: Template Matching**
```python
# First, create NPC template:
# 1. Screenshot NPC (crop to ~64x64 pixels)
# 2. Save as src/osrsbot/images/bot/npcs/cow.png

# Then modify menu.py to use template:
runner.run_script(
    BasicNPCKiller,
    npc_detection_method="template",
    npc_template="src/osrsbot/images/bot/npcs/cow.png",
    runs=1
)
```

### Step 3: Configure Run Settings

The bot will ask:
- **Number of runs:** How many times to fill inventory (default: 1)
- Press Enter to start

### Step 4: Monitor Execution

The bot will:
1. Find nearest NPC (cyan highlight)
2. Click to attack
3. Wait for combat to finish
4. Look for loot (purple highlights)
5. Pick up loot
6. Repeat until inventory full

**To stop early:** Press `q` at any time

---

## Configuration Options

### Inventory Threshold

Stop when inventory has X items (default: 27):

```python
# In menu.py or when creating bot instance
runner.run_script(
    BasicNPCKiller,
    npc_color="#00FFFF",
    inventory_threshold=25  # Stop at 25 items instead of 27
)
```

### NPC Color

Change target NPC color:

```python
runner.run_script(
    BasicNPCKiller,
    npc_color="#FF0000",  # Red NPCs
    loot_color="#ff00dc"  # Purple loot (default)
)
```

---

## How It Works

### State Machine Flow

```
IDLE
  ↓
FIND_TARGET (search for colored NPC)
  ↓
ATTACK (click NPC)
  ↓
COMBAT (wait for combat to finish)
  ↓
LOOT (pick up purple items)
  ↓
Check inventory full? → No → FIND_TARGET
                      → Yes → COMPLETE
```

### NPC Detection

Uses color detection to find NPCs:

```python
# From basic_npc_killer.py
npc_match = self.screen.find_color(
    self.npc_color,      # Default: "#00FFFF" (cyan)
    tolerance=15,        # Allows slight color variance
    find_all=False       # Just find first NPC
)
```

**How it works:**
1. Takes screenshot of game window
2. Scans for cyan pixels (or your configured color)
3. Returns (x, y) coordinates of first match
4. Clicks that position to attack

### Loot Detection

Uses the `LootDetectionService`:

```python
# Finds purple ground item highlights
loot_found = self.actions.pickup_loot(tolerance=30)
```

**How it works:**
1. Scans screen for purple pixels (`#ff00dc`)
2. Clusters nearby pixels into single loot piles
3. Finds nearest loot to player position
4. Clicks it to pick up
5. Repeats until no more loot found

### Inventory Detection

Uses pixel-based slot checking:

```python
# Checks if inventory has >= 27 items
is_full = self.state.inventory_full(threshold=27)
```

**How it works:**
1. Checks center pixel of last inventory slot (slot 28)
2. Compares to empty slot background color (`#453c33`)
3. If pixel doesn't match → slot has item → inventory full
4. Very fast (single pixel check)

---

## Troubleshooting

### "No NPC found on screen"

**Causes:**
- NPCs not highlighted in RuneLite
- Wrong color configured
- NPCs too far away or off-screen

**Solutions:**
1. Check NPC Indicators plugin is enabled
2. Verify NPC highlight color matches config
3. Move closer to NPCs
4. Adjust `tolerance` parameter (increase to be more lenient)

### "No loot found this kill"

**Causes:**
- Ground Items plugin not highlighting loot
- Loot not valuable enough to be highlighted
- Loot despawned before bot could pick it up

**Solutions:**
1. Check Ground Items plugin is enabled
2. Lower minimum loot value threshold in RuneLite
3. Increase combat area size (so loot is closer)

### "Not in combat after clicking NPC"

**Causes:**
- NPC already in combat with someone else
- Click missed the NPC
- NPC moved before click registered

**Solutions:**
- Bot will retry automatically (up to 3 times)
- If persistent, adjust color tolerance or move closer

### "Inventory full" but inventory not actually full

**Causes:**
- Inventory detection failed
- Slot has item that looks like empty background

**Solutions:**
1. Check `config.json` has correct empty slot color
2. Adjust `inventory_threshold` to stop earlier (e.g., 26 instead of 27)
3. Ensure inventory tab is selected in RuneLite

---

## Performance Tips

### Faster Kill Times

1. Use better weapon/armor
2. Use combat potions (strength, attack, super combat)
3. Enable prayer (Piety, Rigour, Augury)

### More Loot Per Trip

1. Adjust `inventory_threshold=26` to leave room for bones/coins
2. Configure Ground Items plugin to only show valuable items
3. Use looting bag (if in Wilderness)

### Safer Botting

1. Start with short runs (1-2 inventory fills)
2. Use the bot in populated areas (less suspicious)
3. Vary your schedule (don't bot same time every day)
4. Monitor HP during combat (bot checks occasionally)

---

## Code Structure

### Main Bot Class

```python
class BasicNPCKiller(StateMachineBot):
    """Kills NPCs and loots until inventory full."""

    def _handle_find_target(self, context):
        # Find NPC using color detection
        npc_pos = self._find_npc()
        return StateResult.SUCCESS

    def _handle_attack(self, context):
        # Click NPC to attack
        self.mouse.click_at(npc_x, npc_y)
        return StateResult.SUCCESS

    def _handle_combat(self, context):
        # Wait for combat to finish
        while self._is_in_combat():
            self.actions.wait("medium")
        return StateResult.SUCCESS

    def _handle_loot(self, context):
        # Pick up loot
        for _ in range(5):  # Try 5 times
            self.actions.pickup_loot()
        return StateResult.SUCCESS
```

### Key Methods

**`_find_npc()`** - Uses `screen.find_color()` to locate NPCs

**`_is_in_combat()`** - Uses `state.in_combat()` to check combat status

**`_check_inventory_full()`** - Uses `state.inventory_full()` to check slots

**`actions.pickup_loot()`** - Uses `LootDetectionService` to find and click loot

---

## Example Run

```
Starting Basic NPC Killer...
IDLE: Starting NPC killer...
FIND_TARGET: Looking for NPC (kills: 0)...
Found NPC at (850, 420)
ATTACK: Attacking NPC (kills: 0)...
Clicking NPC at (850, 420)
Attack successful, entering combat
COMBAT: Fighting NPC (kills: 0)...
Combat finished! Total kills: 1
LOOT: Looting... (kills: 1, loots: 0)
Picked up loot! Total loots: 1
Picked up loot! Total loots: 2
No loot found (attempt 3/5)
Looted 2 items this kill
FIND_TARGET: Looking for NPC (kills: 1)...
...
(continues until inventory full)
...
Inventory full after looting, completing
COMPLETE: Finished! Kills: 15, Loots: 32
```

---

## Future Improvements

Potential enhancements (not yet implemented):

- [ ] Banking support (teleport, bank items, return)
- [ ] Food eating (when HP below threshold)
- [ ] Prayer potion drinking
- [ ] Special attack usage
- [ ] Multi-target selection (prioritize by distance/HP)
- [ ] Anti-PK detection (in Wilderness)
- [ ] Template matching for specific NPCs (more accurate than color)

---

## Related Files

- **Bot script:** `src/osrsbot/scripts/combat/basic_npc_killer.py`
- **Loot detection:** `src/osrsbot/services/loot_detection_service.py`
- **Inventory detection:** `src/osrsbot/queries/inventory_queries.py`
- **Combat detection:** `src/osrsbot/queries/combat_queries.py`
- **Menu entry:** `src/osrsbot/app/menu.py` (option 8)

---

**Last Updated:** 2026-01-09
**Status:** Ready for testing
**Tested:** No (untested skeleton)
