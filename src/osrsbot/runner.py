from typing import Any, Callable
from osrsbot.game_interface import GameInterface
from osrsbot.actions import Actions
from osrsbot.game_state import GameState
from osrsbot.config import Config

class ScriptRunner:
    """Main script runner that sets up everything"""
    
    def __init__(self, window_title: str, config_file: str = "config.json") -> None:
        self.config = Config(config_file)
        
        # Update window title if provided
        if window_title:
            self.config.data["window_title"] = window_title
        
        self.interface = GameInterface(self.config)
        self.state = GameState(self.interface, self.config)
        self.actions = Actions(self.interface, self.state, self.config)
    
    def run_script(self, script_func: Callable, **kwargs: Any) -> None:
        """Run a script function with all dependencies"""
        script_func(self.interface, self.state, self.actions, self.config, **kwargs)
