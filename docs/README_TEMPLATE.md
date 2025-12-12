# OSRS Bot - Educational Automation Framework

⚠️ **EDUCATIONAL PURPOSE ONLY** - This project is for learning about game automation, computer vision, and botting detection techniques. Using automation tools on live game servers violates the game's terms of service and may result in account bans.

---

## Overview

A sophisticated Old School RuneScape (OSRS) automation framework demonstrating advanced software engineering concepts:

- **Computer Vision**: OCR, template matching, color detection
- **Anti-Detection**: Behavioral randomization and human-like patterns
- **State Machines**: Complex workflow automation
- **CQRS Architecture**: Command-query separation for clean design
- **Service Architecture**: Modular, testable components

This project showcases modern Python development practices including dependency injection, design patterns, and comprehensive testing infrastructure.

---

## Features

### Core Automation Capabilities

#### Humanized Mouse Movement
- **Bezier curve paths** for natural mouse movement
- **Multiple movement styles**: Linear, curved, instant, overshoot
- **Randomized speed variance** (0.2-0.6s multipliers)
- **Click variance** (±3 pixel offset from target)
- **Post-click delays** to simulate human reaction time

#### Computer Vision
- **Multi-strategy OCR** for stat reading (HP, prayer, etc.)
- **Template matching** for UI element detection (OpenCV)
- **Color detection** with configurable tolerance
- **Pixel sampling** for inventory slot detection
- **Window management** with dynamic coordinate translation

#### Anti-Ban System
- **Scheduled breaks** with randomized intervals (30-60 min)
- **Micro-breaks** (5% random chance between actions)
- **Session variance** (±15% timing randomization)
- **Idle actions** (mouse jitter, stats checking)
- **Pattern detection** (prevents repetitive action sequences)

#### State Machine Framework
- **Explicit state definitions** with retry logic
- **Automatic failover** on errors
- **Execution history** tracking for debugging
- **Configurable timeouts** and retry limits
- **State transition logging**

### Available Bot Scripts

#### Green Dragons Bot
- State machine implementation for dragon farming
- Automated combat with HP monitoring
- Banking integration (Varrock/Edgeville)
- Loot collection and food management
- Kill counting and statistics

#### Template Matching Test Bot
- UI element detection testing
- Template matching verification
- Yellow NPC detection demo

---

## Architecture

### Design Patterns

The project demonstrates several advanced design patterns:

1. **CQRS (Command Query Responsibility Segregation)**
   - `GameActions` - Commands that modify game state
   - `GameState`, `InventoryState` - Queries that read state

2. **State Machine Pattern**
   - Complex workflows with explicit state definitions
   - Automatic retry and failover logic

3. **Service Architecture**
   - Layered services with dependency injection
   - Single responsibility principle

4. **Strategy Pattern**
   - OCR preprocessing strategies
   - Mouse movement strategies

### Architecture Layers

```
┌─────────────────────────────────────────┐
│     Application Layer                   │
│  CLI Menu, Calibration Tool             │
└─────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────┐
│     Command/Query Layer (CQRS)          │
│  GameActions, GameState, InventoryState │
└─────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────┐
│     Core Layer                          │
│  Bot, StateMachineBot, GameInterface    │
└─────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────┐
│     Services Layer                      │
│  Mouse, Screen, OCR, Template, Anti-Ban │
└─────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────┐
│     Model Layer                         │
│  Config, StateTypes, UIElements         │
└─────────────────────────────────────────┘
```

---

## Technology Stack

**Core Dependencies**:
- Python 3.10+
- pyautogui - GUI automation
- PyWinCtl - Window management (Windows)
- Pillow (PIL) - Image processing
- OpenCV (cv2) - Template matching
- pytesseract - OCR integration
- NumPy - Numerical operations

**Development Tools**:
- pytest - Testing framework
- pytest-cov - Coverage reporting
- black - Code formatting
- ruff - Linting
- mypy - Type checking

**Platform**: Windows (uses Windows-specific APIs)

---

## Installation

### Prerequisites

1. **Python 3.10 or higher**
   ```bash
   python --version  # Should be 3.10+
   ```

2. **Tesseract OCR**
   - Download and install from: https://github.com/UB-Mannheim/tesseract/wiki
   - Default path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
   - Add to PATH or update path in code

3. **Git** (for cloning)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/OSRSbot.git
   cd OSRSbot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   # source venv/bin/activate  # On Linux/Mac (not fully supported)
   ```

3. **Install dependencies**
   ```bash
   pip install -e .
   ```

4. **Create configuration file**
   ```bash
   # Copy example config (if exists)
   cp config.example.json config.json

   # Or create from scratch - see Configuration section
   ```

5. **Configure settings**
   Edit `config.json` with your setup (see Configuration section)

---

## Configuration

### config.json Structure

The bot is configured through `config.json`:

```json
{
  "account_name": "your_account",
  "window_title": "RuneLite - your_account",

  "colors": {
    "yellow_tile_marker": "#fcfc01",
    "green_dragon": "#00ffff",
    "manta_ray": "#ff00ff",
    ...
  },

  "coordinates": {
    "inventory": {
      "slot_1": {"x": 100, "y": 200},
      ...
    },
    "world": {
      "bank_booth": {"x": 300, "y": 400},
      ...
    }
  },

  "timings": {
    "short": [0.4, 0.7],
    "medium": [0.8, 1.3],
    "long": [2.5, 3.8]
  },

  "mouse": {
    "min_speed": 0.2,
    "max_speed": 0.6,
    "overshoot_chance": 0.15,
    "click_variance": 3
  },

  "templates": {
    "ui_grids": {
      "inventory": {
        "path": "templates/inventory.png",
        "rows": 7,
        "cols": 4
      }
    }
  }
}
```

### Calibration

Use the built-in calibration tool to find colors and coordinates:

```bash
osrs-bot
# Select: 1. Calibrate Colors & Coordinates
```

The tool will help you:
- Find hex color codes for UI elements
- Identify coordinate positions
- Test template matching

---

## Usage

### Running the Bot

**Interactive Menu**:
```bash
osrs-bot
```

**Menu Options**:
1. Calibrate Colors & Coordinates
2. Run Green Dragons Script
3. Run Guns Script (legacy)
4. Test Script
5. Template Matching Test
6. State Machine Test

**Direct Script Execution**:
```python
from osrsbot.core.runner import ScriptRunner
from osrsbot.scripts.green_dragons_state import GreenDragonsStateMachineBot

runner = ScriptRunner(config_path="config.json")
runner.run_script(
    GreenDragonsStateMachineBot,
    runs=10,
    bank_location="varrock"
)
```

### Creating Custom Bots

**Option 1: State Machine Bot** (Recommended for complex workflows)

```python
from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_types import StateMetadata, StateResult
from enum import Enum

class MyBotStates(Enum):
    IDLE = "idle"
    GATHERING = "gathering"
    BANKING = "banking"

class MyBot(StateMachineBot):
    def define_states(self):
        return {
            MyBotStates.IDLE: StateMetadata(name="Idle"),
            MyBotStates.GATHERING: StateMetadata(
                name="Gathering",
                max_retries=3,
                timeout=300.0
            ),
            MyBotStates.BANKING: StateMetadata(name="Banking"),
        }

    def define_transitions(self):
        return {
            MyBotStates.IDLE: MyBotStates.GATHERING,
            MyBotStates.GATHERING: MyBotStates.BANKING,
            MyBotStates.BANKING: MyBotStates.GATHERING,
        }

    def handle_state(self, state, context):
        if state == MyBotStates.GATHERING:
            # Gathering logic
            while not self.inventory.is_full():
                self.actions.click_color("resource")
                self.actions.wait("medium")
            return StateResult.SUCCESS

        # Handle other states...
```

**Option 2: Simple Bot** (For basic scripts)

```python
from osrsbot.core.base_bot import Bot

class MySimpleBot(Bot):
    def run_cycle(self, bank_location: str, run_number: int):
        # Simple sequential logic
        self.actions.click_color("resource")
        self.actions.wait("short")

        while not self.inventory.is_full():
            self.actions.click_color("resource")
            self.actions.wait("medium")

        # Banking logic...
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/osrsbot --cov-report=html

# Run specific test file
pytest tests/unit/services/test_mouse_service.py

# Run with markers
pytest -m unit  # Unit tests only
pytest -m integration  # Integration tests only
```

### Test Structure

```
tests/
├── unit/
│   ├── services/
│   │   └── test_mouse_service.py
│   ├── models/
│   │   └── test_config.py
│   └── utils/
│       └── test_color_helpers.py
├── conftest.py  # Fixtures
└── fixtures/    # Test data
```

### Current Coverage

- **Overall**: <10% (goal: 60%+)
- **MouseService**: 85%
- **ColorHelpers**: 90%
- **Config**: 60%

---

## Security & Performance Notes

### Security Considerations

⚠️ **IMPORTANT**: This project has security considerations:

1. **Credentials**: Do NOT commit `config.json` with account information
2. **Config Management**: Use environment variables for sensitive data
3. **Input Validation**: All external inputs should be validated
4. **Logging**: Logs may contain sensitive information

**See**: [docs/SECURITY_REPORT.md](docs/SECURITY_REPORT.md) for detailed security analysis

### Performance Optimization

The bot includes several performance optimizations:

- **Parallel OCR**: Multiple preprocessing strategies run in parallel
- **ROI Captures**: Screen captures limited to regions of interest
- **Batch Operations**: Inventory scanning uses batch pixel sampling
- **Caching**: Window bounds and templates cached

**See**: [docs/PERFORMANCE_REPORT.md](docs/PERFORMANCE_REPORT.md) for detailed performance analysis

---

## Documentation

### Available Documentation

- [**COMPREHENSIVE_ANALYSIS.md**](docs/COMPREHENSIVE_ANALYSIS.md) - Complete codebase analysis
- [**ARCHITECTURE.md**](docs/ARCHITECTURE.md) - Architecture deep dive
- [**SECURITY_REPORT.md**](docs/SECURITY_REPORT.md) - Security assessment
- [**PERFORMANCE_REPORT.md**](docs/PERFORMANCE_REPORT.md) - Performance analysis
- [**CODE_QUALITY_REPORT.md**](docs/CODE_QUALITY_REPORT.md) - Code quality metrics

### Code Organization

- `src/osrsbot/core/` - Core bot framework
- `src/osrsbot/services/` - Service layer (mouse, screen, OCR, etc.)
- `src/osrsbot/commands/` - Game actions (CQRS commands)
- `src/osrsbot/queries/` - Game state queries (CQRS queries)
- `src/osrsbot/models/` - Data models and configuration
- `src/osrsbot/app/` - User interface (CLI menu, calibration)
- `src/osrsbot/scripts/` - Bot implementations
- `src/osrsbot/utils/` - Utility functions

---

## Development

### Code Quality

**Code Formatting**:
```bash
black src/ tests/
```

**Linting**:
```bash
ruff check src/ tests/
```

**Type Checking**:
```bash
mypy src/osrsbot
```

### Contributing

This is an educational project. If you'd like to contribute:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Run code quality tools
6. Submit a pull request

---

## Project Structure

```
OSRSbot/
├── src/osrsbot/           # Source code
│   ├── core/             # Bot framework
│   ├── services/         # Service layer
│   ├── commands/         # CQRS commands
│   ├── queries/          # CQRS queries
│   ├── models/           # Data models
│   ├── app/              # User interface
│   ├── scripts/          # Bot scripts
│   └── utils/            # Utilities
│
├── tests/                # Test suite
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── conftest.py      # Fixtures
│
├── templates/           # UI templates for matching
├── docs/                # Documentation
├── config.json          # Configuration (not in git)
├── config.example.json  # Configuration template
├── pyproject.toml       # Project metadata
└── README.md           # This file
```

---

## Roadmap

### Current Status

**Version**: 1.0 (Educational Alpha)

**Implemented**:
- ✓ Core bot framework
- ✓ State machine pattern
- ✓ CQRS architecture
- ✓ Anti-ban behavioral system
- ✓ Green Dragons bot (demo)
- ✓ Comprehensive documentation

**Known Limitations**:
- ⚠ Test coverage <10% (goal: 60%+)
- ⚠ Type hints 70% (goal: 95%+)
- ⚠ Windows only (no cross-platform support)

### Future Enhancements

**Short-term** (Weeks 1-4):
- [ ] Expand test coverage to 40%+
- [ ] Add type hints to 95%+
- [ ] Refactor large monolithic classes
- [ ] Add CI/CD pipeline

**Medium-term** (Months 2-3):
- [ ] Cross-platform support (Linux, macOS)
- [ ] Web-based configuration UI
- [ ] Real-time performance monitoring
- [ ] Additional bot scripts

**Long-term** (Months 4+):
- [ ] Machine learning for pattern detection
- [ ] Advanced computer vision techniques
- [ ] Comprehensive benchmarking suite
- [ ] Educational video tutorials

---

## FAQ

### General Questions

**Q: Can I use this on live OSRS servers?**
A: No. This is for educational purposes only. Using automation tools violates game terms of service and will result in account bans.

**Q: What can I learn from this project?**
A: Computer vision, state machines, CQRS architecture, anti-detection techniques, Python best practices, testing, and more.

**Q: Does this work on Linux/Mac?**
A: Currently Windows only due to Windows-specific APIs. Cross-platform support is planned.

### Technical Questions

**Q: Why is test coverage so low?**
A: The project prioritized architecture and features first. Test coverage expansion is the top priority for future sprints.

**Q: How does the anti-ban system work?**
A: It randomizes timing, mouse movement patterns, adds breaks, and varies behavior to appear more human-like.

**Q: Can I add my own bot scripts?**
A: Yes! Extend `Bot` or `StateMachineBot` classes. See "Creating Custom Bots" section.

---

## License

**Educational Use Only**

This project is provided for educational purposes to demonstrate:
- Software engineering best practices
- Computer vision techniques
- Game automation concepts
- Anti-detection strategies

**NOT FOR PRODUCTION USE** on live game servers. Using automation tools on Old School RuneScape violates the game's terms of service.

**No Warranty**: This software is provided "as is" without warranty of any kind.

---

## Disclaimer

This project is an independent educational endeavor and is not affiliated with, endorsed by, or associated with Jagex Ltd or Old School RuneScape.

Old School RuneScape is a trademark of Jagex Ltd.

**Using automation tools on live game servers is against the game's rules and may result in permanent account bans.**

---

## Contact & Support

**Issues**: Report bugs or issues on GitHub Issues
**Discussions**: Use GitHub Discussions for questions
**Documentation**: See `docs/` folder for detailed documentation

**Educational Questions**: This project is designed for learning. Study the code, run tests, and experiment in a controlled environment.

---

## Acknowledgments

This project demonstrates concepts from:
- Software architecture patterns (CQRS, State Machine)
- Computer vision techniques (OCR, template matching)
- Anti-detection strategies
- Python best practices

Built with modern Python tooling and comprehensive documentation for educational purposes.

---

**Version**: 1.0
**Last Updated**: December 12, 2025
**Status**: Educational Alpha
