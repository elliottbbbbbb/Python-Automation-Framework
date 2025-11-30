# Codebase Cleanup Analysis

## Current State: Duplicate Files from Incomplete MVC Migration

### Active Files (Currently Used by Entry Points)

**Entry Points:**
- `__main__.py` → imports `osrsbot.views.menu.main` ✅ ACTIVE
- `main.py` → imports `osrsbot.views.menu.main` ✅ ACTIVE

**Active Import Chain:**
```
__main__.py / main.py
  ↓
views/menu.py (ACTIVE)
  ↓ imports
  ├─ osrsbot.models.config.Config
  ├─ osrsbot.views.calibration.Calibrator
  ├─ osrsbot.controllers.runner.ScriptRunner
  └─ osrsbot.scripts.*
      ↓ imports
      ├─ osrsbot.models.state.GameState
      ├─ osrsbot.models.config.Config
      └─ osrsbot.controllers.actions.GameActions
```

### Files Analysis

#### ✅ ACTIVE - Currently Used

| File | Used By | Purpose |
|------|---------|---------|
| `views/menu.py` | `__main__.py`, `main.py` | Main menu (ACTIVE ENTRY POINT) |
| `views/calibration.py` | `views/menu.py` | Calibration tool |
| `controllers/runner.py` | `views/menu.py` | ScriptRunner (DI container) |
| `controllers/actions.py` | All scripts | GameActions (domain logic) |
| `models/config.py` | Everything | Configuration |
| `models/state.py` | Scripts, runner | GameState |
| `scripts/*.py` | Menu choices | Bot scripts |
| `services/mouse_service.py` | `controllers/actions.py` | Mouse control |
| `services/screen_service.py` | `controllers/actions.py` | Screen capture |
| `services/ocr_service.py` | `models/state.py` | OCR |
| `core/game_interface.py` | `controllers/runner.py` | Window management |

#### ⚠️ DEPRECATED - Old Files (Backward Compat Redirects)

| File | Status | Purpose |
|------|--------|---------|
| `actions/__init__.py` | Redirect | Points to `controllers.actions` |
| `actions/game_actions.py` | Duplicate | OLD version with old imports |

**Import in actions/game_actions.py:**
```python
from osrsbot.config import Config  # OLD - uses root config.py
```

#### ❌ UNUSED - Orphaned Files from OLD Structure

| File | Status | Reason |
|------|--------|--------|
| `cli/main.py` | UNUSED | Old menu, uses old imports |
| `cli/runner.py` | UNUSED | Duplicate of `controllers/runner.py` |
| `cli/calibration.py` | UNUSED | Duplicate of `views/calibration.py` |
| `cli/__init__.py` | UNUSED | Exports old cli modules |
| `services/game_state_service.py` | UNUSED | Duplicate of `models/state.py` |
| `config.py` (root) | MAYBE USED? | Old config, check if used |

**cli files import OLD paths:**
```python
# cli/main.py
from osrsbot.config import Config  # Uses root config.py
from osrsbot.cli.calibration import Calibrator
from osrsbot.cli.runner import ScriptRunner
```

### Verification: Check if Root config.py is Used

Let me check what imports the root `config.py`:

```bash
grep -r "from osrsbot.config import" --include="*.py" src/osrsbot/
```

**Result:**
- `actions/game_actions.py` - OLD file (not used)
- `cli/calibration.py` - UNUSED
- `cli/main.py` - UNUSED
- `cli/runner.py` - UNUSED
- `services/game_state_service.py` - UNUSED

**Conclusion:** Root `config.py` is ONLY imported by unused files!

### Import Dependency Graph

```
ACTIVE PATH:
__main__.py
  → views/menu.py
      → models/config.py ✅
      → views/calibration.py ✅
      → controllers/runner.py ✅
          → models/config.py ✅
          → models/state.py ✅
          → controllers/actions.py ✅
              → models/config.py ✅
              → services/mouse_service.py ✅
              → services/screen_service.py ✅

UNUSED PATH:
cli/main.py ❌
  → config.py (root) ❌
  → cli/calibration.py ❌
  → cli/runner.py ❌
      → services/game_state_service.py ❌
```

### Files Safe to Delete

#### 100% Safe (Not imported by anything active):

1. **cli/main.py** - Old menu, superseded by `views/menu.py`
2. **cli/runner.py** - Duplicate of `controllers/runner.py`
3. **cli/calibration.py** - Duplicate of `views/calibration.py`
4. **cli/__init__.py** - Only exports unused cli modules
5. **services/game_state_service.py** - Duplicate of `models/state.py`

#### Needs Careful Check:

6. **config.py** (root) - Only used by deprecated files
7. **actions/game_actions.py** - Old version, `actions/__init__.py` redirects to new one
8. **actions/__init__.py** - Backward compat redirect (maybe keep for safety?)

### Recommended Cleanup Plan

#### Phase 1: Delete Obviously Unused Files (SAFE)

```bash
rm -rf src/osrsbot/cli/
rm src/osrsbot/services/game_state_service.py
```

**Rationale:**
- `cli/` folder is completely unused
- Entry points use `views/menu.py` not `cli/main.py`
- `services/game_state_service.py` duplicates `models/state.py`

#### Phase 2: Delete Root config.py (SAFE with verification)

```bash
rm src/osrsbot/config.py
```

**Verification needed:**
- Check no external code imports `osrsbot.config`
- Only deprecated files use it

#### Phase 3: Handle Backward Compat Redirects (DECISION NEEDED)

**Option A: Keep for safety**
```
Keep: actions/__init__.py (redirect)
Delete: actions/game_actions.py (old duplicate)
```

**Option B: Clean everything**
```
Delete: actions/ folder entirely
Update imports if anything breaks
```

**Recommendation:** Keep `actions/__init__.py` redirect for now, delete `actions/game_actions.py`

### Verification Tests

Before deleting, verify these commands work:

```bash
# Test imports
python -c "from osrsbot.models import Config, GameState; print('✓ Models OK')"
python -c "from osrsbot.controllers import GameActions, ScriptRunner; print('✓ Controllers OK')"
python -c "from osrsbot.views import Calibrator; print('✓ Views OK')"
python -c "from osrsbot.services import MouseService, ScreenService; print('✓ Services OK')"

# Test entry point
python -m osrsbot --help  # Should show menu
```

### After Cleanup: Expected Structure

```
src/osrsbot/
├── models/
│   ├── config.py          ✅ Config
│   └── state.py           ✅ GameState
├── controllers/
│   ├── actions.py         ✅ GameActions
│   └── runner.py          ✅ ScriptRunner
├── views/
│   ├── menu.py            ✅ Main menu
│   └── calibration.py     ✅ Calibrator
├── services/
│   ├── mouse_service.py   ✅ MouseService
│   ├── screen_service.py  ✅ ScreenService
│   └── ocr_service.py     ✅ OCRService
├── core/
│   └── game_interface.py  ✅ GameInterface
├── scripts/
│   ├── green_dragons.py   ✅
│   ├── guns.py            ✅
│   └── test.py            ✅
├── utils/
│   └── ocr_helpers.py     ✅
├── actions/               ⚠️ KEEP for backward compat?
│   └── __init__.py        (redirect only)
├── __init__.py            ✅
├── __main__.py            ✅
└── main.py                ✅
```

### Risk Assessment

| Action | Risk | Mitigation |
|--------|------|------------|
| Delete `cli/` | **LOW** | Not imported anywhere |
| Delete `services/game_state_service.py` | **LOW** | Only old files use it |
| Delete `config.py` root | **LOW** | Only deprecated files use it |
| Delete `actions/game_actions.py` | **MEDIUM** | Keep redirect in `actions/__init__.py` |

### Execution Plan

```bash
# Step 1: Backup (just in case)
git status  # Check current state
git add -A  # Stage current state
git commit -m "Backup before cleanup"

# Step 2: Delete unused directories
rm -rf src/osrsbot/cli/

# Step 3: Delete duplicate services
rm src/osrsbot/services/game_state_service.py

# Step 4: Delete old root config
rm src/osrsbot/config.py

# Step 5: Delete old actions duplicate
rm src/osrsbot/actions/game_actions.py
# Keep: src/osrsbot/actions/__init__.py (backward compat)

# Step 6: Verify
python -c "from osrsbot.models import Config, GameState; print('OK')"
python -c "from osrsbot.controllers import GameActions; print('OK')"
python -c "from osrsbot.views import Calibrator; print('OK')"

# Step 7: Test bot
python -m osrsbot
```

### Summary

**Files to DELETE (5 files + 1 directory):**
1. `cli/` directory (entire folder with 4 files)
2. `services/game_state_service.py`
3. `config.py` (root)
4. `actions/game_actions.py`

**Files to KEEP:**
- Everything in `models/`, `controllers/`, `views/`, `services/`, `core/`, `scripts/`
- `actions/__init__.py` (backward compatibility redirect)

**Expected Outcome:**
- Cleaner codebase
- No duplicate files
- All imports point to correct locations
- Backward compatibility maintained via redirects
- Zero functional changes
