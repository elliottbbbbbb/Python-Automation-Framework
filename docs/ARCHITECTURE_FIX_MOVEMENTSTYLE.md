# Architecture Fix: MovementStyle Import Violation

**Date:** 2026-01-09
**Issue:** Commands layer importing from Services layer
**Status:** ✅ Fixed

---

## Problem

The `GameActions` class (commands layer) was importing `MovementStyle` directly from `MouseService` (services layer):

```python
# game_actions.py - WRONG
from osrsbot.services.mouse_service import MovementStyle
```

This violated the layered architecture:

```
Commands Layer (GameActions)
    ↓ should NOT import from
Services Layer (MouseService)
```

**Why this is bad:**
- Creates tight coupling between layers
- Commands layer should only import from models/constants, not services
- Makes it harder to swap service implementations
- Violates dependency inversion principle

---

## Root Cause

There were actually **TWO definitions** of `MovementStyle`:

1. **Enum in constants.py** (lines 16-23) - NOT being used
   ```python
   class MovementStyle(Enum):
       INSTANT = "instant"
       LINEAR = "linear"
       # ...
   ```

2. **Literal in mouse_service.py** (line 20) - Actually being used
   ```python
   MovementStyle = Literal["instant", "linear", "curved", "overshoot", "random"]
   ```

The code was comparing against **string literals** (`style == "curved"`), not Enum values, so the `Literal` type was correct.

---

## Solution

**Moved `MovementStyle` type alias to `constants.py`** where it belongs:

```python
# constants.py
from typing import Literal

# Mouse movement styles (used as string literals for simpler comparisons)
MovementStyle = Literal["instant", "linear", "curved", "overshoot", "random"]
```

**Updated all imports to use constants:**

```python
# Before (WRONG - violates architecture)
from osrsbot.services.mouse_service import MovementStyle

# After (CORRECT - shared constant)
from osrsbot.constants import MovementStyle
```

---

## Files Changed

### Created
- ~~`models/mouse_types.py`~~ (deleted - wrong location)

### Modified
1. **`constants.py`**
   - Removed: `MovementStyle` Enum (unused)
   - Added: `MovementStyle` Literal type alias
   - Added: `Literal` to imports

2. **`services/mouse_service.py`**
   - Removed: `MovementStyle` definition
   - Changed: Import from `constants`
   - Kept: `Literal` in typing imports (still needed for other params)

3. **`commands/game_actions.py`**
   - Changed: Import from `constants` instead of `services`

4. **`commands/inventory_actions.py`**
   - Changed: Import from `constants` instead of `services`

5. **`commands/combat_actions.py`**
   - Changed: Import from `constants` instead of `services`

6. **`services/walker_service.py`**
   - Changed: Import from `constants` instead of `services`

7. **`services/__init__.py`**
   - Changed: Import and re-export from `constants`

---

## Architecture After Fix

```
┌─────────────────────┐
│   Constants Layer   │  ← MovementStyle defined here
│  (constants.py)     │
└─────────────────────┘
          ↑
          │ (import)
          │
┌─────────────────────┐
│  Services Layer     │
│ (mouse_service.py)  │
└─────────────────────┘
          ↑
          │ (dependency injection)
          │
┌─────────────────────┐
│  Commands Layer     │
│ (game_actions.py)   │  ← Also imports from Constants
└─────────────────────┘
```

**Key principles:**
- ✅ Both layers import from shared `constants`
- ✅ Commands layer doesn't import from Services layer
- ✅ Type alias in appropriate location (constants, not models)

---

## Why Literal Instead of Enum?

The code uses **string comparisons**:

```python
if style == "curved":  # String comparison
    self._move_bezier(...)
```

**Literal** is better here because:
1. ✅ Simpler - no need to write `MovementStyle.CURVED.value`
2. ✅ Type-safe - IDE autocomplete still works
3. ✅ Fewer imports - don't need to import Enum everywhere
4. ✅ Consistent with existing code patterns

**Enum would require:**
```python
if style == MovementStyle.CURVED:  # More verbose
    # or
if style.value == "curved":  # Even worse
```

---

## Verification

```bash
# Test imports work
python -c "from osrsbot.constants import MovementStyle; print(MovementStyle)"
# Output: typing.Literal['instant', 'linear', 'curved', 'overshoot', 'random']

# Test bot imports
python -c "from osrsbot.scripts.combat.basic_npc_killer import BasicNPCKiller; print('OK')"
# Output: OK

# Verify no violations remain
grep -r "from osrsbot.services.mouse_service import.*MovementStyle" src/
# Output: (no matches)
```

---

## Lessons Learned

1. **Type aliases belong in `constants.py`**, not models or services
2. **Check for duplicate definitions** when refactoring
3. **Literal types are better than Enums** when code uses string comparisons
4. **Commands should never import from Services** - use constants/models for shared types

---

## Related Patterns

This same pattern should be used for other shared types:

```python
# constants.py
ButtonType = Literal["left", "right", "middle"]
CombatStyle = Literal["accurate", "aggressive", "defensive", "controlled"]
PrayerType = Literal["melee", "magic", "ranged"]
```

**Rule of thumb:**
- If it's a **type used by multiple layers** → `constants.py`
- If it's a **data model/config** → `models/`
- If it's **service-specific logic** → `services/`

---

**Architectural violation:** ❌ Fixed
**Import paths:** ✅ Corrected
**Type consistency:** ✅ Maintained
