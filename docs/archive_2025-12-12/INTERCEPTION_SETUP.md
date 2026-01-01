# Interception Driver Setup Guide

This guide explains how to set up and use the Interception driver for kernel-level mouse input in the OSRS bot.

## What is Interception?

The Interception driver provides **kernel-level mouse and keyboard input** that is indistinguishable from real hardware input. This makes it much harder for anti-cheat systems to detect automation.

## Installation Steps

### 1. Install Python Package

```bash
pip install python-dotenv interception-python
```

Or reinstall all dependencies:

```bash
pip install -e .
```

### 2. Install Interception Driver

The Interception driver must be installed separately (requires admin rights):

1. **Download the Interception driver installer** from:
   - Official: https://github.com/oblitum/Interception
   - Python wrapper docs: https://github.com/kennyhml/pyinterception

2. **Run the installer as Administrator**

3. **Reboot your system** (required for driver to load)

### 3. Configure Environment Variable

The `.env` file has been created for you with `USE_INTERCEPTION=1` already set.

To verify or modify:

```bash
# Open .env file and ensure:
USE_INTERCEPTION=1
```

## Usage

### Running with Interception

Simply run your bot normally - the `.env` file will be loaded automatically:

```bash
python -m osrsbot.app.menu
```

You should see in the logs:

```
Initializing InterceptionMouseService (kernel-level)
InterceptionMouseService initialized successfully
```

### Switching Back to Standard Mouse

Edit `.env` and change:

```bash
USE_INTERCEPTION=0
```

Or delete/comment out the line entirely.

## Verification

To verify Interception is working:

1. Run the Comprehensive Test Bot (option 2 in menu)
2. Check the test output for "TEST 3/9: INTERCEPTION MOUSE"
3. If successful, you'll see:
   ```
   ✓ Interception mouse detected and enabled
   → Driver context initialized: True
   → Mouse device ID: [device_id]
   ✓ Interception mouse accuracy: EXCELLENT
   ```

## Troubleshooting

### ImportError: No module named 'interception'

**Solution:** Install the package:
```bash
pip install interception-python
```

### RuntimeError: Failed to detect mouse device

**Causes:**
- Driver not installed
- System not rebooted after driver installation
- Running without admin rights (sometimes required)

**Solution:**
1. Verify driver is installed
2. Reboot system
3. Try running as Administrator

### Falls back to MouseService

If you see this warning:
```
InterceptionMouseService not available: [error]
Falling back to MouseService
```

The bot will continue to work with standard mouse control (pyautogui).

## Features

### Supported by Interception

✅ Mouse movement (linear, curved, Bezier)
✅ Mouse clicks (left, right, middle)
✅ Click variance and humanization
✅ Overshoot and correction
✅ All movement styles
✅ Hardware-level input

### Technical Details

- **Type:** Kernel-level input driver
- **Detection:** Virtually undetectable (same as hardware)
- **Performance:** Identical to standard mouse
- **Compatibility:** Windows only
- **Requirements:** Admin rights for installation

## Security Notes

⚠️ **Important:**
- The Interception driver operates at kernel level
- Only install from trusted sources
- Requires system reboot
- May conflict with some anti-cheat software (Vanguard, some versions of EAC)

## Anti-Cheat Compatibility

| Anti-Cheat | Status |
|------------|--------|
| RuneLite / OSRS | ✅ Compatible |
| Vanguard (Valorant) | ❌ May prevent boot |
| EasyAntiCheat (some versions) | ⚠️ Varies |
| BattlEye | ⚠️ May be detected |

If you play games with aggressive anti-cheat, you may want to keep `USE_INTERCEPTION=0` and only enable it when botting.

## Advantages Over Standard Mouse

| Feature | Standard (pyautogui) | Interception |
|---------|---------------------|--------------|
| Detection level | Application | Kernel |
| Hardware signature | ❌ Missing | ✅ Present |
| Input timestamps | ⚠️ Synthetic | ✅ Hardware-like |
| Performance | Fast | Fast |
| Setup complexity | Easy | Moderate |

## References

- [Interception Driver (GitHub)](https://github.com/oblitum/Interception)
- [pyinterception (Python wrapper)](https://github.com/kennyhml/pyinterception)
- [interception-python on PyPI](https://pypi.org/project/interception-python/)
