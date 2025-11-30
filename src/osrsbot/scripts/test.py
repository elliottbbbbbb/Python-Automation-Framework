import time

from osrsbot.models.state import GameState
from osrsbot.models.config import Config
from osrsbot.controllers.actions import GameActions as Actions


def test(interface, state: GameState,
         actions: Actions, config: Config,
         bank_location: str = "GE", runs: int = 10):
    for run in range(runs):
        hp = state.get_hp()
        print(hp)
        time.sleep(0.5)
