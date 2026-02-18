"""
WalkerService - Coordinate-based pathfinding with camera rotation compensation.

Converts world coordinates to minimap pixels using 2D rotation matrix.
Handles iterative waypoint following for navigation.
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from osrsbot.constants import MovementStyle
from osrsbot.core.game_interface import GameInterface
from osrsbot.services.mouse_service import MouseService
from osrsbot.services.screen_service import ScreenService
from osrsbot.services.coordinate_ocr_service import CoordinateOCRService

logger = logging.getLogger(__name__)


@dataclass
class WalkerConfig:
    """Configuration for walker/pathfinding system."""

    minimap_center_x: int = 654
    minimap_center_y: int = 111
    tile_size: int = 4  # Pixels per tile on minimap
    arrival_tolerance: int = 2  # Tiles within target = success
    max_click_distance: int = 15  # Max tiles to click at once
    path_recalculation_interval: float = 2.0  # Seconds between path updates


class WalkerService:
    """
    World coordinate pathfinding with camera rotation compensation.

    Features:
    - 2D rotation matrix for camera angle compensation
    - World tile to minimap pixel conversion
    - Iterative waypoint following
    - Distance-based click chunking
    - Stuck detection and timeout handling
    """

    def __init__(
        self,
        config: WalkerConfig,
        status_socket: CoordinateOCRService,
        mouse: MouseService,
        screen: ScreenService,
        interface: GameInterface,
    ):
        """
        Initialize walker with required dependencies.

        Args:
            config: Walker configuration
            status_socket: Status socket service for player position/camera
            mouse: Mouse service for clicking
            screen: Screen service for coordinate conversion
            interface: Game interface for window bounds
        """
        self.config = config
        self.status_socket = status_socket
        self.mouse = mouse
        self.screen = screen
        self.interface = interface

        # RuneLite camera constants
        self.runelite_yaw_max = 2048
        self.degrees_per_unit = 360.0 / self.runelite_yaw_max

    def walk_to(
        self,
        target_x: int,
        target_y: int,
        path: Optional[List[Tuple[int, int]]] = None,
        move_style: MovementStyle = "curved",
    ) -> bool:
        """
        Walk to world coordinates.

        Args:
            target_x: Target world X coordinate
            target_y: Target world Y coordinate
            path: Optional waypoint list [(x1,y1), (x2,y2), ...]
            move_style: Mouse movement style for clicks

        Returns:
            True if arrived within tolerance, False on timeout/failure
        """
        if path:
            # Use provided path
            return self.walk_path(path, move_style=move_style)
        else:
            # Direct walk (single waypoint)
            return self.walk_path([(target_x, target_y)], move_style=move_style)

    def walk_path(
        self, waypoints: List[Tuple[int, int]], move_style: MovementStyle = "curved"
    ) -> bool:
        """
        Follow a predefined path of world coordinates.

        Args:
            waypoints: List of (x, y) world coordinates to visit in order
            move_style: Mouse movement style for minimap clicks

        Returns:
            True if completed path successfully, False on failure
        """
        if not waypoints:
            logger.error("walk_path called with empty waypoints list")
            return False

        logger.info(f"Walking path with {len(waypoints)} waypoints")

        for waypoint_idx, (waypoint_x, waypoint_y) in enumerate(waypoints):
            logger.debug(
                f"Walking to waypoint {waypoint_idx + 1}/{len(waypoints)}: "
                f"({waypoint_x}, {waypoint_y})"
            )

            # Walk to this waypoint
            if not self._walk_to_waypoint(waypoint_x, waypoint_y, move_style):
                logger.error(f"Failed to reach waypoint ({waypoint_x}, {waypoint_y})")
                return False

            logger.debug(f"Reached waypoint {waypoint_idx + 1}/{len(waypoints)}")

        logger.info("Successfully completed path")
        return True

    def _walk_to_waypoint(
        self, waypoint_x: int, waypoint_y: int, move_style: MovementStyle
    ) -> bool:
        """
        Walk to a single waypoint with distance-based chunking.

        Args:
            waypoint_x: Target world X coordinate
            waypoint_y: Target world Y coordinate
            move_style: Mouse movement style

        Returns:
            True if arrived, False on timeout/failure
        """
        max_attempts = 10  # Prevent infinite loops

        for attempt in range(max_attempts):
            # Get current player state
            state = self.status_socket.get_player_state()
            if not state:
                logger.error("Lost Status Socket connection during walk")
                return False

            # Calculate distance to waypoint
            distance = self._calculate_distance(
                state.world_x, state.world_y, waypoint_x, waypoint_y
            )

            # Check if arrived
            if distance <= self.config.arrival_tolerance:
                logger.debug(
                    f"Arrived at ({waypoint_x}, {waypoint_y}) "
                    f"from ({state.world_x}, {state.world_y})"
                )
                return True

            # Calculate next click position
            # If target is far, click intermediate point
            if distance > self.config.max_click_distance:
                # Click max_click_distance tiles in direction of target
                click_target = self._get_intermediate_point(
                    state.world_x,
                    state.world_y,
                    waypoint_x,
                    waypoint_y,
                    self.config.max_click_distance,
                )
                logger.debug(
                    f"Target far ({distance:.1f} tiles), "
                    f"clicking intermediate: {click_target}"
                )
            else:
                # Click waypoint directly
                click_target = (waypoint_x, waypoint_y)

            # Convert to minimap coordinates
            minimap_pos = self.world_to_minimap(
                click_target[0],
                click_target[1],
                state.world_x,
                state.world_y,
                state.camera_yaw,
            )

            if not minimap_pos:
                logger.warning(
                    f"Target ({
                        click_target[0]}, {
                        click_target[1]}) out of minimap range"
                )
                return False

            # Convert to absolute screen coordinates
            abs_x, abs_y = self.screen.relative_to_absolute(*minimap_pos)

            # Click minimap
            logger.debug(f"Clicking minimap at ({abs_x}, {abs_y})")
            self.mouse.click_at(abs_x, abs_y, move_style=move_style)

            # Wait for movement to start/complete
            if not self.status_socket.wait_for_arrival(
                waypoint_x,
                waypoint_y,
                tolerance=self.config.arrival_tolerance,
                timeout=10.0,
            ):
                logger.warning(
                    f"Timeout on attempt {attempt + 1}/{max_attempts} "
                    f"walking to ({waypoint_x}, {waypoint_y})"
                )
                # Try again
                continue

            # Success - arrived
            return True

        logger.error(
            f"Failed to reach waypoint ({waypoint_x}, {waypoint_y}) "
            f"after {max_attempts} attempts"
        )
        return False

    def world_to_minimap(
        self, world_x: int, world_y: int, player_x: int, player_y: int, camera_yaw: int
    ) -> Optional[Tuple[int, int]]:
        """
        Convert world tile coordinates to minimap pixel coordinates.

        Uses 2D rotation matrix to compensate for camera rotation.

        Algorithm:
        1. Calculate delta: dx = world_x - player_x, dy = world_y - player_y
        2. Convert yaw (0-2048) to radians: angle = (yaw / 2048) * 2π
        3. Apply 2D rotation matrix:
           rotated_x = dx * cos(angle) - dy * sin(angle)
           rotated_y = dx * sin(angle) + dy * cos(angle)
        4. Scale to pixels and add minimap center:
           minimap_x = center_x + (rotated_x * tile_size)
           minimap_y = center_y + (rotated_y * tile_size)

        Args:
            world_x: Target world X coordinate
            world_y: Target world Y coordinate
            player_x: Player world X coordinate
            player_y: Player world Y coordinate
            camera_yaw: Camera yaw (0-2048 RuneLite range)

        Returns:
            (minimap_x, minimap_y) in window-relative coords, or None if out of range
        """
        # Calculate tile delta from player
        dx = world_x - player_x
        dy = world_y - player_y

        # Convert RuneLite yaw (0-2048) to radians
        # RuneLite yaw 0 = north, increases clockwise
        # We need to invert Y axis because OSRS Y increases southward
        degrees = 360 - (camera_yaw * self.degrees_per_unit)
        theta = math.radians(degrees)

        # Apply 2D rotation matrix
        rotated_x = dx * math.cos(theta) - dy * math.sin(theta)
        rotated_y = dx * math.sin(theta) + dy * math.cos(theta)

        # Scale to minimap pixels (4 pixels per tile)
        pixel_x = rotated_x * self.config.tile_size
        pixel_y = rotated_y * self.config.tile_size

        # Add minimap center offset
        minimap_x = self.config.minimap_center_x + int(pixel_x)
        minimap_y = self.config.minimap_center_y + int(pixel_y)

        # Check if within minimap bounds (circular)
        minimap_radius = 73  # pixels
        distance_from_center = math.sqrt(pixel_x**2 + pixel_y**2)

        if distance_from_center > minimap_radius:
            logger.debug(
                f"Target ({world_x}, {world_y}) outside minimap "
                f"(distance: {distance_from_center:.1f} > {minimap_radius})"
            )
            return None

        return (minimap_x, minimap_y)

    def _get_intermediate_point(
        self, start_x: int, start_y: int, end_x: int, end_y: int, max_distance: int
    ) -> Tuple[int, int]:
        """
        Get intermediate point max_distance tiles from start toward end.

        Args:
            start_x: Starting world X
            start_y: Starting world Y
            end_x: Target world X
            end_y: Target world Y
            max_distance: Maximum distance to travel

        Returns:
            (x, y) world coordinates of intermediate point
        """
        dx = end_x - start_x
        dy = end_y - start_y
        distance = math.sqrt(dx**2 + dy**2)

        if distance == 0:
            return (start_x, start_y)

        # Normalize and scale to max_distance
        ratio = max_distance / distance
        intermediate_x = start_x + int(dx * ratio)
        intermediate_y = start_y + int(dy * ratio)

        return (intermediate_x, intermediate_y)

    def _calculate_distance(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Calculate Euclidean distance between two points."""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def compute_minimap_click(
        self, target_x: int, target_y: int
    ) -> Optional[Tuple[int, int]]:
        """
        Calculate minimap pixel coordinates for target world position.

        Convenience method that gets current player state and computes click position.

        Args:
            target_x: Target world X coordinate
            target_y: Target world Y coordinate

        Returns:
            (minimap_x, minimap_y) in window-relative coords, or None if out of range
        """
        state = self.status_socket.get_player_state()
        if not state:
            logger.error("Cannot compute minimap click - Status Socket unavailable")
            return None

        return self.world_to_minimap(
            target_x, target_y, state.world_x, state.world_y, state.camera_yaw
        )
