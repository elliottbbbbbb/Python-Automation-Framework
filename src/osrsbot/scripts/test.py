import time
import logging
# Assuming these imports are available in your runner environment
from osrsbot.models.state import GameState
from osrsbot.models.config import Config
from osrsbot.controllers.actions import GameActions as Actions

logger = logging.getLogger(__name__)

# NOTE: The 'interface' object is assumed to be an instance of GameInterface 
# passed by your script runner.
def test_script(
    interface, 
    state: GameState, 
    actions: Actions, 
    config: Config, 
    bank_location: str = "GE", 
    runs: int = 10
) -> None:
    """
    Standalone function for testing core functionality, including the window 
    bounds refresh fix.
    """
    print(f"\n=== Starting Test Script ({runs} runs) ===")
    
    # 1. CRITICAL FIX: REFRESH WINDOW BOUNDS
    # This function uses the 'interface' dependency to get the new position
    # and updates the 'ScreenService' instance accessible via 'state'.
    try:
        logger.info("Refreshing window bounds...")
        
        # Assumes interface.get_current_window_bounds() is implemented to talk to the OS
        new_bounds = interface.get_window_position() 
        
        # Assumes state exposes the screen service via 'state.screen' 
        # which has the set_window_bounds method.
        state.screen.set_window_bounds(*new_bounds)
         
        
        logger.info(f"Window bounds successfully set to: {new_bounds}")
    except Exception as e:
        logger.error(f"Failed to refresh window bounds: {e}. Mouse clicks will likely fail.", exc_info=True)
        return # Stop script if bounds cannot be set safely

    # 2. EXECUTE TEST LOOP LOGIC
    for run in range(runs):
        # Refresh bounds every iteration to handle window movement
        try:
            new_bounds = interface.get_window_position()
            if state.screen and new_bounds != state.screen.window_bounds:
                logger.info(f"Window moved, updating bounds: {new_bounds}")
                state.screen.set_window_bounds(*new_bounds)
        except Exception as e:
            logger.warning(f"Failed to refresh bounds: {e}")

        hp = state.get_health()
        print(f"Run {run + 1}/{runs}: Current HP = {hp}")

        # Corrected coordinate lookup syntax and action call
        #actions.click_coordinate(("ui", "settings"), "curved")
        logger.info("Clicking at yellow tile marker")
        actions.click_color("yellow_tile_marker")
        time.sleep(3.5)

    print("\n✅ Test script complete.")