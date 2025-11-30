# OSRS Bot Architecture (MVC Pattern)

## Overview

OSRS Bot follows the Model-View-Controller (MVC) architectural pattern, adapted for bot automation:

- **Models** - Data and state management
- **Views** - User interface (CLI, calibration)
- **Controllers** - Business logic and orchestration
- **Services** - Infrastructure (mouse, screen, OCR, window)
- **Scripts** - Bot automation use cases

## Directory Structure

```
src/osrsbot/
├── models/                  # MODEL LAYER - Data & State
│   ├── config.py           # Configuration model
│   └── state.py            # GameState - current game state
│
├── views/                   # VIEW LAYER - User Interface
│   ├── menu.py             # CLI menu interface
│   └── calibration.py      # Calibration UI
│
├── controllers/             # CONTROLLER LAYER - Business Logic
│   ├── runner.py           # ScriptRunner - dependency injection
│   └── actions.py          # GameActions - game operations
│
├── services/                # SERVICE LAYER - Infrastructure
│   ├── mouse_service.py    # Mouse control
│   ├── screen_service.py   # Screen capture & vision
│   ├── ocr_service.py      # Text recognition
│   └── (others)
│
├── core/                    # CORE UTILITIES
│   └── game_interface.py   # Window management
│
├── scripts/                 # USE CASES - Bot Scripts
│   ├── green_dragons.py    # Combat script
│   ├── guns.py             # Pickpocketing script
│   └── test.py             # Test script
│
├── __init__.py             # Package exports
├── __main__.py             # Entry point (python -m osrsbot)
└── main.py                 # Alternative entry point
```

## MVC Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                           USER                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      VIEW (menu.py)                         │
│  • Display menu                                             │
│  • Get user input                                           │
│  • Show script output                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              CONTROLLER (ScriptRunner)                      │
│  • Initialize dependencies (DI container)                   │
│  • Load Config model                                        │
│  • Initialize GameState model                               │
│  • Initialize GameActions controller                        │
│  • Execute script with injected dependencies                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               SCRIPT (green_dragons.py)                     │
│  • Business logic for bot automation                        │
│  • Uses: Controllers (Actions) + Models (State)             │
└───────────┬─────────────────────────┬───────────────────────┘
            │                         │
            │ Commands                │ Queries
            ▼                         ▼
┌─────────────────────┐    ┌──────────────────────┐
│  CONTROLLER         │    │  MODEL               │
│  (GameActions)      │    │  (GameState)         │
│                     │    │                      │
│  • eat()            │    │  • get_hp()          │
│  • attack()         │    │  • in_combat()       │
│  • teleport()       │    │  • inventory_full()  │
└──────────┬──────────┘    └──────────┬───────────┘
           │                          │
           │ Uses                     │ Uses
           ▼                          ▼
┌──────────────────────────────────────────────────┐
│            SERVICES (Infrastructure)              │
│  • MouseService                                  │
│  • ScreenService                                 │
│  • OCRService                                    │
│  • GameInterface                                 │
└──────────────────────────────────────────────────┘
```

## Layer Responsibilities

### 1. Models Layer (Data & State)

**models/config.py - Configuration Model**
- Loads and saves config.json
- Provides getters for configuration values
- Manages default configuration
- Platform-specific settings (Tesseract paths)

**models/state.py - GameState Model**
- Read-only queries about game state
- HP tracking via OCR
- Combat status detection
- Inventory full detection
- Uses: OCRService, ScreenService, Config

### 2. Views Layer (User Interface)

**views/menu.py - CLI Menu**
- Main menu display
- User input prompts
- Script selection interface
- Progress/status output
- Entry point: `main()` function

**views/calibration.py - Calibration Tool**
- Interactive color/coordinate capture
- Visual feedback
- Configuration saving

### 3. Controllers Layer (Business Logic)

**controllers/runner.py - ScriptRunner**
- **Dependency Injection Container**
- Initializes all dependencies in correct order:
  1. Config (model)
  2. GameInterface (core)
  3. MouseService, ScreenService (services)
  4. GameState (model)
  5. GameActions (controller)
- Runs scripts with injected dependencies

**controllers/actions.py - GameActions**
- **Command layer** (changes game state)
- High-level game operations
- Combines multiple service calls
- Examples:
  - `eat(food)` - find color + click + wait
  - `attack(npc)` - find color + click
  - `teleport_ge()` - click slot + wait + teleport
  - `bank_deposit_all()` - click coordinate + wait

### 4. Services Layer (Infrastructure)

**services/mouse_service.py - MouseService**
- Low-level mouse control
- Human-like movement (Bézier curves)
- Click variance and delays
- Configurable movement styles

**services/screen_service.py - ScreenService**
- Screen capture
- Color matching and detection
- Pixel color reading
- Image analysis

**services/ocr_service.py - OCRService**
- Text recognition via Tesseract
- Number reading with validation
- Caching with TTL
- Smoothing and filtering

### 5. Core Layer (Window Management)

**core/game_interface.py - GameInterface**
- Window finding and tracking
- Coordinate translation (relative ↔ absolute)
- Window bounds management
- Pixel reading (legacy support)

## Command-Query Separation (CQRS)

Scripts use both queries and commands:

```python
# QUERIES (GameState) - Read game state
hp = state.get_hp()                    # Model query
in_combat = state.in_combat()          # Model query
full = state.inventory_full()          # Model query

# COMMANDS (GameActions) - Change game state
actions.eat("manta_ray")               # Controller command
actions.attack("green_dragon")         # Controller command
actions.teleport_ge()                  # Controller command
```

**Why this separation?**
- **GameState** is read-only, focused on detecting state
- **GameActions** performs operations that change state
- Clear responsibility: queries vs commands
- Follows CQRS pattern

## Script Structure

Scripts receive 4 dependencies via dependency injection:

```python
def green_dragons_script(
    interface,      # GameInterface (backward compat)
    state,          # GameState (queries)
    actions,        # GameActions (commands)
    config,         # Config (settings)
    **kwargs        # Script-specific parameters
) -> None:
    # Business logic using state (queries) and actions (commands)
    while not state.inventory_full():
        hp = state.get_hp()
        if hp < 70:
            actions.eat("manta_ray")

        if not state.in_combat():
            actions.attack("green_dragon")
```

## Dependency Flow

```
main.py / __main__.py
    ↓
views/menu.py (UI)
    ↓
controllers/runner.py (DI Container)
    ↓
    ├─→ models/config.py (Config)
    ├─→ models/state.py (GameState)
    ├─→ controllers/actions.py (GameActions)
    │
    └─→ Script (green_dragons.py)
            ├─→ state.get_hp() (Model query)
            └─→ actions.eat() (Controller command)
                    └─→ services/* (Infrastructure)
```

## Import Examples

### Clean Package-Level Imports

```python
# Recommended: Use package-level exports
from osrsbot.models import Config, GameState
from osrsbot.controllers import GameActions, ScriptRunner
from osrsbot.services import MouseService, ScreenService
from osrsbot.views import Calibrator
```

### Direct Imports

```python
# Alternative: Direct module imports
from osrsbot.models.config import Config
from osrsbot.models.state import GameState
from osrsbot.controllers.actions import GameActions
from osrsbot.controllers.runner import ScriptRunner
```

### Backward Compatibility

```python
# Legacy imports still work (deprecated)
from osrsbot.actions import GameActions  # Redirects to controllers
```

## Benefits of MVC Architecture

✅ **Industry Standard** - Familiar pattern for developers
✅ **Clear Separation** - Models, Views, Controllers have distinct roles
✅ **CQRS Integration** - Models (queries) vs Controllers (commands)
✅ **Testable** - Each layer can be tested independently
✅ **Scalable** - Easy to add new views, controllers, or models
✅ **Clean Imports** - Package-level exports for convenience
✅ **Type Safety** - Clear interfaces between layers

## Component Details

### ScriptRunner Initialization Order

```python
# 1. Load configuration
config = Config(config_file)

# 2. Initialize window management
interface = GameInterface(config)
bounds = interface.get_bounds()

# 3. Initialize infrastructure services
mouse = MouseService(config.get("mouse"))
screen = ScreenService(window_bounds=bounds)

# 4. Initialize game state (Model)
state = GameState(interface, config, screen)

# 5. Initialize game actions (Controller)
actions = GameActions(mouse, screen, config)

# 6. Run script with all dependencies
script_func(interface, state, actions, config, **kwargs)
```

### Configuration Structure

Config model manages:
- Window title
- Tesseract path
- Colors (NPCs, items, markers)
- Coordinates (UI, inventory, world, minimap)
- Timings (delays)
- Tolerances (color matching)
- OCR settings (TTL, window size)
- Mouse settings (speed, variance)

### GameState Capabilities

GameState model provides:
- HP reading via OCR with caching
- Combat status detection via pixel colors
- Inventory full detection
- Prayer points (optional)
- Run energy (optional)

### GameActions Capabilities

GameActions controller provides:
- Inventory clicking
- Color-based clicking (NPCs, items, markers)
- Coordinate-based clicking
- Teleportation (tabs, items)
- Banking operations
- Food/potion consumption
- Interface management

## Entry Points

1. **python -m osrsbot** - Uses `__main__.py`
2. **python src/osrsbot/main.py** - Uses `main.py`
3. Both call `views/menu.py:main()`

## Testing

```bash
# Test imports
python -c "from osrsbot.models import Config, GameState; print('OK')"

# Test package
python -c "import osrsbot; print(osrsbot.__version__)"

# Run bot
python -m osrsbot
```

## Future Enhancements

Potential improvements while maintaining MVC:

1. **New Views**: GUI using PyQt/Tkinter
2. **New Controllers**: Additional game actions
3. **New Models**: Quest state, bank state
4. **New Scripts**: Organized by category (combat/, skills/, minigames/)
5. **Service Improvements**: Computer vision, path finding
6. **Testing**: Unit tests per layer

## Migration Notes

This codebase recently migrated from a services-based structure to MVC:

**Old structure:**
- `config.py` (root)
- `services/game_state_service.py`
- `actions/game_actions.py`
- `cli/runner.py`
- `cli/main.py`

**New structure (MVC):**
- `models/config.py`
- `models/state.py`
- `controllers/actions.py`
- `controllers/runner.py`
- `views/menu.py`

Old import paths are deprecated but still work via compatibility redirects.
