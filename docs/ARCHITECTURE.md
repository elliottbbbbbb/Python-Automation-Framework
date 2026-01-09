# OSRS Bot Framework - Complete Architecture Documentation

**Last Updated:** 2026-01-09
**Framework Version:** 0.1.0
**Documentation Status:** ✅ Verified against actual codebase

---

## Table of Contents

1. [Overview](#overview)
2. [Layered Architecture](#layered-architecture)
3. [Directory Structure](#directory-structure)
4. [Core Framework Components](#core-framework-components)
5. [Dependency Injection System](#dependency-injection-system)
6. [CQRS Implementation](#cqrs-implementation)
7. [Service Layer](#service-layer)
8. [State Machine Framework](#state-machine-framework)
9. [Design Patterns](#design-patterns)
10. [Execution Flow](#execution-flow)
11. [Configuration System](#configuration-system)
12. [Extension Points](#extension-points)

---

## Overview

The OSRS Bot Framework is a **layered automation toolkit** with **CQRS architecture**, **dependency injection**, and **state machine-driven bot execution**. It provides reusable infrastructure for building OSRS game automation scripts.

### Core Principles

1. **Separation of Concerns** - Clear layer boundaries with no upward dependencies
2. **Dependency Injection** - Single point of initialization with explicit wiring
3. **CQRS** - Separated read (queries) and write (commands) operations
4. **Reusability** - Base classes and templates for common bot patterns
5. **Extensibility** - Service-oriented architecture with clear interfaces
6. **Maintainability** - Focused modules with single responsibilities

### Technology Stack

- **Language:** Python 3.10+
- **Computer Vision:** OpenCV, PIL, pytesseract
- **Input Control:** pyautogui, pywin32 (Windows), interception-python (kernel-level)
- **Window Management:** PyWinCtl (Windows)
- **CLI:** rich (terminal UI)
- **Serialization:** JSON (config), dataclasses (models)

---

## Layered Architecture

### Layer Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│                 (menu.py, calibration.py)                    │
│  - User interface                                            │
│  - Bot selection                                             │
│  - Entry point                                               │
└────────────────────────┬─────────────────────────────────────┘
                         │ creates
                         ↓
┌──────────────────────────────────────────────────────────────┐
│              Dependency Injection Layer                      │
│                    (runner.py)                               │
│  - Service initialization                                    │
│  - Dependency wiring                                         │
│  - Object graph construction                                 │
└────────────────────────┬─────────────────────────────────────┘
                         │ injects dependencies into
                         ↓
┌──────────────────────────────────────────────────────────────┐
│                        Bot Layer                             │
│        (base_bot.py, state_machine_bot.py, scripts/)         │
│  - Abstract base classes                                     │
│  - State machine execution                                   │
│  - Concrete bot implementations                              │
└──────────┬─────────────────────┬──────────────┬─────────────┘
           │ uses                 │ uses         │ uses
           ↓                      ↓              ↓
┌────────────────────┐  ┌─────────────────┐  ┌────────────────┐
│  Commands Layer    │  │  Queries Layer  │  │ Configuration  │
│  (game_actions.py) │  │ (game_queries.py)│ │   (config.py)  │
│                    │  │                 │  │                │
│  Write Operations  │  │ Read Operations │  │  Settings      │
│  - GameActions     │  │ - GameState     │  │  - Coordinates │
│  - InventoryActions│  │ - CombatQueries │  │  - Colors      │
│  - CombatActions   │  │ - StatQueries   │  │  - Timings     │
│  - BankActions     │  │ - InventoryState│  │                │
└─────────┬──────────┘  └────────┬────────┘  └───────┬────────┘
          │ delegates to          │ delegates to      │ loads
          ↓                       ↓                   ↓
┌──────────────────────────────────────────────────────────────┐
│                      Services Layer                          │
│         (mouse_service.py, screen_service.py, etc.)          │
│  - Infrastructure components                                 │
│  - Reusable utilities                                        │
│  - Platform abstractions                                     │
│                                                              │
│  MouseService | ScreenService | TemplateMatchService        │
│  OCRService | AntiBanService | WalkerService                │
│  UIManager | LootDetection | PositionTracking               │
└────────────────────────┬─────────────────────────────────────┘
                         │ interacts with
                         ↓
┌──────────────────────────────────────────────────────────────┐
│                   External Systems                           │
│  - Game Window (RuneLite/OSRS client)                        │
│  - Operating System (Windows/Mac/Linux)                      │
│  - Hardware (mouse, keyboard, screen)                        │
└──────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Imports From | Responsibilities | Example Files |
|-------|--------------|------------------|---------------|
| **Application** | Runner, Config, Bots | Menu, calibration, user interaction | `app/menu.py` |
| **Dependency Injection** | Config, Services, Commands, Queries | Service initialization, wiring | `core/runner.py` |
| **Bot** | Commands, Queries, Config | Bot logic, state machines, execution flow | `core/base_bot.py`, `scripts/` |
| **Commands** | Services, Config, Constants | Write operations (clicking, moving) | `commands/game_actions.py` |
| **Queries** | Services, Config, Constants | Read operations (checking state) | `queries/game_queries.py` |
| **Services** | Constants, Config | Infrastructure (mouse, screen, OCR) | `services/mouse_service.py` |
| **Models/Constants** | None | Data structures, enums, configuration | `constants.py`, `models/config.py` |

### Dependency Rules

1. **No Upward Dependencies** - Lower layers cannot import from higher layers
2. **Constants Exception** - All layers can import from `constants.py`
3. **Config Access** - All layers can access `Config` (read-only)
4. **Service Isolation** - Services do not import from Commands or Queries
5. **Bot Isolation** - Bots only access Commands, Queries, and Config (never Services directly)

---

## Directory Structure

```
src/osrsbot/
├── app/                          # Application Layer
│   ├── menu.py                   # Interactive bot selection menu
│   ├── calibration.py            # First-time color/coordinate setup
│   ├── debug_ui.py               # UI element debugging tools
│   └── __init__.py
│
├── core/                         # Core Framework
│   ├── base_bot.py               # Abstract Bot base class
│   ├── state_machine_bot.py      # State machine bot implementation
│   ├── base_bankstander.py       # Reusable bankstander template
│   ├── game_interface.py         # Window management & coordinates
│   ├── runner.py                 # Dependency injection orchestrator
│   ├── state_types.py            # State machine data structures
│   ├── state_helpers.py          # State machine utilities
│   └── __init__.py
│
├── commands/                     # CQRS Commands (Write Operations)
│   ├── game_actions.py           # Facade for all game actions
│   ├── inventory_actions.py      # Inventory manipulation
│   ├── combat_actions.py         # Combat actions
│   ├── bank_actions.py           # Banking operations
│   └── __init__.py
│
├── queries/                      # CQRS Queries (Read Operations)
│   ├── game_queries.py           # Facade for game state
│   ├── combat_queries.py         # Combat state detection
│   ├── stat_queries.py           # HP/prayer/run OCR reading
│   ├── inventory_queries.py      # Inventory state detection
│   ├── bank_queries.py           # Bank interface detection
│   └── __init__.py
│
├── services/                     # Infrastructure Services
│   ├── mouse_service.py          # Humanized mouse movement
│   ├── win32_mouse_service.py    # Windows SendInput implementation
│   ├── interception_mouse_service.py  # Kernel-level mouse driver
│   ├── screen_service.py         # Screenshot & color detection
│   ├── template_match_service.py # Template matching (UI detection)
│   ├── template_ocr_service.py   # OCR for stats reading
│   ├── ui_manager_service.py     # UI element tracking
│   ├── anti_ban_service.py       # Break scheduling & variance
│   ├── walker_service.py         # Minimap navigation (A* pathfinding)
│   ├── loot_detection_service.py # Ground item detection
│   ├── status_socket_service.py  # RuneLite plugin integration
│   ├── coordinate_ocr_service.py # Position tracking via OCR
│   ├── click_target_tracker.py   # Target blacklisting
│   └── __init__.py
│
├── models/                       # Data Models
│   ├── config.py                 # JSON configuration loader
│   ├── ui_elements.py            # UIElement, UIElementGrid
│   └── __init__.py
│
├── utils/                        # Helper Utilities
│   ├── coordinate_helpers.py     # CoordinateResolver
│   ├── timing_helpers.py         # TimingHelper
│   ├── color_helpers.py          # Color conversion utilities
│   ├── template_helpers.py       # Template matching utilities
│   └── __init__.py
│
├── scripts/                      # Example Bot Implementations
│   ├── afk/
│   │   ├── nmz_afk.py            # Nightmare Zone AFK bot
│   │   └── __init__.py
│   ├── bankstanding/
│   │   ├── bankstanding_flax.py  # Manual herb cleaning bot
│   │   ├── bankstander_example.py
│   │   └── __init__.py
│   ├── bosses/
│   │   ├── vorkath_bot.py
│   │   ├── zulrah.py             # Zulrah boss bot
│   │   └── __init__.py
│   ├── combat/
│   │   ├── basic_npc_killer.py   # Generic NPC killer
│   │   ├── green_dragons_state.py
│   │   └── __init__.py
│   ├── skills/
│   │   ├── mining_bot.py
│   │   └── __init__.py
│   └── tests/
│       ├── comprehensive_state_bot_test.py
│       └── __init__.py
│
├── fonts/                        # OCR font templates
├── images/                       # Template images
│   ├── bot/                      # Bot-specific templates
│   ├── ui/                       # UI element templates
│   └── items/                    # Item templates
│
├── constants.py                  # Global constants, enums, types
├── main.py                       # Application entry point
└── __main__.py                   # python -m osrsbot entry point
```

---

## Core Framework Components

### Bot Base Class

**File:** [`src/osrsbot/core/base_bot.py`](../src/osrsbot/core/base_bot.py)

```python
class Bot(ABC):
    """Abstract base class for all bot scripts.

    Provides:
    - Dependency injection (interface, state, actions, config)
    - Run loop with error handling
    - Exit key support
    - Status UI updates
    - Logging infrastructure
    """

    def __init__(
        self,
        interface: GameInterface,
        state: GameState,
        actions: GameActions,
        config: Config,
        script_name: str = "Base Bot",
        enable_exit_key: bool = False,
        enable_status_ui: bool = False,
    ):
        self.interface = interface      # Window management
        self.state = state              # Game state queries (read)
        self.actions = actions          # Game commands (write)
        self.config = config            # Configuration
        self.script_name = script_name
        self._exit_requested = False
        self._enable_exit_key = enable_exit_key
        self._enable_status_ui = enable_status_ui

    @abstractmethod
    def run_cycle(self, bank_location: str, run_number: int) -> None:
        """Implement bot logic in subclass.

        Called once per run. Should contain complete bot cycle logic.
        """
        pass

    def run(self, bank_location: str = "varrock", runs: int = 1) -> None:
        """Execute bot for N runs with error handling."""
        logger.info(f"Starting {self.script_name} - {runs} runs")

        for run in range(runs):
            if self._exit_requested:
                logger.info("Exit requested by user")
                break

            try:
                logger.info(f"Run {run + 1}/{runs}")
                self.run_cycle(bank_location, run)
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                raise
            except Exception as e:
                logger.error(f"Run {run + 1} failed: {e}", exc_info=True)

        logger.info(f"{self.script_name} completed")
```

**Key Methods:**

- `run_cycle(bank_location, run_number)` - **Abstract method** - Subclass implements bot logic
- `run(bank_location, runs)` - Main execution loop with error handling
- `_check_exit_requested()` - Check for 'q' key press
- `_update_ui(state, action)` - Update console status line
- `_teleport_and_bank(bank_location)` - Reusable banking helper

**Usage Example:**

```python
class MySimpleBot(Bot):
    def run_cycle(self, bank_location, run_number):
        # Bot logic here
        if self.state.inventory_full():
            self.actions.click_banker()
```

---

### State Machine Bot

**File:** [`src/osrsbot/core/state_machine_bot.py`](../src/osrsbot/core/state_machine_bot.py)

```python
class StateMachineBot(Bot):
    """Base class for state-driven bots with retry logic and transitions.

    Features:
    - Automatic state transitions based on results
    - Retry logic with exponential backoff
    - Timeout handling with failover states
    - State history tracking (last 100 entries)
    - Anti-ban integration (breaks, micro-breaks, idle actions)
    - Debug UI support
    """

    def __init__(self, *args, debug_ui: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self._states: Optional[type[Enum]] = None
        self._state_metadata: Dict[Enum, StateMetadata] = {}
        self._transitions: List[StateTransition] = []
        self._current_state: Optional[Enum] = None
        self._state_history: deque = deque(maxlen=100)
        self._retry_counts: Dict[Enum, int] = {}
        self._transition_map: Dict[Enum, List[StateTransition]] = {}
        self._debug_ui = debug_ui
```

**Abstract Methods (must implement in subclass):**

```python
def define_states(self) -> type[Enum]:
    """Return Enum class defining all states."""
    return MyStates

def define_state_metadata(self) -> Dict[Enum, StateMetadata]:
    """Return metadata configuration for each state."""
    return {
        MyStates.STATE1: StateMetadata(
            name="State 1",
            description="Does X",
            max_retries=3,
            timeout=60.0,
            failover_state=MyStates.RECOVERY
        ),
    }

def define_transitions(self) -> List[StateTransition]:
    """Return list of allowed state transitions."""
    return [
        StateTransition(MyStates.STATE1, MyStates.STATE2),
        StateTransition(
            MyStates.STATE2,
            MyStates.STATE3,
            condition=lambda: self.state.inventory_full()  # Guard
        ),
    ]

def get_initial_state(self) -> Enum:
    """Return starting state."""
    return MyStates.STATE1
```

**Execution Flow:**

```python
def run_cycle(self, bank_location: str, run_number: int) -> None:
    """Execute state machine."""
    if not self._states:
        self.initialize_state_machine()

    self._current_state = self.get_initial_state()
    states_executed = 0
    max_states = 1000  # Prevent infinite loops

    while states_executed < max_states:
        result = self._execute_state(self._current_state)
        next_state = self._get_next_state(self._current_state, result)

        if next_state:
            self._current_state = next_state
            states_executed += 1
        else:
            logger.info("No more states to execute - bot cycle complete")
            break
```

**State Handler Convention:**

State handlers are methods named `_handle_{state_name_lowercase}`:

```python
class MyBot(StateMachineBot):
    class MyStates(Enum):
        BANKING = "banking"
        COMBAT = "combat"

    def _handle_banking(self, context: StateExecutionContext) -> StateResult:
        """Handle BANKING state."""
        if self.actions.click_banker():
            return StateResult.SUCCESS
        return StateResult.FAILURE

    def _handle_combat(self, context: StateExecutionContext) -> StateResult:
        """Handle COMBAT state."""
        if self.actions.attack_npc("npc_target"):
            return StateResult.SUCCESS
        return StateResult.RETRY  # Retry on failure
```

**Retry Logic:**

```python
def _execute_state(self, state: Enum) -> StateResult:
    """Execute state with retry logic."""
    metadata = self._state_metadata[state]
    handler = self._get_state_handler(state)

    retry_count = self._retry_counts.get(state, 0)

    while retry_count < metadata.max_retries:
        context = StateExecutionContext(
            current_state=state,
            retry_count=retry_count,
        )

        # Check timeout
        if context.has_timed_out(metadata.timeout):
            logger.warning(f"State {state.value} timed out")
            return StateResult.TIMEOUT

        # Execute handler
        result = handler(context)

        # Record history
        self._state_history.append(StateHistoryEntry(
            state=state,
            result=result,
            duration=context.elapsed_time,
            retry_count=retry_count,
        ))

        if result == StateResult.RETRY:
            retry_count += 1
            time.sleep(2 ** retry_count)  # Exponential backoff
            continue

        # Reset retry count on success
        self._retry_counts[state] = 0
        return result

    # Max retries exceeded
    logger.error(f"State {state.value} failed after {metadata.max_retries} retries")
    return StateResult.FAILURE
```

---

### Bankstander Bot Template

**File:** [`src/osrsbot/core/base_bankstander.py`](../src/osrsbot/core/base_bankstander.py)

```python
class BankstanderBot(StateMachineBot):
    """Reusable template for bankstander scripts.

    Provides complete state machine for:
    - IDLE: Wait for player ready
    - BANKING: Open bank, search items, withdraw
    - PROCESS: Process items (cleaning, alching, etc.) - ABSTRACT
    - DEPOSIT: Deposit processed items
    - RECOVERY: Error recovery
    """

    class BankstanderStates(Enum):
        IDLE = "idle"
        BANKING = "banking"
        PROCESS = "process"
        DEPOSIT = "deposit"
        RECOVERY = "recovery"

    def __init__(
        self,
        item_name: str,                   # "grimy toadflax"
        item_search_text: str,            # "toadflax" (for bank search)
        item_template: str,               # Path to item image
        item_search_threshold: float = 0.75,
        processed_item_name: Optional[str] = None,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._item_name = item_name
        self._item_search_text = item_search_text
        self._item_template = item_template
        self._item_search_threshold = item_search_threshold
        self._processed_item_name = processed_item_name or f"processed {item_name}"

    @abstractmethod
    def process_items(self, context: StateExecutionContext) -> StateResult:
        """Define what to do with items (cleaning, alching, etc).

        Subclass MUST implement this method.
        """
        pass

    # State handlers provided
    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        """Safety checks before starting."""
        # Implementation provided

    def _handle_banking(self, context: StateExecutionContext) -> StateResult:
        """Open bank, search, withdraw items."""
        # Implementation provided

    def _handle_process(self, context: StateExecutionContext) -> StateResult:
        """Delegate to subclass's process_items()."""
        return self.process_items(context)

    def _handle_deposit(self, context: StateExecutionContext) -> StateResult:
        """Deposit processed items."""
        # Implementation provided

    def _handle_recovery(self, context: StateExecutionContext) -> StateResult:
        """Recover from errors."""
        # Implementation provided
```

**Usage Example:**

**File:** [`src/osrsbot/scripts/bankstanding/bankstanding_flax.py`](../src/osrsbot/scripts/bankstanding/bankstanding_flax.py)

```python
class GrimyFlaxBot(BankstanderBot):
    """Manual herb cleaning bot using BankstanderBot template."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            item_name="grimy toadflax",
            item_search_text="toadflax",
            item_template=str(images_dir / "grimy_toadflax.PNG"),
            item_search_threshold=0.75,
            processed_item_name="cleaned toadflax",
            *args, **kwargs,
            script_name="Manual Cleaning Bankstander"
        )

    def process_items(self, context: StateExecutionContext) -> StateResult:
        """Click each inventory slot to clean herbs."""
        # Choose pattern (sequential, random, column-by-column)
        pattern = random.choice(["sequential", "random", "column"])

        if pattern == "sequential":
            slots = list(range(1, 29))
        elif pattern == "random":
            slots = list(range(1, 29))
            random.shuffle(slots)
        else:  # column
            slots = self._get_column_pattern()

        # Click each slot
        for slot in slots:
            if self._exit_requested:
                return StateResult.FAILURE

            self.actions.click_inventory_slot(slot, move_style="curved")
            self.actions.wait("short")

            # Micro-break chance (8%)
            if self.actions.anti_ban and self.actions.anti_ban.should_micro_break():
                self.actions.anti_ban.execute_micro_break()

        return StateResult.SUCCESS
```

---

## Dependency Injection System

### ScriptRunner

**File:** [`src/osrsbot/core/runner.py`](../src/osrsbot/core/runner.py)

**Purpose:** Centralized service initialization and dependency wiring.

**Initialization Order (CRITICAL):**

```python
class ScriptRunner:
    def __init__(self, window_title: str, config_file: str = "config.json"):
        """Initialize all services in dependency order."""

        # 1. Load configuration (everything depends on it)
        self.config = Config(config_file)

        # 2. Initialize game interface (window management)
        self.interface = GameInterface(self.config)

        # 3. Initialize mouse services (try Win32 → Interception → Standard)
        mouse_config = MouseConfig(
            min_speed=self.config.get("mouse.min_speed", default=0.2),
            max_speed=self.config.get("mouse.max_speed", default=0.6),
            overshoot_chance=self.config.get("mouse.overshoot_chance", default=0.15),
        )

        self.mouse = self._initialize_mouse_service(mouse_config)

        # 4. Initialize screen service (screenshot capture)
        self.screen = ScreenService(window_getter=self.interface.get_bounds)

        # 5. Initialize template matching (UI detection)
        self.template_service = TemplateMatchService()
        self.template_service.register_from_config(self.config)

        # 6. Initialize UI manager (element tracking)
        self.ui_manager = UIManager(self.template_service)
        self.ui_manager.sync_from_template_service()

        # 7. Initialize OCR (stat reading)
        self.ocr = TemplateOCRService()

        # 8. Initialize position tracking (RuneLite plugin or OCR fallback)
        self.status_socket = self._initialize_position_service()

        # 9. Initialize walker (depends on position tracking)
        walker_config = WalkerConfig(
            step_size=self.config.get("walker.step_size", default=5),
            max_path_length=self.config.get("walker.max_path_length", default=100),
        )
        self.walker = WalkerService(
            config=walker_config,
            status_socket=self.status_socket,
            mouse=self.mouse,
            screen=self.screen,
            interface=self.interface,
        )

        # 10. Initialize game state (reads) - depends on services
        self.state = GameState(
            self.interface,
            self.config,
            self.ocr,
            self.screen,
            self.template_service
        )

        # 11. Initialize anti-ban service
        self.anti_ban = AntiBanService(self.config)

        # 12. Initialize loot detection
        self.loot_detection = LootDetectionService(self.screen)

        # 13. Initialize utility helpers
        self.coord_resolver = CoordinateResolver(
            self.screen, self.config, self.template_service
        )
        self.timing = TimingHelper(self.config, self.anti_ban)

        # 14. Initialize game actions (writes) - LAST! Depends on all services
        self.actions = GameActions(
            self.mouse, self.screen, self.interface, self.config,
            self.template_service, self.anti_ban, self.loot_detection,
            coord_resolver=self.coord_resolver,
            timing_helper=self.timing,
            walker=self.walker,
            ui_manager=self.ui_manager,
        )

    def run_script(self, script, **kwargs):
        """Execute script (Bot class or function)."""
        if isinstance(script, type) and issubclass(script, Bot):
            # Inject dependencies into bot
            bot_instance = script(
                interface=self.interface,
                state=self.state,
                actions=self.actions,
                config=self.config,
                **kwargs
            )
            bot_instance.run(**kwargs)
        elif callable(script):
            # Function-based script
            script(self.interface, self.state, self.actions, self.config, **kwargs)
```

**Dependency Graph:**

```
Config
  ↓
GameInterface
  ↓
MouseService, ScreenService
  ↓
TemplateMatchService, OCRService, UIManager
  ↓
PositionService (StatusSocket/CoordinateOCR)
  ↓
WalkerService
  ↓
GameState (queries), AntiBanService, LootDetection
  ↓
Utilities (CoordinateResolver, TimingHelper)
  ↓
GameActions (commands) ← DEPENDS ON EVERYTHING
```

---

## CQRS Implementation

### Overview

**CQRS (Command Query Responsibility Segregation)** separates read operations (queries) from write operations (commands).

**Benefits:**
- Clear separation of concerns
- Commands cannot accidentally query state
- Queries have no side effects
- Easier to test and reason about

### Commands Layer (Write Operations)

**File:** [`src/osrsbot/commands/game_actions.py`](../src/osrsbot/commands/game_actions.py)

```python
class GameActions:
    """Facade for all game actions (write operations).

    Maintains backward compatibility while delegating to focused modules.
    """

    def __init__(
        self,
        mouse: MouseService,
        screen: ScreenService,
        interface: GameInterface,
        config: Config,
        template_service: TemplateMatchService = None,
        anti_ban_service = None,
        loot_detection_service = None,
        coord_resolver = None,
        timing_helper = None,
        walker = None,
        ui_manager = None,
    ):
        # Store services
        self.mouse = mouse
        self.screen = screen
        self.interface = interface
        self.config = config
        self.template_service = template_service
        self.anti_ban = anti_ban_service
        self.loot_detection = loot_detection_service
        self.coord_resolver = coord_resolver
        self.timing = timing_helper
        self.walker = walker
        self.ui_manager = ui_manager

        # Delegate to focused modules
        self.inventory = InventoryActions(
            mouse, coord_resolver, timing, anti_ban_service
        )
        self.combat = CombatActions(
            mouse, screen, coord_resolver, timing, config, anti_ban_service
        )
        self.bank = BankActions(
            mouse, self._get_bank_queries(), coord_resolver, timing
        )

    # Facade methods for backward compatibility
    def click_inventory_slot(self, slot_num: int, move_style: str = "curved") -> bool:
        """Click inventory slot (delegates to inventory module)."""
        return self.inventory.click_slot(slot_num, move_style)

    def attack_npc(self, npc_color_name: str, use_smart_targeting: bool = True) -> bool:
        """Attack NPC (delegates to combat module)."""
        return self.combat.attack_npc(npc_color_name, use_smart_targeting)

    def click_banker(self, banker_templates: List[str], threshold: float = 0.7) -> bool:
        """Click banker (delegates to bank module)."""
        return self.bank.click_banker(banker_templates, threshold)

    def wait(self, timing_type: str) -> None:
        """Wait with anti-ban variance (delegates to timing helper)."""
        self.timing.wait(timing_type)
```

#### InventoryActions Module

**File:** [`src/osrsbot/commands/inventory_actions.py`](../src/osrsbot/commands/inventory_actions.py)

```python
class InventoryActions:
    """Focused module for inventory operations."""

    def __init__(
        self,
        mouse: MouseService,
        coord_resolver: CoordinateResolver,
        timing: TimingHelper,
        anti_ban_service = None,
    ):
        self.mouse = mouse
        self.coords = coord_resolver
        self.timing = timing
        self.anti_ban = anti_ban_service

    def click_slot(self, slot_num: int, move_style: MovementStyle = "curved") -> bool:
        """Click inventory slot (1-28) using template detection with config fallback.

        Args:
            slot_num: Slot number (1-28)
            move_style: Mouse movement style

        Returns:
            True if click successful
        """
        # Resolve slot position (template detection → config fallback)
        pos = self.coords.resolve_inventory_slot(slot_num)
        if not pos:
            logger.error(f"Could not resolve inventory slot {slot_num}")
            return False

        rel_x, rel_y = pos
        abs_x, abs_y = self.coords.to_absolute(rel_x, rel_y)

        # Click with anti-ban variance
        return self.mouse.click_at(
            abs_x, abs_y,
            move_style=move_style,
            speed_multiplier=self.timing.get_mouse_speed_multiplier()
        )

    def ensure_open(self) -> bool:
        """Ensure inventory tab is open."""
        # Implementation

    def drop_item(self, slot: int, shift_drop: bool = False) -> bool:
        """Drop item from inventory."""
        # Implementation

    def drop_all_except(self, keep_slots: List[int], shift_drop: bool = True) -> int:
        """Drop all items except specified slots."""
        # Implementation
```

#### CombatActions Module

**File:** [`src/osrsbot/commands/combat_actions.py`](../src/osrsbot/commands/combat_actions.py)

```python
class CombatActions:
    """Focused module for combat operations."""

    def __init__(
        self,
        mouse: MouseService,
        screen: ScreenService,
        coord_resolver: CoordinateResolver,
        timing: TimingHelper,
        config: Config,
        anti_ban_service = None,
    ):
        self.mouse = mouse
        self.screen = screen
        self.coords = coord_resolver
        self.timing = timing
        self.config = config
        self.anti_ban = anti_ban_service
        self._target_tracker = ClickTargetTracker()

    def attack_npc(
        self,
        npc_color_name: str,
        use_smart_targeting: bool = True
    ) -> bool:
        """Attack NPC by color with smart targeting and blacklisting.

        Smart targeting:
        - Tracks recently clicked NPCs
        - Avoids clicking same target repeatedly
        - Auto-expires blacklist after 10 seconds

        Args:
            npc_color_name: Config color key (e.g., "npc_target")
            use_smart_targeting: Enable target tracking

        Returns:
            True if attack initiated
        """
        npc_color = self.config.get("colors", npc_color_name)

        # Find all NPCs with target color
        matches = self.screen.find_color(
            npc_color,
            tolerance=15,
            find_all=True  # Get all matches
        )

        if not matches:
            logger.debug("No NPCs found")
            return False

        # Smart targeting: filter out recently clicked
        if use_smart_targeting:
            valid_matches = [
                m for m in matches
                if not self._target_tracker.is_blacklisted(m.x, m.y)
            ]
            if not valid_matches:
                logger.debug("All targets recently clicked")
                return False
            matches = valid_matches

        # Click nearest NPC
        target = min(matches, key=lambda m: m.confidence)  # Closest to center

        # Blacklist this target
        if use_smart_targeting:
            self._target_tracker.add_target(target.x, target.y, duration=10.0)

        # Click NPC
        return self.mouse.click_at(
            target.x, target.y,
            move_style="curved",
            speed_multiplier=self.timing.get_mouse_speed_multiplier()
        )

    def eat(self, food_color_name: str) -> bool:
        """Click inventory food item."""
        # Implementation

    def drink_potion(self, potion_color_name: str) -> bool:
        """Click inventory potion item."""
        # Implementation
```

---

### Queries Layer (Read Operations)

**File:** [`src/osrsbot/queries/game_queries.py`](../src/osrsbot/queries/game_queries.py)

```python
class GameState:
    """Facade for game state queries (read operations).

    Provides read-only access to game state.
    No side effects - queries should not modify game state.
    """

    def __init__(
        self,
        interface: GameInterface,
        config: Config,
        ocr_service: TemplateOCRService,
        screen_service: ScreenService,
        template_service: TemplateMatchService,
    ):
        self._interface = interface
        self.config = config
        self.ocr_service = ocr_service
        self.screen = screen_service
        self.template_service = template_service

        # Initialize focused query modules
        self.combat_queries = CombatQueries(screen_service, config, template_service)
        self.stat_queries = StatQueries(screen_service, ocr_service, config)
        self.bank_queries = BankQueries(screen_service)
        self.inventory = InventoryState(template_service, screen_service, config)

    # Facade methods for backward compatibility
    def in_combat(self) -> bool:
        """Check if player is in combat."""
        return self.combat_queries.in_combat()

    def get_hp(self) -> Optional[int]:
        """Read HP via OCR."""
        return self.stat_queries.get_hp()

    def inventory_full(self, threshold: int = 27) -> bool:
        """Check if inventory has >= threshold items."""
        return self.inventory.is_full(threshold)
```

#### CombatQueries Module

**File:** [`src/osrsbot/queries/combat_queries.py`](../src/osrsbot/queries/combat_queries.py)

```python
class CombatQueries:
    """Focused module for combat state detection."""

    def __init__(
        self,
        screen: ScreenService,
        config: Config,
        template_service: TemplateMatchService,
    ):
        self.screen = screen
        self.config = config
        self.template_service = template_service

    def in_combat(self) -> bool:
        """Check if player is in combat.

        Uses pixel-based indicator check:
        - Reads pixel at combat indicator position
        - Compares against combat_indicator_green/red colors

        Returns:
            True if in combat
        """
        coord = self.config.get("coordinates", "checks", "combat_indicator")
        color = self.screen.get_pixel_color(coord["x"], coord["y"], relative=True)

        combat_green = self.config.get("colors", "combat_indicator_green")
        combat_red = self.config.get("colors", "combat_indicator_red")

        # Convert hex to RGB
        green_rgb = hex_to_rgb(combat_green)
        red_rgb = hex_to_rgb(combat_red)

        # Check if pixel matches combat colors (with tolerance)
        in_combat = (
            color_distance(color, green_rgb) < 20 or
            color_distance(color, red_rgb) < 20
        )

        return in_combat

    def click_success(self, tries: int = 3) -> bool:
        """Check if click was detected by game.

        Uses template matching on good_click_1/2/3/4 templates.
        """
        # Implementation
```

#### StatQueries Module

**File:** [`src/osrsbot/queries/stat_queries.py`](../src/osrsbot/queries/stat_queries.py)

```python
class StatQueries:
    """Focused module for stat reading via OCR."""

    def __init__(
        self,
        screen: ScreenService,
        ocr_service: TemplateOCRService,
        config: Config,
    ):
        self.screen = screen
        self.ocr = ocr_service
        self.config = config
        self._cache = {}  # Cache for performance

    def get_hp(self, force: bool = False) -> Optional[int]:
        """Read HP via OCR on HP orb region.

        Args:
            force: Skip cache and re-read

        Returns:
            HP value (0-99) or None if OCR failed
        """
        if not force and "hp" in self._cache:
            return self._cache["hp"]

        hp_region = self.config.get("coordinates", "ocr", "hp_region")
        img = self.screen.capture(region=hp_region, relative=True)

        # OCR with multiple colors (green/red orb)
        hp = self.ocr.extract_number(
            img,
            font_name="plain11",
            colors=[ORB_GREEN, ORB_RED]
        )

        if hp is not None:
            self._cache["hp"] = hp

        return hp

    def get_prayer(self, force: bool = False) -> Optional[int]:
        """Read prayer points via OCR."""
        # Implementation

    def get_run_energy(self, force: bool = False) -> Optional[int]:
        """Read run energy via OCR."""
        # Implementation
```

#### InventoryState Module

**File:** [`src/osrsbot/queries/inventory_queries.py`](../src/osrsbot/queries/inventory_queries.py)

```python
class InventoryState:
    """Focused module for inventory state detection."""

    def __init__(
        self,
        template_service: TemplateMatchService,
        screen_service: ScreenService,
        config: Config,
    ):
        self.template_service = template_service
        self.screen = screen_service
        self.config = config
        self.empty_slot_color = hex_to_rgb(
            config.get("inventory.empty_slot_color", default="#3E3529")
        )
        self._cache: Optional[InventorySnapshot] = None

    def is_full(self, threshold: int = 27) -> bool:
        """Check if inventory has >= threshold items.

        Uses pixel-based detection:
        - Check center of each inventory slot (1-28)
        - Compare pixel color against empty_slot_color
        - Count non-empty slots

        Args:
            threshold: Number of items to consider "full" (default 27)

        Returns:
            True if filled_slots >= threshold
        """
        filled_slots = 0

        for slot_num in range(1, 29):
            pos = self.config.get("coordinates", "inventory", f"slot_{slot_num}")
            if not pos:
                continue

            # Get pixel color at slot center
            color = self.screen.get_pixel_color(pos["x"], pos["y"], relative=True)

            # Compare against empty slot color
            if color_distance(color, self.empty_slot_color) > 30:
                filled_slots += 1

        return filled_slots >= threshold

    def get_empty_slots(self) -> List[int]:
        """Return list of empty slot numbers."""
        # Implementation

    def find_item(self, item_color: str) -> Optional[int]:
        """Find first inventory slot with matching color."""
        # Implementation
```

---

### CQRS Command/Query Flow Diagram

```
┌────────────────────────────────────────────────────┐
│                   Bot Layer                        │
│  actions.click_inventory_slot(5)                   │
│  if state.inventory_full():                        │
└────────┬───────────────────────┬───────────────────┘
         │ command                │ query
         ↓                        ↓
┌────────────────────┐  ┌─────────────────────┐
│  GameActions       │  │  GameState          │
│  (Commands)        │  │  (Queries)          │
└────────┬───────────┘  └─────────┬───────────┘
         │ delegates             │ delegates
         ↓                       ↓
┌────────────────────┐  ┌─────────────────────┐
│ InventoryActions   │  │ InventoryState      │
│ - click_slot()     │  │ - is_full()         │
│ - drop_item()      │  │ - get_empty_slots() │
└────────┬───────────┘  └─────────┬───────────┘
         │ uses                   │ uses
         ↓                        ↓
┌────────────────────────────────────────────┐
│          Services Layer                    │
│  MouseService  ScreenService  OCRService   │
└────────────────────────────────────────────┘
```

---

## Service Layer

### Service Responsibilities

| Service | Purpose | Key Methods | Dependencies |
|---------|---------|-------------|--------------|
| **MouseService** | Human-like mouse movement | `move_to()`, `click_at()`, movement styles | None |
| **Win32MouseService** | Windows SendInput alternative | Same as MouseService | pywin32 |
| **InterceptionMouseService** | Kernel-level mouse | Same as MouseService | interception-python |
| **ScreenService** | Screenshot & color detection | `capture()`, `find_color()`, `get_pixel_color()` | GameInterface (window bounds) |
| **TemplateMatchService** | UI element detection | `find_template()`, `register_template()` | None |
| **TemplateOCRService** | OCR stat reading | `extract_number()`, digit templates | pytesseract |
| **UIManager** | UI element tracking | `get_grid()`, `get_button()`, grid detection | TemplateMatchService |
| **AntiBanService** | Break scheduling & variance | `should_take_break()`, `execute_break()` | Config |
| **WalkerService** | Minimap navigation | `walk_to()`, A* pathfinding | StatusSocket, Mouse, Screen |
| **LootDetectionService** | Ground item detection | `find_loot()` | ScreenService |
| **StatusSocketService** | RuneLite integration | `get_position()`, socket communication | RuneLite plugin |
| **CoordinateOCRService** | Position tracking (fallback) | `get_position()`, OCR on coordinates | OCRService |

---

### MouseService

**File:** [`src/osrsbot/services/mouse_service.py`](../src/osrsbot/services/mouse_service.py)

```python
@dataclass
class MouseConfig:
    """Configuration for mouse behavior."""
    min_speed: float = 0.1          # Minimum movement duration
    max_speed: float = 0.5          # Maximum movement duration
    overshoot_chance: float = 0.15  # Probability of overshooting
    overshoot_distance: int = 20    # Overshoot pixels
    click_variance: int = 3         # Random offset on click (pixels)
    post_click_delay: Tuple[float, float] = (0.05, 0.15)  # Delay after click

class MouseService:
    """Human-like mouse movement with multiple movement styles."""

    def __init__(self, config: MouseConfig = None):
        self.config = config or MouseConfig()
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.0

    def move_to(
        self,
        x: int,
        y: int,
        style: MovementStyle = "curved",
        duration: Optional[float] = None,
        speed_multiplier: float = 1.0
    ) -> bool:
        """Move mouse with human-like patterns.

        Styles:
        - "instant": Immediate jump (no movement animation)
        - "linear": Straight line at constant speed
        - "curved": Bezier curve with control points (most human-like)
        - "overshoot": Move past target then back
        - "random": Randomly choose linear/curved/overshoot

        Args:
            x, y: Target screen coordinates (absolute)
            style: Movement style
            duration: Override movement duration (calculated if None)
            speed_multiplier: Speed variance (from anti-ban)

        Returns:
            True if successful
        """
        if style == "instant":
            pyautogui.moveTo(x, y, duration=0)
            return True

        # Calculate duration if not provided
        if duration is None:
            current_x, current_y = pyautogui.position()
            distance = math.hypot(x - current_x, y - current_y)
            base_duration = random.uniform(self.config.min_speed, self.config.max_speed)
            duration = (distance / 1000) * base_duration * speed_multiplier

        if style == "linear":
            pyautogui.moveTo(x, y, duration=duration)

        elif style == "curved":
            self._move_bezier(x, y, duration)

        elif style == "overshoot":
            self._move_with_overshoot(x, y, duration)

        elif style == "random":
            chosen_style = random.choice(["linear", "curved", "overshoot"])
            return self.move_to(x, y, chosen_style, duration, speed_multiplier)

        return True

    def click_at(
        self,
        x: int,
        y: int,
        button: str = "left",
        move_style: MovementStyle = "curved",
        speed_multiplier: float = 1.0
    ) -> bool:
        """Move to coordinate and click.

        Args:
            x, y: Target coordinates (absolute)
            button: Mouse button ("left", "right", "middle")
            move_style: Movement style
            speed_multiplier: Speed variance

        Returns:
            True if successful
        """
        # Add click variance (random offset)
        variance = self.config.click_variance
        x += random.randint(-variance, variance)
        y += random.randint(-variance, variance)

        # Move to target
        self.move_to(x, y, style=move_style, speed_multiplier=speed_multiplier)

        # Click
        pyautogui.click(button=button)

        # Post-click delay
        delay = random.uniform(*self.config.post_click_delay)
        time.sleep(delay)

        return True

    def _move_bezier(self, x: int, y: int, duration: float) -> None:
        """Move mouse along Bezier curve."""
        current_x, current_y = pyautogui.position()

        # Generate control points
        mid_x = (current_x + x) / 2 + random.randint(-50, 50)
        mid_y = (current_y + y) / 2 + random.randint(-50, 50)

        # Sample points along curve
        steps = max(int(duration * 60), 10)  # 60 FPS
        for i in range(steps + 1):
            t = i / steps

            # Quadratic Bezier: B(t) = (1-t)²P0 + 2(1-t)tP1 + t²P2
            bx = (1-t)**2 * current_x + 2*(1-t)*t * mid_x + t**2 * x
            by = (1-t)**2 * current_y + 2*(1-t)*t * mid_y + t**2 * y

            pyautogui.moveTo(int(bx), int(by))
            time.sleep(duration / steps)

    def _move_with_overshoot(self, x: int, y: int, duration: float) -> None:
        """Move past target then back (human-like correction)."""
        # Overshoot by random amount
        overshoot_dist = self.config.overshoot_distance
        angle = random.uniform(0, 2 * math.pi)
        overshoot_x = x + int(overshoot_dist * math.cos(angle))
        overshoot_y = y + int(overshoot_dist * math.sin(angle))

        # Move to overshoot point (70% of duration)
        self._move_bezier(overshoot_x, overshoot_y, duration * 0.7)

        # Correct to target (30% of duration)
        self._move_bezier(x, y, duration * 0.3)
```

---

### ScreenService

**File:** [`src/osrsbot/services/screen_service.py`](../src/osrsbot/services/screen_service.py)

```python
@dataclass
class ColorMatch:
    """Result of color detection."""
    x: int                          # Absolute screen X
    y: int                          # Absolute screen Y
    confidence: float               # Color similarity (0.0-1.0)
    color: Tuple[int, int, int]     # RGB tuple

class ScreenService:
    """Screenshot capture and color detection service."""

    def __init__(
        self,
        window_getter: Callable[[], Tuple[int, int, int, int]] = None
    ):
        """Initialize ScreenService.

        Args:
            window_getter: Function returning (x, y, width, height) of game window
        """
        self.window_getter = window_getter

    def capture(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        relative: bool = True
    ) -> Image.Image:
        """Capture screenshot or region.

        Args:
            region: (x, y, width, height) - relative to window if relative=True
            relative: If True, region is relative to game window

        Returns:
            PIL Image
        """
        if region and relative:
            # Convert to absolute screen coordinates
            win_x, win_y, _, _ = self.window_getter()
            abs_region = (
                win_x + region[0],
                win_y + region[1],
                region[2],
                region[3]
            )
            return pyautogui.screenshot(region=abs_region)
        elif region:
            return pyautogui.screenshot(region=region)
        else:
            # Full game window
            if self.window_getter:
                bounds = self.window_getter()
                return pyautogui.screenshot(region=bounds)
            return pyautogui.screenshot()

    def capture_grayscale(self) -> Optional[np.ndarray]:
        """Capture as grayscale numpy array (for template matching)."""
        img = self.capture()
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)

    def relative_to_absolute(self, x: int, y: int) -> Tuple[int, int]:
        """Convert window-relative coords to screen absolute coords."""
        if not self.window_getter:
            return (x, y)

        win_x, win_y, _, _ = self.window_getter()
        return (win_x + x, win_y + y)

    def get_pixel_color(
        self,
        x: int,
        y: int,
        relative: bool = True
    ) -> Tuple[int, int, int]:
        """Get RGB color at single pixel.

        Args:
            x, y: Coordinates
            relative: If True, coordinates are relative to window

        Returns:
            RGB tuple (r, g, b)
        """
        if relative:
            x, y = self.relative_to_absolute(x, y)

        img = pyautogui.screenshot(region=(x, y, 1, 1))
        return img.getpixel((0, 0))

    def find_color(
        self,
        color_hex: str,
        tolerance: int = 10,
        region: Optional[Tuple[int, int, int, int]] = None,
        find_all: bool = False
    ) -> Optional[ColorMatch] | List[ColorMatch]:
        """Find color on screen with tolerance.

        Args:
            color_hex: Hex color string (e.g., "#FF0000")
            tolerance: Color distance tolerance (0-255)
            region: Search region (relative to window)
            find_all: Return all matches (else return first)

        Returns:
            ColorMatch or List[ColorMatch] if find_all=True
        """
        img = self.capture(region=region, relative=True)
        img_array = np.array(img)

        # Convert hex to RGB
        target_rgb = hex_to_rgb(color_hex)

        # Find all pixels within tolerance
        matches = []
        height, width, _ = img_array.shape

        for y in range(height):
            for x in range(width):
                pixel_rgb = tuple(img_array[y, x])
                distance = color_distance(pixel_rgb, target_rgb)

                if distance <= tolerance:
                    # Convert to absolute screen coords
                    abs_x, abs_y = self.relative_to_absolute(x, y)
                    confidence = 1.0 - (distance / tolerance)

                    matches.append(ColorMatch(
                        x=abs_x,
                        y=abs_y,
                        confidence=confidence,
                        color=pixel_rgb
                    ))

                    if not find_all:
                        return matches[0]

        return matches if find_all else None
```

---

### AntiBanService

**File:** [`src/osrsbot/services/anti_ban_service.py`](../src/osrsbot/services/anti_ban_service.py)

```python
@dataclass
class SessionState:
    """Session-level state for anti-ban."""
    session_start_time: float
    actions_performed: int = 0
    last_break_time: float
    next_break_time: float = 0.0
    timing_variance: float = 1.0          # Session-level timing randomness (0.8-1.2x)
    mouse_speed_variance: float = 1.0     # Session-level speed randomness (0.9-1.1x)
    recent_actions: deque = deque(maxlen=10)

class BreakScheduler:
    """Schedules breaks with randomization."""

    def __init__(
        self,
        interval_min: int = 300,      # 5 minutes
        interval_max: int = 600,      # 10 minutes
        duration_min: int = 30,       # 30 seconds
        duration_max: int = 120,      # 2 minutes
    ):
        self.interval_min = interval_min
        self.interval_max = interval_max
        self.duration_min = duration_min
        self.duration_max = duration_max

    def schedule_next_break(self) -> float:
        """Schedule break in range [interval_min, interval_max] seconds from now."""
        interval = random.triangular(
            self.interval_min,
            self.interval_max,
            (self.interval_min + self.interval_max) / 2
        )
        return time.time() + interval

    def get_break_duration(self) -> float:
        """Get random break duration."""
        return random.triangular(
            self.duration_min,
            self.duration_max,
            (self.duration_min + self.duration_max) / 2
        )

class AntiBanService:
    """Behavioral randomization and break scheduling."""

    def __init__(self, config: Config):
        self.config = config

        # Load break settings
        breaks_config = config.get("anti_ban.breaks", default={})
        self.breaks_enabled = breaks_config.get("enabled", True)

        self.scheduler = BreakScheduler(
            interval_min=breaks_config.get("interval_seconds", [300, 600])[0],
            interval_max=breaks_config.get("interval_seconds", [300, 600])[1],
            duration_min=breaks_config.get("duration_seconds", [30, 120])[0],
            duration_max=breaks_config.get("duration_seconds", [30, 120])[1],
        )

        # Initialize session state
        self.session = SessionState(
            session_start_time=time.time(),
            last_break_time=time.time(),
            next_break_time=self.scheduler.schedule_next_break(),
            timing_variance=random.uniform(0.8, 1.2),        # Session-level timing
            mouse_speed_variance=random.uniform(0.9, 1.1),   # Session-level speed
        )

        logger.info(
            f"AntiBanService initialized: "
            f"breaks_enabled={self.breaks_enabled}, "
            f"timing_variance={self.session.timing_variance:.2f}x, "
            f"mouse_speed_variance={self.session.mouse_speed_variance:.2f}x"
        )

    def should_take_break(self) -> bool:
        """Check if scheduled break time reached."""
        if not self.breaks_enabled:
            return False

        return time.time() >= self.session.next_break_time

    def execute_break(self) -> None:
        """Take scheduled break."""
        duration = self.scheduler.get_break_duration()
        logger.info(f"Taking break for {duration:.1f} seconds")

        time.sleep(duration)

        # Update state
        self.session.last_break_time = time.time()
        self.session.next_break_time = self.scheduler.schedule_next_break()

        # Re-randomize session variances after break
        self.session.timing_variance = random.uniform(0.8, 1.2)
        self.session.mouse_speed_variance = random.uniform(0.9, 1.1)

        logger.info("Break complete - resuming bot")

    def should_micro_break(self) -> bool:
        """Check if micro-break should occur (8% chance per action)."""
        return random.random() < 0.08

    def execute_micro_break(self) -> None:
        """Take micro-break (100-500ms pause)."""
        duration = random.uniform(0.1, 0.5)
        time.sleep(duration)

    def should_idle_action(self) -> bool:
        """Check if idle action should occur (5% chance)."""
        return random.random() < 0.05

    def execute_idle_action(self, mouse: MouseService, actions = None) -> None:
        """Perform random idle action.

        Options:
        - Mouse jitter (small random movement)
        - Camera movement
        - Check inventory
        - Random right-click
        """
        action = random.choice([
            "mouse_jitter",
            "camera_movement",
            "check_inventory",
            "random_rightclick",
        ])

        if action == "mouse_jitter":
            current_x, current_y = pyautogui.position()
            offset_x = random.randint(-20, 20)
            offset_y = random.randint(-20, 20)
            mouse.move_to(current_x + offset_x, current_y + offset_y, style="curved")

        elif action == "camera_movement":
            # Middle mouse drag
            pyautogui.mouseDown(button="middle")
            time.sleep(random.uniform(0.1, 0.3))
            offset = random.randint(-50, 50)
            pyautogui.move(offset, offset, duration=random.uniform(0.2, 0.5))
            pyautogui.mouseUp(button="middle")

        elif action == "check_inventory" and actions:
            actions.inventory.ensure_open()

        elif action == "random_rightclick":
            pyautogui.click(button="right")
            time.sleep(random.uniform(0.2, 0.5))
            pyautogui.press("esc")

    def get_timing_variance(self) -> float:
        """Get session timing multiplier (0.8-1.2x)."""
        return self.session.timing_variance

    def get_mouse_speed_variance(self) -> float:
        """Get session speed multiplier (0.9-1.1x)."""
        return self.session.mouse_speed_variance

    def record_action(self, action_name: str) -> None:
        """Record action for pattern detection."""
        self.session.actions_performed += 1
        self.session.recent_actions.append({
            "action": action_name,
            "timestamp": time.time(),
        })
```

---

## State Machine Framework

### State Machine Data Structures

**File:** [`src/osrsbot/core/state_types.py`](../src/osrsbot/core/state_types.py)

```python
class StateResult(Enum):
    """Results of state execution."""
    SUCCESS = "success"      # Proceed to next state
    FAILURE = "failure"      # May retry or failover
    RETRY = "retry"          # Retry immediately
    SKIP = "skip"            # Skip to next
    TIMEOUT = "timeout"      # Transition to failover

@dataclass
class StateMetadata:
    """Configuration for individual state."""
    name: str
    description: str = ""
    max_retries: int = 3
    timeout: Optional[float] = None          # Seconds (None = no timeout)
    failover_state: Optional[Enum] = None    # Transition on failure

@dataclass
class StateTransition:
    """Defines transition between states."""
    from_state: Enum
    to_state: Enum
    condition: Optional[Callable[[], bool]] = None  # Optional guard condition

    def can_transition(self) -> bool:
        """Check if transition is allowed."""
        if self.condition is None:
            return True
        return bool(self.condition())

@dataclass
class StateHistoryEntry:
    """Execution record for one state."""
    state: Enum
    result: StateResult
    duration: float
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0
    error_message: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.result == StateResult.SUCCESS

    @property
    def failed(self) -> bool:
        return self.result in (StateResult.FAILURE, StateResult.TIMEOUT)

@dataclass
class StateExecutionContext:
    """Context passed to state handler."""
    current_state: Enum
    retry_count: int = 0
    start_time: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time

    def has_timed_out(self, timeout: Optional[float]) -> bool:
        if timeout is None:
            return False
        return self.elapsed_time >= timeout
```

### State Machine Helpers

**File:** [`src/osrsbot/core/state_helpers.py`](../src/osrsbot/core/state_helpers.py)

```python
def create_state_metadata(
    name: str,
    description: str = "",
    max_retries: int = 3,
    timeout: Optional[float] = None,
    failover_state: Optional[Enum] = None,
) -> StateMetadata:
    """Factory for StateMetadata with sensible defaults."""
    return StateMetadata(
        name=name,
        description=description,
        max_retries=max_retries,
        timeout=timeout,
        failover_state=failover_state,
    )

def build_metadata_dict(
    states_enum: type[Enum],
    configs: Dict[Enum, dict]
) -> Dict[Enum, StateMetadata]:
    """Build metadata dict from compact config.

    Example:
        metadata = build_metadata_dict(MyStates, {
            MyStates.COMBAT: {
                "name": "Combat",
                "timeout": 600.0,
                "failover": MyStates.RECOVERY
            }
        })
    """
    result = {}
    for state, config in configs.items():
        result[state] = create_state_metadata(
            name=config.get("name", state.value),
            description=config.get("description", ""),
            max_retries=config.get("max_retries", 3),
            timeout=config.get("timeout"),
            failover_state=config.get("failover"),
        )
    return result

def log_state_execution(handler_func):
    """Decorator to auto-log state entry/exit/result.

    Usage:
        @log_state_execution
        def _handle_combat(self, context: StateExecutionContext) -> StateResult:
            # State logic
            return StateResult.SUCCESS
    """
    @functools.wraps(handler_func)
    def wrapper(self, context: StateExecutionContext) -> StateResult:
        state_name = context.current_state.value
        logger.info(f"[STATE] Entering {state_name} (retry={context.retry_count})")

        start_time = time.time()
        try:
            result = handler_func(self, context)
            duration = time.time() - start_time
            logger.info(f"[STATE] {state_name} completed: {result.value} ({duration:.2f}s)")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[STATE] {state_name} crashed: {e} ({duration:.2f}s)", exc_info=True)
            return StateResult.FAILURE

    return wrapper
```

---

## Design Patterns

### 1. Dependency Injection Pattern

**Where:** [`src/osrsbot/core/runner.py`](../src/osrsbot/core/runner.py)

**Implementation:** Constructor injection with explicit initialization order

```python
class ScriptRunner:
    def __init__(self, window_title: str):
        # Initialize dependencies in correct order
        self.config = Config()
        self.interface = GameInterface(self.config)
        self.mouse = MouseService(mouse_config)
        self.screen = ScreenService(window_getter=self.interface.get_bounds)
        # ... more services ...
        self.state = GameState(self.interface, self.config, ...)
        self.actions = GameActions(self.mouse, self.screen, ...)

    def run_script(self, BotClass, **kwargs):
        # Inject dependencies into bot
        bot = BotClass(
            interface=self.interface,
            state=self.state,
            actions=self.actions,
            config=self.config,
        )
        bot.run(**kwargs)
```

**Benefits:**
- Single source of truth for initialization
- Explicit dependencies (no hidden coupling)
- Easy to mock for testing
- Clear initialization order

---

### 2. Facade Pattern

**Where:** [`src/osrsbot/commands/game_actions.py`](../src/osrsbot/commands/game_actions.py), [`src/osrsbot/queries/game_queries.py`](../src/osrsbot/queries/game_queries.py)

**Implementation:** Facade delegates to focused modules while maintaining backward compatibility

```python
class GameActions:
    """Facade for all game actions."""

    def __init__(self, ...services...):
        # Delegate to focused modules
        self.inventory = InventoryActions(...)
        self.combat = CombatActions(...)
        self.bank = BankActions(...)

    # Facade methods (backward compatibility)
    def click_inventory_slot(self, slot_num: int) -> bool:
        return self.inventory.click_slot(slot_num)

    def attack_npc(self, npc_color: str) -> bool:
        return self.combat.attack_npc(npc_color)

# Old code still works
actions.click_inventory_slot(1)

# New code uses modules directly
actions.inventory.click_slot(1)
```

**Benefits:**
- Simplifies complex subsystems
- Backward compatibility during refactoring
- Progressive migration path

---

### 3. State Machine Pattern

**Where:** [`src/osrsbot/core/state_machine_bot.py`](../src/osrsbot/core/state_machine_bot.py)

**Implementation:** Enum-based states with automatic transitions

```python
class StateMachineBot(Bot):
    def run_cycle(self):
        current_state = self.get_initial_state()

        while True:
            result = self._execute_state(current_state)
            next_state = self._get_next_state(current_state, result)

            if next_state:
                current_state = next_state
            else:
                break

# Subclass defines states
class MyBot(StateMachineBot):
    class MyStates(Enum):
        IDLE = "idle"
        COMBAT = "combat"
        LOOTING = "looting"

    def _handle_idle(self, context) -> StateResult:
        return StateResult.SUCCESS

    def _handle_combat(self, context) -> StateResult:
        if self.actions.attack_npc("target"):
            return StateResult.SUCCESS
        return StateResult.RETRY
```

**Benefits:**
- Clear state definitions
- Automatic retry/timeout handling
- State history tracking
- Testable state handlers

---

### 4. Template Method Pattern

**Where:** [`src/osrsbot/core/base_bot.py`](../src/osrsbot/core/base_bot.py)

**Implementation:** Base class defines execution skeleton, subclass implements specific logic

```python
class Bot(ABC):
    def run(self, bank_location, runs):
        """Template method - defines structure."""
        for run in range(runs):
            try:
                self.run_cycle(bank_location, run)  # Subclass implements
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"Run failed: {e}")

    @abstractmethod
    def run_cycle(self, bank_location, run_number):
        """Subclass implements specific logic."""
        pass

class MyBot(Bot):
    def run_cycle(self, bank_location, run_number):
        # Custom bot behavior
        pass
```

**Benefits:**
- Code reuse (error handling, logging in base class)
- Consistent execution flow
- Extension points for customization

---

### 5. Strategy Pattern

**Where:** [`src/osrsbot/services/mouse_service.py`](../src/osrsbot/services/mouse_service.py)

**Implementation:** Multiple movement algorithms selected at runtime

```python
class MouseService:
    def move_to(self, x, y, style="curved"):
        """Select movement strategy at runtime."""
        if style == "instant":
            pyautogui.moveTo(x, y, duration=0)
        elif style == "linear":
            pyautogui.moveTo(x, y, duration=duration)
        elif style == "curved":
            self._move_bezier(...)
        elif style == "overshoot":
            self._move_with_overshoot(...)

# Usage
mouse.move_to(100, 100, style="curved")    # Use curve strategy
mouse.move_to(100, 100, style="instant")   # Use instant strategy
```

**Benefits:**
- Runtime algorithm selection
- Easy to add new strategies
- No complex conditionals

---

### 6. CQRS Pattern

**Where:** [`commands/`](../src/osrsbot/commands/) + [`queries/`](../src/osrsbot/queries/)

**Implementation:** Separate read (queries) from write (commands) operations

```python
# Commands (writes)
class GameActions:
    def click_inventory_slot(self, slot):
        """Write operation - changes game state."""
        pass

# Queries (reads)
class GameState:
    def inventory_full(self):
        """Read operation - no side effects."""
        pass

# Clean separation
actions.click_inventory_slot(1)  # Writes
if state.inventory_full():       # Reads
    actions.click_banker()       # Writes
```

**Benefits:**
- Clear intent (read vs write)
- No accidental side effects
- Easier to reason about

---

### 7. Adapter Pattern

**Where:** [`src/osrsbot/services/`](../src/osrsbot/services/) (Mouse service variants)

**Implementation:** Multiple implementations of same interface

```python
# Abstract interface
class MouseService:
    def move_to(self, x, y, style="curved"):
        pass

# Windows SendInput adapter
class Win32MouseService(MouseService):
    def move_to(self, x, y, style="curved"):
        # Windows-specific implementation
        pass

# Kernel-level adapter
class InterceptionMouseService(MouseService):
    def move_to(self, x, y, style="curved"):
        # Kernel implementation
        pass

# Selection at runtime
if use_win32:
    mouse = Win32MouseService(config)
else:
    mouse = MouseService(config)
```

**Benefits:**
- Platform abstraction
- Runtime selection
- Drop-in replacements

---

## Execution Flow

### Complete Bot Execution Flow

```
1. USER RUNS: python -m osrsbot
   ↓
2. main() in app/menu.py
   - Display menu with bot options
   - User selects bot #5 (Bankstander)
   ↓
3. ScriptRunner initialization (runner.py)
   a. Load Config("config.json")
   b. Create GameInterface(config)
   c. Create MouseService(mouse_config)
   d. Create ScreenService(window_getter=interface.get_bounds)
   e. Create TemplateMatchService()
   f. Create UIManager(template_service)
   g. Create TemplateOCRService()
   h. Create StatusSocketService() or CoordinateOCRService()
   i. Create WalkerService(position_service, mouse, screen, interface)
   j. Create GameState(interface, config, ocr, screen, templates)
   k. Create AntiBanService(config)
   l. Create LootDetectionService(screen)
   m. Create CoordinateResolver(screen, config, templates)
   n. Create TimingHelper(config, anti_ban)
   o. Create GameActions(all services...)
   ↓
4. runner.run_script(GrimyFlaxBot, runs=999)
   ↓
5. Bot instantiation
   bot = GrimyFlaxBot(
       interface=runner.interface,
       state=runner.state,
       actions=runner.actions,
       config=runner.config,
   )
   ↓
6. bot.run(bank_location="", runs=999)
   - For run in range(999):
     a. bot.run_cycle("", run)  # Calls StateMachineBot.run_cycle()
   ↓
7. StateMachineBot.run_cycle()
   - initialize_state_machine() [first call only]
   - Loop: execute states until completion
     a. _execute_state(current_state)
        - Get handler: _handle_{state_name_lowercase}
        - Execute handler with retry logic
        - Record history
     b. _get_next_state(current_state, result)
        - Check transition conditions
     c. Transition to next state
   ↓
8. State handler execution (e.g., _handle_banking in GrimyFlaxBot)
   - Access: self.actions (GameActions)
   - Access: self.state (GameState)
   - Return: StateResult.SUCCESS/FAILURE/RETRY/TIMEOUT
```

### Command Execution Flow Example

**User code:** `actions.click_inventory_slot(5)`

```
GameActions.click_inventory_slot(5)  [facade]
  ↓
InventoryActions.click_slot(5)  [focused module]
  ↓
coord_resolver.resolve_inventory_slot(5)
  - Try: Template detection
  - Fallback: Config coordinates
  - Returns: (rel_x, rel_y)
  ↓
coord_resolver.to_absolute(rel_x, rel_y)
  - Returns: (abs_x, abs_y) on screen
  ↓
mouse.click_at(abs_x, abs_y, move_style="curved",
               speed_multiplier=timing.get_mouse_speed_multiplier())
  - Apply anti-ban speed variance
  - Move mouse (Bezier curve)
  - Click
```

### Query Execution Flow Example

**User code:** `state.inventory_full()`

```
GameState.inventory_full()  [facade]
  ↓
InventoryState.is_full()  [focused module]
  ↓
self._get_cached_snapshot() or
self._detect_inventory_slots()
  - For each slot 1-28:
    - Get pixel color at slot center
    - Compare against empty_slot_color
    - Record filled/empty
  - Return count of filled slots
  ↓
Return: filled_slots >= threshold
```

---

## Configuration System

### Config File Structure

**File:** `config.json`

```json
{
  "account_name": "YourAccountName",
  "window_title": "RuneLite - ",
  "tesseract_path": "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",

  "colors": {
    "yellow_tile_marker": "#FFFF00",
    "purple_item_outline": "#7d00ff",
    "banker": "#00FFFF",
    "npc_target": "#00FFFF",
    "food_item": "#FF0000",
    "combat_indicator_green": "#00FF00",
    "combat_indicator_red": "#FF0000"
  },

  "coordinates": {
    "inventory": {
      "slot_1": {"x": 591, "y": 257},
      "slot_2": {"x": 633, "y": 257},
      ...
      "slot_28": {"x": 717, "y": 501}
    },
    "ui": {
      "settings": {"x": 689, "y": 506},
      "inventory_tab": {"x": 653, "y": 245},
      "prayer_tab": {"x": 565, "y": 245}
    },
    "ocr": {
      "hp_region": {"x": 10, "y": 50, "width": 30, "height": 20},
      "prayer_region": {"x": 10, "y": 85, "width": 30, "height": 20}
    },
    "checks": {
      "combat_indicator": {"x": 100, "y": 100}
    }
  },

  "timings": {
    "short": 0.5,
    "medium": 1.5,
    "long": 3.0,
    "teleport": 5.0
  },

  "anti_ban": {
    "breaks": {
      "enabled": true,
      "interval_seconds": [300, 600],
      "duration_seconds": [30, 120]
    }
  },

  "mouse": {
    "min_speed": 0.2,
    "max_speed": 0.6,
    "overshoot_chance": 0.15
  }
}
```

### Config Access

**File:** [`src/osrsbot/models/config.py`](../src/osrsbot/models/config.py)

```python
class Config:
    """JSON configuration loader with defaults."""

    def get(self, *keys, default=None):
        """Nested dict access with dot notation.

        Examples:
            config.get("colors", "banker")  → "#00FFFF"
            config.get("timings", "short")  → 0.5
            config.get("nonexistent", default="fallback")  → "fallback"
        """
        result = self.data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
                if result is None:
                    return default
            else:
                return default
        return result
```

---

## Extension Points

### Creating a New Bot

**1. Simple Bot (no state machine):**

```python
from osrsbot.core.base_bot import Bot

class MySimpleBot(Bot):
    def run_cycle(self, bank_location, run_number):
        """Implement bot logic."""
        # Your bot code here
        if self.state.inventory_full():
            self.actions.click_banker()
```

**2. State Machine Bot:**

```python
from osrsbot.core.state_machine_bot import StateMachineBot

class MyStateMachineBot(StateMachineBot):
    class MyStates(Enum):
        IDLE = "idle"
        COMBAT = "combat"
        LOOTING = "looting"

    def define_states(self):
        return self.MyStates

    def define_state_metadata(self):
        return {
            self.MyStates.IDLE: StateMetadata(
                name="Idle",
                max_retries=1,
            ),
            self.MyStates.COMBAT: StateMetadata(
                name="Combat",
                timeout=60.0,
                failover_state=self.MyStates.IDLE,
            ),
        }

    def define_transitions(self):
        return [
            StateTransition(self.MyStates.IDLE, self.MyStates.COMBAT),
            StateTransition(
                self.MyStates.COMBAT,
                self.MyStates.LOOTING,
                condition=lambda: not self.state.in_combat()
            ),
        ]

    def get_initial_state(self):
        return self.MyStates.IDLE

    def _handle_idle(self, context):
        return StateResult.SUCCESS

    def _handle_combat(self, context):
        if self.actions.attack_npc("npc_target"):
            return StateResult.SUCCESS
        return StateResult.RETRY

    def _handle_looting(self, context):
        if self.actions.loot_detection.find_loot():
            return StateResult.SUCCESS
        return StateResult.SKIP
```

**3. Bankstander Bot:**

```python
from osrsbot.core.base_bankstander import BankstanderBot

class MyBankstanderBot(BankstanderBot):
    def __init__(self, *args, **kwargs):
        super().__init__(
            item_name="raw lobster",
            item_search_text="lobster",
            item_template="path/to/lobster.png",
            processed_item_name="cooked lobster",
            *args, **kwargs,
            script_name="Lobster Cooker"
        )

    def process_items(self, context):
        """Cook all lobsters."""
        # Click fire
        # Click lobster
        # Wait for cooking
        return StateResult.SUCCESS
```

### Adding a New Service

```python
# services/my_service.py

class MyService:
    """Description of service purpose."""

    def __init__(self, config: Config, screen: ScreenService):
        self.config = config
        self.screen = screen

    def do_something(self) -> bool:
        """Service method."""
        # Implementation
        pass
```

**Register in runner.py:**

```python
# core/runner.py

class ScriptRunner:
    def __init__(self, window_title: str):
        # ... other services ...

        self.my_service = MyService(self.config, self.screen)

        # If Commands layer needs it, inject into GameActions
        self.actions = GameActions(
            ...,
            my_service=self.my_service,
        )
```

### Adding a New Command

```python
# commands/my_actions.py

class MyActions:
    """Focused module for specific actions."""

    def __init__(self, mouse, screen, config):
        self.mouse = mouse
        self.screen = screen
        self.config = config

    def my_action(self) -> bool:
        """Perform specific action."""
        # Implementation
        pass
```

**Register in GameActions:**

```python
# commands/game_actions.py

class GameActions:
    def __init__(self, ...):
        # ... other modules ...
        self.my_module = MyActions(mouse, screen, config)

    # Optional facade method
    def my_action(self) -> bool:
        return self.my_module.my_action()
```

---

## Summary

### Key Architectural Decisions

1. **Layered Architecture** - Clear separation of concerns with no upward dependencies
2. **Dependency Injection** - Single initialization point in `ScriptRunner`
3. **CQRS** - Separated read (queries) and write (commands) operations
4. **State Machine** - Reusable framework for complex bot logic
5. **Service-Oriented** - Infrastructure components as independent services
6. **Facade Pattern** - Backward compatibility while refactoring to focused modules
7. **Anti-Ban by Design** - Break scheduling, timing variance, micro-breaks built into framework

### File Organization

```
Application (menu.py)
    ↓ creates
Dependency Injection (runner.py)
    ↓ injects into
Bot Layer (base_bot.py, state_machine_bot.py, scripts/)
    ↓ uses
Commands (game_actions.py) + Queries (game_queries.py)
    ↓ delegates to
Services (mouse_service.py, screen_service.py, etc.)
```

### Extension Points

- **New Bot:** Extend `Bot` or `StateMachineBot`
- **New Service:** Add to `services/`, register in `runner.py`
- **New Command:** Add module to `commands/`, register in `GameActions`
- **New Query:** Add module to `queries/`, register in `GameState`

---

**End of Architecture Documentation**

For more information:
- [Quick Start Setup](QUICK_START_SETUP.md) - Installation guide
- [Beginner Developer Guide](BEGINNER_DEVELOPER_GUIDE.md) - Learning path
- [Basic NPC Killer Guide](BASIC_NPC_KILLER_GUIDE.md) - Example bot walkthrough
