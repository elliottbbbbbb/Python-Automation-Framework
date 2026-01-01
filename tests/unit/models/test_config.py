"""
Unit tests for Config model.

Tests configuration loading, nested access, and defaults.
"""

from unittest.mock import mock_open, patch


from osrsbot.models.config import Config


class TestConfigBasics:
    """Test basic Config functionality."""

    def test_load_from_dict(self, sample_config_dict):
        """Test Config initialization with mocked file."""
        with patch("builtins.open", mock_open(read_data='{"test_key": "test_value"}')):
            with patch("pathlib.Path.exists", return_value=True):
                config = Config("test_config.json")
                assert config.data is not None
                assert isinstance(config.data, dict)

    def test_get_simple_key(self):
        """Test getting a simple top-level key."""
        config = Config.__new__(Config)  # Create without __init__
        config.data = {"test_key": "test_value"}
        assert config.get("test_key") == "test_value"

    def test_get_nested_key(self):
        """Test getting nested keys with path."""
        config = Config.__new__(Config)
        config.data = {"parent": {"child": "value"}}
        assert config.get("parent", "child") == "value"

    def test_get_with_default(self):
        """Test getting missing key returns default."""
        config = Config.__new__(Config)
        config.data = {}
        assert config.get("missing_key", default=10) == 10

    def test_get_missing_no_default(self):
        """Test getting missing key without default returns None."""
        config = Config.__new__(Config)
        config.data = {}
        assert config.get("missing_key") is None


class TestConfigPaths:
    """Test Config nested path access."""

    def test_coordinate_path(self):
        """Test accessing coordinate paths."""
        config = Config.__new__(Config)
        config.data = {"coordinates": {"hp": {"x": 100, "y": 50}}}
        assert config.get("coordinates", "hp", "x") == 100
        assert config.get("coordinates", "hp", "y") == 50

    def test_color_path(self):
        """Test accessing color paths."""
        config = Config.__new__(Config)
        config.data = {"colors": {"combat_red": "#FF0000"}}
        assert config.get("colors", "combat_red") == "#FF0000"

    def test_timing_path(self):
        """Test accessing timing paths."""
        config = Config.__new__(Config)
        config.data = {"timings": {"wait": {"short": [0.1, 0.3]}}}
        result = config.get("timings", "wait", "short")
        assert result == [0.1, 0.3]
