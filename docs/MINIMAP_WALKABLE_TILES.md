# Converting OSRS Minimap to Walkable Tiles

**Guide**: How to extract walkable tile information from the OSRS minimap

---

## Overview

The OSRS minimap shows a top-down view of the game world with visible tile grid lines. This guide explains how to convert that visual representation into a programmatic 2D array of walkable/non-walkable tiles.

### What You Can See in the Minimap

- **Green/light areas**: Walkable grass, paths
- **Dark green**: Trees, obstacles (non-walkable)
- **Gray**: Walls, rocks (non-walkable)
- **Tile grid**: Each square is one game tile
- **Colored dots**: Players (white), NPCs (yellow), items (yellow), aggressive NPCs (red)

---

## Approach

### 1. **Extract Minimap Region**
- Minimap is circular, ~146px diameter
- Located in top-right of game window
- Capture square region around center

### 2. **Apply Circular Mask**
- Minimap is circular, ignore corners
- Create circular mask with cv2.circle()

### 3. **Color-Based Segmentation**
- **Walkable colors**: Light green, brown/tan, lighter shades
- **Non-walkable colors**: Dark green, gray, blue (water)
- Use cv2.inRange() for color detection

### 4. **Remove Dots** (Players/NPCs/Items)
- Detect bright colors: white, yellow, red, cyan
- Remove from walkable mask
- These are temporary and shouldn't affect pathfinding

### 5. **Convert to Tile Grid**
- Each tile ≈ 4x4 pixels on minimap
- Divide minimap into grid
- Tile is walkable if >50% of pixels are walkable

### 6. **A* Pathfinding**
- Use tile grid for pathfinding
- Find shortest walkable path between points

---

## Implementation

### MinimapService API

```python
from osrsbot.services.minimap_service import MinimapService

# Initialize
minimap = MinimapService(screen_service)

# Extract walkable tiles
minimap_center = (1450, 100)  # Top-right corner
tile_grid = minimap.extract_walkable_tiles(minimap_center, debug=True)

# tile_grid is 2D boolean array:
# True = walkable, False = non-walkable
# Shape: approximately (36, 36) for 146px diameter / 4px per tile

# Check if tile is walkable
is_walkable = tile_grid[y, x]

# Find path
path = minimap.find_walkable_path(tile_grid, start=(10, 10), goal=(20, 20))
```

### Key Methods

#### `extract_walkable_tiles(minimap_center, debug=False)`
**Returns**: 2D numpy boolean array

```python
tile_grid = minimap.extract_walkable_tiles((1450, 100), debug=True)
# Returns: array([[True, True, False, ...],
#                 [True, False, False, ...],
#                 ...])
```

#### `find_walkable_path(tile_grid, start, goal)`
**Returns**: List of (x, y) positions or None

```python
path = minimap.find_walkable_path(
    tile_grid,
    start=(18, 18),  # Center
    goal=(30, 18)    # Edge
)
# Returns: [(18, 18), (19, 18), (20, 18), ..., (30, 18)]
```

---

## Usage Examples

### Example 1: Basic Extraction

```python
from osrsbot.services.minimap_service import MinimapService
from osrsbot.services.screen_service import ScreenService
from osrsbot.core.game_interface import GameInterface
from osrsbot.models.config import Config

# Setup
config = Config.load("config.json")
interface = GameInterface(config)
screen = ScreenService(interface, config)
minimap = MinimapService(screen)

# Extract tiles
tile_grid = minimap.extract_walkable_tiles(
    minimap_center=(1450, 100),
    debug=True  # Saves debug images
)

print(f"Grid shape: {tile_grid.shape}")
print(f"Walkable tiles: {tile_grid.sum()} / {tile_grid.size}")
```

### Example 2: Pathfinding

```python
# Extract current walkable tiles
tile_grid = minimap.extract_walkable_tiles((1450, 100))

# Find path from center to edge
center = (tile_grid.shape[1] // 2, tile_grid.shape[0] // 2)
goal = (tile_grid.shape[1] - 5, tile_grid.shape[0] // 2)

path = minimap.find_walkable_path(tile_grid, center, goal)

if path:
    print(f"Path found: {len(path)} steps")
    for i, (x, y) in enumerate(path):
        print(f"Step {i}: ({x}, {y})")
else:
    print("No path found - goal is blocked")
```

### Example 3: Real-Time Monitoring

```python
import time

while True:
    # Update tile grid every second
    tile_grid = minimap.extract_walkable_tiles((1450, 100))

    # Check specific tiles
    center_walkable = tile_grid[18, 18]

    if not center_walkable:
        print("Warning: Center tile blocked!")

    time.sleep(1)
```

---

## Color Calibration

Different OSRS clients (RuneLite, official, etc.) may have slightly different colors. Use the calibration tool:

```bash
python examples/minimap_color_calibration.py
```

### Steps:
1. **Capture minimap**: Move mouse to center, press Enter
2. **Analyze colors**: See dominant colors in your minimap
3. **Interactive picker**: Click on tiles to see their exact colors
4. **Update ranges**: Modify `WALKABLE_COLORS` and `NON_WALKABLE_COLORS` in `minimap_service.py`

### Example Color Calibration

After running calibration tool, you might find:

```python
# Your specific client colors (example)
WALKABLE_COLORS = {
    'grass': [(35, 75, 35), (85, 155, 85)],      # Slightly different
    'path': [(55, 55, 35), (105, 105, 75)],
}

NON_WALKABLE_COLORS = {
    'tree': [(18, 35, 18), (45, 75, 45)],
    'wall': [(25, 25, 25), (65, 65, 65)],
}
```

Update these in `src/osrsbot/services/minimap_service.py`

---

## Visualizing Results

### Debug Images

When `debug=True`, three images are saved to `debug/minimap/`:

1. **minimap_original.png**: Raw minimap capture
2. **minimap_walkable_mask.png**: White = walkable, Black = non-walkable
3. **minimap_tile_grid.png**: Overlay showing grid with green (walkable) and red (non-walkable) tiles

### ASCII Visualization

```python
def print_tile_grid(tile_grid):
    """Print grid as ASCII (. = walkable, # = blocked)"""
    for row in tile_grid:
        line = "".join("." if cell else "#" for cell in row)
        print(line)

tile_grid = minimap.extract_walkable_tiles((1450, 100))
print_tile_grid(tile_grid)
```

**Output**:
```
....................##..............
...................####.............
..................######............
.................########...........
................##########..........
...............############.........
..............##############........
.............################.......
............##################......
...........####################.....
```

---

## Advanced Usage

### Custom Tile Classification

```python
def is_tile_type(minimap_img, x, y, tile_type):
    """
    Check if tile at (x, y) is specific type

    Args:
        minimap_img: Minimap image
        x, y: Tile coordinates
        tile_type: 'grass', 'tree', 'water', etc.

    Returns:
        True if tile matches type
    """
    tile_size = 4

    # Extract tile pixels
    tile_pixels = minimap_img[
        y*tile_size:(y+1)*tile_size,
        x*tile_size:(x+1)*tile_size
    ]

    # Check color ranges for type
    if tile_type == 'grass':
        lower = np.array([40, 80, 40])
        upper = np.array([80, 150, 80])
        mask = cv2.inRange(tile_pixels, lower, upper)
        return np.sum(mask) > (tile_size * tile_size * 0.5 * 255)

    # ... other types
```

### Integration with Bot

```python
class SmartBot(Bot):
    """Bot that uses minimap for pathfinding"""

    def run_cycle(self, bank_location, run_number):
        # Get walkable tiles
        tile_grid = self.minimap.extract_walkable_tiles((1450, 100))

        # Current position (center of minimap)
        current_pos = (18, 18)

        # Goal (e.g., bank)
        bank_pos = self.get_bank_position(bank_location)

        # Find path
        path = self.minimap.find_walkable_path(tile_grid, current_pos, bank_pos)

        if path:
            # Walk along path
            for step in path:
                self.walk_to_tile(step)
                self.actions.wait("short")
        else:
            logger.error("No path to bank found")
```

---

## Technical Details

### Minimap Properties (OSRS)

| Property | Value |
|----------|-------|
| Diameter | ~146 pixels |
| Radius | ~73 pixels |
| Pixels per tile | ~4 pixels |
| Visible tiles | ~36x36 grid (circular) |
| Tile size (game) | 1x1 game square |
| Player position | Always at center |

### Color Ranges (BGR)

**Walkable**:
- Grass: (40, 80, 40) to (80, 150, 80)
- Paths: (60, 60, 40) to (100, 100, 70)
- Sand: (100, 150, 180) to (140, 190, 220)

**Non-Walkable**:
- Trees: (20, 40, 20) to (40, 70, 40)
- Walls: (30, 30, 30) to (60, 60, 60)
- Water: (80, 40, 20) to (120, 80, 40)

**Dots** (Remove):
- White (players): (200, 200, 200) to (255, 255, 255)
- Yellow (NPCs/items): (0, 200, 200) to (100, 255, 255)
- Red (aggressive): (0, 0, 200) to (100, 100, 255)

### Algorithm Complexity

- **Color detection**: O(width × height)
- **Tile grid creation**: O(grid_width × grid_height)
- **A* pathfinding**: O(nodes × log(nodes)) worst case

For 36×36 grid:
- Extraction: ~0.1-0.2 seconds
- Pathfinding: <0.01 seconds

---

## Troubleshooting

### Issue: All tiles detected as non-walkable

**Cause**: Wrong color ranges for your client

**Solution**:
1. Run `python examples/minimap_color_calibration.py`
2. Click on walkable areas
3. Note the BGR values
4. Update `WALKABLE_COLORS` in `minimap_service.py`

### Issue: Dots detected as walkable

**Cause**: Dot removal not working

**Solution**:
- Check that dots are being detected in `_remove_dots()`
- May need to adjust dot color ranges
- Increase dilation kernel size

### Issue: Path not found despite clear route

**Cause**: Tile grid has gaps due to color detection

**Solution**:
- Lower walkable threshold (currently 50%)
- Use morphological closing to fill gaps
- Adjust color ranges to be more inclusive

### Issue: Grid doesn't align with visual tiles

**Cause**: Wrong `TILE_SIZE` constant

**Solution**:
- Measure tile size manually from screenshot
- Adjust `TILE_SIZE` in `minimap_service.py`
- Typical values: 3-5 pixels

---

## Performance Optimization

### Caching

```python
class CachedMinimapService(MinimapService):
    """Minimap service with caching"""

    def __init__(self, screen_service, cache_ttl=1.0):
        super().__init__(screen_service)
        self._cache = None
        self._cache_time = 0
        self._cache_ttl = cache_ttl

    def extract_walkable_tiles(self, minimap_center, debug=False):
        import time

        now = time.time()

        if self._cache is None or (now - self._cache_time) > self._cache_ttl:
            self._cache = super().extract_walkable_tiles(minimap_center, debug)
            self._cache_time = now

        return self._cache.copy()
```

### Region of Interest

If you only need to check a small area:

```python
# Only check center 10x10 tiles
tile_grid = minimap.extract_walkable_tiles((1450, 100))
center_region = tile_grid[13:23, 13:23]  # 10x10 around center
```

---

## Integration Example

```python
# In your bot's run_cycle():
def run_cycle(self, bank_location, run_number):
    # 1. Get current walkable tiles
    tile_grid = self.minimap.extract_walkable_tiles(
        self.config.get("minimap_center")
    )

    # 2. Identify goal tile (e.g., bank location)
    goal_tile = self.get_bank_tile(bank_location)

    # 3. Find path
    center = (tile_grid.shape[1] // 2, tile_grid.shape[0] // 2)
    path = self.minimap.find_walkable_path(tile_grid, center, goal_tile)

    # 4. Execute path
    if path:
        for step_tile in path[1:]:  # Skip first (current position)
            # Convert tile to minimap pixel coordinate
            pixel_x, pixel_y = self.tile_to_pixel(step_tile)

            # Click on minimap
            self.actions.click_coordinate_absolute(pixel_x, pixel_y)
            self.actions.wait("short")

            # Wait for arrival
            time.sleep(0.5)
    else:
        logger.warning("No path found, walking manually")
        self.walk_manually(bank_location)
```

---

## Future Enhancements

- **Dynamic obstacle detection**: Detect players/NPCs blocking path
- **Multi-floor support**: Handle different floor levels
- **Terrain type classification**: Identify specific terrain (grass, sand, etc.)
- **Machine learning**: Train model to classify walkable vs non-walkable
- **Real-time updates**: Continuously update tile grid as player moves

---

## Summary

**Key Points**:
1. ✓ Minimap shows ~36×36 tile grid
2. ✓ Use color segmentation to identify walkable areas
3. ✓ Remove temporary dots (players, NPCs, items)
4. ✓ Convert pixel mask to tile grid
5. ✓ Use A* pathfinding on tile grid
6. ✓ Calibrate colors for your specific client

**Files**:
- `src/osrsbot/services/minimap_service.py` - Main implementation
- `examples/minimap_walkable_tiles_demo.py` - Usage example
- `examples/minimap_color_calibration.py` - Calibration tool

**Try it now**:
```bash
python examples/minimap_walkable_tiles_demo.py
```

---

**Happy pathfinding!** 🗺️
