# Bot Development Guide - OSRS Bot Framework

**Complete guide to creating new bots in the framework**

This guide teaches you how to design, implement, and test new bot scripts using the OSRS Bot framework. Whether you're building a simple gathering bot or a complex combat system, this guide covers everything you need to know.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Bot Types](#bot-types)
3. [State Machine Bots](#state-machine-bots)
4. [Bot Lifecycle](#bot-lifecycle)
5. [Using Services](#using-services)
6. [Navigation & Pathfinding](#navigation--pathfinding)
7. [Common Patterns](#common-patterns)
8. [Testing & Debugging](#testing--debugging)
9. [Best Practices](#best-practices)
10. [Complete Examples](#complete-examples)

---

## Quick Start

### Prerequisites

1. Framework installed (see [SETUP_GUIDE.md](../SETUP_GUIDE.md))
2. RuneLite running with Status Socket plugin (for walker features)
3. Config.json calibrated with your coordinates

### Creating Your First Bot

**1. Create bot file**: `src/osrsbot/scripts/my_first_bot.py`

```python
"""My First Bot - Simple resource gathering."""

from enum import Enum
from osrsbot.core.state_machine_bot import StateMachineBot, StateResult
from osrsbot.models.state_types import StateMetadata, StateExecutionContext


class MyBotStates(Enum):
    """Bot states."""
    IDLE = "idle"
    GATHERING = "gathering"
    COMPLETE = "complete"


class MyFirstBot(StateMachineBot):
    """Simple gathering bot."""

    def define_states(self) -> type[Enum]:
        """Define state enum."""
        return MyBotStates

    def define_state_metadata(self) -> dict[Enum, StateMetadata]:
        """Define state configuration."""
        return {
            MyBotStates.IDLE: StateMetadata(name="Idle"),
            MyBotStates.GATHERING: StateMetadata(
                name="Gathering",
                max_retries=3,
                timeout=60.0,
                failover_state=MyBotStates.COMPLETE
            ),
            MyBotStates.COMPLETE: StateMetadata(name="Complete"),
        }

    def define_transitions(self) -> dict[Enum, Enum]:
        """Define state transitions."""
        return {
            MyBotStates.IDLE: MyBotStates.GATHERING,
            MyBotStates.GATHERING: MyBotStates.COMPLETE,
        }

    def define_initial_state(self) -> Enum:
        """Starting state."""
        return MyBotStates.IDLE

    def handle_state(
        self, state: Enum, context: StateExecutionContext
    ) -> StateResult:
        """Execute state logic."""
        if state == MyBotStates.IDLE:
            return self._handle_idle(context)
        elif state == MyBotStates.GATHERING:
            return self._handle_gathering(context)
        elif state == MyBotStates.COMPLETE:
            return self._handle_complete(context)

    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        """Idle state handler."""
        self.logger.info("Bot started, moving to gathering")
        return StateResult.SUCCESS

    def _handle_gathering(self, context: StateExecutionContext) -> StateResult:
        """Gathering state handler."""
        # Click resource
        self.actions.click_color("resource_color")
        self.actions.wait("short")

        # Check if inventory full
        if self.state.is_inventory_full():
            self.logger.info("Inventory full, completing")
            return StateResult.SUCCESS

        return StateResult.RETRY

    def _handle_complete(self, context: StateExecutionContext) -> StateResult:
        """Complete state handler."""
        self.logger.info("Bot completed!")
        return StateResult.SUCCESS
```

**2. Register bot in menu**: `src/osrsbot/app/menu.py`

```python
from osrsbot.scripts.my_first_bot import MyFirstBot

# Add to bot list
AVAILABLE_BOTS = [
    # ... existing bots ...
    {
        "name": "My First Bot",
        "class": MyFirstBot,
        "description": "Simple resource gathering"
    },
]
```

**3. Run bot**:

```bash
python -m osrsbot
# Select "My First Bot" from menu
```

---

## Bot Types

### StateMachineBot (Recommended)

**Best for**: Complex workflows, multiple states, retry logic

**Pros**:
- ✅ Explicit state modeling
- ✅ Built-in retry and failover
- ✅ State history tracking
- ✅ Easier debugging

**Cons**:
- ❌ More boilerplate
- ❌ Overkill for very simple tasks

**Use when**:
- Bot has >2 distinct phases
- Need error handling and retries
- Want to track state history
- Building production bots

### Simple Function Bot

**Best for**: One-time scripts, testing, prototyping

**Pros**:
- ✅ Minimal boilerplate
- ✅ Quick to write
- ✅ Easy to understand

**Cons**:
- ❌ No built-in retry logic
- ❌ Manual error handling
- ❌ Hard to maintain as complexity grows

**Use when**:
- Simple sequential logic
- Throwaway scripts
- Rapid prototyping

**Example**:
```python
def simple_gatherer_bot(runner, bank_location, runs):
    """Simple function-based bot."""
    for run in range(runs):
        # Gather until full
        while not runner.state.is_inventory_full():
            runner.actions.click_color("resource")
            runner.actions.wait("short")

        # Bank
        runner.actions.walk_to_marker("bank")
        runner.actions.click_color("banker")
        # ... banking logic ...
```

---

## State Machine Bots

### State Machine Fundamentals

**State**: A distinct phase of bot execution (e.g., GATHERING, BANKING, COMBAT)

**Transition**: Movement from one state to another

**StateResult**: Outcome of state execution
- `SUCCESS`: State completed, transition to next
- `RETRY`: State incomplete, try again
- `FAILURE`: State failed, go to failover

### Anatomy of a State Machine Bot

```python
class MyBot(StateMachineBot):
    # 1. Define your states
    def define_states(self) -> type[Enum]:
        return MyBotStates  # Your Enum class

    # 2. Configure each state
    def define_state_metadata(self) -> dict[Enum, StateMetadata]:
        return {
            MyBotStates.WORKING: StateMetadata(
                name="Working",
                max_retries=5,      # How many RETRY results before failure
                timeout=300.0,       # Max time in state (seconds)
                failover_state=MyBotStates.IDLE  # Where to go on failure
            ),
        }

    # 3. Define state flow
    def define_transitions(self) -> dict[Enum, Enum]:
        return {
            MyBotStates.IDLE: MyBotStates.WORKING,
            MyBotStates.WORKING: MyBotStates.COMPLETE,
        }

    # 4. Set starting state
    def define_initial_state(self) -> Enum:
        return MyBotStates.IDLE

    # 5. Implement state handlers
    def handle_state(self, state, context) -> StateResult:
        if state == MyBotStates.WORKING:
            return self._handle_working(context)
        # ... other states ...

    def _handle_working(self, context) -> StateResult:
        # State logic here
        if work_done:
            return StateResult.SUCCESS  # → Next state
        if need_retry:
            return StateResult.RETRY    # → Try again
        if critical_error:
            return StateResult.FAILURE  # → Failover state
```

### State Execution Context

Every state handler receives a `StateExecutionContext`:

```python
@dataclass
class StateExecutionContext:
    state: Enum          # Current state
    run_number: int      # Bot run iteration (1, 2, 3...)
    bank_location: str   # Bank location from user
    attempt: int         # Retry attempt (0 = first try)
```

**Using context**:

```python
def _handle_banking(self, context) -> StateResult:
    self.logger.info(f"Banking (run {context.run_number}, attempt {context.attempt})")

    # Use bank_location
    bank = context.bank_location
    self.actions.walk_to_marker(bank)

    # Check if this is a retry
    if context.attempt > 0:
        self.logger.warning("Retrying banking...")

    # Your logic here...
```

### State Metadata Options

```python
StateMetadata(
    name: str,                          # Display name for logging
    max_retries: int = 3,               # Max RETRY results before failure
    timeout: Optional[float] = None,    # Max seconds in state
    failover_state: Optional[Enum] = None,  # Where to go on failure
    description: str = "",              # Optional description
)
```

**Examples**:

```python
# Critical state with strict retry limit
StateMetadata(
    name="Combat",
    max_retries=5,
    timeout=300.0,  # 5 minutes max
    failover_state=States.RECOVERY
)

# Safe state with no failover (will exit bot on failure)
StateMetadata(
    name="Banking",
    max_retries=3,
    timeout=60.0
)

# Terminal state (never retries or fails)
StateMetadata(name="Complete")
```

### Transition Patterns

#### Linear Flow
```python
IDLE → GATHERING → BANKING → COMPLETE
```

```python
def define_transitions(self):
    return {
        States.IDLE: States.GATHERING,
        States.GATHERING: States.BANKING,
        States.BANKING: States.COMPLETE,
    }
```

#### Loop Pattern
```python
IDLE → GATHERING → BANKING → GATHERING → ...
```

```python
def define_transitions(self):
    return {
        States.IDLE: States.GATHERING,
        States.GATHERING: States.BANKING,
        States.BANKING: States.GATHERING,  # Loop back
    }
```

#### Conditional Transitions
```python
def _handle_gathering(self, context) -> StateResult:
    if self.state.is_inventory_full():
        # Manually transition to banking
        return StateResult.SUCCESS  # Will follow transition map

    # Keep gathering
    self.actions.click_color("resource")
    return StateResult.RETRY
```

#### Recovery Pattern
```python
IDLE → COMBAT → (if fail) → RECOVERY → BANKING → IDLE
```

```python
# In state metadata
States.COMBAT: StateMetadata(
    name="Combat",
    max_retries=3,
    failover_state=States.RECOVERY  # Go here on failure
)

# Transitions
def define_transitions(self):
    return {
        States.IDLE: States.COMBAT,
        States.COMBAT: States.BANKING,  # Normal flow
        States.RECOVERY: States.BANKING,  # Recovery flow
        States.BANKING: States.IDLE,
    }
```

---

## Bot Lifecycle

### Execution Flow

```
1. Bot instantiated (dependencies injected)
   ↓
2. run() called by ScriptRunner
   ↓
3. For each run (1 to N):
   ├─> run_cycle() called
   │   ├─> State machine initialized
   │   ├─> States executed in sequence
   │   │   ├─> handle_state() called
   │   │   ├─> Process StateResult
   │   │   └─> Transition to next state
   │   └─> Anti-ban checks
   └─> Cycle complete
   ↓
4. All runs complete
   ↓
5. Bot finished
```

### run_cycle() Execution

```python
def run_cycle(self, bank_location: str, run_number: int):
    """Executed once per bot run."""

    # 1. Initialize state machine (first run only)
    if not self._state_machine_initialized:
        self._initialize_state_machine()

    # 2. Execute state machine
    while not self._is_terminal_state(self._current_state):
        # Get state metadata
        metadata = self._state_metadata[self._current_state]

        # Create context
        context = StateExecutionContext(
            state=self._current_state,
            run_number=run_number,
            bank_location=bank_location,
            attempt=attempt
        )

        # Execute state handler (with retries)
        result = self.handle_state(self._current_state, context)

        # Process result
        if result == StateResult.SUCCESS:
            self._current_state = self._transitions[self._current_state]
        elif result == StateResult.RETRY:
            attempt += 1
            if attempt >= metadata.max_retries:
                self._current_state = metadata.failover_state
        elif result == StateResult.FAILURE:
            self._current_state = metadata.failover_state

        # Anti-ban checks
        if self.anti_ban.should_take_break():
            self.anti_ban.take_scheduled_break()
```

---

## Using Services

### Accessing Services

Services are available via `self` in bot classes:

```python
class MyBot(StateMachineBot):
    def _handle_gathering(self, context):
        # Mouse service
        self.mouse.move_to(x, y)
        self.mouse.click_at(x, y)

        # Screen service
        match = self.screen.find_color("#ff0000")

        # OCR service
        hp = self.ocr.read_digits(screenshot)

        # GameActions (high-level)
        self.actions.click_color("dragon")
        self.actions.wait("short")

        # GameState (queries)
        is_full = self.state.is_inventory_full()
        in_combat = self.state.is_in_combat()
```

### GameActions (Commands)

**File**: `src/osrsbot/commands/game_actions.py`

High-level game actions that combine multiple services.

```python
# Click coordinate from config
self.actions.click_coordinate("ui.bank_deposit_all")

# Click by color
self.actions.click_color("green_dragon", tolerance=5)

# Walk to minimap marker
self.actions.walk_to_marker("bank")

# Walk to world coordinate (NEW)
self.actions.walk_to_world_coordinate(3185, 3448)

# Follow path (NEW)
path = [(3165, 3486), (3185, 3448)]
self.actions.walk_path(path)

# Wait with timing variance
self.actions.wait("short")   # 0.4-0.7s
self.actions.wait("medium")  # 0.8-1.3s
self.actions.wait("long")    # 2.5-3.8s
```

### GameState (Queries)

**File**: `src/osrsbot/queries/game_queries.py`

Read-only queries for game state.

```python
# Inventory
is_full = self.state.is_inventory_full()

# Combat
in_combat = self.state.is_in_combat()

# Health (OCR)
current_hp = self.state.get_hp()
if current_hp and current_hp < 50:
    # Low HP logic
```

---

## Navigation & Pathfinding

### Minimap Navigation (Basic)

Uses color-based markers on minimap.

```python
# Walk to marker (yellow tile marker)
self.actions.walk_to_marker("bank")

# Custom marker color
self.actions.click_color("custom_marker")
```

**Requirements**:
- Marker placed in-game (yellow tile marker)
- Marker color in config.json

### World Coordinate Navigation (Advanced)

Uses RuneLite Status Socket plugin for precise navigation.

```python
# Walk to single coordinate
success = self.actions.walk_to_world_coordinate(3185, 3448)
if not success:
    self.logger.error("Failed to reach bank")
    return StateResult.FAILURE

# Follow predefined path
ge_to_bank_path = [
    (3165, 3486),  # GE
    (3167, 3472),
    (3185, 3436),
    (3185, 3448)   # Bank
]
success = self.actions.walk_path(ge_to_bank_path)
```

**Requirements**:
- RuneLite Status Socket plugin installed
- `status_socket.enabled: true` in config

**Advantages**:
- ✅ Works regardless of camera angle
- ✅ More accurate than color-based
- ✅ Can follow complex paths
- ✅ Real-time arrival detection

---

## Common Patterns

### Pattern 1: Gather Until Full

```python
def _handle_gathering(self, context) -> StateResult:
    """Gather resources until inventory full."""

    # Check if done
    if self.state.is_inventory_full():
        self.logger.info("Inventory full, moving to banking")
        return StateResult.SUCCESS

    # Find and click resource
    resource = self.screen.find_color("#00ffff")
    if not resource:
        self.logger.warning("Resource not found")
        return StateResult.RETRY

    # Click resource
    self.mouse.click_at(resource.x, resource.y)
    self.actions.wait("short")

    # Continue gathering
    return StateResult.RETRY
```

### Pattern 2: Banking

```python
def _handle_banking(self, context) -> StateResult:
    """Bank inventory."""

    # Walk to bank
    bank_location = context.bank_location
    self.actions.walk_to_marker(bank_location)
    self.actions.wait("medium")

    # Click banker
    banker = self.screen.find_color("#00FFFF")  # Cyan NPC outline
    if not banker:
        self.logger.error("Banker not found")
        return StateResult.RETRY

    self.mouse.click_at(banker.x, banker.y)
    self.actions.wait("medium")

    # Deposit all
    self.actions.click_coordinate("ui.bank_deposit_all")
    self.actions.wait("short")

    # Close bank
    self.actions.click_coordinate("ui.bank_close")
    self.actions.wait("short")

    return StateResult.SUCCESS
```

### Pattern 3: Combat Loop

```python
def _handle_combat(self, context) -> StateResult:
    """Combat until low HP or inventory full."""

    # Check exit conditions
    hp = self.state.get_hp()
    if hp and hp < 30:
        self.logger.warning("Low HP, retreating")
        return StateResult.SUCCESS

    if self.state.is_inventory_full():
        self.logger.info("Inventory full")
        return StateResult.SUCCESS

    # If not in combat, find target
    if not self.state.is_in_combat():
        target = self.screen.find_color("#00ffff")  # Green NPC
        if target:
            self.mouse.click_at(target.x, target.y)
            self.actions.wait("short")
        return StateResult.RETRY

    # In combat, wait
    self.actions.wait("medium")
    return StateResult.RETRY
```

### Pattern 4: Potion Management

```python
def _handle_potions(self, context) -> StateResult:
    """Drink potions if needed."""

    # Check if potion needed
    hp = self.state.get_hp()
    if hp and hp < 60:
        # Find food in inventory
        food_slot = self.template_service.find_in_grid("inventory", 0, 0)
        if food_slot:
            self.logger.info("Eating food")
            self.mouse.click_at(*food_slot)
            self.actions.wait("short")

    # Drink super combat
    combat_pot = self.screen.find_color("#1e6c0e", region=inventory_region)
    if combat_pot:
        self.logger.info("Drinking super combat")
        self.mouse.click_at(combat_pot.x, combat_pot.y)
        self.actions.wait("short")

    return StateResult.SUCCESS
```

### Pattern 5: Recovery State

```python
def _handle_recovery(self, context) -> StateResult:
    """Recovery state after failure."""

    self.logger.warning("Entering recovery state")

    # Stop combat
    if self.state.is_in_combat():
        self.logger.info("Escaping combat")
        self.actions.walk_to_marker("safe_spot")
        self.actions.wait("long")

    # Teleport to safety
    self.logger.info("Teleporting to safety")
    teleport_slot = self.template_service.find_in_grid("inventory", 6, 3)
    if teleport_slot:
        self.mouse.click_at(*teleport_slot)
        self.actions.wait("teleport")

    return StateResult.SUCCESS
```

---

## Testing & Debugging

### Logging

```python
import logging

class MyBot(StateMachineBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)

    def _handle_gathering(self, context):
        self.logger.info("Starting gathering phase")
        self.logger.debug(f"Attempt {context.attempt}")
        self.logger.warning("Resource not found")
        self.logger.error("Critical error occurred")
```

### Test Bot Template

Create a test state to validate bot features:

```python
class TestMyBotStates(Enum):
    TEST_NAVIGATION = "test_navigation"
    TEST_COMBAT = "test_combat"
    TEST_BANKING = "test_banking"

class TestMyBot(StateMachineBot):
    def _handle_test_navigation(self, context):
        """Test navigation systems."""
        # Test minimap walking
        self.logger.info("TEST 1: Minimap navigation")
        self.actions.walk_to_marker("test_marker")

        # Test world coordinates
        self.logger.info("TEST 2: World coordinate navigation")
        success = self.actions.walk_to_world_coordinate(3200, 3400)

        return StateResult.SUCCESS
```

### Dry Run Mode

Test without actually performing actions:

```python
class MyBot(StateMachineBot):
    def __init__(self, *args, dry_run=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.dry_run = dry_run

    def _handle_gathering(self, context):
        if self.dry_run:
            self.logger.info("[DRY RUN] Would click resource")
            return StateResult.SUCCESS

        # Normal logic
        self.actions.click_color("resource")
```

### State History Tracking

State machine automatically tracks history:

```python
# Access state history
print(self._state_history)
# [(States.IDLE, 0.5s), (States.GATHERING, 45.2s), ...]

# Get time in state
start_time = time.time()
# ... state logic ...
duration = time.time() - start_time
self.logger.info(f"State took {duration:.2f}s")
```

---

## Best Practices

### Design

1. **Keep states focused**: Each state should have one clear responsibility
2. **Use failover states**: Always provide recovery path for critical states
3. **Plan state diagram**: Draw your state flow before coding
4. **Limit state transitions**: Avoid complex branching, use linear flow when possible

### Error Handling

```python
# Good: Check return values
def _handle_banking(self, context):
    banker = self.screen.find_color("#00FFFF")
    if not banker:
        self.logger.error("Banker not found")
        return StateResult.RETRY  # Will retry up to max_retries

    success = self.mouse.click_at(banker.x, banker.y)
    if not success:
        return StateResult.RETRY

# Bad: Assume success
def _handle_banking(self, context):
    banker = self.screen.find_color("#00FFFF")
    self.mouse.click_at(banker.x, banker.y)  # Crashes if banker is None
```

### Performance

1. **Cache expensive operations**: Template matching, color searches
2. **Use regions**: Limit search areas for screen operations
3. **Avoid unnecessary waits**: Only wait when needed
4. **Batch operations**: Multiple color searches on same screenshot

```python
# Good: Single screenshot, multiple searches
screenshot = self.screen.capture_full()
resource = self.screen.find_color("#ff0000", screenshot=screenshot)
npc = self.screen.find_color("#00ffff", screenshot=screenshot)

# Bad: Multiple screenshots
resource = self.screen.find_color("#ff0000")  # Screenshot 1
npc = self.screen.find_color("#00ffff")       # Screenshot 2
```

### Maintainability

1. **Extract helper methods**: Break down complex state handlers
2. **Use constants**: Avoid magic numbers and strings
3. **Document state logic**: Explain why, not what
4. **Version your bots**: Track changes over time

```python
# Constants
MAX_COMBAT_HP = 30
INVENTORY_FULL_SLOT = 27

# Helper methods
def _is_low_hp(self) -> bool:
    """Check if HP below combat threshold."""
    hp = self.state.get_hp()
    return hp is not None and hp < MAX_COMBAT_HP

def _handle_combat(self, context):
    # Use helpers
    if self._is_low_hp():
        return StateResult.SUCCESS
```

---

## Complete Examples

### Example 1: Simple Woodcutting Bot

```python
"""Woodcutting Bot - Chop trees until inventory full, then bank."""

from enum import Enum
from osrsbot.core.state_machine_bot import StateMachineBot, StateResult
from osrsbot.models.state_types import StateMetadata, StateExecutionContext


class WoodcuttingStates(Enum):
    IDLE = "idle"
    CHOPPING = "chopping"
    BANKING = "banking"
    COMPLETE = "complete"


class WoodcuttingBot(StateMachineBot):
    """Woodcutting bot implementation."""

    def define_states(self) -> type[Enum]:
        return WoodcuttingStates

    def define_state_metadata(self) -> dict[Enum, StateMetadata]:
        return {
            WoodcuttingStates.IDLE: StateMetadata(name="Idle"),
            WoodcuttingStates.CHOPPING: StateMetadata(
                name="Chopping",
                max_retries=5,
                timeout=300.0,
                failover_state=WoodcuttingStates.BANKING
            ),
            WoodcuttingStates.BANKING: StateMetadata(
                name="Banking",
                max_retries=3,
                timeout=60.0
            ),
            WoodcuttingStates.COMPLETE: StateMetadata(name="Complete"),
        }

    def define_transitions(self) -> dict[Enum, Enum]:
        return {
            WoodcuttingStates.IDLE: WoodcuttingStates.CHOPPING,
            WoodcuttingStates.CHOPPING: WoodcuttingStates.BANKING,
            WoodcuttingStates.BANKING: WoodcuttingStates.CHOPPING,
        }

    def define_initial_state(self) -> Enum:
        return WoodcuttingStates.IDLE

    def handle_state(self, state: Enum, context: StateExecutionContext) -> StateResult:
        if state == WoodcuttingStates.IDLE:
            return self._handle_idle(context)
        elif state == WoodcuttingStates.CHOPPING:
            return self._handle_chopping(context)
        elif state == WoodcuttingStates.BANKING:
            return self._handle_banking(context)
        elif state == WoodcuttingStates.COMPLETE:
            return self._handle_complete(context)

    def _handle_idle(self, context: StateExecutionContext) -> StateResult:
        self.logger.info("Starting woodcutting bot")
        return StateResult.SUCCESS

    def _handle_chopping(self, context: StateExecutionContext) -> StateResult:
        """Chop trees until inventory full."""

        # Check if inventory full
        if self.state.is_inventory_full():
            self.logger.info("Inventory full, going to bank")
            return StateResult.SUCCESS

        # Find tree
        tree = self.screen.find_color("#228B22", tolerance=10)
        if not tree:
            self.logger.warning("No tree found")
            return StateResult.RETRY

        # Click tree
        self.mouse.click_at(tree.x, tree.y)
        self.actions.wait("medium")

        # Wait for chopping to complete
        self.actions.wait("long")

        return StateResult.RETRY

    def _handle_banking(self, context: StateExecutionContext) -> StateResult:
        """Bank logs."""

        # Walk to bank
        self.actions.walk_to_marker("bank")
        self.actions.wait("medium")

        # Click banker
        banker = self.screen.find_color("#00FFFF")
        if not banker:
            self.logger.error("Banker not found")
            return StateResult.RETRY

        self.mouse.click_at(banker.x, banker.y)
        self.actions.wait("medium")

        # Deposit all
        self.actions.click_coordinate("ui.bank_deposit_all")
        self.actions.wait("short")

        # Close bank
        self.actions.click_coordinate("ui.bank_close")
        self.actions.wait("short")

        return StateResult.SUCCESS

    def _handle_complete(self, context: StateExecutionContext) -> StateResult:
        self.logger.info("Woodcutting complete!")
        return StateResult.SUCCESS
```

---

**Document Version**: 1.0
**Last Updated**: December 22, 2025
**Related Docs**: [ARCHITECTURE.md](ARCHITECTURE.md), [SERVICE_GUIDE.md](SERVICE_GUIDE.md), [FILE_RESPONSIBILITIES.md](FILE_RESPONSIBILITIES.md)
