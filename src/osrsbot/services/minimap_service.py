"""
MinimapService - Convert minimap to walkable tile grid

Analyzes the OSRS minimap to identify walkable tiles using computer vision.
"""

import cv2
import numpy as np
from PIL import Image
from typing import Tuple, List, Optional
import logging

logger = logging.getLogger(__name__)


class MinimapService:
    """Service for analyzing minimap and extracting walkable tiles"""

    # OSRS minimap colors (BGR format for OpenCV)
    WALKABLE_COLORS = {
        'grass': [(40, 80, 40), (80, 150, 80)],      # Light green grass
        'path': [(60, 60, 40), (100, 100, 70)],      # Brown/tan paths
        'sand': [(100, 150, 180), (140, 190, 220)],  # Sandy areas
        'floor': [(40, 40, 30), (70, 70, 60)],       # Indoor floors
    }

    NON_WALKABLE_COLORS = {
        'tree': [(20, 40, 20), (40, 70, 40)],        # Dark green trees
        'wall': [(30, 30, 30), (60, 60, 60)],        # Gray walls
        'water': [(80, 40, 20), (120, 80, 40)],      # Blue water
        'rock': [(40, 40, 40), (70, 70, 70)],        # Gray rocks
    }

    # Minimap properties
    MINIMAP_RADIUS = 73  # Radius of minimap circle in pixels
    TILE_SIZE = 4  # Approximate pixels per tile on minimap
    GRID_SIZE = 104  # Number of tiles visible (52x52 grid, but circular)

    def __init__(self, screen_service):
        """
        Initialize MinimapService

        Args:
            screen_service: ScreenService for capturing minimap
        """
        self.screen = screen_service

    def get_minimap_image(self, minimap_center: Tuple[int, int]) -> np.ndarray:
        """
        Capture the minimap region

        Args:
            minimap_center: (x, y) center of minimap on screen

        Returns:
            Minimap image as numpy array (BGR)
        """
        x, y = minimap_center
        radius = self.MINIMAP_RADIUS

        # Capture square region around minimap
        region = (
            x - radius,
            y - radius,
            x + radius,
            y + radius
        )

        screenshot = self.screen.capture_region(region)
        minimap_img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        return minimap_img

    def extract_walkable_tiles(
        self,
        minimap_center: Tuple[int, int],
        debug: bool = False
    ) -> np.ndarray:
        """
        Extract walkable tiles from minimap

        Args:
            minimap_center: (x, y) center of minimap on screen
            debug: If True, save debug images

        Returns:
            2D boolean array where True = walkable, False = non-walkable
            Shape: (grid_height, grid_width)
        """
        # Get minimap image
        minimap_img = self.get_minimap_image(minimap_center)

        # Create circular mask (minimap is circular)
        mask = self._create_circular_mask(minimap_img.shape[:2])

        # Apply mask to minimap
        minimap_masked = cv2.bitwise_and(minimap_img, minimap_img, mask=mask)

        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(minimap_masked, cv2.COLOR_BGR2HSV)

        # Detect walkable areas
        walkable_mask = self._detect_walkable_areas(minimap_masked, hsv)

        # Remove dots (players, NPCs, items)
        walkable_mask = self._remove_dots(walkable_mask, minimap_masked)

        # Convert to tile grid
        tile_grid = self._create_tile_grid(walkable_mask, mask)

        if debug:
            self._save_debug_images(minimap_img, walkable_mask, tile_grid)

        return tile_grid

    def _create_circular_mask(self, shape: Tuple[int, int]) -> np.ndarray:
        """
        Create circular mask for minimap

        Args:
            shape: (height, width) of image

        Returns:
            Binary mask (255 inside circle, 0 outside)
        """
        h, w = shape
        center = (w // 2, h // 2)
        radius = self.MINIMAP_RADIUS

        # Create mask
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, center, radius, 255, -1)

        return mask

    def _detect_walkable_areas(
        self,
        minimap_bgr: np.ndarray,
        minimap_hsv: np.ndarray
    ) -> np.ndarray:
        """
        Detect walkable areas based on color

        Args:
            minimap_bgr: Minimap in BGR format
            minimap_hsv: Minimap in HSV format

        Returns:
            Binary mask of walkable areas
        """
        h, w = minimap_bgr.shape[:2]
        walkable_mask = np.zeros((h, w), dtype=np.uint8)

        # Method 1: Color range detection for walkable areas
        for terrain_type, (lower, upper) in self.WALKABLE_COLORS.items():
            lower_bound = np.array(lower, dtype=np.uint8)
            upper_bound = np.array(upper, dtype=np.uint8)

            # Create mask for this terrain type
            terrain_mask = cv2.inRange(minimap_bgr, lower_bound, upper_bound)

            # Add to walkable mask
            walkable_mask = cv2.bitwise_or(walkable_mask, terrain_mask)

        # Method 2: Brightness-based detection
        # Walkable areas are generally brighter on minimap
        gray = cv2.cvtColor(minimap_bgr, cv2.COLOR_BGR2GRAY)
        _, bright_mask = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY)

        # Combine color-based and brightness-based
        walkable_mask = cv2.bitwise_or(walkable_mask, bright_mask)

        # Remove non-walkable areas
        for obstacle_type, (lower, upper) in self.NON_WALKABLE_COLORS.items():
            lower_bound = np.array(lower, dtype=np.uint8)
            upper_bound = np.array(upper, dtype=np.uint8)

            obstacle_mask = cv2.inRange(minimap_bgr, lower_bound, upper_bound)

            # Subtract obstacles from walkable
            walkable_mask = cv2.subtract(walkable_mask, obstacle_mask)

        # Clean up with morphological operations
        kernel = np.ones((3, 3), np.uint8)
        walkable_mask = cv2.morphologyEx(walkable_mask, cv2.MORPH_CLOSE, kernel)
        walkable_mask = cv2.morphologyEx(walkable_mask, cv2.MORPH_OPEN, kernel)

        return walkable_mask

    def _remove_dots(
        self,
        walkable_mask: np.ndarray,
        minimap_bgr: np.ndarray
    ) -> np.ndarray:
        """
        Remove dots (players, NPCs, items) from walkable mask

        Dots are typically:
        - White (players)
        - Yellow (items, NPCs)
        - Red (aggressive NPCs)
        - Cyan (friends)

        Args:
            walkable_mask: Current walkable mask
            minimap_bgr: Original minimap image

        Returns:
            Walkable mask with dots removed
        """
        # Define dot colors (BGR)
        dot_colors = [
            ([200, 200, 200], [255, 255, 255]),  # White (players)
            ([0, 200, 200], [100, 255, 255]),    # Yellow (NPCs/items)
            ([0, 0, 200], [100, 100, 255]),      # Red (aggressive)
            ([200, 200, 0], [255, 255, 100]),    # Cyan (friends)
        ]

        dots_mask = np.zeros_like(walkable_mask)

        for lower, upper in dot_colors:
            lower_bound = np.array(lower, dtype=np.uint8)
            upper_bound = np.array(upper, dtype=np.uint8)

            dot_mask = cv2.inRange(minimap_bgr, lower_bound, upper_bound)
            dots_mask = cv2.bitwise_or(dots_mask, dot_mask)

        # Dilate dots slightly to ensure full removal
        kernel = np.ones((3, 3), np.uint8)
        dots_mask = cv2.dilate(dots_mask, kernel, iterations=1)

        # Remove dots from walkable mask
        walkable_mask = cv2.subtract(walkable_mask, dots_mask)

        return walkable_mask

    def _create_tile_grid(
        self,
        walkable_mask: np.ndarray,
        circular_mask: np.ndarray
    ) -> np.ndarray:
        """
        Convert pixel mask to tile grid

        Each tile is TILE_SIZE x TILE_SIZE pixels

        Args:
            walkable_mask: Pixel-level walkable mask
            circular_mask: Circular mask for minimap

        Returns:
            2D boolean array of walkable tiles
        """
        h, w = walkable_mask.shape
        tile_size = self.TILE_SIZE

        # Calculate grid dimensions
        grid_h = h // tile_size
        grid_w = w // tile_size

        # Create tile grid
        tile_grid = np.zeros((grid_h, grid_w), dtype=bool)

        for i in range(grid_h):
            for j in range(grid_w):
                # Get tile region
                y1 = i * tile_size
                y2 = (i + 1) * tile_size
                x1 = j * tile_size
                x2 = (j + 1) * tile_size

                # Extract tile from walkable mask
                tile_pixels = walkable_mask[y1:y2, x1:x2]
                circular_pixels = circular_mask[y1:y2, x1:x2]

                # Check if tile is within minimap circle
                if np.sum(circular_pixels) == 0:
                    tile_grid[i, j] = False
                    continue

                # Tile is walkable if >50% of pixels are walkable
                walkable_pixels = np.sum(tile_pixels > 0)
                total_pixels = tile_size * tile_size

                tile_grid[i, j] = (walkable_pixels / total_pixels) > 0.5

        return tile_grid

    def get_tile_at_position(
        self,
        tile_grid: np.ndarray,
        world_position: Tuple[int, int]
    ) -> bool:
        """
        Check if specific world position is walkable

        Args:
            tile_grid: 2D walkable tile grid
            world_position: (x, y) position in world coordinates

        Returns:
            True if walkable, False otherwise
        """
        # Convert world position to grid coordinates
        # (Implementation depends on your coordinate system)
        grid_x = world_position[0] % tile_grid.shape[1]
        grid_y = world_position[1] % tile_grid.shape[0]

        return tile_grid[grid_y, grid_x]

    def find_walkable_path(
        self,
        tile_grid: np.ndarray,
        start: Tuple[int, int],
        goal: Tuple[int, int]
    ) -> Optional[List[Tuple[int, int]]]:
        """
        Find path from start to goal using A* pathfinding

        Args:
            tile_grid: 2D walkable tile grid
            start: (x, y) start position in grid coordinates
            goal: (x, y) goal position in grid coordinates

        Returns:
            List of (x, y) positions representing path, or None if no path
        """
        from collections import deque
        import heapq

        def heuristic(a, b):
            """Manhattan distance heuristic"""
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        def get_neighbors(pos):
            """Get walkable neighbors (4-directional)"""
            x, y = pos
            neighbors = []

            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy

                # Check bounds
                if 0 <= nx < tile_grid.shape[1] and 0 <= ny < tile_grid.shape[0]:
                    # Check walkable
                    if tile_grid[ny, nx]:
                        neighbors.append((nx, ny))

            return neighbors

        # A* algorithm
        open_set = []
        heapq.heappush(open_set, (0, start))

        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start, goal)}

        while open_set:
            current = heapq.heappop(open_set)[1]

            if current == goal:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return list(reversed(path))

            for neighbor in get_neighbors(current):
                tentative_g = g_score[current] + 1

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + heuristic(neighbor, goal)

                    if neighbor not in [item[1] for item in open_set]:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return None  # No path found

    def _save_debug_images(
        self,
        minimap_img: np.ndarray,
        walkable_mask: np.ndarray,
        tile_grid: np.ndarray
    ):
        """Save debug images for visualization"""
        import os

        debug_dir = "debug/minimap"
        os.makedirs(debug_dir, exist_ok=True)

        # Save original minimap
        cv2.imwrite(f"{debug_dir}/minimap_original.png", minimap_img)

        # Save walkable mask
        cv2.imwrite(f"{debug_dir}/minimap_walkable_mask.png", walkable_mask)

        # Visualize tile grid
        tile_vis = self._visualize_tile_grid(minimap_img, tile_grid)
        cv2.imwrite(f"{debug_dir}/minimap_tile_grid.png", tile_vis)

        logger.info(f"Debug images saved to {debug_dir}/")

    def _visualize_tile_grid(
        self,
        minimap_img: np.ndarray,
        tile_grid: np.ndarray
    ) -> np.ndarray:
        """
        Create visualization of tile grid overlay on minimap

        Args:
            minimap_img: Original minimap image
            tile_grid: Boolean grid of walkable tiles

        Returns:
            Visualization image
        """
        vis = minimap_img.copy()
        h, w = vis.shape[:2]
        tile_size = self.TILE_SIZE

        # Draw grid
        for i in range(tile_grid.shape[0]):
            for j in range(tile_grid.shape[1]):
                y1 = i * tile_size
                y2 = (i + 1) * tile_size
                x1 = j * tile_size
                x2 = (j + 1) * tile_size

                # Color based on walkability
                if tile_grid[i, j]:
                    color = (0, 255, 0)  # Green for walkable
                    cv2.rectangle(vis, (x1, y1), (x2, y2), color, 1)
                else:
                    color = (0, 0, 255)  # Red for non-walkable
                    cv2.rectangle(vis, (x1, y1), (x2, y2), color, 1)

        return vis
