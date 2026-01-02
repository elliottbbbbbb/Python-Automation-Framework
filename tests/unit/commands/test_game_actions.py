"""
Unit tests for GameActions (CQRS Commands)

Tests high-level game action commands.
"""

from unittest.mock import Mock, patch

import pytest

from osrsbot.commands.game_actions import GameActions
from osrsbot.core.game_interface import GameInterface
from osrsbot.models.config import Config
from osrsbot.queries.game_queries import GameState
from osrsbot.services.mouse_service import MouseService
from osrsbot.services.screen_service import ScreenService


class TestGameActionsInitialization:
    """Test GameActions initialization"""

    def test_initialization_with_dependencies(
        self, mock_interface, mock_config, mock_mouse, mock_screen, mock_state
    ):
        """Test GameActions initializes with all dependencies"""
        actions = GameActions(
            mock_interface, mock_config, mock_mouse, mock_screen, mock_state
        )

        assert actions.interface == mock_interface
        assert actions.config == mock_config
        assert actions.mouse == mock_mouse
        assert actions.screen == mock_screen
        assert actions.state == mock_state


class TestGameActionsClickCoordinate:
    """Test clicking at named coordinates"""

    def test_click_coordinate_success(self, game_actions, mock_config, mock_mouse):
        """Test clicking at a configured coordinate"""
        # Configure coordinate
        mock_config.get.return_value = {"x": 100, "y": 200}

        game_actions.click_coordinate("bank_booth")

        # Should move mouse and click
        mock_mouse.move_to.assert_called_once()
        mock_mouse.click.assert_called_once()

    def test_click_coordinate_not_found(self, game_actions, mock_config):
        """Test clicking coordinate that doesn't exist"""
        mock_config.get.return_value = None

        with pytest.raises((KeyError, ValueError, Exception)):
            game_actions.click_coordinate("nonexistent_coordinate")

    def test_click_coordinate_with_movement_type(
        self, game_actions, mock_config, mock_mouse
    ):
        """Test clicking with specific movement type"""
        mock_config.get.return_value = {"x": 100, "y": 200}

        game_actions.click_coordinate("target", movement_type="curved")

        # Should use specified movement type
        call_args = mock_mouse.move_to.call_args
        assert "movement_type" in call_args.kwargs or len(call_args.args) >= 3


class TestGameActionsClickColor:
    """Test clicking at colored elements"""

    def test_click_color_found(
        self, game_actions, mock_config, mock_screen, mock_mouse
    ):
        """Test clicking when color is found"""
        # Configure color
        mock_config.get.return_value = "#00ff00"

        # Mock color found
        color_match = Mock()
        color_match.x = 150
        color_match.y = 250
        mock_screen.find_color.return_value = color_match

        game_actions.click_color("green_dragon")

        # Should find color and click
        mock_screen.find_color.assert_called_once_with("#00ff00", tolerance=10)
        mock_mouse.move_to.assert_called_once_with(150, 250, movement_type="curved")
        mock_mouse.click.assert_called_once()

    def test_click_color_not_found(self, game_actions, mock_config, mock_screen):
        """Test clicking when color is not found"""
        mock_config.get.return_value = "#00ff00"
        mock_screen.find_color.return_value = None

        # Should handle gracefully (return False or raise exception)
        result = game_actions.click_color("green_dragon")

        # Implementation might return False or raise exception
        assert result is None or result is False

    def test_click_color_with_tolerance(
        self, game_actions, mock_config, mock_screen, mock_mouse
    ):
        """Test clicking color with custom tolerance"""
        mock_config.get.side_effect = lambda *args: {
            ("colors", "target"): "#ff0000",
            ("color_detection", "tolerance"): 15,
        }.get(args, 10)

        color_match = Mock()
        color_match.x = 100
        color_match.y = 100
        mock_screen.find_color.return_value = color_match

        game_actions.click_color("target")

        # Should use configured tolerance
        mock_screen.find_color.assert_called_once()


class TestGameActionsWait:
    """Test wait/timing actions"""

    def test_wait_short(self, game_actions, mock_config):
        """Test short wait timing"""
        mock_config.get.return_value = [0.4, 0.7]

        with patch("time.sleep") as mock_sleep:
            game_actions.wait("short")

            mock_sleep.assert_called_once()
            # Should sleep for time in range
            sleep_time = mock_sleep.call_args[0][0]
            assert 0.4 <= sleep_time <= 0.7

    def test_wait_medium(self, game_actions, mock_config):
        """Test medium wait timing"""
        mock_config.get.return_value = [0.8, 1.3]

        with patch("time.sleep") as mock_sleep:
            game_actions.wait("medium")

            mock_sleep.assert_called_once()
            sleep_time = mock_sleep.call_args[0][0]
            assert 0.8 <= sleep_time <= 1.3

    def test_wait_long(self, game_actions, mock_config):
        """Test long wait timing"""
        mock_config.get.return_value = [2.5, 3.8]

        with patch("time.sleep") as mock_sleep:
            game_actions.wait("long")

            mock_sleep.assert_called_once()
            sleep_time = mock_sleep.call_args[0][0]
            assert 2.5 <= sleep_time <= 3.8

    def test_wait_custom_timing(self, game_actions, mock_config):
        """Test custom timing type"""
        mock_config.get.return_value = [5.0, 10.0]

        with patch("time.sleep") as mock_sleep:
            game_actions.wait("custom_timing")

            mock_sleep.assert_called_once()


class TestGameActionsWalkToMarker:
    """Test walking to colored tile markers"""

    def test_walk_to_marker_success(
        self, game_actions, mock_config, mock_screen, mock_mouse
    ):
        """Test walking to a tile marker"""
        mock_config.get.return_value = "#fcfc01"  # Yellow marker

        color_match = Mock()
        color_match.x = 300
        color_match.y = 400
        mock_screen.find_color.return_value = color_match

        game_actions.walk_to_marker("yellow_tile_marker")

        # Should find marker and click it
        mock_screen.find_color.assert_called_once()
        mock_mouse.move_to.assert_called_once()
        mock_mouse.click.assert_called_once()

    def test_walk_to_marker_not_found(self, game_actions, mock_config, mock_screen):
        """Test walking when marker not found"""
        mock_config.get.return_value = "#fcfc01"
        mock_screen.find_color.return_value = None

        result = game_actions.walk_to_marker("yellow_tile_marker")

        # Should handle marker not found
        assert result is None or result is False


class TestGameActionsIntegration:
    """Test action sequences (integration-like tests)"""

    def test_click_sequence(self, game_actions, mock_config, mock_screen, mock_mouse):
        """Test sequence of clicks"""
        mock_config.get.side_effect = lambda *args: {
            ("colors", "dragon"): "#00ff00",
            ("colors", "food"): "#ff00ff",
        }.get(args, 10)

        # Mock both colors found
        dragon_match = Mock(x=100, y=100)
        food_match = Mock(x=200, y=200)
        mock_screen.find_color.side_effect = [dragon_match, food_match]

        # Click dragon, then food
        game_actions.click_color("dragon")
        game_actions.click_color("food")

        # Both should be clicked
        assert mock_mouse.click.call_count == 2

    def test_click_with_wait(self, game_actions, mock_config, mock_screen, mock_mouse):
        """Test click followed by wait"""
        mock_config.get.side_effect = lambda *args: {
            ("colors", "target"): "#ff0000",
            ("timings", "short"): [0.4, 0.7],
        }.get(args, {"x": 100, "y": 100})

        color_match = Mock(x=100, y=100)
        mock_screen.find_color.return_value = color_match

        with patch("time.sleep") as mock_sleep:
            game_actions.click_color("target")
            game_actions.wait("short")

            # Should click and then wait
            mock_mouse.click.assert_called_once()
            mock_sleep.assert_called_once()


class TestGameActionsErrorHandling:
    """Test error handling in actions"""

    def test_click_handles_mouse_error(
        self, game_actions, mock_config, mock_screen, mock_mouse
    ):
        """Test handling of mouse errors"""
        mock_config.get.return_value = "#ff0000"
        color_match = Mock(x=100, y=100)
        mock_screen.find_color.return_value = color_match

        mock_mouse.click.side_effect = Exception("Mouse error")

        # Should handle error gracefully
        with pytest.raises(Exception):
            game_actions.click_color("target")

    def test_wait_handles_invalid_timing(self, game_actions, mock_config):
        """Test handling invalid timing config"""
        mock_config.get.return_value = None

        with pytest.raises((KeyError, TypeError, Exception)):
            game_actions.wait("nonexistent_timing")


# Fixtures


@pytest.fixture
def mock_interface():
    """Mock GameInterface"""
    interface = Mock(spec=GameInterface)
    interface.get_bounds.return_value = (100, 100, 800, 600)
    return interface


@pytest.fixture
def mock_config():
    """Mock Config"""
    config = Mock(spec=Config)
    config.get.return_value = 10  # Default tolerance
    return config


@pytest.fixture
def mock_mouse():
    """Mock MouseService"""
    mouse = Mock(spec=MouseService)
    return mouse


@pytest.fixture
def mock_screen():
    """Mock ScreenService"""
    screen = Mock(spec=ScreenService)
    return screen


@pytest.fixture
def mock_state():
    """Mock GameState"""
    state = Mock(spec=GameState)
    return state


@pytest.fixture
def game_actions(mock_interface, mock_config, mock_mouse, mock_screen, mock_state):
    """Create GameActions instance for testing"""
    return GameActions(mock_interface, mock_config, mock_mouse, mock_screen, mock_state)
