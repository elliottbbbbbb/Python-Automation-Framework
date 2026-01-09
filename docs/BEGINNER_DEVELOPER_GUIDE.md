# Beginner Developer Guide - Learn Python by Building OSRS Bots

**Learn Python by creating automation scripts in a real framework**

This guide teaches Python fundamentals by building actual working bots. Start simple, learn as you go, and gradually understand the deeper layers of the framework.

---

## Philosophy: Learn by Building

Instead of learning Python syntax in isolation, you'll:
1. **Start with high-level abstractions** - Use the framework's easy APIs
2. **Build working bots immediately** - See results fast
3. **Gradually understand lower layers** - Learn as curiosity grows
4. **Read real production code** - Learn from examples

**No prior programming experience required.**

---

## Prerequisites Checklist

Before starting, make sure you have:

- [ ] **Python 3.10+** installed (get from [python.org](https://python.org))
- [ ] **Git** (optional, for cloning repo)
- [ ] **Code Editor** - VS Code, PyCharm, or any text editor
- [ ] **Terminal/Command Prompt** access
- [ ] **Administrator access** on your computer (for installing packages)
- [ ] **RuneLite** client installed (for running bots)
- [ ] **Tesseract OCR** installed ([Windows download](https://github.com/UB-Mannheim/tesseract/wiki))

**Optional but helpful:**
- [ ] GitHub account (for contributing later)
- [ ] Basic comfort with command line
- [ ] OSRS account (obviously!)

---

## Table of Contents

1. [Level 0: Your First Bot (30 minutes)](#level-0-your-first-bot)
2. [Level 1: Understanding the Code (1-2 hours)](#level-1-understanding-the-code)
3. [Level 2: Customizing Your Bot (2-4 hours)](#level-2-customizing-your-bot)
4. [Level 3: State Machines (1-2 days)](#level-3-state-machines)
5. [Level 4: Understanding Services (3-7 days)](#level-4-understanding-services)
6. [Level 5: Advanced Patterns (2-4 weeks)](#level-5-advanced-patterns)
7. [Learning Resources](#learning-resources)

---

## Level 0: Your First Bot (30 minutes)

**Goal:** Run a working bot without understanding the code yet.

> 💡 **Quick Setup:** If you just want to get running fast, see [QUICK_START_SETUP.md](QUICK_START_SETUP.md) for condensed instructions. Come back here after installation.

### Step 1: Set Up Environment

#### 1.1 Install Python

```bash
# Download from python.org - get version 3.10, 3.11, or 3.12
# During installation on Windows: CHECK "Add Python to PATH"
```

Verify installation:
```bash
python --version
# Should show: Python 3.10.x or higher
```

#### 1.2 Create Virtual Environment (Recommended)

**Why?** Keeps project dependencies isolated from other Python projects.

```bash
# Navigate to project directory
cd OSRS-Automation-Framework

# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate

# You should see (venv) in your terminal now
```

#### 1.3 Install the Package

```bash
# Make sure you're in OSRS-Automation-Framework directory
# and virtual environment is activated (you see "(venv)")

# Install in editable mode
pip install -e .

# The -e flag means "editable" - changes to code take effect immediately
# This reads pyproject.toml and installs all dependencies listed there
```

**What gets installed:**
- pyautogui (for mouse/keyboard control)
- opencv-python (for computer vision)
- pytesseract (for OCR text reading)
- numpy (for fast image processing)
- pillow (for image handling)
- rich (for pretty terminal output)
- ...and 10+ other packages

**Alternative (without virtual environment):**
```bash
# Not recommended, but works
pip install -e .

# Or without editable mode:
pip install .
```

### Step 2: Verify Installation

```bash
# Test that installation worked
python -c "import osrsbot; print('Installation successful!')"

# If you see "Installation successful!" you're good to go
# If you see an error, see Troubleshooting below
```

### Step 3: Run Existing Bot

```bash
# Start the bot menu
python -m osrsbot

# Select option 5: Manual Cleaning Bankstander
# Follow the prompts
```

**What just happened?**
- Python ran the `osrsbot` module
- The menu system started
- You selected a pre-built bot
- The bot executed its logic

**Don't worry about how it works yet. Just see that it works.**

---

### Troubleshooting Installation

**Problem: "No module named 'osrsbot'"**
```bash
# Solution 1: Make sure you're in the project directory
cd OSRS-Automation-Framework
pip install -e .

# Solution 2: Check Python version
python --version  # Should be 3.10 or higher

# Solution 3: Try with pip3 instead
pip3 install -e .
```

**Problem: "ERROR: Could not find a version that satisfies the requirement..."**
```bash
# Solution: Update pip first
python -m pip install --upgrade pip
pip install -e .
```

**Problem: On Windows - "Microsoft Visual C++ is required"**
```bash
# Some packages (like opencv) need C++ build tools
# Download and install from:
# https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

**Problem: "No module named 'pytesseract'"**
```bash
# Tesseract OCR needs to be installed separately (not just Python package)
# Windows: Download installer from https://github.com/UB-Mannheim/tesseract/wiki
# After installing, add to PATH or configure in config.json
```

**Problem: "Permission denied"**
```bash
# Solution: Use --user flag
pip install -e . --user
```

---

## Level 1: Understanding the Code (1-2 hours)

**Goal:** Read and understand a simple bot.

### The Simplest Bot: Bankstanding Flax

Open: `src/osrsbot/scripts/bankstanding/bankstanding_flax.py`

```python
"""
Manual Cleaning Bankstander - Simplified using BankstanderBot base class.

Cleans grimy toadflax by clicking each inventory slot.
"""

import logging
from osrsbot.core.state_types import StateExecutionContext, StateResult
from osrsbot.core.base_bankstander import BankstanderBot

logger = logging.getLogger(__name__)


class GrimyFlaxBot(BankstanderBot):
    """Bankstander that cleans grimy toadflax."""

    def __init__(self, *args, **kwargs):
        """Initialize the bot."""
        super().__init__(
            item_name="grimy toadflax",
            item_search_text="toadflax",
            item_template="path/to/toadflax.PNG",
            *args,
            **kwargs,
        )

    def process_items(self, context: StateExecutionContext) -> StateResult:
        """Click each inventory slot to clean herbs."""

        # Click each slot (1 through 28)
        for slot in range(1, 29):
            self.actions.click_inventory_slot(slot)
            self.actions.wait("micro")

        return StateResult.SUCCESS
```

### Breaking It Down (Line by Line)

```python
import logging
```
**What:** Imports Python's logging library
**Why:** Lets us print messages to help debug
**Learn:** `import` brings in external code we can use

```python
from osrsbot.core.base_bankstander import BankstanderBot
```
**What:** Imports the BankstanderBot base class
**Why:** We inherit from it to get banking logic for free
**Learn:** `from X import Y` brings specific things from modules

```python
class GrimyFlaxBot(BankstanderBot):
```
**What:** Creates a new bot class that inherits from BankstanderBot
**Why:** We get all the banking code without writing it
**Learn:** `class` defines a new type of object. `(BankstanderBot)` means "inherit from this"

```python
def __init__(self, *args, **kwargs):
```
**What:** The "constructor" - runs when bot is created
**Why:** Sets up initial configuration
**Learn:** `def` defines a function. `__init__` is special - it initializes objects

```python
super().__init__(
    item_name="grimy toadflax",
    ...
)
```
**What:** Calls the parent class's constructor
**Why:** Configures the base banking logic
**Learn:** `super()` refers to the parent class. We're passing configuration upward.

```python
def process_items(self, context):
```
**What:** The main logic - what to do with items
**Why:** This is the ONLY method you need to implement!
**Learn:** `self` refers to "this bot". `context` has information about the current run.

```python
for slot in range(1, 29):
```
**What:** Loop through numbers 1 to 28
**Why:** Inventory has 28 slots
**Learn:** `for X in Y:` repeats code. `range(1, 29)` generates 1, 2, 3...28

```python
self.actions.click_inventory_slot(slot)
```
**What:** Click the inventory slot
**Why:** Clicking herbs cleans them
**Learn:** `self.actions` is a service that handles game actions

```python
return StateResult.SUCCESS
```
**What:** Tell the framework we're done successfully
**Why:** The state machine needs to know if we succeeded/failed/should retry
**Learn:** `return` gives a value back to whoever called this function

### Python Concepts You Just Learned

✅ **Imports** - Bringing in code from other files
✅ **Classes** - Defining new types of objects
✅ **Inheritance** - Getting functionality from parent classes
✅ **Functions** - Reusable blocks of code
✅ **Loops** - Repeating actions
✅ **Objects** - Things that have data and methods
✅ **Return values** - Giving results back

**Not bad for 30 lines of code!**

---

## Level 2: Customizing Your Bot (2-4 hours)

**Goal:** Modify existing bots to do new things.

### Project 1: Customize the Herb Cleaner

**Task:** Make the bot click slots in random order instead of 1→28

```python
def process_items(self, context: StateExecutionContext) -> StateResult:
    """Click inventory slots in random order."""

    import random  # Import at top of function (or top of file)

    # Create list of slot numbers
    slots = list(range(1, 29))  # [1, 2, 3, ..., 28]

    # Shuffle them randomly
    random.shuffle(slots)  # Now slots = [14, 3, 27, 1, ...]

    # Click in randomized order
    for slot in slots:
        self.actions.click_inventory_slot(slot)
        self.actions.wait("micro")

    return StateResult.SUCCESS
```

**New concepts learned:**
- ✅ `import random` - Importing specific modules
- ✅ `list(range(...))` - Converting range to a list
- ✅ `random.shuffle()` - Randomizing a list
- ✅ Comments with `#` explain code

### Project 2: Create a Simple Fishing Bot

**Task:** Make a bot that clicks fish until inventory full

```python
"""Simple fishing bot - clicks fishing spot."""

from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_types import StateResult
from enum import Enum

class FishingStates(Enum):
    """Bot states."""
    FISHING = "fishing"
    COMPLETE = "complete"


class SimpleFishingBot(StateMachineBot):
    """Clicks fishing spot until inventory full."""

    def define_states(self) -> type[Enum]:
        return FishingStates

    def define_initial_state(self) -> Enum:
        return FishingStates.FISHING

    def _handle_fishing(self, context) -> StateResult:
        """Main fishing loop."""

        # Check if inventory is full
        if self.state.inventory_full():
            self.logger.info("Inventory full!")
            return StateResult.SUCCESS  # Move to next state

        # Find fishing spot (cyan color)
        spot = self.screen.find_color("#00FFFF")

        if spot:
            # Click the spot
            self.mouse.click_at(spot.x, spot.y)
            self.actions.wait("medium")

        # Keep fishing
        return StateResult.RETRY

    def _handle_complete(self, context) -> StateResult:
        """Fishing complete."""
        self.logger.info("Done fishing!")
        return StateResult.SUCCESS
```

**New concepts learned:**
- ✅ `Enum` - Define a set of named states
- ✅ `if/else` - Conditional logic
- ✅ `self.state.inventory_full()` - Querying game state
- ✅ `StateResult.RETRY` - Tell state machine to try again
- ✅ `self.logger.info()` - Logging messages

### Project 3: Add Configuration

**Task:** Make the fishing spot color configurable

```python
class SimpleFishingBot(StateMachineBot):
    """Clicks fishing spot until inventory full."""

    def __init__(self, spot_color="#00FFFF", *args, **kwargs):
        """
        Initialize fishing bot.

        Args:
            spot_color: Hex color of fishing spot (default cyan)
        """
        super().__init__(*args, **kwargs)
        self.spot_color = spot_color  # Save for later use

    def _handle_fishing(self, context) -> StateResult:
        # Use configured color instead of hardcoded
        spot = self.screen.find_color(self.spot_color)
        # ... rest of code
```

**New concepts learned:**
- ✅ Constructor parameters - Passing configuration
- ✅ `self.variable` - Storing data in the object
- ✅ Default values - `spot_color="#00FFFF"`
- ✅ Docstrings - `"""Documentation"""`

---

## Level 3: State Machines (1-2 days)

**Goal:** Understand how bots manage complex workflows.

### What is a State Machine?

Think of a state machine like a flowchart:

```
START
  ↓
[FISHING] ← Loop here until inventory full
  ↓ (when full)
[BANKING]
  ↓
[FISHING] ← Loop back
  ↓ (after 10 trips)
[COMPLETE]
```

**Each box is a "state". Arrows are "transitions".**

### Simple Combat Bot with States

```python
"""Combat bot with states."""

from enum import Enum
from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_types import StateResult, StateMetadata

class CombatStates(Enum):
    FIND_ENEMY = "find_enemy"
    ATTACK = "attack"
    COMBAT = "combat"
    LOOT = "loot"
    COMPLETE = "complete"


class SimpleCombatBot(StateMachineBot):
    """Kills enemies and loots."""

    def define_states(self):
        return CombatStates

    def define_state_metadata(self):
        """Configure each state."""
        return {
            CombatStates.FIND_ENEMY: StateMetadata(
                name="Find Enemy",
                max_retries=5,  # Try 5 times before giving up
            ),
            CombatStates.ATTACK: StateMetadata(
                name="Attack",
                max_retries=3,
            ),
            CombatStates.COMBAT: StateMetadata(
                name="Combat",
                timeout=60.0,  # Max 60 seconds
            ),
            CombatStates.LOOT: StateMetadata(
                name="Loot",
                max_retries=2,
            ),
            CombatStates.COMPLETE: StateMetadata(
                name="Complete",
            ),
        }

    def define_transitions(self):
        """Define state flow."""
        return {
            CombatStates.FIND_ENEMY: CombatStates.ATTACK,
            CombatStates.ATTACK: CombatStates.COMBAT,
            CombatStates.COMBAT: CombatStates.LOOT,
            CombatStates.LOOT: CombatStates.FIND_ENEMY,  # Loop!
        }

    def define_initial_state(self):
        return CombatStates.FIND_ENEMY

    # State handlers
    def _handle_find_enemy(self, context):
        """Find an enemy to attack."""
        enemy = self.screen.find_color("#FF0000")  # Red NPC

        if not enemy:
            self.logger.debug("No enemy found")
            return StateResult.RETRY  # Try again

        self.enemy_position = (enemy.x, enemy.y)
        return StateResult.SUCCESS  # Found one, move to ATTACK

    def _handle_attack(self, context):
        """Click the enemy."""
        x, y = self.enemy_position
        self.mouse.click_at(x, y)
        self.actions.wait("medium")
        return StateResult.SUCCESS  # Move to COMBAT

    def _handle_combat(self, context):
        """Wait for combat to finish."""
        if self.state.in_combat():
            # Still fighting
            self.actions.wait("medium")
            return StateResult.RETRY

        # Combat over
        return StateResult.SUCCESS  # Move to LOOT

    def _handle_loot(self, context):
        """Pick up loot."""
        if self.actions.pickup_loot():
            self.logger.info("Picked up loot!")

        # Check if inventory full
        if self.state.inventory_full():
            return StateResult.SUCCESS  # Will go to COMPLETE

        # Keep fighting
        return StateResult.SUCCESS  # Will loop to FIND_ENEMY

    def _handle_complete(self, context):
        """Bot finished."""
        self.logger.info("Inventory full, stopping")
        return StateResult.SUCCESS
```

### Understanding State Flow

**1. State Handler Naming Convention:**
```python
def _handle_find_enemy(self, context):  # Handles FIND_ENEMY state
def _handle_attack(self, context):      # Handles ATTACK state
```

The framework automatically calls `_handle_<state_name>()`.

**2. Return Values Control Flow:**
```python
return StateResult.SUCCESS  # Go to next state (from transitions)
return StateResult.RETRY    # Try this state again
return StateResult.FAILURE  # Go to failover state (if defined)
```

**3. Metadata Provides Safety:**
```python
StateMetadata(
    name="Combat",
    max_retries=5,   # After 5 RETRYs, fail
    timeout=60.0,    # After 60s, fail
)
```

### Practice Exercise

**Task:** Add a "Check HP" state that eats food if HP < 50

```python
class CombatStates(Enum):
    FIND_ENEMY = "find_enemy"
    CHECK_HP = "check_hp"      # NEW
    ATTACK = "attack"
    COMBAT = "combat"
    LOOT = "loot"
    COMPLETE = "complete"

# In transitions:
def define_transitions(self):
    return {
        CombatStates.FIND_ENEMY: CombatStates.CHECK_HP,  # Check HP first
        CombatStates.CHECK_HP: CombatStates.ATTACK,      # Then attack
        # ... rest
    }

def _handle_check_hp(self, context):
    """Check HP and eat if needed."""
    hp = self.state.get_hp()  # Read HP via OCR

    if hp and hp < 50:
        # Find food in inventory (slot 1)
        self.actions.click_inventory_slot(1)
        self.actions.wait("short")
        self.logger.info("Ate food!")

    return StateResult.SUCCESS  # Move to ATTACK
```

**New concepts learned:**
- ✅ State machines organize complex workflows
- ✅ `StateResult` controls state flow
- ✅ Transitions define the path between states
- ✅ Metadata adds safety (retries, timeouts)

---

## Level 4: Understanding Services (3-7 days)

**Goal:** Learn what happens "under the hood" when you call framework methods.

### Service Architecture

When you write:
```python
self.actions.click_inventory_slot(5)
```

Here's what actually happens:

```
Bot (your code)
  ↓ calls
GameActions (command layer)
  ↓ uses
TemplateMatchService (finds slot 5)
  ↓ returns coordinates
MouseService (moves mouse)
  ↓ calls
Win32 API (actual click)
```

**This is called "layered architecture".**

### Exploring the Mouse Service

Open: `src/osrsbot/services/mouse_service.py`

```python
def click_at(self, x, y, move_style="curved"):
    """Click at coordinates with human-like movement."""

    # Move mouse to position
    self.move_to(x, y, style=move_style)

    # Click
    pyautogui.click()

    return True
```

**What you're learning:**
- Services are just Python classes with methods
- `move_style="curved"` means human-like Bezier curve movement
- `pyautogui.click()` is the actual Windows API call

### Exploring the Screen Service

Open: `src/osrsbot/services/screen_service.py`

```python
def find_color(self, hex_color, tolerance=10):
    """Find pixels matching a color."""

    # Take screenshot
    screenshot = self.capture()

    # Convert to numpy array (for fast processing)
    img_array = np.array(screenshot)

    # Find matching pixels
    matches = # ... complex numpy operations ...

    return matches
```

**What you're learning:**
- `numpy` makes image processing fast
- Screenshot → Process → Return results
- Tolerance allows for slight color variations

### Creating Your Own Service

**Task:** Create a simple "NotificationService"

```python
"""Notification service - sends desktop notifications."""

import logging
from plyer import notification  # pip install plyer

logger = logging.getLogger(__name__)


class NotificationService:
    """Sends desktop notifications."""

    def __init__(self, app_name="OSRS Bot"):
        """Initialize notification service."""
        self.app_name = app_name
        logger.info(f"NotificationService initialized: {app_name}")

    def send(self, title, message):
        """
        Send a desktop notification.

        Args:
            title: Notification title
            message: Notification body
        """
        try:
            notification.notify(
                title=title,
                message=message,
                app_name=self.app_name,
                timeout=5  # Show for 5 seconds
            )
            logger.info(f"Sent notification: {title}")
            return True
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False


# Usage in your bot:
class MyBot(StateMachineBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.notifications = NotificationService()

    def _handle_complete(self, context):
        self.notifications.send("Bot Complete", "Inventory full!")
        return StateResult.SUCCESS
```

**New concepts learned:**
- ✅ Services are reusable components
- ✅ `__init__` initializes the service
- ✅ Error handling with `try/except`
- ✅ Logging for debugging
- ✅ Dependency injection (passing services to bots)

### Practice Exercise: Read HP Service

**Task:** Understand how HP reading works

1. Open `src/osrsbot/queries/stat_queries.py`
2. Find the `get_hp()` method
3. Trace the code flow:
   - Takes screenshot of HP orb
   - Passes to OCR service
   - OCR reads digits
   - Returns HP as integer

**Questions to answer:**
- Where is the HP orb located? (Check constants)
- What happens if OCR fails?
- How does it handle 2-digit vs 3-digit HP?

---

## Level 5: Advanced Patterns (2-4 weeks)

**Goal:** Understand professional software engineering patterns.

### Pattern 1: Dependency Injection

**Bad (hardcoded dependencies):**
```python
class MyBot:
    def __init__(self):
        self.mouse = MouseService()  # Hardcoded!
        self.screen = ScreenService()  # Can't swap/mock
```

**Good (injected dependencies):**
```python
class MyBot:
    def __init__(self, mouse_service, screen_service):
        self.mouse = mouse_service  # Injected
        self.screen = screen_service  # Testable/swappable
```

**Why it matters:**
- ✅ Can swap implementations (Win32 → Interception mouse)
- ✅ Can test with mock services
- ✅ Easier to maintain

### Pattern 2: CQRS (Command Query Responsibility Segregation)

**Commands (change state):**
```python
self.actions.click_inventory_slot(5)  # Mutates game state
self.actions.bank_deposit_all()       # Changes inventory
```

**Queries (read state):**
```python
hp = self.state.get_hp()              # Reads, doesn't change
full = self.state.inventory_full()    # Reads, doesn't change
```

**Why separate them?**
- ✅ Clear intent: "Am I reading or writing?"
- ✅ Queries can be cached
- ✅ Commands can be logged/audited

### Pattern 3: Template Method

**Base class defines structure:**
```python
class BankstanderBot(StateMachineBot):
    """Base class for banking scripts."""

    def _handle_banking(self, context):
        # 1. Walk to bank (implemented by base class)
        self._walk_to_bank()

        # 2. Click banker (implemented by base class)
        self._click_banker()

        # 3. Withdraw items (implemented by base class)
        self._withdraw_items()

        # 4. Process items (SUBCLASS IMPLEMENTS THIS)
        result = self.process_items(context)

        return result

    def process_items(self, context):
        """Subclass must implement this."""
        raise NotImplementedError("Subclass must implement process_items")
```

**Subclass fills in the blank:**
```python
class HerbCleanerBot(BankstanderBot):
    def process_items(self, context):
        # This is the ONLY method we write!
        for slot in range(1, 29):
            self.actions.click_inventory_slot(slot)
        return StateResult.SUCCESS
```

**Why it's powerful:**
- ✅ Reuse common logic (banking, walking)
- ✅ Only write unique parts
- ✅ Enforces consistent structure

### Pattern 4: Strategy Pattern

**Define interface:**
```python
class NPCDetector:
    """Interface for NPC detection."""
    def find_npc(self):
        raise NotImplementedError
```

**Multiple implementations:**
```python
class ColorDetector(NPCDetector):
    def find_npc(self):
        return self.screen.find_color("#00FFFF")

class TemplateDetector(NPCDetector):
    def find_npc(self):
        return self.template.find("npc.png")
```

**Use interchangeably:**
```python
class CombatBot:
    def __init__(self, detector: NPCDetector):
        self.detector = detector  # Any detector works

    def attack(self):
        npc = self.detector.find_npc()  # Don't care which strategy
        self.mouse.click_at(npc.x, npc.y)
```

**Why it matters:**
- ✅ Swap strategies at runtime
- ✅ Easy to add new strategies
- ✅ Testable in isolation

### Practice Exercise: Add Logging Strategy

**Task:** Create a logging strategy that can log to file OR console

```python
class LogStrategy:
    """Interface for logging."""
    def log(self, message):
        raise NotImplementedError

class FileLogger(LogStrategy):
    def __init__(self, filepath):
        self.file = open(filepath, 'a')

    def log(self, message):
        self.file.write(f"{message}\n")
        self.file.flush()

class ConsoleLogger(LogStrategy):
    def log(self, message):
        print(message)

# Usage:
bot.logger = FileLogger("bot.log")  # Log to file
# OR
bot.logger = ConsoleLogger()  # Log to console
```

---

## Learning Resources

### Python Fundamentals

**Free Online:**
- [Python.org Tutorial](https://docs.python.org/3/tutorial/) - Official docs
- [Real Python](https://realpython.com/) - Excellent tutorials
- [Automate the Boring Stuff](https://automatetheboringstuff.com/) - Practical Python

**Books:**
- "Python Crash Course" by Eric Matthes - Beginner friendly
- "Fluent Python" by Luciano Ramalho - Intermediate/Advanced
- "Design Patterns in Python" by Brandon Rhodes - Patterns

### Software Architecture

**Free Online:**
- [Refactoring Guru](https://refactoring.guru/design-patterns) - Design patterns explained
- [Martin Fowler's Blog](https://martinfowler.com/) - Architecture concepts

**Books:**
- "Clean Code" by Robert C. Martin - Code quality
- "Design Patterns" by Gang of Four - Classic patterns
- "Clean Architecture" by Robert C. Martin - System design

### Computer Vision

**For OSRS Bot Development:**
- OpenCV documentation
- Numpy tutorials
- Tesseract OCR docs

### Practice Projects

**Easy (Week 1-2):**
1. Simple clicking bot (clicks one location repeatedly)
2. Color-based fishing bot
3. Inventory slot clicker

**Medium (Week 3-6):**
4. Bankstanding bot (using base class)
5. Combat bot with HP checking
6. Resource gathering with banking

**Hard (Week 7-12):**
7. Multi-state combat bot with looting
8. Custom service (notifications, database logging)
9. Boss mechanics bot (Vorkath, Zulrah)

---

## Debugging Tips

### Reading Error Messages

**Example error:**
```
Traceback (most recent call last):
  File "bot.py", line 45, in _handle_fishing
    self.mouse.click_at(spot.x, spot.y)
AttributeError: 'NoneType' object has no attribute 'x'
```

**How to read it:**
1. **Bottom line**: `AttributeError` - The error type
2. **What happened**: `'NoneType' has no attribute 'x'` - `spot` is `None`
3. **Where**: `line 45` in `bot.py`
4. **What to fix**: Check if `spot` exists before using it

**Fix:**
```python
spot = self.screen.find_color("#00FFFF")
if spot:  # Check it's not None
    self.mouse.click_at(spot.x, spot.y)
else:
    self.logger.warning("No fishing spot found")
```

### Adding Debug Prints

```python
def _handle_fishing(self, context):
    print("DEBUG: Entering fishing state")

    spot = self.screen.find_color("#00FFFF")
    print(f"DEBUG: Found spot: {spot}")

    if spot:
        print(f"DEBUG: Clicking at ({spot.x}, {spot.y})")
        self.mouse.click_at(spot.x, spot.y)
```

### Using the Logger

```python
# Instead of print(), use logger:
self.logger.debug("Debug message (only in debug mode)")
self.logger.info("Info message")
self.logger.warning("Warning message")
self.logger.error("Error message")
```

---

## Common Mistakes & Solutions

### Mistake 1: Forgetting `self`

**Wrong:**
```python
def _handle_fishing(context):  # Missing self!
    actions.click_inventory_slot(1)  # Won't work
```

**Right:**
```python
def _handle_fishing(self, context):  # self is first param
    self.actions.click_inventory_slot(1)  # Works
```

### Mistake 2: Wrong Indentation

**Wrong:**
```python
def my_function():
print("Hello")  # Not indented!
```

**Right:**
```python
def my_function():
    print("Hello")  # Indented 4 spaces
```

Python uses indentation to define blocks.

### Mistake 3: Mutable Default Arguments

**Wrong:**
```python
def my_function(items=[]):  # DON'T DO THIS
    items.append(1)
    return items
```

**Right:**
```python
def my_function(items=None):
    if items is None:
        items = []
    items.append(1)
    return items
```

### Mistake 4: Not Checking Return Values

**Wrong:**
```python
spot = self.screen.find_color("#00FFFF")
self.mouse.click_at(spot.x, spot.y)  # Crashes if spot is None
```

**Right:**
```python
spot = self.screen.find_color("#00FFFF")
if spot:
    self.mouse.click_at(spot.x, spot.y)
else:
    return StateResult.RETRY
```

---

## Next Steps

### After Completing This Guide

**1. Build Your Own Bot**
- Choose a simple task (fishing, woodcutting, mining)
- Use existing bots as reference
- Don't be afraid to copy and modify

**2. Read Framework Code**
- Start with services you use most
- Understand how they work
- Learn from good examples

**3. Contribute**
- Fix bugs you find
- Add documentation
- Help other learners

**4. Keep Learning**
- Read "Clean Code"
- Learn design patterns
- Practice, practice, practice

---

## Questions?

### Getting Help

**In Code:**
- Read existing bots in `src/osrsbot/scripts/`
- Check services in `src/osrsbot/services/`
- Look at documentation in `docs/`

**Online:**
- Python Discord communities
- Stack Overflow for specific errors
- GitHub issues for framework bugs

### Study Checklist

**Beginner (First Month):**
- [ ] Run existing bots successfully
- [ ] Understand bankstanding_flax.py line by line
- [ ] Create a simple clicking bot
- [ ] Understand `if/else`, `for` loops, functions

**Intermediate (Months 2-3):**
- [ ] Create a combat bot with states
- [ ] Understand services (mouse, screen)
- [ ] Use configuration effectively
- [ ] Handle errors gracefully

**Advanced (Months 4-6):**
- [ ] Understand dependency injection
- [ ] Create your own service
- [ ] Refactor code using patterns
- [ ] Contribute to framework

---

## Remember

**Learning programming is a journey, not a destination.**

- ✅ **Start simple** - Don't try to understand everything at once
- ✅ **Copy and modify** - That's how you learn
- ✅ **Break things** - It's okay, that's how you learn
- ✅ **Ask questions** - No question is stupid
- ✅ **Build projects** - Learning by doing is best

**You don't need to understand the whole framework to build working bots.**

Start at the top (high-level APIs), gradually learn the lower layers. By the time you're curious about "how does mouse movement work?", you'll have enough context to understand the answer.

---

**Version:** 1.0
**Last Updated:** 2026-01-09
**Target Audience:** Complete beginners to intermediate Python developers
**Learning Time:** 1-6 months depending on dedication
