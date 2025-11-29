import time
import pyautogui

from time import sleep
from osrsbot.game_interface import GameInterface
from osrsbot.game_state import GameState
from osrsbot.config  import Config
from osrsbot.actions import Actions

def test(interface: GameInterface, state: GameState, 
                actions: Actions, config: Config, 
                bank_location: str = "GE", runs: int = 10):
    for run in range(runs):
        hp = state.get_hp()
        print(hp)
        time.sleep(0.5)