import time
import logging
from typing import Optional, Any
import pyautogui

from osrsbot.game_interface import GameInterface
from osrsbot.game_state import GameState
from osrsbot.config import Config

logger = logging.getLogger(__name__)


class Actions:
    """Common reusable actions (teleport, bank, etc.)"""
    
    def __init__(self, interface: GameInterface, state: GameState, config: Config) -> None:
        self.interface = interface
        self.state = state
        self.config = config
    
    def wait(self, timing_type: str) -> None:
        """Wait using configured timing."""
        try:
            delay = self.config.get("timings", timing_type, default=1.0)
            if delay is None or not isinstance(delay, (int, float, str)):
                logger.warning(f"Invalid timing value for '{timing_type}', using default 1.0s")
                delay = 1.0
            time.sleep(float(delay))
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid timing value for '{timing_type}', using default 1.0s: {e}")
            time.sleep(1.0)
    
    # === INVENTORY ===
    
    def click_slot(self, slot_num: int) -> bool:
        """Click inventory slot (1-28)."""
        if not 1 <= slot_num <= 28:
            logger.error(f"Invalid slot number: {slot_num}. Must be between 1 and 28.")
            return False
        
        try:
            coord = self.config.get("coordinates", "inventory", f"slot_{slot_num}")
            if coord:
                self.interface.click_coord(coord)
                return True
            else:
                logger.warning(f"No coordinates found for slot {slot_num}")
                return False
        except Exception as e:
            logger.error(f"Error clicking slot {slot_num}: {e}")
            return False
    
    def use_item(self, item_color_name: str) -> bool:
        """Use item by its color."""
        try:
            color = self.config.get("colors", item_color_name)
            if color and isinstance(color, str):
                return self.interface.click_color(color)
            else:
                logger.warning(f"No valid color found for item: {item_color_name}")
                return False
        except Exception as e:
            logger.error(f"Error using item '{item_color_name}': {e}")
            return False
    
    # === TELEPORTS ===
    
    def teleport_ge(self) -> bool:
        """Teleport to Grand Exchange."""
        try:
            for _ in range(2):
                if not self.click_slot(2):  # Varrock tab in slot 2
                    logger.error("Failed to click Varrock teleport tab")
                    return False
                self.wait("short")
            self.wait("teleport")
            return True
        except Exception as e:
            logger.error(f"Error teleporting to GE: {e}")
            return False
    
    def teleport_myth_cape(self) -> bool:
        """Teleport with Mythical Cape."""
        try:
            for _ in range(2):
                if not self.use_item("mythical_cape"):
                    logger.error("Failed to use mythical cape")
                    return False
                self.wait("short")
            return True
        except Exception as e:
            logger.error(f"Error teleporting with Mythical Cape: {e}")
            return False
    
    def teleport_ardy(self) -> bool:
        """Teleport with Ardy Cloak."""
        try:
            for _ in range(2):
                if not self.use_item("ardy_cloak"):
                    logger.error("Failed to use Ardy cloak")
                    return False
                self.wait("short")
            return True
        except Exception as e:
            logger.error(f"Error teleporting with Ardy Cloak: {e}")
            return False
    
    # === NAVIGATION ===
    
    def walk_marker(self, color_name: str) -> bool:
        """Walk to tile marker."""
        try:
            color = self.config.get("colors", color_name)
            if color and isinstance(color, str):
                return self.interface.click_color(color)
            else:
                logger.warning(f"No valid color found for marker: {color_name}")
                return False
        except Exception as e:
            logger.error(f"Error walking to marker '{color_name}': {e}")
            return False
    
    def click_minimap(self, location_name: str) -> bool:
        """Click minimap location."""
        try:
            coord = self.config.get("coordinates", "minimap", location_name)
            if coord:
                self.interface.click_coord(coord)
                return True
            else:
                logger.warning(f"No coordinates found for minimap location: {location_name}")
                return False
        except Exception as e:
            logger.error(f"Error clicking minimap location '{location_name}': {e}")
            return False
    
    # === BANKING ===
    
    def bank_search(self, item_name: str) -> bool:
        """Search in bank."""
        if not item_name:
            logger.error("Item name cannot be empty")
            return False
        
        try:
            coord = self.config.get("coordinates", "ui", "bank_search")
            if not coord:
                logger.error("Bank search coordinates not found in config")
                return False
            
            self.interface.click_coord(coord)
            self.wait("short")
            pyautogui.write(item_name)
            self.wait("short")
            return True
        except Exception as e:
            logger.error(f"Error searching bank for '{item_name}': {e}")
            return False
    
    def deposit_all(self) -> bool:
        """Deposit all inventory items to bank."""
        try:
            coord = self.config.get("coordinates", "ui", "bank_deposit_all")
            if not coord:
                logger.error("Bank deposit all coordinates not found in config")
                return False
            
            self.interface.click_coord(coord)
            self.wait("medium")
            return True
        except Exception as e:
            logger.error(f"Error depositing all items: {e}")
            return False
    
    # === COMBAT ===
    
    def attack(self, npc_color_name: str) -> bool:
        """Attack NPC by color."""
        try:
            logger.debug(f"Attacking NPC: {npc_color_name}")
            return self.use_item(npc_color_name)
        except Exception as e:
            logger.error(f"Error attacking NPC '{npc_color_name}': {e}")
            return False
    
    def eat(self, food_color_name: str) -> bool:
        """Eat food."""
        try:
            return self.use_item(food_color_name)
        except Exception as e:
            logger.error(f"Error eating food '{food_color_name}': {e}")
            return False