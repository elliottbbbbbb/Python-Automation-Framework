# Quick Start Setup Guide

**Get up and running in 10 minutes**

---

## Step-by-Step Installation

### 1. Install Python

**Download:** [python.org](https://python.org) - Get version **3.10, 3.11, 3.12, or 3.13**

**Important on Windows:** ✅ Check "Add Python to PATH" during installation

**Verify:**
```bash
python --version
# Should show: Python 3.10.x or higher
# Note: Python 3.13 works too!
```

---

### 2. Get the Code

**Option A: Download ZIP**
- Download this repository as ZIP
- Extract to your desired location
- Open terminal/command prompt in that folder

**Option B: Clone with Git**
```bash
git clone <repository-url>
cd OSRS-Automation-Framework
```

---

### 3. Create Virtual Environment

**What is this?** Keeps packages for this project separate from other Python projects.

```bash
# In the project folder (OSRS-Automation-Framework)
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate

# You should see (venv) appear in your terminal
```

**To deactivate later:**
```bash
deactivate
```

---

### 4. Install Dependencies

```bash
# Make sure (venv) is showing in terminal
pip install -e .
```

**What `-e` means:** "Editable mode" - any code changes take effect immediately (no need to reinstall)

**What this does:**
- Reads `pyproject.toml` (the modern Python package configuration file)
- Downloads and installs 15+ required packages automatically
- Takes 2-5 minutes depending on internet speed

**Expected output:**
```
Successfully installed osrsbot-0.1.0 pyautogui-0.9.54 opencv-python-4.8.0 ...
```

**Alternative (without editable mode):**
```bash
# If you just want to use the package without modifying code
pip install .
# Note: Need to reinstall after code changes
```

---

### 5. Install Tesseract OCR

**Windows:**
1. Download installer: [Tesseract Windows](https://github.com/UB-Mannheim/tesseract/wiki)
2. Run installer (use default location)
3. Add to PATH or configure in `config.json`

**Mac:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

---

### 6. Verify Installation

```bash
# Test that everything works
python -c "import osrsbot; print('Success!')"

# If you see "Success!" you're ready to go!
```

---

### 7. Run Your First Bot

```bash
# Start the bot menu
python -m osrsbot

# Select option 5: Manual Cleaning Bankstander
# Follow the on-screen prompts
```

---

## Troubleshooting

### "No module named 'osrsbot'"

**Solution:**
```bash
# Make sure you're in the right directory
cd OSRS-Automation-Framework

# Make sure virtual environment is activated
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Try installing again
pip install -e .
```

---

### "pip is not recognized"

**Solution:**
```bash
# Use python -m pip instead
python -m pip install -e .
```

---

### "Permission denied"

**Solution:**
```bash
# Windows: Run terminal as Administrator
# Or use --user flag
pip install -e . --user
```

---

### "Microsoft Visual C++ is required"

**Solution:**
Download and install: [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

Select "Desktop development with C++" during installation.

---

### "Could not find a version that satisfies the requirement"

**Solution:**
```bash
# Update pip first
python -m pip install --upgrade pip

# Try again
pip install -e .
```

---

## Every Time You Work on the Project

**1. Activate virtual environment:**
```bash
# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

**2. Run the bot:**
```bash
python -m osrsbot
```

**3. When done, deactivate:**
```bash
deactivate
```

---

## Configuration

### First Run Calibration

Before using bots, calibrate your screen coordinates:

```bash
python -m osrsbot
# Select option 1: Calibrate Colors & Coordinates
# Follow the prompts to set up your config.json
```

### Config File Location

`config.json` in the project root directory.

**Important settings:**
- `window_title`: Your RuneLite window title
- `tesseract_path`: Path to Tesseract executable
- `colors`: NPC/item highlight colors
- `coordinates`: UI element positions

---

## Next Steps

Once installed, read:
- **[Beginner Developer Guide](BEGINNER_DEVELOPER_GUIDE.md)** - Learn Python by building bots
- **[Bot Development Guide](BOT_DEVELOPMENT_GUIDE.md)** - Advanced bot creation
- **[Architecture Guide](ARCHITECTURE.md)** - Understand the framework

---

## Common Commands Reference

```bash
# Activate virtual environment
venv\Scripts\activate              # Windows
source venv/bin/activate           # Mac/Linux

# Run bot menu
python -m osrsbot

# Test import
python -c "import osrsbot"

# Install new package (if needed)
pip install package-name

# Update dependencies
pip install -e . --upgrade

# Deactivate virtual environment
deactivate

# Check what's installed
pip list
```

---

## System Requirements

**Minimum:**
- Python 3.10 or higher (3.10, 3.11, 3.12, or 3.13 all work)
- 4GB RAM
- Windows 10/11, macOS 10.14+, or Linux
- Internet connection (for initial setup)

**Recommended:**
- Python 3.11, 3.12, or 3.13 (latest is usually best)
- 8GB RAM
- SSD for faster package installation
- RuneLite client installed

**Note:** Most dependencies are cross-platform, but some Windows-specific packages (pywin32, PyWinCtl, keyboard, mouse) are automatically excluded on Mac/Linux per `pyproject.toml`

---

## Package Dependencies (Auto-Installed)

When you run `pip install -e .`, these are installed:

**Core:**
- pyautogui (mouse/keyboard)
- opencv-python (computer vision)
- numpy (fast arrays)
- pillow (image processing)

**OCR:**
- pytesseract (text recognition)

**Windows-specific:**
- pywin32 (Windows API)
- PyWinCtl (window control)
- keyboard, mouse (input control)

**Utilities:**
- rich (pretty terminal output)
- python-dotenv (environment variables)
- pyserial (hardware communication)

**ML/AI:**
- onnxruntime (neural network inference)

---

## Getting Help

**Installation Issues:**
1. Check this troubleshooting guide
2. Check `docs/` folder for more guides
3. Search error message on Google/Stack Overflow
4. Create GitHub issue with error details

**Learning Python:**
- See [Beginner Developer Guide](BEGINNER_DEVELOPER_GUIDE.md)
- Start with Level 0 (just run existing bots)
- Progress gradually through levels

---

## Setup Verification Checklist

Run through this checklist to make sure everything is working:

- [ ] **Python installed:** `python --version` shows 3.10+
- [ ] **In project directory:** `cd OSRS-Automation-Framework`
- [ ] **Virtual environment created:** `venv` folder exists
- [ ] **Virtual environment activated:** See `(venv)` in terminal
- [ ] **Package installed:** `pip install -e .` completed successfully
- [ ] **Import works:** `python -c "import osrsbot"` runs without error
- [ ] **Tesseract installed:** `tesseract --version` shows version (if using OCR)
- [ ] **Bot menu runs:** `python -m osrsbot` shows menu
- [ ] **Config exists:** `config.json` in project root (created after first calibration)

**If all checked ✅, you're ready to build bots!**

---

## Common Installation Patterns

**Fresh install:**
```bash
cd OSRS-Automation-Framework
python -m venv venv
venv\Scripts\activate  # Windows
pip install -e .
python -m osrsbot
```

**Updating after git pull:**
```bash
cd OSRS-Automation-Framework
venv\Scripts\activate  # Windows
pip install -e . --upgrade  # Reinstall if dependencies changed
python -m osrsbot
```

**Clean reinstall (if something breaks):**
```bash
cd OSRS-Automation-Framework
# Delete venv folder
rmdir /s venv  # Windows
rm -rf venv    # Mac/Linux

# Recreate everything
python -m venv venv
venv\Scripts\activate  # Windows
pip install -e .
```

---

**Last Updated:** 2026-01-09
**Python Version Required:** 3.10+ (3.10, 3.11, 3.12, 3.13 all supported)
**Estimated Setup Time:** 10-15 minutes
**Package Manager:** pip with pyproject.toml
