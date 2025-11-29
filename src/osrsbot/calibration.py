import logging
import mouse
from typing import Optional
import pyautogui
import pywinctl as gw

from osrsbot.config import Config

logger = logging.getLogger(__name__)


class Calibrator:
    """Interactive color and coordinate calibration"""
    
    def __init__(self, config: Config) -> None:
        self.config = config
        self.window: Optional[gw.Window] = None
        self.capturing: bool = False
    
    def start(self, window_title: str) -> None:
        """Start interactive calibration."""
        if not window_title or not window_title.strip():
            logger.error("Window title cannot be empty")
            print("âŒ Window title is required")
            return

        try:
            windows = gw.getWindowsWithTitle(window_title)
        except Exception as e:
            logger.error(f"Error searching for windows: {e}", exc_info=True)
            print(f"âŒ Failed to search for windows: {e}")
            return

        if not windows:
            logger.error(f"Window {window_title} not found")
            print(f"âŒ Window '{window_title}' not found")
            return

        self.window = windows[0]
        print("\n" + "="*60)
        print("COLOR & COORDINATE CALIBRATION")
        print("="*60)
        print("\nInstructions:")
        print("  â€¢ LEFT CLICK  - Capture color at cursor")
        print("  â€¢ RIGHT CLICK - Capture coordinates at cursor")
        print("  â€¢ Press 'q'   - Finish and save\n")
        print("Hover over items/UI elements and click to capture!\n")
        
        def on_left_click() -> None:
            if not self.capturing:
                return
            self._capture_color()
        
        def on_right_click() -> None:
            if not self.capturing:
                return
            self._capture_coordinate()
        
        mouse.on_button(lambda: on_left_click(), buttons=('left',), types=('down',))
        mouse.on_button(lambda: on_right_click(), buttons=('right',), types=('down',))

        self.capturing = True
        try:
            try:
                import keyboard
            except ImportError as e:
                logger.error("keyboard module not installed")
                print("âŒ 'keyboard' module required. Install with: pip install keyboard")
                return

            keyboard.wait('q')
        finally:
            self.capturing = False
            mouse.unhook_all()
            self.config.save()
            print("\nâœ“ Calibration saved to config.json")
    
    def _capture_color(self) -> None:
        """Capture color at cursor position."""
        if not self.window:
            logger.error("Window reference missing during color capture")
            print("Invalid window reference")
            return

        try:
            mouse_x, mouse_y = pyautogui.position()
            win_x, win_y = self.window.topleft
            rel_x = mouse_x - win_x
            rel_y = mouse_y - win_y
        
            r, g, b = pyautogui.pixel(mouse_x, mouse_y)
            hex_color = f"#{r:02x}{g:02x}{b:02x}".upper()
            
            print(f"\n COLOR: {hex_color} at ({rel_x}, {rel_y})")
            name = input("   Name (or Enter to skip): ").strip()

            if name:
                self.config.data["colors"][name] = hex_color
                print(f"   âœ“ Saved as '{name}'")
            
        except Exception as e:
            logger.error(f"Failed to capture color: {e}")
            print(f"    Failed to capture color")
    
    def _capture_coordinate(self) -> None:
        """Capture coordinates at cursor position."""
        if not self.window:
            logger.error("Window reference missing during coordinate capture")
            print("Invalid window reference")
            return
            
        try:
            logger.debug("Starting coordinate capture")
            mouse_x, mouse_y = pyautogui.position()
            win_x, win_y = self.window.topleft
            rel_x = mouse_x - win_x
            rel_y = mouse_y - win_y
           
            logger.debug(f"Raw coords: mouse=({mouse_x}, {mouse_y}), window=({win_x}, {win_y})")
            logger.debug(f"Relative coords calculated: ({rel_x}, {rel_y})")
            
            print(f"\n COORD: ({rel_x}, {rel_y})")
            name = input("   Name (or Enter to skip): ").strip()
           
            if not name:
                logger.debug("Coordinate capture skipped (no name given)")
                return
            
            category = input("   Category (ui/minimap/world/inventory): ").strip() or "ui"
               
            if category not in self.config.data["coordinates"]:
                logger.debug(f"Creating new category {category}")
                self.config.data["coordinates"][category] = {}
               
            self.config.data["coordinates"][category][name] = {"x": rel_x, "y": rel_y}
            logger.info(f"Saved coordinate: {category}.{name} = ({rel_x}, {rel_y})")
            print(f"   âœ“ Saved as '{category}.{name}'")

        except Exception as e:
            logger.error(f"Error capturing coordinate: {e}", exc_info=True)
            print(f"    Failed to capture coordinate")