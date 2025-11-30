# OSRS Bot Refactoring Summary

## Overview
Successfully refactored the OSRS bot from a monolithic architecture to a clean service-based architecture with proper separation of concerns.

## What Was Changed

### New Files Created

#### Services Layer
- **`src/osrsbot/services/mouse_service.py`** - Professional mouse control with human-like movement
  - Bezier curve movement (OSBC-inspired)
  - Multiple movement styles (instant, linear, curved, overshoot, random)
  - Configurable speeds, variance, and overshoot
  - Anti-detection features

- **`src/osrsbot/services/screen_service.py`** - Screen capture and visual detection
  - Color finding and matching
  - Screenshot capture with regions
  - Image template matching
  - Wait for color/image functionality

- **`src/osrsbot/services/__init__.py`** - Package exports

#### Core Layer
- **`src/osrsbot/core/game_interface.py`** - Simplified GameInterface
  - Window finding and management ONLY
  - Coordinate translation (relative <-> absolute)
  - Window state checking
  - No longer handles clicking, colors, or screenshots

- **`src/osrsbot/core/__init__.py`** - Package exports

#### Actions Layer
- **`src/osrsbot/actions/game_actions.py`** - High-level game actions
  - Banking, teleporting, attacking, etc.
  - Uses services for low-level operations
  - Backward compatible with old Actions API

- **`src/osrsbot/actions/__init__.py`** - Package exports with backward compatibility alias

### Files Modified

#### Config (`src/osrsbot/config.py`)
Added new configuration sections:
- `colors.empty_inventory_slot` - "#4B423A"
- `colors.combat_indicator_green` - "#078B36"
- `colors.combat_indicator_red` - "#63150D"
- `coordinates.ocr.hp_region` - HP OCR region coordinates
- `ocr.hp_ttl` - OCR cache TTL (0.5s)
- `ocr.window_size` - OCR smoothing window size (5)
- `mouse.*` - Mouse service configuration

#### GameState (`src/osrsbot/game_state.py`)
**Removed hardcoded values:**
- Window title "RuneLite - 61grouphunt" (line 39)
- HP region coordinates (527, 79, 35, 20) (line 117)
- Combat indicator colors [(7, 139, 54), (99, 21, 19)] (line 275)
- Empty slot color (75, 66, 58) (line 260-261)

**Changes:**
- Now accepts `screen_service` parameter
- Uses ScreenService for pixel operations (with fallback to old interface)
- HPDetector now accepts config and reads values from it
- Added `_hex_to_rgb()` static method
- Removed unused `pygetwindow` import

#### ScriptRunner (`src/osrsbot/runner.py`)
**New initialization flow:**
1. Load Config
2. Initialize GameInterface (window management only)
3. Get window bounds
4. Initialize MouseService (with mouse config)
5. Initialize ScreenService (with window bounds)
6. Initialize GameState (with services)
7. Initialize GameActions (with services)

**Changes:**
- Imports from new locations (`osrsbot.core`, `osrsbot.services`, `osrsbot.actions`)
- Creates and configures MouseService and ScreenService
- Passes services to GameState and GameActions

#### Main (`src/osrsbot/main.py`)
**Removed hardcoded values:**
- Line 138: Hardcoded window title in dev mode

**Changes:**
- Dev mode now reads from environment variable `OSRS_WINDOW_TITLE` or prompts user

#### Scripts

**`src/osrsbot/scripts/green_dragons.py`:**
- Removed `time`, `pyautogui` imports
- Removed `GameInterface` import
- Changed all `interface.click_coord()` → `actions.click_coordinate()`
- Changed all `interface.click_color()` → `actions.click_color()`
- Changed `pyautogui.press('escape')` → `actions.close_interface()`

**`src/osrsbot/scripts/guns.py`:**
- Removed `time`, `pyautogui` imports
- Removed `GameInterface` import
- Changed `time.sleep(0.8)` → `actions.wait("short")`
- Changed all `interface.click_coord()` → `actions.click_coordinate()`
- Changed all `interface.click_color()` → `actions.click_color()`
- Changed `pyautogui.press('escape')` → `actions.close_interface()`

**`src/osrsbot/scripts/test.py`:**
- Removed `GameInterface` import
- Interface parameter no longer typed (accepts any)

### Files Not Modified (Kept for Reference)
- `src/osrsbot/game_interface.py` - Old version, can be deleted after testing
- `src/osrsbot/actions.py` - Old version, can be deleted after testing

## Architecture Changes

### Before (Monolithic)
```
Scripts → GameInterface (clicks, colors, screenshots)
       → GameState (state detection)
       → Actions (high-level actions)
       → Config
```

### After (Service-Based)
```
Scripts → GameActions (high-level actions)
            ↓
          MouseService (clicking, movement)
          ScreenService (colors, screenshots)
          Config
            ↓
          GameInterface (window management ONLY)

GameState → ScreenService (pixel operations)
         → GameInterface (window position)
         → Config
```

## Benefits

1. **Separation of Concerns**
   - Each component has a single responsibility
   - Services are reusable and testable
   - Clear dependency flow

2. **No Hardcoded Values**
   - All colors from config
   - All coordinates from config
   - All timings from config
   - Window titles from config/environment

3. **Better Testability**
   - Services can be mocked
   - No direct pyautogui calls in scripts
   - Clear dependency injection

4. **Human-like Behavior**
   - Bezier curve mouse movement
   - Random overshooting
   - Configurable click variance
   - Natural timing variations

5. **Backward Compatibility**
   - Scripts receive same parameters
   - `Actions` alias for `GameActions`
   - Gradual migration possible

## Testing

All imports verified working:
```python
from osrsbot.services.mouse_service import MouseService
from osrsbot.services.screen_service import ScreenService
from osrsbot.actions import Actions
from osrsbot.core import GameInterface
```

Scripts can import as before:
```python
from osrsbot.actions import Actions  # Works via alias
from osrsbot.game_state import GameState
from osrsbot.config import Config
```

## Next Steps

1. Test the bot with a real RuneLite window
2. Verify all scripts work correctly
3. Delete old files after confirming everything works:
   - `src/osrsbot/game_interface.py` (old)
   - `src/osrsbot/actions.py` (old)
4. Update config.json with new fields (auto-generated on first run)

## Environment Variables

- `OSRS_WINDOW_TITLE` - Set this to avoid typing window title in dev mode
  ```bash
  set OSRS_WINDOW_TITLE=RuneLite - YourUsername
  ```

## Known Issues

None - all imports working correctly!

## Git Branch

Currently on branch: `test-refactoring`

Safe to test without affecting main branch.
