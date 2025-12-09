# OSRS Bot

Automated bot framework for Old School RuneScape using Python.

## Features

- 🎯 **Template Matching** - Detect UI elements with OpenCV
- 🖱️ **Human-like Mouse Movement** - Curved paths with variance
- 👁️ **OCR Health Detection** - Read HP from game UI
- 🎨 **Color Detection** - Find and click colored markers
- 🔧 **Config-Driven** - JSON configuration for all settings
- 📦 **Modular Architecture** - Clean separation of concerns

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run the bot
python -m osrsbot.main
```

## Project Structure

```
OSRSbot/
├── src/osrsbot/          # Main source code
│   ├── app/              # Application layer (menu, calibration)
│   ├── controllers/      # Controllers (actions, runner)
│   ├── core/             # Core components (game interface, base bot)
│   ├── models/           # Data models (config, state)
│   ├── scripts/          # Bot scripts (green_dragons, guns, etc.)
│   └── services/         # Services (mouse, screen, OCR, template matching)
├── docs/                 # Documentation
├── examples/             # Example scripts
├── templates/            # Template images for UI detection
├── config.json           # Configuration file
└── pyproject.toml        # Project metadata
```

## Documentation

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get started quickly
- **[Full README](docs/README.md)** - Complete project documentation
- **[Template Matching Guide](docs/TEMPLATE_MATCHING_GUIDE.md)** - Learn template detection
- **[Architecture Overview](docs/ARCHITECTURE_DIAGRAM.md)** - System design
- **[Documentation Index](docs/INDEX.md)** - All documentation

## Configuration

Edit `config.json` to configure:
- Account name and window title
- Colors for detection
- Coordinates for UI elements
- Mouse movement settings
- Template paths

## Creating Bots

Bots inherit from the `Bot` base class:

```python
from osrsbot.core.base_bot import Bot

class MyBot(Bot):
    def run_cycle(self, bank_location: str, run_number: int) -> None:
        # Your bot logic here
        self.actions.click_color("yellow_tile_marker")
        self.state.get_health()
```

## Examples

See [examples/](examples/) for:
- `template_matching_example.py` - Full template matching demo
- `old_todo_reference.py` - Original pattern matcher reference

## Requirements

- Python 3.11+
- RuneLite OSRS client
- Tesseract OCR

## License

See LICENSE file for details.

## Contributing

Contributions welcome! Please read the documentation first.

## On The Table - Future Improvements

These are potential improvements to consider, but not critical to current functionality:

### Optimization Ideas
- **Template Matching OCR** - Replace shape detection OCR with cv2 template matching or CNN approach for potentially higher accuracy
- **CoordinateSystem Class** - Create dedicated class with caching to consolidate coordinate conversion (currently well-handled in GameInterface)
- **Split GameActions** - Break down GameActions (~425 lines) into separate files: click_actions.py, combat_actions.py, bank_actions.py, navigation_actions.py

### Enhancement Ideas
- **Pydantic Config Validation** - Replace manual JSON validation with Pydantic models for stricter schema validation and better error messages
- **Custom Exception Hierarchy** - Create WindowNotFoundError, OCRError, ClickError, etc. instead of generic RuntimeError/ValueError
- **Constants.py** - Extract remaining magic numbers (OCR thresholds, preprocessing values) into named constants
- **File-based Logging** - Add rotating file logs with configurable levels per module (currently console-only)
- **Banking Strategy Pattern** - Create BankStrategy base class with VarrockBankStrategy, FaladorBankStrategy, etc.
- **Enhanced Randomization** - Add variance to wait() times, random micro-movements during idle, occasional "misclicks"
- **Result Type Pattern** - Consider Result[T, E] return types instead of Optional/bool for better error context

### Infrastructure
- **Test Suite** - Add pytest tests for core functionality (coordinate conversion, mouse movement, config loading, color detection)
- **CI/CD Pipeline** - Run tests and linting on commits
- **Type Checking** - Run mypy in CI to catch type annotation issues
