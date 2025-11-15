import time
import pyautogui

from osrsbot.game_interface import GameInterface
from osrsbot.game_state import GameState
from osrsbot.config import Config

class Actions:
    """Common reusable actions (teleport, bank, etc.)"""
    
    def __init__(self, interface: GameInterface, state: GameState, config: Config):
        self.interface = interface
        self.state = state
        self.config = config
    
    def wait(self, timing_type: str):
        """Wait using configured timing"""
        time.sleep(self.config.get("timings", timing_type, default=1.0))
    
    # === INVENTORY ===
    
    def click_slot(self, slot_num: int):
        """Click inventory slot (1-28)"""
        coord = self.config.get("coordinates", "inventory", f"slot_{slot_num}")
        if coord:
            self.interface.click_coord(coord)
    
    def use_item(self, item_color_name: str) -> bool:
        """Use item by its color"""
        color = self.config.get("colors", item_color_name)
        if color:
            return self.interface.click_color(color)
        return False
    
    # === TELEPORTS ===
    
    def teleport_ge(self):
        """Teleport to Grand Exchange"""
        for _ in range(2):
            self.click_slot(2)  # Varrock tab in slot 2
            self.wait("short")
        self.wait("teleport")
    
    def teleport_myth_cape(self):
        """Teleport with Mythical Cape"""
        for _ in range(2):
            self.use_item("mythical_cape")
            self.wait("short")
    
    def teleport_ardy(self):
        """Teleport with Ardy Cloak"""
        for _ in range(2):
            self.use_item("ardy_cloak")
            self.wait("short")
    
    # === NAVIGATION ===
    
    def walk_marker(self, color_name: str):
        """Walk to tile marker"""
        color = self.config.get("colors", color_name)
        if color:
            self.interface.click_color(color)
    
    def click_minimap(self, location_name: str):
        """Click minimap location"""
        coord = self.config.get("coordinates", "minimap", location_name)
        if coord:
            self.interface.click_coord(coord)
    
    # === BANKING ===
    
    def bank_search(self, item_name: str):
        """Search in bank"""
        coord = self.config.get("coordinates", "ui", "bank_search")
        self.interface.click_coord(coord)
        self.wait("short")
        pyautogui.write(item_name)
        self.wait("short")
    
    def deposit_all(self):
        """Click deposit all"""
        coord = self.config.get("coordinates", "ui", "bank_deposit_all")
        self.interface.click_coord(coord)
        self.wait("medium")
    
    # === COMBAT ===
    
    def attack(self, npc_color_name: str) -> bool:
        """Attack NPC by color"""
        color = self.config.get("colors", "blue_tile_marker")
        print(npc_color_name)
        print(color) 
        return self.use_item(npc_color_name)
    
    def eat(self, food_color_name: str):
        """Eat food"""
        self.use_item(food_color_name)

