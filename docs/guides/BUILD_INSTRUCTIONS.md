# Building OSRS Bot as an Executable

This guide shows you how to package your OSRS Bot into a standalone `.exe` file for distribution.

## Prerequisites

1. Python 3.10 or higher installed
2. All bot dependencies installed: `pip install -e .`
3. PyInstaller installed: `pip install pyinstaller`

## Quick Build

### Option 1: Using the build script (Recommended)

```bash
# Install PyInstaller if not already installed
pip install pyinstaller

# Run the build script
python build_exe.py
```

The executable will be created in `dist/OSRS_Bot.exe`

### Option 2: Manual PyInstaller command

```bash
pyinstaller launcher.py ^
    --name=OSRS_Bot ^
    --onefile ^
    --add-data="src/osrsbot;osrsbot" ^
    --add-data="src/osrsbot/config.json;osrsbot" ^
    --add-data="src/osrsbot/images;osrsbot/images" ^
    --hidden-import=osrsbot ^
    --clean ^
    --noconfirm
```

## Before Distribution

**CRITICAL: Update these URLs before building!**

1. Open `launcher.py`
2. Update line with `api_url = "..."` to your Railway deployment URL:
   ```python
   api_url = "https://osrs-automation-framework-production.up.railway.app"
   ```
3. Update line with `purchase_url = "..."` to your sales page:
   ```python
   purchase_url = "https://yourstore.com/buy-osrs-bot"
   ```
4. Rebuild the executable after making changes

## Customizing the Launcher

The `launcher.py` file is a simple entry point that:
1. Validates the license
2. Shows activation dialog if no license found
3. Exits if license invalid

To make it actually run your bot scripts, modify the `launcher.py` file after successful license validation:

```python
# After license validation succeeds, add:
from osrsbot.core.runner import ScriptRunner
from osrsbot.scripts.your_script import YourBot

runner = ScriptRunner("Old School RuneScape")
runner.run(YourBot)
```

## Testing the Executable

1. **Test on your development machine first:**
   ```bash
   dist/OSRS_Bot.exe
   ```

2. **Test on a clean machine without Python installed:**
   - Copy `OSRS_Bot.exe` to a different computer
   - Run it and verify license activation works
   - Ensure all features work properly

3. **Test with a real license key:**
   - Create a test license from your admin API
   - Activate it through the GUI
   - Verify the bot runs correctly

## Distribution Checklist

- [ ] Railway license server is deployed and running
- [ ] Production API URL is updated in `launcher.py`
- [ ] Purchase URL is updated in `launcher.py`
- [ ] Executable built with latest code
- [ ] Tested on clean machine without Python
- [ ] License activation tested end-to-end
- [ ] All bot features tested in executable
- [ ] Payment system configured (Gumroad/LemonSqueezy)
- [ ] License delivery system set up

## Advanced: Adding an Icon

1. Create or download a `.ico` file for your bot
2. Place it in the project root (e.g., `bot_icon.ico`)
3. Update `build_exe.py` line:
   ```python
   '--icon=bot_icon.ico',  # Changed from '--icon=NONE'
   ```
4. Rebuild

## Advanced: Including Multiple Scripts

If your bot has multiple scripts users can choose from, modify `launcher.py` to show a menu:

```python
def main():
    # ... license validation code ...

    print("Select a script to run:")
    print("1. NMZ AFK Bot")
    print("2. Woodcutting Bot")
    print("3. Mining Bot")

    choice = input("Enter choice (1-3): ")

    runner = ScriptRunner("Old School RuneScape")

    if choice == "1":
        from osrsbot.scripts.afk.nmz_afk import NMZBot
        runner.run(NMZBot)
    elif choice == "2":
        from osrsbot.scripts.woodcutting_bot import WoodcuttingBot
        runner.run(WoodcuttingBot)
    # etc...
```

## Reducing Executable Size

The default build includes all dependencies (~100-200MB). To reduce size:

1. **Exclude unused packages** - Add to `build_exe.py`:
   ```python
   '--exclude-module=matplotlib',
   '--exclude-module=pandas',
   ```

2. **Use UPX compression** (if available):
   ```python
   '--upx-dir=/path/to/upx',
   ```

3. **Don't include unnecessary data files**

## Troubleshooting

### "Failed to execute script launcher"

- Check that all `--hidden-import` directives are correct
- Ensure all data files are included with `--add-data`
- Run PyInstaller with `--debug=all` for verbose output

### "Module not found" errors

Add the missing module to `build_exe.py`:
```python
'--hidden-import=missing_module_name',
```

### Images/resources not loading

Ensure the path is correct in `--add-data`:
```python
f'--add-data={SOURCE_PATH};{DESTINATION_PATH}',
```

### License activation fails

- Verify the `api_url` in `launcher.py` is correct
- Check that the Railway server is running
- Test the API directly: `curl https://your-url.railway.app/health`

## Support

If you encounter issues:
1. Check the build log for errors
2. Test the Python script directly before building
3. Verify all dependencies are installed
4. Try building with `--onedir` instead of `--onefile` for easier debugging
