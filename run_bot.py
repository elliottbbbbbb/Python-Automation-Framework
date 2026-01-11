"""
OSRS Bot - Main Entry Point

This script demonstrates how the license system is integrated.
Every bot that uses ScriptRunner will automatically validate licenses.
"""

import sys
from osrsbot.core.runner import ScriptRunner

# Import your bot scripts
from osrsbot.scripts.afk.nmz_afk import NMZAfkBot
# Add more imports as needed
# from osrsbot.scripts.skills.mining_bot import MiningBot
# from osrsbot.scripts.combat.basic_npc_killer import BasicNPCKiller


def main():
    print("="*60)
    print("  OSRS Bot Launcher")
    print("="*60)
    print()
    print("Available bots:")
    print("1. NMZ AFK Bot")
    print("2. Exit")
    print()

    choice = input("Select bot (1-2): ").strip()

    if choice == "2":
        print("Exiting...")
        return

    bot_class = None

    if choice == "1":
        bot_class = NMZAfkBot
        print("\nStarting NMZ AFK Bot...")
    else:
        print("Invalid choice!")
        return

    try:
        # ScriptRunner initialization will automatically validate license
        # If no valid license, GUI dialog appears
        # If license expired, bot exits with error message
        print("\nInitializing bot (validating license)...")
        runner = ScriptRunner("Old School RuneScape", config_file="src/osrsbot/config.json")

        print("✓ License validated successfully!")
        print("\nStarting bot script...")

        # Run the bot
        runner.run(bot_class)

    except SystemExit as e:
        # License validation failed - exit gracefully
        if e.code == 1:
            print("\n" + "="*60)
            print("  Bot startup cancelled due to license issue")
            print("="*60)
        sys.exit(e.code)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
