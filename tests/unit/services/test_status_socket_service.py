"""Unit tests for StatusSocketService."""
import json
import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from osrsbot.services.status_socket_service import StatusSocketService, PlayerState


class TestStatusSocketService:
    """Test StatusSocketService functionality."""

    @pytest.fixture
    def valid_json_data(self):
        """Sample valid Status Socket JSON data."""
        return {
            "worldPoint": {"x": 3200, "y": 3400, "plane": 0},
            "camera": {"yaw": 512, "pitch": 256},
            "isMoving": False,
            "animation": -1
        }

    @pytest.fixture
    def mock_file_path(self, tmp_path):
        """Create a temporary file path for testing."""
        return tmp_path / "live_data.json"

    def test_get_player_state_file_not_found(self, mock_file_path):
        """Test graceful handling when file doesn't exist."""
        service = StatusSocketService(data_file=str(mock_file_path))

        state = service.get_player_state()

        assert state is None
        assert service._file_unavailable_warned is True

    def test_get_player_state_valid_data(self, mock_file_path, valid_json_data):
        """Test parsing valid JSON data."""
        # Write valid JSON to file
        with open(mock_file_path, 'w') as f:
            json.dump(valid_json_data, f)

        service = StatusSocketService(data_file=str(mock_file_path))
        state = service.get_player_state()

        assert state is not None
        assert state.world_x == 3200
        assert state.world_y == 3400
        assert state.plane == 0
        assert state.camera_yaw == 512
        assert state.is_moving is False
        assert state.animation_id == -1
        assert state.timestamp > 0

    def test_get_player_state_caching(self, mock_file_path, valid_json_data):
        """Test that state is cached when file hasn't changed."""
        # Write initial data
        with open(mock_file_path, 'w') as f:
            json.dump(valid_json_data, f)

        service = StatusSocketService(data_file=str(mock_file_path))

        # First read
        state1 = service.get_player_state()
        timestamp1 = state1.timestamp

        # Small delay
        time.sleep(0.01)

        # Second read (file unchanged)
        state2 = service.get_player_state()

        # Should return same cached state
        assert state1 is state2
        assert state2.timestamp == timestamp1

    def test_get_player_state_file_updated(self, mock_file_path, valid_json_data):
        """Test that new data is read when file is modified."""
        # Write initial data
        with open(mock_file_path, 'w') as f:
            json.dump(valid_json_data, f)

        service = StatusSocketService(data_file=str(mock_file_path))
        state1 = service.get_player_state()

        # Modify file
        time.sleep(0.01)  # Ensure different mtime
        valid_json_data["worldPoint"]["x"] = 3250
        with open(mock_file_path, 'w') as f:
            json.dump(valid_json_data, f)

        # Read again
        state2 = service.get_player_state()

        assert state2.world_x == 3250
        assert state1 is not state2

    def test_get_player_state_invalid_json(self, mock_file_path):
        """Test handling of corrupted JSON."""
        # Write invalid JSON
        with open(mock_file_path, 'w') as f:
            f.write("{invalid json")

        service = StatusSocketService(data_file=str(mock_file_path))
        state = service.get_player_state()

        # Should return None and log warning
        assert state is None

    def test_get_player_state_invalid_json_with_cache(self, mock_file_path, valid_json_data):
        """Test that cache is used when JSON becomes corrupted."""
        # Write valid data first
        with open(mock_file_path, 'w') as f:
            json.dump(valid_json_data, f)

        service = StatusSocketService(data_file=str(mock_file_path))
        state1 = service.get_player_state()
        assert state1 is not None

        # Corrupt the file
        time.sleep(0.01)
        with open(mock_file_path, 'w') as f:
            f.write("{corrupt")

        # Should return last known good state
        state2 = service.get_player_state()
        assert state2 is state1
        assert state2.world_x == 3200

    def test_is_available_when_file_exists(self, mock_file_path, valid_json_data):
        """Test is_available returns True when plugin active."""
        with open(mock_file_path, 'w') as f:
            json.dump(valid_json_data, f)

        service = StatusSocketService(data_file=str(mock_file_path))

        assert service.is_available() is True

    def test_is_available_when_file_missing(self, mock_file_path):
        """Test is_available returns False when file missing."""
        service = StatusSocketService(data_file=str(mock_file_path))

        assert service.is_available() is False

    def test_is_available_detects_stale_data(self, mock_file_path, valid_json_data):
        """Test is_available returns False when data is stale."""
        with open(mock_file_path, 'w') as f:
            json.dump(valid_json_data, f)

        service = StatusSocketService(data_file=str(mock_file_path))
        service._stale_data_threshold = 0.1  # 100ms threshold for testing

        # Get initial state
        state = service.get_player_state()
        assert state is not None

        # Manually set old timestamp
        state.timestamp = time.time() - 1.0  # 1 second ago

        # Should detect stale data
        assert service.is_available() is False

    def test_wait_for_arrival_success(self, mock_file_path, valid_json_data):
        """Test successful arrival at target."""
        # Player starts at (3200, 3400)
        with open(mock_file_path, 'w') as f:
            json.dump(valid_json_data, f)

        service = StatusSocketService(data_file=str(mock_file_path), poll_interval=0.01)

        # Simulate player arriving at target after 2 updates
        def update_position():
            time.sleep(0.02)
            valid_json_data["worldPoint"]["x"] = 3202
            valid_json_data["worldPoint"]["y"] = 3402
            with open(mock_file_path, 'w') as f:
                json.dump(valid_json_data, f)

        import threading
        updater = threading.Thread(target=update_position)
        updater.start()

        # Wait for arrival at (3202, 3402) with tolerance 2
        result = service.wait_for_arrival(3202, 3402, tolerance=2, timeout=1.0)

        updater.join()
        assert result is True

    def test_wait_for_arrival_timeout(self, mock_file_path, valid_json_data):
        """Test timeout when player doesn't arrive."""
        with open(mock_file_path, 'w') as f:
            json.dump(valid_json_data, f)

        service = StatusSocketService(data_file=str(mock_file_path), poll_interval=0.01)

        # Try to reach distant target
        result = service.wait_for_arrival(5000, 5000, tolerance=2, timeout=0.1)

        assert result is False

    def test_wait_for_arrival_stuck_detection(self, mock_file_path, valid_json_data):
        """Test detection of stuck player."""
        with open(mock_file_path, 'w') as f:
            json.dump(valid_json_data, f)

        service = StatusSocketService(data_file=str(mock_file_path), poll_interval=0.01)

        # Player stays at same position
        result = service.wait_for_arrival(3210, 3410, tolerance=2, timeout=1.0)

        # Should detect stuck and return False
        assert result is False

    def test_wait_for_arrival_plugin_disconnects(self, mock_file_path, valid_json_data):
        """Test handling when plugin disconnects during wait."""
        with open(mock_file_path, 'w') as f:
            json.dump(valid_json_data, f)

        service = StatusSocketService(data_file=str(mock_file_path), poll_interval=0.01)

        # Delete file after first read to simulate plugin crash
        def delete_file():
            time.sleep(0.02)
            mock_file_path.unlink()

        import threading
        deleter = threading.Thread(target=delete_file)
        deleter.start()

        result = service.wait_for_arrival(3210, 3410, tolerance=2, timeout=1.0)

        deleter.join()
        assert result is False

    def test_calculate_distance(self, mock_file_path):
        """Test distance calculation."""
        service = StatusSocketService(data_file=str(mock_file_path))

        # Same point
        assert service._calculate_distance(0, 0, 0, 0) == 0

        # Horizontal distance
        assert service._calculate_distance(0, 0, 3, 0) == 3

        # Vertical distance
        assert service._calculate_distance(0, 0, 0, 4) == 4

        # Pythagorean (3-4-5 triangle)
        assert service._calculate_distance(0, 0, 3, 4) == 5

    def test_player_state_dataclass(self):
        """Test PlayerState dataclass creation."""
        state = PlayerState(
            world_x=100,
            world_y=200,
            plane=1,
            camera_yaw=1024,
            timestamp=time.time(),
            is_moving=True,
            animation_id=808
        )

        assert state.world_x == 100
        assert state.world_y == 200
        assert state.plane == 1
        assert state.camera_yaw == 1024
        assert state.is_moving is True
        assert state.animation_id == 808

    def test_player_state_defaults(self):
        """Test PlayerState default values."""
        state = PlayerState(
            world_x=100,
            world_y=200,
            plane=0,
            camera_yaw=512,
            timestamp=time.time()
        )

        assert state.is_moving is False
        assert state.animation_id == -1
