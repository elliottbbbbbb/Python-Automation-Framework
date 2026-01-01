# Known Issues to Fix

## 1. Combat Indicator Not Registered ❌

**Issue:** Combat detection expects a `combat_indicator` template but it doesn't exist.

**Location:** [game_queries.py:211](src/osrsbot/queries/game_queries.py#L211)

**Current Code:**
```python
def in_combat(self) -> bool:
    # Detect combat indicator template
    combat_result = self.template_service.find_button(
        "combat_indicator",
        threshold=0.7
    )
```

**Problem:**
- Template file `combat_indicator.png` doesn't exist
- Config has coordinates for it but no image template
- Falls back to color detection, but primary method fails

**Files Involved:**
- `src/osrsbot/queries/game_queries.py` (lines 192-251)
- `src/osrsbot/images/bot/combat/` - Missing `combat_indicator.png`
- `config.json` - Has coordinates but no template path

**Solutions:**

### Option 1: Create Combat Indicator Template (Recommended)
1. Capture screenshot of combat indicator (the swords icon when in combat)
2. Save as `src/osrsbot/images/bot/combat/combat_indicator.png`
3. Add to `config.json`:
```json
"ui_buttons": {
  "combat_indicator": {
    "path": "src/osrsbot/images/bot/combat/combat_indicator.png",
    "threshold": 0.75
  },
  ...
}
```

### Option 2: Use Color Detection Only
Remove template matching, rely only on color detection:
```python
def in_combat(self) -> bool:
    """Check if in combat using color detection only."""
    coord = self.config.get("coordinates", "checks", "combat_indicator")
    combat_green_hex = self.config.get("colors", "combat_indicator_green")
    combat_red_hex = self.config.get("colors", "combat_indicator_red")

    # Check for combat colors at indicator position
    # ... existing color detection code ...
```

**Recommendation:** Option 1 - More reliable with template + color validation

---

## 2. Inventory Detection Doesn't Work Correctly ❌

**Issue:** Inventory detection not accurately counting empty slots.

**Location:** [inventory_queries.py](src/osrsbot/queries/inventory_queries.py)

**Current Method:**
Uses color detection to check if slots are empty by sampling center pixel of each slot:
```python
def get_snapshot(self) -> InventorySnapshot:
    # Detect inventory grid
    grid = self.template_service.find_grid("inventory")

    # Sample each slot's center pixel
    for slot in grid.elements:
        center = slot.center()
        pixel_color = self.screen.get_pixel_color(center)

        # Check if pixel matches empty slot color
        if self._is_empty_slot_color(pixel_color):
            empty_slots.append(i)
```

**Problems:**
1. **Single pixel sampling** - Not reliable, items can have similar colors
2. **Empty slot color varies** - Depends on lighting, item transparency
3. **No validation** - Assumes template matching always finds grid

**Debug Steps:**
1. Check if inventory grid is being detected:
   ```python
   grid = state.inventory.template_service.find_grid("inventory")
   logger.info(f"Grid detected: {grid is not None}")
   ```

2. Check slot detection:
   ```python
   snapshot = state.inventory.get_snapshot()
   logger.info(f"Empty slots: {snapshot.empty_slots}")
   logger.info(f"Filled slots: {snapshot.filled_slots}")
   ```

3. Verify empty slot color in config:
   ```json
   "inventory": {
     "empty_slot_color": "#453c33",  // Check this matches your client
     "color_tolerance": 15
   }
   ```

**Solutions:**

### Option 1: Multi-Point Sampling
Sample multiple points per slot instead of just center:
```python
def _is_slot_empty(self, slot_rect: UIElement) -> bool:
    """Check if slot is empty by sampling multiple points."""
    sample_points = [
        slot_rect.center(),
        (slot_rect.center()[0] - 5, slot_rect.center()[1]),
        (slot_rect.center()[0] + 5, slot_rect.center()[1]),
        (slot_rect.center()[0], slot_rect.center()[1] - 5),
        (slot_rect.center()[0], slot_rect.center()[1] + 5),
    ]

    empty_count = 0
    for point in sample_points:
        color = self.screen.get_pixel_color(point)
        if self._is_empty_slot_color(color):
            empty_count += 1

    # Consider empty if majority of points match
    return empty_count >= 3
```

### Option 2: Template Matching for Items
Use template matching to detect known items:
```python
def get_snapshot(self) -> InventorySnapshot:
    # Detect grid
    grid = self.template_service.find_grid("inventory")

    # For each slot, try to match known item templates
    for i, slot in enumerate(grid.elements):
        # Check if any item template matches this slot
        has_item = self._detect_item_in_slot(slot)
        if has_item:
            filled_slots.append(i)
        else:
            empty_slots.append(i)
```

### Option 3: Edge Detection
Detect slot borders/edges to identify empty vs filled:
```python
def _is_slot_empty(self, slot_rect: UIElement) -> bool:
    """Check if slot is empty using edge detection."""
    # Capture slot region
    slot_img = self.screen.capture(region=slot_rect.to_tuple())

    # Convert to grayscale and detect edges
    gray = cv2.cvtColor(np.array(slot_img), cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    # Empty slots have minimal edges, items have many
    edge_density = np.sum(edges) / edges.size
    return edge_density < 0.05  # Threshold for "empty"
```

**Recommendation:** Option 1 (multi-point) as quick fix, Option 3 (edge detection) for best accuracy

---

## 3. Loot Detection Test Added ✅ COMPLETE

**Status:** Fixed - Added to comprehensive test bot

**Changes:**
- Added `TEST_LOOT_DETECTION` state
- Added `_handle_test_loot_detection()` handler
- Tests loot service availability and functionality
- Shows loot count and nearest loot position

**Test Coverage:**
1. ✅ Service availability check
2. ✅ Detect all loot on screen
3. ✅ Find nearest loot to player
4. ✅ Test different color tolerances

---

## 4. Green Dragons Loot System ✅ COMPLETE

**Status:** Fixed - Full loot detection integrated

**Changes:**
- Added `LOOT` state to state machine
- Added `_handle_loot()` handler
- Integrated `LootDetectionService`
- Proper architecture (uses `ScreenService`)

**Features:**
1. ✅ Automatic loot detection after kills
2. ✅ Picks up nearest items first
3. ✅ Returns to combat when no loot
4. ✅ Banks when inventory full
5. ✅ Zero dependency violations

---

## Priority Fixes

### 🔴 High Priority

1. **Combat Indicator** - Breaks combat detection
   - Impact: Can't detect when in combat
   - Fix: Create template or remove template check
   - Effort: 15 minutes

2. **Inventory Detection** - Inaccurate slot counting
   - Impact: Wrong inventory full/empty checks
   - Fix: Multi-point sampling or edge detection
   - Effort: 1-2 hours

### 🟡 Medium Priority

3. **Inventory Empty Color** - May need calibration
   - Impact: Detection accuracy
   - Fix: Capture actual empty slot color from your client
   - Effort: 5 minutes

---

## Testing Recommendations

### Test Combat Indicator
```bash
# Run comprehensive test bot
python -m osrsbot.scripts.comprehensive_state_bot_test

# Check combat test (Test 10/10)
# Should detect when attacking NPC
```

### Test Inventory Detection
```python
# In test script:
state = self.state
snapshot = state.inventory.get_snapshot()

logger.info(f"Total items: {snapshot.total_items}")
logger.info(f"Empty slots: {snapshot.empty_slots}")
logger.info(f"Filled slots: {snapshot.filled_slots}")

# Expected: Accurate count matching actual inventory
# Actual: May be incorrect due to color sampling issues
```

### Calibrate Empty Slot Color
```python
# Capture screenshot with inventory open
screenshot = state.screen.capture()

# Sample pixel from known empty slot
# Update config.json with correct color
```

---

## Code Quality Impact

### Before Fixes:
- ❌ Combat detection unreliable (missing template)
- ❌ Inventory detection inaccurate (single point sampling)
- ⚠️ Bots may bank too early or miss full inventory

### After Fixes:
- ✅ Combat detection reliable (template + color)
- ✅ Inventory detection accurate (multi-point or edge)
- ✅ Bots work efficiently

---

## Next Steps

1. **Fix Combat Indicator** (15 min)
   - Capture combat indicator screenshot
   - Add template to config
   - Test with comprehensive bot

2. **Fix Inventory Detection** (1-2 hours)
   - Implement multi-point sampling
   - Test with various inventory states
   - Calibrate empty slot color if needed

3. **Test Both Fixes** (30 min)
   - Run comprehensive test bot
   - Run green dragons bot
   - Verify accuracy

**Total Effort:** ~2-3 hours to fix everything properly
