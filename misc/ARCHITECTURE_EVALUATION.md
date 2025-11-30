# Architecture Evaluation & Recommendations for OSRS Bot

## Current State Analysis

### What You Have Now

Your bot currently uses a **hybrid MVC-ish architecture** with some good patterns but also some confusion:

```
models/          # Data & state (Config, GameState)
views/           # UI (menu, calibration)
controllers/     # Logic (ScriptRunner, GameActions)
services/        # Infrastructure (mouse, screen, OCR)
core/            # Window management (GameInterface)
scripts/         # Bot automation scripts
```

**The Good:**
- Clear separation of concerns at the service layer
- Command-Query Separation (GameState vs GameActions)
- Dependency injection via ScriptRunner
- Configuration centralization
- Infrastructure services are well-designed

**The Problems:**
1. **MVC doesn't fit game bots well** - Scripts aren't controllers, and GameState isn't really a model
2. **Layer confusion** - Is GameInterface core or a service? Where do scripts fit?
3. **Terminology mismatch** - "Controllers" and "Models" don't match what they actually do
4. **Scalability concerns** - As you add more bots, where do shared behaviors go?

---

## Architecture Options for Game Bots

### Option 1: **Service-Oriented + Script Pattern** (RECOMMENDED)

This is the **industry standard for game bots** (used by RuneLite plugins, OSBC, etc.)

```
services/          # Infrastructure services
├── input/
│   └── mouse.py         # MouseService
├── vision/
│   ├── screen.py        # ScreenService
│   └── ocr.py           # OCRService
├── window/
│   └── interface.py     # GameInterface
└── state/
    └── game_state.py    # GameState

domain/            # Game-specific domain logic
├── actions.py           # GameActions (domain operations)
└── queries.py           # GameQueries (if you split state)

scripts/           # Bot automation scripts
├── combat/
│   └── green_dragons.py
├── skills/
│   └── pickpocketing.py
└── base/
    └── script_base.py   # Base class for all scripts

app/               # Application layer
├── runner.py            # ScriptRunner (DI container)
├── menu.py              # CLI menu
└── calibration.py       # Calibration tool

models/            # Data models (NOT MVC models!)
└── config.py            # Configuration data
```

**Why this works:**
- **Services** = Infrastructure (mouse, screen, OCR, window)
- **Domain** = Game-specific logic (actions, queries)
- **Scripts** = Use cases (bot behaviors)
- **App** = Application orchestration
- **Models** = Data structures

**Benefits:**
✅ Matches game bot domain perfectly
✅ Clear separation: services → domain → scripts
✅ Easy to add new scripts without changing architecture
✅ Services are reusable across all scripts
✅ Domain layer prevents scripts from being too low-level
✅ Scalable - can add new services/actions without refactoring

**Example:**
```python
# Script uses domain layer, not services directly
def green_dragons(runner):
    while not runner.state.inventory_full():  # Domain query
        if runner.state.hp() < 70:
            runner.actions.eat("manta_ray")   # Domain action
        if not runner.state.in_combat():
            runner.actions.attack("green_dragon")
```

---

### Option 2: **Plugin Architecture** (Scalable, Complex)

Similar to RuneLite - each bot is a plugin with lifecycle hooks.

```
core/              # Core bot framework
├── plugin_manager.py
├── event_bus.py
└── lifecycle.py

plugins/           # Individual bots as plugins
├── green_dragons/
│   ├── plugin.py
│   ├── config.py
│   └── state.py
└── guns/
    ├── plugin.py
    └── config.py

services/          # Shared infrastructure
└── (same as Option 1)
```

**When to use:**
- You plan to run multiple bots simultaneously
- You want hot-reloadable plugins
- You need complex event handling
- You're building a platform, not just scripts

**Not recommended unless:**
- Your bot needs to handle 10+ different activities
- You need isolation between scripts
- You want community plugins

---

### Option 3: **Behavior Tree Pattern** (Advanced AI)

Used for complex decision-making in game AI.

```
behaviors/
├── composite/     # Sequence, Selector, Parallel
├── leaf/          # Attack, Eat, Bank
└── decorator/     # Repeat, Retry, Until

scripts/
└── green_dragons.py  # Builds behavior tree
```

**When to use:**
- Complex decision trees
- Need to visualize bot logic
- Want reusable behavior components

**Not recommended unless:**
- Your bot has complex AI needs
- Simple sequential logic isn't enough
- You want visual debugging of decisions

---

### Option 4: **Keep MVC** (Not Recommended)

You could force MVC to work:

**Problems:**
- Scripts aren't Views (they don't display anything)
- GameState isn't a Model (it queries game state, not application data)
- GameActions isn't a Controller (it doesn't handle user input)
- Confusing terminology for newcomers
- Fighting against the pattern

**Only use if:**
- You absolutely must follow MVC for some external reason
- You're okay with non-standard terminology

---

## Recommended Approach: Service-Oriented + Script Pattern

### Refactored Structure

```
src/osrsbot/
├── models/
│   └── config.py              # Data models only
│
├── services/
│   ├── input/
│   │   └── mouse.py           # MouseService
│   ├── vision/
│   │   ├── screen.py          # ScreenService
│   │   └── ocr.py             # OCRService
│   ├── window/
│   │   └── interface.py       # GameInterface
│   └── __init__.py
│
├── domain/
│   ├── actions.py             # GameActions
│   ├── state.py               # GameState
│   └── __init__.py
│
├── scripts/
│   ├── base.py                # Base script class
│   ├── combat/
│   │   └── green_dragons.py
│   └── skills/
│       └── pickpocketing.py
│
├── app/
│   ├── runner.py              # ScriptRunner
│   ├── menu.py                # CLI menu
│   └── calibration.py         # Calibration tool
│
└── main.py
```

### Migration Path

**Phase 1: Rename for clarity**
```
controllers/ → domain/
models/state.py → domain/state.py
models/config.py → models/config.py (keep)
views/ → app/
core/ → services/window/
```

**Phase 2: Reorganize services**
```
services/mouse_service.py → services/input/mouse.py
services/screen_service.py → services/vision/screen.py
services/ocr_service.py → services/vision/ocr.py
```

**Phase 3: Organize scripts**
```
scripts/green_dragons.py → scripts/combat/green_dragons.py
scripts/guns.py → scripts/skills/pickpocketing.py
```

**Phase 4: Update imports**
```python
# Old
from osrsbot.controllers.actions import GameActions
from osrsbot.models.state import GameState

# New
from osrsbot.domain import GameActions, GameState
from osrsbot.services.input import MouseService
from osrsbot.services.vision import ScreenService
```

---

## Key Design Principles for Game Bots

### 1. **Layered Architecture**

```
Scripts (Use Cases)
    ↓ uses
Domain (Game Logic)
    ↓ uses
Services (Infrastructure)
    ↓ uses
OS/Hardware
```

**Rules:**
- Scripts depend on Domain, not Services directly
- Domain depends on Services
- Services depend on nothing except OS
- **Never reverse dependencies**

### 2. **Command-Query Separation**

```python
# Queries (read state) - return values, no side effects
hp = state.get_hp()
full = state.inventory_full()
combat = state.in_combat()

# Commands (change state) - perform actions, may return success
actions.eat("food")
actions.attack("npc")
actions.teleport()
```

### 3. **Dependency Injection**

```python
class ScriptRunner:
    """DI Container - assembles all dependencies"""

    def __init__(self):
        # Build dependency graph
        self.config = Config()
        self.interface = GameInterface(self.config)
        self.mouse = MouseService(self.config)
        self.screen = ScreenService(self.interface)
        self.state = GameState(self.screen, self.config)
        self.actions = GameActions(self.mouse, self.screen)

    def run(self, script):
        # Inject dependencies
        script(self.state, self.actions, self.config)
```

### 4. **Single Responsibility**

Each component does **one thing well**:
- **MouseService** - Only mouse control
- **ScreenService** - Only screen capture/vision
- **GameState** - Only state queries
- **GameActions** - Only game actions
- **ScriptRunner** - Only dependency injection
- **Scripts** - Only bot logic

---

## Scalability Concerns

### When You Add More Bots

**Bad (tight coupling):**
```python
def green_dragons():
    # Every script duplicates this logic
    if hp < 70:
        find_food()
        click_food()
        wait()
```

**Good (reusable domain layer):**
```python
def green_dragons(actions, state):
    # Shared logic in domain
    if state.hp() < 70:
        actions.eat_food("manta_ray")
```

### Common Patterns

Extract reusable behaviors into domain:
```python
# domain/actions.py
class GameActions:
    def safe_combat(self, target, food, hp_threshold=70):
        """Reusable combat pattern"""
        while not self.state.inventory_full():
            if self.state.hp() < hp_threshold:
                self.eat(food)
            if not self.state.in_combat():
                self.attack(target)

# scripts/combat/green_dragons.py
def run(actions):
    actions.safe_combat("green_dragon", "manta_ray", hp_threshold=70)
```

---

## Testing Strategy

### Unit Tests
```python
# Test services in isolation
def test_mouse_moves_to_target():
    mouse = MouseService(MockConfig())
    assert mouse.move_to(100, 100) == True

# Test domain with mocked services
def test_eat_finds_and_clicks_food():
    actions = GameActions(mock_mouse, mock_screen)
    actions.eat("manta_ray")
    assert mock_mouse.clicked_at == (100, 200)
```

### Integration Tests
```python
# Test full script with test environment
def test_green_dragons_script():
    runner = ScriptRunner(test_window)
    runner.run(green_dragons_script, runs=1)
    assert runner.state.inventory_full()
```

---

## Comparison Matrix

| Pattern | Complexity | Scalability | Bot-Friendly | Learning Curve |
|---------|-----------|-------------|--------------|----------------|
| **Service-Oriented** (Recommended) | Low | High | ⭐⭐⭐⭐⭐ | Low |
| Plugin Architecture | High | Very High | ⭐⭐⭐⭐ | High |
| Behavior Trees | Medium | High | ⭐⭐⭐ | Medium |
| MVC | Medium | Medium | ⭐⭐ | Medium |

---

## Final Recommendation

### Go with Service-Oriented + Script Pattern

**Why:**
1. ✅ Natural fit for game bots
2. ✅ Clear layering: Services → Domain → Scripts
3. ✅ Easy to understand and explain
4. ✅ Scales well as you add more bots
5. ✅ Industry standard (RuneLite, OSBC, etc.)
6. ✅ Testable at every layer
7. ✅ No fighting against the pattern

### Migration Plan

**Step 1: Rename layers** (minimal changes)
```
controllers/ → domain/
views/ → app/
core/ → services/window/
```

**Step 2: Reorganize services** (optional, can do later)
```
services/
├── input/
├── vision/
└── window/
```

**Step 3: Organize scripts** (as you add more)
```
scripts/
├── combat/
├── skills/
└── misc/
```

**Step 4: Document** (update ARCHITECTURE.md)

---

## Questions to Ask Yourself

1. **How many scripts will you have?**
   - < 5 scripts: Keep it simple (Service-Oriented)
   - 5-20 scripts: Service-Oriented with shared behaviors
   - 20+ scripts: Consider Plugin Architecture

2. **Will scripts share logic?**
   - Yes → Need strong domain layer
   - No → Can keep scripts independent

3. **Do you need hot-reloading?**
   - Yes → Plugin Architecture
   - No → Service-Oriented is fine

4. **Is this a platform or a personal bot?**
   - Platform → Plugin Architecture
   - Personal → Service-Oriented

5. **How complex is the decision-making?**
   - Simple sequences → Service-Oriented
   - Complex AI → Consider Behavior Trees

---

## Next Steps

1. **Decide** on architecture pattern
2. **Create migration plan** if changing
3. **Update ARCHITECTURE.md** with chosen pattern
4. **Refactor incrementally** (one layer at a time)
5. **Add tests** as you refactor
6. **Document patterns** for future scripts

---

## Resources

- **RuneLite Plugin System**: https://github.com/runelite/runelite
- **OSBC Framework**: Similar service-oriented approach
- **Clean Architecture**: Robert C. Martin (layers and dependencies)
- **Domain-Driven Design**: Eric Evans (domain layer concepts)
