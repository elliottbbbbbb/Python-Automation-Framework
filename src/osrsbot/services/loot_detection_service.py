"""Loot detection service using color detection for ground items."""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class LootDetectionService:
    """
    Detect loot items on ground using color detection.

    RuneLite highlights valuable loot in purple/pink, making color-based
    detection simple and reliable.
    """

    def __init__(self, screen_service, loot_color: str = "#ff00dc"):
        """
        Initialize loot detection service.

        Args:
            screen_service: ScreenService instance for color detection
            loot_color: Hex color for loot highlights (default: RuneLite purple/pink)
        """
        self.screen = screen_service
        self.loot_color = loot_color
        logger.info(f"LootDetectionService initialized (loot color: {loot_color})")

    def detect_loot(
        self, region: Optional[Tuple[int, int, int, int]] = None, tolerance: int = 30
    ) -> list[Tuple[int, int]]:
        """
        Detect all loot items on screen using color detection.

        RuneLite highlights valuable loot in purple/pink, making detection
        simple and reliable.

        Args:
            region: Optional (x, y, w, h) search region
            tolerance: Color matching tolerance (0-255, default 30)

        Returns:
            List of (x, y) coordinates for each loot item found
        """
        # Find all purple loot highlights
        loot_positions = self.screen.find_color(
            self.loot_color, tolerance=tolerance, region=region
        )

        if not loot_positions:
            logger.debug("No loot detected on screen")
            return []

        # Remove duplicate/overlapping detections (loot highlights are multi-pixel)
        filtered = self._cluster_nearby_positions(loot_positions, cluster_radius=10)

        logger.debug(f"Found {len(filtered)} loot items on screen")
        return filtered

    def detect_nearest_loot(
        self,
        player_pos: Tuple[int, int],
        region: Optional[Tuple[int, int, int, int]] = None,
        tolerance: int = 30,
    ) -> Optional[Tuple[int, int]]:
        """
        Detect nearest loot item to player position.

        Args:
            player_pos: Player position (x, y)
            region: Optional search region
            tolerance: Color matching tolerance

        Returns:
            (x, y) coordinates of nearest loot, or None if not found
        """
        all_loot = self.detect_loot(region, tolerance)

        if not all_loot:
            return None

        # Find closest to player
        player_x, player_y = player_pos

        def distance(pos: Tuple[int, int]) -> float:
            loot_x, loot_y = pos
            import math

            return math.sqrt((loot_x - player_x) ** 2 + (loot_y - player_y) ** 2)

        nearest = min(all_loot, key=distance)
        dist = distance(nearest)

        logger.debug(f"Nearest loot at {nearest}, distance: {dist:.1f}px from player")
        return nearest

    def _cluster_nearby_positions(
        self, positions: list[Tuple[int, int]], cluster_radius: int = 10
    ) -> list[Tuple[int, int]]:
        """
        Cluster nearby positions into single points.

        Loot highlights are multi-pixel, so we need to cluster nearby
        detections into single loot items.

        Args:
            positions: List of (x, y) positions
            cluster_radius: Maximum distance to consider same cluster (pixels)

        Returns:
            List of cluster centers (average position of each cluster)
        """
        if len(positions) <= 1:
            return positions

        clusters = []
        used = set()

        for pos in positions:
            if pos in used:
                continue

            # Start new cluster
            cluster = [pos]
            used.add(pos)

            # Find all nearby positions
            for other_pos in positions:
                if other_pos in used:
                    continue

                dx = abs(pos[0] - other_pos[0])
                dy = abs(pos[1] - other_pos[1])
                distance = (dx**2 + dy**2) ** 0.5

                if distance <= cluster_radius:
                    cluster.append(other_pos)
                    used.add(other_pos)

            # Calculate cluster center (average position)
            avg_x = sum(p[0] for p in cluster) // len(cluster)
            avg_y = sum(p[1] for p in cluster) // len(cluster)
            clusters.append((avg_x, avg_y))

        return clusters
