# File Structure Refactoring Plan

## Current Issues
1. **Inconsistent naming**: `game_actions.py` vs `mouse_service.py` vs `config.py`
2. **`_service` suffix redundancy**: All files in `services/` are services - suffix is noise
3. **Unclear system boundaries**: `actions/` and `core/` not clearly distinct from `services/`
4. **Mixed concerns in `cli/`**: Has both CLI and core business logic (runner)
5. **Ambiguous naming**: `main.py` at two levels (root and cli/)

## Python Naming Conventions (PEP 8)
- **Modules**: `lowercase_with_underscores.py`
- **Packages**: `lowercase` (no underscores preferred, but allowed)
- **Classes**: `CapWords`
- **Keep names short but descriptive**
- **Avoid redundant suffixes** when folder context makes it clear

## Proposed New Structure - System-Based

```
src/osrsbot/
├── __init__.py
├── __main__.py              # Entry point: python -m osrsbot
│
├── domain/                  # Domain/Business Logic Layer
│   ├── __init__.py
│   ├── actions.py           # GameActions class
│   └── state.py             # GameState class (queries)
│
├── infrastructure/          # Infrastructure Layer (I/O, External Systems)
│   ├── __init__.py
│   ├── input/              # Input systems
│   │   ├── __init__.py
│   │   └── mouse.py        # MouseService
│   │
│   ├── vision/             # Vision/perception systems
│   │   ├── __init__.py
│   │   ├── screen.py       # ScreenService
│   │   └── ocr.py          # OCRService
│   │
│   └── platform/           # Platform integration
│       ├── __init__.py
│       └── window.py       # GameInterface (window management)
│
├── application/            # Application Layer
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   └── runner.py           # ScriptRunner (dependency injection)
│
├── interface/              # User Interface Layer
│   ├── __init__.py
│   ├── cli.py              # CLI menu and commands
│   └── calibration.py      # Calibration tools
│
├── scripts/                # Bot Scripts (use cases)
│   ├── __init__.py
│   ├── green_dragons.py
│   ├── guns.py
│   └── test.py
│
└── utils/                  # Shared utilities
    ├── __init__.py
    └── helpers.py          # OCR helpers, etc.
```

## Alternative: Simpler Feature-Based Structure

```
src/osrsbot/
├── __init__.py
├── __main__.py              # Entry point: python -m osrsbot
│
├── core/                    # Core business logic
│   ├── __init__.py
│   ├── actions.py           # GameActions
│   ├── state.py             # GameState
│   ├── config.py            # Configuration
│   └── runner.py            # ScriptRunner
│
├── io/                      # Input/Output systems
│   ├── __init__.py
│   ├── mouse.py             # Mouse control
│   ├── screen.py            # Screen capture
│   ├── ocr.py               # OCR
│   └── window.py            # Window management
│
├── cli/                     # Command-line interface
│   ├── __init__.py
│   ├── menu.py              # Main menu
│   └── calibration.py       # Calibration tools
│
├── scripts/                 # Bot scripts
│   ├── __init__.py
│   ├── green_dragons.py
│   ├── guns.py
│   └── test.py
│
└── utils/                   # Utilities
    ├── __init__.py
    └── helpers.py
```

## Recommended: Hybrid Approach (Best Balance)

```
src/osrsbot/
├── __init__.py
├── __main__.py              # Entry point

├── domain/                  # Domain layer (business logic)
│   ├── __init__.py
│   ├── actions.py           # GameActions (commands)
│   └── queries.py           # GameState (queries) - clearer name!

├── services/                # Service layer (infrastructure)
│   ├── __init__.py
│   ├── input.py             # MouseService
│   ├── vision.py            # ScreenService
│   ├── ocr.py               # OCRService
│   └── window.py            # GameInterface

├── app/                     # Application layer
│   ├── __init__.py
│   ├── config.py            # Configuration
│   └── runner.py            # ScriptRunner

├── cli/                     # Interface layer
│   ├── __init__.py
│   ├── menu.py              # Main menu (renamed from main.py)
│   └── calibration.py       # Calibration UI

├── scripts/                 # Scripts (use cases)
│   ├── __init__.py
│   ├── combat/             # Combat-related scripts
│   │   ├── __init__.py
│   │   └── green_dragons.py
│   │
│   ├── skills/             # Skilling scripts
│   │   ├── __init__.py
│   │   └── guns.py         # Thieving
│   │
│   └── dev/                # Development/testing
│       ├── __init__.py
│       └── test.py

└── utils/
    ├── __init__.py
    └── helpers.py
```

## Key Improvements

### 1. Remove `_service` Suffix
**Before**: `mouse_service.py`, `screen_service.py`, `game_state_service.py`
**After**: `input.py`, `vision.py`, `queries.py`

**Rationale**:
- Folder name `services/` already indicates these are services
- Shorter, cleaner imports: `from osrsbot.services.input import MouseService`
- Less redundant: `services/mouse_service.py` → `services/input.py`

### 2. Clearer Domain Separation
**Before**: Unclear distinction between `actions/`, `core/`, `services/`
**After**:
- `domain/` = Business logic (what the bot does)
- `services/` = Infrastructure (how it does it)
- `app/` = Application wiring

### 3. Better Script Organization
**Before**: Flat `scripts/` directory
**After**: Categorized by type:
- `scripts/combat/` - Combat scripts
- `scripts/skills/` - Skilling scripts
- `scripts/dev/` - Development/testing

### 4. Renamed for Clarity
- `game_actions.py` → `actions.py` (context clear from folder)
- `game_state_service.py` → `queries.py` (more accurate name!)
- `cli/main.py` → `cli/menu.py` (avoid confusion with root main)
- `core/game_interface.py` → `services/window.py` (clearer purpose)

### 5. Entry Point Convention
- `__main__.py` at package root
- Allows: `python -m osrsbot` instead of `python main.py`
- Standard Python convention

## Migration Strategy

### Phase 1: Rename Files (No structural changes)
1. `game_actions.py` → `actions.py`
2. `mouse_service.py` → `input.py`
3. `screen_service.py` → `vision.py`
4. `game_state_service.py` → `queries.py`
5. `game_interface.py` → `window.py`
6. `ocr_service.py` → `ocr.py`

### Phase 2: Reorganize Folders
1. Rename `actions/` → `domain/`
2. Move `config.py` and `cli/runner.py` → `app/`
3. Rename `cli/main.py` → `cli/menu.py`
4. Create `__main__.py` entry point
5. Organize scripts by category

### Phase 3: Update Imports
1. Update all import statements
2. Update `__init__.py` exports
3. Update documentation

## Import Examples

### Current (Verbose)
```python
from osrsbot.services.mouse_service import MouseService
from osrsbot.services.screen_service import ScreenService
from osrsbot.services.game_state_service import GameState
from osrsbot.actions.game_actions import GameActions
```

### Proposed (Clean)
```python
from osrsbot.services.input import MouseService
from osrsbot.services.vision import ScreenService
from osrsbot.domain.queries import GameState
from osrsbot.domain.actions import GameActions
```

### Even Better (Package-level exports)
```python
from osrsbot.services import Mouse, Screen
from osrsbot.domain import Actions, State
```

## Decision Points

**Which structure do you prefer?**

1. **System-Based** (infrastructure/, domain/, application/) - DDD-style
2. **Feature-Based** (core/, io/, cli/) - Simpler, flatter
3. **Hybrid** (domain/, services/, app/) - Recommended balance

**Additional questions:**
- Keep `_service` suffix or remove it?
- Categorize scripts by type or keep flat?
- Use `__main__.py` or stick with `main.py`?
- Rename `GameState` to `GameQueries` for clarity?

Let me know your preferences and I'll implement the refactoring!
