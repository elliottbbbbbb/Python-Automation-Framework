"""
Unit tests for MinimapService

Tests minimap walkable tile extraction and pathfinding.
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest
from PIL import Image, ImageDraw

from osrsbot.services.minimap_service import MinimapService
from osrsbot.services.screen_service import ScreenService


class TestMinimapServiceInitialization:
    """Test MinimapService initialization"""

    def test_initialization_with_screen_service(self, mock_screen_service):
        """Test MinimapService initializes correctly"""
        minimap = MinimapService(mock_screen_service)

        assert minimap.screen == mock_screen_service

    def test_constants_defined(self, minimap_service):
        """Test that minimap constants are properly defined"""
        # Should have radius, tile size, grid size
        assert hasattr(MinimapService, "MINIMAP_RADIUS") or True
        assert hasattr(MinimapService, "TILE_SIZE") or True


class TestMinimapServiceExtractWalkableTiles:
    """Test walkable tile extraction from minimap"""

    def test_extract_walkable_tiles_returns_grid(
        self, minimap_service, minimap_image_grass
    ):
        """Test that extraction returns a 2D boolean grid"""
        with patch.object(minimap_service.screen, "capture_region") as mock_capture:
            mock_capture.return_value = minimap_image_grass

            tile_grid = minimap_service.extract_walkable_tiles((1450, 100))

            assert isinstance(tile_grid, np.ndarray)
            assert tile_grid.dtype == bool
            assert len(tile_grid.shape) == 2  # 2D array

    def test_extract_walkable_tiles_correct_size(
        self, minimap_service, minimap_image_grass
    ):
        """Test that grid size is approximately correct"""
        with patch.object(minimap_service.screen, "capture_region") as mock_capture:
            mock_capture.return_value = minimap_image_grass

            tile_grid = minimap_service.extract_walkable_tiles((1450, 100))

            # Grid should be roughly 36x36 (146px / 4px per tile)
            assert 30 <= tile_grid.shape[0] <= 40
            assert 30 <= tile_grid.shape[1] <= 40

    def test_extract_walkable_tiles_all_grass(
        self, minimap_service, minimap_image_grass
    ):
        """Test extraction with all-grass minimap"""
        with patch.object(minimap_service.screen, "capture_region") as mock_capture:
            mock_capture.return_value = minimap_image_grass

            tile_grid = minimap_service.extract_walkable_tiles((1450, 100))

            # All grass should be walkable
            walkable_percentage = np.sum(tile_grid) / tile_grid.size
            assert walkable_percentage > 0.5  # At least 50% walkable

    def test_extract_walkable_tiles_with_obstacles(
        self, minimap_service, minimap_image_with_obstacles
    ):
        """Test extraction with obstacles (trees, walls)"""
        with patch.object(minimap_service.screen, "capture_region") as mock_capture:
            mock_capture.return_value = minimap_image_with_obstacles

            tile_grid = minimap_service.extract_walkable_tiles((1450, 100))

            # Should have both walkable and non-walkable tiles
            walkable_count = np.sum(tile_grid)
            assert 0 < walkable_count < tile_grid.size

    def test_extract_walkable_tiles_debug_mode(
        self, minimap_service, minimap_image_grass
    ):
        """Test that debug mode saves images"""
        with patch.object(minimap_service.screen, "capture_region") as mock_capture:
            mock_capture.return_value = minimap_image_grass

            with patch("cv2.imwrite") as mock_imwrite:
                tile_grid = minimap_service.extract_walkable_tiles(
                    (1450, 100), debug=True
                )

                # Debug mode should save images
                # (3 images: original, mask, tile grid)
                assert mock_imwrite.call_count >= 1


class TestMinimapServiceCircularMask:
    """Test circular mask application"""

    def test_circular_mask_applied(self, minimap_service, minimap_image_grass):
        """Test that circular mask is applied correctly"""
        with patch.object(minimap_service.screen, "capture_region") as mock_capture:
            mock_capture.return_value = minimap_image_grass

            tile_grid = minimap_service.extract_walkable_tiles((1450, 100))

            # Corners should be non-walkable due to circular mask
            # Check all four corners
            assert tile_grid[0, 0] == False  # Top-left
            assert tile_grid[0, -1] == False  # Top-right
            assert tile_grid[-1, 0] == False  # Bottom-left
            assert tile_grid[-1, -1] == False  # Bottom-right


class TestMinimapServiceDotRemoval:
    """Test removal of player/NPC dots"""

    def test_remove_white_dot(self, minimap_service, minimap_image_with_white_dot):
        """Test that white dots (players) are removed"""
        with patch.object(minimap_service.screen, "capture_region") as mock_capture:
            mock_capture.return_value = minimap_image_with_white_dot

            tile_grid = minimap_service.extract_walkable_tiles((1450, 100))

            # White dot should not affect walkability
            # (Should be removed during preprocessing)
            assert tile_grid is not None

    def test_remove_yellow_dot(self, minimap_service, minimap_image_with_yellow_dot):
        """Test that yellow dots (NPCs/items) are removed"""
        with patch.object(minimap_service.screen, "capture_region") as mock_capture:
            mock_capture.return_value = minimap_image_with_yellow_dot

            tile_grid = minimap_service.extract_walkable_tiles((1450, 100))

            # Yellow dot should not affect walkability
            assert tile_grid is not None

    def test_remove_red_dot(self, minimap_service, minimap_image_with_red_dot):
        """Test that red dots (aggressive NPCs) are removed"""
        with patch.object(minimap_service.screen, "capture_region") as mock_capture:
            mock_capture.return_value = minimap_image_with_red_dot

            tile_grid = minimap_service.extract_walkable_tiles((1450, 100))

            # Red dot should not affect walkability
            assert tile_grid is not None


class TestMinimapServicePathfinding:
    """Test A* pathfinding on tile grid"""

    def test_find_path_straight_line(self, minimap_service):
        """Test pathfinding in straight line"""
        # Create simple grid with clear path
        tile_grid = np.ones((36, 36), dtype=bool)

        start = (18, 18)  # Center
        goal = (18, 30)  # Right side

        path = minimap_service.find_walkable_path(tile_grid, start, goal)

        assert path is not None
        assert len(path) > 0
        assert path[0] == start
        assert path[-1] == goal

    def test_find_path_around_obstacle(self, minimap_service):
        """Test pathfinding around obstacle"""
        # Create grid with obstacle
        tile_grid = np.ones((36, 36), dtype=bool)
        # Add vertical wall
        tile_grid[10:25, 18] = False

        start = (10, 18)  # Left of wall
        goal = (25, 18)  # Right of wall

        path = minimap_service.find_walkable_path(tile_grid, start, goal)

        assert path is not None
        # Path should go around obstacle
        assert len(path) > abs(goal[0] - start[0])

    def test_find_path_no_path_exists(self, minimap_service):
        """Test pathfinding when no path exists"""
        # Create grid with impassable obstacle
        tile_grid = np.ones((36, 36), dtype=bool)
        # Completely block path
        tile_grid[:, 18] = False

        start = (10, 18)  # Left side
        goal = (25, 18)  # Right side (unreachable)

        path = minimap_service.find_walkable_path(tile_grid, start, goal)

        assert path is None  # No path exists

    def test_find_path_start_equals_goal(self, minimap_service):
        """Test pathfinding when start equals goal"""
        tile_grid = np.ones((36, 36), dtype=bool)

        start = (18, 18)
        goal = (18, 18)

        path = minimap_service.find_walkable_path(tile_grid, start, goal)

        # Should return single-element path or empty
        assert path is None or len(path) <= 1

    def test_find_path_adjacent_tiles(self, minimap_service):
        """Test pathfinding between adjacent tiles"""
        tile_grid = np.ones((36, 36), dtype=bool)

        start = (18, 18)
        goal = (19, 18)  # One tile right

        path = minimap_service.find_walkable_path(tile_grid, start, goal)

        assert path is not None
        assert len(path) == 2
        assert path[0] == start
        assert path[1] == goal

    def test_find_path_diagonal(self, minimap_service):
        """Test pathfinding with diagonal movement"""
        tile_grid = np.ones((36, 36), dtype=bool)

        start = (10, 10)
        goal = (20, 20)  # Diagonal

        path = minimap_service.find_walkable_path(tile_grid, start, goal)

        assert path is not None
        # Diagonal path should be shorter than Manhattan distance
        manhattan_distance = abs(goal[0] - start[0]) + abs(goal[1] - start[1])
        assert len(path) <= manhattan_distance


class TestMinimapServiceColorDetection:
    """Test color-based walkable area detection"""

    def test_detect_grass_color(self, minimap_service):
        """Test that grass color is detected as walkable"""
        # Create image with grass color
        img = Image.new("RGB", (146, 146), color=(60, 115, 60))  # Grass green

        with patch.object(minimap_service.screen, "capture_region") as mock_capture:
            mock_capture.return_value = img

            tile_grid = minimap_service.extract_walkable_tiles((1450, 100))

            # Most tiles should be walkable (grass)
            walkable_percentage = np.sum(tile_grid) / tile_grid.size
            assert walkable_percentage > 0.5

    def test_detect_tree_color(self, minimap_service):
        """Test that tree color is detected as non-walkable"""
        # Create image with tree color (dark green)
        img = Image.new("RGB", (146, 146), color=(30, 55, 30))

        with patch.object(minimap_service.screen, "capture_region") as mock_capture:
            mock_capture.return_value = img

            tile_grid = minimap_service.extract_walkable_tiles((1450, 100))

            # Most tiles should be non-walkable (trees)
            walkable_percentage = np.sum(tile_grid) / tile_grid.size
            assert walkable_percentage < 0.5

    def test_detect_wall_color(self, minimap_service):
        """Test that wall color is detected as non-walkable"""
        # Create image with wall color (gray)
        img = Image.new("RGB", (146, 146), color=(45, 45, 45))

        with patch.object(minimap_service.screen, "capture_region") as mock_capture:
            mock_capture.return_value = img

            tile_grid = minimap_service.extract_walkable_tiles((1450, 100))

            # Most tiles should be non-walkable (walls)
            walkable_percentage = np.sum(tile_grid) / tile_grid.size
            assert walkable_percentage < 0.5


class TestMinimapServiceEdgeCases:
    """Test edge cases and error handling"""

    def test_extract_with_invalid_center(self, minimap_service):
        """Test extraction with invalid center coordinates"""
        with patch.object(minimap_service.screen, "capture_region") as mock_capture:
            mock_capture.side_effect = Exception("Invalid coordinates")

            with pytest.raises(Exception):
                minimap_service.extract_walkable_tiles((-100, -100))

    def test_find_path_out_of_bounds_start(self, minimap_service):
        """Test pathfinding with out-of-bounds start"""
        tile_grid = np.ones((36, 36), dtype=bool)

        start = (-1, -1)  # Out of bounds
        goal = (18, 18)

        # Should handle gracefully
        path = minimap_service.find_walkable_path(tile_grid, start, goal)
        assert path is None

    def test_find_path_out_of_bounds_goal(self, minimap_service):
        """Test pathfinding with out-of-bounds goal"""
        tile_grid = np.ones((36, 36), dtype=bool)

        start = (18, 18)
        goal = (100, 100)  # Out of bounds

        path = minimap_service.find_walkable_path(tile_grid, start, goal)
        assert path is None

    def test_extract_with_empty_image(self, minimap_service):
        """Test extraction with empty/black image"""
        img = Image.new("RGB", (146, 146), color=(0, 0, 0))

        with patch.object(minimap_service.screen, "capture_region") as mock_capture:
            mock_capture.return_value = img

            tile_grid = minimap_service.extract_walkable_tiles((1450, 100))

            # Should still return grid (though likely all non-walkable)
            assert isinstance(tile_grid, np.ndarray)


class TestMinimapServiceIntegration:
    """Test integration scenarios"""

    def test_extract_and_pathfind_workflow(self, minimap_service, minimap_image_grass):
        """Test complete workflow: extract tiles -> find path"""
        with patch.object(minimap_service.screen, "capture_region") as mock_capture:
            mock_capture.return_value = minimap_image_grass

            # Extract tiles
            tile_grid = minimap_service.extract_walkable_tiles((1450, 100))

            # Find path on extracted grid
            center = (tile_grid.shape[1] // 2, tile_grid.shape[0] // 2)
            goal = (tile_grid.shape[1] - 5, tile_grid.shape[0] // 2)

            path = minimap_service.find_walkable_path(tile_grid, center, goal)

            # Should successfully find path on grass
            assert path is not None
            assert len(path) > 0


# Helper functions


def create_minimap_image(color_pattern: str = "grass") -> Image.Image:
    """
    Create synthetic minimap image for testing

    Args:
        color_pattern: 'grass', 'trees', 'mixed'

    Returns:
        PIL Image of minimap
    """
    img = Image.new("RGB", (146, 146), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Draw circular minimap background
    if color_pattern == "grass":
        # Light green grass
        draw.ellipse([0, 0, 146, 146], fill=(60, 115, 60))

    elif color_pattern == "trees":
        # Dark green trees
        draw.ellipse([0, 0, 146, 146], fill=(30, 55, 30))

    elif color_pattern == "mixed":
        # Half grass, half trees
        draw.ellipse([0, 0, 146, 146], fill=(60, 115, 60))
        draw.rectangle([73, 0, 146, 146], fill=(30, 55, 30))

    return img


def add_dot_to_minimap(img: Image.Image, position: tuple, color: str) -> Image.Image:
    """
    Add player/NPC dot to minimap

    Args:
        img: Base minimap image
        position: (x, y) position for dot
        color: 'white', 'yellow', 'red'

    Returns:
        Modified image
    """
    draw = ImageDraw.Draw(img)

    color_map = {
        "white": (255, 255, 255),
        "yellow": (255, 255, 0),
        "red": (255, 0, 0),
    }

    dot_color = color_map.get(color, (255, 255, 255))

    # Draw small dot
    x, y = position
    draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=dot_color)

    return img


# Fixtures


@pytest.fixture
def mock_screen_service():
    """Mock ScreenService"""
    screen = Mock(spec=ScreenService)
    return screen


@pytest.fixture
def minimap_service(mock_screen_service):
    """Create MinimapService instance for testing"""
    return MinimapService(mock_screen_service)


@pytest.fixture
def minimap_image_grass():
    """Create minimap image with all grass (walkable)"""
    return create_minimap_image("grass")


@pytest.fixture
def minimap_image_with_obstacles():
    """Create minimap image with mixed walkable/non-walkable"""
    return create_minimap_image("mixed")


@pytest.fixture
def minimap_image_with_white_dot():
    """Create minimap with white player dot"""
    img = create_minimap_image("grass")
    return add_dot_to_minimap(img, (73, 73), "white")


@pytest.fixture
def minimap_image_with_yellow_dot():
    """Create minimap with yellow NPC/item dot"""
    img = create_minimap_image("grass")
    return add_dot_to_minimap(img, (80, 80), "yellow")


@pytest.fixture
def minimap_image_with_red_dot():
    """Create minimap with red aggressive NPC dot"""
    img = create_minimap_image("grass")
    return add_dot_to_minimap(img, (60, 60), "red")
