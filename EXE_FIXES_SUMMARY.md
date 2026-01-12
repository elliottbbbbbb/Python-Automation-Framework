# OSRS Bot .exe Fixes Summary

**Date:** 2026-01-12
**Issue:** Bot .exe was not loading external config.json or finding bundled image files

---

## Problems Identified

1. **Config Loading**: Bot always loaded bundled config from inside .exe, ignoring external `config.json` next to executable
2. **Image Path Resolution**: Template images with paths like `src/osrsbot/images/...` couldn't be found when running as .exe
3. **Windows Path Separators**: Path comparisons failed because Windows uses backslashes `\` but code checked for forward slashes `/`
4. **Broken Fallback Logic**: Runner.py had non-functional fallback code causing TypeError
5. **No Debug Logging**: When .exe crashed, terminal closed immediately with no error logs
6. **Missing Exit Key**: Some scripts didn't support pressing 'q' to exit gracefully

---

## Changes Made

### 1. Config Loading Priority Fix
**File:** `src/osrsbot/models/config.py` (lines 13-33)

**What Changed:**
- Modified `Config.__init__()` to detect when running as .exe (`sys.frozen`)
- When running as .exe, now **prioritizes external config.json** next to executable
- Only falls back to bundled config if external doesn't exist

**Impact:**
- Users can now modify `config.json` next to the .exe and changes will be used
- Dev workflow unchanged (still uses `src/osrsbot/config.json`)

```python
# Before: Always used src/osrsbot/config.json
# After: Checks for external config.json first when running as .exe
if getattr(sys, "frozen", False):
    external_config = Path(sys.executable).parent / "config.json"
    if external_config.exists():
        self.config_file = external_config  # Use external!
```

---

### 2. Image Path Resolution - UI Templates
**File:** `src/osrsbot/models/ui_elements.py` (lines 170-180, 413-423)

**What Changed:**
- Updated `UIElementGrid._load_template()` and `UIButton._load_template()`
- Added path resolution logic to convert relative paths to bundled locations
- Fixed Windows backslash issue by normalizing paths before comparison

**Impact:**
- UI template images from config.json now load correctly from bundled .exe
- Paths like `src/osrsbot/images/bot/ui_templates/inventory_empty.PNG` resolve to `sys._MEIPASS/osrsbot/images/...`

```python
# Normalize Windows backslashes to forward slashes for comparison
normalized_path = self.template_path.replace("\\", "/")

if normalized_path.startswith("src/osrsbot/"):
    relative_path = normalized_path.replace("src/osrsbot/", "", 1)
    template_path = Path(sys._MEIPASS) / "osrsbot" / relative_path
```

---

### 3. Image Path Resolution - Template Matching
**File:** `src/osrsbot/queries/bank_queries.py` (lines 29-60, 81, 129, 194)

**What Changed:**
- Created helper function `_resolve_template_path()` for consistent path resolution
- Applied to all 3 cv.imread() calls in bank_queries.py:
  - `is_bank_open()` - Bank search button template
  - `find_template()` - General template matching
  - `find_best_template()` - Multi-template matching

**Impact:**
- Hardcoded image paths in scripts (like NMZ) now work correctly
- `click_template()` calls resolve paths automatically

---

### 4. Runner.py Fallback Logic Fix
**File:** `src/osrsbot/core/runner.py` (lines 73-95)

**What Changed:**
- Fixed broken fallback that caused `TypeError: unsupported operand type(s) for /: 'str' and 'str'`
- Line 80 had `sys._MEIPASS / "osrsbot" / "config.json"` which did nothing (strings can't use `/` operator)
- Properly implemented fallback to bundled config using `Path(sys._MEIPASS)`

**Impact:**
- No more TypeError crashes
- Config loading has proper fallback chain: external → bundled → error

---

### 5. Debug Logging System
**File:** `src/osrsbot/app/menu.py` (lines 42-61, 376-392)

**What Changed:**
- Added `osrs_bot_debug.log` file handler that writes next to .exe
- Logs everything to both console AND file simultaneously
- Added fatal error handler that catches unhandled exceptions
- Terminal stays open with "Press Enter to exit..." prompt on crash

**Impact:**
- When .exe crashes, full error details saved to `osrs_bot_debug.log`
- No more instant terminal closes losing error messages
- Easy debugging for end users

```python
# Log file next to .exe
log_file = Path(sys.executable).parent / "osrs_bot_debug.log"

# Both handlers
handlers=[
    logging.StreamHandler(sys.stdout),  # Console
    logging.FileHandler(log_file, mode='w', encoding='utf-8')  # File
]
```

---

### 6. Exit Key Support (Press 'q' to Exit)
**Files Modified:**
- `src/osrsbot/scripts/afk/nmz_afk.py` (line 496)
- `src/osrsbot/scripts/bosses/zulrah.py` (line 352)
- `src/osrsbot/scripts/tests/comprehensive_state_bot_test.py` (line 1003)

**What Changed:**
- Added `self._check_exit_requested()` calls to main loops
- Checks for user pressing 'q' key to gracefully exit

**Impact:**
- All major scripts now support pressing 'q' to exit cleanly
- No need to force-close or Ctrl+C

**Scripts with Exit Support:**
- ✅ NMZ AFK Bot
- ✅ Zulrah Boss Bot
- ✅ Basic NPC Killer (already had it)
- ✅ Bankstanding Flax (already had it)
- ✅ Comprehensive Test Bot
- ✅ Bankstander Example (already had it)

---

## Technical Details

### Windows Path Issue
The core problem was Windows path normalization:
```python
# Input path (forward slashes)
template_path = "src/osrsbot/images/bot/items/overload_potion.png"

# After Path() on Windows (backslashes)
Path(template_path) → "src\osrsbot\images\bot\items\overload_potion.png"

# Check failed because of backslashes
str(path).startswith("src/osrsbot/")  # FALSE! ❌

# Solution: Normalize before comparing
normalized = template_path.replace("\\", "/")
normalized.startswith("src/osrsbot/")  # TRUE! ✅
```

### PyInstaller Bundle Structure
```
my_bot.exe
├── sys._MEIPASS/ (temporary extraction folder)
│   └── osrsbot/
│       ├── config.json (bundled fallback)
│       └── images/
│           └── bot/
│               ├── items/
│               └── ui_templates/
└── config.json (external - user editable) ← Now prioritized!
```

---

## Testing Checklist

Before deploying, verify:

- [ ] Rebuild .exe with PyInstaller
- [ ] External `config.json` next to .exe is loaded (check log for "Using external config")
- [ ] Modify external config, verify changes take effect
- [ ] NMZ script finds overload/absorption potion images
- [ ] UI templates load (inventory, prayer tab, etc.)
- [ ] Press 'q' during script execution exits gracefully
- [ ] Check `osrs_bot_debug.log` created next to .exe
- [ ] Force an error, verify terminal stays open with prompt

---

## Files Modified Summary

| File | Lines Changed | Purpose |
|------|--------------|---------|
| `src/osrsbot/models/config.py` | 13-33 | External config priority |
| `src/osrsbot/models/ui_elements.py` | 170-180, 413-423 | UI template path resolution |
| `src/osrsbot/queries/bank_queries.py` | 29-60, 81, 129, 194 | Template matching path resolution |
| `src/osrsbot/core/runner.py` | 73-95 | Fixed broken fallback logic |
| `src/osrsbot/app/menu.py` | 42-61, 376-392 | Debug logging & error handling |
| `src/osrsbot/scripts/afk/nmz_afk.py` | 496 | Exit key support |
| `src/osrsbot/scripts/bosses/zulrah.py` | 352 | Exit key support |
| `src/osrsbot/scripts/tests/comprehensive_state_bot_test.py` | 1003 | Exit key support |

---

## Log Output Examples

### Successful Config Loading
```
2026-01-12 09:51:45 - osrsbot.models.config - INFO - Using external config next to .exe: C:\...\dist\config.json
```

### Image Path Resolution
```
2026-01-12 09:51:51 - osrsbot.queries.bank_queries - INFO - Resolved bundled template: src/osrsbot/images/bot/items/overload_potion.png -> C:\Users\...\AppData\Local\Temp\_MEI123456\osrsbot\images\bot\items\overload_potion.png
```

### Exit Request
```
2026-01-12 10:05:23 - osrsbot.core.base_bot - INFO - Exit requested by user (pressed 'q')
🛑 Exit requested... finishing current action...
```

---

## Developer Notes

- All path resolution uses the same pattern: check `sys.frozen`, normalize slashes, strip `src/osrsbot/` prefix
- The `_resolve_template_path()` helper in bank_queries.py can be extracted to a utility module if more files need it
- Debug logging always overwrites (mode='w'), so each run gets a fresh log
- Exit key uses pynput library which is already in requirements

---

## Future Improvements

1. **Centralized path resolver**: Create `src/osrsbot/utils/path_resolver.py` with shared logic
2. **Config migration**: Auto-create external config if missing, copying from bundled template
3. **Image bundling verification**: Add startup check to verify all required images exist
4. **Lazy image loading**: Only load images when first used (currently all load at startup)

---

**End of Summary**
