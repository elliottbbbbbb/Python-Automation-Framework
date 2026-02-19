# FletchingBot Code Review

## How the Base Class Works

`BankstanderBot` (in `core/base_bankstander.py`) is a reusable template for all bankstanding scripts. It provides 5 state handlers out of the box:

- `_handle_idle` - safety checks
- `_handle_banking` - opens bank, searches for items, withdraws them
- `_handle_deposit` - reopens bank if needed, deposits all items, tracks cycles
- `_handle_recovery` - resets bank state on error
- `_handle_process` - calls `process_items()` which the child class implements

The only method a child class **needs** to implement is `process_items()`. Everything else is inherited.

### GrimyFlaxBot - Reference Implementation

```
bankstanding_flax.py - 122 lines total

__init__:       13 lines  (passes config to super())
process_items:  70 lines  (clicks 28 inventory slots with anti-ban patterns)
Methods overridden: 1 (process_items only)
Base class methods used: ALL - banking, deposit, recovery all inherited
```

This is how the base class is meant to be used. The flax bot defines what's unique (click patterns for cleaning herbs) and inherits everything else.

## Why FletchingBot Should Just Use the Base Class

The fletching workflow is: open bank → deposit finished bows → withdraw bowstrings → withdraw unstrung bows → close bank → combine items → wait → loop.

The base class workflow is: open bank → search → withdraw → close bank → process items → deposit → loop.

These are the same flow. The only difference is withdrawing two items instead of one. That can be handled by calling `bank_search_and_withdraw()` twice, or a small override to `_handle_banking()` that calls the base version and then withdraws a second item. It does **not** require rewriting all 5 state handlers from scratch.

`process_items()` is the only method that genuinely needs a full custom implementation — the use-item-on-item crafting, Make All wait loop, and level-up detection are unique to fletching. Everything else (opening the bank, depositing, recovery, cycle tracking) is identical to what the base class already does.

## FletchingBot - Current Issues

```
bankstanding_fletching.py - 851 lines total

__init__:          153 lines
_handle_banking:   124 lines  (completely rewritten)
_handle_deposit:    68 lines  (completely rewritten)
process_items:     310 lines
+ 5 new methods
Methods overridden: 4 out of 5
Base class methods used: NONE - all handlers are replaced
```

### Issue 1: Base Class Banking is Not Used

The base class `_handle_banking` already handles:
- Opening bank (via template-matched banker click)
- Searching for items by name
- Withdrawing items
- Retrying if dialogue interferes
- Error recovery

FletchingBot overrides this entirely at line 341 and reimplements banking from scratch using color detection and right-click menu offsets. The base class methods `click_banker()`, `bank_search_and_withdraw()`, and `is_bank_open()` (all available via `self.actions`) are never called.

If the GE banker needs color-based interaction instead of template matching, the right approach is to either:
1. Add a parameter to the base class for the banking method (color vs template)
2. Override just the bank-opening step, not the entire handler

### Issue 2: Base Class Deposit is Not Used

Same problem. The base class `_handle_deposit` handles reopening the bank, depositing, cycle counting, and idle anti-ban. FletchingBot replaces all of it at line 466 with its own version that uses template-matched deposit buttons.

### Issue 3: Duplicated Re-Initiation Logic (3 copies)

The "click bowstring, click material, wait, press space" sequence appears three times:

1. **Lines 700-727** - after level-up detection
2. **Lines 762-783** - after level-up re-check
3. **Lines 794-834** - after generic interruption

These are nearly identical (~25 lines each). They should be one method:

```python
def _reinitiate_craft(self) -> bool:
    """Re-click bowstring on material and press Space for Make All."""
    tool_match = self.state.find_multi_template(self._tool_template, threshold=0.7)
    if not tool_match:
        logger.warning("PROCESS: Can't find bowstring for re-initiation")
        return False

    cx, cy, conf, _ = tool_match
    ax, ay = self.actions.coord_resolver.to_absolute(cx, cy)
    self.actions.mouse.click_at(ax, ay, move_style="curved")
    self.actions.wait("short")

    mat_match = self.state.find_multi_template(self._material_template, threshold=0.7)
    if not mat_match:
        logger.warning("PROCESS: Can't find material for re-initiation")
        return False

    cx, cy, conf, _ = mat_match
    ax, ay = self.actions.coord_resolver.to_absolute(cx, cy)
    self.actions.mouse.click_at(ax, ay, move_style="curved")
    time.sleep(2.0)
    self.keyboard.press("space", mode="humanized")
    return True
```

Then all three call sites become `self._reinitiate_craft()`.

### Issue 4: Duplicated Level-Up Handling (2 copies)

The level-up block (WOM check, increment level, upgrade tier, press space twice) appears at:
- Lines 673-728
- Lines 738-783

Same fix - extract to `_handle_levelup()`.

### Issue 5: Template Glob Pattern Repeated 7 Times

The `__init__` has this 4-line pattern copied 7 times with different slugs:

```python
templates = sorted(images_dir.glob(f"items/{slug}*.png"))
self._foo_template = (
    [str(p) for p in templates] if templates
    else [str(images_dir / "items" / f"{slug}.png")]
)
```

Should be one helper:

```python
def _load_templates(self, images_dir: Path, subdir: str, slug: str) -> list[str]:
    paths = sorted(images_dir.glob(f"{subdir}/{slug}*.png"))
    return [str(p) for p in paths] if paths else [str(images_dir / subdir / f"{slug}.png")]
```

### Issue 6: WOM HTTP POST Duplicated from wom_service.py

`wom_service.py` already exists and handles WOM API calls. But FletchingBot does an inline `import requests` and raw POST at lines 80-89 and again at lines 252-259, duplicating what the service already provides.

## Summary

| What | FletchingBot (current) | What it should be |
|---|---|---|
| Total lines | 851 | ~250-300 |
| `__init__` | 153 lines, 7 glob blocks, inline HTTP | ~40 lines with helper method |
| Banking | Full rewrite (124 lines) | Inherit base or override one step |
| Deposit | Full rewrite (68 lines) | Inherit base class |
| Re-initiation | 3 copies (~75 lines) | 1 method, 3 call sites |
| Level-up handling | 2 copies (~90 lines) | 1 method, 2 call sites |
| WOM calls | Inline duplicated HTTP | Use `wom_service.py` |

The game logic is correct - the bot strings bows, detects level-ups, upgrades tiers, and handles interruptions. The implementation just needs to be consolidated and should use the base class methods instead of replacing them.
