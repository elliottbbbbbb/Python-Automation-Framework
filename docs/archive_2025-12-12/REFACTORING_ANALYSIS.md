# Refactoring Analysis - Template Matching & Actions


## ✅ **COMPLETED** - December 11, 2025

**Implementation Summary:**
✅ Phase 1 DONE: Moved `UIElement` and `UIElementGrid` to `models/ui_elements.py`
✅ Phase 2 DONE: Added section headers to `actions.py` for better organization
❌ Splitting actions.py REJECTED: Would create coupling issues

See [FILE_RESPONSIBILITIES.md](FILE_RESPONSIBILITIES.md) for updated architecture.

---

## Original Analysis

### Overview

Two potential refactorings identified:
1. **Move dataclasses from `template_match_service.py` to `models/`**
2. **Split `actions.py` (654 lines) into domain-specific action modules**

---

## 1. Template Matching Dataclasses

### Current State
**Location**: `services/template_match_service.py`
- `UIElement` dataclass (lines 29-71)
- `UIElementGrid` class (lines 73-200+)

### Analysis

#### ✅ **RECOMMEND REFACTORING**

**Reasons to move to models:**

1. **Separation of Concerns**
   - `UIElement` and `UIElementGrid` are **data models**, not service logic
   - Services should contain behavior, not data structure definitions
   - Models directory should contain all data structures used across the app

2. **Reusability**
   - These models could be used by other services (e.g., `game_queries.py` uses UIElement)
   - Currently causes circular import risk if other services need these types

3. **Testing**
   - Models can be tested independently of service logic
   - Easier to mock and validate data structures

4. **Industry Standard**
   - Django/Flask/FastAPI all separate models from services
   - Clean Architecture principle: separate entities from use cases

#### Proposed Structure

```
src/osrsbot/models/
├── __init__.py
├── config.py          (existing)
├── ui_elements.py     (NEW - contains UIElement, UIElementGrid)
└── README.md          (NEW - explains model responsibilities)
```

**New file: `models/ui_elements.py`**
```python
"""
UI Element Models - Data structures for template-matched UI elements.

Contains dataclasses representing UI elements detected via template matching.
Used by TemplateMatchService, GameActions, and game state queries.
"""
from dataclasses import dataclass
from typing import Tuple, Optional, List

@dataclass
class UIElement:
    """Represents a single clickable UI element..."""
    # Move entire class here

class UIElementGrid:
    """Represents a grid of UI elements..."""
    # Move entire class here
```

**Update imports:**
- `template_match_service.py` → `from osrsbot.models.ui_elements import UIElement, UIElementGrid`
- `game_queries.py` → `from osrsbot.models.ui_elements import UIElement`
- `actions.py` → `from osrsbot.models.ui_elements import UIElement`

### Migration Impact

**Files to update:**
- `services/template_match_service.py` (remove classes, add import)
- `queries/game_queries.py` (update import if used)
- `controllers/actions.py` (update import if used)
- `models/__init__.py` (export new models)

**Risk**: LOW - Clean refactoring with no logic changes

---

## 2. Actions.py Refactoring

### Current State
**Location**: `controllers/actions.py`
**Size**: 654 lines
**Functions**: 25+ action methods

### Method Categorization

#### **Inventory Actions** (5 methods)
- `click_inventory_slot()` - Config-based clicking
- `click_inventory_slot_detected()` - Template-based clicking
- `ensure_inventory_open()` - UI state management

#### **UI/Button Actions** (2 methods)
- `click_ui_button_detected()` - Template-based UI clicking
- `close_interface()` - Close dialogs

#### **Color-Based Actions** (2 methods)
- `click_color()` - Simple color clicking
- `click_color_smart()` - Smart clicking with tracking/blacklisting (200+ lines!)

#### **Coordinate Actions** (1 method)
- `click_coordinate()` - Direct coordinate clicking

#### **Item Actions** (4 methods)
- `use_item()` - Use item by color
- `eat_food()` - Wrapper for eating
- `drink_potion()` - Wrapper for drinking

#### **NPC/Movement Actions** (3 methods)
- `attack_npc()` - Color-based NPC clicking
- `walk_to_marker()` - Click ground marker
- `click_minimap()` - Click minimap location

#### **Teleport Actions** (2 methods)
- `teleport_varrock()` - Hardcoded teleport
- `teleport_item()` - Generic teleport item

#### **Banking Actions** (2 methods)
- `bank_deposit_all()` - Deposit inventory
- `bank_search()` - Search bank

#### **Utility Actions** (4 methods)
- `wait()` - Delay execution
- `reset_click_tracking()` - Clear tracker state
- `wait_for_color()` - Poll until color appears
- `_to_absolute()` - Coordinate conversion (private)
- `_get_player_position()` - Player center (private)

### Analysis

#### ⚠️ **PARTIAL REFACTORING RECOMMENDED**

**Don't split by domain (banking, combat, etc.)** - Here's why:

#### Arguments AGAINST splitting by domain:

1. **High Coupling Between Domains**
   - Banking uses inventory actions
   - Combat uses item actions (potions, food)
   - Teleporting uses item actions
   - All use coordinate/color actions
   - Would create circular dependencies or require complex dependency injection

2. **Shared State**
   - All actions share `self.screen`, `self.mouse`, `self.config`
   - All use same `_to_absolute()` coordinate conversion
   - All use same `click_tracker` for smart clicking
   - Splitting would duplicate this state across multiple classes

3. **Size Not Critical**
   - 654 lines is manageable for a controller
   - File is well-organized with logical grouping
   - Most methods are small (10-30 lines)
   - Only `click_color_smart()` is large (~200 lines)

#### ✅ **RECOMMENDED REFACTORING INSTEAD:**

### Option A: Extract Smart Clicking Logic (RECOMMENDED)

Extract the complex `click_color_smart()` into a dedicated service:

```
src/osrsbot/services/
├── smart_click_service.py  (NEW)
└── template_match_service.py
```

**New: `services/smart_click_service.py`**
```python
"""
Smart Click Service - Intelligent color-based target selection.

Provides smart clicking with:
- Target locking (follow moving NPCs)
- Blacklisting (avoid inaccessible locations)
- Stuck detection (avoid clicking same spot)
- Distance-based sorting
"""
class SmartClickService:
    def __init__(
        self,
        screen_service: ScreenService,
        tracker: ClickTargetTracker
    ):
        self.screen = screen_service
        self.tracker = tracker

    def find_and_click_target(
        self,
        hex_color: str,
        mouse_service: MouseService,
        reference_point: Optional[Tuple[int, int]] = None,
        ...
    ) -> bool:
        """Core smart clicking logic (extracted from GameActions)"""
        # 200+ lines of smart clicking logic here
```

**Benefits:**
- Reduces `actions.py` by ~200 lines (to ~450 lines)
- Isolates complex logic for easier testing
- `SmartClickService` can be unit tested independently
- `GameActions.click_color_smart()` becomes a thin wrapper:

```python
def click_color_smart(self, color_name: str, ...) -> bool:
    hex_color = self.config.get("colors", color_name)
    return self.smart_click_service.find_and_click_target(
        hex_color=hex_color,
        mouse_service=self.mouse,
        ...
    )
```

### Option B: Keep As-Is with Better Organization

Just improve documentation and add section markers:

```python
class GameActions:
    # ==================== INITIALIZATION ====================
    def __init__(...): ...

    # ==================== UTILITIES ====================
    def wait(...): ...
    def _to_absolute(...): ...

    # ==================== INVENTORY ====================
    def click_inventory_slot(...): ...
    def ensure_inventory_open(...): ...

    # ==================== COLOR-BASED CLICKING ====================
    def click_color(...): ...
    def click_color_smart(...): ...

    # ==================== BANKING ====================
    def bank_deposit_all(...): ...
    def bank_search(...): ...

    # ... etc
```

**Benefits:**
- Zero refactoring cost
- Maintains cohesion
- Easy to navigate with section headers

---

## Recommendation Summary

| Refactoring | Recommend? | Priority | Effort | Benefit |
|-------------|-----------|----------|--------|---------|
| **Move UIElement/UIElementGrid to models/** | ✅ **YES** | HIGH | LOW (1-2 hours) | Better architecture, testability |
| **Split actions.py by domain** | ❌ **NO** | N/A | HIGH | Creates coupling issues |
| **Extract SmartClickService** | ⚠️ **MAYBE** | MEDIUM | MEDIUM (3-4 hours) | Cleaner separation, easier testing |
| **Better organize actions.py** | ✅ **YES** | LOW | LOW (30 min) | Improved readability |

---

## Implementation Plan

### Phase 1: Move Models (HIGH PRIORITY) ✅

1. Create `src/osrsbot/models/ui_elements.py`
2. Move `UIElement` dataclass from template_match_service.py
3. Move `UIElementGrid` class from template_match_service.py
4. Update imports in:
   - `services/template_match_service.py`
   - `queries/game_queries.py`
   - `controllers/actions.py`
5. Update `models/__init__.py` exports
6. Run tests to verify no breakage

**Estimated Time**: 1-2 hours
**Risk**: LOW

### Phase 2: Improve Actions Organization (QUICK WIN) ✅

1. Add section comment headers to `actions.py`
2. Group related methods together
3. Add module-level docstring explaining organization
4. Document which methods are most commonly used

**Estimated Time**: 30 minutes
**Risk**: NONE

### Phase 3: Extract SmartClickService (OPTIONAL) ⚠️

Only do this if:
- You're adding more smart clicking features
- Testing smart clicking in isolation is important
- You want to reuse smart clicking logic elsewhere

Otherwise, **defer this refactoring** until needed.

**Estimated Time**: 3-4 hours
**Risk**: MEDIUM (complex logic to extract)

---

## Code Metrics After Refactoring

### Before
| File | Lines | Responsibility |
|------|-------|----------------|
| `template_match_service.py` | ~400 | Service logic + 2 dataclasses |
| `actions.py` | 654 | All game actions |
| `models/` | 2 files | Config only |

### After (Phase 1 + 2)
| File | Lines | Responsibility |
|------|-------|----------------|
| `template_match_service.py` | ~300 | Service logic only ✅ |
| `actions.py` | 654 | All game actions (better organized) ✅ |
| `models/ui_elements.py` | ~100 | UI dataclasses ✅ |
| `models/` | 3 files | Config + UI elements |

### After (All Phases)
| File | Lines | Responsibility |
|------|-------|----------------|
| `template_match_service.py` | ~300 | Service logic only ✅ |
| `actions.py` | ~450 | Game actions (delegating smart clicks) ✅ |
| `smart_click_service.py` | ~250 | Smart clicking logic ✅ |
| `models/ui_elements.py` | ~100 | UI dataclasses ✅ |

---

## Decision

**My Recommendation**: Proceed with **Phase 1 ONLY** for now.

**Reasoning:**
1. Moving models to `models/` is architecturally correct and low-risk
2. Splitting `actions.py` creates more problems than it solves
3. Current 654-line file is manageable and well-organized
4. Extract SmartClickService only if future requirements demand it

**What do you think?** Should we:
- ✅ **Option A**: Move models to `models/` (Phase 1)
- ✅ **Option B**: Move models + improve organization (Phase 1 + 2)
- ⚠️ **Option C**: Move models + extract SmartClickService (Phase 1 + 3)
- 💭 **Option D**: Something else?
