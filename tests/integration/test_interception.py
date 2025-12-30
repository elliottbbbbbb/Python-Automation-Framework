"""
Diagnostic script to test Interception driver setup.
Run this to diagnose why Interception isn't working.
"""
import sys
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

print("=" * 60)
print("INTERCEPTION DRIVER DIAGNOSTIC")
print("=" * 60)

# Test 1: Check environment variable
print("\n[TEST 1] Environment Variable Check")
use_interception = os.getenv("USE_INTERCEPTION", "")
print(f"  USE_INTERCEPTION = '{use_interception}'")
print(f"  Will use interception: {use_interception.lower() in ('1', 'true', 'yes')}")

# Test 2: Check if interception-python is installed
print("\n[TEST 2] Python Package Check")
try:
    import interception
    print("  OK interception-python package is installed")
    print(f"  Package location: {interception.__file__}")
    print(f"  Package version: {interception.__version__ if hasattr(interception, '__version__') else 'unknown'}")
except ImportError as e:
    print(f"  X interception-python package NOT installed")
    print(f"  Error: {e}")
    print("\n  FIX: Run 'pip install interception-python'")
    sys.exit(1)

# Test 3: Try to initialize the driver
print("\n[TEST 3] Driver Initialization (New API)")
try:
    from interception import Interception
    print("  -> Creating Interception context...")
    context = Interception()

    if context:
        print("  OK Interception context created successfully")
        print(f"  Mouse device: {context.mouse}")
        print(f"  Keyboard device: {context.keyboard}")
    else:
        print("  X Failed to create interception context (returned None)")
        print("\n  POSSIBLE CAUSES:")
        print("    1. Interception driver not installed")
        print("    2. System not rebooted after driver installation")
        print("    3. Need to run as Administrator")
        sys.exit(1)

except Exception as e:
    print(f"  X Failed to initialize interception driver")
    print(f"  Error: {e}")
    print("\n  POSSIBLE CAUSES:")
    print("    1. Interception driver not installed")
    print("    2. System not rebooted after driver installation <<< MOST LIKELY")
    print("    3. Driver installation failed")
    print("    4. Need to run as Administrator")
    print("\n  FIX:")
    print("    1. Download Interception installer from:")
    print("       https://github.com/oblitum/Interception/releases")
    print("    2. Run 'install-interception.exe /install' as Administrator")
    print("    3. **REBOOT YOUR SYSTEM** (critical step!)")
    sys.exit(1)

# Test 4: Try to move mouse
print("\n[TEST 4] Test Mouse Movement")
try:
    from interception import move_to
    import pyautogui

    current_x, current_y = pyautogui.position()
    print(f"  -> Current position: ({current_x}, {current_y})")

    test_x = current_x + 50
    test_y = current_y

    print(f"  -> Moving to ({test_x}, {test_y}) [50 pixels right]...")
    move_to(test_x, test_y, blocking=True)

    new_x, new_y = pyautogui.position()
    print(f"  -> New position: ({new_x}, {new_y})")

    error = abs(new_x - test_x) + abs(new_y - test_y)
    if error <= 5:
        print("  OK Mouse movement successful (<=5px error)")
    else:
        print(f"  ! Mouse moved with {error}px error")

    # Move back
    print(f"  -> Moving back to ({current_x}, {current_y})...")
    move_to(current_x, current_y, blocking=True)
    print("  OK Movement test complete")

except Exception as e:
    print(f"  X Failed to move mouse")
    print(f"  Error: {e}")
    sys.exit(1)

# Test 5: Try to click
print("\n[TEST 5] Test Mouse Click")
try:
    from interception import click

    print("  -> Sending left click...")
    click(button="left")
    print("  OK Click sent successfully")

except Exception as e:
    print(f"  X Failed to click")
    print(f"  Error: {e}")
    sys.exit(1)

# All tests passed
print("\n" + "=" * 60)
print("ALL TESTS PASSED!")
print("=" * 60)
print("\nInterception driver is working correctly.")
print("Your bot will now use kernel-level mouse input!")
print("=" * 60)
