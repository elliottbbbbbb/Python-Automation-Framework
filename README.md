# OSRS Automation Framework

A Python-based color/vision bot framework for Old School RuneScape. No client modification, no injection — reads pixels and moves the mouse like a human.

## Features

- **State Machine Framework** — Define bot logic as states with retries, timeouts, and failover transitions
- **CQRS Architecture** — Clean separation between commands (actions) and queries (state reads)
- **Computer Vision** — OpenCV template matching, color detection, and template-based OCR
- **Human-like Input** — Bezier curve mouse movement with overshoot, speed variance, and click jitter
- **Anti-Ban** — Weighted break patterns, session drift, micro-breaks, idle actions, and auto-relogin
- **Live Debug View** — Real-time overlay showing what the bot sees (template matches, OCR regions, UI elements)
- **Configurable** — JSON config with deep-merge defaults. Calibration tool for colors and coordinates

## Included Bot Scripts

| Script | Description |
|--------|-------------|
| NMZ AFK | 1 HP absorption strategy with overload cycling |
| Herb Cleaning | Bankstander for cleaning grimy herbs |
| Construction | Chair building 1-40 with Phials NPC |

The framework is designed to make writing new bot scripts easy — see the examples below.

## Requirements

- Python 3.10+
- Windows (uses Win32 APIs for input)
- RuneLite client with relevant plugins (NPC Indicators, Tile Markers, etc.)

## Quick Start

```bash
# Clone and install
git clone https://github.com/yourusername/OSRS-Automation-Framework.git
cd OSRS-Automation-Framework
python -m venv .venv
.venv\Scripts\activate
pip install -e .

# Configure
# Edit src/osrsbot/config.json with your account name and window title

# Run
python -m osrsbot.app.menu
```

## Writing a Bot Script

### Simple Bot (linear logic)
```python
from osrsbot.core.base_bot import Bot

class MyBot(Bot):
    def __init__(self, **kwargs):
        super().__init__(script_name="My Bot", **kwargs)

    def run_cycle(self, bank_location: str, run_number: int) -> None:
        if not self.state.in_combat():
            self.actions.click_color("npc_target")
        if self.state.get_hp() < 30:
            self.actions.eat("manta_ray")
```

### State Machine Bot (complex logic)
```python
from osrsbot.core.state_machine_bot import StateMachineBot
from osrsbot.core.state_types import StateResult
from enum import Enum, auto

class States(Enum):
    IDLE = auto()
    COMBAT = auto()
    BANKING = auto()

class MyBot(StateMachineBot):
    def define_states(self) -> type[Enum]:
        return States

    def _handle_idle(self, context) -> StateResult:
        return StateResult.SUCCESS  # transitions to next state

    def _handle_combat(self, context) -> StateResult:
        if self.state.in_combat():
            return StateResult.RETRY
        return StateResult.SUCCESS
```

### Bankstander Bot (repetitive bank tasks)
```python
from osrsbot.core.base_bankstander import BankstanderBot
from osrsbot.core.state_types import StateResult

class MyBankstander(BankstanderBot):
    def __init__(self, **kwargs):
        super().__init__(
            item_name="grimy toadflax",
            item_search_text="toadflax",
            item_template="images/bot/items/grimy_toadflax.png",
            script_name="Herb Cleaner",
            **kwargs,
        )

    def process_items(self, context) -> StateResult:
        for slot in range(1, 29):
            self.actions.click_inventory_slot(slot)
        return StateResult.SUCCESS
```

## Configuration

Copy `src/osrsbot/config.json` and edit:

- `account_name` / `window_title` — your RuneLite window title
- `colors` — hex colors matching your RuneLite NPC Indicator / tile marker settings
- `coordinates` — screen positions (use the calibration tool: menu option 1)
- `templates` — paths to template images for UI detection
- `timings` — action delay ranges
- `mouse` — movement speed, overshoot chance, click variance

## Project Structure

```
src/osrsbot/
  core/           # Framework: base classes, state machine, runner
  commands/       # CQRS write side (GameActions facade)
  queries/        # CQRS read side (GameState facade)
  services/       # Mouse, screen, OCR, anti-ban, template matching
  scripts/        # Bot implementations
  models/         # Config, state types, UI elements
  app/            # Menu, calibration, debug UI
  images/         # Template images for matching
```

## Disclaimer

This project is for educational purposes. Use at your own risk. Botting violates Jagex's Terms of Service and can result in account bans.
