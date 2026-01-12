import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from osrsbot.app.calibration import Calibrator
from osrsbot.core.runner import ScriptRunner
from osrsbot.models.config import Config
from osrsbot.scripts.tests.comprehensive_state_bot_test import ComprehensiveTestBot
from osrsbot.scripts.tests.hp_tracker import HPTrackerBot
from osrsbot.scripts.tests.test_inventory_clicks import test_inventory_clicks
from osrsbot.scripts.bankstanding.bankstanding_flax import GrimyFlaxBot
from osrsbot.scripts.afk.nmz_afk import NMZAfkBot
from osrsbot.scripts.bosses.zulrah import ZulrahBot
from osrsbot.scripts.combat.basic_npc_killer import BasicNPCKiller
load_dotenv()

logger = logging.getLogger(__name__)


def get_valid_int(prompt: str, default: int) -> int:
    try:
        user_input = input(prompt).strip()
        if not user_input:
            return default
        value = int(user_input)
        if value <= 0:
            logger.warning(
                f"Invalid value {value}, must be positive. " f"Using default: {default}"
            )
            print(f"  ⚠ Must be positive. Using default: {default}")
            return default
        return value
    except ValueError as e:
        logger.warning(f"Invalid integer input: {e}. Using default: {default}")
        print(f"⚠️  Invalid number. Using default: {default}")
        return default


def main() -> None:
    # Determine log file location (next to .exe when frozen, or in cwd when dev)
    if getattr(sys, "frozen", False):
        log_dir = Path(sys.executable).parent
    else:
        log_dir = Path.cwd()

    log_file = log_dir / "osrs_bot_debug.log"

    # Configure logging with both console and file output
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),  # Console output
            logging.FileHandler(log_file, mode='w', encoding='utf-8')  # File output
        ]
    )

    logger.info(f"Debug log file: {log_file}")
    logger.info(f"Running as .exe: {getattr(sys, 'frozen', False)}")

    # Validate license before showing menu
    from osrsbot.services.license_service import LicenseService
    from osrsbot.ui.license_dialog import LicenseDialog
    from osrsbot.exceptions.license_exceptions import (
        LicenseExpiredException,
        LicenseInvalidException,
    )

    try:
        config = Config()
        license_config = config.get("license", default={})
        api_url = license_config.get("api_url", "http://localhost:8000")
        purchase_url = license_config.get("purchase_url", "https://yoursite.com/buy")
        cache_file = license_config.get("cache_file", ".license_cache")

        license_service = LicenseService(api_url=api_url, cache_file=cache_file)

        print("Validating license...")
        license_service.validate()

        status = license_service.get_license_status()
        if status["status"] == "active":
            hours = status.get("hours_remaining", 0)
            print(f"✓ License valid ({hours:.1f} hours remaining)\n")

    except LicenseInvalidException:
        print("\n" + "="*60)
        print("  OSRS Bot - License Activation Required")
        print("="*60)
        print("  No valid license found.")
        print(f"  Purchase a license at: {purchase_url}")
        print("="*60 + "\n")

        def activate_callback(key: str) -> bool:
            try:
                license_service.activate(key)
                return True
            except Exception as e:
                raise e

        dialog = LicenseDialog(
            on_activate=activate_callback,
            purchase_url=purchase_url
        )

        if not dialog.show():
            print("\n❌ License activation required to use this bot.")
            print(f"   Visit: {purchase_url}")
            sys.exit(1)

        # Validate again after activation
        license_service.validate()
        print("✓ License activated successfully!\n")

    except LicenseExpiredException as e:
        print("\n" + "="*60)
        print("  OSRS Bot - License Expired")
        print("="*60)
        print(f"  {e}")
        print(f"  Purchase a new license at: {purchase_url}")
        print("="*60 + "\n")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ License validation error: {e}")
        print("   Please check your internet connection or contact support.")
        sys.exit(1)

    try:
        print("\n" + "=" * 60)
        print("OSRS BOT - TASK SCRIPT RUNNER")
        print("=" * 60)
        print("\n1. Calibrate Colors & Coordinates")
        print("2. Comprehensive Test Bot (Tests All Framework Features)")
        print("3. Stats Tracker (HP/Prayer/Run/Spec OCR Comparison)")
        print("4. Template Click Test (Test All Template-Matched UI Elements)")
        print("5. Manual Cleaning Bankstander (Grimy Toadflax)")
        print("6. NMZ AFK Bot (1 HP Absorption Strategy)")
        print("7. Zulrah Boss Bot (Color-Coded Tile Marker Strategy)")
        print("8. Basic NPC Killer (Combat + Looting)")

        choice = input("\nSelect: ").strip()

        if choice == "1":
            logger.info("Starting calibration mode")
            try:
                config = Config()
                calibrator = Calibrator(config)
                title = input("Window title [default: RuneLite -]: ").strip()
                calibrator.start(title or "RuneLite - ")
            except FileNotFoundError as e:
                logger.error(f"Config file not found: {e}")
                print(f"❌ Config file error: {e}")
                sys.exit(1)
            except Exception as e:
                logger.error(f"Calibration failed: {e}", exc_info=True)
                print(f"❌ Calibration error: {e}")
                sys.exit(1)

        elif choice == "2":
            logger.info("Starting Comprehensive Test Bot")
            try:
                config = Config()
                window_title = config.get_window_title()
                runs = get_valid_int("Number of runs [default: 1]: ", default=1)

                print("\n🤖 Comprehensive Test Bot")
                print("This bot tests ALL framework features in sequence:")
                print("  1. Minimap Navigation (walking in all directions)")
                print("  2. Inventory Detection (pixel-based slot checking)")
                print("  3. Inventory Clicking (template-based slot clicking)")
                print("  4. Color Detection (smart NPC targeting)")
                print("  5. Template Matching (UI element detection)")
                print("  6. OCR (HP and stats reading)")
                print("  7. Combat Detection (10 NPC kills)")
                print("\n📝 Logs will be saved to: bot_debug.log")
                print("\nMake sure you have NPCs nearby for combat testing!")
                input("\nPress Enter to start...")

                runner = ScriptRunner(window_title)
                runner.run_script(ComprehensiveTestBot, runs=runs, bank_location="")
            except Exception as e:
                logger.error(f"Comprehensive Test Bot failed: {e}", exc_info=True)
                print(f"❌ Script error: {e}")
                sys.exit(1)

        elif choice == "3":
            logger.info("Starting Stats Tracker Bot")
            try:
                config = Config()
                window_title = config.get_window_title()

                print("\n📊 Stats Tracker Bot")
                print("Tracks HP, Prayer, Run Energy, and Special Attack")
                print("Compares Tesseract OCR vs Template Matching OCR")
                print("\nPress Ctrl+C to stop and see final results.")
                input("\nPress Enter to start...")

                runner = ScriptRunner(window_title)
                runner.run_script(HPTrackerBot, runs=1, bank_location="")
            except Exception as e:
                logger.error(f"HP Tracker Bot failed: {e}", exc_info=True)
                print(f"❌ Script error: {e}")
                sys.exit(1)

        elif choice == "4":
            logger.info("Starting Template Click Test")
            try:
                print("\n🎯 Template Click Test")
                print("This test will:")
                print("  1. Detect all UI grids (inventory, minimap, chat)")
                print("  2. Detect all UI buttons (logout, autoretal, clicks)")
                print("  3. Click all detected elements to verify accuracy")
                print("\nMake sure:")
                print("  • RuneLite is open and visible")
                print("  • Inventory tab is selected")
                print("  • Camera is not moving")
                print("\nNOTE: Only visible UI elements will be tested")
                input("\nPress Enter to start...")

                success = test_inventory_clicks()
                if success:
                    print("\n✅ Test completed successfully!")
                else:
                    print("\n❌ Test failed. Check logs for details.")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Template Click Test failed: {e}", exc_info=True)
                print(f"❌ Test error: {e}")
                sys.exit(1)

        elif choice == "5":
            logger.info("Starting Manual Cleaning Bankstander")
            try:
                config = Config()
                window_title = config.get_window_title()
                runs = get_valid_int("Number of cycles [default: 999]: ", default=999)

                print("\n🌿 Manual Cleaning Bankstander (Grimy Toadflax)")
                print("This bot will:")
                print("  1. Click banker to open bank (template matching)")
                print("  2. Withdraw 28 grimy toadflax (template matching)")
                print("  3. Click each inventory slot to clean herbs")
                print("  4. Deposit cleaned toadflax")
                print("  5. Repeat")
                print("\nMake sure:")
                print("  • You are standing near a banker")
                print("  • You have grimy toadflax in bank")
                print("  • Herblore 50+ to clean toadflax")
                print("\n📝 Logs will be saved to: bot_debug.log")
                print(f"🔄 Will run for {runs} cycles (Ctrl+C to stop)")
                input("\nPress Enter to start...")

                runner = ScriptRunner(window_title)
                runner.run_script(GrimyFlaxBot, runs=runs, bank_location="")
            except Exception as e:
                logger.error(f"Manual Cleaning Bankstander failed: {e}", exc_info=True)
                print(f"❌ Script error: {e}")
                sys.exit(1)

        elif choice == "6":
            logger.info("Starting NMZ AFK Bot")
            try:
                config = Config()
                window_title = config.get_window_title()
                runs = get_valid_int("Number of cycles [default: 999]: ", default=999)

                print("\n💤 NMZ AFK Bot (1 HP Absorption Strategy)")
                print("This bot will:")
                print("  1. Drink overload potion")
                print("  2. Lower HP to 1 with rock cake")
                print("  3. Drink 6 doses of absorption")
                print("  4. Monitor HP and use locator orb when HP >= 2")
                print("  5. Re-dose overload every 5 minutes")
                print("  6. Re-dose absorption every 5 minutes")
                print("\nMake sure:")
                print("  • You are INSIDE the NMZ dream (manual entry)")
                print("  • Inventory has: Overload, Absorption, Rock cake, Locator orb")
                print("  • Item templates are configured in config.json")
                print("\n📝 Logs will be saved to: bot_debug.log")
                print(f"🔄 Will run for {runs} cycles (Ctrl+C to stop)")
                input("\nPress Enter to start...")

                runner = ScriptRunner(window_title)
                runner.run_script(NMZAfkBot, runs=runs, bank_location="")
            except Exception as e:
                logger.error(f"NMZ AFK Bot failed: {e}", exc_info=True)
                print(f"❌ Script error: {e}")
                sys.exit(1)

        elif choice == "7":
            logger.info("Starting Zulrah Boss Bot")
            try:
                config = Config()
                window_title = config.get_window_title()
                runs = get_valid_int("Number of kills [default: 999]: ", default=999)

                print("\n🐍 Zulrah Boss Bot (Color-Coded Tile Marker Strategy)")
                print("This bot will:")
                print("  1. Identify rotation pattern (1-4) by observing first phases")
                print("  2. Navigate to safe spots using colored RuneLite tile markers")
                print("  3. Switch prayers automatically (Protect from Magic/Ranged/Melee)")
                print("  4. Switch gear between mage and range")
                print("  5. Attack Zulrah and handle snakelings")
                print("  6. Manage HP with food and prayer with potions")
                print("  7. Loot drops and repeat")
                print("\nPREREQUISITES:")
                print("  • RuneLite tile markers configured (see wiki for positions)")
                print("  • Zulrah config completed in config.json")
                print("  • Standing at Zul-Andra dock or inside instance")
                print("  • Inventory setup: Food, prayer pots, range/mage gear")
                print("\n⚠️  IMPORTANT: This bot requires proper tile marker setup!")
                print("   See docs/zulrah_setup.md for detailed instructions")
                print("\n📝 Logs will be saved to: bot_debug.log")
                print(f"🔄 Will attempt {runs} kills (Ctrl+C to stop)")
                input("\nPress Enter to start...")

                runner = ScriptRunner(window_title)
                runner.run_script(ZulrahBot, runs=runs, bank_location="")
            except Exception as e:
                logger.error(f"Zulrah Boss Bot failed: {e}", exc_info=True)
                print(f"❌ Script error: {e}")
                sys.exit(1)

        elif choice == "8":
            logger.info("Starting Basic NPC Killer")
            try:
                config = Config()
                window_title = config.get_window_title()
                runs = get_valid_int("Number of runs [default: 1]: ", default=1)

                print("\n⚔️  Basic NPC Killer")
                print("This bot will:")
                print("  1. Find and attack NPCs (using color detection)")
                print("  2. Wait for combat to finish")
                print("  3. Loot items (purple ground item highlights)")
                print("  4. Repeat until inventory is full")
                print("\nMake sure:")
                print("  • RuneLite NPC Indicators plugin is enabled")
                print("  • Target NPCs are highlighted (default: cyan #00FFFF)")
                print("  • Ground Items plugin highlights valuable loot in purple")
                print("  • You are in a safe combat area with NPCs nearby")
                print("\nOptional Config:")
                print("  • colors.npc_target = NPC highlight color (default: #00FFFF)")
                print("  • inventory_threshold = stop at X items (default: 27)")
                print("\n📝 Logs will be saved to: bot_debug.log")
                print(f"🔄 Will run for {runs} cycles or until inventory full")
                print("\n⚠️  Press 'q' at any time to stop the bot safely")
                input("\nPress Enter to start...")

                runner = ScriptRunner(window_title)
                runner.run_script(BasicNPCKiller, runs=runs, bank_location="")
            except Exception as e:
                logger.error(f"Basic NPC Killer failed: {e}", exc_info=True)
                print(f"❌ Script error: {e}")
                sys.exit(1)

        else:
            logger.info(f"Invalid choice: {choice}")
            print("❌ Invalid choice. Exiting...")
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("User interrupted execution")
        print("\n\n⚠️  Interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unexpected error in main: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Log the exception before the terminal closes
        logger.critical("FATAL ERROR - Bot crashed", exc_info=True)

        # Also print to console (in case file logging fails)
        print("\n" + "="*60)
        print("FATAL ERROR - Bot crashed!")
        print("="*60)
        print(f"Error: {e}")
        print("\nCheck osrs_bot_debug.log for full details")
        print("="*60)

        # Keep the terminal open so user can see the error
        input("\nPress Enter to exit...")
        sys.exit(1)
