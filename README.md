
* Practice scalable system design
* Apply design patterns to a non-trivial domain
* Write maintainable, self-documenting Python
* Manage complexity through clear layering and separation of concerns

---

## Architecture

Layered architecture with strict responsibility boundaries:

```
Application Layer (CLI, calibration tools)
→ Command / Query Layer (CQRS)
→ Core Layer (State Machine, Bot Framework)
→ Services Layer (Mouse, Screen, OCR, CV, Anti-detection)
→ Models & Configuration
```

**Why this matters:**

* Predictable state mutation via CQRS
* Testable, replaceable services via dependency injection
* Clear isolation between behavior, perception, and control

---

## Technical Highlights

### Architecture & Design

* State machine framework with retries, timeouts, and failover states
* CQRS separation between actions (commands) and state inspection (queries)
* Full dependency injection via constructors
* Strategy pattern for OCR preprocessing and mouse movement algorithms
* Configuration-driven behavior using JSON

### Computer Vision

* OpenCV-based template matching with configurable thresholds
* Multi-strategy OCR preprocessing for improved recognition accuracy
* HSV color detection with tolerance-based matching
* Coordinate transformation between screen spaces
* Region-of-interest limiting for performance

### Behavioral Systems

* Humanized mouse movement using Bezier curves and overshoot simulation
* Gaussian-distributed timing variance
* Randomized micro-break scheduling
* Distance-based target prioritization with stuck detection
* Automatic blacklisting of problematic targets

---

## Project Structure

```
src/osrsbot/
├── core/                    # Framework foundation
│   ├── base_bot.py
│   ├── state_machine_bot.py
│   ├── game_interface.py
│   └── runner.py
├── services/               # Service layer
│   ├── mouse_service.py
│   ├── screen_service.py
│   ├── ocr_service.py
│   ├── template_match_service.py
│   ├── anti_ban_service.py
│   ├── loot_detection_service.py
│   └── minimap_pathfinding_service.py
├── commands/               # CQRS - write operations
│   └── game_actions.py
├── queries/                # CQRS - read operations
│   └── game_queries.py
├── models/                 # Configuration and data models
│   ├── config.py
│   ├── state_types.py
│   └── ui_elements.py
└── scripts/                # Bot implementations
    └── test_state_machine_bot.py
```

---

## Code Quality & Refactoring

Recent refactoring focused on long-term maintainability:

* Removed 900+ lines of duplicate code
* Eliminated AI-generated patterns and verbose boilerplate
* Reduced defensive checks in favor of clear invariants
* Resolved all TODO/FIXME items
* Refactored toward small, self-documenting functions

Result: a significantly cleaner and more maintainable codebase.

---

## Example: State Machine Bot

```python
class MyBot(StateMachineBot):
    def define_states(self) -> type[Enum]:
        return MyBotStates

    def define_state_metadata(self) -> dict[Enum, StateMetadata]:
        return {
            MyBotStates.WORKING: StateMetadata(
                name="Working",
                max_retries=5,
                timeout=300.0,
                failover_state=MyBotStates.COMPLETE,
            ),
        }

    def _handle_working(self, context) -> StateResult:
        if work_complete:
            return StateResult.SUCCESS
        return StateResult.RETRY
```

---

## Configuration

All behavior is controlled via JSON configuration:

* Mouse movement and timing
* Anti-detection behavior
* Template matching thresholds
* Coordinates and UI mappings

This allows rapid tuning without code changes.

---

## Technologies Used

* Python 3.10+
* OpenCV
* Tesseract OCR
* NumPy, Pillow
* PyAutoGUI, PyWinCtl
* pytest, black, ruff, mypy

---

## Project Metrics

| Metric           | Value                             |
| ---------------- | --------------------------------- |
| Lines of Code    | ~5,000                            |
| Python Modules   | 44                                |
| Services         | 7                                 |
| Design Patterns  | CQRS, State Machine, Strategy, DI |
| Development Time | 6+ months                         |

---

## Status

Active learning project. Used as a portfolio demonstration of Python proficiency, software architecture, and problem-solving ability.

**Last updated:** December 2024

---

## Disclaimer

This project automates interaction with third-party software and may violate terms of service. It was developed strictly for educational purposes and has never been used commercially.
