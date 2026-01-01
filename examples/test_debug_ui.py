"""
Example script demonstrating the Debug UI feature.

This script shows how to enable the terminal debug UI for real-time
monitoring of bot state, events, stats, and anti-ban status.

Usage:
    python examples/test_debug_ui.py

Requirements:
    - pip install rich>=13.7.0
    - RuneScape client must be running and logged in
"""

import logging

from osrsbot.core.runner import ScriptRunner
from osrsbot.scripts.test_state_machine_bot import StateMachineTestBot

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Run test bot with debug UI enabled."""

    # Initialize script runner
    logger.info("Initializing ScriptRunner...")
    runner = ScriptRunner("RuneLite - 61grouphunt", "config.json")

    # Create bot instance with debug UI enabled
    logger.info("Creating bot with debug UI enabled...")
    bot = StateMachineTestBot(
        interface=runner.interface,
        state=runner.state,
        actions=runner.actions,
        config=runner.config,
        debug_ui=True,  # Enable debug UI
    )

    # Run bot
    logger.info("Starting bot with debug UI...")
    logger.info("Press Ctrl+C to stop")

    try:
        bot.run(bank_location="", runs=999)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        logger.info("Cleanup complete")


if __name__ == "__main__":
    main()
