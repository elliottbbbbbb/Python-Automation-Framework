import logging
import sys
from osrsbot.config import Config
from osrsbot.calibration import Calibrator
from osrsbot.runner import ScriptRunner
from osrsbot.scripts.green_dragons import green_dragons_script
from osrsbot.scripts.guns import guns_script
from osrsbot.scripts.test import test
logger = logging.getLogger(__name__)


def get_valid_int(prompt: str, default: int) -> int:
    """Get valid integer input from user with default fallback."""
    try:
        user_input = input(prompt).strip()
        if not user_input:
            return default
        value = int(user_input)
        if value <= 0:
            logger.warning(
                f"Invalid value {value}, must be positive. "
                f"Using default: {default}")
            print(f"âš ï¸  Must be positive. Using default: {default}")
            return default
        return value
    except ValueError as e:
        logger.warning(f"Invalid integer input: {e}. Using default: {default}")
        print(f"âš ï¸  Invalid number. Using default: {default}")
        return default


def get_window_title(prompt: str, default: str = "") -> str:
    """Get window title from user with validation."""
    title = input(prompt).strip()
    if not title and default:
        return default
    if not title:
        logger.error("Window title cannot be empty")
        print("âŒ Window title is required!")
        sys.exit(1)
    return title


def main() -> None:
    """Main entry point for OSRS Bot."""
    # Set up basic logging
    logging.basicConfig(
        level=logging.DEBUG,
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
        print("5. Dev")

        choice = input("\nSelect: ").strip()

        if choice == "1":
            # Calibration
            logger.info("Starting calibration mode")
            try:
                config = Config()
                calibrator = Calibrator(config)
                title = input("Window title [default: RuneLite -]: ").strip()
                calibrator.start(title or "RuneLite - ")
            except FileNotFoundError as e:
                logger.error(f"Config file not found: {e}")
                print(f"âŒ Config file error: {e}")
                sys.exit(1)
            except Exception as e:
                logger.error(f"Calibration failed: {e}", exc_info=True)
                print(f"âŒ Calibration error: {e}")
                sys.exit(1)

        elif choice == "2":
            # Green Dragons
            logger.info("Starting Green Dragons script")
            try:
                window_title = get_window_title("Window title: ")
                runs = get_valid_int(
                    "Number of runs [default: 10]: ", default=10)
                bank = input("Bank location [varrock]: ").strip() or "varrock"

                runner = ScriptRunner(window_title)
                runner.run_script(
                    green_dragons_script,
                    bank_location=bank,
                    runs=runs)
            except Exception as e:
                logger.error(
                    f"Green Dragons script failed: {e}",
                    exc_info=True)
                print(f"âŒ Script error: {e}")
                sys.exit(1)

        elif choice == "3":
            # Guns
            logger.info("Starting Guns script")
            try:
                window_title = get_window_title("Window title: ")
                runs = get_valid_int(
                    "Number of runs [default: 10]: ", default=10)
                bank = input("Bank location [GE]: ").strip() or "GE"

                runner = ScriptRunner(window_title)
                runner.run_script(guns_script, bank_location=bank, runs=runs)
            except Exception as e:
                logger.error(f"Guns script failed: {e}", exc_info=True)
                print(f"âŒ Script error: {e}")
                sys.exit(1)

        elif choice == "4":
            # Test Script
            logger.info("Starting Test script")
            try:
                window_title = get_window_title("Window title: ")
                runs = get_valid_int(
                    "Number of runs [default: 10]: ", default=10)
                bank = input("Bank location [GE]: ").strip() or "GE"

                runner = ScriptRunner(window_title)
                runner.run_script(test, bank_location=bank, runs=runs)
            except Exception as e:
                logger.error(f"Test script failed: {e}", exc_info=True)
                print(f"âŒ Script error: {e}")
                sys.exit(1)

        elif choice == "5":
            # Dev Mode
            logger.info("Starting Dev mode")
            try:
                window_title = "RuneLite - 61grouphunt"
                runs = 500
                bank = "GE"

                runner = ScriptRunner(window_title)
                runner.run_script(test, bank_location=bank, runs=runs)
            except Exception as e:
                logger.error(f"Dev mode failed: {e}", exc_info=True)
                print(f"âŒ Script error: {e}")
                sys.exit(1)

        else:
            logger.info(f"Invalid choice: {choice}")
            print("âŒ Invalid choice. Exiting...")
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("User interrupted execution")
        print("\n\nâš ï¸  Interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unexpected error in main: {e}", exc_info=True)
        print(f"\nâŒ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
