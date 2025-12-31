import logging
import sys
from dotenv import load_dotenv

load_dotenv()

from osrsbot.models.config import Config
from osrsbot.app.calibration import Calibrator
from osrsbot.core.runner import ScriptRunner
from osrsbot.scripts.comprehensive_state_bot_test import ComprehensiveTestBot
from osrsbot.scripts.hp_tracker import HPTrackerBot
from osrsbot.scripts.test_inventory_clicks import test_inventory_clicks
logger = logging.getLogger(__name__)


def get_valid_int(prompt: str, default: int) -> int:
    try:
        user_input = input(prompt).strip()
        if not user_input:
            return default
        value = int(user_input)
        if value <= 0:
            logger.warning(
                f"Invalid value {value}, must be positive. "
                f"Using default: {default}")
            print(f"  ⚠ Must be positive. Using default: {default}")
            return default
        return value
    except ValueError as e:
        logger.warning(f"Invalid integer input: {e}. Using default: {default}")
        print(f"⚠️  Invalid number. Using default: {default}")
        return default


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        print("\n" + "=" * 60)
        print("OSRS BOT - TASK SCRIPT RUNNER")
        print("=" * 60)
        print("\n1. Calibrate Colors & Coordinates")
        print("2. Comprehensive Test Bot (Tests All Framework Features)")
        print("3. Stats Tracker (HP/Prayer/Run/Spec OCR Comparison)")
        print("4. Template Click Test (Test All Template-Matched UI Elements)")

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
                runs = get_valid_int(
                    "Number of runs [default: 1]: ", default=1)

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

                # Manually instantiate bot with debug UI enabled
                bot = ComprehensiveTestBot(
                    interface=runner.interface,
                    state=runner.state,
                    actions=runner.actions,
                    config=runner.config,
                    debug_ui=False # Enable debug UI
                )
                bot.run(bank_location="", runs=runs)
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

                # Instantiate HP Tracker bot
                bot = HPTrackerBot(
                    interface=runner.interface,
                    state=runner.state,
                    actions=runner.actions,
                    config=runner.config,
                    debug_ui=False
                )
                bot.run(bank_location="", runs=1)
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
    main()
