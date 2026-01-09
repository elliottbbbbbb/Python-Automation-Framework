# Zulrah Bot Implementation Summary

## Overview

Complete implementation of a Zulrah boss bot using a hybrid approach:
- **Color-coded RuneLite tile markers** for safe spot navigation
- **Computer vision** for Zulrah form detection and combat
- **State machine architecture** for fight management

## Implementation Status: ✅ COMPLETE

All tasks completed:
- ✅ Filled in rotation phase data for all 4 rotations (43 total phases)
- ✅ Created ZulrahDetector helper class (215 lines)
- ✅ Created ZulrahNavigator helper class (124 lines)
- ✅ Created ZulrahCombatManager helper class (268 lines)
- ✅ Refactored ZulrahBot main class (543 lines)
- ✅ Added to menu.py (Option 7)
- ✅ Created bosses/__init__.py package file
- ✅ Verified all method calls exist in codebase
- ✅ Fixed attack_zulrah() to use proper color detection

## Architecture

### File Structure
```
src/osrsbot/scripts/bosses/
├── __init__.py                    # Package exports
├── zulrah.py                      # Main bot (543 lines)
├── zulrah_detector.py             # CV detection (215 lines)
├── zulrah_navigator.py            # Movement (124 lines)
└── zulrah_combat_manager.py       # Combat (268 lines)
```

### Class Diagram
```
ZulrahBot (StateMachineBot)
├── ZulrahFightManager         # Rotation tracking
├── ZulrahDetector             # Computer vision
│   └── ScreenService          # Color detection
├── ZulrahNavigator            # Movement
│   ├── MouseService           # Clicking
│   └── ZulrahDetector         # Tile detection
└── ZulrahCombatManager        # Combat
    ├── GameActions            # Actions
    ├── StatQueries            # HP/Prayer
    └── ScreenService          # Color detection
```

## How It Works

### 1. Rotation Identification
- Observes first 2-4 phases of fight
- Detects Zulrah form (serpentine/tanzanite/magma) and position
- Matches observed patterns to one of 4 rotation patterns
- Switches to combat mode once rotation identified

### 2. Safe Spot Navigation
- Each phase has a `safe_position` (e.g., "west", "middle", "south")
- Bot looks up tile color from config: `tile_colors["west"]` → `#0000FF` (Blue)
- Clicks on the blue tile marker using color detection
- Verifies position by checking proximity to tile marker

### 3. Combat Management
- **Prayer Switching**: Activates protect_magic/ranged/melee based on phase
- **Gear Switching**: Swaps between mage and range gear (inventory slots 20/21)
- **Attacking**: Uses color detection to find and click Zulrah
  - Serpentine: `#006400` (dark green)
  - Tanzanite: `#4169E1` (royal blue)
  - Magma: `#DC143C` (crimson red)
- **HP Management**: Eats food when HP < 40
- **Prayer Management**: Drinks prayer potions when prayer < 20

### 4. Snakeling Handling
- Detects snakelings using color detection
- Attacks nearest snakeling during snakeling phases
- Returns to attacking Zulrah after snakelings cleared

## Configuration

All settings in `config.json` under `"zulrah"` section:

### Tile Colors (Universal for All Rotations)
```json
"tile_colors": {
  "middle": "#FF0000",           // Red
  "south": "#00FF00",            // Green
  "west": "#0000FF",             // Blue
  "east": "#FFFF00",             // Yellow
  "pillar_west_side": "#00FFFF", // Cyan
  "pillar_east_side": "#FF00FF", // Magenta
  "north": "#FFA500",            // Orange
  "starting_area": "#800080"     // Purple
}
```

### Rotation Data
Each rotation has 10-11 phases with:
- `phase_num`: Phase number (1-11)
- `safe_position`: Which tile to stand on (e.g., "west")
- `prayer`: Which prayer to use (e.g., "protect_ranged")
- `attack_style`: Mage or range (e.g., "mage")
- `form`: Zulrah's form (serpentine/tanzanite/magma)
- `spawns_snakelings`: Boolean - does this phase spawn snakelings?

### Form Colors (for Attacking)
```json
"form_colors": {
  "serpentine": "#006400",  // Dark green
  "tanzanite": "#4169E1",   // Royal blue
  "magma": "#DC143C"        // Crimson red
}
```

### Thresholds
```json
"hp_threshold": 40,              // Eat when HP < 40
"prayer_threshold": 20,          // Drink when prayer < 20
"food_slot": 1,                  // Inventory slot for food
"prayer_potion_slot": 2,         // Inventory slot for prayer pots
"teleport_threshold_hp": 15,     // Emergency teleport at HP < 15
"color_tolerance": 30            // RGB tolerance for color matching
```

## State Machine

### States
1. **START** - Initialize fight
2. **IDENTIFY_ROTATION** - Observe phases to determine rotation
3. **POSITION_FOR_PHASE** - Move to safe spot
4. **SWITCH_GEAR_PRAYER** - Equip correct gear and prayer
5. **ATTACK_ZULRAH** - Attack Zulrah until phase complete
6. **KILL_SNAKELINGS** - Handle snakeling spawns
7. **EAT_FOOD** - Consume food when HP low
8. **DRINK_PRAYER** - Drink prayer potion when prayer low
9. **LOOT** - Collect drops after kill
10. **END** - Reset for next kill

### Dynamic State Transitions
Priority order:
1. **Survival** - Food/prayer takes priority over everything
2. **Snakelings** - Kill snakelings during snakeling phases
3. **Phase Progression** - Move through phase sequence
4. **Normal Flow** - Attack Zulrah

Example logic:
```python
# Always check HP first
if hp < 40:
    return EAT_FOOD

# Then check prayer
if prayer < 20:
    return DRINK_PRAYER

# Then check for snakelings
if current_phase.spawns_snakelings and snakelings_detected:
    return KILL_SNAKELINGS

# Normal combat flow
if zulrah_visible:
    return ATTACK_ZULRAH
```

## Setup Requirements

### In-Game Setup (RuneLite)
1. Enter Zulrah instance
2. Mark all safe spot tiles with colored markers:
   - Middle tile: Red (#FF0000)
   - South tile: Green (#00FF00)
   - West tile: Blue (#0000FF)
   - East tile: Yellow (#FFFF00)
   - Pillar west side: Cyan (#00FFFF)
   - Pillar east side: Magenta (#FF00FF)
   - North tile: Orange (#FFA500)
   - Starting area: Purple (#800080)

### Inventory Setup
- Slot 1: Food (sharks/mantas)
- Slot 2: Prayer potions
- Slots 3-19: Mix of supplies
- Slot 20: Mage weapon (e.g., Trident)
- Slot 21: Range weapon (e.g., Blowpipe)
- Remaining slots: Switches, antivenom, etc.

### Prayer Book
- Protect from Magic
- Protect from Ranged
- Protect from Melee

## Method Audit Results

All 38 method calls verified as existing:
- ✅ All `GameActions` methods exist
- ✅ All `CombatActions` methods exist
- ✅ All `StatQueries` methods exist
- ✅ All `MouseService` methods exist
- ✅ All `ScreenService` methods exist
- ✅ All custom Zulrah component methods exist

## Attack Zulrah Implementation (Option 3)

Uses **direct color detection** approach:

```python
def attack_zulrah(self) -> bool:
    """Click on Zulrah using color detection."""

    # Get form colors from config
    form_colors = config.get("form_colors")  # serpentine, tanzanite, magma
    tolerance = 30  # RGB tolerance

    # Try each form color
    for form_name, hex_color in form_colors.items():
        match = screen.find_color(hex_color, tolerance)

        if match:
            # Found Zulrah - click it
            mouse.move_to(match.x, match.y, move_style="curved")
            mouse.click()
            return True

    return False  # Zulrah not visible (submerged)
```

**Why this approach:**
- Simple and reliable
- Zulrah has very distinct colors (green/blue/red)
- Works even when Zulrah is partially obscured
- Fast detection (no template matching overhead)

**Potential upgrade path:**
If you encounter issues with accidentally clicking snakelings, upgrade to **right-click menu approach**:
1. Find Zulrah color
2. Right-click on it
3. Use OCR or fixed offset to click "Attack Zulrah" option

## Testing Checklist

### Phase 1: Single Rotation Test
- [ ] Bot identifies rotation correctly
- [ ] All phases execute in order
- [ ] Prayer switches work (verify with prayer icons)
- [ ] Safe spot navigation works (verify with tile markers)
- [ ] Attacks Zulrah successfully
- [ ] Handles snakelings when they spawn
- [ ] Eats food when HP low
- [ ] Drinks prayer potions when prayer low

### Phase 2: All Rotations Test
- [ ] Rotation 1 completes successfully
- [ ] Rotation 2 completes successfully
- [ ] Rotation 3 completes successfully
- [ ] Rotation 4 completes successfully

### Phase 3: Edge Cases
- [ ] Handles death gracefully
- [ ] Handles running out of food
- [ ] Handles running out of prayer potions
- [ ] Handles rotation misidentification
- [ ] Handles missing tile markers

## Known Limitations

1. **Tile Markers Required**: Bot won't work without properly configured RuneLite tile markers
2. **Gear Switching**: Currently uses fixed inventory slots (20, 21) - needs manual setup
3. **Banking**: Not yet implemented - manual banking required
4. **Death Recovery**: Not yet implemented - manual restart required
5. **Loot Detection**: Placeholder implementation - may need enhancement

## Future Enhancements

### Priority 1 (Required for Full Automation)
- [ ] Implement banking logic
- [ ] Implement death recovery
- [ ] Implement loot detection/collection

### Priority 2 (Quality of Life)
- [ ] Add spec weapon usage
- [ ] Add venom/poison management
- [ ] Add kill tracking and profit calculation
- [ ] Add performance metrics logging

### Priority 3 (Advanced)
- [ ] Auto-detect gear slots instead of hardcoding
- [ ] Add rotation pattern learning (improve identification)
- [ ] Add emergency teleport logic
- [ ] Add multi-account support

## Running the Bot

1. Launch menu: `python -m osrsbot.app.menu`
2. Select option: `7. Zulrah Boss Bot`
3. Enter number of kills (default: 999)
4. Press Enter to start

Bot will:
1. Start fight
2. Identify rotation (2-4 phases)
3. Execute all phases
4. Loot and repeat

Press `Ctrl+C` to stop safely.

## Logs

All activity logged to: `bot_debug.log`

Log levels:
- **INFO**: Phase transitions, kills, important events
- **DEBUG**: Detailed detection results, positions
- **WARNING**: Failed detections, retries
- **ERROR**: Critical failures

## Support

For issues or questions:
- Check logs first: `bot_debug.log`
- Verify tile marker setup
- Verify config.json has all rotation data
- Ensure RuneLite is focused and visible
- Check that form colors match your game (may need calibration)

---

**Status**: Ready for testing! 🐍
