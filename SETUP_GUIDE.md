# OSRS Bot Setup Guide

This guide will help you install and run the OSRS automation bot.

## Prerequisites

- **Python 3.10 or higher** (tested with Python 3.13.7)
- **Windows OS** (required for some Windows-specific dependencies)
- **Tesseract OCR** (for text recognition features)

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/osrsbot.git
cd osrsbot
```

### 2. Verify Python Installation

Check that Python is installed:

```powershell
python --version
```

You should see `Python 3.10.x` or higher.

### 3. Install pip (if needed)

Check if pip is available:

```powershell
python -m pip --version
```

If pip is not found, install it:

```powershell
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
```

### 4. Install the Package

Install the osrsbot package in editable mode from the project root directory:

```powershell
python -m pip install -e .
```

This will install osrsbot and all its dependencies:
- pyautogui (GUI automation)
- opencv-python (computer vision)
- numpy (numerical computing)
- pytesseract (OCR)
- Pillow (image processing)
- rich (terminal UI)
- Windows-specific packages (PyWinCtl, mouse, keyboard)

### 5. Install Tesseract OCR

Download and install Tesseract OCR from:
https://github.com/UB-Mannheim/tesseract/wiki

Add Tesseract to your system PATH or configure the path in your bot configuration.

## Running the Bot

Once installed, you can run the bot using the CLI command:

```powershell
osrs-bot
```

Or directly with Python:

```powershell
python -m osrsbot
```

## Troubleshooting

### ModuleNotFoundError: No module named 'osrsbot'

This error occurs when the package isn't installed. Make sure you run:

```powershell
python -m pip install -e .
```

from the project root directory.

### No module named 'cv2'

This means opencv-python isn't installed. Reinstall the package:

```powershell
python -m pip install -e . --force-reinstall
```

### No module named 'pip'

Install pip using:

```powershell
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
```

### Command not found: osrs-bot

Make sure Python's Scripts directory is in your PATH:
```
C:\Users\YourUsername\AppData\Local\Programs\Python\Python3XX\Scripts
```

You can also run directly:
```powershell
python -m osrsbot
```

## Development Setup

For development with additional tools (testing, linting, formatting):

```powershell
python -m pip install -e ".[dev]"
```

This installs:
- pytest (testing framework)
- pytest-cov (coverage reporting)
- black (code formatting)
- ruff (linting)

## Project Structure

```
Python-Automation-Framework/
├── src/osrsbot/          # Source code
│   ├── core/             # Bot framework
│   ├── services/         # Service layer
│   ├── commands/         # CQRS commands
│   ├── queries/          # CQRS queries
│   ├── models/           # Data models
│   ├── app/              # Application layer
│   └── main.py           # Entry point
├── pyproject.toml        # Project configuration
└── README.md             # Project documentation
```

## Configuration

Bot behavior is controlled via JSON configuration files. See the documentation in the [README.md](README.md) for details on configuration options.

## Next Steps

1. Configure your bot settings in the configuration files
2. Run the calibration tools to set up screen coordinates
3. Start with test scripts to verify functionality
4. Refer to the main [README.md](README.md) for architecture details

## Advanced Features Setup

### Status Socket Plugin (Required for Walker/Pathfinding)

The Status Socket plugin provides real-time player position and camera data from RuneLite. This is **required** for the advanced walker/pathfinding system.

#### Installation (RuneLite Plugin Hub)

1. Open RuneLite
2. Click the **wrench icon** (Configuration)
3. Scroll to **"Plugin Hub"**
4. Search for: **"Status Socket"**
5. Click **"Install"**
6. **Restart RuneLite**

#### Configuration

1. In RuneLite Configuration, find **"Status Socket"**
2. Set **Output File Path** to:
   ```
   C:\Users\ellio\Documents\Projects\OSRSbot\Python-Automation-Framework\live_data.json
   ```
   *(Adjust path to match your installation directory)*
3. Set **Update Interval**: `100` ms
4. Enable: **WorldPoint**, **Camera**, **Animation**, **Movement**

#### Verification

1. Start RuneLite and log into OSRS
2. Check that `live_data.json` is created in your bot directory
3. File should contain JSON with `worldPoint` and `camera` data
4. Move in-game and verify coordinates update in real-time
5. Run bot and check logs for:
   ```
   INFO - StatusSocketService initialized (plugin detected)
   INFO - WalkerService initialized successfully
   ```

#### Troubleshooting

- **Plugin not appearing**: Update RuneLite, enable Plugin Hub, restart
- **File not created**: Check path permissions, verify plugin enabled
- **Bot not detecting**: Verify `data_file` path in `config.json` matches actual file location
- **Data stale**: Plugin may have crashed, restart RuneLite

### Arduino Mouse (Optional)

Hardware mouse control via Arduino for enhanced anti-detection. **Optional** and disabled by default.

#### Requirements

- Arduino board (Uno, Nano, Leonardo)
- `pyserial`: `pip install pyserial`
- Custom Arduino firmware (not included)

#### Configuration

1. Connect Arduino via USB
2. Find serial port (Windows: COM3, Linux: /dev/ttyUSB0)
3. Update `config.json`:
   ```json
   "arduino": {
     "enabled": true,
     "serial_port": "COM3",
     "baud_rate": 115200
   }
   ```

#### Verification

Logs should show:
```
INFO - Arduino connection established successfully
INFO - ArduinoMouseService initialized
```

Or fallback:
```
WARNING - Arduino not available, falling back to software mouse
```

## Support

For issues or questions:
- Check the [README.md](README.md) for project documentation
- Review the code in `src/osrsbot/` for implementation details
- Report issues at: https://github.com/elliottbbbbbb/Python-Automation-Framework/issues
- This is a portfolio/learning project - use at your own risk

## Legal Disclaimer

This bot automates interaction with third-party software and may violate terms of service. It is developed strictly for educational purposes and portfolio demonstration. Use responsibly and at your own risk.
