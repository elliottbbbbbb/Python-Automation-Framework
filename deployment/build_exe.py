"""
Build OSRS Bot as standalone executable.

This script packages the bot with all dependencies into a single .exe file.
Users can run the exe without installing Python.

Usage:
    python deployment/build_exe.py

Output:
    dist/OSRS_Bot.exe
"""

import PyInstaller.__main__
import os
import sys
from pathlib import Path

# Get paths
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
OSRSBOT_DIR = SRC_DIR / "osrsbot"
ENTRY_POINT = OSRSBOT_DIR / "app" / "menu.py"

print("="*60)
print("  OSRS Bot - Executable Builder")
print("="*60)
print()
print(f"Project root: {PROJECT_ROOT}")
print(f"Entry point:  {ENTRY_POINT}")
print()

# Verify entry point exists
if not ENTRY_POINT.exists():
    print(f"❌ Error: Entry point not found: {ENTRY_POINT}")
    sys.exit(1)

# PyInstaller options
pyinstaller_args = [
    str(ENTRY_POINT),
    '--name=OSRS_Bot',
    '--onefile',  # Single executable file
    # '--windowed',  # Uncomment to hide console window
    '--icon=NONE',  # Add '--icon=bot_icon.ico' if you have an icon

    # Include data files
    f'--add-data={OSRSBOT_DIR};osrsbot',
    f'--add-data={OSRSBOT_DIR / "config.json"};osrsbot',
    f'--add-data={OSRSBOT_DIR / "images"};osrsbot/images',

    # Include hidden imports (modules PyInstaller might miss)
    '--hidden-import=osrsbot',
    '--hidden-import=osrsbot.app',
    '--hidden-import=osrsbot.app.menu',
    '--hidden-import=osrsbot.app.calibration',
    '--hidden-import=osrsbot.core',
    '--hidden-import=osrsbot.core.runner',
    '--hidden-import=osrsbot.core.game_interface',
    '--hidden-import=osrsbot.services',
    '--hidden-import=osrsbot.services.license_service',
    '--hidden-import=osrsbot.services.hardware_fingerprint',
    '--hidden-import=osrsbot.ui',
    '--hidden-import=osrsbot.ui.license_dialog',
    '--hidden-import=osrsbot.exceptions',
    '--hidden-import=osrsbot.exceptions.license_exceptions',
    '--hidden-import=osrsbot.scripts',
    '--hidden-import=osrsbot.scripts.afk',
    '--hidden-import=osrsbot.scripts.afk.nmz_afk',
    '--hidden-import=osrsbot.scripts.bosses',
    '--hidden-import=osrsbot.scripts.bosses.zulrah',
    '--hidden-import=osrsbot.scripts.combat',
    '--hidden-import=osrsbot.scripts.combat.basic_npc_killer',
    '--hidden-import=osrsbot.scripts.bankstanding',
    '--hidden-import=osrsbot.scripts.bankstanding.bankstanding_flax',
    '--hidden-import=osrsbot.scripts.tests',
    '--hidden-import=osrsbot.scripts.tests.comprehensive_state_bot_test',
    '--hidden-import=osrsbot.scripts.tests.hp_tracker',
    '--hidden-import=osrsbot.scripts.tests.test_inventory_clicks',

    # Include dependencies
    '--hidden-import=requests',
    '--hidden-import=cv2',
    '--hidden-import=numpy',
    '--hidden-import=PIL',
    '--hidden-import=pyautogui',
    '--hidden-import=pytesseract',
    '--hidden-import=tkinter',
    '--hidden-import=logging',

    # Build options
    '--clean',
    '--noconfirm',
]

print("Building executable...")
print("This may take several minutes...")
print()
print("Tip: While waiting, make sure you've updated config.json with:")
print("  - Your Railway API URL")
print("  - Your purchase page URL")
print()

try:
    # Change to project root for build
    os.chdir(PROJECT_ROOT)

    PyInstaller.__main__.run(pyinstaller_args)

    print()
    print("="*60)
    print("  ✓ Build Complete!")
    print("="*60)
    print()
    print(f"Executable: {PROJECT_ROOT / 'dist' / 'OSRS_Bot.exe'}")
    print()
    print("Next steps:")
    print("1. Test the exe on your machine:")
    print("   - Delete .license_cache")
    print("   - Run dist/OSRS_Bot.exe")
    print("   - Test license activation")
    print()
    print("2. Test on a clean machine (without Python)")
    print()
    print("3. Distribute OSRS_Bot.exe to customers")
    print()
    print("="*60)

except Exception as e:
    print()
    print("="*60)
    print("  ❌ Build Failed")
    print("="*60)
    print(f"Error: {e}")
    print()
    print("Common fixes:")
    print("  - Ensure PyInstaller is installed: pip install pyinstaller")
    print("  - Check that all imports are correct")
    print("  - Try running with --debug=all for more info")
    sys.exit(1)
