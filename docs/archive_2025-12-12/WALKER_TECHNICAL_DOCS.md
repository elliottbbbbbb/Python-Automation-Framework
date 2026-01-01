# Walker & Arduino Mouse - Technical Documentation

Complete technical documentation for the advanced pathfinding and hardware mouse features.

---

## Table of Contents

1. [Overview](#overview)
2. [Status Socket Service](#status-socket-service)
3. [Walker Service](#walker-service)
4. [Arduino Mouse Service](#arduino-mouse-service)
5. [Configuration Reference](#configuration-reference)
6. [API Reference](#api-reference)
7. [Implementation Details](#implementation-details)
8. [Testing Guide](#testing-guide)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This implementation adds two major features to the OSRS bot framework:

### 1. Advanced Pathfinding/Walker System
- **Purpose**: Navigate to any world coordinate using minimap clicks
- **Key Technology**: 2D rotation matrix for camera angle compensation
- **Dependencies**: RuneLite/OpenOSRS Status Socket plugin
- **Status**: Production-ready, fully integrated

### 2. Arduino Mouse Control (Optional)
- **Purpose**: Hardware-based mouse input for enhanced anti-detection
- **Key Technology**: Serial communication protocol with Arduino
- **Dependencies**: Arduino hardware, pyserial library
- **Status**: Optional, disabled by default with automatic fallback

---

## Status Socket Service

### Purpose

The Status Socket service reads real-time game state from RuneLite/OpenOSRS, providing:
- Player world coordinates (X, Y, plane)
- Camera rotation (yaw/pitch)
- Animation state
- Movement status

This data is essential for the walker to function correctly.

### How It Works

#### File Monitoring System

```python
class StatusSocketService:
    def __init__(self, data_file: str, poll_interval: float):
        self.data_file = Path(data_file)  # Default: "live_data.json"
        self.poll_interval = poll_interval  # Default: 0.1 seconds
        self._last_modified: float = 0
        self._last_state: Optional[PlayerState] = None
```

**File Monitoring Strategy:**
1. Check file modification time (`st_mtime`)
2. Only parse JSON if file has changed
3. Cache last known good state
4. Return cached state if file unchanged

**Benefits:**
- Avoids redundant JSON parsing
- Reduces I/O overhead
- Maintains state during temporary file issues

#### Data Structure

```python
@dataclass
class PlayerState:
    world_x: int          # World X coordinate (e.g., 3200)
    world_y: int          # World Y coordinate (e.g., 3400)
    plane: int            # Z-level (0 = ground, 1+ = upper floors)
    camera_yaw: int       # Camera rotation (0-2048, 0 = north)
    timestamp: float      # When data was captured
    is_moving: bool       # Is player currently moving
    animation_id: int     # Current animation (-1 = idle)
```

#### JSON Format from Status Socket Plugin

```json
{
  "worldPoint": {
    "x": 3213,
    "y": 3425,
    "plane": 0
  },
  "camera": {
    "yaw": 512,
    "pitch": 256,
    "x": 0,
    "y": 0,
    "z": 0
  },
  "animation": -1,
  "isMoving": false
}
```

#### Error Handling

**File Not Found:**
```python
if not self.data_file.exists():
    if not self._file_unavailable_warned:
        logger.warning("Status Socket data file not found")
        self._file_unavailable_warned = True
    return None
```
- Warns once to avoid log spam
- Returns `None` gracefully

**JSON Parse Errors:**
```python
except json.JSONDecodeError as e:
    logger.warning(f"Failed to parse JSON: {e}. Using last known state.")
    return self._last_state
```
- Falls back to cached state
- Handles corrupt/partial file writes

**Stale Data Detection:**
```python
def is_available(self) -> bool:
    state = self.get_player_state()
    if state is None:
        return False

    time_since_update = time.time() - state.timestamp
    if time_since_update > self._stale_data_threshold:  # Default: 5 seconds
        logger.warning(f"Data is stale ({time_since_update:.1f}s)")
        return False

    return True
```

#### Arrival Detection

```python
def wait_for_arrival(
    self, target_x: int, target_y: int,
    tolerance: int = 2,
    timeout: float = 10.0
) -> bool:
    """Poll until player reaches target or timeout."""

    start_time = time.time()
    stuck_threshold = 5
    stuck_counter = 0
    last_position = None

    while (time.time() - start_time) < timeout:
        state = self.get_player_state()

        # Calculate distance
        distance = sqrt((state.world_x - target_x)^2 + (state.world_y - target_y)^2)

        if distance <= tolerance:
            return True  # Arrived!

        # Stuck detection
        current_position = (state.world_x, state.world_y)
        if current_position == last_position:
            stuck_counter += 1
            if stuck_counter >= stuck_threshold:
                logger.warning("Player appears stuck")
                return False
        else:
            stuck_counter = 0

        last_position = current_position
        time.sleep(self.poll_interval)

    return False  # Timeout
```

**Stuck Detection:**
- Tracks position across poll intervals
- Increments counter if position unchanged
- After 5 checks without movement (0.5s), declares stuck
- Prevents infinite waiting on obstacles

---

## Walker Service

### Purpose

The Walker service converts world coordinates to minimap pixel coordinates and handles waypoint-based navigation.

### The Camera Rotation Problem

**Challenge:** OSRS minimap rotates with the camera. A target "north" of the player appears in different minimap positions depending on camera angle.

**Solution:** 2D rotation matrix transformation.

### Rotation Matrix Mathematics

#### Understanding the Coordinate System

```
OSRS World Coordinates:
- X increases EASTWARD
- Y increases NORTHWARD (yes, north is higher Y)
- Origin varies by region

RuneLite Camera Yaw:
- Range: 0 - 2048
- 0 = North (camera facing north)
- 512 = East
- 1024 = South
- 1536 = West
- Increases CLOCKWISE

Minimap Screen Coordinates:
- Origin at minimap center (default: 654, 111)
- X increases RIGHTWARD
- Y increases DOWNWARD (standard screen coords)
```

#### The Transformation Algorithm

**Step 1: Calculate Tile Delta**
```python
dx = target_x - player_x  # Tiles east/west of player
dy = target_y - player_y  # Tiles north/south of player
```

**Step 2: Convert Yaw to Radians**
```python
# RuneLite yaw 0-2048 → degrees 0-360
degrees = 360 - (camera_yaw * (360.0 / 2048.0))

# Convert to radians for math functions
theta = math.radians(degrees)
```

**Why subtract from 360?**
- RuneLite yaw increases clockwise
- Math functions expect counter-clockwise
- Inversion corrects the coordinate system

**Step 3: Apply 2D Rotation Matrix**

Standard 2D rotation matrix:
```
| cos(θ)  -sin(θ) |   | dx |
| sin(θ)   cos(θ) | × | dy |
```

In code:
```python
rotated_x = dx * math.cos(theta) - dy * math.sin(theta)
rotated_y = dx * math.sin(theta) + dy * math.cos(theta)
```

**Step 4: Scale to Pixels**
```python
# OSRS minimap: 4 pixels per tile
pixel_x = rotated_x * tile_size  # tile_size = 4
pixel_y = rotated_y * tile_size
```

**Step 5: Offset to Minimap Center**
```python
minimap_x = minimap_center_x + int(pixel_x)  # Default center: 654
minimap_y = minimap_center_y + int(pixel_y)  # Default center: 111
```

#### Worked Example

**Scenario:**
- Player at: (3200, 3200)
- Target at: (3200, 3210) - 10 tiles north
- Camera yaw: 512 (facing east)

**Calculation:**
```python
# Step 1: Delta
dx = 3200 - 3200 = 0
dy = 3210 - 3200 = 10

# Step 2: Convert yaw
degrees = 360 - (512 * (360/2048)) = 360 - 90 = 270°
theta = radians(270) = 4.712 radians

# Step 3: Rotate
rotated_x = 0 * cos(270°) - 10 * sin(270°) = 0 - 10*(-1) = 10
rotated_y = 0 * sin(270°) + 10 * cos(270°) = 0 + 10*0 = 0

# Step 4: Scale
pixel_x = 10 * 4 = 40
pixel_y = 0 * 4 = 0

# Step 5: Offset
minimap_x = 654 + 40 = 694
minimap_y = 111 + 0 = 111
```

**Result:** Target appears 40 pixels to the RIGHT of minimap center (east on screen when camera faces east).

**Validation:**
- Target is north of player in world
- Camera faces east
- North appears to the right when facing east ✓
- Rotation matrix correctly compensates!

### Boundary Detection

```python
def world_to_minimap(...) -> Optional[Tuple[int, int]]:
    # ... rotation calculation ...

    # Minimap is circular
    minimap_radius = 73  # pixels
    distance_from_center = sqrt(pixel_x^2 + pixel_y^2)

    if distance_from_center > minimap_radius:
        logger.debug("Target outside minimap bounds")
        return None  # Out of range

    return (minimap_x, minimap_y)
```

**Why circular?**
- OSRS minimap is a circle, not a square
- Prevents clicking outside visible area
- Radius: 73 pixels ≈ 18 tiles view distance

### Waypoint Following Algorithm

#### High-Level Flow

```
For each waypoint in path:
    While not at waypoint:
        1. Get current player position
        2. Calculate distance to waypoint
        3. If arrived (within tolerance): break
        4. If too far (>max_distance): click intermediate point
        5. Else: click waypoint directly
        6. Wait for player to move
        7. Poll until arrived or timeout
```

#### Distance-Based Chunking

```python
if distance > self.config.max_click_distance:  # Default: 15 tiles
    # Target far away - click intermediate point
    click_target = self._get_intermediate_point(
        player_x, player_y,
        waypoint_x, waypoint_y,
        max_distance
    )
else:
    # Target within range - click directly
    click_target = (waypoint_x, waypoint_y)
```

**Why chunk?**
- Minimap has limited view distance (~18 tiles)
- Long paths may go outside minimap
- Breaking into chunks ensures targets stay visible

#### Intermediate Point Calculation

```python
def _get_intermediate_point(
    start_x: int, start_y: int,
    end_x: int, end_y: int,
    max_distance: int
) -> Tuple[int, int]:
    """
    Get point max_distance tiles from start toward end.
    """
    dx = end_x - start_x
    dy = end_y - start_y
    distance = sqrt(dx^2 + dy^2)

    if distance == 0:
        return (start_x, start_y)

    # Normalize vector and scale to max_distance
    ratio = max_distance / distance
    intermediate_x = start_x + int(dx * ratio)
    intermediate_y = start_y + int(dy * ratio)

    return (intermediate_x, intermediate_y)
```

**Example:**
- Start: (3200, 3200)
- End: (3250, 3250) - 70 tiles away diagonally
- Max distance: 15 tiles

```
dx = 50, dy = 50
distance = sqrt(50^2 + 50^2) = 70.7
ratio = 15 / 70.7 = 0.212
intermediate_x = 3200 + 50*0.212 = 3211
intermediate_y = 3200 + 50*0.212 = 3211
```

Result: (3211, 3211) - exactly 15 tiles from start toward target.

### Complete Walk Cycle

```python
def walk_path(self, waypoints: List[Tuple[int, int]], move_style: MovementStyle) -> bool:
    for waypoint_x, waypoint_y in waypoints:
        max_attempts = 10

        for attempt in range(max_attempts):
            # 1. Get player state
            state = self.status_socket.get_player_state()
            if not state:
                return False

            # 2. Check if arrived
            distance = self._calculate_distance(
                state.world_x, state.world_y,
                waypoint_x, waypoint_y
            )
            if distance <= self.config.arrival_tolerance:
                break  # Waypoint reached

            # 3. Determine click target
            if distance > self.config.max_click_distance:
                click_target = self._get_intermediate_point(...)
            else:
                click_target = (waypoint_x, waypoint_y)

            # 4. Convert to minimap coords
            minimap_pos = self.world_to_minimap(
                click_target[0], click_target[1],
                state.world_x, state.world_y,
                state.camera_yaw
            )
            if not minimap_pos:
                logger.warning("Target out of minimap range")
                return False

            # 5. Convert to absolute screen coords
            abs_x, abs_y = self.screen.relative_to_absolute(*minimap_pos)

            # 6. Click minimap
            self.mouse.click_at(abs_x, abs_y, move_style=move_style)

            # 7. Wait for arrival
            if not self.status_socket.wait_for_arrival(
                waypoint_x, waypoint_y,
                tolerance=self.config.arrival_tolerance,
                timeout=10.0
            ):
                # Timeout - try again
                continue

            # Success
            return True

        # Failed after max_attempts
        return False

    return True  # All waypoints completed
```

### Anti-Ban Integration

```python
# In GameActions.walk_path():
if self.anti_ban:
    speed_multiplier = self.anti_ban.get_mouse_speed_variance()
else:
    speed_multiplier = 1.0

self.mouse.click_at(x, y, move_style=move_style, speed_multiplier=speed_multiplier)
```

**Anti-Ban Features:**
- Session-level speed variance (0.9-1.1x)
- Random movement styles ("curved", "overshoot", "linear")
- Click variance (±3 pixels default)
- Variable delays between clicks

---

## Arduino Mouse Service

### Purpose

Provides hardware-based mouse control via Arduino to evade software-based detection methods.

### Serial Communication Protocol

#### Message Format

**Movement Command:**
```
Format: "x;y\n"
Example: "1920;1080\n"

Where:
- x: Target X coordinate (absolute screen position)
- y: Target Y coordinate (absolute screen position)
- \n: Line terminator
```

**Click Command:**
```
Format: "l\n" | "r\n" | "m\n"

Where:
- "l\n": Left click
- "r\n": Right click
- "m\n": Middle click
```

#### Arduino Firmware Requirements

The Arduino must run firmware that:
1. Reads serial commands via `Serial.read()`
2. Parses command format (movement or click)
3. Uses Arduino Mouse library to control system cursor
4. Implements smooth movement interpolation
5. Sends acknowledgment (optional)

**Example Arduino Sketch Structure:**
```cpp
#include <Mouse.h>

void setup() {
  Serial.begin(115200);
  Mouse.begin();
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');

    if (command.indexOf(';') > 0) {
      // Movement command: "x;y"
      int sep = command.indexOf(';');
      int x = command.substring(0, sep).toInt();
      int y = command.substring(sep + 1).toInt();

      // Move cursor to absolute position
      moveTo(x, y);

    } else if (command == "l") {
      Mouse.click(MOUSE_LEFT);
    } else if (command == "r") {
      Mouse.click(MOUSE_RIGHT);
    } else if (command == "m") {
      Mouse.click(MOUSE_MIDDLE);
    }
  }
}

void moveTo(int target_x, int target_y) {
  // Implement smooth movement interpolation
  // Arduino Mouse library provides Mouse.move() for relative movement
  // You'll need to calculate deltas and interpolate
}
```

### Python Implementation

#### Connection Management

```python
class ArduinoMouseService:
    def _connect_arduino(self) -> Optional[serial.Serial]:
        try:
            connection = serial.Serial(
                port=self.serial_port,      # e.g., "COM3"
                baudrate=self.baud_rate,    # e.g., 115200
                timeout=1.0,
                write_timeout=1.0
            )

            # Wait for Arduino to initialize (bootloader)
            time.sleep(2.0)

            return connection

        except serial.SerialException as e:
            logger.warning(f"Failed to connect: {e}")
            return None
```

**Initialization Delay:**
- Arduino boards reset when serial connection opens
- Bootloader runs for ~2 seconds
- Must wait before sending commands

#### Position Tracking

```python
def _get_cursor_position(self) -> Tuple[int, int]:
    """Get current cursor position using Windows API."""
    try:
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        point = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
        return (point.x, point.y)

    except Exception as e:
        logger.error(f"Failed to get cursor position: {e}")
        return (0, 0)
```

**Why Windows API?**
- Arduino controls cursor via HID protocol
- Operating system tracks actual position
- Need OS-level API to verify movement accuracy

#### Multi-Pass Position Correction

```python
def move_to(self, x: int, y: int, ...) -> bool:
    # Send initial movement command
    self._send_movement(x, y, duration)

    # Multi-pass correction (up to 2 retries)
    for attempt in range(2):
        actual_x, actual_y = self._get_cursor_position()
        error = abs(actual_x - x) + abs(actual_y - y)

        if error <= 3:  # Within 3 pixels = success
            return True

        # Send correction
        logger.debug(f"Position correction attempt {attempt + 1}")
        self._send_movement(x, y, duration=0.05)

    return True  # Best effort
```

**Why correction needed?**
- Serial communication latency
- Arduino processing delays
- Screen resolution rounding
- Cumulative error in relative movements

#### Windows Timer Resolution Hack

```python
def _set_high_resolution_timer(self):
    """Improve time.sleep() accuracy from ~15ms to ~1ms."""
    try:
        import platform
        if platform.system() == 'Windows':
            timeBeginPeriod = ctypes.windll.winmm.timeBeginPeriod
            timeBeginPeriod(1)  # Set to 1ms resolution

            # Cleanup on exit
            import atexit
            timeEndPeriod = ctypes.windll.winmm.timeEndPeriod
            atexit.register(lambda: timeEndPeriod(1))
    except Exception as e:
        logger.warning(f"Failed to set high-resolution timer: {e}")
```

**Why this matters:**
- Default Windows timer: ~15.6ms granularity
- Smooth mouse movement needs <5ms precision
- `timeBeginPeriod(1)` improves accuracy to 1-2ms
- Critical for human-like movement

### Fallback System

```python
def __init__(self, config, serial_port, fallback_to_software=True):
    # Try Arduino connection
    self._connection = self._connect_arduino()

    # Fallback if unavailable
    if not self._connection and fallback_to_software:
        logger.warning("Falling back to software mouse")
        self._fallback = MouseService(config)
    else:
        self._fallback = None

def move_to(self, x, y, style, duration, speed_multiplier):
    # Use fallback if Arduino disconnected
    if self._fallback:
        return self._fallback.move_to(x, y, style, duration, speed_multiplier)

    # Otherwise use Arduino
    # ...
```

**Transparent fallback:**
- Same interface as `MouseService`
- Bot code unchanged
- Automatic detection and switching

---

## Configuration Reference

### Status Socket Configuration

```json
{
  "status_socket": {
    "enabled": true,
    "data_file": "live_data.json",
    "poll_interval": 0.1
  }
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | `true` | Enable Status Socket integration |
| `data_file` | string | `"live_data.json"` | Path to RuneLite output file |
| `poll_interval` | float | `0.1` | Poll frequency in seconds (10 Hz) |

### Walker Configuration

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

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `minimap_center_x` | int | `654` | Minimap center X (window-relative) |
| `minimap_center_y` | int | `111` | Minimap center Y (window-relative) |
| `tile_size` | int | `4` | Pixels per tile on minimap |
| `arrival_tolerance` | int | `2` | Tiles within target = arrived |
| `max_click_distance` | int | `15` | Max tiles to click at once |
| `enable_anti_ban_variance` | bool | `true` | Apply anti-ban randomization |

**Calibration Notes:**
- Minimap center coordinates are for **fixed window mode**
- Resizable mode may have different values
- Use calibration tool to find exact center

### Arduino Configuration

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

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | `false` | Enable Arduino mouse (requires hardware) |
| `serial_port` | string | `"COM3"` | Serial port (Windows: COM3, Linux: /dev/ttyUSB0) |
| `baud_rate` | int | `115200` | Serial communication speed |
| `fallback_to_software` | bool | `true` | Use MouseService if Arduino unavailable |
| `connection_timeout` | float | `2.0` | Connection timeout in seconds |

---

## API Reference

### GameActions (High-Level API)

#### walk_to_world_coordinate()

```python
def walk_to_world_coordinate(
    self,
    x: int,
    y: int,
    move_style: MovementStyle = "curved"
) -> bool:
    """
    Walk to world tile coordinates using advanced walker.

    Args:
        x: Target world X coordinate
        y: Target world Y coordinate
        move_style: Mouse movement style ("curved", "linear", "overshoot", "random")

    Returns:
        True if successfully arrived, False otherwise

    Example:
        # Walk to Varrock West Bank
        success = self.actions.walk_to_world_coordinate(3185, 3448)
    """
```

#### walk_path()

```python
def walk_path(
    self,
    waypoints: List[Tuple[int, int]],
    move_style: MovementStyle = "random"
) -> bool:
    """
    Follow a predefined path of world coordinates.

    Args:
        waypoints: List of (x, y) world coordinates to visit in order
        move_style: Mouse movement style for minimap clicks

    Returns:
        True if completed path successfully, False otherwise

    Example:
        # Walk from GE to Varrock West Bank
        path = [
            (3165, 3486),  # GE north entrance
            (3167, 3472),  # Path north
            (3185, 3436),  # Varrock square
            (3185, 3448)   # West bank
        ]
        success = self.actions.walk_path(path, move_style="curved")
    """
```

### WalkerService (Low-Level API)

#### world_to_minimap()

```python
def world_to_minimap(
    self,
    world_x: int,
    world_y: int,
    player_x: int,
    player_y: int,
    camera_yaw: int
) -> Optional[Tuple[int, int]]:
    """
    Convert world coordinates to minimap pixel coordinates.

    Args:
        world_x: Target world X
        world_y: Target world Y
        player_x: Player world X
        player_y: Player world Y
        camera_yaw: Camera yaw (0-2048)

    Returns:
        (minimap_x, minimap_y) in window-relative coords, or None if out of range

    Note:
        Applies 2D rotation matrix for camera angle compensation.
    """
```

#### compute_minimap_click()

```python
def compute_minimap_click(
    self,
    target_x: int,
    target_y: int
) -> Optional[Tuple[int, int]]:
    """
    Calculate minimap click position for target world coordinate.

    Convenience method that gets current player state automatically.

    Args:
        target_x: Target world X
        target_y: Target world Y

    Returns:
        (minimap_x, minimap_y) or None if unavailable
    """
```

### StatusSocketService (Low-Level API)

#### get_player_state()

```python
def get_player_state(self) -> Optional[PlayerState]:
    """
    Get current player state from Status Socket plugin.

    Returns:
        PlayerState if available, None if file unavailable or parse error

    Note:
        Uses file modification time caching to avoid redundant parsing.
    """
```

#### wait_for_arrival()

```python
def wait_for_arrival(
    self,
    target_x: int,
    target_y: int,
    tolerance: int = 2,
    timeout: float = 10.0
) -> bool:
    """
    Poll until player reaches target or timeout.

    Args:
        target_x: Target world X
        target_y: Target world Y
        tolerance: Distance in tiles to consider "arrived"
        timeout: Maximum wait time in seconds

    Returns:
        True if arrived, False on timeout

    Note:
        Includes stuck detection (5 checks without movement).
    """
```

---

## Implementation Details

### Integration Architecture

```
Bot Script (e.g., green_dragons_state.py)
    │
    └─→ self.actions.walk_path(waypoints)
            │
            ├─→ GameActions.walk_path()
            │       │
            │       └─→ WalkerService.walk_path()
            │               │
            │               ├─→ StatusSocketService.get_player_state()
            │               ├─→ WalkerService.world_to_minimap()
            │               ├─→ ScreenService.relative_to_absolute()
            │               └─→ MouseService.click_at()
            │                       │
            │                       └─→ (Optional) ArduinoMouseService
            │
            └─→ StatusSocketService.wait_for_arrival()
```

### Dependency Injection Chain

```python
# In runner.py:

# 1. Initialize Status Socket
self.status_socket = StatusSocketService(
    data_file="live_data.json",
    poll_interval=0.1
)

# 2. Initialize Walker (depends on Status Socket, Mouse, Screen)
self.walker = WalkerService(
    config=walker_config,
    status_socket=self.status_socket,
    mouse=self.mouse,
    screen=self.screen,
    interface=self.interface
)

# 3. Initialize GameActions (depends on Walker)
self.actions = GameActions(
    mouse=self.mouse,
    screen=self.screen,
    interface=self.interface,
    config=self.config,
    template_service=self.template_service,
    anti_ban=self.anti_ban,
    loot_detection=self.loot_detection,
    walker=self.walker  # ← Walker injected
)
```

### Error Handling Strategy

**Graceful Degradation:**
```python
# Status Socket unavailable → Walker disabled
if not self.status_socket.is_available():
    logger.info("WalkerService disabled (Status Socket not available)")
    self.walker = None

# Walker unavailable → walk_path returns False
if not self.walker:
    logger.error("WalkerService not initialized")
    return False
```

**Retry Logic:**
```python
# Walker retries each waypoint up to 10 times
max_attempts = 10
for attempt in range(max_attempts):
    if self._walk_to_waypoint(waypoint_x, waypoint_y, move_style):
        break  # Success
    logger.warning(f"Retry {attempt + 1}/{max_attempts}")
```

**Timeout Protection:**
```python
# wait_for_arrival has 10-second timeout per waypoint
if not self.status_socket.wait_for_arrival(x, y, timeout=10.0):
    logger.warning("Timeout walking to waypoint")
    return False
```

---

## Testing Guide

### Unit Tests

**Running All Tests:**
```bash
pytest tests/unit/services/test_status_socket_service.py -v
pytest tests/unit/services/test_walker_service.py -v
pytest tests/unit/services/test_arduino_mouse_service.py -v
```

**Key Test Categories:**

**Status Socket:**
- File monitoring and caching
- JSON parsing (valid/invalid data)
- Graceful degradation
- Stuck detection

**Walker:**
- **Rotation matrix accuracy** (8 directions tested)
- Boundary detection
- Distance calculations
- Waypoint following

**Arduino Mouse:**
- Serial protocol formatting
- Fallback behavior
- Position correction

### Integration Testing

**Manual Walker Test:**
```python
from osrsbot.core.runner import ScriptRunner

runner = ScriptRunner("RuneLite - YourAccount")

# Get current position from live_data.json first
state = runner.walker.status_socket.get_player_state()
print(f"Current position: ({state.world_x}, {state.world_y})")

# Test short walk (5 tiles north)
target_x = state.world_x
target_y = state.world_y + 5

print(f"Walking to ({target_x}, {target_y})")
success = runner.actions.walk_to_world_coordinate(target_x, target_y)

if success:
    print("✓ Walker test successful")
else:
    print("✗ Walker test failed")
```

**Camera Rotation Test:**
```python
# Critical test: Verify rotation matrix works at all angles

test_angles = [
    (0, "North"),
    (512, "East"),
    (1024, "South"),
    (1536, "West")
]

for yaw, direction in test_angles:
    print(f"\nTesting camera facing {direction} (yaw={yaw})")

    # Manually rotate camera in-game to match yaw
    input(f"Rotate camera to face {direction}, then press Enter...")

    # Walk 5 tiles north
    state = runner.walker.status_socket.get_player_state()
    target_x = state.world_x
    target_y = state.world_y + 5

    success = runner.actions.walk_to_world_coordinate(target_x, target_y)

    if success:
        print(f"✓ {direction} test passed")
    else:
        print(f"✗ {direction} test FAILED - rotation matrix error!")
```

---

## Troubleshooting

### Walker Issues

#### Player Walks Wrong Direction

**Symptoms:** Character walks opposite direction or perpendicular to target.

**Causes:**
1. Incorrect rotation matrix calculation
2. Wrong minimap center coordinates
3. Camera yaw not in 0-2048 range

**Solutions:**
1. Test with camera facing north (yaw=0) first
2. Verify minimap center in config matches actual center
3. Check `live_data.json` yaw values are 0-2048
4. Run rotation matrix unit tests

#### Player Gets Stuck

**Symptoms:** Character stops moving, timeout occurs.

**Causes:**
1. Obstacle blocking path
2. Arrival tolerance too small
3. Network lag/disconnection

**Solutions:**
1. Increase `arrival_tolerance` to 3-4 tiles
2. Add intermediate waypoints around obstacles
3. Check for random events
4. Verify Status Socket still updating

#### Clicks Outside Minimap

**Symptoms:** Mouse clicks far from minimap, nothing happens.

**Causes:**
1. Target outside minimap view distance
2. Boundary check not working
3. Coordinate calculation error

**Solutions:**
1. Verify `max_click_distance` ≤ 15 tiles
2. Check minimap radius (default: 73px)
3. Use path chunking for long distances

### Status Socket Issues

#### Plugin Not Detected

**Error:** `Status Socket plugin not detected. Walker disabled.`

**Solutions:**
1. Install plugin from RuneLite Plugin Hub
2. Verify `live_data.json` exists
3. Check file path in config matches actual location
4. Ensure plugin is enabled (green checkmark)

#### Data Stale Warning

**Warning:** `Status Socket data is stale (5.0s since last update)`

**Solutions:**
1. RuneLite may have crashed - restart
2. Plugin may have disabled itself - re-enable
3. Character may be logged out
4. Check RuneLite logs for errors

### Arduino Mouse Issues

#### Connection Failed

**Error:** `Failed to connect to Arduino on COM3`

**Solutions:**
1. Check Device Manager for correct port
2. Verify Arduino connected via USB
3. Try different USB port
4. Install Arduino drivers if needed
5. Check `serial_port` in config

#### Position Inaccurate

**Symptoms:** Cursor drifts, clicks miss targets.

**Solutions:**
1. Increase baud rate to 115200
2. Implement better interpolation in Arduino firmware
3. Check for USB interference
4. Verify Windows timer resolution hack is working

#### Permission Denied (Linux)

**Error:** `Permission denied: '/dev/ttyUSB0'`

**Solution:**
```bash
sudo usermod -a -G dialout $USER
# Log out and log back in
```

---

## Performance Considerations

### Walker Performance

**Typical Timings:**
- Position poll: 0.1s (configurable)
- Rotation calculation: <1ms
- Click execution: 0.2-0.6s (mouse movement)
- Arrival detection: 0.5-2s (depends on distance)
- Total per waypoint: 1-5s

**Optimization Tips:**
- Lower `poll_interval` for faster response (min: 0.05s)
- Increase `max_click_distance` for fewer clicks (max: ~18 tiles)
- Use straight paths to reduce waypoint count

### Status Socket Performance

**File I/O Optimization:**
- Modification time check: ~0.1ms
- JSON parsing: ~1-2ms
- Caching eliminates redundant parsing
- Typical overhead: <1% CPU usage

### Arduino Mouse Performance

**Latency Sources:**
- Serial write: ~1-2ms
- Arduino processing: ~1-5ms
- USB transfer: ~1ms
- Total latency: ~5-10ms

**Comparison:**
- Software mouse: 0ms latency
- Arduino mouse: 5-10ms latency
- Human reaction time: 200-300ms

**Verdict:** Arduino latency is negligible compared to human reaction time.

---

## Future Enhancements

### Potential Improvements

**Walker:**
- [ ] A* pathfinding with obstacle avoidance
- [ ] Dynamic path recalculation on stuck
- [ ] Multi-floor navigation (z-level support)
- [ ] Path caching for repeated routes
- [ ] Integration with web walking APIs

**Arduino Mouse:**
- [ ] Bezier curve movement in firmware
- [ ] Mouse acceleration curves
- [ ] Multi-device support (failover)
- [ ] Bluetooth Arduino support

**Status Socket:**
- [ ] Network socket support (TCP/UDP)
- [ ] Multiple client connections
- [ ] Historical position tracking
- [ ] Movement prediction

---

## Credits & References

**Implementation Based On:**
- RuneLite Status Socket Plugin: https://github.com/while-loop/runelite-plugins
- OSRS Basic Botting Functions: https://github.com/slyautomation/osrs_basic_botting_functions

**Mathematical References:**
- 2D Rotation Matrix: https://en.wikipedia.org/wiki/Rotation_matrix
- Coordinate System Transformations

**Technologies:**
- Python 3.10+
- pyautogui (mouse control)
- pyserial (Arduino communication)
- RuneLite/OpenOSRS

---

*Last Updated: 2025-12-22*
*Framework Version: 1.0.0*
