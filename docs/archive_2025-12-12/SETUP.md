# OSRS Automation Framework - Setup Guide

Complete setup instructions for getting the framework running on your machine.

## Prerequisites

- **Python 3.10 or higher** (tested on Python 3.13)
- **Windows 10/11** (required for some features)
- **Git** (for cloning the repository)
- **Tesseract OCR** (for text recognition)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/OSRS-Automation-Framework.git
cd OSRS-Automation-Framework
```

### 2. Install Python Dependencies

```bash
pip install -e .
```

This will install all required packages from `pyproject.toml`.

### 3. Install Tesseract OCR

Download and install Tesseract OCR:

- **Download**: https://github.com/UB-Mannheim/tesseract/wiki
- **Recommended version**: 5.0 or higher
- **Installation path**: `C:\Program Files\Tesseract-OCR\` (default)

If you install to a custom location, you'll need to set the path in `.env` (see Configuration below).

### 4. Download MNIST Model (for OCR)

The framework uses a CNN-based digit classifier for improved accuracy. Download the model:

```bash
python scripts/download_mnist_model.py
```

This downloads a 26KB pre-trained model to `src/osrsbot/models/mnist_cnn.onnx`.

### 5. Run the Bot

```bash
osrs-bot
```

Or:

```bash
python -m osrsbot.app.menu
```

You should see the main menu with options to calibrate and run test bots.

## Configuration

### Environment Variables (.env)

Create a `.env` file in the root directory to customize settings:

```bash
# Mouse Input Driver
# Set to 1 to use Interception driver (kernel-level, requires setup)
# Set to 0 or omit to use standard mouse control (default)
USE_INTERCEPTION=0

# Tesseract OCR Path (only needed if not in default location)
# TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe

# Logging Level
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Development Mode
# Set to 1 to enable additional debug features
DEV_MODE=0
```

An example `.env.example` file is provided in the repository.

### Bot Configuration (config.json)

The `config.json` file contains bot behavior settings:

- Mouse movement timing and styles
- Anti-detection parameters
- Template matching thresholds
- UI element coordinates

You can edit this file to customize bot behavior without changing code.

## Advanced Setup (Optional)

### Hardware Mouse Control (Arduino)

For enhanced anti-detection, you can use an Arduino as a hardware mouse:

**Requirements:**
- Arduino board (Uno, Leonardo, Micro, etc.)
- USB cable
- Arduino IDE

**Setup:**
1. Upload the sketch from `arduino/mouse_controller/mouse_controller.ino` to your Arduino
2. Note the COM port (e.g., `COM3`)
3. Set `ARDUINO_PORT=COM3` in your `.env` file
4. The framework will automatically use the Arduino mouse if available

**Fallback:** If the Arduino is not connected, the framework automatically falls back to standard mouse control.

### Kernel-Level Mouse (Interception Driver) - OPTIONAL

The Interception driver provides kernel-level mouse input that's harder to detect. **This is optional and not required.**

> **Warning:** The Interception driver is complex to set up and may not work on all systems. Only attempt this if you need kernel-level input.

See [INTERCEPTION_SETUP.md](INTERCEPTION_SETUP.md) for detailed instructions.

**Fallback:** If Interception is not available, the framework automatically falls back to standard mouse control.

## Verification

### 1. Run Calibration

```bash
osrs-bot
# Select option 1: Calibrate Colors & Coordinates
```

This helps you configure color detection and UI coordinates for your setup.

### 2. Run Comprehensive Test

```bash
osrs-bot
# Select option 2: Comprehensive Test Bot
```

This tests all framework features:
- Mouse movement
- OCR (HP, prayer, stats)
- Template matching
- Color detection
- Pathfinding
- Combat detection
- State machine

You should see a detailed report of all tested features.

## Troubleshooting

### Tesseract Not Found

**Error:** `TesseractNotFoundError` or OCR not working

**Solution:**
1. Verify Tesseract is installed: Open CMD and run `tesseract --version`
2. If not found, add Tesseract to your system PATH
3. Or set `TESSERACT_PATH` in `.env` to point to `tesseract.exe`

### MNIST Model Not Found

**Error:** `onnxruntime not installed. Digit classifier will not be available.`

**Solution:**
```bash
pip install onnxruntime
python scripts/download_mnist_model.py
```

The framework will fall back to Tesseract OCR if the MNIST model isn't available.

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'osrsbot'`

**Solution:**
```bash
pip install -e .
```

This installs the package in editable mode.

### Python Version Issues

**Error:** Syntax errors or type hint issues

**Solution:** Ensure you're using Python 3.10 or higher:
```bash
python --version
```

## Development Setup

If you want to contribute or modify the code:

### Install Dev Dependencies

```bash
pip install -e ".[dev]"
```

This includes testing and linting tools.

### Code Quality Tools

```bash
# Format code
black src/

# Lint code
ruff check src/

# Type checking
mypy src/
```

### Running Tests

```bash
pytest
```

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10 | Windows 10/11 |
| Python | 3.10 | 3.13+ |
| RAM | 4 GB | 8 GB+ |
| CPU | Dual-core | Quad-core+ |
| Disk Space | 500 MB | 1 GB |

## Next Steps

1. **Calibrate colors and coordinates** for your display setup
2. **Run the comprehensive test** to verify all features work
3. **Explore the example scripts** in `src/osrsbot/scripts/`
4. **Read the architecture documentation** in the main README.md

## Getting Help

- Check the [README.md](README.md) for architecture details
- Review example scripts in `src/osrsbot/scripts/`
- Check the issues page for known problems

## License

See [LICENSE](LICENSE) for details.

## Disclaimer

This project automates interaction with third-party software and may violate terms of service. It was developed strictly for educational purposes.
