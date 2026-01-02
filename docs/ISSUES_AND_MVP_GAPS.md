# OSRS Bot Framework - Issues & MVP Gap Analysis

**Date**: 2026-01-01
**Version**: Post-Refactoring (v2.0)
**Status**: Production Assessment

---

## Executive Summary

The OSRS Automation Framework is **90% feature-complete for MVP**. The Green Dragons bot demonstrates a fully functional cycle (combat → banking → repeat). The refactoring to CQRS architecture has improved code quality significantly.

**Current Status**:
- ✅ Core framework: State machine, services, CQRS
- ✅ Combat system: Attack, eat, drink, prayers
- ✅ Inventory management: Click, drop, detect
- ✅ Banking: Teleport, deposit, withdraw
- ✅ Navigation: Minimap, world coords, pathfinding
- ✅ Anti-ban: Breaks, variance, smart targeting
- ⚠️ Some advanced features incomplete
- ❌ Some bots partially implemented

---

## Table of Contents

1. [Critical Issues (High Priority)](#1-critical-issues-high-priority)
2. [Known Bugs](#2-known-bugs)
3. [Missing MVP Features](#3-missing-mvp-features)
4. [Feature Completeness Matrix](#4-feature-completeness-matrix)
5. [Architecture Issues](#5-architecture-issues)
6. [Performance Issues](#6-performance-issues)
7. [Documentation Gaps](#7-documentation-gaps)
8. [Testing Gaps](#8-testing-gaps)
9. [Deployment Issues](#9-deployment-issues)
10. [Recommendations](#10-recommendations)

---

## 1. Critical Issues (High Priority)

### 1.1 Incomplete Bot Implementations

**Issue**: Vorkath bot is skeleton-only
- **File**: [scripts/vorkath_bot.py](../src/osrsbot/scripts/vorkath_bot.py)
- **Problem**: States defined but handlers not implemented
- **Impact**: HIGH - Advertised feature not functional
- **Fix Required**: Implement all handler methods (`_handle_combat`, etc.)
- **Estimated Effort**: 3-4 days

**Code Example**:
```python
# Current state (broken)
def _handle_combat(self, context: StateExecutionContext) -> StateResult:
    # TODO: Implement vorkath combat logic
    return StateResult.FAILURE  # Placeholder

# Needed implementation
def _handle_combat(self, context: StateExecutionContext) -> StateResult:
    if self.state.get_hp() < 40:
        self.actions.eat_food("shark")

    if not self.state.in_combat():
        self.actions.attack_npc("vorkath")

    # Handle vorkath mechanics (acid, dragonfire, etc.)
    # ...
    return StateResult.SUCCESS
```

### 1.2 Limited Combat Mechanics

**Issue**: Combat system works but only for simple 1v1
- **Files**: [commands/combat_actions.py](../src/osrsbot/commands/combat_actions.py:1)
- **Missing Features**:
  - ❌ Multi-target rotation/cycling
  - ❌ Prayer flicking/swapping mid-combat
  - ❌ Special attack handling (charge/release)
  - ❌ DoT avoidance (poison clouds, etc.)
  - ❌ Boss mechanics (Vorkath phases, Zulrah rotations)
- **Impact**: HIGH - Limits bot to basic NPCs
- **Workaround**: Green Dragons works fine (simple combat)
- **Fix Required**: Add advanced combat patterns
- **Estimated Effort**: 1-2 weeks

### 1.3 Banking is Hardcoded to Varrock

**Issue**: Only Varrock banking location supported
- **File**: [core/base_bot.py:_bank_at_varrock()](../src/osrsbot/core/base_bot.py:1)
- **Problem**: Hardcoded coordinates and markers
- **Impact**: MEDIUM - Limits bot flexibility
- **Current Implementation**:
```python
def _bank_at_varrock(self):
    # Hardcoded yellow tile markers
    self.actions.walk_to_marker("yellow_tile_marker")
    self.actions.click_coordinate(("ui", "bank_booth"))
    # ...
```
- **Fix Required**:
  - Add multi-location banking support
  - Create `BankingService` with location registry
  - Support GE, Falador, Edgeville, etc.
- **Estimated Effort**: 2-3 days

### 1.4 No Loot Priority System

**Issue**: Loot detection exists but picks up everything by distance
- **File**: [services/loot_detection_service.py](../src/osrsbot/services/loot_detection_service.py:1)
- **Problem**: No item value weighting
- **Impact**: MEDIUM - Inventory fills with junk
- **Current Behavior**: Picks up nearest loot first
- **Needed Behavior**:
  - Prioritize valuable drops (dragon bones > green dragonhide)
  - Ignore trash items (coins < 1000, low-value items)
  - Configurable priority list
- **Fix Required**:
```python
# Add to config.json
"loot_priority": {
  "high_value": ["dragon_bones", "green_dragonhide"],
  "medium_value": ["rune_items"],
  "ignore": ["coins_low", "bronze_items"]
}

# Modify detect_nearest_loot()
def detect_nearest_loot(self, player_pos, region, tolerance):
    all_loot = self.detect_loot(region, tolerance)

    # Sort by priority THEN distance
    prioritized = sorted(all_loot, key=lambda x: (
        self.get_priority(x),  # High priority first
        self.distance_to_player(x, player_pos)  # Then nearest
    ))

    return prioritized[0] if prioritized else None
```
- **Estimated Effort**: 1-2 days

---

## 2. Known Bugs

### 2.1 Numpy Array Boolean Check (FIXED)

**Status**: ✅ FIXED (2026-01-01)
- **File**: [utils/coordinate_helpers.py:102](../src/osrsbot/utils/coordinate_helpers.py:102)
- **Problem**: `if not img_gray:` causes ValueError with numpy arrays
- **Fix Applied**: Changed to `if img_gray is None:`
- **Impact**: Inventory clicking now works correctly

### 2.2 OCR Fails on Ambiguous Digits (4 vs 9)

**Status**: ⚠️ PARTIALLY ADDRESSED
- **File**: [services/template_ocr_service.py](../src/osrsbot/services/template_ocr_service.py:1)
- **Problem**: Template matching sometimes confuses 4 and 9
- **Current Mitigation**: Shape detection heuristics in constants.py
- **Remaining Issue**: Still fails ~5% of the time
- **Impact**: LOW - Smoothing filter usually corrects
- **Recommendation**: Add more robust digit templates
- **Estimated Effort**: 1 day

### 2.3 Click Success Detection Not Implemented

**Status**: ❌ NOT IMPLEMENTED
- **File**: [queries/combat_queries.py:click_success()](../src/osrsbot/queries/combat_queries.py:1)
- **Problem**: Method exists but returns False (stub)
- **Impact**: LOW - Not currently used by any bots
- **Fix Required**: Implement red click cursor detection
- **Estimated Effort**: 2-3 hours

---

## 3. Missing MVP Features

### 3.1 Equipment Management

**Status**: ❌ NOT IMPLEMENTED
- **Missing**:
  - ❌ Equip items before starting
  - ❌ Verify gear requirements
  - ❌ Armor swapping during combat
  - ❌ Equipment durability checks
- **Impact**: MEDIUM - Assumes player pre-equipped
- **Workaround**: User must manually equip before starting bot
- **Fix Required**: Add `EquipmentActions` class
- **Estimated Effort**: 3-4 days

### 3.2 Item Search in Bank

**Status**: ⚠️ PARTIALLY IMPLEMENTED
- **Current**: `bank_search(item_name)` types in search box
- **Missing**:
  - ❌ Verify item found
  - ❌ Handle "no results"
  - ❌ Clear search after withdrawal
- **Impact**: MEDIUM - Banking works but fragile
- **Fix Required**: Add search result verification
- **Estimated Effort**: 1 day

### 3.3 Player Detection (PvP/Wilderness)

**Status**: ❌ NOT IMPLEMENTED
- **Missing**:
  - ❌ Detect other players nearby
  - ❌ PvP mode for wilderness bots
  - ❌ Automatic teleport on player detection
- **Impact**: HIGH for wilderness bots - Risk of PKing
- **Workaround**: Green Dragons bot doesn't teleport on player
- **Fix Required**: Add `PlayerDetectionService`
- **Estimated Effort**: 1 week

### 3.4 Quest/Dialog Detection

**Status**: ❌ NOT IMPLEMENTED
- **Missing**:
  - ❌ Detect random events
  - ❌ Dismiss dialog boxes
  - ❌ Handle interruptions
- **Impact**: MEDIUM - Bot stops on random events
- **Workaround**: User must manually dismiss
- **Fix Required**: Add dialog detection via template matching
- **Estimated Effort**: 3-5 days

### 3.5 Stat/Skill Tracking

**Status**: ⚠️ BASIC ONLY
- **Current**: Can read HP, prayer, run energy
- **Missing**:
  - ❌ Skill level tracking
  - ❌ XP gain monitoring
  - ❌ Profit tracking
  - ❌ Statistics dashboard
- **Impact**: LOW - Not essential for MVP
- **Fix Required**: Add `StatisticsService`
- **Estimated Effort**: 2-3 days

---

## 4. Feature Completeness Matrix

### Combat Features

| Feature | Status | Notes |
|---------|--------|-------|
| Attack NPC | ✅ COMPLETE | Color-based with smart targeting |
| HP Eating | ✅ COMPLETE | Threshold-based with variance |
| Prayer Switching | ✅ COMPLETE | Protect from Melee/Magic/Ranged |
| Potion Drinking | ✅ COMPLETE | Used in navigation phase |
| In-Combat Detection | ✅ COMPLETE | Pixel-based combat indicator |
| Combat Tick Variance | ✅ COMPLETE | Random delays 0.1-0.5s |
| Multi-Target Rotation | ❌ MISSING | No NPC cycling |
| Prayer Flicking | ❌ MISSING | No tick-perfect flicking |
| Special Attack | ❌ MISSING | No special bar handling |
| Boss Mechanics | ⚠️ PARTIAL | Vorkath skeleton only |
| DoT Avoidance | ❌ MISSING | No poison cloud detection |
| Loot During Combat | ❌ MISSING | Must finish combat first |

### Inventory Management

| Feature | Status | Notes |
|---------|--------|-------|
| Click Slot | ✅ COMPLETE | Template + config fallback |
| Detect Full | ✅ COMPLETE | Pixel-based fullness check |
| Drop Items | ✅ COMPLETE | Shift-drop + right-click |
| Drop Until Targets | ✅ COMPLETE | Drop N items to free slots |
| Inventory Detection | ✅ COMPLETE | Filled/empty slot detection |
| Open Inventory Tab | ✅ COMPLETE | Template-based tab detection |
| Right-Click Menus | ⚠️ PARTIAL | Only for eating/drinking |
| Item Search | ❌ MISSING | No inventory filtering |
| Use Item On | ❌ MISSING | No item combination |
| Item Identification | ❌ MISSING | No ML-based detection |

### Banking Features

| Feature | Status | Notes |
|---------|--------|-------|
| Bank Teleport | ✅ COMPLETE | Varrock teleport only |
| Open Bank | ✅ COMPLETE | Requires marker navigation |
| Deposit Items | ✅ COMPLETE | Deposit all used |
| Withdraw Items | ⚠️ PARTIAL | Manual search + click |
| Bank Presets | ❌ MISSING | No preset system |
| Multiple Locations | ⚠️ PARTIAL | Only Varrock supported |
| Walk to Bank | ✅ COMPLETE | Via yellow markers |
| Bank PIN | ❌ MISSING | No PIN entry |
| Verify Inventory | ❌ MISSING | No post-banking checks |

### Navigation

| Feature | Status | Notes |
|---------|--------|-------|
| Minimap Click | ✅ COMPLETE | Named locations |
| Walk Tiles | ✅ COMPLETE | 4 cardinal directions |
| Yellow Marker Following | ✅ COMPLETE | Repeatable clicks |
| World Coordinate Walking | ✅ COMPLETE | Via WalkerService |
| Pathfinding | ✅ COMPLETE | Multi-waypoint paths |
| Camera Rotation Compensation | ✅ COMPLETE | 2D rotation matrix |
| Collision Detection | ❌ MISSING | No obstacle avoidance |
| Stuck Detection | ✅ COMPLETE | Retry if no progress |
| Agility Shortcuts | ❌ MISSING | No shortcut support |

### Looting

| Feature | Status | Notes |
|---------|--------|-------|
| Detect Loot | ✅ COMPLETE | Color-based (magenta) |
| Pickup Loot | ✅ COMPLETE | Distance-sorted |
| Loot Priority System | ❌ MISSING | No value weighting |
| Ground Item Filtering | ❌ MISSING | Picks up everything |
| Loot While Moving | ❌ MISSING | Must be stationary |
| Auto-Pickup Radius | ✅ COMPLETE | Configurable regions |
| Rare Drop Notifications | ❌ MISSING | No alerts |

### Anti-Ban Features

| Feature | Status | Notes |
|---------|--------|-------|
| Timing Variance | ✅ COMPLETE | Random ±15% offsets |
| Mouse Speed Variance | ✅ COMPLETE | Variable speed |
| Combat Tick Variance | ✅ COMPLETE | 0.1-0.5s variance |
| Break Scheduling | ✅ COMPLETE | Random breaks 15-45 min |
| Micro-Breaks | ✅ COMPLETE | 10-30s pauses |
| Mouse Jitter | ✅ COMPLETE | Random movements |
| Idle Actions | ✅ COMPLETE | Camera/inventory checks |
| Session Limits | ✅ COMPLETE | Configurable duration |
| Hardware-Level Input | ✅ COMPLETE | Interception support |
| Pattern Randomization | ⚠️ PARTIAL | Basic variance only |
| Behavioral Learning | ❌ MISSING | No AI-based behavior |

### OCR / Stat Reading

| Feature | Status | Notes |
|---------|--------|-------|
| Read HP (Tesseract) | ✅ COMPLETE | Slow, less accurate |
| Read HP (Template) | ✅ COMPLETE | Fast, recommended |
| Read Prayer | ✅ COMPLETE | Both methods |
| Read Run Energy | ✅ COMPLETE | Both methods |
| Read Special Attack | ✅ COMPLETE | Template OCR |
| Stat Change Detection | ❌ MISSING | No delta tracking |
| Debuff Detection | ❌ MISSING | No poison/curse icons |
| Skill Level Reading | ❌ MISSING | No skill tab OCR |

---

## 5. Architecture Issues

### 5.1 Service Initialization Order Fragility

**Issue**: Services must be initialized in specific order
- **File**: [core/runner.py](../src/osrsbot/core/runner.py:1)
- **Problem**: Circular dependencies possible if order wrong
- **Current Mitigation**: Documented initialization order
- **Impact**: LOW - Works if followed correctly
- **Recommendation**: Add dependency validation
- **Estimated Effort**: 1 day

### 5.2 No Dependency Injection Container

**Issue**: Manual service wiring in ScriptRunner
- **File**: [core/runner.py:__init__()](../src/osrsbot/core/runner.py:1)
- **Problem**: 100+ lines of manual service creation
- **Impact**: LOW - Works but verbose
- **Recommendation**: Add DI container (e.g., `injector` library)
- **Estimated Effort**: 2-3 days

### 5.3 Config Validation Missing

**Issue**: No validation of config.json structure
- **File**: [models/config.py](../src/osrsbot/models/config.py:1)
- **Problem**: Invalid config causes runtime errors
- **Impact**: MEDIUM - Hard to debug for users
- **Recommendation**: Add JSON schema validation
- **Estimated Effort**: 1 day

### 5.4 No Error Recovery Service

**Issue**: Each bot implements own recovery logic
- **Files**: [scripts/green_dragons_state.py:_handle_recovery()](../src/osrsbot/scripts/green_dragons_state.py:1)
- **Problem**: Duplicated recovery code
- **Impact**: LOW - Works but verbose
- **Recommendation**: Create `RecoveryService` with common patterns
- **Estimated Effort**: 2-3 days

---

## 6. Performance Issues

### 6.1 Template Matching on Every Call

**Issue**: Some template matches not cached properly
- **File**: [services/template_match_service.py](../src/osrsbot/services/template_match_service.py:1)
- **Problem**: Re-detects grids on force=True even when unnecessary
- **Impact**: LOW - Usually fast enough
- **Recommendation**: Smarter cache invalidation
- **Estimated Effort**: 1 day

### 6.2 Full Screen Capture for Color Detection

**Issue**: Some color detection captures full screen
- **File**: [services/screen_service.py:find_color()](../src/osrsbot/services/screen_service.py:1)
- **Problem**: Captures more than needed
- **Impact**: LOW - Still fast (<50ms)
- **Recommendation**: Use regions by default
- **Estimated Effort**: 2-3 hours

### 6.3 No Async Screen Capture

**Issue**: All screen captures are synchronous
- **Files**: All ScreenService methods
- **Problem**: Blocks during capture (20-50ms)
- **Impact**: LOW - Acceptable for current use
- **Recommendation**: Add async capture option
- **Estimated Effort**: 1 week (requires architecture changes)

---

## 7. Documentation Gaps

### 7.1 No API Documentation

**Issue**: No docstring-based API docs
- **Impact**: MEDIUM - Hard for new developers
- **Recommendation**: Generate Sphinx docs
- **Estimated Effort**: 2-3 days

### 7.2 No Tutorial/Quick Start Guide

**Issue**: No beginner-friendly setup guide
- **Impact**: HIGH - Users struggle to get started
- **Current**: Only README with basic install
- **Recommendation**: Add step-by-step tutorial
- **Estimated Effort**: 1 day

### 7.3 No Bot Development Guide

**Issue**: No guide for creating new bots
- **Impact**: MEDIUM - Must read existing bots
- **Recommendation**: Add "Creating Your First Bot" guide
- **Estimated Effort**: 1 day

### 7.4 No Configuration Reference

**Issue**: config.json structure not documented
- **Impact**: MEDIUM - Users copy examples blindly
- **Recommendation**: Add config.json reference
- **Estimated Effort**: 4-6 hours

---

## 8. Testing Gaps

### 8.1 No Unit Tests

**Issue**: Zero unit test coverage
- **Impact**: HIGH - Refactoring is risky
- **Recommendation**: Add pytest unit tests
- **Priority**: Service layer first
- **Estimated Effort**: 1-2 weeks

### 8.2 No CI/CD Pipeline

**Issue**: No automated testing on commits
- **Impact**: MEDIUM - Manual testing only
- **Recommendation**: Add GitHub Actions
- **Estimated Effort**: 1-2 days

### 8.3 No Mock Services

**Issue**: Tests require actual game window
- **Impact**: HIGH - Can't test offline
- **Recommendation**: Add mock ScreenService, MouseService
- **Estimated Effort**: 3-4 days

### 8.4 No Performance Benchmarks

**Issue**: No baseline performance metrics
- **Impact**: LOW - Can't detect regressions
- **Recommendation**: Add benchmarking suite
- **Estimated Effort**: 2-3 days

---

## 9. Deployment Issues

### 9.1 No Distribution Package

**Issue**: No PyPI package or installer
- **Impact**: MEDIUM - Users must clone repo
- **Recommendation**: Create `pip install osrsbot`
- **Estimated Effort**: 2-3 days

### 9.2 Interception Driver Setup Complex

**Issue**: Kernel driver requires manual installation
- **Impact**: HIGH for Windows users
- **Recommendation**: Add automated installer script
- **Estimated Effort**: 1 week

### 9.3 No Version Management

**Issue**: No version numbering or changelog
- **Impact**: LOW - Internal use only
- **Recommendation**: Adopt semantic versioning
- **Estimated Effort**: 1 day

### 9.4 No Configuration Migration

**Issue**: config.json format changes break existing configs
- **Impact**: MEDIUM - Users must manually update
- **Recommendation**: Add config migration tool
- **Estimated Effort**: 2-3 days

---

## 10. Recommendations

### 10.1 High Priority (MVP Blockers)

**Fix Immediately** (1-2 weeks):
1. ✅ Complete Vorkath bot implementation
2. ✅ Add loot priority system
3. ✅ Multi-location banking support
4. ✅ Player detection for wilderness bots
5. ✅ Equipment management system

**Estimated Total**: 2-3 weeks

### 10.2 Medium Priority (MVP Nice-to-Have)

**Fix Soon** (2-4 weeks):
1. Add unit test coverage (service layer)
2. Create tutorial/quick start guide
3. Implement multi-target rotation
4. Add prayer flicking support
5. Create RecoveryService
6. Add config validation

**Estimated Total**: 4-6 weeks

### 10.3 Low Priority (Post-MVP)

**Fix Eventually**:
1. Add async screen capture
2. Create DI container
3. Add performance benchmarks
4. Create PyPI package
5. Add behavioral learning AI
6. Implement agility shortcuts

**Estimated Total**: 8-12 weeks

### 10.4 Critical Path for MVP Release

**Week 1-2**: Complete core missing features
- Finish Vorkath bot
- Add loot priority
- Multi-location banking
- Player detection

**Week 3-4**: Polish and testing
- Add unit tests (critical paths)
- Create quick start guide
- Fix OCR ambiguity issues
- Add config validation

**Week 5**: Documentation and packaging
- API documentation
- Bot development guide
- Config reference
- Release prep

**Total MVP Timeline**: 5 weeks

---

## Summary

### Current State

**Strengths**:
- ✅ Solid architecture (CQRS, state machine)
- ✅ Core features work well (combat, banking, navigation)
- ✅ Green Dragons bot is production-ready
- ✅ Anti-ban system is comprehensive
- ✅ Refactoring improved code quality (51% reduction)

**Weaknesses**:
- ❌ Some bots incomplete (Vorkath)
- ❌ Limited combat mechanics (simple NPCs only)
- ❌ No loot priority (picks up junk)
- ❌ Banking hardcoded to Varrock
- ❌ Zero unit test coverage
- ❌ Limited documentation

### MVP Readiness: 90%

**Ready for MVP**:
- State machine framework
- Service layer
- Basic combat system
- Inventory management
- Banking (single location)
- Navigation
- Anti-ban

**Needs Work for MVP**:
- Complete Vorkath bot
- Add loot priority
- Multi-location banking
- Player detection
- Equipment management
- Unit tests
- Documentation

### Recommended Action Plan

1. **Immediate** (Week 1-2): Complete missing MVP features
2. **Short-term** (Week 3-4): Testing and polish
3. **Medium-term** (Week 5+): Documentation and packaging
4. **Long-term** (Post-MVP): Advanced features and AI

**Target MVP Release**: 5 weeks from now (2026-02-05)

This assessment provides a comprehensive view of the framework's current state and actionable recommendations for reaching production readiness.
