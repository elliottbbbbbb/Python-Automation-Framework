# Geometry Overlay System Design

## Purpose

Draw visual overlays on the OSRS client for:
- **Debugging**: See what the bot "sees" (click targets, color matches)
- **Tracking**: Visualize mouse paths, movement history
- **Validation**: Ensure bot is clicking correct locations
- **Development**: Quick visual feedback during script development

---

## Architecture Placement

### Layer: **Services** (Infrastructure)

```
services/
├── input/
│   └── mouse.py
├── vision/
│   ├── screen.py
│   ├── ocr.py
│   └── overlay.py          # ← NEW: OverlayService
└── window/
    └── interface.py
```

**Why Services Layer?**
- It's **infrastructure** (rendering graphics)
- It's **reusable** across all scripts
- It doesn't contain game logic
- Similar to MouseService or ScreenService

---

## System Flow Integration

### Option 1: Independent Overlay Service (Recommended)

```
┌─────────────────────────────────────────────────────────────────┐
│                         SCRIPT LAYER                             │
│                                                                   │
│  green_dragons.py:                                               │
│      hp = state.get_hp()                                         │
│      actions.attack("green_dragon")                              │
│                                                                   │
│  (Script doesn't need to know about overlay)                     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DOMAIN LAYER                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  actions.py (GameActions)                                │  │
│  │                                                            │  │
│  │  def attack(npc_name):                                    │  │
│  │      match = screen.find_color(hex, tolerance)            │  │
│  │      if overlay.enabled:                    ◄─────┐       │  │
│  │          overlay.draw_circle(match.x, match.y)    │       │  │
│  │      mouse.click_at(match.x, match.y)             │       │  │
│  └────────────────────────┬──────────────────────────────────┘  │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                ┌───────────┴──────────┐
                │                      │
                ▼                      ▼
┌──────────────────────┐    ┌──────────────────────┐
│  SERVICES            │    │  SERVICES            │
│  vision/screen.py    │    │  vision/overlay.py   │ ← NEW
│                      │    │                      │
│  find_color()        │    │  OverlayService:     │
│    └─ returns (x,y)  │    │   • draw_circle()    │
│                      │    │   • draw_rectangle() │
│  MouseService:       │    │   • draw_line()      │
│  click_at(x, y)      │    │   • draw_path()      │
│    ├─ move()         │    │   • clear()          │
│    │                 │    │   • enabled flag     │
│    └─ if overlay:    │    │                      │
│        overlay.draw_path()│                      │
└──────────────────────┘    └──────────────────────┘
                            │
                            ▼
                    ┌──────────────────┐
                    │   OS/HARDWARE     │
                    │                   │
                    │  • Transparent    │
                    │    window overlay │
                    │  • OpenCV/PIL     │
                    │  • Win32 API      │
                    └──────────────────┘
```

---

## Detailed Component Design

### OverlayService API

```python
from typing import Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum

class Color(Enum):
    """Predefined overlay colors"""
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    CYAN = (0, 255, 255)
    WHITE = (255, 255, 255)

@dataclass
class Point:
    x: int
    y: int

class OverlayService:
    """
    Draws debug overlays on top of game window.

    Features:
    - Transparent overlay window
    - Draw shapes (circles, rectangles, lines)
    - Track mouse paths
    - Auto-clear after timeout
    - Toggle on/off
    """

    def __init__(self, window_bounds: Tuple[int, int, int, int], enabled: bool = False):
        """
        Args:
            window_bounds: (left, top, width, height) of game window
            enabled: Start with overlay enabled/disabled
        """
        self.bounds = window_bounds
        self.enabled = enabled
        self.shapes = []  # List of shapes to draw
        self.mouse_path = []  # Track mouse movement

        if enabled:
            self._create_overlay_window()

    def enable(self) -> None:
        """Enable overlay rendering"""
        self.enabled = True
        self._create_overlay_window()

    def disable(self) -> None:
        """Disable overlay rendering"""
        self.enabled = False
        self._destroy_overlay_window()

    def draw_circle(
        self,
        x: int,
        y: int,
        radius: int = 5,
        color: Color = Color.RED,
        thickness: int = 2,
        duration: float = 2.0
    ) -> None:
        """
        Draw a circle at position.

        Args:
            x, y: Center position (relative to window)
            radius: Circle radius in pixels
            color: Circle color
            thickness: Line thickness (-1 = filled)
            duration: Auto-remove after N seconds (0 = permanent)
        """
        if not self.enabled:
            return

        self.shapes.append({
            'type': 'circle',
            'x': x,
            'y': y,
            'radius': radius,
            'color': color.value,
            'thickness': thickness,
            'expires': time.time() + duration if duration > 0 else None
        })
        self._render()

    def draw_rectangle(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        color: Color = Color.BLUE,
        thickness: int = 2,
        duration: float = 2.0
    ) -> None:
        """Draw a rectangle"""
        if not self.enabled:
            return

        self.shapes.append({
            'type': 'rectangle',
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'color': color.value,
            'thickness': thickness,
            'expires': time.time() + duration if duration > 0 else None
        })
        self._render()

    def draw_line(
        self,
        x1: int, y1: int,
        x2: int, y2: int,
        color: Color = Color.GREEN,
        thickness: int = 2,
        duration: float = 2.0
    ) -> None:
        """Draw a line between two points"""
        if not self.enabled:
            return

        self.shapes.append({
            'type': 'line',
            'x1': x1, 'y1': y1,
            'x2': x2, 'y2': y2,
            'color': color.value,
            'thickness': thickness,
            'expires': time.time() + duration if duration > 0 else None
        })
        self._render()

    def draw_path(
        self,
        points: List[Point],
        color: Color = Color.CYAN,
        thickness: int = 2,
        duration: float = 5.0
    ) -> None:
        """Draw a path connecting multiple points (for mouse movement)"""
        if not self.enabled or len(points) < 2:
            return

        for i in range(len(points) - 1):
            self.draw_line(
                points[i].x, points[i].y,
                points[i+1].x, points[i+1].y,
                color, thickness, duration
            )

    def draw_text(
        self,
        x: int, y: int,
        text: str,
        color: Color = Color.WHITE,
        font_size: int = 12,
        duration: float = 2.0
    ) -> None:
        """Draw text label"""
        if not self.enabled:
            return

        self.shapes.append({
            'type': 'text',
            'x': x,
            'y': y,
            'text': text,
            'color': color.value,
            'font_size': font_size,
            'expires': time.time() + duration if duration > 0 else None
        })
        self._render()

    def track_mouse_position(self, x: int, y: int) -> None:
        """Add point to mouse path tracking"""
        if not self.enabled:
            return

        self.mouse_path.append(Point(x, y))

        # Keep only last 50 points
        if len(self.mouse_path) > 50:
            self.mouse_path.pop(0)

    def draw_mouse_path(self, duration: float = 3.0) -> None:
        """Draw the tracked mouse path"""
        if self.mouse_path:
            self.draw_path(self.mouse_path, Color.CYAN, 1, duration)

    def clear(self) -> None:
        """Clear all shapes"""
        self.shapes = []
        self.mouse_path = []
        self._render()

    def _render(self) -> None:
        """Internal: Render all shapes to overlay window"""
        # Remove expired shapes
        now = time.time()
        self.shapes = [s for s in self.shapes if s['expires'] is None or s['expires'] > now]

        # Platform-specific rendering
        # Option A: OpenCV + transparent window
        # Option B: PIL + Win32 overlay
        # Option C: Tkinter transparent canvas
        pass

    def _create_overlay_window(self) -> None:
        """Create transparent overlay window on top of game"""
        pass

    def _destroy_overlay_window(self) -> None:
        """Destroy overlay window"""
        pass
```

---

## Integration Points

### 1. In GameActions (Domain)

```python
class GameActions:
    def __init__(self, mouse, screen, config, overlay=None):
        self.mouse = mouse
        self.screen = screen
        self.config = config
        self.overlay = overlay  # Optional overlay service

    def attack(self, npc_name: str) -> bool:
        """Attack NPC with visual debugging"""
        hex_color = self.config.get("colors", npc_name)
        match = self.screen.find_color(hex_color, tolerance=10)

        if not match:
            logger.debug(f"NPC '{npc_name}' not found")
            return False

        # DEBUG: Draw circle where NPC was found
        if self.overlay and self.overlay.enabled:
            self.overlay.draw_circle(match.x, match.y, radius=10,
                                    color=Color.GREEN, duration=2.0)
            self.overlay.draw_text(match.x, match.y - 15, npc_name,
                                  color=Color.WHITE)

        # Click the NPC
        success = self.mouse.click_at(match.x, match.y)
        return success
```

### 2. In MouseService (Service)

```python
class MouseService:
    def __init__(self, config, overlay=None):
        self.config = config
        self.overlay = overlay
        self.movement_points = []

    def move_to(self, x: int, y: int, style: MovementStyle = "curved") -> bool:
        """Move mouse with path tracking"""
        # Track movement points for debugging
        if self.overlay and self.overlay.enabled:
            self.overlay.track_mouse_position(x, y)

        # Perform movement
        if style == "curved":
            points = self._generate_bezier_curve(current_x, current_y, x, y)

            # Draw the planned path
            if self.overlay and self.overlay.enabled:
                path = [Point(p[0], p[1]) for p in points]
                self.overlay.draw_path(path, Color.YELLOW, thickness=1, duration=1.0)

            # Execute movement
            for px, py in points:
                pyautogui.moveTo(px, py)

        return True

    def click_at(self, x: int, y: int, button: str = 'left') -> bool:
        """Click with visual indicator"""
        # Move to position
        self.move_to(x, y)

        # DEBUG: Draw click indicator
        if self.overlay and self.overlay.enabled:
            self.overlay.draw_circle(x, y, radius=8, color=Color.RED,
                                    thickness=-1, duration=0.5)  # Filled circle

        # Perform click
        pyautogui.click(x, y, button=button)
        return True
```

### 3. In ScriptRunner (DI Container)

```python
class ScriptRunner:
    def __init__(self, window_title: str, config_file: str = "config.json",
                 debug_overlay: bool = False):
        # ... existing initialization ...

        # Initialize overlay service (optional)
        self.overlay = None
        if debug_overlay:
            bounds = self.interface.get_bounds()
            self.overlay = OverlayService(bounds, enabled=True)
            logger.info("Debug overlay enabled")

        # Inject overlay into services that need it
        self.mouse = MouseService(mouse_config, overlay=self.overlay)
        self.screen = ScreenService(bounds, overlay=self.overlay)

        # Inject into domain
        self.actions = GameActions(
            self.mouse,
            self.screen,
            self.config,
            overlay=self.overlay
        )
```

### 4. In CLI Menu

```python
def main():
    print("\n1. Run Green Dragons Script")
    print("2. Run with DEBUG OVERLAY")

    choice = input("\nSelect: ").strip()

    if choice == "2":
        window_title = get_window_title("Window title: ")
        runner = ScriptRunner(window_title, debug_overlay=True)  # Enable overlay
        runner.run_script(green_dragons_script, runs=10)
```

---

## Visual Output Examples

### Example 1: Attack Green Dragon

```
┌──────────────────────────────────────────┐
│         OSRS Game Client                 │
│                                          │
│         🐉 Green Dragon                  │
│         ⭕ ← Red circle (click target)   │
│         "green_dragon" ← White text      │
│                                          │
│    ╭─────────╮ Player                   │
│    │  💚 HP  │                           │
│    ╰─────────╯                           │
│                                          │
│  🔵 (Manta Ray in inventory)            │
│                                          │
└──────────────────────────────────────────┘
```

### Example 2: Mouse Path Visualization

```
┌──────────────────────────────────────────┐
│         OSRS Game Client                 │
│                                          │
│    Start                                 │
│      ●─────╮                            │
│            │  Bezier curve (yellow)      │
│            ╰─────╮                       │
│                  │                       │
│                  ╰──────● Target        │
│                         ⭕ Red circle    │
│                                          │
└──────────────────────────────────────────┘
```

### Example 3: OCR Region Debugging

```python
# In GameState
def get_hp(self) -> Optional[int]:
    hp_region = self.config.get("coordinates", "ocr", "hp_region")

    # DEBUG: Draw OCR region
    if self.overlay and self.overlay.enabled:
        self.overlay.draw_rectangle(
            hp_region['x'], hp_region['y'],
            hp_region['width'], hp_region['height'],
            color=Color.BLUE, thickness=2, duration=1.0
        )

    hp = self.ocr_service.read_number(...)

    # DEBUG: Show OCR result
    if self.overlay and self.overlay.enabled:
        self.overlay.draw_text(
            hp_region['x'], hp_region['y'] - 10,
            f"HP: {hp}", color=Color.GREEN
        )

    return hp
```

---

## System Flow Update

```
┌─────────────────────────────────────────────────────────────────┐
│                      SERVICES LAYER                              │
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐ │
│  │ MouseService│  │ScreenService│ │ OCRService │  │ Overlay   │ │
│  │            │  │            │  │            │  │ Service   │ │
│  │ click_at() │  │find_color()│  │read_number()│ │           │ │
│  │    │       │  │    │       │  │    │       │  │ NEW!      │ │
│  │    ▼       │  │    ▼       │  │    ▼       │  │           │ │
│  │ overlay.   │  │ overlay.   │  │ overlay.   │  │ • draw_   │ │
│  │ draw_      │  │ draw_      │  │ draw_      │  │   circle()│ │
│  │ circle()   │  │ circle()   │  │ rectangle()│  │ • draw_   │ │
│  │            │  │            │  │            │  │   rect()  │ │
│  └────────────┘  └────────────┘  └────────────┘  │ • draw_   │ │
│                                                   │   line()  │ │
│                                                   │ • draw_   │ │
│                                                   │   path()  │ │
│                                                   │ • track() │ │
│                                                   └─────┬─────┘ │
└─────────────────────────────────────────────────────────┼───────┘
                                                          │
                                                          ▼
                                                  ┌───────────────┐
                                                  │ Transparent   │
                                                  │ Overlay Window│
                                                  │               │
                                                  │ (on top of    │
                                                  │  game client) │
                                                  └───────────────┘
```

---

## Implementation Options

### Option A: OpenCV + Win32 Transparent Window (Recommended)

**Pros:**
- Full control over rendering
- Can save overlay as screenshots
- Good performance

**Cons:**
- More complex setup
- Windows-specific (for now)

```python
import cv2
import numpy as np
from win32gui import SetWindowLong, SetLayeredWindowAttributes
from win32con import WS_EX_LAYERED, WS_EX_TRANSPARENT, LWA_COLORKEY

class OverlayService:
    def _create_overlay_window(self):
        # Create transparent window
        cv2.namedWindow("Overlay", cv2.WINDOW_NORMAL)
        cv2.setWindowProperty("Overlay", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        # Set transparency
        # ... Win32 API calls ...
```

### Option B: Tkinter Transparent Canvas (Simpler)

**Pros:**
- Cross-platform
- Built into Python
- Simpler code

**Cons:**
- Less control
- Potential performance issues with many shapes

```python
import tkinter as tk

class OverlayService:
    def _create_overlay_window(self):
        self.root = tk.Tk()
        self.root.attributes('-alpha', 0.6)  # Semi-transparent
        self.root.attributes('-topmost', True)  # Always on top
        self.canvas = tk.Canvas(self.root, bg='black')
        self.canvas.pack(fill='both', expand=True)
```

### Option C: PyQt5 Overlay (Most Powerful)

**Pros:**
- Professional-grade
- Excellent rendering
- Full GUI capabilities

**Cons:**
- Extra dependency
- Overkill for simple overlays

---

## Configuration

Add overlay settings to config.json:

```json
{
  "overlay": {
    "enabled": false,
    "default_duration": 2.0,
    "max_shapes": 100,
    "track_mouse_path": true,
    "colors": {
      "click": "#FF0000",
      "target": "#00FF00",
      "path": "#00FFFF",
      "ocr_region": "#0000FF"
    }
  }
}
```

---

## Usage Examples

### Debug Mode Script

```python
def green_dragons_debug(interface, state, actions, config):
    """Green dragons with full visual debugging"""

    # Enable overlay if available
    if hasattr(actions, 'overlay') and actions.overlay:
        overlay = actions.overlay
        overlay.enable()

    try:
        while not state.inventory_full():
            hp = state.get_hp()  # Draws OCR region + result

            if hp < 70:
                actions.eat("manta_ray")  # Draws circle on food

            if not state.in_combat():
                actions.attack("green_dragon")  # Draws circle on NPC

        # Final summary overlay
        if overlay:
            overlay.draw_text(400, 300, "✓ Inventory Full!",
                            color=Color.GREEN, font_size=24, duration=5.0)
    finally:
        if overlay:
            overlay.clear()
            overlay.disable()
```

---

## Benefits

✅ **Visual Debugging** - See exactly what bot is doing
✅ **Development Speed** - Instant feedback on clicks/targets
✅ **Validation** - Ensure bot clicks correct locations
✅ **Learning** - Understand bot behavior visually
✅ **Optional** - Zero impact when disabled
✅ **Reusable** - Works across all scripts
✅ **Non-invasive** - Scripts don't need to change

---

## Future Enhancements

1. **Recording** - Save overlay + game screen as video
2. **Heatmaps** - Visualize click patterns over time
3. **Statistics** - Show APM, clicks/min, success rate
4. **Remote Viewing** - Web interface to watch bot remotely
5. **Annotation Tools** - Draw manual overlays for calibration
