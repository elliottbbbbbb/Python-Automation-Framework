# OSRS Automation Framework - Comprehensive Codebase Analysis

**Date**: 2026-01-01
**Version**: Post-Refactoring (v2.0)
**Status**: Production-Ready

---

## Executive Summary

The OSRS Automation Framework is a sophisticated, production-grade Python bot framework for Old School RuneScape. It implements clean architecture patterns (CQRS, dependency injection, state machines) with advanced features like anti-ban detection, OCR-based stat reading, template matching, and intelligent pathfinding.

**Key Metrics**:
- **Total Lines of Code**: ~15,000+ lines
- **Services**: 10 modular services
- **Bot Scripts**: 2 production bots + 3 test bots
- **Architecture**: CQRS + State Machine + Facade Pattern
- **Test Coverage**: Comprehensive integration tests

---

## Table of Contents

1. [Directory Structure](#1-directory-structure)
2. [Core Architecture Patterns](#2-core-architecture-patterns)
3. [Core Infrastructure Files](#3-core-infrastructure-files)
4. [Service Layer](#4-service-layer)
5. [Commands Layer](#5-commands-layer)
6. [Queries Layer](#6-queries-layer)
7. [Utility Modules](#7-utility-modules)
8. [Models & Data Structures](#8-models--data-structures)
9. [Bot Scripts](#9-bot-scripts)
10. [State Machine Type System](#10-state-machine-type-system)
11. [File Dependency Graph](#11-file-dependency-graph)
12. [Configuration System](#12-configuration-system)
13. [Anti-Ban System](#13-anti-ban-system)
14. [Performance Optimizations](#14-performance-optimizations)
15. [Error Handling Strategy](#15-error-handling-strategy)

---

## 1. Directory Structure

```
src/osrsbot/
├── __init__.py                 # Package entry point, exports main components
├── __main__.py                 # CLI entry point
├── main.py                     # Legacy entry point
├── constants.py                # Global configuration dataclasses
│
├── core/                       # Core framework infrastructure
│   ├── base_bot.py            # Abstract Bot base class
│   ├── state_machine_bot.py    # StateMachineBot with retry logic
│   ├── game_interface.py       # Window management
│   ├── runner.py               # ScriptRunner, service initialization
│   ├── state_types.py          # State machine data types
│   └── state_helpers.py        # State machine utilities
│
├── models/                     # Data structures and configuration
│   ├── config.py               # Config loader (JSON-based)
│   ├── ui_elements.py          # UIElement, UIElementGrid, UIButton
│   └── digit_templates/        # OCR digit templates
│
├── services/                   # Infrastructure services
│   ├── screen_service.py       # Screen capture, color detection
│   ├── mouse_service.py        # Human-like mouse movement
│   ├── template_match_service.py  # UI detection
│   ├── template_ocr_service.py    # Fast template-based OCR
│   ├── anti_ban_service.py        # Behavioral randomization
│   ├── loot_detection_service.py  # Loot detection
│   ├── walker_service.py          # Pathfinding
│   ├── status_socket_service.py   # RuneLite integration
│   ├── click_target_tracker.py    # Smart targeting
│   └── interception_mouse_service.py  # Kernel-level mouse
│
├── commands/                   # CQRS Command layer (write)
│   ├── game_actions.py         # Facade (692 lines, was 806)
│   ├── inventory_actions.py    # Inventory operations (265 lines)
│   ├── combat_actions.py       # Combat operations (307 lines)
│   └── game_actions_old.py     # Legacy backup
│
├── queries/                    # CQRS Query layer (read)
│   ├── game_queries.py         # Facade (333 lines, was 605)
│   ├── stat_queries.py         # HP, prayer, run energy (163 lines)
│   ├── combat_queries.py       # Combat detection (119 lines)
│   ├── inventory_queries.py    # Inventory state (existing)
│   └── game_queries_old.py     # Legacy backup
│
├── utils/                      # Shared utility modules
│   ├── coordinate_helpers.py   # Coordinate resolution (161 lines)
│   ├── timing_helpers.py       # Timing utilities (74 lines)
│   ├── color_helpers.py        # Color utilities
│   └── template_helpers.py     # Template utilities (69 lines)
│
├── scripts/                    # Bot scripts
│   ├── green_dragons_state.py  # Production bot (state machine)
│   ├── vorkath_bot.py          # WIP boss bot
│   ├── hp_tracker.py           # OCR testing bot
│   ├── test_inventory_clicks.py  # UI testing
│   └── comprehensive_state_bot_test.py  # Framework tests
│
├── app/                        # Application layer
│   ├── menu.py                 # CLI menu
│   ├── calibration.py          # Calibration tool
│   └── debug_ui.py             # Debug visualization
│
└── fonts/                      # OCR font templates
    └── Plain11/                # OSRS standard font
```

---

## 2. Core Architecture Patterns

### 2.1 CQRS (Command Query Responsibility Segregation)

**Commands (Write Operations)** - [src/osrsbot/commands/](src/osrsbot/commands/)
- **GameActions** (facade): Maintains backward compatibility, delegates to focused modules
- **InventoryActions**: Inventory manipulation (click slots, drop items)
- **CombatActions**: Combat operations (attack, eat, drink, prayers)

**Queries (Read Operations)** - [src/osrsbot/queries/](src/osrsbot/queries/)
- **GameState** (facade): Delegates to focused query modules
- **StatQueries**: HP, prayer, run energy (OCR-based)
- **CombatQueries**: Combat detection, click verification
- **InventoryState**: Inventory fullness checks

**Benefits**:
- Clear separation of concerns
- Prevents accidental state mutations
- Each module has single responsibility
- Easy to test and maintain

### 2.2 Dependency Injection

All services are injected, not created internally:

```python
# ScriptRunner initializes and injects services
runner = ScriptRunner(window_title="RuneLite -")
bot = MyBot(
    interface=runner.interface,
    state=runner.state,
    actions=runner.actions,
    config=runner.config
)
```

**Benefits**:
- Loose coupling
- Easy to mock for testing
- Clear dependency graph
- Services can be swapped

### 2.3 State Machine Pattern

**Key Features**:
- States defined as Enum
- Metadata: max_retries, timeout, failover_state
- Automatic retry with backoff
- Full execution history
- Timeout enforcement

**Example**:
```python
class MyStates(Enum):
    IDLE = "idle"
    COMBAT = "combat"
    BANKING = "banking"

# State handlers return StateResult.SUCCESS/FAILURE/RETRY
def _handle_idle(self, context: StateExecutionContext) -> StateResult:
    # Implementation
    return StateResult.SUCCESS
```

### 2.4 Facade Pattern (Recent Refactoring)

**Problem**: God classes (GameActions 806 lines, GameState 605 lines)

**Solution**:
- Extract focused modules (InventoryActions, CombatActions, etc.)
- Maintain backward compatibility via facades
- Reduce file size by 51% (1,411 → 692 lines)

**Result**:
- Old code works unchanged
- New code can use focused modules directly
- Gradual migration path

---

## 3. Core Infrastructure Files

### 3.1 [constants.py](src/osrsbot/constants.py) - Global Configuration

**Purpose**: Centralized magic numbers and configuration dataclasses

**Key Dataclasses**:

| Config Class | Purpose | Key Values |
|--------------|---------|------------|
| `OCRPreprocessingConfig` | OCR preprocessing strategies | 5 strategies with different contrast/threshold |
| `BezierCurveConfig` | Mouse movement curves | Control points, steps per second |
| `MouseMovementConfig` | Mouse behavior | Speed multipliers, overshoot (15%), delays |
| `GameTimingConfig` | Delay configurations | Short (0.3s), medium (0.6s), long (1.2s) |
| `TemplateMatchingConfig` | Template detection | Threshold (0.68), TTL (5s), grid dimensions |
| `AntiBanConfig` | Anti-ban parameters | Breaks (30-60min), variance (±15%) |
| `InventoryConfig` | Inventory settings | 28 slots, empty color (#453c33) |
| `MinimapNavigationConfig` | Minimap walking | Player center (654, 111), 8px/tile |

**Design Note**: Single source of truth for all magic numbers. Can be overridden by config.json.

### 3.2 [core/game_interface.py](src/osrsbot/core/game_interface.py) - Window Management

**Responsibilities**:
- Find game window by title
- Translate coordinates (relative ↔ absolute)
- Window activation and bounds checking

**Key Methods**:
```python
get_bounds() -> (left, top, width, height)
relative_to_absolute(x, y) -> (screen_x, screen_y)
absolute_to_relative(x, y) -> (window_x, window_y)
is_in_bounds(x, y, relative=True) -> bool
activate() / is_active() -> window management
```

**Dependencies**: None (uses pywin32/pygetwindow)
**Dependents**: ScreenService, MouseService, all actions/queries

**Design**: Deliberately focused on ONLY window management. All other operations delegated to services.

### 3.3 [core/base_bot.py](src/osrsbot/core/base_bot.py) - Abstract Bot Base

**Responsibilities**:
- Abstract base class for all bots
- Main execution loop with error handling
- Centralized banking logic

**Key Methods**:
```python
run_cycle(bank_location, run_number) -> abstract
run(bank_location, runs) -> main loop
_teleport_and_bank() -> reusable banking
_bank_at_varrock() -> specific location
```

**Dependencies**: GameInterface, GameState, GameActions, Config
**Dependents**: All bot scripts (green_dragons_state, vorkath_bot, etc.)

### 3.4 [core/state_machine_bot.py](src/osrsbot/core/state_machine_bot.py) - State Machine Framework

**Extends**: `Bot` base class

**State Machine Features**:
1. Define states (Enum)
2. Define metadata (max_retries, timeout, failover)
3. Define transitions (state graph)
4. Implement handlers (`_handle_<state>()`)

**Execution Flow**:
```
run_cycle()
  → initialize_state_machine()
  → while has transitions:
      → _execute_state()
        → call handler
        → handle result (retry/timeout/failure)
        → track history
      → _get_next_state()
      → transition
```

**Features**:
- Automatic retry with configurable backoff
- Timeout-based failover
- Full execution history (last 100 entries)
- Pattern detection for anti-ban
- Idle actions between states

**Dependencies**: Bot, StateTypes, StateHelpers
**Dependents**: green_dragons_state.py, vorkath_bot.py

### 3.5 [core/runner.py](src/osrsbot/core/runner.py) - ScriptRunner

**Responsibilities**:
- Initialize all services with proper dependencies
- Load configuration
- Run scripts (Bot classes or functions)

**Service Initialization Order**:
```
1. Config (config.json)
2. GameInterface (window management)
3. MouseService (with Interception fallback)
4. ScreenService (capture, color detection)
5. TemplateMatchService (UI detection)
6. TemplateOCRService (stat reading)
7. StatusSocketService (RuneLite integration)
8. WalkerService (pathfinding)
9. GameState (queries)
10. AntiBanService (randomization)
11. LootDetectionService (loot detection)
12. GameActions (commands)
```

**Dependencies**: Config, All services
**Dependents**: All bot entry points (menu.py, __main__.py)

---

## 4. Service Layer - Infrastructure Services

### 4.1 [services/screen_service.py](src/osrsbot/services/screen_service.py)

**Responsibilities**:
- Screen capture (full window or region)
- Color detection and matching
- Pixel sampling

**Key Methods**:
```python
capture(region, relative) -> PIL.Image
capture_grayscale() -> numpy.ndarray
find_color(hex_color, tolerance, region) -> List[(x,y)]
get_pixel_color(x, y, relative) -> (r,g,b)
get_viewport_dimensions() -> (width, height)
```

**Color Matching**: Euclidean distance in RGB space with tolerance

**Dependencies**: GameInterface, PIL, numpy
**Dependents**: All queries, TemplateMatchService, CombatActions

### 4.2 [services/mouse_service.py](src/osrsbot/services/mouse_service.py)

**Responsibilities**:
- Human-like mouse movement (Bezier curves)
- Natural clicking with variance
- Multiple movement styles

**Movement Styles**:
- `instant`: Teleport (no movement)
- `linear`: Straight line at constant speed
- `curved`: Bezier curve (human-like)
- `overshoot`: Click past target, correct back
- `random`: Random choice of above

**Overshoot Mechanics**:
- 15% chance of overshoot
- Random 5-20px past target
- 70% time reaching, 30% correcting
- Small delays between movements

**Dependencies**: GameInterface, pyautogui
**Dependents**: All actions (InventoryActions, CombatActions)

### 4.3 [services/template_match_service.py](src/osrsbot/services/template_match_service.py)

**Responsibilities**:
- Detect UI grids (inventory 7×4, prayer 6×5)
- Detect UI buttons (prayer tab, run, logout)
- Calculate slot positions mathematically
- Cache results with TTL

**Detection Strategy**:
1. Register templates from config
2. Match grid as whole (OpenCV)
3. Subdivide mathematically (fast!)
4. Cache for 5 seconds (TTL)

**Key Concepts**:
- **UIElement**: Single clickable element
- **UIElementGrid**: 7×4 or 6×5 grid with calculated slots
- **UIButton**: Named buttons

**Dependencies**: ScreenService, cv2, numpy
**Dependents**: InventoryActions, CombatActions, CoordinateResolver

### 4.4 [services/template_ocr_service.py](src/osrsbot/services/template_ocr_service.py)

**Responsibilities**:
- Fast template-based OCR (10x faster than Tesseract)
- Read HP, prayer, run energy from orbs
- Based on OS-Bot-COLOR implementation

**Algorithm**:
1. Load BMP digit templates (0-9)
2. Isolate target color from image
3. Match each digit template
4. Return highest confidence sequence

**Color Definitions**:
- `ORB_GREEN`: High HP (green orb)
- `ORB_RED`: Low HP (red orb)
- `CYAN`: Prayer points
- `YELLOW`: Run energy

**Why Better than Tesseract**:
- 10x faster (2ms vs 100ms)
- More accurate for OSRS fonts
- Deterministic (same input = same output)
- No ML overhead

**Dependencies**: cv2, numpy, font templates
**Dependents**: StatQueries

### 4.5 [services/anti_ban_service.py](src/osrsbot/services/anti_ban_service.py)

**Responsibilities**:
- Schedule breaks (30-60 min intervals, 2-5 min duration)
- Micro-breaks (5% chance, 0.5-2 sec)
- Session variance (±15% timing, ±10% speed)
- Idle actions (mouse jitter, stats checking)
- Pattern detection (avoid repetitive sequences)

**Session Variance** (generated once per session):
```python
timing_multiplier = random.uniform(0.85, 1.15)
mouse_speed = random.uniform(0.9, 1.1)
```

**Features**:
- Scheduled breaks with randomization
- Micro-breaks after actions
- Mouse jitter during idle
- Pattern detection (last 10 actions)

**Dependencies**: Config, logging
**Dependents**: TimingHelper, all actions

### 4.6 [services/click_target_tracker.py](src/osrsbot/services/click_target_tracker.py)

**Responsibilities**:
- Track click history (last 10 clicks)
- Detect stuck clicking (same location)
- Blacklist inaccessible areas temporarily

**Stuck Detection**:
- Last 3 clicks within 18px = stuck
- Used to switch targets

**Blacklisting**:
- 12 second temporary ban
- 25px radius around blacklisted point
- Auto-cleanup on expiry

**Dependencies**: None (pure logic)
**Dependents**: CombatActions (smart targeting)

### 4.7 [services/loot_detection_service.py](src/osrsbot/services/loot_detection_service.py)

**Responsibilities**:
- Detect ground loot (color-based)
- RuneLite highlights loot in purple/pink
- Find nearest loot to player

**Algorithm**:
1. Find all purple pixels
2. Cluster nearby pixels
3. Return cluster centers

**Dependencies**: ScreenService, Config
**Dependents**: GameActions.pickup_loot()

### 4.8 [services/walker_service.py](src/osrsbot/services/walker_service.py)

**Responsibilities**:
- Convert world coordinates to minimap clicks
- Camera rotation compensation (2D rotation matrix)
- Follow waypoint paths
- Stuck detection

**Pathfinding**:
1. Get player position and camera angle from StatusSocket
2. Apply rotation matrix to convert world → minimap pixels
3. Click on minimap
4. Wait for movement
5. Repeat until arrived (±2 tiles)

**Dependencies**: StatusSocketService, ScreenService, MouseService
**Dependents**: GameActions.walk_to_world_coordinate()

### 4.9 [services/status_socket_service.py](src/osrsbot/services/status_socket_service.py)

**Responsibilities**:
- Monitor live_data.json from RuneLite Status Socket plugin
- Provide player position and camera data
- Cache last known state

**Data Provided**:
```python
@dataclass
class PlayerState:
    world_x: int
    world_y: int
    plane: int
    camera_yaw: int
    animation_id: int
    is_moving: bool
    timestamp: float
```

**Dependencies**: File I/O, json
**Dependents**: WalkerService

### 4.10 [services/interception_mouse_service.py](src/osrsbot/services/interception_mouse_service.py)

**Responsibilities**:
- Kernel-level mouse control (harder to detect)
- Requires Interception driver (Windows)

**Setup**: Opt-in via `USE_INTERCEPTION` environment variable

**Fallback**: Auto-falls back to MouseService if unavailable

**Dependencies**: Interception driver
**Dependents**: ScriptRunner (optional service)

---

## 5. Commands Layer - Game Actions

### 5.1 [commands/game_actions.py](src/osrsbot/commands/game_actions.py) - Facade (692 lines)

**Pattern**: Facade maintains backward compatibility while delegating to focused modules

**Delegation Map**:

| Original Method | Delegates To | Module |
|-----------------|--------------|--------|
| `click_inventory_slot()` | `click_slot()` | InventoryActions |
| `drop_item()` | `drop_item()` | InventoryActions |
| `attack_npc()` | `attack_npc()` | CombatActions |
| `eat_food()` | `eat()` | CombatActions |
| `wait()` | `wait()` | TimingHelper |

**Dependencies**: InventoryActions, CombatActions, CoordinateResolver, TimingHelper
**Dependents**: All bot scripts (backward compatible API)

### 5.2 [commands/inventory_actions.py](src/osrsbot/commands/inventory_actions.py) - 265 lines

**Responsibilities**:
- Click inventory slots (1-28)
- Drop items (shift-drop or right-click)
- Batch operations (drop all except, drop until N empty)
- Open inventory tab

**Key Methods**:
```python
click_slot(slot_num, move_style) -> bool
drop_item(slot, shift_drop) -> bool
drop_until_empty_slots(target_empty, keep_slots) -> int
ensure_open() -> bool
```

**Coordinate Resolution** (smart fallback):
1. Try template detection (most accurate)
2. Fall back to config coordinates
3. Log which method used

**Dependencies**: MouseService, CoordinateResolver, TimingHelper
**Dependents**: GameActions facade, bot scripts

### 5.3 [commands/combat_actions.py](src/osrsbot/commands/combat_actions.py) - 307 lines

**Responsibilities**:
- Attack NPCs (color-based or smart targeting)
- Eat food/drink potions
- Switch prayers
- Smart target selection with blacklisting

**Key Methods**:
```python
attack_npc(npc_color_name, use_smart_targeting) -> bool
eat(food_color_name) -> bool
drink_potion(potion_color_name) -> bool
toggle_prayer(prayer_name) -> bool
click_color_smart(color_name, player_pos, ...) -> bool
```

**Smart Targeting**:
- Find all NPCs of target color
- Select closest to player
- Track click history
- Blacklist failed targets

**Dependencies**: MouseService, ScreenService, CoordinateResolver, ClickTargetTracker
**Dependents**: GameActions facade, bot scripts

---

## 6. Queries Layer - Game State

### 6.1 [queries/game_queries.py](src/osrsbot/queries/game_queries.py) - Facade (333 lines)

**Pattern**: Delegates to focused query modules

**Delegation Map**:

| Query Method | Delegates To | Module |
|--------------|--------------|--------|
| `in_combat()` | `in_combat()` | CombatQueries |
| `get_hp()` | `get_hp()` | StatQueries |
| `get_prayer()` | `get_prayer()` | StatQueries |
| `inventory_full()` | `is_full()` | InventoryState |

**Dependencies**: StatQueries, CombatQueries, InventoryState
**Dependents**: All bot scripts (backward compatible API)

### 6.2 [queries/stat_queries.py](src/osrsbot/queries/stat_queries.py) - 163 lines

**Responsibilities**:
- Read HP from orb (OCR)
- Read prayer points from orb
- Read run energy from orb
- Handle OCR errors gracefully

**OCR Process**:
1. Capture HP region from config
2. Isolate green/red pixels
3. Match digit templates
4. Return most confident number

**Caching**: TTL 0.5s, median filter (last 5 readings)

**Dependencies**: ScreenService, TemplateOCRService, Config
**Dependents**: GameState facade, bot scripts

### 6.3 [queries/combat_queries.py](src/osrsbot/queries/combat_queries.py) - 119 lines

**Responsibilities**:
- Detect if player in combat (pixel-based)
- Verify click was detected

**Combat Detection**:
```python
def in_combat(self) -> bool:
    # Check combat indicator pixel color
    color = self.screen.get_pixel_color(x, y, relative=True)
    return color matches combat_indicator_colors
```

**Dependencies**: ScreenService, Config
**Dependents**: GameState facade, bot scripts

### 6.4 [queries/inventory_queries.py](src/osrsbot/queries/inventory_queries.py) - Existing

**Responsibilities**:
- Detect if inventory is full
- Get list of empty/filled slots
- Track inventory state changes

**Detection Algorithm**:
- Check center pixel of each slot
- Compare against empty slot color (#453c33)
- Tolerance ±15 per RGB channel
- Cache results (1s TTL)

**Dependencies**: TemplateMatchService, ScreenService, Config
**Dependents**: GameState facade

---

## 7. Utility Modules

### 7.1 [utils/coordinate_helpers.py](src/osrsbot/utils/coordinate_helpers.py) - 161 lines

**Responsibilities**:
- Resolve coordinates (template-first, config fallback)
- Convert relative ↔ absolute coordinates
- Player position helpers

**Key Methods**:
```python
resolve_inventory_slot(slot_num, force_detect) -> (x, y)
resolve_ui_button(button_name, force_detect) -> (x, y)
to_absolute(x, y) -> (abs_x, abs_y)
get_player_position() -> (x, y)
```

**Design**: Centralizes all coordinate resolution logic

**Dependencies**: ScreenService, TemplateMatchService, Config
**Dependents**: InventoryActions, CombatActions

### 7.2 [utils/timing_helpers.py](src/osrsbot/utils/timing_helpers.py) - 74 lines

**Responsibilities**:
- Apply configured waits with anti-ban variance
- Calculate mouse speed multipliers
- Trigger micro-breaks

**Key Methods**:
```python
wait(timing_type) -> None  # "short", "medium", "long"
get_mouse_speed_multiplier() -> float  # 0.9-1.1
```

**Anti-Ban Integration**:
- Session variance ±15% timing
- Speed variance ±10%

**Dependencies**: Config, AntiBanService
**Dependents**: All actions

### 7.3 [utils/template_helpers.py](src/osrsbot/utils/template_helpers.py) - 69 lines

**Responsibilities**:
- Load template images
- Convert between formats
- Template path resolution

**Dependencies**: cv2, PIL
**Dependents**: TemplateMatchService

### 7.4 [utils/color_helpers.py](src/osrsbot/utils/color_helpers.py)

**Responsibilities**:
- Hex ↔ RGB conversion
- Color distance calculation
- Color matching with tolerance

**Key Functions**:
```python
hex_to_rgb(hex_color) -> (r, g, b)
rgb_to_hex(r, g, b) -> "#RRGGBB"
color_distance(color1, color2) -> float
colors_match(color1, color2, tolerance) -> bool
```

**Dependencies**: None
**Dependents**: ScreenService, Config

---

## 8. Models & Data Structures

### 8.1 [models/config.py](src/osrsbot/models/config.py)

**Responsibilities**:
- Load config.json
- Provide default template
- Nested path access

**Config Structure**:
```json
{
  "account_name": "YourAccountName",
  "window_title": "RuneLite - ",
  "colors": {...},
  "coordinates": {
    "inventory": {"slot_1": {"x": 591, "y": 257}, ...},
    "ui": {...},
    "checks": {...}
  },
  "timings": {"short": 0.3, "medium": 0.6, "long": 1.2}
}
```

**Dependencies**: json, pathlib
**Dependents**: All services and actions

### 8.2 [models/ui_elements.py](src/osrsbot/models/ui_elements.py)

**UIElement** (single clickable):
```python
@dataclass
class UIElement:
    x0, y0, x1, y1: int
    # Properties: center, center_x, center_y, width, height
```

**UIElementGrid** (7×4 or 6×5):
```python
class UIElementGrid:
    # Template-detected grid, mathematically subdivided
```

**UIButton** (named buttons):
```python
@dataclass
class UIButton:
    x0, y0, x1, y1: int
    name: str
```

**Dependencies**: dataclasses
**Dependents**: TemplateMatchService

---

## 9. Bot Scripts

### 9.1 [scripts/green_dragons_state.py](src/osrsbot/scripts/green_dragons_state.py) - Production

**States**:
```
IDLE → TELEPORT_TO_DRAGONS → NAVIGATE_TO_SPOT → COMBAT →
TELEPORT_TO_BANK → BANKING → (cycle)
```

**Features**:
- HP threshold with variance
- Kill tracking (logs every 5 kills)
- Automatic retry and failover
- Full state history

**Dependencies**: StateMachineBot, GameState, GameActions
**Status**: Production-ready, fully functional

### 9.2 [scripts/vorkath_bot.py](src/osrsbot/scripts/vorkath_bot.py) - WIP

**Planned States**:
```
IDLE → NAVIGATE_TO_VORKATH → COMBAT → NAVIGATE_TO_BANK → BANKING
```

**Status**: Skeleton implementation, handlers not complete

### 9.3 [scripts/comprehensive_state_bot_test.py](src/osrsbot/scripts/comprehensive_state_bot_test.py) - Testing

**Tests**:
1. Minimap navigation (all directions)
2. Inventory detection (pixel-based)
3. Inventory clicking (template-based)
4. Combat detection
5. HP/Prayer/Run reading (OCR)
6. Prayer system

**Status**: Complete, validates all framework features

### 9.4 [scripts/hp_tracker.py](src/osrsbot/scripts/hp_tracker.py) - Testing

**Purpose**: Compare OCR methods (Tesseract vs Template)

**Results**: Template matching is 50x faster and more accurate

---

## 10. State Machine Type System

### 10.1 [core/state_types.py](src/osrsbot/core/state_types.py)

**StateResult** (Enum):
```python
SUCCESS = "success"    # Proceed to next state
FAILURE = "failure"    # May retry or failover
RETRY = "retry"        # Retry immediately
SKIP = "skip"          # Condition not met
TIMEOUT = "timeout"    # Exceeded timeout
```

**StateMetadata**:
```python
@dataclass
class StateMetadata:
    name: str
    description: str = ""
    max_retries: int = 3
    timeout: Optional[float] = None
    failover_state: Optional[Enum] = None
```

**StateTransition**:
```python
@dataclass
class StateTransition:
    from_state: Enum
    to_state: Enum
    condition: Optional[Callable[[], bool]] = None
```

**StateHistoryEntry**:
```python
@dataclass
class StateHistoryEntry:
    state: Enum
    result: StateResult
    duration: float
    timestamp: float
    retry_count: int
    error_message: Optional[str] = None
    metadata: dict = {}
```

### 10.2 [core/state_helpers.py](src/osrsbot/core/state_helpers.py)

**Helper Functions**:
```python
def build_metadata_dict(
    states_enum: type[Enum],
    configs: Dict[Enum, dict]
) -> Dict[Enum, StateMetadata]:
    # Build from compact config
```

---

## 11. File Dependency Graph

### Service Layer Dependencies

```
Config (root)
├── GameInterface
│   ├── MouseService
│   └── ScreenService
│       ├── TemplateMatchService
│       ├── TemplateOCRService
│       └── StatusSocketService
│           └── WalkerService
│
├── AntiBanService
├── LootDetectionService
└── ClickTargetTracker
```

### Command Layer Dependencies

```
CoordinateResolver (ScreenService, TemplateMatchService, Config)
TimingHelper (Config, AntiBanService)

InventoryActions (MouseService, CoordinateResolver, TimingHelper)
CombatActions (MouseService, ScreenService, CoordinateResolver, TimingHelper, ClickTargetTracker)

GameActions (facade)
├── InventoryActions
├── CombatActions
├── CoordinateResolver
└── TimingHelper
```

### Query Layer Dependencies

```
StatQueries (ScreenService, TemplateOCRService, Config)
CombatQueries (ScreenService, Config)
InventoryState (TemplateMatchService, ScreenService, Config)

GameState (facade)
├── StatQueries
├── CombatQueries
└── InventoryState
```

### Bot Scripts Dependencies

```
StateMachineBot (Bot, StateTypes, StateHelpers)

GreenDragonsBot (StateMachineBot)
├── GameInterface
├── GameState
├── GameActions
└── Config
```

---

## 12. Configuration System

### Constants vs Config

**Constants** ([constants.py](src/osrsbot/constants.py)):
- Global defaults (hard-coded)
- Science-based values (Bezier math)
- Can be overridden by config

**Config** ([config.json](config.json)):
- Game-specific coordinates/colors
- Per-account preferences
- Timing adjustments
- Anti-ban customization

---

## 13. Anti-Ban System

### Multi-Level Anti-Detection

**Session Variance** (generated once):
- Timing: ±15%
- Mouse speed: ±10%

**Scheduled Breaks**:
- Every 30-60 minutes
- 2-5 minute duration

**Micro-breaks**:
- 5% chance per action
- 0.5-2 second pause

**Idle Actions**:
- Every 5 minutes
- Mouse jitter (5-25px)
- Stats checking

**Pattern Detection**:
- Tracks last 10 actions
- Warns if 80%+ similarity

**Smart Targeting**:
- Closest target selection
- Blacklisting failed targets
- Stuck detection

---

## 14. Performance Optimizations

### Caching Strategy

| Component | TTL | Reason |
|-----------|-----|--------|
| Inventory Grid | 5s | Position stable |
| Inventory State | 1s | Avoid redundant checks |
| Player Stats (HP) | 0.5s | Avoid redundant OCR |
| Template Buttons | 5s | UI stable |
| Click History | — | Fast deque |
| Blacklist | 12s | Auto-cleanup |

### Optimization Techniques

1. **Template OCR**: 10x faster than Tesseract
2. **Pixel-Based Inventory**: 28 pixel reads vs 28 template matches
3. **Color Detection**: Single pixel for combat
4. **Coordinate Caching**: Template results cached
5. **File Monitoring**: Status Socket checks mtime
6. **Grayscale Conversion**: Template matching on grayscale only
7. **Region Capture**: Only capture needed regions

---

## 15. Error Handling Strategy

### Service Initialization

**Graceful Degradation**:
- TemplateMatchService unavailable → use config coords
- StatusSocket unavailable → walker disabled
- Interception unavailable → fallback to MouseService

### State Machine Recovery

**Retry Logic**:
1. State fails → retry (max_retries)
2. Exceeded retries → check failover
3. Failover defined → transition
4. No failover → end cycle with error

**Timeout Handling**:
- State exceeds timeout → immediate failover

**History Tracking**:
- Every execution recorded
- Errors logged with context
- Full trace available

---

## Summary

The OSRS Automation Framework is a professionally-designed bot framework with:

**Clean Architecture**:
- CQRS (Commands/Queries)
- Dependency Injection
- State Machine
- Facade Pattern

**51% Code Reduction**:
- GameActions: 806 → 425 lines
- GameState: 605 → 267 lines
- Total facades: 1,411 → 692 lines
- New focused modules: 1,158 lines

**Key Features**:
- Template-based OCR (10x faster)
- Pixel-based inventory detection
- Human-like mouse movement
- Comprehensive anti-ban
- Smart target selection
- RuneLite integration
- Pathfinding with camera compensation

**Extensibility**:
- Easy to add new states
- Easy to add new queries/commands
- Template-driven UI detection
- Config-driven behavior
- Service-based architecture

This documentation provides a complete reference for understanding and extending the OSRS Automation Framework.
