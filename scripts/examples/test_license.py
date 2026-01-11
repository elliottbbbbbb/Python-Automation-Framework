"""
Simple script to test license validation.

This will trigger the license check when ScriptRunner is initialized.
"""

from osrsbot.core.runner import ScriptRunner
from osrsbot.scripts.afk.nmz_afk import NMZAfkBot

def main():
    print("="*60)
    print("  Testing License Validation")
    print("="*60)
    print()

    # This will trigger license validation in ScriptRunner.__init__()
    # If no valid license exists, the GUI dialog will appear
    runner = ScriptRunner("Old School RuneScape", config_file="src/osrsbot/config.json")

    print()
    print("✓ License validation passed!")
    print("Bot is ready to run.")
    print()
    print("="*60)

if __name__ == "__main__":
    main()
