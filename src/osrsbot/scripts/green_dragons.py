import time
import pyautogui

from osrsbot.game_interface import GameInterface
from osrsbot.game_state import GameState
from osrsbot.config  import Config
from osrsbot.actions import Actions

def green_dragons_script(interface: GameInterface, state: GameState, 
                         actions: Actions, config: Config, 
                         bank_location: str = "varrock", runs: int = 10):
    """
    Green Dragons task script:
    1. Teleport to location
    2. Use potions
    3. Kill dragons until inventory full
    4. Bank loot
    5. Repeat
    """
    
    print(f"\n🐉 Starting Green Dragons Script ({runs} runs)")
    
    for run in range(runs):
        print(f"\n=== Run {run + 1}/{runs} ===")
        
        # === SETUP ===
        print("Setting up...")
        actions.click_slot(1)  # Mythical cape
        actions.wait("long")
        
        # Walk to marker
        for _ in range(2):
            actions.walk_marker("yellow_tile_marker")
        actions.wait("long")
        
        # Navigate to dragons
        actions.click_minimap("green_dragons")
        actions.wait("medium")
        
        # Use potions
        actions.use_item("extended_antifire")
        actions.wait("medium")
        actions.use_item("super_combat")
        actions.wait("long")
        
        # === COMBAT LOOP ===
        print("Fighting dragons...")
        kills = 0
        
        while not state.inventory_full():
            # Health check
            hp = state.get_health()
            if hp and hp < 70:
                print(f"HP low ({hp}), eating...")
                actions.eat("manta_ray")
                actions.wait("medium")
            
            # Attack if not in combat
            if not state.in_combat():
                if actions.attack("green_dragon"):
                    kills += 1
                    print(f"  Kill #{kills}")
            
            time.sleep(1)
        
        print(f"✓ Inventory full! ({kills} kills)")
        
        # === BANKING ===
        print("Banking...")
        
        if bank_location == "varrock":
            # Teleport to Varrock
            actions.teleport_ge()
            actions.wait("long")
            
            interface.click(594, 85)  # Fountain
            actions.wait("teleport")
            
            # Walk to bank
            for _ in range(2):
                actions.walk_marker("yellow_tile_marker")
            actions.wait("long")
            
            # Open bank
            for _ in range(2):
                coord = config.get("coordinates", "world", "bank_booth")
                interface.click_coord(coord)
            actions.wait("long")
            
            # Deposit loot
            for _ in range(12):
                color = config.get("colors", "purple_item_outline")
                interface.click_color(color)
                actions.wait("short")
            
            # Withdraw food
            actions.wait("medium")
            interface.click(248, 346)  # Quantity
            actions.wait("medium")
            actions.bank_search("manta ray")
            interface.click(104, 231)  # Click food
            actions.wait("long")
            pyautogui.press('escape')
    
    print("\n✅ Green Dragons script complete!")