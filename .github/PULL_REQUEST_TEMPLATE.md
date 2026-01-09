# Major Framework Improvements: Architecture Documentation, Bankstanding System & Combat Bots

## 🎯 Overview

This PR introduces significant improvements to the OSRS Bot Framework including comprehensive architecture documentation, enhanced bankstanding system, new combat bots, and critical architecture fixes.

---

## 📚 Documentation

### Architecture Documentation (NEW)
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Complete 1,500+ line verified architecture guide
  - Layered architecture with ASCII diagrams
  - Dependency injection system documentation
  - CQRS implementation details (Commands vs Queries)
  - Service layer comprehensive reference (13+ services)
  - State machine framework documentation
  - 7 design patterns with real code examples
  - Execution flow diagrams
  - Extension points for developers
  - Every claim verified with file paths and line numbers

### Setup & Learning Guides (NEW)
- **[QUICK_START_SETUP.md](docs/QUICK_START_SETUP.md)** - 10-minute setup guide
- **[BEGINNER_DEVELOPER_GUIDE.md](docs/BEGINNER_DEVELOPER_GUIDE.md)** - Progressive learning path (Level 0-5)
- **[SETUP_VERIFICATION.md](docs/SETUP_VERIFICATION.md)** - Installation verification checklist
- **[BASIC_NPC_KILLER_GUIDE.md](docs/BASIC_NPC_KILLER_GUIDE.md)** - Combat bot usage guide

### Implementation Summaries (NEW)
- **[SESSION_SUMMARY_2026-01-09.md](docs/SESSION_SUMMARY_2026-01-09.md)** - Development session notes
- **[ARCHITECTURE_FIX_MOVEMENTSTYLE.md](docs/ARCHITECTURE_FIX_MOVEMENTSTYLE.md)** - Type refactoring explanation
- **[ZULRAH_IMPLEMENTATION_SUMMARY.md](docs/ZULRAH_IMPLEMENTATION_SUMMARY.md)** - Zulrah bot architecture

### UI Debugging Documentation (Reorganized)
- Moved to `docs/ui_debugging/`
  - UI_DEBUG_GUIDE.md
  - UI_DEBUG_QUICKREF.md
  - UI_INTEGRATION_SUMMARY.md

---

## 🏗️ Architecture Improvements

### Critical Fix: Layer Boundary Violation
**Problem:** Commands layer (`GameActions`) was importing from Services layer (`MouseService`), violating layered architecture principles.

**Solution:** Moved `MovementStyle` type to `constants.py`
- ✅ `constants.py`: Added `MovementStyle` as `Literal` type
- ✅ `services/__init__.py`: Re-export from constants
- ✅ `commands/*.py`: Import from constants
- ✅ `services/mouse_service.py`: Import from constants
- ✅ `services/walker_service.py`: Import from constants

**Impact:** Preserves layer boundaries - Commands can import from Constants, not Services directly.

---

## 🤖 New Features

### 1. Bankstanding System Enhancement
**File:** `src/osrsbot/core/base_bankstander.py`

Complete reusable template for bankstanding bots:
- State machine with IDLE → BANKING → PROCESS → DEPOSIT → RECOVERY
- Automatic bank interaction
- Item searching and withdrawal
- Abstract `process_items()` method for custom logic
- Template matching for item detection
- Error recovery

**Example Implementation:** `scripts/bankstanding/bankstanding_flax.py`
- Manual herb cleaning bot
- Pattern variation (sequential, random, column-by-column)
- Anti-ban micro-breaks
- Session variance in timing

### 2. Basic NPC Killer Bot (NEW)
**File:** `src/osrsbot/scripts/combat/basic_npc_killer.py`

State machine-based combat bot with dual detection methods:

**Features:**
- ✅ **Dual NPC Detection:**
  - Color detection (default) - Uses RuneLite NPC highlights
  - Template matching (fallback) - Visual pattern matching
- ✅ Kill → Loot → Repeat until inventory full
- ✅ Smart targeting with blacklist tracking
- ✅ Inventory full detection (pixel-based)
- ✅ Loot detection using `LootDetectionService`
- ✅ Exit key support ('q')
- ✅ Kill/loot statistics tracking

**States:**
```
IDLE → FIND_NPC → ATTACK_NPC → WAIT_COMBAT → LOOT → CHECK_INVENTORY
```

**Strategy Pattern Implementation:**
```python
def _find_npc(self):
    if self.npc_detection_method == "color":
        return self._find_npc_by_color()
    elif self.npc_detection_method == "template":
        return self._find_npc_by_template()
```

### 3. NMZ AFK Bot (Enhanced)
**File:** `src/osrsbot/scripts/afk/nmz_afk.py`

Nightmare Zone absorption strategy bot:
- Timer-based drinking (absorption/overload)
- Rock cake HP management
- Prayer flicking
- Status monitoring

---

## 📁 Project Reorganization

### Scripts Directory Structure (NEW)
```
src/osrsbot/scripts/
├── afk/                  # AFK farming bots
│   └── nmz_afk.py
├── bankstanding/         # Bankstanding scripts
│   ├── bankstanding_flax.py
│   └── bankstander_example.py
├── bosses/               # Boss fight bots
│   ├── vorkath_bot.py
│   ├── zulrah.py
│   ├── zulrah_combat_manager.py
│   ├── zulrah_detector.py
│   └── zulrah_navigator.py
├── combat/               # Combat scripts
│   ├── basic_npc_killer.py
│   └── green_dragons_state.py
├── skills/               # Skill training bots
│   └── mining_bot.py
└── tests/                # Test/debug bots
    ├── comprehensive_state_bot_test.py
    ├── hp_tracker.py
    └── test_inventory_clicks.py
```

Each category now has `__init__.py` for proper module structure.

### Other Reorganizations
- Moved `debug_ui_elements.py` → `tests/debug/`
- Moved `loc.py` → `tools/`
- Moved `example_ui_debug_bot.py` → `examples/`
- Moved `ui_manager.py` → `services/ui_manager_service.py` (consistent naming)

---

## 🔧 Code Quality Improvements

### Removed Dead Code
- ❌ `src/osrsbot/commands/game_actions_old.py` - Replaced by modular system
- ❌ `src/osrsbot/queries/game_queries_old.py` - Replaced by modular system
- ❌ `src/osrsbot/scripts/workspace.code-workspace` - Not needed in source control

### Menu Updates
**File:** `src/osrsbot/app/menu.py`

Added new bot options:
```
8. Basic NPC Killer (NEW)
```

---

## 🎨 Design Patterns Documented

This PR documents the following patterns actually used in the codebase:

1. **Dependency Injection** - `runner.py` - Centralized service initialization
2. **Facade Pattern** - `game_actions.py`, `game_queries.py` - Simplified interfaces
3. **State Machine Pattern** - `state_machine_bot.py` - Bot execution flow
4. **Template Method Pattern** - `base_bot.py` - Execution skeleton
5. **Strategy Pattern** - `mouse_service.py`, `basic_npc_killer.py` - Runtime algorithm selection
6. **CQRS Pattern** - `commands/` + `queries/` - Separated reads/writes
7. **Adapter Pattern** - Mouse service variants - Platform abstractions

---

## 📊 Statistics

- **Files Changed:** 44
- **Lines Added:** 4,087
- **Lines Removed:** 1,606
- **New Documentation:** 8 files (2,500+ lines)
- **New Bots:** 1 (Basic NPC Killer)
- **Enhanced Bots:** 2 (Bankstander, NMZ AFK)
- **Architecture Fixes:** 1 (MovementStyle import violation)

---

## ✅ Testing

### Verified Functionality
- ✅ Manual Cleaning Bankstander (bankstanding_flax.py) - Tested
- ✅ NMZ AFK Bot - Tested
- ⚠️ Basic NPC Killer - Implementation complete, needs field testing
- ⚠️ Zulrah Bot - Skeleton implementation

### Installation Verified
- ✅ Python 3.13.5 - Working
- ✅ `pip install -e .` - All dependencies install correctly
- ✅ Import test: `python -c "import osrsbot"` - Success
- ✅ Bot menu: `python -m osrsbot` - Launches correctly

---

## 🔄 Breaking Changes

**None.** All changes are backward compatible.

- Old code using `actions.click_inventory_slot()` still works (facade methods preserved)
- New code can use `actions.inventory.click_slot()` (focused modules)
- `MovementStyle` import location changed but re-exported from `services/__init__.py`

---

## 📖 Documentation Index

### For New Users
1. Start with [QUICK_START_SETUP.md](docs/QUICK_START_SETUP.md) - Get running in 10 minutes
2. Follow [BEGINNER_DEVELOPER_GUIDE.md](docs/BEGINNER_DEVELOPER_GUIDE.md) - Learn progressively

### For Developers
1. Read [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Understand the framework
2. Check [BASIC_NPC_KILLER_GUIDE.md](docs/BASIC_NPC_KILLER_GUIDE.md) - Example bot walkthrough
3. Review [SESSION_SUMMARY_2026-01-09.md](docs/SESSION_SUMMARY_2026-01-09.md) - Recent work

### For Debugging
1. [UI_DEBUG_GUIDE.md](docs/ui_debugging/UI_DEBUG_GUIDE.md) - UI element debugging
2. [SETUP_VERIFICATION.md](docs/SETUP_VERIFICATION.md) - Installation troubleshooting

---

## 🎯 Next Steps

After this PR is merged:

1. **Field Testing**
   - Test Basic NPC Killer on various NPCs (cows, chickens, goblins)
   - Verify NMZ AFK bot stability over extended sessions
   - Test Bankstander with different items

2. **Feature Enhancements**
   - Add food eating to Basic NPC Killer
   - Implement banking for combat bots
   - Add prayer support to NPC killer

3. **Documentation**
   - Add video tutorials
   - Create contribution guide
   - Document common bot patterns

4. **Testing**
   - Add unit tests for state machines
   - Mock services for testing
   - Create integration test suite

---

## 🙏 Acknowledgments

This work includes:
- Comprehensive architecture analysis of the existing framework
- Documentation of design patterns already in use
- Organization of scripts into logical categories
- Preservation of all working functionality while improving structure

All code follows established patterns in the codebase and maintains backward compatibility.

---

## 📝 Reviewer Notes

**Key Files to Review:**

1. **Architecture:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Verify accuracy against codebase
2. **Core Framework:** [src/osrsbot/core/base_bankstander.py](src/osrsbot/core/base_bankstander.py) - Reusable template pattern
3. **New Bot:** [src/osrsbot/scripts/combat/basic_npc_killer.py](src/osrsbot/scripts/combat/basic_npc_killer.py) - Strategy pattern example
4. **Architecture Fix:** [src/osrsbot/constants.py](src/osrsbot/constants.py) - MovementStyle type location

**Questions for Review:**

1. Is the architecture documentation accurate and helpful?
2. Should we add more examples to the beginner guide?
3. Are the script categories organized logically?
4. Should we create a `CONTRIBUTING.md` before accepting external PRs?

---

**Co-Authored-By:** Claude Sonnet 4.5 <noreply@anthropic.com>
