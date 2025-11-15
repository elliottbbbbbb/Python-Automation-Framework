import re
import time
import pytesseract
from typing import Optional
from PIL import ImageEnhance, ImageFilter, ImageOps

from osrsbot.game_interface import GameInterface
from osrsbot.config import Config


class GameState:
    """Query game state (inventory, combat, health, etc.)"""
    
    def __init__(self, interface: GameInterface, config: Config):
        self.interface = interface
        self.config = config
        self._health_cache = None
        self._health_time = 0
    
    def inventory_full(self) -> bool:
        """Check if inventory is full"""
        coord = self.config.get("coordinates", "inventory", "last_slot")
        color = self.interface.get_pixel(coord['x'], coord['y'])
        return color != (75, 66, 58)  # Empty slot color
    
    def in_combat(self) -> bool:
        """Check if player is in combat"""
        coord = self.config.get("coordinates", "checks", "combat_indicator")
        color = self.interface.get_pixel(coord['x'], coord['y'])
        
        combat_colors = [(7, 139, 54), (99, 21, 19)]
        tolerance = self.config.get("tolerances", "color_match")
        
        return any(
            all(abs(color[i] - cc[i]) <= tolerance for i in range(3))
            for cc in combat_colors
        )

    def clean_ocr_text(self, text):
        """Fix common OCR misreads for digits"""
        replacements = {
            'i': '1', 'I': '1', 'l': '1', '|': '1',
            'o': '0', 'O': '0', 'Q': '0',
            'S': '5', 's': '5',
            'Z': '2', 'z': '2',
            'B': '8', 'g': '9', 'G': '6',
            ' ': '', '\n': '', '\r': '', '\t': '',
            'D': '0', 'd': '0'
        }
         
        cleaned = text
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        
        return cleaned
    

    def get_health(self):
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' 
        window_position = self.interface._find_window()
        if not window_position:
            print("Window not found")
            return None
        
        
        # Define hp region - crop tighter to avoid the heart icon
        hp_region = (520 , 79, 35, 20)

        # Screenshot hp region
        screenshot = self.interface.screenshot(region=hp_region)
        
        # Convert to grayscale
        screenshot = screenshot.convert('L')
        
        # INVERT: white text on black -> black text on white
        screenshot = ImageOps.invert(screenshot)
        
        # Scale up FIRST (before other processing)
        screenshot = screenshot.resize((screenshot.width * 5, screenshot.height * 5))
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(screenshot)
        screenshot = enhancer.enhance(2.5)
        
        # Apply threshold with lower value to preserve detail
        screenshot = screenshot.point(lambda p: 255 if p > 100 else 0)
        
        screenshot.save("debug.png")
        
        # Try multiple OCR configurations with digit whitelist
        configs = [
            r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789',
            r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789',
            r'--oem 1 --psm 7 -c tessedit_char_whitelist=0123456789',
            r'--oem 3 --psm 13 -c tessedit_char_whitelist=0123456789',
            r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789',
        ]
        
        results = []
        
        for config in configs:
            text = pytesseract.image_to_string(screenshot, config=config)
            print(f"Raw OCR (psm={config.split('--psm')[1].split()[0]}): '{text.strip()}'")
            
            # Clean the OCR output
            cleaned_text = self.clean_ocr_text(text)
            print(f"Cleaned: '{cleaned_text}'")
            
            # Extract digits
            hp = re.findall(r'\d+', cleaned_text)
            if hp:
                hp_value = int(hp[0])
                # Sanity check: HP should be reasonable (1-99 for OSRS)
                if 1 <= hp_value <= 99:
                    results.append(hp_value)
        
        # Return most common result if we got any
        if results:
            from collections import Counter
            most_common = Counter(results).most_common(1)[0][0]
            print(f"Found HP (consensus): {most_common}")
            return most_common
        
        print("No valid HP found")
        return None