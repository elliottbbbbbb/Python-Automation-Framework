# File Responsibilities - OSRSbot

This document lists every file in the codebase and its clear, single responsibility.

---

## Core (`src/osrsbot/core/`)

### [base_bot.py](src/osrsbot/core/base_bot.py)
**Responsibility**: Abstract base class for legacy Bot-based scripts with run loop orchestration
- Provides common bot lifecycle (initialization, run loop, banking)
- **Status**: Maintained for backward compatibility (prefer StateMachineBot for new bots)

### [state_machine_bot.py](src/osrsbot/core/state_machine_bot.py)
**Responsibility**: State machine framework for structured, testable bot implementations
- Manages state transitions, retry logic, timeouts
- Tracks state history for debugging
- **Status**: ✅ **Recommended for all new bots**

### [state_types.py](src/osrsbot/core/state_types.py)
**Responsibility**: Type definitions and dataclasses for state machine framework
- Defines `StateMetadata`, `StateTransition`, `TransitionCondition`
- Provides type-safe state configuration

### [game_interface.py](src/osrsbot/core/game_interface.py)
**Responsibility**: Window management and bounds detection for game client
- Finds RuneLite window by title
- Provides window position/dimensions
- Single source of truth for window bounds

---

## Services (`src/osrsbot/services/`)

### [screen_service.py](src/osrsbot/services/screen_service.py)
**Responsibility**: Screen capture and pixel-level color detection
- Captures screenshots (full window or regions)
- Finds pixels matching specific colors
- Sorts matches by distance from reference point
- **Dependencies**: GameInterface for window bounds

### [ocr_service.py](src/osrsbot/services/ocr_service.py)
**Responsibility**: Optical Character Recognition for reading game UI stats (HP, prayer, etc.)
- Multi-strategy preprocessing for difficult digits
- Smoothing and caching to reduce OCR calls
- Special handling for confusing digits (9 vs 4)
- **Dependencies**: Tesseract, OCR helpers

### [mouse_service.py](src/osrsbot/services/mouse_service.py)
**Responsibility**: Physical mouse movement with human-like behavior
- Bezier curve movement
- Overshoot and correction
- Click variance and delays
- **Use Case**: When you need to move the physical cursor

### [virtual_mouse_service.py](src/osrsbot/services/virtual_mouse_service.py)
**Responsibility**: Virtual mouse clicks without moving physical cursor
- Sends Windows messages directly to game window
- Allows using computer while bot runs
- **Use Case**: Preferred for most automation tasks

### [template_match_service.py](src/osrsbot/services/template_match_service.py)
**Responsibility**: OpenCV template matching for UI element detection
- Detects buttons, icons, and UI elements from template images
- Manages template caching and TTL
- Supports grid detection (inventory, prayers)
- **Key Use Cases**: Inventory slot detection, button detection
- **Data Models**: Uses `UIElement` and `UIElementGrid` from `models/ui_elements.py`

### [click_target_tracker.py](src/osrsbot/services/click_target_tracker.py)
**Responsibility**: Intelligent target selection with history tracking
- Detects stuck clicking patterns
- Maintains target locks for moving NPCs
- Blacklists inaccessible locations temporarily
- **Improves**: Color-based clicking reliability

---

## Controllers (`src/osrsbot/controllers/`)

### [actions.py](src/osrsbot/controllers/actions.py)
**Responsibility**: High-level game actions (click, wait, attack, bank, etc.)
- Coordinates services to perform game actions
- Provides bot-level API for common tasks
- **Well-Organized**: Clear section headers for different action categories
- **Used By**: All bot scripts

### [runner.py](src/osrsbot/controllers/runner.py)
**Responsibility**: Bot lifecycle management and execution orchestration
- Initializes all services and dependencies
- Runs bot classes, instances, or functions
- Standardized error handling and logging
- **Entry Point**: For executing bot scripts

---

## Queries (`src/osrsbot/queries/`)

### [game_queries.py](src/osrsbot/queries/game_queries.py)
**Responsibility**: Query game state (HP, combat status, inventory full, etc.)
- Reads HP/prayer/run energy via OCR
- Detects combat via template matching or pixel checks
- Checks inventory fullness
- **Naming Note**: Could be renamed to `game_state_service.py` for consistency

---

## Models (`src/osrsbot/models/`)

### [config.py](src/osrsbot/models/config.py)
**Responsibility**: Configuration management (load, save, default values)
- Loads from `config.json`
- Provides platform-specific defaults (Tesseract path)
- Type-safe config access via `get()` method

### [ui_elements.py](src/osrsbot/models/ui_elements.py) ✨ **NEW**
**Responsibility**: UI element data structures for template matching
- `UIElement` dataclass: Single clickable UI element with bounding box
- `UIElementGrid` class: Grid of elements (inventory, prayer) with subdivision logic
- **Used By**: TemplateMatchService, GameActions, GameState
- **Separation**: Models separated from service logic for better architecture

---

## Utils (`src/osrsbot/utils/`)

### [ocr_helpers.py](src/osrsbot/utils/ocr_helpers.py)
**Responsibility**: Shape detection heuristics to distinguish confusing digits (9 vs 4)
- Morphological image preprocessing
- Hole and tail detection
- Connected component analysis
- **Used By**: OCRService for improving accuracy

### [color_helpers.py](src/osrsbot/utils/color_helpers.py)
**Responsibility**: Color conversion and matching utilities
- Hex ↔ RGB conversion
- Color distance calculation
- Color matching with tolerance
- **Shared Utility**: Used across services and queries

---

## App (`src/osrsbot/app/`)

### [menu.py](src/osrsbot/app/menu.py)
**Responsibility**: CLI menu for launching bots and calibration tools
- User-facing script selection
- Input validation
- **Entry Point**: Main user interface

### [calibration.py](src/osrsbot/app/calibration.py)
**Responsibility**: Interactive tool for calibrating coordinates and colors
- Click coordinate capture
- Color picker
- Saves calibration to config.json

---

## Scripts (`src/osrsbot/scripts/`)

### [green_dragons_state.py](src/osrsbot/scripts/green_dragons_state.py)
**Responsibility**: Green Dragons farming bot (StateMachineBot implementation)
- **States**: IDLE → NAVIGATION → POTIONS → COMBAT → BANKING → COMPLETE
- **Status**: ✅ **Active** (state machine version)

### [test_state_machine_bot.py](src/osrsbot/scripts/test_state_machine_bot.py)
**Responsibility**: Test bot demonstrating StateMachineBot features
- Tests state transitions and retry logic
- Used for framework validation

### [legacy/green_dragons.py](src/osrsbot/scripts/legacy/green_dragons.py)
**Responsibility**: ⚠️ **DEPRECATED** - Legacy Bot-based Green Dragons implementation
- **Migration**: Use `green_dragons_state.py` instead

### [legacy/guns.py](src/osrsbot/scripts/legacy/guns.py)
**Responsibility**: ⚠️ **DEPRECATED** - Legacy function-based pickpocketing script
- **Migration**: Rewrite using StateMachineBot framework

### [legacy/test.py](src/osrsbot/scripts/legacy/test.py)
**Responsibility**: ⚠️ **DEPRECATED** - Legacy test script
- **Migration**: Use `test_state_machine_bot.py` instead

---

## Configuration & Constants

### [constants.py](src/osrsbot/constants.py)
**Responsibility**: Centralized configuration constants organized by domain
- OCR preprocessing strategies
- Shape detection thresholds
- Mouse movement parameters
- Color detection thresholds
- Game timing configurations
- Template matching settings
- **Organization**: Uses dataclasses for logical grouping

---

## Entry Points

### [__main__.py](src/osrsbot/__main__.py)
**Responsibility**: Package entry point (enables `python -m osrsbot`)
- Delegates to menu.py

### [main.py](src/osrsbot/main.py)
**Responsibility**: Alternative entry point
- Also delegates to menu.py

---

## File Count Summary

| Category | Count | Purpose |
|----------|-------|---------|
| **Core** | 4 | Bot frameworks and window management |
| **Services** | 7 | Reusable game interaction services |
| **Controllers** | 2 | Action coordination and bot execution |
| **Queries** | 1 | Game state reading |
| **Models** | 2 | Configuration and UI element data structures ✨ |
| **Utils** | 2 | Shared utilities (OCR, colors) |
| **App** | 2 | CLI and calibration |
| **Scripts (Active)** | 2 | Bot implementations |
| **Scripts (Legacy)** | 3 | Deprecated implementations |
| **Config** | 1 | Constants and configurations |
| **Entry** | 2 | Package entry points |
| **Total** | 28 | Active Python files ✨ |

---

## Architecture Layers

```
┌─────────────────────────────────────┐
│  Entry Points (main.py, __main__.py)│
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  App Layer (menu.py, calibration.py)│
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Scripts (bot implementations)      │
│  - green_dragons_state.py           │
│  - test_state_machine_bot.py        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Core (bot frameworks)              │
│  - StateMachineBot                  │
│  - Bot (legacy)                     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Controllers (action coordination)  │
│  - ScriptRunner                     │
│  - GameActions                      │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Services (game interaction)        │
│  - OCRService, MouseService, etc.   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Utils & Models (shared)            │
│  - Config, color_helpers, etc.      │
└─────────────────────────────────────┘
```

---

## Design Principles

### 1. **Single Responsibility**
Each file has one clear purpose. Services don't overlap in functionality.

### 2. **Dependency Injection**
Services are passed to controllers and bots, not created internally. Makes testing easier.

### 3. **Layered Architecture**
- **App Layer**: User interface
- **Script Layer**: Bot logic
- **Controller Layer**: Action orchestration
- **Service Layer**: Reusable game interactions
- **Util Layer**: Shared utilities

### 4. **State Machine Pattern**
New bots use StateMachineBot for explicit state management, testability, and debuggability.

### 5. **Centralized Configuration**
- Game-specific values: `config.json`
- System constants: `constants.py`
- No magic numbers in business logic

---

## Naming Conventions

### Files
- `snake_case.py` for all Python files
- Descriptive names indicating purpose (e.g., `template_match_service.py` not `templates.py`)

### Classes
- `PascalCase` (e.g., `StateMachineBot`, `OCRService`)
- Suffix with type when helpful (e.g., `*Service`, `*Bot`, `*Config`)

### Functions/Methods
- `snake_case` for all functions
- Private methods prefixed with `_` (e.g., `_clean_ocr_text`)
- Descriptive verb-noun pairs (e.g., `get_health`, `click_inventory_slot`)

---

## Module Docstrings

All active files have module-level docstrings following this format:

```python
"""
FileName - Brief one-line description.

Longer description explaining:
- What this module does
- Key classes/functions
- Main responsibilities
- Dependencies (if complex)
"""
```

---

## File Status Legend

- ✅ **Active**: Currently maintained and recommended
- ⚠️ **Deprecated**: Legacy code, use alternatives
- 🔄 **Refactoring**: Under active improvement
- 📝 **Documentation**: Primarily documentation

---

## Quick Reference

**Starting a new bot?** → Use [state_machine_bot.py](src/osrsbot/core/state_machine_bot.py)

**Need to capture screen?** → Use [screen_service.py](src/osrsbot/services/screen_service.py)

**Need to read HP/stats?** → Use [ocr_service.py](src/osrsbot/services/ocr_service.py)

**Need to click?** → Use [virtual_mouse_service.py](src/osrsbot/services/virtual_mouse_service.py)

**Need to detect UI elements?** → Use [template_match_service.py](src/osrsbot/services/template_match_service.py)

**Need to coordinate actions?** → Use [actions.py](src/osrsbot/controllers/actions.py)

**Adding constants?** → Update [constants.py](src/osrsbot/constants.py)

---

## Recent Changes (December 11, 2025)

### ✨ Refactoring: UI Models Extracted

**What Changed:**
- Created `models/ui_elements.py` with `UIElement` and `UIElementGrid`
- Moved dataclasses from `template_match_service.py` to models layer
- Improved separation of concerns (models vs service logic)
- Added comprehensive section headers to `actions.py`

**Benefits:**
- ✅ Better architecture: Models separate from services
- ✅ Improved testability: Can test data structures independently
- ✅ Clearer organization: actions.py has 8 logical sections
- ✅ Follows industry best practices (Django/Flask pattern)

**Files Modified:**
- `models/ui_elements.py` (NEW)
- `models/__init__.py` (updated exports)
- `services/template_match_service.py` (removed classes, added import)
- `controllers/actions.py` (added section headers)

---

**Last Updated**: December 11, 2025
