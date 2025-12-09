"""
OSRS Bot - Automated OSRS gameplay.

Structure:
- models: Data and state (Config, GameState)
- app: Application layer (CLI, calibration)
- controllers: Business logic (GameActions, ScriptRunner)
- services: Infrastructure (mouse, screen, OCR, window)
- scripts: Bot scripts and use cases
"""

__version__ = "0.1.0"

# Export main components for convenience
from osrsbot.models import Config, GameState
from osrsbot.controllers import GameActions, ScriptRunner
from osrsbot.app import Calibrator

__all__ = [
    'Config',
    'GameState',
    'GameActions',
    'ScriptRunner',
    'Calibrator',
]
