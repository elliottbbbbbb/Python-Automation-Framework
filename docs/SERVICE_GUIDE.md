# Service Layer Guide - OSRS Bot Framework

**Complete guide to all services in the framework**

This document provides in-depth documentation for every service in the OSRS Bot framework, including usage examples, configuration options, best practices, and troubleshooting.

---

## Table of Contents

1. [Service Overview](#service-overview)
2. [Core Services](#core-services)
   - [GameInterface](#gameinterface)
   - [MouseService](#mouseservice)
   - [ScreenService](#screenservice)
3. [Perception Services](#perception-services)
   - [OCRService](#ocrservice)
   - [TemplateMatchService](#templatematchservice)
4. [Navigation Services](#navigation-services)
   - [StatusSocketService](#statussocketservice)
   - [WalkerService](#walkerservice)
   - [MinimapPathfindingService](#minimappathfindingservice)
5. [Utility Services](#utility-services)
   - [AntiBanService](#antibanservice)
   - [ClickTargetTracker](#clicktargettracker)
   - [LootDetectionService](#lootdetectionservice)
6. [Hardware Integration](#hardware-integration)
   - [ArduinoMouseService](#arduinomouseservice)
7. [Service Dependencies](#service-dependencies)
8. [Configuration Reference](#configuration-reference)
9. [Best Practices](#best-practices)

---

## Service Overview

The framework uses **10 specialized services** organized by responsibility:

| Service | Purpose | Layer | Dependencies |
|---------|---------|-------|--------------|
| GameInterface | Window management | Infrastructure | None |
| MouseService | Software mouse control | Input | GameInterface |
| ScreenService | Screen capture | Perception | GameInterface |
| OCRService | Text recognition | Perception | Config |
| TemplateMatchService | UI detection | Perception | ScreenService |
| StatusSocketService | Real-time position | Data | None (external file) |
| WalkerService | Advanced pathfinding | Navigation | StatusSocket, Mouse, Screen |
| MinimapPathfindingService | Minimap navigation | Navigation | Screen, Mouse |
| AntiBanService | Anti-detection | Utility | Mouse, Screen |
| ClickTargetTracker | Target tracking | Utility | None |
| LootDetectionService | Loot detection | Perception | Screen |
| ArduinoMouseService | Hardware mouse | Input | Serial (optional) |

---

## Core Services

### GameInterface

**File**: [src/osrsbot/core/game_interface.py](../src/osrsbot/core/game_interface.py)

**Purpose**: Foundation service for window management and coordinate translation.

#### Key Features
- Finds RuneLite window by title
- Provides window bounds (position and dimensions)
- Converts between relative and absolute coordinates
- Single source of truth for window state

#### Initialization

```python
from osrsbot.models.config import Config
from osrsbot.core.game_interface import GameInterface

config = Config.load("config.json")
interface = GameInterface(config)
```

#### API Reference

```python
def get_bounds(self) -> Tuple[int, int, int, int]:
    """
    Get window bounds.

    Returns:
        (x, y, width, height) - Window position and dimensions
    """

def to_absolute_coordinates(self, x: int, y: int) -> Tuple[int, int]:
    """
    Convert relative window coordinates to absolute screen coordinates.

    Args:
        x: X coordinate relative to window
        y: Y coordinate relative to window

    Returns:
        (abs_x, abs_y) - Absolute screen coordinates
    """

def to_relative_coordinates(self, x: int, y: int) -> Tuple[int, int]:
    """
    Convert absolute screen coordinates to relative window coordinates.

    Args:
        x: Absolute screen X coordinate
        y: Absolute screen Y coordinate

    Returns:
        (rel_x, rel_y) - Window-relative coordinates
    """
```

#### Configuration

```json
{
  "window_title": "RuneLite - 61grouphunt",
  "account_name": "61grouphunt"
}
```

#### Best Practices

1. **Create once, inject everywhere**: GameInterface should be instantiated once in ScriptRunner
2. **Always use coordinate methods**: Never hardcode absolute coordinates
3. **Check window active**: Verify window exists before starting automation

#### Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Window not found | Incorrect window title | Update `window_title` in config.json |
| Coordinates offset | Window moved | Restart bot to refresh window bounds |
| Window detection slow | Multiple RuneLite windows | Use unique account name in title |

---

### MouseService

**File**: [src/osrsbot/services/mouse_service.py](../src/osrsbot/services/mouse_service.py)

**Purpose**: Humanized software mouse control with anti-detection features.

#### Key Features
- **Movement Styles**: Linear, Bezier curve, instant, random
- **Overshoot Simulation**: 15% chance of overshooting target
- **Click Variance**: ±3 pixels randomization
- **Speed Variance**: Configurable min/max speed
- **Post-click Delays**: Random delays after clicks

#### Initialization

```python
from osrsbot.services.mouse_service import MouseService, MouseConfig

mouse_config = MouseConfig(
    min_speed=0.2,
    max_speed=0.6,
    overshoot_chance=0.15,
    overshoot_distance=20,
    click_variance=3,
    post_click_delay=(0.05, 0.15)
)

mouse = MouseService(interface, config)
```

#### API Reference

```python
def move_to(
    self,
    x: int,
    y: int,
    style: MovementStyle = "curved",
    duration: Optional[float] = None,
    speed_multiplier: float = 1.0
) -> bool:
    """
    Move mouse to position.

    Args:
        x: Target X coordinate (relative to window)
        y: Target Y coordinate (relative to window)
        style: "linear", "curved", "instant", or "random"
        duration: Override automatic duration calculation
        speed_multiplier: Speed variance (1.0 = normal)

    Returns:
        True if successful
    """

def click_at(
    self,
    x: int,
    y: int,
    button: Literal["left", "right", "middle"] = "left",
    move_style: MovementStyle = "curved",
    variance: bool = True,
    speed_multiplier: float = 1.0
) -> bool:
    """
    Move to position and click.

    Args:
        x: Target X coordinate
        y: Target Y coordinate
        button: Mouse button to click
        move_style: Movement style for approach
        variance: Add ±3px randomization
        speed_multiplier: Speed variance

    Returns:
        True if successful
    """
```

#### Movement Styles

| Style | Behavior | Use Case |
|-------|----------|----------|
| **curved** | Bezier curve with possible overshoot | Default, most human-like |
| **linear** | Straight line movement | Fast, low-risk actions |
| **instant** | Teleport cursor (no movement) | Testing only |
| **random** | Randomly choose linear or curved | Maximum variance |

#### Configuration

```json
{
  "mouse": {
    "min_speed": 0.2,
    "max_speed": 0.6,
    "overshoot_chance": 0.15,
    "overshoot_distance": 20,
    "click_variance": 3,
    "post_click_delay_min": 0.05,
    "post_click_delay_max": 0.15
  }
}
```

#### Best Practices

1. **Use curved movement for important actions**: More human-like
2. **Enable variance for clicks**: Prevents pixel-perfect patterns
3. **Adjust speed_multiplier for different scenarios**: Slower for precision, faster for repetitive actions
4. **Don't disable post-click delays**: Essential for anti-detection

#### Performance Tips

- Linear movement is ~50% faster than curved
- Instant movement should only be used for testing
- Lower overshoot_chance for critical clicks (banking, combat)

---

### ScreenService

**File**: [src/osrsbot/services/screen_service.py](../src/osrsbot/services/screen_service.py)

**Purpose**: Screen capture and pixel-level color detection.

#### Key Features
- Full window or region capture
- Color matching with tolerance
- Multi-match support (find all occurrences)
- Distance-based sorting (closest match first)
- NumPy optimization for performance

#### Initialization

```python
from osrsbot.services.screen_service import ScreenService

screen = ScreenService(interface, config)
```

#### API Reference

```python
def find_color(
    self,
    hex_color: str,
    tolerance: int = 10,
    region: Optional[Tuple[int, int, int, int]] = None,
    find_all: bool = False,
    reference_point: Optional[Tuple[int, int]] = None
) -> Optional[Union[ColorMatch, List[ColorMatch]]]:
    """
    Find color on screen.

    Args:
        hex_color: Color in hex format (e.g., "#ff0000")
        tolerance: Acceptable color difference (0-255)
        region: (x, y, width, height) to search, or None for full window
        find_all: Return all matches instead of closest
        reference_point: Sort matches by distance from this point

    Returns:
        ColorMatch or List[ColorMatch] if found, None otherwise
    """

def get_pixel_color(self, x: int, y: int) -> Tuple[int, int, int]:
    """
    Get RGB color at specific pixel.

    Args:
        x: X coordinate (relative to window)
        y: Y coordinate (relative to window)

    Returns:
        (r, g, b) - RGB color tuple
    """

def capture_region(
    self,
    region: Tuple[int, int, int, int]
) -> Image.Image:
    """
    Capture specific screen region.

    Args:
        region: (x, y, width, height) to capture

    Returns:
        PIL Image of region
    """
```

#### Usage Examples

```python
# Find single closest match
match = screen.find_color("#00ffff", tolerance=5)
if match:
    print(f"Found at ({match.x}, {match.y})")

# Find all matches
matches = screen.find_color("#00ffff", tolerance=5, find_all=True)
print(f"Found {len(matches)} occurrences")

# Search specific region (inventory area)
inventory_region = (570, 240, 180, 260)
match = screen.find_color("#ff0000", region=inventory_region)

# Get pixel color for verification
color = screen.get_pixel_color(100, 100)
print(f"RGB: {color}")
```

#### Configuration

```json
{
  "colors": {
    "yellow_tile_marker": "#fcfc01",
    "blue_outline": "#0002cd",
    "green_dragon": "#00ffff",
    "banker": "#00FFFF"
  },
  "tolerances": {
    "color_match": 5
  }
}
```

#### Best Practices

1. **Use regions for performance**: Limit search area when possible
2. **Tune tolerance carefully**: Too low = false negatives, too high = false positives
3. **Sort by distance**: Use reference_point for consistent target selection
4. **Cache screenshots**: Reuse screenshot for multiple color searches

#### Performance

- Full window scan: ~10-20ms
- Region scan (inventory): ~2-5ms
- Pixel color check: <1ms

---

## Perception Services

### OCRService

**File**: [src/osrsbot/services/ocr_service.py](../src/osrsbot/services/ocr_service.py)

**Purpose**: Optical character recognition for reading game UI stats.

#### Key Features
- 5 preprocessing strategies for maximum accuracy
- Digit-only recognition (HP, prayer, etc.)
- Result consensus voting
- Shape detection for confusing digits (9 vs 4)
- Result smoothing and caching

#### Initialization

```python
from osrsbot.services.ocr_service import OCRService

ocr = OCRService(config)
```

#### API Reference

```python
def read_digits(
    self,
    screenshot: Image.Image,
    region: Optional[Tuple[int, int, int, int]] = None
) -> Optional[int]:
    """
    Read digits from screenshot using multiple strategies.

    Args:
        screenshot: PIL Image to read from
        region: (x, y, width, height) sub-region, or None for full image

    Returns:
        Integer value if recognized, None otherwise

    Strategies Applied:
        1. Low contrast (2x resize, 1.5 contrast)
        2. Medium contrast (3x resize, 2.0 contrast)
        3. High contrast (4x resize, 2.5 contrast)
        4. Very high contrast (4x resize, 3.0 contrast)
        5. Adaptive threshold
    """
```

#### Usage Examples

```python
# Read HP from screenshot
hp_region = config.get("coordinates", "hp_box")
screenshot = screen.capture_region(hp_region)
hp = ocr.read_digits(screenshot)
print(f"Current HP: {hp}")

# Read from full screenshot with region
screenshot = screen.capture_full()
hp = ocr.read_digits(screenshot, region=hp_region)
```

#### Configuration

```json
{
  "tesseract_path": "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
  "ocr": {
    "hp_ttl": 0.1,
    "window_size": 5
  },
  "coordinates": {
    "hp_box": {
      "x": 527,
      "y": 79,
      "width": 35,
      "height": 20
    }
  }
}
```

#### Preprocessing Strategies

| Strategy | Resize | Contrast | Threshold | Best For |
|----------|--------|----------|-----------|----------|
| Low | 2x | 1.5 | 127 | Normal conditions |
| Medium | 3x | 2.0 | 127 | Slightly faded text |
| High | 4x | 2.5 | 127 | Very faded text |
| Very High | 4x | 3.0 | 127 | Extreme conditions |
| Adaptive | 3x | 2.0 | Adaptive | Variable lighting |

#### Best Practices

1. **Calibrate regions carefully**: Exact region = better accuracy
2. **Use TTL caching**: Avoid re-reading identical values
3. **Verify with shape detection**: For 9 vs 4 disambiguation
4. **Test all strategies**: Different scenarios may need different approaches

#### Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Always returns None | Tesseract path incorrect | Update `tesseract_path` in config |
| Wrong digits | Region too large | Shrink region to exact text area |
| 9 read as 4 | Shape confusion | Enable shape detection |
| Slow performance | Too many OCR calls | Increase `hp_ttl` for caching |

---

### TemplateMatchService

**File**: [src/osrsbot/services/template_match_service.py](../src/osrsbot/services/template_match_service.py)

**Purpose**: UI element detection via OpenCV template matching.

#### Key Features
- Single template matching (buttons, icons)
- Grid-based detection (inventory, prayer)
- Configurable confidence thresholds
- Sticky caching (5s TTL)
- Supports multiple template variants

#### Initialization

```python
from osrsbot.services.template_match_service import TemplateMatchService

template_service = TemplateMatchService(screen, config)
```

#### API Reference

```python
def find_template(
    self,
    template_name: str
) -> Optional[Tuple[int, int]]:
    """
    Find single template match.

    Args:
        template_name: Key from templates.ui_buttons config

    Returns:
        (x, y) center of match, or None
    """

def find_in_grid(
    self,
    grid_name: str,
    row: int,
    col: int
) -> Optional[Tuple[int, int]]:
    """
    Find element in UI grid (inventory, prayers).

    Args:
        grid_name: Key from templates.ui_grids config
        row: Grid row (0-indexed)
        col: Grid column (0-indexed)

    Returns:
        (x, y) center of cell, or None
    """
```

#### Configuration

```json
{
  "templates": {
    "ui_grids": {
      "inventory": {
        "path": "templates/inventory.png",
        "rows": 7,
        "cols": 4,
        "threshold": 0.65,
        "sticky": true,
        "padding": 5,
        "border_offset": 3
      }
    },
    "ui_buttons": {
      "logout": {
        "path": "templates/logout.png",
        "threshold": 0.68
      },
      "combat_indicator": {
        "path": "templates/in_combat.png",
        "threshold": 0.654,
        "sticky": false,
        "ttl_seconds": 0.5
      }
    }
  }
}
```

#### Usage Examples

```python
# Find inventory grid
inv_slot = template_service.find_in_grid("inventory", row=0, col=0)
if inv_slot:
    mouse.click_at(*inv_slot)

# Find logout button
logout_button = template_service.find_template("logout")
if logout_button:
    mouse.click_at(*logout_button)

# Check combat status
in_combat = template_service.find_template("combat_indicator") is not None
```

#### Best Practices

1. **Use high-quality templates**: Clean, well-cropped images
2. **Test thresholds**: Balance between false positives and false negatives
3. **Enable sticky caching**: For UI elements that don't move
4. **Use multiple variants**: For icons with different states

---

## Navigation Services

### StatusSocketService

**File**: [src/osrsbot/services/status_socket_service.py](../src/osrsbot/services/status_socket_service.py)

**Purpose**: Real-time player position and camera data from RuneLite Status Socket plugin.

**⚠️ Requires**: RuneLite Status Socket plugin (see [SETUP_GUIDE.md](../SETUP_GUIDE.md))

#### Key Features
- Reads live_data.json from RuneLite plugin
- File modification time caching
- Graceful degradation if plugin unavailable
- Stuck detection (player not moving)
- World coordinate and camera yaw tracking

#### Initialization

```python
from osrsbot.services.status_socket_service import StatusSocketService

status_socket = StatusSocketService(
    data_file="live_data.json",
    poll_interval=0.1  # 100ms polling
)
```

#### API Reference

```python
def get_player_state(self) -> Optional[PlayerState]:
    """
    Get current player state.

    Returns:
        PlayerState with world_x, world_y, plane, camera_yaw, etc.
        Returns None if data unavailable or stale
    """

def is_available(self) -> bool:
    """Check if Status Socket plugin is active and data is fresh."""

def wait_for_arrival(
    self,
    target_x: int,
    target_y: int,
    tolerance: int = 2,
    timeout: float = 10.0
) -> bool:
    """
    Poll until player reaches target coordinates.

    Args:
        target_x: Target world X coordinate
        target_y: Target world Y coordinate
        tolerance: Arrival distance threshold
        timeout: Max wait time in seconds

    Returns:
        True if arrived, False if timeout or stuck
    """
```

#### PlayerState Dataclass

```python
@dataclass
class PlayerState:
    world_x: int          # World X coordinate
    world_y: int          # World Y coordinate
    plane: int            # Game plane (0-3)
    camera_yaw: int       # Camera rotation (0-2048, 0=north, 512=east, 1024=south, 1536=west)
    timestamp: float      # Last update time
    is_moving: bool       # Movement detection
    animation_id: int     # Current animation ID (-1 = idle)
```

#### Configuration

```json
{
  "status_socket": {
    "enabled": true,
    "data_file": "live_data.json",
    "poll_interval": 0.1
  }
}
```

#### Usage Examples

```python
# Get current position
state = status_socket.get_player_state()
if state:
    print(f"Position: ({state.world_x}, {state.world_y})")
    print(f"Camera: {state.camera_yaw}")
    print(f"Moving: {state.is_moving}")

# Wait for player to reach location
arrived = status_socket.wait_for_arrival(3185, 3448, tolerance=2, timeout=10.0)
if arrived:
    print("Reached destination!")
```

#### Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| is_available() returns False | Plugin not installed | Install Status Socket plugin |
| Data always None | File path incorrect | Verify data_file in config matches plugin output |
| Stuck detection triggering | Plugin crashed | Restart RuneLite |
| Data stale | Plugin disabled | Enable plugin in RuneLite |

---

### WalkerService

**File**: [src/osrsbot/services/walker_service.py](../src/osrsbot/services/walker_service.py)

**Purpose**: Advanced pathfinding with camera rotation compensation.

**⚠️ Requires**: StatusSocketService (RuneLite plugin)

#### Key Features
- **2D Rotation Matrix**: Compensates for camera angle automatically
- **World tiles → Minimap pixels**: Precise coordinate conversion
- **Waypoint following**: Multi-step path navigation
- **Arrival detection**: Configurable tolerance
- **Distance limiting**: Only clicks within minimap range

#### Initialization

```python
from osrsbot.services.walker_service import WalkerService, WalkerConfig

walker_config = WalkerConfig(
    minimap_center_x=654,
    minimap_center_y=111,
    tile_size=4,
    arrival_tolerance=2,
    max_click_distance=15
)

walker = WalkerService(
    config=walker_config,
    status_socket=status_socket,
    mouse=mouse,
    screen=screen,
    interface=interface
)
```

#### API Reference

```python
def walk_to(
    self,
    target_x: int,
    target_y: int,
    path: Optional[List[Tuple[int, int]]] = None,
    move_style: MovementStyle = "curved"
) -> bool:
    """
    Walk to world coordinates.

    Args:
        target_x: Target world X coordinate
        target_y: Target world Y coordinate
        path: Optional intermediate waypoints
        move_style: Mouse movement style ("curved", "linear")

    Returns:
        True if arrived, False on timeout or error
    """

def walk_path(
    self,
    waypoints: List[Tuple[int, int]],
    move_style: MovementStyle = "curved"
) -> bool:
    """
    Follow predefined path of world coordinates.

    Args:
        waypoints: List of (x, y) world coordinates
        move_style: Mouse movement style

    Returns:
        True if all waypoints reached
    """

def world_to_minimap(
    self,
    world_x: int,
    world_y: int,
    player_x: int,
    player_y: int,
    camera_yaw: int
) -> Optional[Tuple[int, int]]:
    """
    Convert world tiles to minimap pixels using rotation matrix.

    Args:
        world_x: Target world X
        world_y: Target world Y
        player_x: Current player X
        player_y: Current player Y
        camera_yaw: Camera angle (0-2048)

    Returns:
        (minimap_x, minimap_y) or None if out of range
    """
```

#### Rotation Matrix Mathematics

```python
# Step 1: Calculate delta
dx = world_x - player_x
dy = world_y - player_y

# Step 2: Convert yaw (0-2048) to degrees
degrees = 360 - (camera_yaw * (360 / 2048))
theta = radians(degrees)

# Step 3: Apply 2D rotation matrix
rotated_x = dx * cos(theta) - dy * sin(theta)
rotated_y = dx * sin(theta) + dy * cos(theta)

# Step 4: Scale to pixels (4 pixels per tile)
pixel_x = rotated_x * 4
pixel_y = rotated_y * 4

# Step 5: Translate to minimap center
minimap_x = center_x + pixel_x
minimap_y = center_y + pixel_y
```

#### Configuration

```json
{
  "walker": {
    "minimap_center_x": 654,
    "minimap_center_y": 111,
    "tile_size": 4,
    "arrival_tolerance": 2,
    "max_click_distance": 15,
    "enable_anti_ban_variance": true
  }
}
```

#### Usage Examples

```python
# Walk to single coordinate (Varrock West Bank)
success = walker.walk_to(3185, 3448)
if success:
    print("Arrived at bank!")

# Follow predefined path (GE to bank)
path = [
    (3165, 3486),  # Start at GE
    (3167, 3472),  # Walk west
    (3185, 3436),  # Walk south
    (3185, 3448)   # Arrive at bank
]
success = walker.walk_path(path)

# Convert coordinates manually
state = status_socket.get_player_state()
minimap_pos = walker.world_to_minimap(
    3185, 3448,
    state.world_x, state.world_y,
    state.camera_yaw
)
if minimap_pos:
    mouse.click_at(*minimap_pos)
```

#### Best Practices

1. **Use waypoints for long distances**: Break up paths >15 tiles
2. **Test with different camera angles**: Verify rotation matrix works
3. **Handle arrival failures**: Implement retry logic
4. **Adjust tolerance for precision**: Lower tolerance for exact positions

#### Performance

- Rotation matrix calculation: <1ms
- Walk to single target: 5-10s (depending on distance)
- Path with 4 waypoints: 20-40s

---

## Utility Services

### AntiBanService

**File**: [src/osrsbot/services/anti_ban_service.py](../src/osrsbot/services/anti_ban_service.py)

**Purpose**: Behavioral randomization and anti-detection.

#### Key Features
- Scheduled breaks (30-60 min intervals)
- Micro-breaks (5% random chance)
- Session variance (±15% timing)
- Idle actions (mouse jitter, stats check)
- Action pattern tracking

#### API Reference

```python
def should_take_break(self) -> bool:
    """Check if scheduled break is needed."""

def take_scheduled_break(self) -> None:
    """Execute break with random duration."""

def perform_idle_action(self) -> None:
    """Execute random idle action (jitter, stats check)."""

def get_timing_variance(self, base_timing: float) -> float:
    """Apply session variance to timing."""
```

#### Configuration

```json
{
  "anti_ban": {
    "break_interval_min": 1800,
    "break_interval_max": 3600,
    "break_duration_min": 120,
    "break_duration_max": 300,
    "micro_break_chance": 0.05,
    "timing_variance": 0.15
  }
}
```

---

### ArduinoMouseService

**File**: [src/osrsbot/services/arduino_mouse_service.py](../src/osrsbot/services/arduino_mouse_service.py)

**Purpose**: Hardware mouse control via Arduino serial connection.

**⚠️ Optional**: Requires Arduino hardware, pyserial, custom firmware

#### Key Features
- Drop-in replacement for MouseService (identical interface)
- Serial communication protocol
- Multi-pass position correction
- Automatic fallback to software mouse
- Windows high-resolution timer

#### Initialization

```python
from osrsbot.services.arduino_mouse_service import ArduinoMouseService
from osrsbot.services.mouse_service import MouseConfig

mouse_config = MouseConfig(...)
arduino_mouse = ArduinoMouseService(
    config=mouse_config,
    serial_port="COM3",
    baud_rate=115200,
    fallback_to_software=True
)
```

#### Serial Protocol

- Movement: `"x;y\n"` (e.g., `"1920;1080\n"`)
- Left click: `"l\n"`
- Right click: `"r\n"`
- Middle click: `"m\n"`

#### Configuration

```json
{
  "arduino": {
    "enabled": false,
    "serial_port": "COM3",
    "baud_rate": 115200,
    "fallback_to_software": true,
    "connection_timeout": 2.0
  }
}
```

---

## Service Dependencies

```
GameInterface (foundation)
    ├─> MouseService
    ├─> ScreenService
    │       ├─> TemplateMatchService
    │       ├─> LootDetectionService
    │       └─> WalkerService
    │
    └─> WalkerService
            └─> StatusSocketService

AntiBanService
    ├─> MouseService
    └─> ScreenService

OCRService (independent)

ArduinoMouseService (alternative to MouseService)
    └─> Fallback: MouseService
```

---

## Best Practices

### General Service Usage

1. **Inject dependencies**: Never create services inside other services
2. **Use interfaces consistently**: Follow established patterns
3. **Handle errors gracefully**: Check return values, catch exceptions
4. **Log appropriately**: Use logging module for debugging
5. **Test in isolation**: Mock dependencies for unit tests

### Performance Optimization

1. **Cache expensive operations**: Template matches, OCR results
2. **Limit search regions**: Screen searches should use regions
3. **Batch operations**: Multiple color searches on same screenshot
4. **Use appropriate services**: Choose right tool for the job

### Error Handling

```python
# Good: Check return values
match = screen.find_color("#ff0000")
if match:
    success = mouse.click_at(match.x, match.y)
    if not success:
        logger.error("Click failed")
        return False

# Bad: Assume success
match = screen.find_color("#ff0000")
mouse.click_at(match.x, match.y)  # Will crash if match is None
```

### Configuration Management

1. **Use config.get() with defaults**: Prevent missing key errors
2. **Validate config on startup**: Check required fields exist
3. **Document config options**: Add comments in config.json
4. **Use environment-specific configs**: Different config per account

---

## Troubleshooting

### Common Issues

| Issue | Affected Services | Solution |
|-------|------------------|----------|
| "Window not found" | GameInterface | Update window_title in config |
| "Tesseract not found" | OCRService | Install Tesseract, set path in config |
| "Template not found" | TemplateMatchService | Verify template file exists |
| "Arduino connection failed" | ArduinoMouseService | Check serial port, enable fallback |
| "Status Socket unavailable" | StatusSocketService | Install RuneLite plugin |
| "Color not found" | ScreenService | Adjust tolerance, verify hex color |

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Profiling

```python
import time

start = time.time()
match = screen.find_color("#ff0000")
elapsed = time.time() - start
print(f"Color search took {elapsed*1000:.2f}ms")
```

---

**Document Version**: 1.0
**Last Updated**: December 22, 2025
**Related Docs**: [ARCHITECTURE.md](ARCHITECTURE.md), [WALKER_TECHNICAL_DOCS.md](WALKER_TECHNICAL_DOCS.md), [SETUP_GUIDE.md](../SETUP_GUIDE.md)
