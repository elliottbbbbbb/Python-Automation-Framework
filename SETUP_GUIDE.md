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

## Support

For issues or questions:
- Check the [README.md](README.md) for project documentation
- Review the code in `src/osrsbot/` for implementation details
- This is a portfolio/learning project - use at your own risk

## Legal Disclaimer

This bot automates interaction with third-party software and may violate terms of service. It is developed strictly for educational purposes and portfolio demonstration. Use responsibly and at your own risk.
