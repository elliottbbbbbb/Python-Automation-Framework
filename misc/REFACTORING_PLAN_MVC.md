# MVC Refactoring Plan for OSRS Bot

## MVC Pattern Applied to Bot Architecture

### Classic MVC
- **Model**: Data and business logic (game state, configuration)
- **View**: User interface (CLI, calibration tools)
- **Controller**: Handles user input, coordinates Model and View (script runner, main menu)

### Adapted for Bot Architecture
Since this is a bot (not a traditional web/GUI app), we'll adapt MVC:

- **Models**: Game state data, configuration, OCR results
- **Views**: CLI interface, output formatting, calibration UI
- **Controllers**: Script execution, menu navigation, command routing
- **Services**: Infrastructure (mouse, screen, OCR, window) - supporting layer
- **Scripts**: Use cases that coordinate Controllers and Models

## Proposed MVC Structure

```
src/osrsbot/
├── __init__.py
├── __main__.py              # Entry point: python -m osrsbot
│
├── models/                  # MODEL LAYER - Data & State
│   ├── __init__.py
│   ├── config.py            # Configuration model
│   ├── state.py             # GameState - current game state (HP, combat, inventory)
│   └── coordinates.py       # Coordinate/region models (optional)
│
├── views/                   # VIEW LAYER - User Interface
│   ├── __init__.py
│   ├── cli.py               # CLI menu interface
│   ├── calibration.py       # Calibration UI
│   └── formatters.py        # Output formatting utilities
│
├── controllers/             # CONTROLLER LAYER - Business Logic
│   ├── __init__.py
│   ├── runner.py            # ScriptRunner - executes scripts
│   ├── actions.py           # GameActions - game operations (commands)
│   └── menu.py              # MenuController - handles menu navigation
│
├── services/                # SERVICE LAYER - Infrastructure
│   ├── __init__.py
│   ├── input.py             # MouseService - input control
│   ├── vision.py            # ScreenService - screen capture
│   ├── ocr.py               # OCRService - text recognition
│   └── window.py            # WindowService - window management
│
├── scripts/                 # SCRIPTS - Use Cases
│   ├── __init__.py
│   ├── combat/
│   │   ├── __init__.py
│   │   └── green_dragons.py
│   │
│   ├── skills/
│   │   ├── __init__.py
│   │   └── thieving.py      # guns.py renamed for clarity
│   │
│   └── dev/
│       ├── __init__.py
│       └── test.py
│
└── utils/                   # UTILITIES - Helpers
    ├── __init__.py
    └── helpers.py
```

## Detailed MVC Mapping

### 1. Models (Data & State)

**models/config.py**
- Configuration data model
- Loads/saves config.json
- Provides getters/setters
- Validation logic

**models/state.py** (renamed from game_state_service.py)
- Current game state representation
- HP, combat status, inventory
- **Read-only queries** (CQRS pattern)
- Uses services to detect state

```python
# models/state.py
class GameState:
    """Model: Represents current game state (read-only queries)"""
    def get_hp(self) -> int
    def in_combat(self) -> bool
    def inventory_full(self) -> bool
```

### 2. Views (User Interface)

**views/cli.py**
- Main menu display
- User input prompts
- Script selection interface
- Progress/status output

**views/calibration.py**
- Calibration tool UI
- Visual feedback
- Coordinate display

**views/formatters.py**
- Format script output
- Color-coded logging
- Progress bars

```python
# views/cli.py
class CLIView:
    """View: CLI interface for user interaction"""
    def display_menu(self, options: List[str])
    def get_user_choice(self) -> int
    def display_status(self, message: str)
```

### 3. Controllers (Business Logic)

**controllers/runner.py**
- Orchestrates script execution
- Dependency injection
- Initializes Models, Services
- **Main controller** for bot execution

**controllers/actions.py** (renamed from game_actions.py)
- Game action controller
- **Commands** that change game state (CQRS)
- Coordinates services to perform actions
- eat(), attack(), teleport(), etc.

**controllers/menu.py**
- Menu navigation logic
- Routes user choices to appropriate scripts
- Handles user input from View

```python
# controllers/runner.py
class ScriptRunner:
    """Controller: Orchestrates script execution"""
    def __init__(self, window_title: str)
    def run_script(self, script_func, **kwargs)

# controllers/actions.py
class GameActions:
    """Controller: Executes game actions (commands)"""
    def eat(self, food_name: str)
    def attack(self, npc_name: str)
    def teleport_ge(self)
```

### 4. Services (Infrastructure)

**services/input.py** (renamed from mouse_service.py)
- Mouse control service
- Input simulation

**services/vision.py** (renamed from screen_service.py)
- Screen capture
- Color detection
- Image matching

**services/ocr.py**
- Text recognition
- OCR caching

**services/window.py** (renamed from game_interface.py)
- Window management
- Coordinate translation

```python
# services/input.py
class MouseService:
    """Service: Low-level mouse input"""

# services/vision.py
class ScreenService:
    """Service: Screen capture and vision"""
```

## File Naming Conventions

### Remove `_service` suffix (redundant in services/ folder)
- `mouse_service.py` → `input.py`
- `screen_service.py` → `vision.py`
- `ocr_service.py` → `ocr.py`
- `game_interface.py` → `window.py`

### Remove `game_` prefix (context is clear)
- `game_actions.py` → `actions.py`
- `game_state_service.py` → `state.py`

### Use singular for modules (PEP 8 style)
- Keep as-is: `models/`, `views/`, `controllers/`, `services/`

## Complete New Structure

```
src/osrsbot/
├── __init__.py
├── __main__.py

├── models/                  # DATA LAYER
│   ├── __init__.py
│   ├── config.py           # Configuration model
│   └── state.py            # GameState queries

├── views/                   # PRESENTATION LAYER
│   ├── __init__.py
│   ├── cli.py              # CLI menu
│   ├── calibration.py      # Calibration UI
│   └── formatters.py       # Output formatting

├── controllers/             # LOGIC LAYER
│   ├── __init__.py
│   ├── runner.py           # ScriptRunner
│   ├── actions.py          # GameActions (commands)
│   └── menu.py             # MenuController

├── services/                # INFRASTRUCTURE LAYER
│   ├── __init__.py
│   ├── input.py            # MouseService
│   ├── vision.py           # ScreenService
│   ├── ocr.py              # OCRService
│   └── window.py           # WindowService

├── scripts/                 # USE CASES
│   ├── __init__.py
│   ├── combat/
│   │   ├── __init__.py
│   │   └── green_dragons.py
│   ├── skills/
│   │   ├── __init__.py
│   │   └── thieving.py
│   └── dev/
│       ├── __init__.py
│       └── test.py

└── utils/
    ├── __init__.py
    └── helpers.py
```

## Import Examples

### Before (Current)
```python
from osrsbot.services.mouse_service import MouseService
from osrsbot.services.screen_service import ScreenService
from osrsbot.services.game_state_service import GameState
from osrsbot.actions.game_actions import GameActions
from osrsbot.config import Config
```

### After (MVC)
```python
# Models
from osrsbot.models.config import Config
from osrsbot.models.state import GameState

# Controllers
from osrsbot.controllers.actions import GameActions
from osrsbot.controllers.runner import ScriptRunner

# Services
from osrsbot.services.input import MouseService
from osrsbot.services.vision import ScreenService
from osrsbot.services.ocr import OCRService
from osrsbot.services.window import WindowService

# Views
from osrsbot.views.cli import CLIView
```

### Cleaner (with package exports)
```python
from osrsbot.models import Config, State
from osrsbot.controllers import Actions, Runner
from osrsbot.services import Mouse, Screen, OCR, Window
from osrsbot.views import CLI
```

## MVC Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                           USER                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      VIEW (CLI)                             │
│  • Display menu                                             │
│  • Get user input                                           │
│  • Show script output                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              CONTROLLER (MenuController)                    │
│  • Route user choice                                        │
│  • Initialize ScriptRunner                                  │
│  • Pass to appropriate script                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               SCRIPT (green_dragons.py)                     │
│  • Business logic                                           │
│  • Uses: Controllers (Actions) + Models (State)             │
└───────────┬─────────────────────────┬───────────────────────┘
            │                         │
            │ Commands                │ Queries
            ▼                         ▼
┌─────────────────────┐    ┌──────────────────────┐
│  CONTROLLER         │    │  MODEL               │
│  (Actions)          │    │  (State)             │
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
│  • MouseService (input.py)                       │
│  • ScreenService (vision.py)                     │
│  • OCRService (ocr.py)                           │
│  • WindowService (window.py)                     │
└──────────────────────────────────────────────────┘
```

## Migration Plan

### Phase 1: Create New Folders
```bash
mkdir src/osrsbot/models
mkdir src/osrsbot/views
mkdir src/osrsbot/controllers
```

### Phase 2: Move and Rename Files

**Models:**
- `config.py` → `models/config.py`
- `services/game_state_service.py` → `models/state.py`

**Controllers:**
- `actions/game_actions.py` → `controllers/actions.py`
- `cli/runner.py` → `controllers/runner.py`
- `cli/main.py` → `controllers/menu.py` (rename for clarity)

**Views:**
- Extract menu display from `main.py` → `views/cli.py`
- `cli/calibration.py` → `views/calibration.py`

**Services:**
- `services/mouse_service.py` → `services/input.py`
- `services/screen_service.py` → `services/vision.py`
- `services/ocr_service.py` → `services/ocr.py`
- `core/game_interface.py` → `services/window.py`

**Entry Point:**
- `main.py` → `__main__.py`

**Delete:**
- `actions/` folder (moved to controllers)
- `core/` folder (moved to services)
- `cli/` folder (split between views and controllers)

### Phase 3: Update Imports
1. Update all `from osrsbot.services.mouse_service` → `from osrsbot.services.input`
2. Update all `from osrsbot.actions.game_actions` → `from osrsbot.controllers.actions`
3. Update all `from osrsbot.services.game_state_service` → `from osrsbot.models.state`
4. Update all `from osrsbot.config` → `from osrsbot.models.config`

### Phase 4: Update `__init__.py` Exports
Create clean package-level imports for each layer.

## Benefits of MVC Structure

✅ **Industry Standard**: Familiar pattern for most developers
✅ **Clear Separation**: Model, View, Controller have distinct responsibilities
✅ **CQRS Integration**: Models (queries) vs Controllers (commands)
✅ **Testable**: Each layer can be tested independently
✅ **Scalable**: Easy to add new views (GUI?), controllers (new actions), models
✅ **Clean Names**: No redundant prefixes/suffixes

## Next Steps

1. **Approve structure**: Confirm MVC layout works for you
2. **Execute migration**: Run the 4-phase migration
3. **Update documentation**: Update ARCHITECTURE.md with MVC pattern
4. **Test**: Ensure all imports work and scripts run

Would you like me to proceed with the MVC refactoring?
