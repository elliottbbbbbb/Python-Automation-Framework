# Dynamic Image Detection Guide

This guide explains different techniques for detecting objects that change appearance, rotation, or scale.

## Comparison: Different Detection Methods

| Method | Speed | Rotation Invariant | Scale Invariant | Use Case |
|--------|-------|-------------------|-----------------|----------|
| **Template Matching** | Fast (1-5ms) | ❌ No | ❌ No | Static UI, inventory items |
| **Multi-Template** | Medium (5-25ms) | ❌ No | ⚠️ Limited | Multiple zoom levels |
| **Color Detection** | Very Fast (<1ms) | ✅ Yes | ✅ Yes | NPCs, highlighted objects |
| **Feature Matching (ORB)** | Slow (10-50ms) | ✅ Yes | ✅ Yes | Rotated/scaled objects |
| **Deep Learning** | Very Slow (50-200ms) | ✅ Yes | ✅ Yes | Complex recognition |

## 1. Color Detection (Recommended for OSRS)

**Best for:** Moving NPCs, highlighted objects, items with unique colors

**Your existing system:**
```python
# Attack NPCs using RuneLite's highlighting
self.actions.attack_npc("green_dragon")  # Uses color "#00ffff"
self.actions.click_color_smart("zulrah_serpentine")

# Click items by color
self.actions.eat_food("manta_ray")  # Color-based inventory click
```

**Advantages:**
- ✅ Extremely fast
- ✅ Works at any angle/rotation
- ✅ Works at any zoom level
- ✅ RuneLite provides highlighting
- ✅ Simple to configure

**Disadvantages:**
- ❌ Requires unique colors
- ❌ Can match wrong objects if colors overlap
- ❌ Lighting changes can affect accuracy

**When to use:**
- NPCs (with RuneLite highlighting)
- Items with distinctive colors
- Objects that move or rotate

## 2. Standard Template Matching (Current System)

**Best for:** Static UI elements, inventory items at fixed zoom

**Your existing system:**
```python
# Works great for inventory items
self.actions.click_template("images/bot/items/overload.png", "overload")
```

**Advantages:**
- ✅ Fast (1-5ms)
- ✅ Precise matching
- ✅ Simple to implement

**Disadvantages:**
- ❌ Requires exact size match
- ❌ Breaks with rotation
- ❌ Breaks with zoom changes

**When to use:**
- Inventory items (users have fixed zoom)
- UI buttons
- Bank items
- Any static, non-rotating content

## 3. Multi-Template Matching (Enhanced System)

**Best for:** Items that appear at different zoom levels

**Your new system:**
```python
# Handles different zoom levels
self.actions.click_template([
    "custom:item_zoom1.png",
    "custom:item_zoom2.png",
    "custom:item_zoom3.png"
], "item")
```

**Advantages:**
- ✅ Handles multiple zoom levels
- ✅ Still relatively fast (5-25ms for 3-5 templates)
- ✅ No code changes needed

**Disadvantages:**
- ❌ Requires creating multiple templates
- ❌ Still breaks with rotation
- ❌ Slower than single template

**When to use:**
- Users have different zoom settings
- Items that appear at various scales
- Maximum compatibility needed

## 4. Feature Matching (NEW - ORB/SIFT)

**Best for:** Objects that rotate or scale dynamically

**Usage example:**
```python
from osrsbot.services.feature_match_service import FeatureMatchService

# Initialize once
feature_matcher = FeatureMatchService(n_features=500)

# Use for matching
screenshot = self.screen.capture()
template = cv.imread("template.png")
result = feature_matcher.find_template(screenshot, template)

if result:
    center_x, center_y, confidence = result
    # Click at center_x, center_y
```

**Advantages:**
- ✅ Works with rotation
- ✅ Works with scale changes
- ✅ Robust to partial occlusion
- ✅ Handles lighting changes better

**Disadvantages:**
- ❌ Much slower (10-50ms)
- ❌ Requires distinctive features
- ❌ More complex to implement
- ❌ May fail on simple/uniform objects

**When to use:**
- NPCs at different angles (though color detection is better)
- Items that rotate (rare in OSRS)
- Objects with distinctive patterns
- When template matching fails due to rotation/scale

## 5. Deep Learning (Not Implemented)

**Best for:** Complex object recognition

**Advantages:**
- ✅ Extremely robust
- ✅ Handles any transformation
- ✅ Can recognize objects by type, not just appearance

**Disadvantages:**
- ❌ Very slow (50-200ms+)
- ❌ Requires training data
- ❌ Overkill for OSRS
- ❌ Large model files

**When to use:**
- Complex recognition tasks
- When other methods fail
- **Not recommended for OSRS** - simpler methods work better

## Recommendations by Use Case

### Inventory Items (Potions, Food, Equipment)
✅ **Use: Standard Template Matching**
- Fast and precise
- Items don't rotate
- Users typically have fixed zoom

```python
self.actions.click_template("images/bot/items/overload.png", "overload")
```

**If supporting multiple zoom levels:**
```python
self.actions.click_template([
    "custom:overload_zoom1.png",
    "custom:overload_zoom2.png",
    "custom:overload_zoom3.png"
], "overload")
```

### NPCs (Dragons, Zulrah, Monsters)
✅ **Use: Color Detection**
- Extremely fast
- Handles any angle/rotation
- RuneLite provides highlighting

```python
# Use RuneLite's NPC highlighting
self.actions.attack_npc("green_dragon")
self.actions.click_color_smart("zulrah_serpentine")
```

**Don't use template matching for NPCs** - they move and rotate!

### UI Buttons (Prayer, Inventory, Settings)
✅ **Use: Standard Template Matching**
- UI never rotates
- Always same size
- Very reliable

```python
self.actions.click_ui_button_detected("prayer_tab")
```

### Bank Items
✅ **Use: Standard Template Matching**
- Fixed positions in grid
- No rotation
- Consistent appearance

```python
self.actions.click_template("images/bot/items/twisted_bow.png", "twisted bow")
```

### World Objects (Rocks, Trees, Altars)
✅ **Use: Color Detection**
- May appear at different angles
- Camera can rotate
- Color-based is faster

```python
self.actions.click_color("iron_rock")
```

### Ground Items (Loot)
✅ **Use: Color Detection (RuneLite Highlighting)**
- Already implemented in your codebase
- Handles any position/rotation

```python
self.actions.pickup_loot()  # Uses purple highlight detection
```

## Performance Comparison

Based on typical OSRS bot use cases:

```
Color Detection:        <1ms   ⚡⚡⚡⚡⚡ (Fastest)
Template Matching:      1-5ms  ⚡⚡⚡⚡
Multi-Template (3x):    5-15ms ⚡⚡⚡
Feature Matching (ORB): 10-50ms ⚡⚡
Deep Learning:          50-200ms+ ⚡
```

## Conclusion

For OSRS bots, stick with:
1. **Color Detection** for dynamic content (NPCs, world objects)
2. **Template Matching** for static content (inventory, UI, bank)
3. **Multi-Template** if you need zoom level support

**Feature Matching (ORB)** is available if needed, but rarely necessary for OSRS. Your current system is already optimal!

## Example: Hybrid Approach

```python
class MyBot(StateMachineBot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Template matching for inventory items
        self.POTION_TEMPLATE = "images/bot/items/super_combat.png"

        # Color detection for NPCs
        self.NPC_COLOR = "green_dragon"

    def attack_and_potion(self):
        # Use color detection for dynamic NPC
        if self.actions.attack_npc(self.NPC_COLOR):
            logger.info("Attacked NPC")

        # Use template matching for static inventory item
        if self.actions.click_template(self.POTION_TEMPLATE, "potion"):
            logger.info("Drank potion")
```

This hybrid approach gives you the best of both worlds!
