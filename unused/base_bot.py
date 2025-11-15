from abc import ABC, abstractmethod
from osrsbot.game_interface import GameInterface
from osrsbot.actions import Actions
from osrsbot.game_state import GameState
from osrsbot.config import Config

class BaseBot(ABC):
    """Base class for all bots - inherit from this!"""
    
    def __init__(self, window_title: str, config_file: str = "bot_config.json"):
        self.config = Config(config_file)
        self.interface = GameInterface(self.config, window_title)
        self.state = GameState(self.interface, self.config)
        self.actions = Actions(self.interface, self.config)
        
        self.is_running = False
        self.run_count = 0
    
    @abstractmethod
    def setup(self):
        """Called once before bot starts - setup inventory, etc."""
        pass
    
    @abstractmethod
    def run_cycle(self):
        """Main bot loop - called repeatedly"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Called when bot stops - bank items, etc."""
        pass
    
    def start(self, max_runs: int = None):
        """Start the bot"""
        self.is_running = True
        print(f"Starting {self.__class__.__name__}...")
        
        try:
            self.setup()
            
            while self.is_running:
                if max_runs and self.run_count >= max_runs:
                    break
                
                self.run_cycle()
                self.run_count += 1
                
        except KeyboardInterrupt:
            print("\nBot interrupted by user")
        except Exception as e:
            print(f"\nBot error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()
            print(f"Bot stopped after {self.run_count} runs")
    
    def stop(self):
        """Stop the bot"""
        self.is_running = False