from osrsbot.config import Config
from osrsbot.calibration import Calibrator
from osrsbot.runner import ScriptRunner
from osrsbot.scripts.green_dragons import green_dragons_script
from osrsbot.scripts.guns import guns_script
from osrsbot.scripts.test import test

def main() -> None:
    print("\n" + "="*60)
    print("OSRS BOT - TASK SCRIPT RUNNER")
    print("="*60)
    print("\n1. Calibrate Colors & Coordinates")
    print("2. Run Green Dragons Script")
    print("3. Run Guns Script (Pickpocketing)")
    print("4. Test Script")
    print("5. Dev")
    
    choice = input("\nSelect: ").strip()
    
    if choice == "1":
        # Calibration
        config = Config()
        calibrator = Calibrator(config)
        title = input("Window title [default: RuneLite -]: ").strip()
     
        calibrator.start(title or "RuneLite - ")
    
    elif choice == "2":
        # Green Dragons
        window_title = input("Window title: ").strip()
        runs = int(input("Number of runs: ") or "10")
        bank = input("Bank location [varrock]: ").strip() or "varrock"
        
        runner = ScriptRunner(window_title)
        runner.run_script(green_dragons_script, bank_location=bank, runs=runs)
    
    elif choice == "3":
        # Guns
        window_title = input("Window title: ").strip()
        runs = int(input("Number of runs: ") or "10")
        bank = input("Bank location [GE]: ").strip() or "GE"
        
        runner = ScriptRunner(window_title)
        runner.run_script(guns_script, bank_location=bank, runs=runs)
    
    elif choice == "4":
        window_title = input("Window title: ").strip()
        runs = int(input("Number of runs: ") or "10")
        bank = input("Bank location [GE]: ").strip() or "GE"

        runner = ScriptRunner(window_title)
        runner.run_script(test, bank_location=bank, runs=runs)

    elif choice == "5":
        window_title = "RuneLite - 61grouphunt" 
        runs = 500
        bank = "GE"

        runner = ScriptRunner(window_title)
        runner.run_script(test, bank_location=bank, runs=runs)

    else:
        print("Exiting...")

if __name__ == "__main__":
    main()