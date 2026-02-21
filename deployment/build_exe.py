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

# Resolve paths relative to this script so the build works on any machine
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
OSRSBOT_DIR = SRC_DIR / "osrsbot"
ENTRY_POINT = OSRSBOT_DIR / "app" / "menu.py"

print("=" * 60)
print("  OSRS Bot - Executable Builder")
print("=" * 60)
print()
print(f"Project root: {PROJECT_ROOT}")
print(f"Entry point:  {ENTRY_POINT}")
print()

if not ENTRY_POINT.exists():
    print(f"Error: Entry point not found: {ENTRY_POINT}")
    sys.exit(1)

# On Windows PyInstaller uses ';' as the separator in --add-data
SEP = ";" if sys.platform == "win32" else ":"

pyinstaller_args = [
    str(ENTRY_POINT),
    '--name=OSRS_Bot',
    '--onedir',
    '--icon=NONE',

    # Bundle only the images directory - Python source is compiled by PyInstaller separately
    f'--add-data={OSRSBOT_DIR / "images"}{SEP}osrsbot/images',

    # Add src/ to path so PyInstaller can locate the osrsbot package for analysis
    f'--paths={SRC_DIR}',

    # Keep the spec file in the deployment folder
    f'--specpath={Path(__file__).parent}',

    # --- Package roots ---
    '--hidden-import=osrsbot',
    '--hidden-import=osrsbot.app',
    '--hidden-import=osrsbot.commands',
    '--hidden-import=osrsbot.core',
    '--hidden-import=osrsbot.exceptions',
    '--hidden-import=osrsbot.models',
    '--hidden-import=osrsbot.queries',
    '--hidden-import=osrsbot.scrapers',
    '--hidden-import=osrsbot.services',
    '--hidden-import=osrsbot.ui',
    '--hidden-import=osrsbot.utils',
    '--hidden-import=osrsbot.scripts',
    '--hidden-import=osrsbot.scripts.afk',
    '--hidden-import=osrsbot.scripts.bankstanding',
    '--hidden-import=osrsbot.scripts.bosses',
    '--hidden-import=osrsbot.scripts.combat',
    '--hidden-import=osrsbot.scripts.skills',
    '--hidden-import=osrsbot.scripts.tests',

    # --- App ---
    '--hidden-import=osrsbot.app.calibration',
    '--hidden-import=osrsbot.app.debug_ui',
    '--hidden-import=osrsbot.app.menu',

    # --- Commands ---
    '--hidden-import=osrsbot.commands.bank_actions',
    '--hidden-import=osrsbot.commands.combat_actions',
    '--hidden-import=osrsbot.commands.game_actions',
    '--hidden-import=osrsbot.commands.inventory_actions',

    # --- Constants ---
    '--hidden-import=osrsbot.constants',

    # --- Core ---
    '--hidden-import=osrsbot.core.anti_afk',
    '--hidden-import=osrsbot.core.base_bankstander',
    '--hidden-import=osrsbot.core.base_bot',
    '--hidden-import=osrsbot.core.game_interface',
    '--hidden-import=osrsbot.core.runner',
    '--hidden-import=osrsbot.core.state_helpers',
    '--hidden-import=osrsbot.core.state_machine_bot',
    '--hidden-import=osrsbot.core.state_types',

    # --- Exceptions ---
    '--hidden-import=osrsbot.exceptions.license_exceptions',

    # --- Models ---
    '--hidden-import=osrsbot.models.config',
    '--hidden-import=osrsbot.models.config_defaults',
    '--hidden-import=osrsbot.models.ui_elements',

    # --- Queries ---
    '--hidden-import=osrsbot.queries.bank_queries',
    '--hidden-import=osrsbot.queries.combat_queries',
    '--hidden-import=osrsbot.queries.game_queries',
    '--hidden-import=osrsbot.queries.inventory_queries',
    '--hidden-import=osrsbot.queries.login_queries',
    '--hidden-import=osrsbot.queries.stat_queries',

    # --- Scrapers ---
    '--hidden-import=osrsbot.scrapers.wiki_item_scraper',

    # --- Scripts - AFK ---
    '--hidden-import=osrsbot.scripts.afk.nmz_afk',

    # --- Scripts - Bankstanding ---
    '--hidden-import=osrsbot.scripts.bankstanding.bankstander_example',
    '--hidden-import=osrsbot.scripts.bankstanding.bankstanding_flax',
    '--hidden-import=osrsbot.scripts.bankstanding.bankstanding_fletching',
    '--hidden-import=osrsbot.scripts.bankstanding.bankstanding_herblore',
    '--hidden-import=osrsbot.scripts.bankstanding.fletching_items',
    '--hidden-import=osrsbot.scripts.bankstanding.herblore_items',

    # --- Scripts - Bosses ---
    '--hidden-import=osrsbot.scripts.bosses.vorkath_bot',
    '--hidden-import=osrsbot.scripts.bosses.zulrah',
    '--hidden-import=osrsbot.scripts.bosses.zulrah_combat_manager',
    '--hidden-import=osrsbot.scripts.bosses.zulrah_detector',
    '--hidden-import=osrsbot.scripts.bosses.zulrah_navigator',

    # --- Scripts - Combat ---
    '--hidden-import=osrsbot.scripts.combat.basic_npc_killer',
    '--hidden-import=osrsbot.scripts.combat.chinning_monkeys',
    '--hidden-import=osrsbot.scripts.combat.green_dragons_state',
    '--hidden-import=osrsbot.scripts.combat.sand_crabs_combat',

    # --- Scripts - Skills ---
    '--hidden-import=osrsbot.scripts.skills.construction_training',
    '--hidden-import=osrsbot.scripts.skills.mining_bot',

    # --- Scripts - Tests ---
    '--hidden-import=osrsbot.scripts.tests.comprehensive_state_bot_test',
    '--hidden-import=osrsbot.scripts.tests.hp_tracker',
    '--hidden-import=osrsbot.scripts.tests.stats_reader_test',
    '--hidden-import=osrsbot.scripts.tests.stats_test',
    '--hidden-import=osrsbot.scripts.tests.test_inventory_clicks',

    # --- Services ---
    '--hidden-import=osrsbot.services.anti_ban_service',
    '--hidden-import=osrsbot.services.bezier_utils',
    '--hidden-import=osrsbot.services.click_target_tracker',
    '--hidden-import=osrsbot.services.coordinate_ocr_service',
    '--hidden-import=osrsbot.services.feature_match_service',
    '--hidden-import=osrsbot.services.hardware_fingerprint',
    '--hidden-import=osrsbot.services.item_detection_service',
    '--hidden-import=osrsbot.services.keyboard_service',
    '--hidden-import=osrsbot.services.license_service',
    '--hidden-import=osrsbot.services.loot_detection_service',
    '--hidden-import=osrsbot.services.mouse_service',
    '--hidden-import=osrsbot.services.screen_service',
    '--hidden-import=osrsbot.services.template_match_service',
    '--hidden-import=osrsbot.services.template_ocr_service',
    '--hidden-import=osrsbot.services.ui_manager_service',
    '--hidden-import=osrsbot.services.live_view_service',
    '--hidden-import=osrsbot.services.walker_service',
    '--hidden-import=osrsbot.services.win32_mouse_service',
    '--hidden-import=osrsbot.services.wom_service',

    # --- UI ---
    '--hidden-import=osrsbot.ui.license_dialog',

    # --- Utils ---
    '--hidden-import=osrsbot.utils.color_helpers',
    '--hidden-import=osrsbot.utils.coordinate_helpers',
    '--hidden-import=osrsbot.utils.path_helpers',
    '--hidden-import=osrsbot.utils.template_helpers',
    '--hidden-import=osrsbot.utils.timing_helpers',

    # --- Third-party ---
    '--hidden-import=requests',
    '--hidden-import=cv2',
    '--hidden-import=numpy',
    '--hidden-import=PIL',
    '--hidden-import=pyautogui',
    '--hidden-import=pytesseract',
    '--hidden-import=tkinter',
    '--hidden-import=win32api',
    '--hidden-import=win32con',
    '--hidden-import=win32gui',
    '--hidden-import=pynput',
    '--hidden-import=dotenv',

    # Build options
    '--clean',
    '--noconfirm',
]

print("Building executable...")
print("This may take several minutes...")
print()

try:
    os.chdir(PROJECT_ROOT)
    PyInstaller.__main__.run(pyinstaller_args)

    print()
    print("=" * 60)
    print("  Build Complete!")
    print("=" * 60)
    print()
    print(f"Executable: {PROJECT_ROOT / 'dist' / 'OSRS_Bot' / 'OSRS_Bot.exe'}")
    print()

except Exception as e:
    print()
    print("=" * 60)
    print("  Build Failed")
    print("=" * 60)
    print(f"Error: {e}")
    print()
    print("Common fixes:")
    print("  - Ensure PyInstaller is installed: pip install pyinstaller")
    print("  - Check that all imports resolve correctly")
    print("  - Try running with --debug=all for more info")
    sys.exit(1)
