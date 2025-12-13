"""
OSRS Bot - Automated OSRS gameplay.

Structure:
- models: Data and state (Config, GameState)
- queries: Read operations (GameState queries, CQRS pattern)
- commands: Write operations (GameActions, CQRS pattern)
- core: Core infrastructure (ScriptRunner, GameInterface, base bots)
- app: Application layer (CLI, calibration)
- services: Infrastructure (mouse, screen, OCR, window)
- scripts: Bot scripts and use cases
"""

__version__ = "0.1.0"

# Export main components for convenience
from osrsbot.models import Config
from osrsbot.queries import GameState
from osrsbot.commands import GameActions
from osrsbot.core.runner import ScriptRunner
from osrsbot.app import Calibrator

__all__ = [
    'Config',
    'GameState',
    'GameActions',
    'ScriptRunner',
    'Calibrator',
]
