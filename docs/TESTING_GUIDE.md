# Testing Guide for OSRS Bot

**Last Updated**: December 12, 2025

This guide shows you how to run and work with the test suite.

---

## Quick Start

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src/osrsbot --cov-report=html

# Run specific test file
pytest tests/unit/services/test_mouse_service.py

# Run tests matching pattern
pytest -k "test_mouse"
```

---

## Table of Contents

1. [Installation](#installation)
2. [Running Tests](#running-tests)
3. [Test Structure](#test-structure)
4. [Writing Tests](#writing-tests)
5. [Coverage Reports](#coverage-reports)
6. [Troubleshooting](#troubleshooting)

---

## Installation

### 1. Install Test Dependencies

```bash
# Activate virtual environment
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dev dependencies
pip install -e ".[dev]"

# Or install test packages directly
pip install pytest pytest-cov pytest-mock
```

### 2. Verify Installation

```bash
# Check pytest is installed
pytest --version

# Should output: pytest 7.x.x or higher
```

---

## Running Tests

### Basic Commands

#### Run All Tests
```bash
pytest
```

**Output**:
```
=================== test session starts ===================
platform win32 -- Python 3.10.x, pytest-7.x.x
collected 87 items

tests/unit/services/test_mouse_service.py .......... [ 11%]
tests/unit/services/test_screen_service.py ........ [ 20%]
tests/unit/services/test_ocr_service.py ........... [ 32%]
tests/unit/commands/test_game_actions.py ......... [ 43%]
tests/unit/models/test_config.py ................. [ 54%]
tests/unit/utils/test_color_helpers.py ........... [ 65%]
tests/integration/test_basic_integration.py ...... [ 76%]

=================== 87 passed in 2.34s ====================
```

#### Run with Verbose Output
```bash
pytest -v
```

Shows each test name as it runs:
```
tests/unit/services/test_screen_service.py::TestScreenServiceInitialization::test_initialization_with_valid_params PASSED
tests/unit/services/test_screen_service.py::TestScreenServiceColorDetection::test_find_color_simple_match PASSED
...
```

#### Run Specific Test File
```bash
# Run only screen service tests
pytest tests/unit/services/test_screen_service.py

# Run only OCR tests
pytest tests/unit/services/test_ocr_service.py

# Run only minimap service tests
pytest tests/unit/services/test_minimap_service.py

# Run only integration tests
pytest tests/integration/
```

#### Run Specific Test Class
```bash
# Run only color detection tests
pytest tests/unit/services/test_screen_service.py::TestScreenServiceColorDetection

# Run only mouse movement tests
pytest tests/unit/services/test_mouse_service.py::TestMouseServiceInstantMovement

# Run only minimap pathfinding tests
pytest tests/unit/services/test_minimap_service.py::TestMinimapServicePathfinding
```

#### Run Specific Test
```bash
# Run single test
pytest tests/unit/services/test_screen_service.py::TestScreenServiceColorDetection::test_find_color_simple_match

# Run minimap pathfinding test
pytest tests/unit/services/test_minimap_service.py::TestMinimapServicePathfinding::test_find_path_straight_line
```

### Advanced Commands

#### Run Tests by Marker
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only slow tests
pytest -m slow
```

#### Run Tests Matching Pattern
```bash
# Run all tests with "color" in name
pytest -k "color"

# Run all tests with "mouse" or "screen"
pytest -k "mouse or screen"

# Exclude tests with "slow" in name
pytest -k "not slow"
```

#### Stop on First Failure
```bash
# Stop immediately on first failure
pytest -x

# Stop after 3 failures
pytest --maxfail=3
```

#### Show Print Statements
```bash
# Show print() output even for passing tests
pytest -s

# Show print output and be verbose
pytest -sv
```

---

## Test Structure

### Current Test Organization

```
tests/
├── unit/                           # Unit tests (isolated components)
│   ├── services/
│   │   ├── test_mouse_service.py      # Mouse movement & clicking (87 tests)
│   │   ├── test_screen_service.py     # Screen capture & color detection (NEW)
│   │   ├── test_ocr_service.py        # OCR digit recognition (NEW)
│   │   └── test_minimap_service.py    # Minimap walkable tiles & pathfinding (NEW)
│   ├── commands/
│   │   └── test_game_actions.py       # High-level game actions (NEW)
│   ├── models/
│   │   └── test_config.py             # Configuration loading (17 tests)
│   └── utils/
│       └── test_color_helpers.py      # Color utilities (21 tests)
│
├── integration/                    # Integration tests (components together)
│   └── test_basic_integration.py      # Basic service integration (NEW)
│
├── conftest.py                    # Shared fixtures
└── fixtures/                      # Test data
    └── sample_data.py
```

### Test File Naming

- `test_*.py` - Test files
- `*_test.py` - Also valid

### Test Class Naming

- `TestClassNameFeature` - Group related tests
- Example: `TestScreenServiceColorDetection`

### Test Function Naming

- `test_what_it_tests` - Descriptive name
- Example: `test_find_color_simple_match`

---

## Writing Tests

### Basic Test Structure

```python
import pytest
from unittest.mock import Mock, patch

def test_simple_addition():
    """Test that addition works"""
    result = 2 + 2
    assert result == 4

def test_with_fixture(mock_config):
    """Test using a fixture"""
    value = mock_config.get("key")
    assert value is not None

@pytest.mark.slow
def test_slow_operation():
    """Test marked as slow"""
    # Long-running test
    pass
```

### Using Fixtures

```python
# In conftest.py
@pytest.fixture
def mock_config():
    """Create mock config for tests"""
    config = Mock()
    config.get.return_value = "default_value"
    return config

# In test file
def test_uses_config(mock_config):
    """Test receives fixture automatically"""
    assert mock_config.get("anything") == "default_value"
```

### Mocking

#### Mock External Dependencies
```python
from unittest.mock import Mock, patch

def test_with_mock():
    """Test with mocked pyautogui"""
    with patch('pyautogui.screenshot') as mock_screenshot:
        mock_screenshot.return_value = fake_image

        # Your test code
        result = some_function_that_uses_pyautogui()

        # Verify mock was called
        mock_screenshot.assert_called_once()
```

#### Mock Object Methods
```python
def test_mock_method():
    """Test with mocked object method"""
    obj = Mock()
    obj.method.return_value = 42

    result = obj.method("arg")

    assert result == 42
    obj.method.assert_called_with("arg")
```

### Common Assertions

```python
# Equality
assert result == expected

# Truth values
assert is_true
assert not is_false

# Exceptions
with pytest.raises(ValueError):
    function_that_should_raise()

# Approximate equality (for floats)
assert result == pytest.approx(3.14, abs=0.01)

# Contains
assert item in collection

# Type checking
assert isinstance(result, int)

# None checking
assert result is None
assert result is not None
```

---

## Coverage Reports

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=src/osrsbot

# Generate HTML coverage report
pytest --cov=src/osrsbot --cov-report=html

# Generate both terminal and HTML reports
pytest --cov=src/osrsbot --cov-report=term-missing --cov-report=html
```

### View Coverage Report

```bash
# Open HTML report (Windows)
start htmlcov/index.html

# Open HTML report (Linux/Mac)
open htmlcov/index.html
```

### Coverage Output Example

```
---------- coverage: platform win32, python 3.10.x -----------
Name                                      Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------
src/osrsbot/__init__.py                       0      0   100%
src/osrsbot/services/mouse_service.py       124     12    90%   145-156
src/osrsbot/services/screen_service.py      156     45    71%   89-102, 234-256
src/osrsbot/services/ocr_service.py         98     32    67%   123-145, 178-189
src/osrsbot/commands/game_actions.py        203    78    62%   45-67, 145-178
src/osrsbot/models/config.py                 45      5    89%   78-82
src/osrsbot/utils/color_helpers.py           28      0   100%
-----------------------------------------------------------------------
TOTAL                                       654    172    74%
```

### Branch Coverage

```bash
# Include branch coverage
pytest --cov=src/osrsbot --cov-branch --cov-report=term-missing
```

Shows coverage of if/else branches, not just lines.

---

## Test Markers

### Available Markers

Defined in `pytest.ini`:

```ini
[pytest]
markers =
    unit: Unit tests (isolated components)
    integration: Integration tests (multiple components)
    slow: Slow tests (>1 second)
```

### Using Markers

```python
@pytest.mark.unit
def test_unit_test():
    """Fast isolated test"""
    pass

@pytest.mark.integration
def test_integration():
    """Test multiple components together"""
    pass

@pytest.mark.slow
def test_slow_operation():
    """Test that takes >1 second"""
    pass

# Multiple markers
@pytest.mark.unit
@pytest.mark.slow
def test_complex_calculation():
    """Slow unit test"""
    pass
```

### Running Marked Tests

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run unit tests but skip slow ones
pytest -m "unit and not slow"
```

---

## Troubleshooting

### Common Issues

#### 1. "ModuleNotFoundError: No module named 'osrsbot'"

**Solution**:
```bash
# Install package in development mode
pip install -e .
```

#### 2. "No tests ran / 0 collected"

**Cause**: Test files not named correctly

**Solution**:
- Ensure files start with `test_`
- Ensure functions start with `test_`
- Check you're in the right directory

```bash
# Run from project root
cd /path/to/OSRSbot
pytest
```

#### 3. "ImportError: cannot import name 'something'"

**Cause**: Missing dependencies

**Solution**:
```bash
pip install -r requirements.txt
pip install pytest pytest-cov
```

#### 4. Tests fail with "Tesseract not found"

**Cause**: OCR tests need Tesseract, but it's mocked

**Solution**: Tests should mock pytesseract. If not:
```python
@patch('pytesseract.image_to_string')
def test_ocr(mock_ocr):
    mock_ocr.return_value = "42"
    # Test code
```

#### 5. "Fixture 'mock_config' not found"

**Cause**: Fixture not defined in conftest.py

**Solution**: Add fixture to `tests/conftest.py` or test file

---

## Testing Specific Services

### MinimapService Tests

The minimap service tests cover walkable tile extraction and pathfinding:

```bash
# Run all minimap tests
pytest tests/unit/services/test_minimap_service.py -v

# Run only pathfinding tests
pytest tests/unit/services/test_minimap_service.py::TestMinimapServicePathfinding -v

# Run a specific pathfinding test
pytest tests/unit/services/test_minimap_service.py::TestMinimapServicePathfinding::test_find_path_straight_line -v
```

**Test Coverage**:
- ✓ Walkable tile extraction from minimap
- ✓ Circular mask application
- ✓ Dot removal (players, NPCs, items)
- ✓ Color-based terrain classification
- ✓ A* pathfinding on tile grid
- ✓ Edge cases (no path, out of bounds, obstacles)

**Example Test**:
```python
def test_find_path_around_obstacle(minimap_service):
    """Test pathfinding around obstacle"""
    # Create grid with obstacle
    tile_grid = np.ones((36, 36), dtype=bool)
    tile_grid[10:25, 18] = False  # Vertical wall

    start = (10, 18)
    goal = (25, 18)

    path = minimap_service.find_walkable_path(tile_grid, start, goal)

    assert path is not None
    assert len(path) > abs(goal[0] - start[0])  # Goes around
```

### ScreenService Tests

```bash
# Run all screen service tests
pytest tests/unit/services/test_screen_service.py -v

# Run only color detection tests
pytest tests/unit/services/test_screen_service.py::TestScreenServiceColorDetection -v
```

**Test Coverage**:
- ✓ Color detection with tolerance
- ✓ Pixel sampling
- ✓ Screen capture
- ✓ Region-based operations
- ✓ Color matching algorithms

### OCRService Tests

```bash
# Run all OCR tests
pytest tests/unit/services/test_ocr_service.py -v

# Run preprocessing tests
pytest tests/unit/services/test_ocr_service.py::TestOCRServicePreprocessing -v
```

**Test Coverage**:
- ✓ Digit recognition (single, double, triple digits)
- ✓ Multiple preprocessing strategies
- ✓ Consensus voting
- ✓ Edge cases (zero, empty image, noise)

### GameActions Tests

```bash
# Run all game actions tests
pytest tests/unit/commands/test_game_actions.py -v

# Run timing tests
pytest tests/unit/commands/test_game_actions.py::TestGameActionsWait -v
```

**Test Coverage**:
- ✓ Click coordinate actions
- ✓ Click color actions
- ✓ Wait timing (short, medium, long)
- ✓ Walk to marker
- ✓ Action sequences

---

## Best Practices

### DO:
- ✓ Write tests for new features
- ✓ Keep tests isolated (use mocks for external dependencies)
- ✓ Use descriptive test names
- ✓ Test both success and failure cases
- ✓ Run tests before committing
- ✓ Aim for >60% coverage on new code

### DON'T:
- ✗ Don't test external libraries (e.g., don't test pyautogui)
- ✗ Don't make tests depend on each other
- ✗ Don't use real game window in unit tests
- ✗ Don't hardcode paths or system-specific values
- ✗ Don't skip writing tests ("I'll add them later")

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest --cov=src/osrsbot --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## Test Coverage Goals

### Current Status

| Component | Coverage | Target | Status |
|-----------|----------|--------|--------|
| MouseService | 85% | 90% | ✓ Good |
| ScreenService | 20% | 80% | ⚠ NEW - Needs work |
| OCRService | 15% | 70% | ⚠ NEW - Needs work |
| GameActions | 10% | 70% | ⚠ NEW - Needs work |
| Config | 60% | 80% | ⚠ Needs improvement |
| ColorHelpers | 90% | 90% | ✓ Excellent |
| **Overall** | **25%** | **60%** | ⚠ Improving |

### Roadmap

**Sprint 1** (Weeks 1-2): 25% → 40%
- Expand ScreenService tests
- Expand OCRService tests
- Add GameActions tests

**Sprint 2** (Weeks 3-4): 40% → 60%
- Add TemplateMatchService tests
- Add AntiBanService tests
- Add StateMachineBot tests

**Sprint 3** (Weeks 5-8): 60%+ → Target
- Add end-to-end tests
- Add error path tests
- Achieve 60%+ coverage

---

## Example Test Session

```bash
# 1. Navigate to project
cd C:\Users\ellio\Documents\Projects\OSRSbot

# 2. Activate virtual environment
venv\Scripts\activate

# 3. Run all tests with coverage
pytest --cov=src/osrsbot --cov-report=html --cov-report=term-missing

# Output:
# =================== test session starts ===================
# collected 87 items
#
# tests/unit/services/test_mouse_service.py .......... [ 11%]
# tests/unit/services/test_screen_service.py ........ [ 20%]
# tests/unit/services/test_ocr_service.py ........... [ 32%]
# ...
# =================== 87 passed in 3.45s ====================
#
# ---------- coverage: platform win32 -----------
# Name                                Stmts   Miss  Cover   Missing
# -----------------------------------------------------------------
# src/osrsbot/services/mouse.py        124     12    90%   145-156
# ...
# TOTAL                                654    172    74%

# 4. View HTML coverage report
start htmlcov/index.html

# 5. Run specific tests
pytest tests/unit/services/test_screen_service.py -v

# 6. Run with specific marker
pytest -m unit -v
```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `pytest` | Run all tests |
| `pytest -v` | Verbose output |
| `pytest -s` | Show print statements |
| `pytest -x` | Stop on first failure |
| `pytest -k "pattern"` | Run tests matching pattern |
| `pytest -m marker` | Run tests with marker |
| `pytest --cov=src` | Run with coverage |
| `pytest --cov-report=html` | Generate HTML coverage |
| `pytest path/to/test.py` | Run specific file |
| `pytest path/to/test.py::TestClass::test_func` | Run specific test |

---

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

---

**Happy Testing!** 🧪

Remember: Good tests = confident code changes = better software!
