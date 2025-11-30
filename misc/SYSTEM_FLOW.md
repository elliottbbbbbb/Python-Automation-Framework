# OSRS Bot - System Flow Diagram

## High-Level Architecture Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                            USER                                  │
│                     (runs: python -m osrsbot)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      APP LAYER                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  menu.py                                                  │  │
│  │  • Display menu options                                   │  │
│  │  • Get user script selection                             │  │
│  │  • Get parameters (window title, runs, bank location)    │  │
│  └────────────────────────┬─────────────────────────────────┘  │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      APP LAYER                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  runner.py (ScriptRunner - DI Container)                 │  │
│  │                                                            │  │
│  │  __init__(window_title, config_file):                    │  │
│  │    1. config = Config(config_file)         ◄─┐           │  │
│  │    2. interface = GameInterface(config)      │           │  │
│  │    3. mouse = MouseService(config)           │           │  │
│  │    4. screen = ScreenService(interface)      │           │  │
│  │    5. state = GameState(...)                 │           │  │
│  │    6. actions = GameActions(...)             │           │  │
│  │                                               │           │  │
│  │  run_script(script_func, **kwargs):          │           │  │
│  │    script_func(interface, state, actions, config)        │  │
│  └────────────────────────┬─────────────────────────────────┘  │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                            │ Injects dependencies
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SCRIPTS LAYER                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  combat/green_dragons.py                                 │  │
│  │  skills/pickpocketing.py (guns.py)                       │  │
│  │                                                            │  │
│  │  def script(interface, state, actions, config, **kwargs):│  │
│  │      # Main bot logic                                     │  │
│  │      while not state.inventory_full():  ◄────────┐       │  │
│  │          hp = state.get_hp()            ◄────┐   │       │  │
│  │          if hp < 70:                         │   │       │  │
│  │              actions.eat("manta_ray")  ──┐   │   │       │  │
│  │          if not state.in_combat():  ◄────┼───┼───┘       │  │
│  │              actions.attack("dragon") ─┐ │   │           │  │
│  └────────────────────────────────────────┼─┼───┼───────────┘  │
└───────────────────────────────────────────┼─┼───┼───────────────┘
                                            │ │   │
                    ┌───────────────────────┘ │   │
                    │         ┌───────────────┘   │
                    │         │   ┌───────────────┘
                    │         │   │
        ┌───────────▼─────────▼───▼───────────────────────────────┐
        │              DOMAIN LAYER                                │
        │  ┌────────────────────┐    ┌────────────────────────┐  │
        │  │  actions.py        │    │  state.py (future)     │  │
        │  │  (GameActions)     │    │  (GameQueries)         │  │
        │  │                    │    │                        │  │
        │  │ COMMANDS:          │    │ QUERIES:               │  │
        │  │ • eat(food)        │    │ • get_hp()             │  │
        │  │ • attack(npc)      │    │ • in_combat()          │  │
        │  │ • teleport()       │    │ • inventory_full()     │  │
        │  │ • bank_deposit()   │    │ • get_prayer()         │  │
        │  │ • use_item()       │    │ • get_run_energy()     │  │
        │  │ • walk_marker()    │    │                        │  │
        │  └─────┬──────────────┘    └────────┬───────────────┘  │
        └────────┼─────────────────────────────┼───────────────────┘
                 │                             │
                 │ Uses                        │ Uses
                 ▼                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SERVICES LAYER                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ input/       │  │ vision/      │  │ window/      │          │
│  │              │  │              │  │              │          │
│  │ mouse.py     │  │ screen.py    │  │ interface.py │          │
│  │              │  │ ocr.py       │  │              │          │
│  │ MouseService │  │ ScreenService│  │ GameInterface│          │
│  │              │  │ OCRService   │  │              │          │
│  │              │  │ overlay.py   │  │              │          │
│  │ • move_to()  │  │ • capture()  │  │ • find_win() │          │
│  │ • click()    │  │ • find_color()│ │ • get_bounds()│         │
│  │ • bezier()   │  │ • get_pixel()│  │ • rel_to_abs()│         │
│  │ • humanize() │  │ • wait_for() │  │ • activate() │          │
│  │              │  │              │  │              │          │
│  │              │  │ OverlayService (OPTIONAL - Debug Mode)    │
│  │              │  │ • draw_circle()    - Mark click targets   │
│  │              │  │ • draw_rectangle() - Show OCR regions     │
│  │              │  │ • draw_line()      - Show connections     │
│  │              │  │ • draw_path()      - Track mouse movement │
│  │              │  │ • draw_text()      - Label elements       │
│  │              │  │ • track_mouse()    - Record path history  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼──────────────────┘
          │                  │                  │
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MODELS LAYER                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  config.py (Config)                                      │  │
│  │                                                            │  │
│  │  • Load/save config.json                                 │  │
│  │  • Get colors, coordinates, timings                      │  │
│  │  • Platform-specific settings                            │  │
│  │                                                            │  │
│  │  Data:                                                    │  │
│  │    - colors: {npc_name: "#RRGGBB", ...}                  │  │
│  │    - coordinates: {ui, inventory, minimap, world}        │  │
│  │    - timings: {short, medium, long, teleport}            │  │
│  │    - mouse: {speed, variance, delays}                    │  │
│  │    - ocr: {tesseract_path, ttl, window_size}             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   OS / HARDWARE  │
                    │                  │
                    │  • Windows API   │
                    │  • PyAutoGUI     │
                    │  • Tesseract     │
                    │  • Screen/Mouse  │
                    └─────────────────┘
```

---

## Detailed Component Interaction Flow

### Example: "Attack Green Dragon" Action

```
Script Layer:
  green_dragons.py: actions.attack("green_dragon")
                            │
                            ▼
Domain Layer:
  actions.py: def attack(npc_name):
                1. Get NPC color from config
                2. Call screen.find_color()
                3. Call mouse.click_at()
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
Services Layer:
  screen.py:                    mouse.py:
    find_color(hex, tolerance)    click_at(x, y, style)
      │                             │
      ├─ Capture screenshot         ├─ Calculate bezier path
      ├─ Search for color           ├─ Move with humanization
      └─ Return (x, y) or None      └─ Click with variance
              │                             │
              └─────────────┬───────────────┘
                            ▼
                      OS/Hardware:
                      • Screenshot via mss
                      • Mouse via pyautogui
                      • Window via pywinctl
```

---

## State Query Flow

### Example: "Check HP" Query

```
Script Layer:
  green_dragons.py: hp = state.get_hp()
                            │
                            ▼
Services Layer (currently, should be Domain):
  state.py (GameState): def get_hp():
                          1. Get HP region from config
                          2. Call ocr.read_number()
                          3. Return HP value
                            │
                            ▼
Services Layer:
  ocr.py (OCRService): read_number(region, min, max):
                         │
                         ├─ Get screenshot from window
                         ├─ Crop to region
                         ├─ Preprocess image
                         ├─ Call Tesseract OCR
                         ├─ Parse and validate number
                         ├─ Apply smoothing/caching
                         └─ Return number or None
                            │
                            ▼
                      Tesseract OCR Engine
```

---

## Dependency Injection Flow (ScriptRunner)

```
1. User runs: python -m osrsbot
        │
        ▼
2. app/menu.py:
        │
        ├─ Display menu
        ├─ Get user choice (script #2)
        ├─ Get parameters (window="RuneLite - Player", runs=10)
        │
        ▼
3. Create ScriptRunner(window_title="RuneLite - Player")
        │
        ├─ Load Config("config.json")
        │   └─ Read colors, coords, timings from JSON
        │
        ├─ Create GameInterface(config)
        │   ├─ Find window by title
        │   └─ Get window bounds (x, y, w, h)
        │
        ├─ Create MouseService(config.mouse)
        │   └─ Set speed, variance, delays
        │
        ├─ Create ScreenService(window_bounds)
        │   └─ Initialize screenshot capabilities
        │
        ├─ Create GameState(interface, config, screen)
        │   ├─ Initialize OCRService
        │   └─ Set up state tracking
        │
        └─ Create GameActions(mouse, screen, config)
            └─ Ready to execute commands
        │
        ▼
4. runner.run_script(green_dragons_script, runs=10)
        │
        └─ Call: green_dragons_script(
                    interface,  # GameInterface
                    state,      # GameState
                    actions,    # GameActions
                    config,     # Config
                    runs=10     # kwargs
                 )
        │
        ▼
5. Script executes with all dependencies injected
```

---

## Data Flow: Complete Example

### Scenario: Bot eats food when HP is low

```
┌─────────────────────────────────────────────────────────────┐
│ 1. SCRIPT LAYER                                              │
│                                                               │
│   while not state.inventory_full():                          │
│       hp = state.get_hp()              ◄─── QUERY           │
│       if hp < 70:                                            │
│           actions.eat("manta_ray")     ◄─── COMMAND         │
└───────────────────┬─────────────────────────────────────────┘
                    │
        ┌───────────┴──────────┐
        │                      │
        ▼ QUERY                ▼ COMMAND
┌──────────────────┐    ┌──────────────────┐
│ 2a. STATE        │    │ 2b. ACTIONS      │
│ (Domain/Services)│    │ (Domain)         │
│                  │    │                  │
│ get_hp():        │    │ eat(food):       │
│   region = cfg   │    │   hex = cfg      │
│   ├─ ocr.read()  │    │   ├─ screen.find()│
│   └─ return hp   │    │   └─ mouse.click()│
└────┬─────────────┘    └─────┬────────────┘
     │                        │
     ▼                        ▼
┌─────────────────────────────────────┐
│ 3. SERVICES                         │
│                                     │
│ OCRService:          ScreenService: │
│  read_number()        find_color()  │
│    ├─ screenshot        ├─ capture  │
│    ├─ crop region       ├─ search   │
│    ├─ tesseract         └─ return(x,y)│
│    └─ return 65                     │
│                      MouseService:  │
│                       click_at(x,y) │
│                        ├─ move()    │
│                        └─ click()   │
└─────┬───────────────────┬───────────┘
      │                   │
      ▼                   ▼
┌─────────────────────────────────────┐
│ 4. OS/HARDWARE                      │
│                                     │
│  Tesseract → reads "65" from screen │
│  mss → captures screenshot          │
│  pyautogui → moves mouse & clicks   │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│ 5. RESULT                           │
│                                     │
│  HP = 65 (< 70)                     │
│  → Manta ray found at (x, y)       │
│  → Mouse clicks manta ray          │
│  → HP increases                     │
└─────────────────────────────────────┘
```

---

## Layer Dependencies (Dependency Rule)

```
┌─────────────────────────────────────────────┐
│ Layer 1: SCRIPTS                            │  ← Highest level (most business logic)
│   Depends on: Domain, Models                │
│   Depended by: Nothing                      │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Layer 2: DOMAIN                             │
│   Depends on: Services, Models              │
│   Depended by: Scripts                      │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Layer 3: SERVICES                           │
│   Depends on: Models, OS                    │
│   Depended by: Domain, Scripts              │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Layer 4: MODELS                             │
│   Depends on: Nothing (pure data)           │
│   Depended by: Everyone                     │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Layer 5: OS/HARDWARE                        │  ← Lowest level (infrastructure)
│   Depends on: Nothing                       │
│   Depended by: Services                     │
└─────────────────────────────────────────────┘

RULE: Dependencies only flow DOWNWARD (high-level → low-level)
```

---

## Control Flow vs Data Flow

### Control Flow (who calls who)

```
User
  → app/menu.py
      → app/runner.py (creates dependencies)
          → scripts/combat/green_dragons.py
              → domain/actions.py (commands)
              → domain/state.py (queries)
                  → services/* (infrastructure)
                      → OS/Hardware
```

### Data Flow (information movement)

```
config.json
  → models/config.py (loads)
      → Passed to all layers

Game Screen (OSRS)
  → services/vision/screen.py (captures)
      → domain/state.py (interprets)
          → scripts/*.py (uses for decisions)

User Decisions (in script)
  → domain/actions.py (executes)
      → services/input/mouse.py (performs)
          → Game Client (receives input)
```

---

## Comparison: Current vs Proposed

### Current Structure (MVC-ish)

```
models/config.py  ──┐
models/state.py   ──┤ Models (confusing - state isn't a model)
                    │
controllers/      ──┤ Controllers (confusing - not handling requests)
  runner.py       ──┤
  actions.py      ──┘

views/            ──┐ Views (confusing - CLI isn't really a view)
  menu.py         ──┤
  calibration.py  ──┘

services/         ──── Services (✓ Good!)
scripts/          ──── Scripts (✓ Good!)
```

### Proposed Structure (Service-Oriented)

```
models/           ──── Data models (✓ Clear purpose)
  config.py

domain/           ──── Game-specific logic (✓ Clear purpose)
  actions.py
  state.py

app/              ──── Application layer (✓ Clear purpose)
  runner.py
  menu.py
  calibration.py

services/         ──── Infrastructure (✓ Same as before)
scripts/          ──── Bot behaviors (✓ Same as before)
```

---

## Key Takeaways

1. **Layered Architecture**: Each layer has clear responsibility
2. **Dependency Rule**: High-level → Low-level only
3. **Separation of Concerns**: Commands vs Queries, Domain vs Infrastructure
4. **Dependency Injection**: Runner assembles everything
5. **Single Responsibility**: Each component does one thing well

This structure scales from 1 script to 100+ scripts without refactoring.

---

## Geometry/Overlay System Flow (Debug Mode)

### Purpose
Visual debugging to see what the bot "sees" - click targets, OCR regions, mouse paths, etc.

### Architecture Integration

```
┌─────────────────────────────────────────────────────────────────┐
│ APP LAYER - runner.py (ScriptRunner)                            │
│                                                                   │
│  __init__(window_title, debug_overlay=True):                    │
│    1. config = Config()                                          │
│    2. interface = GameInterface(config)                          │
│    3. bounds = interface.get_bounds()                            │
│    4. overlay = OverlayService(bounds, enabled=True)  ← NEW      │
│    5. mouse = MouseService(config, overlay)           ← Injected │
│    6. screen = ScreenService(bounds, overlay)         ← Injected │
│    7. state = GameState(..., overlay)                 ← Injected │
│    8. actions = GameActions(..., overlay)             ← Injected │
└───────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCRIPT LAYER - green_dragons.py                                 │
│                                                                   │
│  # Script doesn't need to know about overlay                     │
│  while not state.inventory_full():                               │
│      hp = state.get_hp()              ◄─────┐                   │
│      actions.attack("green_dragon")   ◄─────┼─────┐             │
└─────────────────────────────────────────────┼─────┼─────────────┘
                                              │     │
                    ┌─────────────────────────┘     │
                    │                               │
                    ▼                               ▼
┌────────────────────────────────┐  ┌────────────────────────────┐
│ DOMAIN/SERVICE - state.py      │  │ DOMAIN - actions.py        │
│                                 │  │                            │
│ get_hp():                       │  │ attack(npc):               │
│   region = config.get("ocr")    │  │   match = screen.find()    │
│   hp = ocr.read_number(region)  │  │                            │
│                                 │  │   if overlay.enabled:      │
│   if overlay.enabled:           │  │     overlay.draw_circle(   │
│     overlay.draw_rectangle(     │  │       match.x, match.y,    │
│       region.x, region.y,       │  │       color=GREEN)         │
│       region.w, region.h,       │  │     overlay.draw_text(     │
│       color=BLUE)               │  │       match.x, match.y,    │
│     overlay.draw_text(          │  │       npc_name)            │
│       region.x, region.y,       │  │                            │
│       f"HP: {hp}")              │  │   mouse.click_at(match.x,  │
│                                 │  │                   match.y)  │
│   return hp                     │  │                            │
└─────────────────┬───────────────┘  └──────────────┬─────────────┘
                  │                                 │
                  │ Uses                            │ Uses
                  ▼                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ SERVICES LAYER                                                   │
│                                                                   │
│  ┌──────────────────────┐  ┌────────────────────────────────┐  │
│  │ MouseService         │  │ OverlayService                 │  │
│  │                      │  │                                │  │
│  │ click_at(x, y):      │  │ draw_circle(x, y, color):      │  │
│  │   move_to(x, y)      │  │   shapes.append({              │  │
│  │                      │  │     'type': 'circle',          │  │
│  │   if overlay.enabled:│  │     'x': x, 'y': y,            │  │
│  │     # Track path     │  │     'color': color,            │  │
│  │     overlay.track_   │  │     'expires': time + 2.0      │  │
│  │       mouse(x, y)    │  │   })                           │  │
│  │     # Draw path      │  │   _render()                    │  │
│  │     overlay.draw_    │  │                                │  │
│  │       path(points)   │  │ draw_rectangle(x,y,w,h,color): │  │
│  │     # Draw click     │  │   shapes.append({...})         │  │
│  │     overlay.draw_    │  │   _render()                    │  │
│  │       circle(x, y,   │  │                                │  │
│  │         color=RED)   │  │ draw_text(x, y, text):         │  │
│  │                      │  │   shapes.append({...})         │  │
│  │   pyautogui.click()  │  │   _render()                    │  │
│  └──────────────────────┘  │                                │  │
│                            │ _render():                     │  │
│                            │   # Remove expired shapes      │  │
│                            │   # Draw to transparent window │  │
│                            └────────────┬───────────────────┘  │
└─────────────────────────────────────────┼───────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ OS/HARDWARE                                                      │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Transparent Overlay Window (on top of OSRS client)        │  │
│  │                                                             │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │ OSRS Game Client                                     │ │  │
│  │  │                                                        │ │  │
│  │  │   🐉 Green Dragon          ⬜ ← Blue OCR region      │ │  │
│  │  │   ⭕ ← Green circle             "HP: 85" ← Text      │ │  │
│  │  │   "green_dragon" ← Text                              │ │  │
│  │  │                                                        │ │  │
│  │  │   Player                                              │ │  │
│  │  │   ╭────~~~~~────╮ ← Yellow path (mouse movement)    │ │  │
│  │  │   ⭕ ← Red circle (click indicator)                  │ │  │
│  │  │                                                        │ │  │
│  │  │   Inventory:                                          │ │  │
│  │  │   [🐟] [🐟] [⭕] ← Red circle on clicked food       │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  Implementation: OpenCV/Tkinter/PyQt transparent window          │
└─────────────────────────────────────────────────────────────────┘
```

### Detailed Overlay Flow: "Attack Green Dragon"

```
1. Script calls: actions.attack("green_dragon")
        │
        ▼
2. GameActions.attack():
   ├─ Get color from config: "#00FFFF"
   ├─ Call screen.find_color("#00FFFF")
   ├─ Receives: ColorMatch(x=300, y=200)
   │
   ├─ if overlay.enabled:
   │   ├─ overlay.draw_circle(300, 200, radius=10, color=GREEN)
   │   │   └─ Draws: Green circle at NPC location
   │   │
   │   └─ overlay.draw_text(300, 185, "green_dragon", color=WHITE)
   │       └─ Draws: Label above NPC
   │
   └─ Call mouse.click_at(300, 200)
        │
        ▼
3. MouseService.click_at(300, 200):
   ├─ Call move_to(300, 200)
   │   ├─ Generate bezier curve points: [(x1,y1), (x2,y2), ...]
   │   │
   │   ├─ if overlay.enabled:
   │   │   ├─ overlay.track_mouse_position(x, y) for each point
   │   │   │   └─ Stores: [(150,400), (175,380), ..., (300,200)]
   │   │   │
   │   │   └─ overlay.draw_path(points, color=YELLOW)
   │   │       └─ Draws: Yellow curved line showing mouse path
   │   │
   │   └─ Execute movement: pyautogui.moveTo() for each point
   │
   ├─ if overlay.enabled:
   │   └─ overlay.draw_circle(300, 200, radius=8, color=RED, filled=True)
   │       └─ Draws: Red filled circle at click location
   │
   └─ Execute click: pyautogui.click(300, 200)
        │
        ▼
4. OverlayService._render():
   ├─ Remove expired shapes (older than 2 seconds)
   ├─ Draw all active shapes to transparent window:
   │   ├─ Blue rectangle (OCR region) - from state.get_hp()
   │   ├─ Green circle (NPC target) - from actions.attack()
   │   ├─ White text "green_dragon"
   │   ├─ Yellow path (mouse movement)
   │   └─ Red circle (click indicator)
   │
   └─ Display transparent window over OSRS client
        │
        ▼
5. User sees visual feedback:
   ✓ HP region highlighted in blue
   ✓ NPC marked with green circle
   ✓ Mouse path shown as yellow curve
   ✓ Click location marked with red dot
   ✓ Labels showing what bot is targeting
```

### Configuration Flow

```
1. User starts bot with debug flag:
   python -m osrsbot --debug-overlay

2. app/menu.py:
   runner = ScriptRunner(window_title, debug_overlay=True)

3. ScriptRunner.__init__():
   if debug_overlay:
       self.overlay = OverlayService(bounds, enabled=True)
   else:
       self.overlay = None  # No performance impact

4. Services receive overlay:
   ├─ MouseService(config, overlay=self.overlay)
   ├─ ScreenService(bounds, overlay=self.overlay)
   └─ GameState(..., overlay=self.overlay)

5. Domain receives overlay:
   └─ GameActions(..., overlay=self.overlay)

6. Throughout execution:
   if overlay and overlay.enabled:
       overlay.draw_*(...)  # Draw debug visuals
```

### Data Structures

```python
# Overlay maintains list of shapes
overlay.shapes = [
    {
        'type': 'circle',
        'x': 300,
        'y': 200,
        'radius': 10,
        'color': (0, 255, 0),    # Green
        'thickness': 2,
        'expires': 1638360125.5  # Unix timestamp
    },
    {
        'type': 'rectangle',
        'x': 527,
        'y': 79,
        'width': 35,
        'height': 20,
        'color': (0, 0, 255),    # Blue
        'thickness': 2,
        'expires': 1638360125.5
    },
    {
        'type': 'text',
        'x': 300,
        'y': 185,
        'text': 'green_dragon',
        'color': (255, 255, 255),  # White
        'font_size': 12,
        'expires': 1638360125.5
    },
    # ... more shapes
]

# Mouse path tracking
overlay.mouse_path = [
    Point(150, 400),
    Point(175, 380),
    Point(200, 350),
    # ... up to 50 points
    Point(300, 200)
]
```

### Performance Considerations

**Minimal Impact When Disabled:**
```python
# Every overlay call is guarded
if overlay and overlay.enabled:
    overlay.draw_circle(...)  # Only runs in debug mode

# In production: overlay=None, no overhead
# In debug: overlay draws, helps development
```

**When Enabled:**
- Shapes auto-expire (2 second default)
- Max 100 shapes rendered at once
- Transparent window uses GPU acceleration
- ~5-10ms render time per frame

### Use Cases

**1. Script Development**
```
See exactly what bot is clicking
↓
Verify colors are detected correctly
↓
Ensure coordinates are accurate
↓
Watch mouse movement patterns
```

**2. Debugging Issues**
```
Bot clicking wrong spot?
  → See green circle on actual target
  → Compare with expected location

OCR not reading HP?
  → See blue rectangle on OCR region
  → Check if region is positioned correctly

Mouse movement looks bot-like?
  → See yellow path visualization
  → Adjust bezier curve parameters
```

**3. Visual Validation**
```
Before running long sessions:
  → Run with overlay for 1-2 minutes
  → Verify all actions are correct
  → Disable overlay for production run
```

### Integration Summary

**Layer:** Services (vision/overlay.py)
**Purpose:** Visual debugging infrastructure
**Used By:** Domain (GameActions), Services (MouseService, GameState)
**Optional:** Yes - zero impact when disabled
**Benefit:** Instant visual feedback during development
