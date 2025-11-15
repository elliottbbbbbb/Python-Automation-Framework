import time
import pyautogui

from osrsbot.game_interface import GameInterface
from osrsbot.game_state import GameState
from osrsbot.config  import Config
from osrsbot.actions import Actions

def guns_script(interface: GameInterface, state: GameState, 
                actions: Actions, config: Config, 
                bank_location: str = "GE", runs: int = 10):
    """
    Guns (Pickpocketing) task script:
    1. Teleport to location
    2. Pickpocket until inventory full
    3. Bank/sell loot at GE
    4. Repeat
    """
    
    print(f"\n💰 Starting Guns Script ({runs} runs)")
    
    for run in range(runs):
        print(f"\n=== Run {run + 1}/{runs} ===")
        
        # === SETUP ===
        print("Teleporting...")
        actions.click_slot(1)  # Teleport item
        actions.wait("long")
        
        # Walk to pickpocket location
        interface.click(700, 400)  # Minimap click (adjust in config)
        actions.wait("teleport")
        
        # === PICKPOCKET LOOP ===
        print("Pickpocketing...")
        pickpockets = 0
        
        while not state.inventory_full():
            if actions.attack("guns_npc"):
                pickpockets += 1
                if pickpockets % 10 == 0:
                    print(f"  Pickpocket #{pickpockets}")
            time.sleep(0.8)
        
        print(f"✓ Inventory full! ({pickpockets} pickpockets)")
        
        # Handle food
        actions.use_item("red_outline")  # Drop/eat sandwich
        actions.wait("medium")
        
        # === BANKING ===
        print("Banking at GE...")
        
        if bank_location == "GE":
            # Teleport to GE
            actions.teleport_ge()
            
            # Walk to GE clerk
            actions.walk_marker("yellow_tile_marker")
            actions.wait("long")
            
            # Click clerk
            coord = config.get("coordinates", "world", "ge_clerk")
            for _ in range(2):
                interface.click_coord(coord)
            actions.wait("medium")
            
            # Collect previous GP
            coord = config.get("coordinates", "ui", "ge_collect")
            interface.click_coord(coord)
            actions.wait("short")
            
            # Select items to sell
            color = config.get("colors", "red_outline")
            interface.click_color(color)
            actions.wait("short")
            
            # Set quantity to ALL
            interface.click(198, 239)
            actions.wait("medium")
            
            # Lower price 10%
            interface.click(313, 239)
            actions.wait("medium")
            
            # Confirm
            interface.click(257, 319)
            actions.wait("medium")
            
            pyautogui.press('escape')
            actions.wait("medium")
    
    print("\n✅ Guns script complete!")