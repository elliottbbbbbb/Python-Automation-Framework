import logging
import sys

from osrsbot.models.config import Config
from osrsbot.app.calibration import Calibrator
from osrsbot.core.runner import ScriptRunner
from osrsbot.scripts.legacy.green_dragons import GreenDragonsBot
from osrsbot.scripts.legacy.guns import guns_script
from osrsbot.scripts.legacy.test import test_script
from osrsbot.scripts.test_state_machine_bot import ComprehensiveTestBot
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
        print("2. Run Green Dragons Script")
        print("3. Run Guns Script (Pickpocketing)")
        print("4. Test Script")
        print("5. Test Template Matching - Click All 28 Inventory Slots")
        print("6. Comprehensive Test Bot (Tests All Framework Features)")

        choice = input("\nSelect: ").strip()

        if choice == "1":
            # Calibration
            logger.info("Starting calibration mode")
            try:
                config = Config()
                calibrator = Calibrator(config)
                # TODO: Remove this prompt - users should add window title to config.json
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
            # Green Dragons
            logger.info("Starting Green Dragons script")
            try:
                config = Config()
                window_title = config.get_window_title()
                runs = get_valid_int(
                    "Number of runs [default: 10]: ", default=10)
                bank = input("Bank location [varrock]: ").strip() or "varrock"

                runner = ScriptRunner(window_title)
                runner.run_script(
                    GreenDragonsBot,
                    bank_location=bank,
                    runs=runs)
            except Exception as e:
                logger.error(
                    f"Green Dragons script failed: {e}",
                    exc_info=True)
                print(f"❌ Script error: {e}")
                sys.exit(1)

        elif choice == "3":
            # Guns
            logger.info("Starting Guns script")
            try:
                config = Config()
                window_title = config.get_window_title()
                runs = get_valid_int(
                    "Number of runs [default: 10]: ", default=10)
                bank = input("Bank location [GE]: ").strip() or "GE"

                runner = ScriptRunner(window_title)
                runner.run_script(guns_script, bank_location=bank, runs=runs)
            except Exception as e:
                logger.error(f"Guns script failed: {e}", exc_info=True)
                print(f"❌ Script error: {e}")
                sys.exit(1)

        elif choice == "4":
            # Test Script
            logger.info("Starting Test script")
            try:
                config = Config()
                window_title = config.get_window_title()
                runs = get_valid_int(
                    "Number of runs [default: 10]: ", default=10)
                bank = input("Bank location [GE]: ").strip() or "GE"

                runner = ScriptRunner(window_title)
                runner.run_script(test_script, bank_location=bank, runs=runs)
            except Exception as e:
                logger.error(f"Test script failed: {e}", exc_info=True)
                print(f"❌ Script error: {e}")
                sys.exit(1)

        elif choice == "5":
            # Template Matching Test
            logger.info("Starting template matching test")
            try:
                config = Config()
                window_title = config.get_window_title()
                runs = get_valid_int(
                    "Number of runs [default: 1]: ", default=1)

                runner = ScriptRunner(window_title)
                runner.run_script(test_script, bank_location="", runs=runs)
            except Exception as e:
                logger.error(f"Template matching test failed: {e}", exc_info=True)
                print(f"❌ Script error: {e}")
                sys.exit(1)

        elif choice == "6":
            # State Machine Test Bot
            logger.info("Starting State Machine Test Bot")
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
                    debug_ui=True  # Enable debug UI
                )
                bot.run(bank_location="", runs=runs)
            except Exception as e:
                logger.error(f"Comprehensive Test Bot failed: {e}", exc_info=True)
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
    main()
