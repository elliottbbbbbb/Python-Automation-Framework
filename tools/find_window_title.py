"""
Simple script to find the exact RuneLite window title.
Run this while RuneLite is open to see the correct title.
"""

import platform

if platform.system() == "Windows":
    try:
        import pygetwindow as gw

        print("=== All Window Titles ===\n")
        all_windows = gw.getAllTitles()

        runelite_windows = []
        for title in all_windows:
            if title and "RuneLite" in title:
                runelite_windows.append(title)
                print(f"✅ Found RuneLite window: '{title}'")

        if not runelite_windows:
            print("❌ No RuneLite windows found!")
            print("\nAll windows:")
            for title in all_windows:
                if title:  # Only show non-empty titles
                    print(f"  - {title}")
        else:
            print(f"\n📋 Copy one of the above titles to your config.json")
            print(f"   Example: \"window_title\": \"{runelite_windows[0]}\"")

    except ImportError:
        print("pygetwindow not installed. Trying PyWinCtl...")
        try:
            from pywinctl import getAllTitles

            print("=== All Window Titles ===\n")
            all_windows = getAllTitles()

            runelite_windows = []
            for title in all_windows:
                if title and "RuneLite" in title:
                    runelite_windows.append(title)
                    print(f"✅ Found RuneLite window: '{title}'")

            if not runelite_windows:
                print("❌ No RuneLite windows found!")
                print("\nAll windows:")
                for title in all_windows[:50]:  # Limit output
                    if title:
                        print(f"  - {title}")
            else:
                print(f"\n📋 Copy one of the above titles to your config.json")
                print(f"   Example: \"window_title\": \"{runelite_windows[0]}\"")

        except ImportError:
            print("❌ Neither pygetwindow nor PyWinCtl available")
            print("Install with: pip install PyWinCtl")

else:
    print("This script is for Windows only")
    print("On Mac/Linux, window management works differently")
