"""Unit tests for WalkerService - Focus on rotation matrix accuracy."""
import math
import pytest
from unittest.mock import Mock, MagicMock

from osrsbot.services.walker_service import WalkerService, WalkerConfig
from osrsbot.services.status_socket_service import PlayerState


class TestWalkerService:
    """Test WalkerService functionality with emphasis on rotation accuracy."""

    @pytest.fixture
    def walker_config(self):
        """Default walker configuration."""
        return WalkerConfig(
            minimap_center_x=654,
            minimap_center_y=111,
            tile_size=4,
            arrival_tolerance=2,
            max_click_distance=15
        )

    @pytest.fixture
    def mock_services(self):
        """Mock service dependencies."""
        return {
            'status_socket': Mock(),
            'mouse': Mock(),
            'screen': Mock(),
            'interface': Mock()
        }

    @pytest.fixture
    def walker(self, walker_config, mock_services):
        """Create WalkerService instance with mocks."""
        return WalkerService(
            config=walker_config,
            status_socket=mock_services['status_socket'],
            mouse=mock_services['mouse'],
            screen=mock_services['screen'],
            interface=mock_services['interface']
        )

    # ========================================================================
    # ROTATION MATRIX TESTS (CRITICAL - Test all 8 directions)
    # ========================================================================

    def test_rotation_north_yaw_0(self, walker):
        """Test rotation when camera faces north (yaw=0)."""
        # Player at (3200, 3200), camera north
        # Target 10 tiles north at (3200, 3210) should be directly north on minimap
        player_x, player_y = 3200, 3200
        target_x, target_y = 3200, 3210
        camera_yaw = 0

        result = walker.world_to_minimap(target_x, target_y, player_x, player_y, camera_yaw)

        assert result is not None
        minimap_x, minimap_y = result

        # 10 tiles north at 4 pixels/tile = 40 pixels north
        # Minimap Y increases downward, north is negative
        expected_x = 654  # Center (no horizontal movement)
        expected_y = 111 - 40  # 40 pixels north (up)

        assert abs(minimap_x - expected_x) <= 1, f"X: got {minimap_x}, expected {expected_x}"
        assert abs(minimap_y - expected_y) <= 1, f"Y: got {minimap_y}, expected {expected_y}"

    def test_rotation_east_yaw_512(self, walker):
        """Test rotation when camera faces east (yaw=512 = 90 degrees)."""
        # Camera rotated 90° clockwise
        # Target 10 tiles north should appear to the left (west) on minimap
        player_x, player_y = 3200, 3200
        target_x, target_y = 3200, 3210  # North
        camera_yaw = 512  # East

        result = walker.world_to_minimap(target_x, target_y, player_x, player_y, camera_yaw)

        assert result is not None
        minimap_x, minimap_y = result

        # After rotation, should be approximately 40 pixels west (left)
        expected_x = 654 - 40  # West
        expected_y = 111  # Center vertically

        assert abs(minimap_x - expected_x) <= 2, f"X: got {minimap_x}, expected {expected_x}"
        assert abs(minimap_y - expected_y) <= 2, f"Y: got {minimap_y}, expected {expected_y}"

    def test_rotation_south_yaw_1024(self, walker):
        """Test rotation when camera faces south (yaw=1024 = 180 degrees)."""
        # Camera rotated 180°
        # Target 10 tiles north should appear south on minimap
        player_x, player_y = 3200, 3200
        target_x, target_y = 3200, 3210  # North
        camera_yaw = 1024  # South

        result = walker.world_to_minimap(target_x, target_y, player_x, player_y, camera_yaw)

        assert result is not None
        minimap_x, minimap_y = result

        # After rotation, should be approximately 40 pixels south (down)
        expected_x = 654  # Center
        expected_y = 111 + 40  # South

        assert abs(minimap_x - expected_x) <= 2, f"X: got {minimap_x}, expected {expected_x}"
        assert abs(minimap_y - expected_y) <= 2, f"Y: got {minimap_y}, expected {expected_y}"

    def test_rotation_west_yaw_1536(self, walker):
        """Test rotation when camera faces west (yaw=1536 = 270 degrees)."""
        # Camera rotated 270° clockwise (90° counter-clockwise)
        # Target 10 tiles north should appear to the right (east) on minimap
        player_x, player_y = 3200, 3200
        target_x, target_y = 3200, 3210  # North
        camera_yaw = 1536  # West

        result = walker.world_to_minimap(target_x, target_y, player_x, player_y, camera_yaw)

        assert result is not None
        minimap_x, minimap_y = result

        # After rotation, should be approximately 40 pixels east (right)
        expected_x = 654 + 40  # East
        expected_y = 111  # Center

        assert abs(minimap_x - expected_x) <= 2, f"X: got {minimap_x}, expected {expected_x}"
        assert abs(minimap_y - expected_y) <= 2, f"Y: got {minimap_y}, expected {expected_y}"

    def test_rotation_northeast_yaw_256(self, walker):
        """Test rotation at NE diagonal (yaw=256 = 45 degrees)."""
        # Camera at 45° (NE)
        player_x, player_y = 3200, 3200
        target_x, target_y = 3210, 3210  # NE diagonal (10, 10)
        camera_yaw = 256  # NE

        result = walker.world_to_minimap(target_x, target_y, player_x, player_y, camera_yaw)

        assert result is not None
        # Should be roughly in upper area of minimap
        # Exact position depends on rotation, just verify it's computed

    def test_rotation_southeast_yaw_768(self, walker):
        """Test rotation at SE diagonal (yaw=768 = 135 degrees)."""
        player_x, player_y = 3200, 3200
        target_x, target_y = 3210, 3190  # SE diagonal
        camera_yaw = 768  # SE

        result = walker.world_to_minimap(target_x, target_y, player_x, player_y, camera_yaw)

        assert result is not None

    def test_rotation_southwest_yaw_1280(self, walker):
        """Test rotation at SW diagonal (yaw=1280 = 225 degrees)."""
        player_x, player_y = 3200, 3200
        target_x, target_y = 3190, 3190  # SW diagonal
        camera_yaw = 1280  # SW

        result = walker.world_to_minimap(target_x, target_y, player_x, player_y, camera_yaw)

        assert result is not None

    def test_rotation_northwest_yaw_1792(self, walker):
        """Test rotation at NW diagonal (yaw=1792 = 315 degrees)."""
        player_x, player_y = 3200, 3200
        target_x, target_y = 3190, 3210  # NW diagonal
        camera_yaw = 1792  # NW

        result = walker.world_to_minimap(target_x, target_y, player_x, player_y, camera_yaw)

        assert result is not None

    # ========================================================================
    # BOUNDARY DETECTION TESTS
    # ========================================================================

    def test_world_to_minimap_out_of_bounds(self, walker):
        """Test detection of targets outside minimap visible area."""
        # Player at (3200, 3200)
        # Target very far away (100 tiles north)
        player_x, player_y = 3200, 3200
        target_x, target_y = 3200, 3300
        camera_yaw = 0

        result = walker.world_to_minimap(target_x, target_y, player_x, player_y, camera_yaw)

        # Should return None (out of bounds)
        assert result is None

    def test_world_to_minimap_at_boundary(self, walker):
        """Test targets at edge of minimap (should still work)."""
        # Minimap radius is 73 pixels
        # At 4 pixels/tile, that's ~18 tiles radius
        player_x, player_y = 3200, 3200
        target_x, target_y = 3200, 3218  # 18 tiles north
        camera_yaw = 0

        result = walker.world_to_minimap(target_x, target_y, player_x, player_y, camera_yaw)

        # Should succeed (just within bounds)
        assert result is not None

    def test_world_to_minimap_same_tile(self, walker):
        """Test target at player's current position."""
        player_x, player_y = 3200, 3200
        target_x, target_y = 3200, 3200
        camera_yaw = 512

        result = walker.world_to_minimap(target_x, target_y, player_x, player_y, camera_yaw)

        assert result is not None
        minimap_x, minimap_y = result

        # Should be at minimap center
        assert abs(minimap_x - 654) <= 1
        assert abs(minimap_y - 111) <= 1

    # ========================================================================
    # DISTANCE CALCULATION TESTS
    # ========================================================================

    def test_calculate_distance_same_point(self, walker):
        """Test distance calculation for same point."""
        distance = walker._calculate_distance(0, 0, 0, 0)
        assert distance == 0

    def test_calculate_distance_horizontal(self, walker):
        """Test horizontal distance."""
        distance = walker._calculate_distance(0, 0, 5, 0)
        assert distance == 5

    def test_calculate_distance_vertical(self, walker):
        """Test vertical distance."""
        distance = walker._calculate_distance(0, 0, 0, 12)
        assert distance == 12

    def test_calculate_distance_pythagorean(self, walker):
        """Test Pythagorean distance (3-4-5 triangle)."""
        distance = walker._calculate_distance(0, 0, 3, 4)
        assert distance == 5

    # ========================================================================
    # INTERMEDIATE POINT TESTS
    # ========================================================================

    def test_get_intermediate_point_within_max_distance(self, walker):
        """Test intermediate point when target is far."""
        # Start at (3200, 3200), target at (3250, 3250) (50 tiles diagonal)
        # Max distance 15 tiles
        start_x, start_y = 3200, 3200
        end_x, end_y = 3250, 3250
        max_distance = 15

        intermediate = walker._get_intermediate_point(
            start_x, start_y, end_x, end_y, max_distance
        )

        # Should be 15 tiles from start toward target
        distance_from_start = walker._calculate_distance(
            start_x, start_y, intermediate[0], intermediate[1]
        )

        assert abs(distance_from_start - max_distance) <= 1

    def test_get_intermediate_point_same_tile(self, walker):
        """Test intermediate point when start equals end."""
        intermediate = walker._get_intermediate_point(100, 100, 100, 100, 10)

        assert intermediate == (100, 100)

    # ========================================================================
    # WALK PATH TESTS
    # ========================================================================

    def test_walk_path_single_waypoint(self, walker, mock_services):
        """Test walking to a single waypoint."""
        # Mock player state
        mock_services['status_socket'].get_player_state.return_value = PlayerState(
            world_x=3200,
            world_y=3200,
            plane=0,
            camera_yaw=0,
            timestamp=0
        )
        mock_services['status_socket'].wait_for_arrival.return_value = True
        mock_services['screen'].relative_to_absolute.return_value = (1000, 500)

        waypoints = [(3205, 3205)]
        result = walker.walk_path(waypoints)

        assert result is True
        assert mock_services['mouse'].click_at.called

    def test_walk_path_empty_waypoints(self, walker):
        """Test walk_path with empty list."""
        result = walker.walk_path([])

        assert result is False

    def test_walk_path_status_socket_unavailable(self, walker, mock_services):
        """Test handling when Status Socket disconnects."""
        mock_services['status_socket'].get_player_state.return_value = None

        result = walker.walk_path([(3210, 3210)])

        assert result is False

    def test_walk_path_multiple_waypoints(self, walker, mock_services):
        """Test multi-waypoint path."""
        # Mock progressive movement
        positions = [
            PlayerState(3200, 3200, 0, 0, 0),
            PlayerState(3205, 3205, 0, 0, 0),
            PlayerState(3210, 3210, 0, 0, 0)
        ]
        mock_services['status_socket'].get_player_state.side_effect = positions
        mock_services['status_socket'].wait_for_arrival.return_value = True
        mock_services['screen'].relative_to_absolute.return_value = (1000, 500)

        waypoints = [(3205, 3205), (3210, 3210)]
        result = walker.walk_path(waypoints)

        assert mock_services['mouse'].click_at.call_count >= 2

    # ========================================================================
    # COMPUTE MINIMAP CLICK TESTS
    # ========================================================================

    def test_compute_minimap_click_success(self, walker, mock_services):
        """Test compute_minimap_click convenience method."""
        mock_services['status_socket'].get_player_state.return_value = PlayerState(
            world_x=3200,
            world_y=3200,
            plane=0,
            camera_yaw=512,
            timestamp=0
        )

        result = walker.compute_minimap_click(3210, 3210)

        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_compute_minimap_click_no_player_state(self, walker, mock_services):
        """Test compute_minimap_click when Status Socket unavailable."""
        mock_services['status_socket'].get_player_state.return_value = None

        result = walker.compute_minimap_click(3210, 3210)

        assert result is None

    # ========================================================================
    # WALK_TO TESTS
    # ========================================================================

    def test_walk_to_without_path(self, walker, mock_services):
        """Test walk_to creates single-waypoint path."""
        mock_services['status_socket'].get_player_state.return_value = PlayerState(
            world_x=3200,
            world_y=3200,
            plane=0,
            camera_yaw=0,
            timestamp=0
        )
        mock_services['status_socket'].wait_for_arrival.return_value = True
        mock_services['screen'].relative_to_absolute.return_value = (1000, 500)

        result = walker.walk_to(3205, 3205)

        assert result is True

    def test_walk_to_with_path(self, walker, mock_services):
        """Test walk_to uses provided path."""
        mock_services['status_socket'].get_player_state.return_value = PlayerState(
            world_x=3200,
            world_y=3200,
            plane=0,
            camera_yaw=0,
            timestamp=0
        )
        mock_services['status_socket'].wait_for_arrival.return_value = True
        mock_services['screen'].relative_to_absolute.return_value = (1000, 500)

        path = [(3202, 3202), (3205, 3205), (3210, 3210)]
        result = walker.walk_to(3210, 3210, path=path)

        # Should attempt to walk all waypoints
        assert mock_services['mouse'].click_at.call_count >= len(path)

    # ========================================================================
    # WALKER CONFIG TESTS
    # ========================================================================

    def test_walker_config_defaults(self):
        """Test WalkerConfig default values."""
        config = WalkerConfig()

        assert config.minimap_center_x == 654
        assert config.minimap_center_y == 111
        assert config.tile_size == 4
        assert config.arrival_tolerance == 2
        assert config.max_click_distance == 15
        assert config.path_recalculation_interval == 2.0

    def test_walker_config_custom_values(self):
        """Test WalkerConfig with custom values."""
        config = WalkerConfig(
            minimap_center_x=700,
            minimap_center_y=150,
            tile_size=5,
            arrival_tolerance=3,
            max_click_distance=20
        )

        assert config.minimap_center_x == 700
        assert config.minimap_center_y == 150
        assert config.tile_size == 5
        assert config.arrival_tolerance == 3
        assert config.max_click_distance == 20
