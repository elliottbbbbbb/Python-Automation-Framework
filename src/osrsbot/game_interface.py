import random
import pyautogui
import pywinctl as gw
from typing import Tuple, Optional

from osrsbot.config import Config

class GameInterface:
    """Low-level interface for clicking and color detection"""
    
    def __init__(self, config: Config):
        self.config = config
        self.window = self._find_window()
    
    def _find_window(self):
        """Find the OSRS client window"""
        title = self.config.get("window_title")
        title = "RuneLite - 61grouphunt"
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            raise Exception(f"Window '{title}' not found!")
        return windows[0]
    
    def click(self, x: int, y: int, button='left', offset=(0, 0)):
        """Click at coordinates relative to window"""
        left, top = self.window.topleft
        width, height = self.window.size
        
        if not (0 <= x < width and 0 <= y < height):
            print(f"⚠️  Coords ({x}, {y}) outside window")
            return
        
        ox = random.randint(-offset[0], offset[0])
        oy = random.randint(-offset[1], offset[1])
        
        pyautogui.click(left + x + ox, top + y + oy, button=button)
    
    def click_coord(self, coord: dict, button='left'):
        """Click using coordinate dict"""
        self.click(coord['x'], coord['y'], button)
    
    def find_color(self, hex_color: str, tolerance: int = None) -> Optional[Tuple[int, int]]:
        """Find first occurrence of color"""
        if tolerance is None:
            tolerance = self.config.get("tolerances", "color_match")
        
        target = self._hex_to_rgb(hex_color)
        left, top = self.window.topleft
        width, height = self.window.size
        
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        pixels = screenshot.load()
        
        for x in range(screenshot.width):
            for y in range(screenshot.height):
                if self._color_match(pixels[x, y][:3], target, tolerance):
                    return (x, y)
        return None
    
    def click_color(self, hex_color: str, offset=(0, 0), tolerance: int = None) -> bool:
        """Find and click a color"""
        pos = self.find_color(hex_color, tolerance)
        if pos:
            self.click(pos[0] + offset[0], pos[1] + offset[1])
            return True
        return False
    
    def get_pixel(self, x: int, y: int) -> Tuple[int, int, int]:
        """Get RGB at coordinate"""
        left, top = self.window.topleft
        return pyautogui.pixel(left + x, top + y)
    
    def screenshot(self, region: Tuple[int, int, int, int] = None):
        """Take screenshot of window or region"""
        left, top = self.window.topleft
        if region:
            return pyautogui.screenshot(region=(
                left + region[0], top + region[1], region[2], region[3]
            ))
        width, height = self.window.size
        return pyautogui.screenshot(region=(left, top, width, height))
    
    @staticmethod
    def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def _color_match(c1: Tuple, c2: Tuple, tolerance: int) -> bool:
        return all(abs(c1[i] - c2[i]) <= tolerance for i in range(3))
