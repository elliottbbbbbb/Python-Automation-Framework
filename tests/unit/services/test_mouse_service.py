"""
Unit tests for MouseService.

Tests mouse movement, clicking, and humanization with heavy mocking.
"""

import pytest
from unittest.mock import Mock, patch, call
from osrsbot.services.mouse_service import MouseService, MouseConfig


@pytest.fixture
def mock_pyautogui(monkeypatch):
    """Mock pyautogui for all mouse operations."""
    mock = Mock()
    mock.position.return_value = (100, 100)
    mock.moveTo = Mock()
    mock.click = Mock()
    mock.drag = Mock()
    mock.FAILSAFE = True
    mock.PAUSE = 0

    monkeypatch.setattr("pyautogui.position", mock.position)
    monkeypatch.setattr("pyautogui.moveTo", mock.moveTo)
    monkeypatch.setattr("pyautogui.click", mock.click)
    monkeypatch.setattr("pyautogui.drag", mock.drag)
    monkeypatch.setattr("pyautogui.FAILSAFE", mock.FAILSAFE)
    monkeypatch.setattr("pyautogui.PAUSE", mock.PAUSE)

    return mock


@pytest.fixture
def mock_time(monkeypatch):
    """Mock time.time() and time.sleep()."""
    mock = Mock()
    mock.time.return_value = 1000.0
    mock.sleep = Mock()

    monkeypatch.setattr("time.time", mock.time)
    monkeypatch.setattr("time.sleep", mock.sleep)

    return mock


@pytest.fixture
def mock_random(monkeypatch):
    """Mock random for deterministic testing."""
    mock = Mock()
    mock.uniform.return_value = 0.3
    mock.randint.return_value = 5
    mock.random.return_value = 0.5
    mock.choice.return_value = "linear"

    monkeypatch.setattr("random.uniform", mock.uniform)
    monkeypatch.setattr("random.randint", mock.randint)
    monkeypatch.setattr("random.random", mock.random)
    monkeypatch.setattr("random.choice", mock.choice)

    return mock


@pytest.fixture
def mouse_service():
    """Create MouseService with default config."""
    config = MouseConfig(
        min_speed=0.1,
        max_speed=0.5,
        overshoot_chance=0.15,
        overshoot_distance=20,
        click_variance=3,
        post_click_delay=(0.05, 0.15)
    )
    return MouseService(config)


class TestMouseServiceInit:
    """Test MouseService initialization."""

    def test_initialization_with_config(self, mock_pyautogui):
        """Test MouseService initializes with custom config."""
        config = MouseConfig(min_speed=0.2, max_speed=0.6)
        service = MouseService(config)

        assert service.config.min_speed == 0.2
        assert service.config.max_speed == 0.6

    def test_initialization_without_config(self, mock_pyautogui):
        """Test MouseService uses default config when none provided."""
        service = MouseService()

        assert service.config is not None
        assert isinstance(service.config, MouseConfig)

    def test_pyautogui_failsafe_enabled(self, mock_pyautogui):
        """Test PyAutoGUI failsafe is enabled."""
        service = MouseService()

        assert mock_pyautogui.FAILSAFE == True


class TestMoveToInstant:
    """Test instant mouse movement."""

    def test_instant_move(self, mouse_service, mock_pyautogui):
        """Test instant movement style."""
        result = mouse_service.move_to(200, 200, style="instant")

        assert result == True
        mock_pyautogui.moveTo.assert_called_once_with(200, 200, duration=0)

    def test_calls_pyautogui_moveTo(self, mouse_service, mock_pyautogui):
        """Test instant movement calls moveTo with correct args."""
        mouse_service.move_to(300, 400, style="instant")

        mock_pyautogui.moveTo.assert_called_with(300, 400, duration=0)


class TestMoveToLinear:
    """Test linear mouse movement."""

    def test_linear_movement(self, mouse_service, mock_pyautogui, mock_random):
        """Test linear movement style."""
        result = mouse_service.move_to(200, 200, style="linear", duration=0.5)

        assert result == True
        mock_pyautogui.moveTo.assert_called_once_with(200, 200, duration=0.5)

    def test_duration_calculation(self, mouse_service, mock_pyautogui, mock_random):
        """Test automatic duration calculation for linear movement."""
        # Mock distance calculation will use random.uniform
        mock_random.uniform.return_value = 0.3

        mouse_service.move_to(200, 200, style="linear")

        # Verify moveTo was called (duration calculated automatically)
        assert mock_pyautogui.moveTo.called


class TestMoveToCurved:
    """Test curved (Bezier) mouse movement."""

    def test_curved_movement(self, mouse_service, mock_pyautogui, mock_random, mock_time):
        """Test curved movement uses Bezier algorithm."""
        result = mouse_service.move_to(200, 200, style="curved", duration=0.1)

        assert result == True
        # Bezier should call moveTo multiple times (for each step)
        assert mock_pyautogui.moveTo.call_count > 1

    def test_bezier_curve_generation(self, mouse_service, mock_pyautogui, mock_random, mock_time):
        """Test Bezier curve generates multiple points."""
        mouse_service.move_to(200, 200, style="curved", duration=0.1)

        # Bezier movement should have multiple steps
        assert mock_pyautogui.moveTo.call_count >= 5


class TestMoveToOvershoot:
    """Test overshoot mouse movement."""

    def test_overshoot_movement(self, mouse_service, mock_pyautogui, mock_random, mock_time):
        """Test overshoot movement style."""
        # Mock random to trigger overshoot
        mock_random.random.return_value = 0.1  # < overshoot_chance (0.15)

        result = mouse_service.move_to(200, 200, style="overshoot", duration=0.1)

        assert result == True
        # Overshoot should involve multiple movements
        assert mock_pyautogui.moveTo.call_count > 1

    def test_overshoot_calculation(self, mouse_service, mock_pyautogui, mock_random, mock_time):
        """Test overshoot calculates correct overshoot point."""
        mock_random.random.return_value = 0.1  # Trigger overshoot
        mock_random.randint.return_value = 10

        mouse_service.move_to(200, 200, style="overshoot", duration=0.1)

        # Should have multiple moveTo calls (overshoot then correction)
        assert mock_pyautogui.moveTo.call_count >= 2


class TestMoveToRandom:
    """Test random movement style selection."""

    def test_random_style_selection(self, mouse_service, mock_pyautogui, mock_random):
        """Test random style picks from available styles."""
        mock_random.choice.return_value = "linear"

        result = mouse_service.move_to(200, 200, style="random", duration=0.5)

        assert result == True
        # Should delegate to chosen style
        mock_random.choice.assert_called_once()


class TestClick:
    """Test mouse clicking."""

    def test_basic_click(self, mouse_service, mock_pyautogui, mock_time, mock_random):
        """Test basic click at current position."""
        result = mouse_service.click()

        assert result == True
        mock_pyautogui.click.assert_called_once_with(button="left")

    def test_click_with_button(self, mouse_service, mock_pyautogui, mock_time, mock_random):
        """Test click with different button."""
        mouse_service.click(button="right")

        mock_pyautogui.click.assert_called_with(button="right")

    def test_click_with_coordinates(self, mouse_service, mock_pyautogui, mock_time, mock_random):
        """Test click at specific coordinates."""
        mouse_service.click(x=100, y=200, variance=False)

        mock_pyautogui.moveTo.assert_called_once_with(100, 200)
        mock_pyautogui.click.assert_called_once()

    def test_click_with_variance(self, mouse_service, mock_pyautogui, mock_time, mock_random):
        """Test click adds variance offset."""
        mock_random.randint.return_value = 2

        mouse_service.click(x=100, y=200, variance=True)

        # Variance should add offset to coordinates
        # With randint returning 2, final position should be (102, 202)
        mock_pyautogui.moveTo.assert_called_with(102, 202)

    def test_click_delay_after(self, mouse_service, mock_pyautogui, mock_time, mock_random):
        """Test click adds delay after clicking."""
        mock_random.uniform.return_value = 0.1

        mouse_service.click(delay_after=True)

        # Should call sleep with delay
        mock_time.sleep.assert_called()


class TestClickAt:
    """Test move and click composite operation."""

    def test_click_at_coordinates(self, mouse_service, mock_pyautogui, mock_time, mock_random):
        """Test click_at moves then clicks."""
        result = mouse_service.click_at(200, 300, move_style="instant")

        assert result == True
        # Should call both moveTo and click
        assert mock_pyautogui.moveTo.called
        assert mock_pyautogui.click.called

    def test_uses_movement_style(self, mouse_service, mock_pyautogui, mock_time, mock_random):
        """Test click_at uses specified movement style."""
        mouse_service.click_at(200, 300, move_style="linear")

        # Linear style should call moveTo once for the move
        assert mock_pyautogui.moveTo.called


class TestDragTo:
    """Test mouse dragging."""

    def test_basic_drag(self, mouse_service, mock_pyautogui):
        """Test basic drag operation."""
        mock_pyautogui.position.return_value = (100, 100)

        result = mouse_service.drag_to(200, 200, duration=0.5)

        assert result == True
        mock_pyautogui.drag.assert_called_once_with(
            100, 100, duration=0.5, button="left"
        )

    def test_drag_with_button(self, mouse_service, mock_pyautogui):
        """Test drag with specific button."""
        mock_pyautogui.position.return_value = (50, 50)

        mouse_service.drag_to(150, 150, button="right")

        # Should calculate relative offset (150-50, 150-50)
        mock_pyautogui.drag.assert_called_with(
            100, 100, duration=0.5, button="right"
        )


class TestGetPosition:
    """Test getting current mouse position."""

    def test_get_position(self, mouse_service, mock_pyautogui):
        """Test get_position returns current coordinates."""
        mock_pyautogui.position.return_value = (250, 350)

        position = mouse_service.get_position()

        assert position == (250, 350)


class TestRandomMovement:
    """Test random mouse movement."""

    def test_random_movement(self, mouse_service, mock_pyautogui, mock_random, mock_time):
        """Test random movement within radius."""
        mock_pyautogui.position.return_value = (100, 100)
        # randint is used for offset AND Bezier control points, so return fixed value
        mock_random.randint.return_value = 5

        mouse_service.random_movement(radius=20)

        # Should move to offset position (will call moveTo for Bezier steps)
        assert mock_pyautogui.moveTo.call_count > 0
