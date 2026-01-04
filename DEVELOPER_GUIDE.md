# OSRS Bot Framework - Developer Guide

**Welcome!** This guide will help you start writing bot scripts for the OSRS Automation Framework.

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Architecture and Patterns](#2-architecture-and-patterns)
3. [Project Structure](#3-project-structure)
4. [Writing Your First Bot](#4-writing-your-first-bot)
5. [The CQRS Pattern](#5-the-cqrs-pattern)
6. [Service Layer](#6-service-layer)
7. [Configuration](#7-configuration)
8. [Common Patterns](#8-common-patterns)
9. [Examples](#9-examples)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Project Overview

This is a **6,000+ line Python bot framework** for Old School RuneScape (OSRS) automation. It demonstrates:

- **Clean Architecture** with layered design
- **CQRS Pattern** (Command Query Responsibility Segregation)
- **State Machine Framework** for complex bot logic
- **Dependency Injection** for testability
- **Computer Vision** for game interaction (OpenCV, Tesseract OCR)
- **Anti-Ban Techniques** (timing variance, idle actions, breaks)

**Technology Stack:**
- Python 3.11+
- OpenCV (template matching, image processing)
- Tesseract OCR (stat reading)
- PyAutoGUI (input simulation)
- NumPy (pixel analysis)

---

## 2. Architecture and Patterns

### 2.1 Layered Architecture

```
┌─────────────────────────────────────────┐
│  YOUR BOT SCRIPT (scripts/)             │
│  - State machine or simple loop         │
│  - Calls actions and queries            │
└────────┬──────────────┬─────────────────┘
         │              │
    ┌────▼─────┐   ┌───▼──────┐
    │ Commands │   │ Queries  │  ← CQRS Layer
    │ (WRITE)  │   │ (READ)   │
    └────┬─────┘   └───┬──────┘
         │             │
    ┌────▼─────────────▼─────┐
    │   Services Layer       │  ← Utilities
    │  (Mouse, Screen, OCR)  │
    └────────────────────────┘
```

### 2.2 Key Principles

**CQRS (Command Query Responsibility Segregation):**
- **Commands** = Actions that *change* game state (click, move, eat)
- **Queries** = Checks that *read* game state (is inventory full?, am I in combat?)

**Separation of Concerns:**
- **Scripts** = High-level bot logic
- **Commands** = Game actions
- **Queries** = Game state checks
- **Services** = Low-level utilities

**Dependency Injection:**
- All services are created by `ScriptRunner`
- Injected into your bot automatically
- No manual initialization needed

---

## 3. Project Structure

```
src/osrsbot/
├── core/                  # Framework foundation
│   ├── base_bot.py       # Simple bot base class
│   ├── state_machine_bot.py  # State machine framework
│   ├── base_bankstander.py   # Banking bot base class
│   └── runner.py         # Script runner (entry point)
│
├── commands/              # CQRS Command layer (WRITE operations)
│   ├── game_actions.py   # Main action facade
│   ├── combat_actions.py # Combat-specific actions
│   ├── bank_actions.py   # Banking actions
│   └── inventory_actions.py  # Inventory manipulation
│
├── queries/               # CQRS Query layer (READ operations)
│   ├── game_queries.py   # Main query facade
│   ├── combat_queries.py # Combat state checks
│   ├── inventory_queries.py  # Inventory state
│   ├── stat_queries.py   # HP/Prayer/Run via OCR
│   └── bank_queries.py   # Bank interface detection
│
├── services/              # Service implementations
│   ├── mouse_service.py  # Human-like mouse movement
│   ├── screen_service.py # Screenshot & pixel analysis
│   ├── template_match_service.py  # OpenCV matching
│   ├── template_ocr_service.py    # Tesseract OCR
│   ├── walker_service.py # World coordinate pathfinding
│   └── anti_ban_service.py  # Anti-detection
│
├── scripts/               # ← YOUR BOTS GO HERE
│   ├── nmz_afk.py        # Example: NMZ AFK bot
│   ├── bs_flax.py        # Example: Herb cleaning
│   └── comprehensive_state_bot_test.py  # Full example
│
├── models/                # Data structures
│   ├── config.py         # Configuration loading
│   └── ui_elements.py    # UI element models
│
└── app/                   # Application layer
    ├── menu.py           # CLI menu
    └── calibration.py    # Color/coordinate calibration
```

### Where Things Go

| You Want To... | Create It In... | Example |
|----------------|-----------------|---------|
| Write a new bot | `scripts/` | `my_bot.py` |
| Add a new action (click, move) | `commands/` | `my_actions.py` |
| Add a new state check | `queries/` | `my_queries.py` |
| Add utility logic | `services/` | `my_service.py` |
| Add configuration | `config.json` | N/A |

---

## 4. Writing Your First Bot

### 4.1 Choose Your Base Class

You have three options:

| Base Class | Use When... | Complexity |
|------------|-------------|------------|
| **`Bot`** | Simple linear logic, no states | Low |
| **`StateMachineBot`** | Complex logic with multiple states | Medium |
| **`BankstanderBot`** | Banking + processing items | Low |

### 4.2 Option 1: Simple Bot (Bot Class)

**When to use:** Straightforward logic without state management.

```python
# File: src/osrsbot/scripts/my_simple_bot.py

import logging
from osrsbot.core.base_bot import Bot

logger = logging.getLogger(__name__)


class MySimpleBot(Bot):
    """Simple bot that does one thing repeatedly."""

    def __init__(self, **kwargs):
        super().__init__(script_name="My Simple Bot", **kwargs)

    def run_cycle(self, bank_location: str, run_number: int) -> None:
        """
        Execute one full cycle of the bot.

        This method is called repeatedly by the framework.

        Args:
            bank_location: Bank location (if applicable)
            run_number: Current run number (1, 2, 3, ...)
        """
        logger.info(f"[Run {run_number}] Starting cycle...")

        # Your bot logic here
        if not self.state.in_combat():
            # Attack something
            self.actions.attack_npc("green_dragon")

        # Eat if HP low
        hp = self.state.get_hp()
        if hp and hp < 30:
            self.actions.eat("manta_ray")

        # Wait a bit
        self.actions.wait("medium")
```

**That's it!** The framework handles:
- Window management
- Service initialization
- Error handling
- Keyboard listener ('q' to exit)

### 4.3 Option 2: State Machine Bot

**When to use:** Complex logic with multiple phases (combat, banking, looting).

```python
# File: src/osrsbot/scripts/my_state_bot.py

import logging
from enum import Enum, auto
from typing import Dict

from osrsbot.core.state_machine_bot import StateMachineBot, StateResult
from osrsbot.core.state_helpers import build_metadata_dict
from osrsbot.models.state_types import StateMetadata, StateExecutionContext

logger = logging.getLogger(__name__)


# Step 1: Define your states
class MyBotStates(Enum):
    IDLE = auto()
    COMBAT = auto()
    BANKING = auto()
    COMPLETE = auto()


# Step 2: Create bot class
class MyStateBot(StateMachineBot):
    """State machine bot with multiple phases."""

    def __init__(self, **kwargs):
        super().__init__(script_name="My State Bot", **kwargs)
        self.kills = 0

    # Step 3: Define states enum
    def define_states(self) -> type[Enum]:
        return MyBotStates

    # Step 4: Configure each state
    def define_state_metadata(self) -> Dict[Enum, StateMetadata]:
        return build_metadata_dict(MyBotStates, {
            MyBotStates.IDLE: {
                "name": "Idle",
                "description": "Initialize",
                "max_retries": 1,
            },
            MyBotStates.COMBAT: {
                "name": "Combat",
                "description": "Fight NPCs",
                "timeout": 300.0,  # 5 minutes
                "failover": MyBotStates.BANKING,
            },
            MyBotStates.BANKING: {
                "name": "Banking",
                "description": "Bank items",
                "max_retries": 3,
                "failover": MyBotStates.COMPLETE,
            },
            MyBotStates.COMPLETE: {
                "name": "Complete",
                "description": "Run finished",
            },
        })

    # Step 5: Define valid transitions
    def define_transitions(self) -> list:
        from osrsbot.models.state_types import StateTransition
        return [
            StateTransition(MyBotStates.IDLE, MyBotStates.COMBAT),
            StateTransition(MyBotStates.COMBAT, MyBotStates.BANKING),
            StateTransition(MyBotStates.BANKING, MyBotStates.COMPLETE),
        ]

    # Step 6: Set starting state
    def get_initial_state(self) -> Enum:
        return MyBotStates.IDLE

    # Step 7: Implement handlers for each state
    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        """IDLE state - Initialize."""
        logger.info("[IDLE] Starting bot...")
        return StateResult.SUCCESS  # Move to next state

    def _handle_combat(self, context: StateExecutionContext) -> StateResult:
        """COMBAT state - Fight NPCs."""
        logger.info("[COMBAT] Fighting...")

        # If not in combat, find target
        if not self.state.in_combat():
            if self.actions.attack_npc("green_dragon"):
                logger.info("COMBAT: Attacked NPC")
            else:
                logger.warning("COMBAT: No NPCs found")
                return StateResult.FAILURE

        # Check HP and eat if needed
        hp = self.state.get_hp()
        if hp and hp < 40:
            self.actions.eat("manta_ray")

        # Wait for combat to finish
        self.actions.wait("medium")

        # If killed 10, go bank
        if self.kills >= 10:
            return StateResult.SUCCESS  # Move to BANKING

        # Otherwise keep fighting
        return StateResult.RETRY  # Stay in COMBAT

    def _handle_banking(self, context: StateExecutionContext) -> StateResult:
        """BANKING state - Deposit loot."""
        logger.info("[BANKING] Banking items...")

        # Open bank
        if not self.actions.click_banker(["banker"]):
            return StateResult.FAILURE

        self.actions.wait("medium")

        # Deposit all
        self.actions.deposit_all()
        self.actions.wait("short")

        # Close bank
        self.actions.close_interface()

        return StateResult.SUCCESS  # Move to COMPLETE

    def _handle_complete(self, context: StateExecutionContext) -> StateResult:
        """COMPLETE state - Finish run."""
        logger.info("[COMPLETE] Run finished!")
        return StateResult.SUCCESS
```

**State Handler Naming Convention:**
- State: `MyBotStates.COMBAT`
- Handler: `def _handle_combat(self, context) -> StateResult:`

### 4.4 Option 3: Bankstander Bot

**When to use:** Repetitive banking task (cleaning herbs, making potions).

```python
# File: src/osrsbot/scripts/my_bankstander.py

import logging
from pathlib import Path

from osrsbot.core.base_bankstander import BankstanderBot
from osrsbot.models.state_types import StateExecutionContext, StateResult

logger = logging.getLogger(__name__)


class MyBankstander(BankstanderBot):
    """Clean grimy herbs."""

    def __init__(self, **kwargs):
        # Path to item template image
        images_dir = Path(__file__).parent.parent / "images" / "bot" / "items"

        super().__init__(
            item_name="grimy toadflax",
            item_search_text="toadflax",
            item_template=str(images_dir / "grimy_toadflax.PNG"),
            banker_templates=["banker"],
            **kwargs,
            script_name="Herb Cleaner"
        )

    def process_items(self, context: StateExecutionContext) -> StateResult:
        """
        Process inventory items.

        Base class handles:
        - Opening bank
        - Withdrawing items
        - Depositing processed items

        You only implement the processing logic.
        """
        logger.info("[PROCESS] Cleaning herbs...")

        # Click each inventory slot to clean herb
        for slot in range(1, 29):
            self.actions.click_inventory_slot(slot)
            self.actions.wait("short")

        return StateResult.SUCCESS
```

**That's it!** The base class handles all banking states for you.

---

## 5. The CQRS Pattern

**CQRS = Command Query Responsibility Segregation**

Separate *reading* game state from *changing* game state.

### 5.1 Queries (READ) - "What's the state?"

**Location:** `src/osrsbot/queries/`

Queries **read** game state without modifying anything.

**Main facade:** `GameQueries` (accessed via `self.state`)

```python
# Check combat status
if self.state.in_combat():
    logger.info("Currently fighting")

# Check inventory
if self.state.inventory_full():
    logger.info("Inventory is full")

# Check bank interface
if self.state.is_bank_open():
    logger.info("Bank is open")

# Read HP (OCR)
hp = self.state.get_hp()
if hp and hp < 30:
    logger.warning(f"Low HP: {hp}")

# Read prayer (OCR)
prayer = self.state.get_prayer()

# Count inventory items
filled_slots = self.state.count_filled_slots()
```

**Available query modules:**

| Module | Purpose | Key Methods |
|--------|---------|-------------|
| `game_queries.py` | Main facade | `in_combat()`, `inventory_full()`, `is_bank_open()` |
| `combat_queries.py` | Combat checks | `in_combat()`, `click_success()` |
| `inventory_queries.py` | Inventory state | `count_filled_slots()`, `get_filled_slots()` |
| `stat_queries.py` | OCR stats | `get_hp()`, `get_prayer()`, `get_run_energy()` |
| `bank_queries.py` | Bank detection | `is_bank_open()` |

### 5.2 Commands (WRITE) - "Do something"

**Location:** `src/osrsbot/commands/`

Commands **perform actions** that change game state.

**Main facade:** `GameActions` (accessed via `self.actions`)

```python
# Combat actions
self.actions.attack_npc("green_dragon")
self.actions.eat("manta_ray")
self.actions.drink_potion("super_restore")

# Movement
self.actions.walk_to_marker("yellow_tile_marker")
self.actions.walk_tiles("north", 5)

# Inventory
self.actions.click_inventory_slot(1)
self.actions.drop_item(1)
self.actions.drop_all_except([1, 2, 3])

# Banking
self.actions.click_banker(["banker"])
self.actions.deposit_all()
self.actions.withdraw_item("manta_ray", 10)

# Interface
self.actions.close_interface()

# Waiting
self.actions.wait("short")   # ~0.5s
self.actions.wait("medium")  # ~1.5s
self.actions.wait("long")    # ~3.0s
```

**Available command modules:**

| Module | Purpose | Key Methods |
|--------|---------|-------------|
| `game_actions.py` | Main facade | Most common methods |
| `combat_actions.py` | Combat | `attack_npc()`, `eat()`, `drink_potion()` |
| `bank_actions.py` | Banking | `click_banker()`, `deposit_all()`, `withdraw_item()` |
| `inventory_actions.py` | Inventory | `click_slot()`, `drop_item()` |

### 5.3 Why Separate Queries and Commands?

**Benefits:**
1. **Clarity** - Obvious what changes state vs reads state
2. **Testability** - Mock queries/commands independently
3. **Maintainability** - Single source of truth for state
4. **Debugging** - Easy to trace where state changes happen

---

## 6. Service Layer

Services are low-level utilities that queries/commands use internally.

**You typically don't call services directly** - use `self.actions` and `self.state` instead.

### Available Services

| Service | Purpose | Access Via |
|---------|---------|------------|
| **MouseService** | Human-like mouse movement | `self.actions.mouse` |
| **ScreenService** | Screenshot & pixel analysis | `self.state.screen` |
| **TemplateMatchService** | OpenCV template matching | `self.actions.template_service` |
| **TemplateOCRService** | Tesseract OCR | `self.state.ocr_service` |
| **WalkerService** | World pathfinding | `self.actions.walker` |
| **AntiBanService** | Randomization, breaks | `self.actions.anti_ban` |

**Example (advanced):**
```python
# Direct service access (rarely needed)
screenshot = self.state.screen.capture()
matches = self.state.screen.find_color("#FF0000", tolerance=10)

# Mouse movement styles
self.actions.mouse.move_to(x, y, style="bezier")  # Bezier curve
self.actions.mouse.move_to(x, y, style="curved")  # Simple curve
```

---

## 7. Configuration

All bot behavior is configured via `config.json`.

### 7.1 Config Structure

**File:** `config.json` (root directory)

```json
{
  "account_name": "YourAccount",
  "window_title": "RuneLite - ",
  "tesseract_path": "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",

  "colors": {
    "yellow_tile_marker": "#FFFF00",
    "green_dragon": "#00FFFF",
    "manta_ray": "#765C45",
    "banker": "#00FFFF"
  },

  "coordinates": {
    "inventory": {
      "slot_1": {"x": 591, "y": 257},
      "slot_2": {"x": 633, "y": 256}
    },
    "world": {
      "varrock_fountain": {"x": 3207, "y": 3434}
    }
  },

  "templates": {
    "ui_buttons": {
      "banker": {
        "path": "src/osrsbot/images/bot/npcs/banker.PNG",
        "threshold": 0.70
      }
    }
  },

  "timings": {
    "short": [0.4, 0.7],
    "medium": [0.8, 1.3],
    "long": [2.5, 3.8]
  },

  "mouse": {
    "min_speed": 0.2,
    "max_speed": 0.6,
    "overshoot_chance": 0.15
  }
}
```

### 7.2 Accessing Config

```python
# Get window title
window_title = self.config.get("window_title")

# Get color
dragon_color = self.config.get("colors", "green_dragon")

# Get nested value with default
threshold = self.config.get(("templates", "ui_buttons", "banker", "threshold"), default=0.7)
```

### 7.3 Calibration Tool

Use the built-in calibration tool to get accurate colors/coordinates:

```bash
python -m osrsbot.app.menu
# Select: 1. Calibrate Colors & Coordinates
```

---

## 8. Common Patterns

### 8.1 State Machine State Results

Return these from state handlers:

```python
def _handle_my_state(self, context: StateExecutionContext) -> StateResult:
    # Success - move to next state
    return StateResult.SUCCESS

    # Failure - retry (if retries available) or failover
    return StateResult.FAILURE

    # Retry immediately (don't count as retry)
    return StateResult.RETRY

    # Timeout - transition to failover state
    return StateResult.TIMEOUT
```

### 8.2 Transition to Specific State

```python
from osrsbot.core.state_machine_bot import StateTransitionRequest

def _handle_combat(self, context) -> StateResult:
    if self.kills >= 10:
        # Go to banking instead of next sequential state
        return StateTransitionRequest(MyBotStates.BANKING)

    return StateResult.SUCCESS  # Normal transition
```

### 8.3 Retry Logic

```python
def _handle_something(self, context: StateExecutionContext) -> StateResult:
    # Access retry count
    logger.info(f"Attempt {context.retry_count + 1}")

    if context.retry_count >= 2:
        logger.error("Failed after 3 attempts, giving up")
        return StateResult.FAILURE

    # Try action
    if self.actions.click_banker(["banker"]):
        return StateResult.SUCCESS

    return StateResult.RETRY  # Try again
```

### 8.4 Anti-Ban Integration

```python
# Timing variance (automatic)
self.actions.wait("short")  # Varies between 0.4-0.7s

# Scheduled breaks
if self.actions.anti_ban.should_take_break():
    self.actions.anti_ban.execute_break()

# Idle actions
if self.actions.anti_ban.should_idle_action():
    self.actions.anti_ban.execute_idle_action()
```

### 8.5 Logging

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Important event")
logger.debug("Detailed info")
logger.warning("Warning message")
logger.error("Error occurred")
```

### 8.6 State History (Debugging)

```python
# Get recent state transitions
history = self.get_state_history(last_n=5)

for entry in history:
    print(f"{entry.state.name}: {entry.result.value} ({entry.duration:.2f}s)")
    if entry.error_message:
        print(f"  Error: {entry.error_message}")
```

---

## 9. Examples

### Example 1: Minimal Bankstander

Clean herbs by clicking inventory slots.

```python
from pathlib import Path
from osrsbot.core.base_bankstander import BankstanderBot
from osrsbot.models.state_types import StateExecutionContext, StateResult

class HerbCleaner(BankstanderBot):
    def __init__(self, **kwargs):
        images = Path(__file__).parent.parent / "images" / "bot" / "items"
        super().__init__(
            item_name="grimy toadflax",
            item_search_text="toadflax",
            item_template=str(images / "grimy_toadflax.PNG"),
            **kwargs,
            script_name="Herb Cleaner"
        )

    def process_items(self, context: StateExecutionContext) -> StateResult:
        for slot in range(1, 29):
            self.actions.click_inventory_slot(slot)
        return StateResult.SUCCESS
```

**Lines of code:** ~15. Banking handled automatically.

### Example 2: Combat Bot with States

```python
from enum import Enum, auto
from osrsbot.core.state_machine_bot import StateMachineBot, StateResult
from osrsbot.models.state_types import StateExecutionContext

class CombatStates(Enum):
    FIND_NPC = auto()
    COMBAT = auto()
    LOOT = auto()

class SimpleCombatBot(StateMachineBot):
    def __init__(self, **kwargs):
        super().__init__(script_name="Combat Bot", **kwargs)
        self.kills = 0

    def define_states(self) -> type[Enum]:
        return CombatStates

    def get_initial_state(self) -> Enum:
        return CombatStates.FIND_NPC

    def _handle_find_npc(self, context: StateExecutionContext) -> StateResult:
        if self.actions.attack_npc("green_dragon"):
            return StateResult.SUCCESS
        return StateResult.RETRY

    def _handle_combat(self, context: StateExecutionContext) -> StateResult:
        # Eat if low HP
        hp = self.state.get_hp()
        if hp and hp < 40:
            self.actions.eat("manta_ray")

        # Wait for combat to finish
        if self.state.in_combat():
            return StateResult.RETRY

        self.kills += 1
        return StateResult.SUCCESS  # -> LOOT

    def _handle_loot(self, context: StateExecutionContext) -> StateResult:
        # Loot drops
        self.actions.wait("medium")
        return StateResult.SUCCESS  # -> FIND_NPC
```

### Example 3: Custom Query

Add bot-specific detection logic:

```python
# File: src/osrsbot/queries/my_custom_queries.py

class MyCustomQueries:
    def __init__(self, screen_service):
        self.screen = screen_service

    def is_special_npc_nearby(self) -> bool:
        matches = self.screen.find_color("#FF00FF", tolerance=15)
        return len(matches) > 0
```

Use in your bot:
```python
from osrsbot.queries.my_custom_queries import MyCustomQueries

class MyBot(StateMachineBot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.custom_queries = MyCustomQueries(self.state.screen)

    def _handle_some_state(self, context):
        if self.custom_queries.is_special_npc_nearby():
            logger.info("Special NPC detected!")
```

---

## 10. Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| "Window not found" | Check `window_title` in config.json matches RuneLite exactly |
| Template matching fails | Verify template image is from current client, check threshold |
| Color detection wrong | Use calibration tool (menu option 1) |
| OCR reading wrong | Check tesseract path in config |
| Bot won't exit on 'q' | Set `enable_exit_key=True` in constructor |
| State stuck in loop | Check handler return values and transitions |

### Debugging Strategies

1. **Enable debug logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Print state history:**
   ```python
   for entry in self.get_state_history():
       print(f"{entry.state.name}: {entry.result.value}")
   ```

3. **Test queries:**
   ```python
   print(f"In combat: {self.state.in_combat()}")
   print(f"HP: {self.state.get_hp()}")
   print(f"Inventory full: {self.state.inventory_full()}")
   ```

4. **Screenshot for inspection:**
   ```python
   import pyautogui
   screenshot = pyautogui.screenshot()
   screenshot.save("debug.png")
   ```

### Getting Help

1. Check existing similar bots:
   - `bs_flax.py` - Simple bankstander
   - `nmz_afk.py` - State machine with timers
   - `comprehensive_state_bot_test.py` - Full feature showcase

2. Read docstrings in base classes:
   - `base_bot.py`
   - `state_machine_bot.py`
   - `base_bankstander.py`

3. Review the facades:
   - `game_actions.py` - All available actions
   - `game_queries.py` - All available queries

---

## Quick Start Checklist

- [ ] Choose base class: `Bot`, `StateMachineBot`, or `BankstanderBot`
- [ ] Create file in `src/osrsbot/scripts/my_bot.py`
- [ ] Implement required methods (`run_cycle()` or state handlers)
- [ ] Add colors/coordinates to `config.json` if needed
- [ ] Test bot independently with a simple `main()` block
- [ ] Add to `menu.py` if you want CLI integration
- [ ] Add logging for debugging
- [ ] Test with anti-ban features enabled

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│  YOUR BOT (MyBot.py)                            │
│  ├─ Defines states/handlers                    │
│  ├─ Calls self.actions (commands)              │
│  └─ Calls self.state (queries)                 │
└────────┬────────────────────┬───────────────────┘
         │                    │
    ┌────▼──────────┐    ┌───▼────────────┐
    │ Commands      │    │ Queries        │
    │ (WRITE)       │    │ (READ)         │
    │ - click       │    │ - in_combat()  │
    │ - move        │    │ - get_hp()     │
    │ - eat         │    │ - is_full()    │
    └────┬──────────┘    └───┬────────────┘
         │                   │
    ┌────▼───────────────────▼──────────────┐
    │  SERVICES                             │
    │  ┌─────────┐ ┌─────────┐ ┌─────────┐ │
    │  │ Mouse   │ │ Screen  │ │   OCR   │ │
    │  └─────────┘ └─────────┘ └─────────┘ │
    │  ┌─────────┐ ┌─────────┐ ┌─────────┐ │
    │  │ Walker  │ │Template │ │Anti-Ban │ │
    │  └─────────┘ └─────────┘ └─────────┘ │
    └───────────────────────────────────────┘
```

---

## Final Notes

This framework prioritizes **clean architecture** and **maintainability**. Each layer has a clear responsibility:

- **Scripts** = What should happen
- **Commands** = How to change state
- **Queries** = How to read state
- **Services** = Low-level utilities

When you're stuck, always check:
1. Existing similar scripts for patterns
2. Docstrings in base classes
3. Available methods in facades (`game_actions.py`, `game_queries.py`)
4. State history for execution trace

**Good luck building your bots!** 🤖
