# OSRS Bot Architecture Documentation

**Date**: December 12, 2025
**Version**: 1.0

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Design Patterns](#2-design-patterns)
3. [Layered Architecture](#3-layered-architecture)
4. [Component Details](#4-component-details)
5. [Data Flow](#5-data-flow)
6. [Extension Points](#6-extension-points)

---

## 1. Architecture Overview

The OSRS Bot implements a **layered, service-oriented architecture** with clear separation of concerns and CQRS pattern for game operations.

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 APPLICATION LAYER                        │
│                                                          │
│  ┌──────────────────┐      ┌──────────────────┐        │
│  │   CLI Menu       │      │  Calibration     │        │
│  │  (menu.py)       │      │  Tool            │        │
│  └──────────────────┘      └──────────────────┘        │
└─────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│       ORCHESTRATION LAYER (Dependency Injection)         │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │           ScriptRunner                          │   │
│  │  - Loads Config                                 │   │
│  │  - Initializes GameInterface                    │   │
│  │  - Creates all Services                         │   │
│  │  - Creates GameState (Queries)                  │   │
│  │  - Creates GameActions (Commands)               │   │
│  │  - Injects dependencies into Bots               │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│            COMMAND/QUERY LAYER (CQRS)                    │
│                                                          │
│  ┌──────────────────┐      ┌──────────────────┐        │
│  │   GameActions    │      │   GameState      │        │
│  │   (Commands)     │      │   (Queries)      │        │
│  └──────────────────┘      └──────────────────┘        │
└─────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│              CORE LAYER (Business Logic)                 │
│                                                          │
│  ┌─────────────────────────┐  ┌──────────────────┐     │
│  │   Bot Base              │  │ StateMachineBot  │     │
│  └─────────────────────────┘  └──────────────────┘     │
└─────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│               SERVICES LAYER (Low-level)                 │
│                                                          │
│  ┌─────────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐ │
│  │GameInterface│ │ Mouse   │ │ Screen  │ │   OCR    │ │
│  │(Foundation) │ │ Service │ │ Service │ │ Service  │ │
│  └─────────────┘ └─────────┘ └─────────┘ └──────────┘ │
│                                                          │
│  ┌──────────┐ ┌─────────┐ ┌─────────────────────────┐ │
│  │Template  │ │Anti-Ban │ │   ClickTargetTracker    │ │
│  │ Matcher  │ │ Service │ │                          │ │
│  └──────────┘ └─────────┘ └─────────────────────────┘ │
│                                                          │
│  ┌─────────────┐ ┌────────────┐ ┌──────────────────┐  │
│  │StatusSocket │ │   Walker   │ │  ArduinoMouse    │  │
│  │  Service    │ │  Service   │ │    Service       │  │
│  └─────────────┘ └────────────┘ └──────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  MODEL LAYER (Data)                      │
│                                                          │
│  ┌──────────────────┐      ┌──────────────────┐        │
│  │     Config       │      │   StateTypes     │        │
│  └──────────────────┘      └──────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Design Principles

1. **Separation of Concerns**: Each layer has distinct responsibilities
2. **Dependency Injection**: Services are injected, enabling testability
3. **Single Responsibility**: Each service/class has one clear purpose
4. **Open/Closed**: Open for extension via inheritance, closed for modification
5. **Interface Segregation**: Small, focused interfaces (CQRS)
6. **Dependency Inversion**: High-level modules don't depend on low-level details

---

## 2. Design Patterns

### 2.1 CQRS (Command Query Responsibility Segregation)

**Purpose**: Separate operations that modify state from those that read state

#### Commands (GameActions)
**File**: [src/osrsbot/commands/game_actions.py](../src/osrsbot/commands/game_actions.py)

```python
class GameActions:
    """Commands that modify game state"""

    def click_coordinate(self, name: str) -> None:
        """Execute a click action"""

    def walk_to_marker(self, marker: str) -> None:
        """Execute a movement action"""

    def wait(self, timing_type: str) -> None:
        """Execute a timing action"""
```

#### Queries (GameState, InventoryState)
**Files**:
- [src/osrsbot/queries/game_queries.py](../src/osrsbot/queries/game_queries.py)
- [src/osrsbot/queries/inventory_queries.py](../src/osrsbot/queries/inventory_queries.py)

```python
class GameState:
    """Queries that read game state"""

    def get_hp(self) -> Optional[int]:
        """Read current HP"""

    def is_in_combat(self) -> bool:
        """Check combat status"""

class InventoryState:
    """Queries for inventory state"""

    def is_full(self) -> bool:
        """Check if inventory is full"""
```

**Benefits**:
- Clear separation between reads and writes
- Easier testing (mock queries, verify commands)
- Better performance (can optimize queries separately)

### 2.2 State Machine Pattern

**File**: [src/osrsbot/core/state_machine_bot.py](../src/osrsbot/core/state_machine_bot.py)

**Purpose**: Manage complex bot workflows with explicit states and transitions

```python
class StateMachineBot(Bot):
    """State machine framework for complex automation"""

    def define_states(self) -> Dict[Enum, StateMetadata]:
        """Define states with metadata (retries, timeouts, failovers)"""

    def define_transitions(self) -> Dict[Enum, Enum]:
        """Define state-to-state transitions"""

    def handle_state(self, state: Enum, context: StateExecutionContext) -> StateResult:
        """Execute state logic"""
```

**State Execution Flow**:
```
1. Enter State
   ↓
2. Execute State Handler
   ↓
3. Check Result (SUCCESS, RETRY, FAILURE)
   ↓
4. If RETRY and retries < max_retries:
   → Re-execute state
   ↓
5. If FAILURE or max retries exceeded:
   → Transition to failover state
   ↓
6. If SUCCESS:
   → Transition to next state
   ↓
7. Check anti-ban (should take break?)
   ↓
8. Repeat until terminal state or max iterations
```

**Example Usage**:
```python
class GreenDragonsBot(StateMachineBot):
    def define_states(self):
        return {
            States.IDLE: StateMetadata(name="Idle"),
            States.COMBAT: StateMetadata(
                name="Combat",
                max_retries=5,
                timeout=300.0,
                failover_state=States.RECOVERY
            ),
        }

    def handle_state(self, state, context):
        if state == States.COMBAT:
            return self._handle_combat(context)
```

**Benefits**:
- Explicit state definitions
- Automatic retry logic
- Failover on errors
- History tracking for debugging

### 2.3 Strategy Pattern

**Purpose**: Encapsulate algorithms and make them interchangeable

#### OCR Preprocessing Strategies
**File**: [src/osrsbot/services/ocr_service.py](../src/osrsbot/services/ocr_service.py)

```python
@dataclass(frozen=True)
class PreprocessingStrategy:
    name: str
    resize_multiplier: int
    contrast_level: float
    threshold: int

strategies = [
    PreprocessingStrategy("low_contrast", 2, 1.5, 127),
    PreprocessingStrategy("medium_contrast", 3, 2.0, 127),
    PreprocessingStrategy("high_contrast", 4, 2.5, 127),
    PreprocessingStrategy("very_high_contrast", 4, 3.0, 127),
    PreprocessingStrategy("adaptive", 3, 2.0, -1),
]
```

#### Mouse Movement Strategies
**File**: [src/osrsbot/services/mouse_service.py](../src/osrsbot/services/mouse_service.py)

- Linear movement
- Bezier curve movement
- Instant movement
- Overshoot movement

**Benefits**:
- Easy to add new strategies
- Can switch strategies at runtime
- Testable in isolation

### 2.4 Service Architecture Pattern

**Purpose**: Organize functionality into reusable, focused services

**Services**:
- [MouseService](../src/osrsbot/services/mouse_service.py) - Mouse control
- [ScreenService](../src/osrsbot/services/screen_service.py) - Screen capture
- [OCRService](../src/osrsbot/services/ocr_service.py) - Text recognition
- [TemplateMatchService](../src/osrsbot/services/template_match_service.py) - UI detection
- [AntiBanService](../src/osrsbot/services/anti_ban_service.py) - Anti-detection

**Dependency Injection**:
```python
# ScriptRunner creates all services
mouse = MouseService(interface, config)
screen = ScreenService(interface, config)
actions = GameActions(interface, config, mouse, screen, state)

# Services are injected into consumers
bot = GreenDragonsBot(interface, state, actions, config)
```

**Benefits**:
- Testability (mock services)
- Flexibility (swap implementations)
- Reusability (services used by multiple consumers)

---

## 3. Layered Architecture

### 3.1 Layer Responsibilities

#### Layer 6: Application Layer
**Location**: [src/osrsbot/app/](../src/osrsbot/app/)

**Responsibility**: User interface and interaction

**Components**:
- `menu.py` - Interactive CLI menu for script selection
- `calibration.py` - Color and coordinate calibration tool

**Dependencies**: All lower layers

---

#### Layer 5: Orchestration Layer (Dependency Injection)
**Location**: [src/osrsbot/core/runner.py](../src/osrsbot/core/runner.py)

**Responsibility**: Initialize and wire up all dependencies before bot execution

**Components**:
- `ScriptRunner` - Dependency injection orchestrator
  - Loads Config
  - Initializes GameInterface
  - Creates all Services (Mouse, Screen, OCR, etc.)
  - Creates GameState (Queries)
  - Creates GameActions (Commands)
  - Injects dependencies into Bots

**Dependencies**: All lower layers

**Key Point**: ScriptRunner runs FIRST, creating the CQRS layer (GameActions/GameState) and all services before any bot logic executes.

---

#### Layer 4: Command/Query Layer (CQRS)
**Location**: [src/osrsbot/commands/](../src/osrsbot/commands/), [src/osrsbot/queries/](../src/osrsbot/queries/)

**Responsibility**: Game operation abstraction

**Components**:
- `GameActions` (Commands) - High-level game operations
- `GameState` (Queries) - Read-only state checks
- `InventoryState` (Queries) - Inventory queries

**Dependencies**: Core layer, Services layer

**Note**: These are created and initialized by ScriptRunner before being injected into bots.

---

#### Layer 3: Core Layer
**Location**: [src/osrsbot/core/](../src/osrsbot/core/)

**Responsibility**: Business logic and bot framework

**Components**:
- `Bot` - Abstract base class for all bots
- `StateMachineBot` - State machine framework

**Dependencies**: Services layer, Model layer, CQRS layer (via injection)

---

#### Layer 2: Services Layer
**Location**: [src/osrsbot/services/](../src/osrsbot/services/) and [src/osrsbot/core/game_interface.py](../src/osrsbot/core/game_interface.py)

**Responsibility**: Low-level automation primitives and infrastructure

**Components**:
- `GameInterface` - Window management and coordinate translation (foundational service)
- `MouseService` - Mouse movement and clicking
- `ScreenService` - Screen capture and pixel detection
- `OCRService` - Optical character recognition
- `TemplateMatchService` - UI element detection
- `AntiBanService` - Behavioral randomization
- `ClickTargetTracker` - Click verification
- `StatusSocketService` - Real-time player position/camera data from RuneLite plugin
- `WalkerService` - Advanced pathfinding with camera rotation compensation
- `ArduinoMouseService` - Hardware mouse control via serial connection (optional)

**Dependencies**: Model layer only

**Note**: GameInterface is physically located in `core/` but conceptually belongs to the Services layer as it provides infrastructure services (window management, coordinate translation) rather than business logic.

---

#### Layer 1: Model Layer
**Location**: [src/osrsbot/models/](../src/osrsbot/models/)

**Responsibility**: Data structures and configuration

**Components**:
- `Config` - Configuration management
- `StateTypes` - State machine type definitions
- `UIElements` - UI element definitions

**Dependencies**: None (foundational layer)

---

### 3.2 Dependency Rules

**Allowed**:
- ✓ Higher layers depend on lower layers
- ✓ Same layer components can interact
- ✓ Services can depend on other services (with care)

**Not Allowed**:
- ✗ Lower layers depend on higher layers
- ✗ Model layer depends on anything
- ✗ Circular dependencies

---

## 4. Component Details

### 4.1 Service Components

#### GameInterface (Foundational Service)
**File**: [src/osrsbot/core/game_interface.py](../src/osrsbot/core/game_interface.py)

**Layer**: Services (despite being in core/ directory)

**Responsibility**: Window management and coordinate translation

**Key Methods**:
```python
def __init__(self, config: Config):
    """Find and attach to game window"""

def get_bounds(self) -> Tuple[int, int, int, int]:
    """Get window bounds (x, y, width, height)"""

def to_absolute_coordinates(self, x: int, y: int) -> Tuple[int, int]:
    """Convert relative to absolute coordinates"""

def to_relative_coordinates(self, x: int, y: int) -> Tuple[int, int]:
    """Convert absolute to relative coordinates"""
```

**Design Notes**:
- Foundational infrastructure service
- Single source of truth for window position
- Coordinate translation abstraction
- Dynamic window tracking
- Used as dependency by other services (MouseService, ScreenService)

**Why It's a Service, Not Core Logic**:
- Provides low-level OS/platform operations (window management)
- No business rules or workflow decisions
- Reusable infrastructure component
- Other services depend on it

---

### 4.2 Core Components

---

#### Bot (Base Class)
**File**: [src/osrsbot/core/base_bot.py](../src/osrsbot/core/base_bot.py)

**Responsibility**: Abstract base for all bot scripts

**Key Methods**:
```python
def run(self, bank_location: str, runs: int = 1):
    """Main execution loop"""

def run_cycle(self, bank_location: str, run_number: int):
    """Single bot iteration - ABSTRACT"""

def withdraw_food(self, bank_location: str):
    """Common banking logic"""
```

**Design Notes**:
- Template method pattern
- Subclasses implement `run_cycle()`
- Common utilities provided

---

#### StateMachineBot
**File**: [src/osrsbot/core/state_machine_bot.py](../src/osrsbot/core/state_machine_bot.py)

**Responsibility**: State machine framework

**Key Components**:
```python
class StateMachineBot(Bot):
    # State machine configuration
    def define_states(self) -> Dict[Enum, StateMetadata]:
        """Define states with retry/timeout/failover"""

    def define_transitions(self) -> Dict[Enum, Enum]:
        """Define state transitions"""

    def define_initial_state(self) -> Enum:
        """Define starting state"""

    # State handlers
    def handle_state(self, state: Enum, context: StateExecutionContext):
        """Execute state logic"""

    # Execution
    def run_cycle(self, bank_location: str, run_number: int):
        """Execute state machine"""
```

**State Execution Context**:
```python
@dataclass
class StateExecutionContext:
    state: Enum
    run_number: int
    bank_location: str
    attempt: int  # Retry count
```

**State Metadata**:
```python
@dataclass
class StateMetadata:
    name: str
    max_retries: int = 3
    timeout: Optional[float] = None
    failover_state: Optional[Enum] = None
```

**Design Notes**:
- Declarative state definition
- Automatic retry and failover
- Comprehensive logging

---

#### ScriptRunner
**File**: [src/osrsbot/core/runner.py](../src/osrsbot/core/runner.py)

**Responsibility**: Dependency injection orchestrator

**Initialization Flow**:
```python
def __init__(self, config_path: str = "config.json"):
    # 1. Load configuration
    self.config = Config.load(config_path)

    # 2. Initialize game interface
    self.interface = GameInterface(self.config)

    # 3. Initialize services
    self.mouse = MouseService(self.interface, self.config)
    self.screen = ScreenService(self.interface, self.config)
    self.ocr = OCRService(self.config)
    self.template_matcher = TemplateMatchService(self.screen, self.config)
    self.anti_ban = AntiBanService(self.mouse, self.screen, self.config)

    # 4. Initialize queries
    self.state = GameState(
        self.interface, self.config, self.screen,
        self.ocr, self.template_matcher
    )

    # 5. Initialize commands
    self.actions = GameActions(
        self.interface, self.config, self.mouse,
        self.screen, self.state
    )
```

**Design Notes**:
- Centralized service creation
- Manages dependency graph
- Provides unified interface for bot execution

---

### 4.3 Additional Service Components

#### MouseService
**File**: [src/osrsbot/services/mouse_service.py](../src/osrsbot/services/mouse_service.py)

**Responsibility**: Humanized mouse movement and clicking

**Key Features**:
- Bezier curve movement
- Overshoot simulation (15% chance)
- Click variance (±3 pixels)
- Speed randomization
- Post-click delays

**Key Methods**:
```python
def move_to(self, x: int, y: int, movement_type: str = "curved"):
    """Move mouse to position"""

def click(self, x: int, y: int, button: str = "left"):
    """Click at position"""

def drag(self, x1: int, y1: int, x2: int, y2: int):
    """Drag from one position to another"""
```

---

#### ScreenService
**File**: [src/osrsbot/services/screen_service.py](../src/osrsbot/services/screen_service.py)

**Responsibility**: Screen capture and pixel detection

**Key Features**:
- Color detection with tolerance
- Pixel color sampling
- Region capture support
- NumPy optimization for performance

**Key Methods**:
```python
def find_color(
    self, hex_color: str, tolerance: int = 10,
    region: Optional[Tuple] = None, find_all: bool = False
) -> Optional[Union[ColorMatch, List[ColorMatch]]]:
    """Find color on screen"""

def get_pixel_color(self, x: int, y: int) -> Tuple[int, int, int]:
    """Get RGB color at position"""
```

---

#### OCRService
**File**: [src/osrsbot/services/ocr_service.py](../src/osrsbot/services/ocr_service.py)

**Responsibility**: Optical character recognition

**Key Features**:
- 5 preprocessing strategies
- Digit-only recognition
- Shape detection (4 vs 9 disambiguation)
- Result consensus voting

**Key Methods**:
```python
def read_digits(
    self, screenshot: Image.Image, region: Optional[Tuple] = None
) -> Optional[int]:
    """Read digits from screenshot using multiple strategies"""
```

**Strategies**:
1. Low contrast (2x resize, 1.5 contrast)
2. Medium contrast (3x resize, 2.0 contrast)
3. High contrast (4x resize, 2.5 contrast)
4. Very high contrast (4x resize, 3.0 contrast)
5. Adaptive threshold

---

#### TemplateMatchService
**File**: [src/osrsbot/services/template_match_service.py](../src/osrsbot/services/template_match_service.py)

**Responsibility**: UI element detection via template matching

**Key Features**:
- Grid-based detection (inventory)
- Single template matching (buttons, icons)
- Confidence thresholds
- Sticky caching (5s TTL)

**Key Methods**:
```python
def find_in_grid(
    self, grid_name: str, row: int, col: int
) -> Optional[Tuple[int, int]]:
    """Find element in UI grid"""

def find_template(self, template_name: str) -> Optional[Tuple[int, int]]:
    """Find single template match"""
```

---

#### AntiBanService
**File**: [src/osrsbot/services/anti_ban_service.py](../src/osrsbot/services/anti_ban_service.py)

**Responsibility**: Behavioral randomization and anti-detection

**Key Features**:
- Scheduled breaks (30-60 min intervals)
- Micro-breaks (5% random chance)
- Session variance (±15% timing)
- Idle actions (mouse jitter, stats check)
- Action pattern tracking

**Key Methods**:
```python
def should_take_break(self) -> bool:
    """Check if break is needed"""

def take_scheduled_break(self) -> None:
    """Execute break with random duration"""

def perform_idle_action(self) -> None:
    """Execute random idle action"""

def get_timing_variance(self, base_timing: float) -> float:
    """Apply session variance to timing"""
```

---

#### StatusSocketService
**File**: [src/osrsbot/services/status_socket_service.py](../src/osrsbot/services/status_socket_service.py)

**Responsibility**: Real-time player position and camera data from RuneLite Status Socket plugin

**Key Features**:
- Monitors live_data.json for player state updates
- File modification time caching (avoids re-parsing unchanged data)
- Graceful degradation if plugin unavailable
- Stuck detection (player not moving)
- World coordinate and camera yaw tracking

**Key Methods**:
```python
def get_player_state(self) -> Optional[PlayerState]:
    """Get current player world position, plane, and camera yaw"""

def is_available(self) -> bool:
    """Check if Status Socket plugin is active"""

def wait_for_arrival(
    self, target_x: int, target_y: int,
    tolerance: int = 2, timeout: float = 10.0
) -> bool:
    """Poll until player reaches target coordinates"""
```

**PlayerState Dataclass**:
```python
@dataclass
class PlayerState:
    world_x: int          # World X coordinate
    world_y: int          # World Y coordinate
    plane: int            # Game plane (0-3)
    camera_yaw: int       # Camera rotation (0-2048, 0=north)
    timestamp: float      # Last update time
    is_moving: bool       # Movement detection
    animation_id: int     # Current animation ID
```

**Design Notes**:
- Required for WalkerService
- Falls back gracefully if plugin not installed
- Implements file-based IPC with RuneLite

---

#### WalkerService
**File**: [src/osrsbot/services/walker_service.py](../src/osrsbot/services/walker_service.py)

**Responsibility**: World coordinate pathfinding with camera rotation compensation

**Key Features**:
- 2D rotation matrix for camera angle compensation
- World tiles → minimap pixels conversion
- Waypoint-based path following
- Arrival detection with tolerance
- Distance-based click range limiting

**Key Methods**:
```python
def walk_to(
    self, target_x: int, target_y: int,
    path: Optional[List[Tuple[int, int]]] = None,
    move_style: MovementStyle = "curved"
) -> bool:
    """Walk to world coordinates. Returns True if arrived."""

def walk_path(
    self, waypoints: List[Tuple[int, int]],
    move_style: MovementStyle = "curved"
) -> bool:
    """Follow predefined path of world coordinates."""

def world_to_minimap(
    self, world_x: int, world_y: int,
    player_x: int, player_y: int, camera_yaw: int
) -> Optional[Tuple[int, int]]:
    """Convert world tiles to minimap pixels using rotation matrix."""
```

**Rotation Matrix Algorithm**:
```python
# Convert world delta to minimap pixels
dx = world_x - player_x
dy = world_y - player_y

# Convert camera yaw (0-2048) to degrees
degrees = 360 - (camera_yaw * (360 / 2048))
theta = radians(degrees)

# Apply 2D rotation matrix
rotated_x = dx * cos(theta) - dy * sin(theta)
rotated_y = dx * sin(theta) + dy * cos(theta)

# Scale to minimap pixels (4 pixels per tile)
pixel_x = rotated_x * 4
pixel_y = rotated_y * 4

# Translate to minimap center
minimap_x = center_x + pixel_x
minimap_y = center_y + pixel_y
```

**Design Notes**:
- Depends on StatusSocketService for player position/camera
- Handles camera rotation automatically
- Supports intermediate waypoints for long distances
- Integrates with existing MouseService for clicking

---

#### ArduinoMouseService
**File**: [src/osrsbot/services/arduino_mouse_service.py](../src/osrsbot/services/arduino_mouse_service.py)

**Responsibility**: Hardware mouse control via Arduino serial connection

**Key Features**:
- Drop-in replacement for MouseService (identical interface)
- Serial communication protocol for movement and clicks
- Multi-pass position correction (up to 2 retries)
- Automatic fallback to software mouse if Arduino unavailable
- Windows high-resolution timer for accurate movement timing

**Key Methods**:
```python
def move_to(
    self, x: int, y: int,
    style: MovementStyle = "curved",
    duration: Optional[float] = None,
    speed_multiplier: float = 1.0
) -> bool:
    """Move mouse to absolute screen coordinates via Arduino"""

def click_at(
    self, x: int, y: int,
    button: Literal["left", "right", "middle"] = "left",
    move_style: MovementStyle = "curved",
    variance: bool = True,
    speed_multiplier: float = 1.0
) -> bool:
    """Move to position and click via Arduino"""
```

**Serial Protocol**:
- Movement: `"x;y\n"` (e.g., `"1920;1080\n"`)
- Left click: `"l\n"`
- Right click: `"r\n"`
- Middle click: `"m\n"`

**Design Notes**:
- Optional feature (disabled by default in config)
- Requires pyserial and Arduino hardware with custom firmware
- Falls back to MouseService if connection fails
- Position verification using Windows API (GetCursorPos)

---

## 5. Data Flow

### 5.1 Bot Execution Flow

```
User Input (menu.py)
        ↓
ScriptRunner.run_script(BotClass, runs, bank_location)
        ↓
Bot Instance Created
    - Dependencies injected (interface, state, actions, config)
        ↓
bot.run(bank_location, runs)
    ├─> For each run:
    │   ├─> run_cycle(bank_location, run_number)
    │   │       ↓
    │   │   [Bot-specific logic]
    │   │   - State machine transitions (if StateMachineBot)
    │   │   - Or custom logic (if function-based bot)
    │   │       ↓
    │   │   GameActions (Commands)
    │   │   - actions.click_color("dragon")
    │   │   - actions.wait("short")
    │   │   - actions.walk_to_marker("bank")
    │   │       ↓
    │   │   Services (Low-level)
    │   │   - mouse.move_to(x, y)
    │   │   - screen.find_color(hex_color)
    │   │       ↓
    │   │   GameState (Queries)
    │   │   - state.get_hp()
    │   │   - state.is_in_combat()
    │   │   - inventory.is_full()
    │   │       ↓
    │   │   Anti-Ban Checks
    │   │   - anti_ban.should_take_break()
    │   │   - anti_ban.perform_idle_action()
    │   │       ↓
    │   └─> run_cycle() complete
    │
    └─> All runs complete
        ↓
Execution finished
```

### 5.2 Command Flow (CQRS)

**Command Example: Click Color**
```
actions.click_color("green_dragon")
        ↓
GameActions.click_color()
    ├─> config.get("colors", "green_dragon")  # Get hex color
    ├─> screen.find_color(hex_color)          # Find on screen
    │       ↓
    │   ScreenService captures screenshot
    │   Converts to NumPy array
    │   Searches for matching pixels
    │       ↓
    │   Returns ColorMatch(x, y)
    │
    ├─> mouse.move_to(x, y, "curved")         # Move to target
    │       ↓
    │   MouseService calculates Bezier curve
    │   Applies speed variance
    │   Optionally adds overshoot
    │       ↓
    │   pyautogui.move(...)
    │
    └─> mouse.click(x, y)                     # Click
            ↓
        MouseService adds click variance (±3px)
        Adds post-click delay
            ↓
        pyautogui.click(...)
```

**Query Example: Get HP**
```
current_hp = state.get_hp()
        ↓
GameState.get_hp()
    ├─> config.get("coordinates", "hp_box")   # Get HP region
    ├─> screen.capture_region(hp_region)      # Capture screenshot
    │       ↓
    │   ScreenService captures specific region
    │   Returns PIL Image
    │
    └─> ocr.read_digits(screenshot)           # OCR
            ↓
        OCRService tries 5 strategies
        ├─> Preprocess image (resize, invert, threshold)
        ├─> pytesseract.image_to_string()
        ├─> Parse digits
        └─> Return consensus result
```

### 5.3 State Machine Flow

**State Transition Example**:
```
StateMachineBot.run_cycle()
    ├─> Initialize state machine (if needed)
    │   - Load state definitions
    │   - Load transitions
    │   - Set initial state
    │
    └─> Execute state loop:
        ├─> Get current state metadata
        │   - max_retries, timeout, failover_state
        │
        ├─> Create execution context
        │   - state, run_number, bank_location, attempt
        │
        ├─> Execute state handler (with retry)
        │   └─> handle_state(current_state, context)
        │       ├─> Bot-specific logic
        │       │   - actions.click_color(...)
        │       │   - while not inventory.is_full(): ...
        │       │
        │       └─> Return StateResult (SUCCESS, RETRY, FAILURE)
        │
        ├─> Process result
        │   ├─> If RETRY and attempt < max_retries:
        │   │   └─> Increment attempt, retry state
        │   │
        │   ├─> If FAILURE or max retries exceeded:
        │   │   └─> Transition to failover_state
        │   │
        │   └─> If SUCCESS:
        │       └─> Transition to next state (from transitions map)
        │
        ├─> Check anti-ban
        │   └─> If anti_ban.should_take_break():
        │       └─> anti_ban.take_scheduled_break()
        │
        └─> Repeat until terminal state or max iterations
```

### 5.4 Walker/Pathfinding Flow

**Walking to World Coordinates Example**:
```
actions.walk_to_world_coordinate(3185, 3448)  # Varrock West Bank
        ↓
GameActions.walk_to_world_coordinate()
    ├─> Checks if WalkerService initialized
    │
    └─> walker.walk_to(3185, 3448)
            ↓
        WalkerService.walk_to()
            ├─> status_socket.get_player_state()
            │       ↓
            │   StatusSocketService reads live_data.json
            │   Returns: PlayerState(world_x=3165, world_y=3486, camera_yaw=1024)
            │
            ├─> Calculate distance to target
            │   distance = sqrt((3185-3165)² + (3448-3486)²) = ~42 tiles
            │
            ├─> Loop until arrival:
            │   │
            │   ├─> world_to_minimap(3185, 3448, player_x, player_y, camera_yaw)
            │   │       ↓
            │   │   Apply 2D rotation matrix:
            │   │   1. dx = 20, dy = -38
            │   │   2. Convert yaw 1024 → 180° (facing south)
            │   │   3. Rotate: rotated_x = 20*cos(180°) - (-38)*sin(180°) = -20
            │   │              rotated_y = 20*sin(180°) + (-38)*cos(180°) = 38
            │   │   4. Scale: pixel_x = -20*4 = -80, pixel_y = 38*4 = 152
            │   │   5. Translate: minimap_x = 654 + (-80) = 574
            │   │                 minimap_y = 111 + 152 = 263
            │   │       ↓
            │   │   Returns: (574, 263)
            │   │
            │   ├─> mouse.click_at(574, 263, move_style="curved")
            │   │       ↓
            │   │   MouseService moves cursor with Bezier curve
            │   │   Clicks minimap position
            │   │
            │   ├─> status_socket.wait_for_arrival(3185, 3448, tolerance=2)
            │   │       ↓
            │   │   Poll player position every 100ms:
            │   │   - Current: (3170, 3475) → distance = 21 tiles → keep waiting
            │   │   - Current: (3178, 3460) → distance = 13 tiles → keep waiting
            │   │   - Current: (3184, 3449) → distance = 1 tile → ARRIVED!
            │   │       ↓
            │   │   Returns: True
            │   │
            │   └─> Check if arrived (distance <= 2)
            │       ↓
            │   SUCCESS - player reached target
            │
            └─> Returns: True

**Key Insight**: Camera rotation (yaw) is automatically compensated by the rotation
matrix, so clicks on the minimap are always accurate regardless of camera angle.
```

**Path Following Example**:
```
path = [(3165, 3486), (3167, 3472), (3185, 3436), (3185, 3448)]
actions.walk_path(path)
        ↓
WalkerService.walk_path(waypoints)
    ├─> For each waypoint in path:
    │   │
    │   ├─> walk_to(waypoint_x, waypoint_y)
    │   │   [Executes full walk_to flow above]
    │   │       ↓
    │   │   Waypoint 1 (3165, 3486): ✓ Reached
    │   │       ↓
    │   │   Waypoint 2 (3167, 3472): ✓ Reached
    │   │       ↓
    │   │   Waypoint 3 (3185, 3436): ✓ Reached
    │   │       ↓
    │   │   Waypoint 4 (3185, 3448): ✓ Reached
    │   │
    │   └─> All waypoints completed
    │
    └─> Returns: True
```

---

## 6. Extension Points

### 6.1 Creating New Bots

**Option 1: State Machine Bot** (Recommended for complex workflows)

```python
from osrsbot.core.state_machine_bot import StateMachineBot
from enum import Enum

class MyBotStates(Enum):
    IDLE = "idle"
    GATHERING = "gathering"
    BANKING = "banking"

class MyBot(StateMachineBot):
    def define_states(self):
        return {
            MyBotStates.IDLE: StateMetadata(name="Idle"),
            MyBotStates.GATHERING: StateMetadata(
                name="Gathering",
                max_retries=3,
                timeout=300.0,
                failover_state=MyBotStates.IDLE
            ),
            MyBotStates.BANKING: StateMetadata(name="Banking"),
        }

    def define_transitions(self):
        return {
            MyBotStates.IDLE: MyBotStates.GATHERING,
            MyBotStates.GATHERING: MyBotStates.BANKING,
            MyBotStates.BANKING: MyBotStates.GATHERING,
        }

    def define_initial_state(self):
        return MyBotStates.IDLE

    def handle_state(self, state, context):
        if state == MyBotStates.GATHERING:
            return self._handle_gathering(context)
        # ... handle other states
```

**Option 2: Simple Bot** (For basic scripts)

```python
from osrsbot.core.base_bot import Bot

class MySimpleBot(Bot):
    def run_cycle(self, bank_location: str, run_number: int):
        # Simple sequential logic
        self.actions.click_color("resource")
        self.actions.wait("short")

        while not self.inventory.is_full():
            self.actions.click_color("resource")
            self.actions.wait("medium")

        self.actions.click_color("bank")
        # ... banking logic
```

### 6.2 Adding New Services

```python
from osrsbot.core.game_interface import GameInterface
from osrsbot.models.config import Config

class MyNewService:
    def __init__(self, interface: GameInterface, config: Config):
        self.interface = interface
        self.config = config

    def my_operation(self):
        # Service logic
        pass

# Register in ScriptRunner
runner = ScriptRunner()
runner.my_service = MyNewService(runner.interface, runner.config)
```

### 6.3 Adding New Commands/Queries

**New Command**:
```python
# In GameActions class
def my_new_action(self, param: str) -> None:
    """New game action"""
    # Use services to perform action
    self.mouse.move_to(x, y)
    self.mouse.click(x, y)
```

**New Query**:
```python
# In GameState class
def get_my_stat(self) -> Optional[int]:
    """Read a new game stat"""
    region = self.config.get("coordinates", "my_stat")
    screenshot = self.screen.capture_region(region)
    return self.ocr.read_digits(screenshot)
```

### 6.4 Adding Configuration

**In config.json**:
```json
{
  "my_feature": {
    "enabled": true,
    "threshold": 42,
    "color": "#ff0000"
  }
}
```

**In Code**:
```python
enabled = self.config.get("my_feature", "enabled", default=False)
threshold = self.config.get("my_feature", "threshold", default=50)
```

---

## 7. Architectural Decisions

### 7.1 Why CQRS?

**Decision**: Separate commands (GameActions) from queries (GameState)

**Rationale**:
- Clearer responsibilities (read vs write)
- Easier testing (mock queries, verify commands)
- Better performance (optimize reads separately)
- Follows CQRS pattern from DDD

### 7.2 Why State Machines?

**Decision**: Use state machine pattern for complex bots

**Rationale**:
- Explicit state modeling
- Built-in retry and error handling
- Easier debugging (state history)
- Better than procedural code for complex workflows

### 7.3 Why Dependency Injection?

**Decision**: Inject services into components

**Rationale**:
- Testability (mock dependencies)
- Flexibility (swap implementations)
- Clear dependencies (explicit in constructor)
- Follows SOLID principles

### 7.4 Why Service Layer?

**Decision**: Separate services layer from business logic

**Rationale**:
- Reusability (services used by multiple bots)
- Single responsibility
- Easier to test in isolation
- Clear abstraction levels

### 7.5 Why GameInterface is a Service?

**Decision**: GameInterface belongs conceptually to Services layer (despite physical location in core/)

**Rationale**:
- **Infrastructure, not business logic**: Manages OS-level window operations
- **Foundational dependency**: Other services (Mouse, Screen) depend on it
- **No workflow decisions**: Pure coordinate translation and window management
- **Reusable primitive**: Not specific to any bot or business logic

**Physical vs Conceptual Organization**:
- Physical location: `src/osrsbot/core/game_interface.py`
- Conceptual layer: Services layer
- This is acceptable - file location doesn't always match layer perfectly
- What matters: Dependencies flow correctly (Services → Models, Core → Services)

---

## Conclusion

The OSRS Bot architecture demonstrates strong software engineering principles with clear layering, separation of concerns, and modern design patterns. The architecture supports:

- ✓ **Extensibility**: Easy to add new bots, services, and features
- ✓ **Testability**: Dependency injection enables mocking
- ✓ **Maintainability**: Clear responsibilities and organization
- ✓ **Reusability**: Service layer provides reusable components
- ✓ **Advanced Features**: World coordinate navigation and hardware mouse control

**Key Strengths**:
- CQRS pattern for clear read/write separation
- State machine framework for complex workflows
- Service architecture for modularity
- Dependency injection for flexibility
- Advanced pathfinding with 2D rotation matrix mathematics
- Hardware integration capability (Arduino mouse)
- Real-time position tracking via external plugin integration

**Recent Additions (December 2025)**:
- **StatusSocketService**: Real-time player position and camera data from RuneLite
- **WalkerService**: Advanced pathfinding with camera rotation compensation using 2D rotation matrices
- **ArduinoMouseService**: Optional hardware mouse control for enhanced anti-detection
- Comprehensive test suite covering all 10+ services
- Detailed technical documentation (WALKER_TECHNICAL_DOCS.md, SERVICE_GUIDE.md)

**Areas for Future Enhancement**:
- Add Protocol/ABC definitions for service interfaces
- Extract retry logic to decorator
- Implement circuit breaker pattern for resilience
- A* pathfinding for obstacle avoidance
- Neural network for anti-ban behavior modeling

---

**Document Version**: 2.0
**Last Updated**: December 22, 2025
