# OSRS Bot Pipeline - High-Level Overview

**Date:** 2026-01-12
**Example:** Nightmare Zone (NMZ) AFK Bot

---

## Table of Contents
1. [Bot Startup Pipeline](#bot-startup-pipeline)
2. [NMZ Bot Execution Flow](#nmz-bot-execution-flow)
3. [Click Template Pipeline](#click-template-pipeline)
4. [Template Matching Deep Dive](#template-matching-deep-dive)
5. [OCR Pipeline (HP Detection)](#ocr-pipeline-hp-detection)
6. [Mouse Movement Pipeline](#mouse-movement-pipeline)
7. [Complete Example: "Drink Overload Potion"](#complete-example-drink-overload-potion)

---

## Bot Startup Pipeline

### Level 0: User Runs Bot
```
User launches .exe → menu.py:main()
├─ Initialize logging (console + file)
├─ Validate license
├─ Show menu
└─ User selects "6. NMZ AFK Bot"
```

### Level 1: Script Runner Initialization
```python
# File: src/osrsbot/app/menu.py:305
ScriptRunner(window_title="RuneLite - mweow rawr")
│
├─ Load Config (config.json)
│  └─ src/osrsbot/models/config.py:Config.__init__()
│
├─ Initialize GameInterface
│  └─ src/osrsbot/core/game_interface.py:GameInterface.__init__()
│     ├─ Find game window by title
│     ├─ Get window bounds (position, size)
│     └─ Store window handle
│
├─ Initialize Services
│  ├─ Win32MouseService (mouse control)
│  │  └─ src/osrsbot/services/win32_mouse_service.py
│  │
│  ├─ ScreenService (screenshot capture)
│  │  └─ src/osrsbot/services/screen_service.py
│  │     └─ Takes screenshots of game window
│  │
│  ├─ TemplateMatchService (UI template detection)
│  │  └─ src/osrsbot/services/template_match_service.py
│  │     └─ Loads ALL UI templates from config.json at startup
│  │        ├─ inventory_empty.PNG
│  │        ├─ prayer_tab.png
│  │        └─ 20+ more UI templates (ALL loaded into memory)
│  │
│  ├─ TemplateOCRService (text reading)
│  │  └─ src/osrsbot/services/template_ocr_service.py
│  │     └─ Loads digit templates for OCR
│  │
│  ├─ GameState (game state tracking)
│  │  └─ src/osrsbot/queries/game_queries.py
│  │
│  ├─ AntiBanService (human-like behavior)
│  │  └─ src/osrsbot/services/anti_ban_service.py
│  │
│  └─ GameActions (high-level game actions)
│     └─ src/osrsbot/commands/game_actions.py
│        └─ Aggregates all command layers (bank, inventory, combat)
│
└─ Run Bot Script
   └─ runner.run_script(NMZAfkBot, runs=999)
```

---

## NMZ Bot Execution Flow

### Level 2: Bot Initialization
```python
# File: src/osrsbot/scripts/afk/nmz_afk.py:62-93
NMZAfkBot.__init__()
│
├─ Extends StateMachineBot (state machine framework)
├─ Define hardcoded image paths:
│  ├─ OVERLOAD_TEMPLATE = "src/osrsbot/images/bot/items/overload_potion.png"
│  ├─ ABSORPTION_TEMPLATE = "src/osrsbot/images/bot/items/absorption_potion.png"
│  ├─ ROCK_CAKE_TEMPLATE = "src/osrsbot/images/bot/items/dwarven_rock_cake.png"
│  └─ LOCATOR_ORB_TEMPLATE = "src/osrsbot/images/bot/items/locator_orb.png"
│
└─ Initialize state machine with 7 states:
   1. IDLE
   2. DRINK_OVERLOAD
   3. WAIT_FOR_DAMAGE
   4. LOWER_HP
   5. DRINK_ABSORPTION
   6. COMBAT_LOOP (main loop - runs indefinitely)
   7. RECOVERY
```

### Level 3: State Machine Execution
```python
# File: src/osrsbot/core/state_machine_bot.py:run_cycle()
State Machine Loop:
│
├─ Start at IDLE state
├─ Execute state handler → _handle_idle()
├─ State returns SUCCESS
├─ Look up transition: IDLE → DRINK_OVERLOAD
├─ Execute next state → _handle_drink_overload()
└─ Repeat until bot completes or user exits (press 'q')

State Transitions:
IDLE → DRINK_OVERLOAD → WAIT_FOR_DAMAGE → LOWER_HP → DRINK_ABSORPTION → COMBAT_LOOP
                                                                              ↓ (loops forever)
                                                                              ↑
```

---

## NMZ State Handlers (Example: DRINK_OVERLOAD)

### Level 4: State Handler - Drink Overload
```python
# File: src/osrsbot/scripts/afk/nmz_afk.py:366-388
def _handle_drink_overload(context):
    """
    STATE: DRINK_OVERLOAD
    Goal: Click overload potion in inventory
    """

    # Step 1: Record action for anti-ban
    self._record_action("drink_overload")

    # Step 2: Click the overload template
    if not self._click_item_or_fail(
        template="src/osrsbot/images/bot/items/overload_potion.png",
        item_name="overload potion"
    ):
        return StateResult.FAILURE

    # Step 3: Update timers
    self._last_overload_time = time.time()

    # Step 4: Wait (human delay)
    self.actions.wait("medium")

    return StateResult.SUCCESS
```

**What happens here:**
1. Records action for anti-ban pattern tracking
2. Calls `_click_item_or_fail()` which internally calls `self.actions.click_template()`
3. This triggers the **Click Template Pipeline** (see next section)

---

## Click Template Pipeline

### Level 5: Click Template Execution
```python
# Entry Point: src/osrsbot/scripts/afk/nmz_afk.py:139
self.actions.click_template(template_path, item_name)
│
└─> # File: src/osrsbot/commands/game_actions.py:490-494
    GameActions.click_template(template_path, item_name, threshold=0.7)
    │
    └─> # Delegates to BankActions (reused for all template clicks)
        # File: src/osrsbot/commands/bank_actions.py:108-147
        BankActions.click_template(template_path, item_name, threshold)
        │
        ├─ STEP 1: Find the template on screen
        │  └─> BankQueries.find_template(template_path, threshold)
        │     │
        │     └─> # File: src/osrsbot/queries/bank_queries.py:85-138
        │         BankQueries.find_template()
        │         │
        │         ├─ Resolve template path (for .exe)
        │         │  └─> _resolve_template_path(template_path)
        │         │      └─ Convert "src/osrsbot/images/..." to bundled path
        │         │
        │         ├─ Load template image with OpenCV
        │         │  └─> cv.imread(resolved_path, cv.IMREAD_COLOR)
        │         │      └─ Returns: NumPy array (height, width, 3) BGR format
        │         │
        │         ├─ Capture current game screenshot
        │         │  └─> ScreenService.capture()
        │         │      │
        │         │      └─> # File: src/osrsbot/services/screen_service.py:66-86
        │         │          ├─ Get game window bounds from GameInterface
        │         │          ├─ Use PIL ImageGrab to screenshot the region
        │         │          └─ Return: PIL.Image (RGB)
        │         │
        │         ├─ Convert screenshot to OpenCV format
        │         │  └─ PIL RGB → NumPy array → cv.cvtColor(RGB2BGR)
        │         │
        │         ├─ Perform template matching
        │         │  └─> cv.matchTemplate(screenshot, template, cv.TM_CCOEFF_NORMED)
        │         │      └─ Returns: Confidence matrix (0.0-1.0 for each pixel)
        │         │
        │         ├─ Find best match location
        │         │  └─> cv.minMaxLoc(result)
        │         │      └─ Returns: (min_val, max_val, min_loc, max_loc)
        │         │
        │         ├─ Check if confidence >= threshold (0.7)
        │         │  └─ If max_val >= 0.7: MATCH FOUND
        │         │
        │         └─ Calculate center coordinates
        │            └─ center_x = match_x + template_width // 2
        │            └─ center_y = match_y + template_height // 2
        │            └─ Return: (center_x, center_y, confidence)
        │
        ├─ STEP 2: Check if template found
        │  └─ If None: Log warning "overload potion not found"
        │     └─ Return False
        │
        ├─ STEP 3: Convert to absolute screen coordinates
        │  └─> CoordinateResolver.to_absolute(center_x, center_y)
        │      └─ Add game window offset: abs_x = window_x + center_x
        │
        └─ STEP 4: Click the position
           └─> MouseService.click_at(abs_x, abs_y, move_style="curved", speed=1.0)
               │
               └─> [See Mouse Movement Pipeline below]
```

---

## Template Matching Deep Dive

### How OpenCV Template Matching Works

```
┌─────────────────────────────────────────────────────────────┐
│                    GAME SCREENSHOT                          │
│  (765 x 503 pixels)                                         │
│                                                             │
│  ┌──────────────────────────────────────┐                  │
│  │        Game Window                   │                  │
│  │                                      │                  │
│  │  [...]                               │                  │
│  │  [Inventory with items]              │                  │
│  │  [🧪 Overload]  [Empty]  [Empty]     │ ← Template      │
│  │  [Empty]       [Empty]  [Empty]     │   matching       │
│  │                                      │   searches here  │
│  └──────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
                        ↓
              cv.matchTemplate()
                        ↓
┌─────────────────────────────────────────────────────────────┐
│              CONFIDENCE HEAT MAP                            │
│  Every pixel gets a confidence score (0.0-1.0)              │
│                                                             │
│  [0.12] [0.15] [0.18] ... [0.91] [0.88] ... [0.10]         │
│  [0.11] [0.14] [0.17] ... [0.93] [0.89] ... [0.09]         │
│  [0.13] [0.16] [0.19] ... [0.95] ← MAX! ... [0.11]         │
│                                ↑                            │
│                    Best match at (x:245, y:102)             │
│                    Confidence: 0.95 (95%)                   │
└─────────────────────────────────────────────────────────────┘
                        ↓
              Threshold Check: 0.95 >= 0.7? YES!
                        ↓
              Calculate Center: (245 + width/2, 102 + height/2)
                        ↓
              Return: (center_x=260, center_y=117, conf=0.95)
```

**Template Matching Algorithm:**
1. Slide template image over screenshot pixel-by-pixel
2. At each position, calculate similarity score (normalized cross-correlation)
3. Create confidence map of all positions
4. Find position with highest confidence
5. If confidence >= threshold: Match found!

---

## OCR Pipeline (HP Detection)

### Level 6: Reading HP Value
```python
# Entry Point: src/osrsbot/scripts/afk/nmz_afk.py:286-296
self._get_hp()
│
└─> self.state.get_hp(force=True)
    │
    └─> # File: src/osrsbot/queries/stat_queries.py:27-52
        StatQueries.get_hp(force=True)
        │
        ├─ STEP 1: Get HP region coordinates
        │  └─ HP_REGION = (508, 58, 539, 70)  # (x1, y1, x2, y2)
        │
        ├─ STEP 2: Capture screenshot of HP region
        │  └─> ScreenService.capture_region(HP_REGION)
        │      └─ Same as capture() but crops to specific region
        │
        ├─ STEP 3: Perform OCR using template matching
        │  └─> TemplateOCRService.read_digits(hp_screenshot, "Plain11")
        │      │
        │      └─> # File: src/osrsbot/services/template_ocr_service.py:103-180
        │          ├─ Convert image to grayscale
        │          ├─ Threshold to binary (black/white only)
        │          ├─ Split into individual digit regions
        │          ├─ For each digit:
        │          │  └─ Template match against digit templates (0-9)
        │          │     └─ digit_templates["Plain11"]["0"] through ["9"]
        │          │     └─ Find best matching digit
        │          └─ Concatenate recognized digits → "99"
        │
        └─ STEP 4: Parse as integer
           └─ int("99") → 99
           └─ Return: 99
```

**OCR Template Matching:**
```
HP Screenshot: [9][9]
                ↓
         Grayscale + Threshold
                ↓
    ┌─────────┐  ┌─────────┐
    │ █   █   │  │ █   █   │  ← Individual digits
    │ █   █   │  │ █   █   │
    │ █████   │  │ █████   │
    │     █   │  │     █   │
    └─────────┘  └─────────┘
         ↓            ↓
    Match vs       Match vs
    templates      templates
    0-9            0-9
         ↓            ↓
    Best: "9"      Best: "9"
    (0.94)         (0.92)
         ↓            ↓
         "99" (HP value)
```

---

## Mouse Movement Pipeline

### Level 7: Clicking the Target
```python
# Entry Point: src/osrsbot/commands/bank_actions.py:138
MouseService.click_at(abs_x, abs_y, move_style="curved", speed_multiplier=1.0)
│
└─> # File: src/osrsbot/services/win32_mouse_service.py:264-331
    Win32MouseService.click_at(x, y, move_style="curved", speed=1.0)
    │
    ├─ STEP 1: Get current mouse position
    │  └─> win32api.GetCursorPos() → (current_x, current_y)
    │
    ├─ STEP 2: Calculate movement path (Bezier curve)
    │  └─> BezierPathGenerator.generate_path(start, end, speed_multiplier)
    │      │
    │      └─> # File: src/osrsbot/utils/coordinate_helpers.py:143-221
    │          ├─ Create control points for Bezier curve
    │          │  └─ Add randomness to control points (human-like)
    │          │  └─ Random offset: ±20-50 pixels
    │          │
    │          ├─ Calculate number of steps (based on distance)
    │          │  └─ distance = sqrt((x2-x1)² + (y2-y1)²)
    │          │  └─ num_steps = distance / 2  (approx)
    │          │
    │          ├─ Generate Bezier curve points
    │          │  └─ For t from 0.0 to 1.0:
    │          │     └─ point = (1-t)³*P0 + 3(1-t)²t*P1 + 3(1-t)t²*P2 + t³*P3
    │          │
    │          └─ Return: List of (x, y) coordinates
    │             └─ [(100,200), (105,203), (110,207), ..., (300,350)]
    │
    ├─ STEP 3: Move mouse along path
    │  └─> For each point in path:
    │      ├─ win32api.SetCursorPos(point_x, point_y)
    │      │  └─ Moves cursor to exact pixel position
    │      │
    │      └─ time.sleep(delay)
    │         └─ delay = 0.001 - 0.005 seconds per point
    │         └─ Creates smooth, human-like movement
    │
    ├─ STEP 4: Add pre-click micro-pause (anti-ban)
    │  └─> time.sleep(random.uniform(0.05, 0.15))
    │
    ├─ STEP 5: Send mouse down event
    │  └─> win32api.mouse_event(MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    │
    ├─ STEP 6: Random click duration
    │  └─> time.sleep(random.uniform(0.05, 0.12))
    │
    ├─ STEP 7: Send mouse up event
    │  └─> win32api.mouse_event(MOUSEEVENTF_LEFTUP, x, y, 0, 0)
    │
    └─ STEP 8: Post-click pause
       └─> time.sleep(random.uniform(0.1, 0.3))
```

**Bezier Curve Visualization:**
```
Start: (100, 200)                     End: (300, 350)
   *                                          *
    \                                        /
     \     Control Point 1                 /
      \    (150, 180)                     /
       *-----------------------*         /
                              Control Point 2
                              (250, 370)

The curve smoothly connects start to end through control points,
creating a natural, human-like mouse path.
```

---

## Complete Example: "Drink Overload Potion"

### Full Pipeline Trace (All Levels)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ USER ACTION: Bot enters DRINK_OVERLOAD state                           │
└─────────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ LEVEL 1: State Handler (nmz_afk.py:366)                                │
│ _handle_drink_overload()                                                │
│   → Calls: self.actions.click_template(                                │
│       "src/osrsbot/images/bot/items/overload_potion.png",              │
│       "overload potion"                                                 │
│     )                                                                   │
└─────────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ LEVEL 2: Game Actions (game_actions.py:490)                            │
│ GameActions.click_template()                                            │
│   → Delegates to: BankActions.click_template()                         │
└─────────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ LEVEL 3: Bank Actions (bank_actions.py:108)                            │
│ BankActions.click_template()                                            │
│   → Step 1: Find item using BankQueries.find_template()                │
└─────────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ LEVEL 4: Bank Queries (bank_queries.py:85)                             │
│ BankQueries.find_template()                                             │
│                                                                         │
│   Step 1: Resolve path (Windows .exe fix)                              │
│   ─────────────────────────────────────                                │
│   Input:  "src/osrsbot/images/bot/items/overload_potion.png"           │
│   Output: "C:\...\AppData\Local\Temp\_MEI12345\osrsbot\images\..."     │
│                                                                         │
│   Step 2: Load template image                                          │
│   ─────────────────────────────                                        │
│   cv.imread(resolved_path) → NumPy array [36×36×3 BGR]                 │
│                                                                         │
│   Step 3: Capture game screenshot                                      │
│   ─────────────────────────────────                                    │
│   ScreenService.capture() → PIL Image [765×503 RGB]                    │
│   Convert to OpenCV format → NumPy array [765×503×3 BGR]               │
│                                                                         │
│   Step 4: Template matching                                            │
│   ─────────────────────────────                                        │
│   cv.matchTemplate(screenshot, template, TM_CCOEFF_NORMED)             │
│   Result: Confidence matrix [729×467] (every possible position)        │
│                                                                         │
│   Step 5: Find best match                                              │
│   ─────────────────────────────                                        │
│   cv.minMaxLoc(result) → max_val=0.93, max_loc=(612, 298)              │
│   Threshold check: 0.93 >= 0.7 ✓ MATCH FOUND!                          │
│                                                                         │
│   Step 6: Calculate center                                             │
│   ─────────────────────────────                                        │
│   center_x = 612 + 36/2 = 630 (relative to game window)                │
│   center_y = 298 + 36/2 = 316                                          │
│                                                                         │
│   Return: (630, 316, 0.93)                                             │
└─────────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ LEVEL 5: Bank Actions (continued)                                      │
│                                                                         │
│   Step 2: Convert to absolute screen coordinates                       │
│   ──────────────────────────────────────────────                       │
│   Game window position: (100, 50) ← from GameInterface                 │
│   abs_x = 100 + 630 = 730                                              │
│   abs_y = 50 + 316 = 366                                               │
│                                                                         │
│   Step 3: Click the position                                           │
│   ──────────────────────────                                           │
│   MouseService.click_at(730, 366, "curved", 1.0)                       │
└─────────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ LEVEL 6: Mouse Service (win32_mouse_service.py:264)                    │
│ Win32MouseService.click_at(730, 366)                                    │
│                                                                         │
│   Step 1: Get current cursor position                                  │
│   ───────────────────────────────────                                  │
│   win32api.GetCursorPos() → (450, 250)                                 │
│                                                                         │
│   Step 2: Generate Bezier curve path                                   │
│   ──────────────────────────────────                                   │
│   Start: (450, 250)                                                    │
│   End:   (730, 366)                                                    │
│   Distance: sqrt((280)² + (116)²) = 303 pixels                         │
│   Num steps: 303 / 2 = 151 points                                      │
│                                                                         │
│   Control points (randomized):                                         │
│   P1: (520, 240) ← Start + random offset                               │
│   P2: (680, 380) ← End + random offset                                 │
│                                                                         │
│   Bezier curve: (450,250) → ... → (730,366)                            │
│   Path: [(450,250), (451,250), (453,251), ..., (730,366)]              │
│                                                                         │
│   Step 3: Move mouse along path (animated)                             │
│   ────────────────────────────────────────                             │
│   For each point:                                                      │
│     win32api.SetCursorPos(point)                                       │
│     time.sleep(0.002) ← ~2ms per point                                 │
│   Total time: 151 points × 2ms = ~300ms movement                       │
│                                                                         │
│   Step 4: Pre-click pause (anti-ban)                                   │
│   ──────────────────────────────────                                   │
│   time.sleep(0.087) ← Random: 50-150ms                                 │
│                                                                         │
│   Step 5: Mouse down                                                   │
│   ────────────────────                                                 │
│   win32api.mouse_event(MOUSEEVENTF_LEFTDOWN)                           │
│                                                                         │
│   Step 6: Click duration                                               │
│   ────────────────────────                                             │
│   time.sleep(0.073) ← Random: 50-120ms                                 │
│                                                                         │
│   Step 7: Mouse up                                                     │
│   ──────────────────                                                   │
│   win32api.mouse_event(MOUSEEVENTF_LEFTUP)                             │
│                                                                         │
│   Step 8: Post-click pause                                             │
│   ─────────────────────────                                            │
│   time.sleep(0.214) ← Random: 100-300ms                                │
└─────────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ GAME RECEIVES CLICK                                                    │
│ Player drinks overload potion                                          │
└─────────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ LEVEL 7: State Handler (continued)                                     │
│ _handle_drink_overload()                                                │
│   → Update timer: _last_overload_time = time.time()                    │
│   → Wait: self.actions.wait("medium") ← 0.8-1.2 seconds                │
│   → Return: StateResult.SUCCESS                                        │
└─────────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ LEVEL 8: State Machine                                                 │
│ StateMachineBot.run_cycle()                                             │
│   → State DRINK_OVERLOAD completed successfully                        │
│   → Lookup transition: DRINK_OVERLOAD → WAIT_FOR_DAMAGE                │
│   → Execute next state: _handle_wait_for_damage()                      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Timing Breakdown

**Total Time for "Click Overload Potion":**

| Step | Operation | Time |
|------|-----------|------|
| 1 | Template matching (find potion) | ~50-100ms |
| 2 | Mouse movement (Bezier curve) | ~300ms |
| 3 | Pre-click pause (anti-ban) | ~50-150ms |
| 4 | Click duration (down + up) | ~50-120ms |
| 5 | Post-click pause | ~100-300ms |
| 6 | State wait ("medium") | ~800-1200ms |
| **Total** | **~1350-1970ms (1.4-2.0 seconds)** |

---

## Anti-Ban Integration

Throughout the pipeline, anti-ban features are integrated:

1. **Movement Randomization** (Mouse Service)
   - Bezier curves with random control points
   - Variable speed (0.8x - 1.2x multiplier)
   - Random overshoots and corrections

2. **Timing Randomization** (Actions)
   - All waits have ranges (not fixed values)
   - Pre-click, click, post-click pauses all randomized

3. **Pattern Tracking** (Anti-Ban Service)
   - Records all actions with timestamps
   - Tracks repetitive patterns
   - Suggests micro-breaks

4. **Fatigue Simulation** (Anti-Ban Service)
   - Slower reactions over time
   - Occasional missed actions (4% chance)
   - Zone-out periods (30-90 second pauses)

---

## Architecture Summary

### Layer Hierarchy (Top to Bottom)

```
┌──────────────────────────────────────────┐
│  Layer 1: Bot Scripts (nmz_afk.py)      │ ← User-level: Define bot behavior
│  ─────────────────────────────────────   │
│  State machines, game logic, strategy    │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│  Layer 2: Commands (game_actions.py)    │ ← CQRS Write: Mutations/actions
│  ─────────────────────────────────────   │
│  Click, move, type, interact            │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│  Layer 3: Queries (bank_queries.py)     │ ← CQRS Read: State detection
│  ─────────────────────────────────────   │
│  Template matching, OCR, detection      │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│  Layer 4: Services (mouse, screen, etc) │ ← Low-level: Hardware/OS interface
│  ─────────────────────────────────────   │
│  Screenshot, mouse control, templates    │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│  Layer 5: OS/Game                        │ ← System: Windows API, OSRS client
│  ─────────────────────────────────────   │
│  win32api, PIL, OpenCV                   │
└──────────────────────────────────────────┘
```

### Data Flow

```
Bot State
   ↓
Commands (Write)  ← ← ← ← ← ← Feedback Loop
   ↓                              ↑
Services                          ↑
   ↓                              ↑
Game/OS                           ↑
   ↓                              ↑
Screenshot Capture                ↑
   ↓                              ↑
Queries (Read) → → → → → → → → → ↑
   ↓
State Detection
   ↓
Bot State (next iteration)
```

---

## Key Takeaways

1. **Everything starts with a state machine** - Organized, retryable, recoverable
2. **CQRS pattern** - Clear separation between reading (queries) and writing (commands)
3. **Template matching is the core** - 95% of game interaction uses it
4. **Layered architecture** - Each layer has clear responsibilities
5. **Anti-ban at every level** - Randomization and human-like behavior throughout
6. **Coordinate systems matter** - Game-relative → Screen-absolute conversions
7. **OpenCV does the heavy lifting** - Template matching, image processing, OCR

---

**End of Pipeline Overview**
