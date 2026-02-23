"""
MinimapLocalizationService - Determines player world position by matching
the current minimap screenshot against a pre-loaded reference map image.

Vision-based approach that is robust to different fonts, display settings, and
RuneLite configurations — no OCR, no plugins, no memory reading.

How it works:
    The OSRS minimap renders a top-down view of the world at ~4px per tile.
    By sliding this minimap crop over a pre-loaded map image of the area and
    finding the best match (cv2.matchTemplate), we get the player's exact tile
    position with no OCR, no plugins, and no memory reading.

Requirements:
    - Camera must be North-up. Press the compass button in RuneLite once at
      bot startup to snap the camera North before running.
    - A pre-loaded PNG map image of the relevant area at 4px-per-tile scale.
    - The world coordinates of the map image's top-left (NW) corner.

Map images:
    Store map images in src/osrsbot/images/maps/.
    Use osrsbot.utils.path_helpers.get_maps_path("area.png") to reference them.

    To obtain a map image for a new area:
      1. Open the OSRS world map in-game or on the wiki.
      2. Screenshot the region you need at the correct zoom level (1px = 1 tile).
      3. Scale by 4x (so each tile = 4px) to match minimap resolution.
      4. Note the world X,Y of the top-left corner of your screenshot.

Coordinate system:
    - World X increases going East  → image X increases right  (same direction)
    - World Y increases going North → image Y increases DOWN   (opposite direction)
    So: world_x = origin_x + pixel_x
        world_y = origin_y - pixel_y   (origin_y is the NORTHMOST tile = highest Y)

Usage:
    service = MinimapLocalizationService(
        screen=screen_service,
        map_image_path=get_maps_path("sand_crabs.png"),
        map_origin_world_x=3420,   # World X of leftmost pixel in image
        map_origin_world_y=3310,   # World Y of topmost pixel in image (northernmost)
    )

    state = service.get_player_state()
    if state:
        print(state.world_x, state.world_y)

    # Plug into an existing WalkerService:
    walker.status_socket = service
"""

from __future__ import annotations

import logging
import math
import time
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

from dataclasses import dataclass

from osrsbot.services.screen_service import ScreenService


@dataclass
class PlayerState:
    """Player position and state data."""
    world_x: int
    world_y: int
    plane: int = 0
    camera_yaw: int = 0
    timestamp: float = 0.0
    is_moving: bool = False
    animation_id: int = -1

logger = logging.getLogger(__name__)


class MinimapLocalizationService:
    """
    Determines player world position by matching the minimap to a reference map.

    Drop-in replacement for CoordinateOCRService — implements the same
    get_player_state() / get_coordinates() / wait_for_arrival() interface so it
    can be passed directly to WalkerService.status_socket.
    """

    # Minimap geometry (standard OSRS UI at 1366x768).
    # Override via constructor for other resolutions.
    DEFAULT_CENTER_X: int = 654   # Window-relative pixel
    DEFAULT_CENTER_Y: int = 111   # Window-relative pixel
    DEFAULT_RADIUS: int = 73      # Pixels; the minimap is a circle

    # Mask inset — crop slightly inside the circle to avoid the compass orb
    # and the run/prayer/HP orbs that sit on the minimap edge.
    MASK_INSET: int = 6

    # Template-match confidence below this → position unknown, return last known.
    MATCH_THRESHOLD: float = 0.40

    def __init__(
        self,
        screen: ScreenService,
        map_image_path: str | Path,
        map_origin_world_x: int,
        map_origin_world_y: int,
        minimap_center_x: int = DEFAULT_CENTER_X,
        minimap_center_y: int = DEFAULT_CENTER_Y,
        minimap_radius: int = DEFAULT_RADIUS,
    ) -> None:
        """
        Args:
            screen:               ScreenService for minimap capture.
            map_image_path:       Path to the reference map PNG.
            map_origin_world_x:   World X of the leftmost (west) pixel in the map image.
            map_origin_world_y:   World Y of the topmost (north) pixel in the map image.
                                  This is the LARGEST Y value in the covered area.
            minimap_center_x:     Minimap centre X relative to game window.
            minimap_center_y:     Minimap centre Y relative to game window.
            minimap_radius:       Pixel radius of the circular minimap.
        """
        self._screen = screen
        self._origin_x = map_origin_world_x
        self._origin_y = map_origin_world_y
        self._cx = minimap_center_x
        self._cy = minimap_center_y
        self._r = minimap_radius

        self._map = self._load_map(Path(map_image_path))
        self._mask = self._build_mask()

        self._last_state: Optional[PlayerState] = None
        self._last_confidence: float = 0.0

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _load_map(self, path: Path) -> np.ndarray:
        if not path.exists():
            raise FileNotFoundError(f"Map image not found: {path}")
        img = cv2.imread(str(path))
        if img is None:
            raise ValueError(f"cv2 could not read map image: {path}")
        logger.info(f"MinimapLocalization: loaded map {path.name} ({img.shape[1]}x{img.shape[0]}px)")
        d = self._r * 2
        if img.shape[0] < d or img.shape[1] < d:
            raise ValueError(
                f"Map image ({img.shape[1]}x{img.shape[0]}) must be larger than "
                f"the minimap crop ({d}x{d}). Use a bigger map image."
            )
        return img

    def _build_mask(self) -> np.ndarray:
        """Circular mask with inset — zeros out compass orb and edge UI."""
        d = self._r * 2
        mask = np.zeros((d, d), dtype=np.uint8)
        effective_r = self._r - self.MASK_INSET
        cv2.circle(mask, (self._r, self._r), effective_r, 255, thickness=-1)
        return mask

    # ── Minimap capture ───────────────────────────────────────────────────────

    def _capture_minimap(self) -> Optional[np.ndarray]:
        """Capture the circular minimap region as a masked BGR ndarray."""
        d = self._r * 2
        region = (self._cx - self._r, self._cy - self._r, d, d)
        pil = self._screen.capture(region=region, relative=True)
        if pil is None:
            return None

        bgr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

        # Black-out pixels outside the circle so they don't influence matching
        bgr[self._mask == 0] = 0
        return bgr

    # ── Localisation ──────────────────────────────────────────────────────────

    def get_player_state(self) -> Optional[PlayerState]:
        """
        Match the current minimap against the reference map.

        Returns:
            PlayerState with world_x / world_y if confidence is above threshold,
            otherwise the last known good state (or None on first failure).
        """
        minimap = self._capture_minimap()
        if minimap is None:
            logger.warning("MinimapLocalization: minimap capture failed")
            return self._last_state

        result = cv2.matchTemplate(self._map, minimap, cv2.TM_CCOEFF_NORMED)
        _, confidence, _, top_left = cv2.minMaxLoc(result)
        self._last_confidence = float(confidence)

        if confidence < self.MATCH_THRESHOLD:
            logger.debug(
                f"MinimapLocalization: low confidence {confidence:.2f} "
                f"(threshold {self.MATCH_THRESHOLD}) — using last known position"
            )
            return self._last_state

        # top_left is the position in the map image where the minimap crop starts.
        # The player is at the centre of that crop.
        map_px = top_left[0] + self._r   # pixel column in map image
        map_py = top_left[1] + self._r   # pixel row in map image

        # Convert map pixels → world tiles.
        # X: map image left → East  (same direction, no flip)
        # Y: map image top  → North (opposite: high world Y = low image Y)
        world_x = self._origin_x + map_px
        world_y = self._origin_y - map_py

        state = PlayerState(
            world_x=world_x,
            world_y=world_y,
            plane=0,
            camera_yaw=0,   # Assumes North-up camera; see module docstring
            timestamp=time.time(),
        )
        logger.debug(
            f"MinimapLocalization: ({world_x}, {world_y}) confidence={confidence:.2f}"
        )
        self._last_state = state
        return state

    def get_coordinates(self) -> Optional[PlayerState]:
        """Alias for get_player_state()."""
        return self.get_player_state()

    def wait_for_arrival(
        self,
        target_x: int,
        target_y: int,
        tolerance: int = 2,
        timeout: float = 10.0,
    ) -> bool:
        """
        Poll until the player reaches target tile or timeout.

        Compatible with WalkerService.wait_for_arrival() call signature.

        Args:
            target_x:  Target world X.
            target_y:  Target world Y.
            tolerance: Arrival radius in tiles.
            timeout:   Maximum seconds to wait.

        Returns:
            True if arrived within tolerance, False on timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            state = self.get_player_state()
            if state:
                dist = math.sqrt(
                    (target_x - state.world_x) ** 2 + (target_y - state.world_y) ** 2
                )
                if dist <= tolerance:
                    logger.debug(f"MinimapLocalization: arrived at ({target_x}, {target_y})")
                    return True
            time.sleep(0.25)

        logger.warning(f"MinimapLocalization: timeout waiting for ({target_x}, {target_y})")
        return False

    def is_available(self) -> bool:
        """Return True if a position fix can be obtained right now."""
        return self.get_player_state() is not None

    @property
    def last_confidence(self) -> float:
        """Match confidence of the most recent call (0.0–1.0)."""
        return self._last_confidence
