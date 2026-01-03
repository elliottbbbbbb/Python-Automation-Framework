# OSRS Bot Architecture - CQRS Pattern

## Overview

This codebase follows the **CQRS (Command Query Responsibility Segregation)** pattern for clean separation of concerns.

## CQRS Layers

### Query Layer (`src/osrsbot/queries/`)
**Responsibility**: READ-ONLY operations - detect game state, find elements

- `BankQueries` - Bank state detection, template matching
- `CombatQueries` - Combat state detection
- `StatQueries` - HP/Prayer/Run energy detection
- `InventoryQueries` - Inventory state detection
- `GameState` - Facade providing unified API to all queries

**Key Rule**: Query layer NEVER modifies anything - only reads and detects.

### Command Layer (`src/osrsbot/commands/`)
**Responsibility**: WRITE operations - execute actions based on query results

- `BankActions` - Bank interactions (clicking banker, searching, withdrawing)
- `CombatActions` - Combat actions
- `InventoryActions` - Inventory operations
- `GameActions` - Facade providing unified API to all actions

**Key Rule**: Command layer uses query layer to find things, then performs actions.

---

## Banking Components (Example)

### Query Layer: `BankQueries`

```python
# Location: src/osrsbot/queries/bank_queries.py

class BankQueries:
    def is_bank_open(self, search_button_template: str) -> bool:
        """Detect if bank is open (READ-ONLY)"""

    def find_template(self, template_path: str) -> Optional[Tuple[int, int, float]]:
        """Find element on screen (READ-ONLY)"""

    def find_multi_template(self, templates: List[str]) -> Optional[Tuple]:
        """Find best matching template (READ-ONLY)"""
```

### Command Layer: `BankActions`

```python
# Location: src/osrsbot/commands/bank_actions.py

class BankActions:
    def __init__(self, mouse, bank_queries, coord_resolver, timing):
        self.bank_queries = bank_queries  # Uses query layer!

    def click_banker(self, templates: List[str]) -> bool:
        """
        1. Query layer finds banker
        2. Command layer clicks it
        """
        result = self.bank_queries.find_multi_template(templates)
        if result:
            self.mouse.click_at(x, y)

    def search_and_withdraw(self, ...) -> bool:
        """
        1. Query layer finds search button
        2. Command layer clicks it
        3. Type search text
        4. Query layer finds item
        5. Command layer clicks item
        """
```

### Facade Layer: `GameActions` & `GameState`

```python
# Location: src/osrsbot/commands/game_actions.py

class GameActions:
    def __init__(self, ...):
        self.bank = BankActions(...)  # Focused module

    # Convenience methods delegate to focused modules
    def is_bank_open(self, template: str) -> bool:
        return self.bank.is_bank_open(template)

    def click_banker(self, templates: List[str]) -> bool:
        return self.bank.click_banker(templates)
```

---

## Usage in Bot Scripts

### ✅ Correct Usage (CQRS Pattern)

```python
class MyBot(StateMachineBot):
    def _handle_banking(self, context):
        actions = self.actions  # GameActions
        state = self.state      # GameState

        # Query layer: Check state
        if not actions.is_bank_open(search_template):
            # Command layer: Execute action
            actions.click_banker(banker_templates)

        # Command layer: Combined action (uses queries internally)
        actions.bank_search_and_withdraw(
            search_button_template,
            item_template,
            "item name",
            "search text"
        )
```

### ❌ Incorrect Usage (Anti-patterns)

```python
# DON'T: Implement template matching in bot scripts
class MyBot(StateMachineBot):
    def _my_template_matching(self):  # ❌ Belongs in BankQueries
        template = cv.imread(...)
        result = cv.matchTemplate(...)

# DON'T: Mix queries and commands in same method
def find_and_click(self):  # ❌ Split into query + command
    pos = self.find()  # Query
    self.click(pos)    # Command
```

---

## Benefits of This Architecture

1. **Separation of Concerns**
   - Queries: "Where is it?"
   - Commands: "Click it!"

2. **Reusability**
   - BankQueries can be used by any script
   - BankActions can be used by any script
   - No code duplication

3. **Testability**
   - Mock query layer to test commands
   - Mock command layer to test logic

4. **Maintainability**
   - Fix bugs in one place
   - All scripts benefit immediately

5. **Modularity**
   - Easy to add new queries
   - Easy to add new commands
   - Focused, single-responsibility classes

---

## Creating New Features

### Adding New Bank Functionality

1. **Query needed?** Add to `BankQueries`
   ```python
   def find_deposit_button(self) -> Optional[Tuple[int, int]]:
       # Template matching logic
   ```

2. **Action needed?** Add to `BankActions`
   ```python
   def click_deposit_all(self) -> bool:
       pos = self.bank_queries.find_deposit_button()
       self.mouse.click_at(pos)
   ```

3. **Facade method?** Add to `GameActions` (optional)
   ```python
   def bank_deposit_all(self) -> bool:
       return self.bank.click_deposit_all()
   ```

### Creating Bankstander Scripts

**Option 1**: Use `BankstanderBot` base class (simplest)
```python
from osrsbot.scripts.base_bankstander import BankstanderBot

class MyBot(BankstanderBot):
    def __init__(self, *args, **kwargs):
        super().__init__(
            item_name="my item",
            item_search_text="search",
            item_template="path/to/template.PNG",
            *args, **kwargs
        )

    def process_items(self, context):
        # Your custom processing logic
        pass
```

**Option 2**: Use `BankActions` directly
```python
class MyBot(StateMachineBot):
    def _handle_banking(self, context):
        # All banking logic available via self.actions.bank.*
        if not self.actions.is_bank_open(template):
            self.actions.click_banker(templates)
        self.actions.bank_search_and_withdraw(...)
```

---

## File Organization

```
src/osrsbot/
├── queries/              # Query Layer (READ)
│   ├── bank_queries.py   # Bank state detection
│   ├── combat_queries.py
│   ├── stat_queries.py
│   ├── inventory_queries.py
│   └── game_queries.py   # Facade
│
├── commands/             # Command Layer (WRITE)
│   ├── bank_actions.py   # Bank interactions
│   ├── combat_actions.py
│   ├── inventory_actions.py
│   └── game_actions.py   # Facade
│
├── scripts/              # Bot Scripts
│   ├── base_bankstander.py
│   ├── bankstander_flax.py
│   └── ...
│
├── core/                 # Base Classes
│   ├── base_bot.py
│   └── state_machine_bot.py
│
└── services/             # Low-level Services
    ├── mouse_service.py
    ├── screen_service.py
    └── ...
```

---

## Key Principles

1. **Queries never mutate** - Only detect and return data
2. **Commands use queries** - Commands call queries to find things
3. **Scripts use facades** - Scripts call `GameActions` and `GameState`
4. **Focused modules** - Each class has one clear responsibility
5. **No duplication** - Shared logic goes in queries/commands, not scripts

---

## See Also

- `BANKSTANDER_GUIDE.md` - Quick guide for creating bankstander scripts
- `src/osrsbot/scripts/base_bankstander.py` - Reusable bankstander base class
- `src/osrsbot/scripts/bankstander_flax.py` - Complete working example
