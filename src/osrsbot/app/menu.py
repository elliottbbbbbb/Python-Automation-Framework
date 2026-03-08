import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from osrsbot.app.calibration import Calibrator
from osrsbot.core.runner import ScriptRunner
from osrsbot.models.config import Config
from osrsbot.scripts.bankstanding.bankstanding_flax import GrimyFlaxBot
from osrsbot.scripts.afk.nmz_afk import NMZAfkBot
from osrsbot.scripts.skills.construction_training import ConstructionTrainingBot
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
            print(f"  Must be positive. Using default: {default}")
            return default
        return value
    except ValueError as e:
        logger.warning(f"Invalid integer input: {e}. Using default: {default}")
        print(f"  Invalid number. Using default: {default}")
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

    try:
        print("\n" + "=" * 60)
        print("OSRS BOT - TASK SCRIPT RUNNER")
        print("=" * 60)
        print("\n1. Calibrate Colors & Coordinates")
        print("2. Herb Cleaning Bankstander (Grimy Toadflax)")
        print("3. NMZ AFK Bot (1 HP Absorption Strategy)")
        print("4. Construction Training (Chair Building 1-40)")

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
                print(f"Config file error: {e}")
                sys.exit(1)
            except Exception as e:
                logger.error(f"Calibration failed: {e}", exc_info=True)
                print(f"Calibration error: {e}")
                sys.exit(1)

        elif choice == "2":
            logger.info("Starting Herb Cleaning Bankstander")
            try:
                config = Config()
                window_title = config.get_window_title()
                runs = get_valid_int("Number of cycles [default: 999]: ", default=999)

                print("\nHerb Cleaning Bankstander (Grimy Toadflax)")
                print("This bot will:")
                print("  1. Click banker to open bank (template matching)")
                print("  2. Withdraw 28 grimy toadflax (template matching)")
                print("  3. Click each inventory slot to clean herbs")
                print("  4. Deposit cleaned toadflax")
                print("  5. Repeat")
                print("\nMake sure:")
                print("  - You are standing near a banker")
                print("  - You have grimy toadflax in bank")
                print("  - Herblore 50+ to clean toadflax")
                print(f"\nWill run for {runs} cycles (Ctrl+C to stop)")
                input("\nPress Enter to start...")

                runner = ScriptRunner(window_title)
                runner.run_script(GrimyFlaxBot, runs=runs, bank_location="")
            except Exception as e:
                logger.error(f"Herb Cleaning Bankstander failed: {e}", exc_info=True)
                print(f"Script error: {e}")
                sys.exit(1)

        elif choice == "3":
            logger.info("Starting NMZ AFK Bot")
            try:
                config = Config()
                window_title = config.get_window_title()
                runs = get_valid_int("Number of cycles [default: 999]: ", default=999)

                print("\nNMZ AFK Bot (1 HP Absorption Strategy)")
                print("This bot will:")
                print("  1. Drink overload potion")
                print("  2. Lower HP to 1 with rock cake")
                print("  3. Drink 6 doses of absorption")
                print("  4. Monitor HP and use locator orb when HP >= 2")
                print("  5. Re-dose overload every 5 minutes")
                print("  6. Re-dose absorption every 5 minutes")
                print("\nMake sure:")
                print("  - You are INSIDE the NMZ dream (manual entry)")
                print("  - Inventory has: Overload, Absorption, Rock cake, Locator orb")
                print("  - Item templates are configured in config.json")
                print(f"\nWill run for {runs} cycles (Ctrl+C to stop)")
                input("\nPress Enter to start...")

                runner = ScriptRunner(window_title)
                runner.run_script(NMZAfkBot, runs=runs, bank_location="")
            except Exception as e:
                logger.error(f"NMZ AFK Bot failed: {e}", exc_info=True)
                print(f"Script error: {e}")
                sys.exit(1)

        elif choice == "4":
            logger.info("Starting Construction Training Bot")
            try:
                config = Config()
                window_title = config.get_window_title()
                runs = get_valid_int("Number of cycles [default: 999]: ", default=999)

                print("\nConstruction Training Bot (Chair Building)")
                print("This bot will:")
                print("  1. Teleport to house using scroll")
                print("  2. Exit house to Rimmington")
                print("  3. Exchange noted planks with Phials NPC (press 3)")
                print("  4. Re-enter house")
                print("  5. Build highest level chair available (rocking > wooden > crude)")
                print("  6. Remove chair and repeat")
                print("\nMake sure:")
                print("  - House set to Rimmington")
                print("  - Chair hotspot built in parlour")
                print("  - RuneLite NPC Indicators: Phials highlighted (#FFD700)")
                print("  - All template images created")
                print("\nInventory Required:")
                print("  - Teleport to house scrolls (10-50)")
                print("  - Noted planks (100-1000)")
                print("  - Iron nails (100-1000)")
                print("  - Coins (10-100k for exchange fees)")
                print("  - Hammer and Saw")
                print(f"\nWill run for {runs} cycles (Ctrl+C to stop)")
                input("\nPress Enter to start...")

                runner = ScriptRunner(window_title)
                runner.run_script(ConstructionTrainingBot, runs=runs, bank_location="")
            except Exception as e:
                logger.error(f"Construction Training Bot failed: {e}", exc_info=True)
                print(f"Script error: {e}")
                sys.exit(1)

        else:
            logger.info(f"Invalid choice: {choice}")
            print("Invalid choice. Exiting...")
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("User interrupted execution")
        print("\n\nInterrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unexpected error in main: {e}", exc_info=True)
        print(f"\nFatal error: {e}")
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
