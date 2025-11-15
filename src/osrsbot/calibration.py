import time
import mouse
import pyautogui
import pywinctl as gw

from osrsbot.config import Config

class Calibrator:
    """Interactive color and coordinate calibration"""
    
    def __init__(self, config: Config):
        self.config = config
        self.window = None
        self.capturing = False
    
    def start(self, window_title: str):
        """Start interactive calibration"""
        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            print(f"❌ Window '{window_title}' not found!")
            return
        
        self.window = windows[0]
        print("\n" + "="*60)
        print("COLOR & COORDINATE CALIBRATION")
        print("="*60)
        print("\nInstructions:")
        print("  • LEFT CLICK  - Capture color at cursor")
        print("  • RIGHT CLICK - Capture coordinates at cursor")
        print("  • Press 'q'   - Finish and save\n")
        print("Hover over items/UI elements and click to capture!\n")
        
        def on_left_click():
            if not self.capturing:
                return
            self._capture_color()
        
        def on_right_click():
            if not self.capturing:
                return
            self._capture_coordinate()
        
        mouse.on_button(lambda: on_left_click(), buttons=('left',), types=('down',))
        mouse.on_button(lambda: on_right_click(), buttons=('right',), types=('down',))
        
        self.capturing = True
        try:
            import keyboard
            keyboard.wait('q')
        finally:
            self.capturing = False
            mouse.unhook_all()
            self.config.save()
            print("\n✅ Calibration saved to config.json")
    
    def _capture_color(self):
        """Capture color at cursor position"""
        mouse_x, mouse_y = pyautogui.position()
        win_x, win_y = self.window.topleft
        rel_x = mouse_x - win_x
        rel_y = mouse_y - win_y
        
        r, g, b = pyautogui.pixel(mouse_x, mouse_y)
        hex_color = f"#{r:02x}{g:02x}{b:02x}".upper()
        
        print(f"\n📌 COLOR: {hex_color} at ({rel_x}, {rel_y})")
        name = input("   Name (or Enter to skip): ").strip()
        
        if name:
            self.config.data["colors"][name] = hex_color
            print(f"   ✓ Saved as '{name}'")
    
    def _capture_coordinate(self):
        """Capture coordinates at cursor position"""
        mouse_x, mouse_y = pyautogui.position()
        win_x, win_y = self.window.topleft
        rel_x = mouse_x - win_x
        rel_y = mouse_y - win_y
        
        print(f"\n📍 COORD: ({rel_x}, {rel_y})")
        name = input("   Name (or Enter to skip): ").strip()
        
        if name:
            # Determine category
            category = input("   Category (ui/minimap/world/inventory): ").strip() or "ui"
            
            if category not in self.config.data["coordinates"]:
                self.config.data["coordinates"][category] = {}
            
            self.config.data["coordinates"][category][name] = {"x": rel_x, "y": rel_y}
            print(f"   ✓ Saved as '{category}.{name}'")