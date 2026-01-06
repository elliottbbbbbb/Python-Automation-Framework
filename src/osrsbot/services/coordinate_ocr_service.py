"""
CoordinateOCRService - Reads world coordinates from RuneLite's bottom-left display.

Uses template-based OCR (same method as HP/Prayer reading) to extract X, Y, plane
coordinates from the coordinate display in the bottom-left corner.
"""

# Note to self: Why on earth did Claude choose to create this 
# instead of the template matching service that already exists?

import logging
import cv2
import numpy as np
from typing import Optional
from dataclasses import dataclass

from osrsbot.services.screen_service import ScreenService
from osrsbot.services.template_ocr_service import TemplateOCRService, YELLOW, WHITE, GRAY, LIGHT_GRAY
from osrsbot.services.status_socket_service import PlayerState
from osrsbot.models.config import Config

logger = logging.getLogger(__name__)


class CoordinateOCRService:
    """
    Reads world coordinates from RuneLite's coordinate display.

    Uses the same template OCR approach as HP/Prayer reading for accuracy.
    The display format is typically: "World: 3200, 3400, 0"

    Located in bottom-left corner of game window.
    """

    def __init__(self, screen: ScreenService, ocr: TemplateOCRService, config: Config):
        """
        Initialize coordinate OCR service.

        Args:
            screen: Screen service for screenshots
            ocr: OCR service for template matching
            config: Configuration for screen regions
        """
        self.screen = screen
        self.ocr = ocr
        self.config = config
        self._last_state: Optional[PlayerState] = None

    def get_coordinates(self) -> Optional[PlayerState]:
        """
        Read current world coordinates from screen using OCR.

        Reads X, Y, and plane separately from the bottom-left coordinate display.

        Returns:
            PlayerState if successfully read, None otherwise
        """
        import time

        # Get coordinate region from config
        coord_region = self.config.get("coordinates", "ocr", "world_coord_region")
        if not coord_region:
            logger.warning("world_coord_region not in config - using defaults")
            # Default region for bottom-left coordinates
            coord_region = {
                "x": 10,
                "y": 500,
                "width": 150,
                "height": 20
            }

        # Read X coordinate (format: "3200," or "3200")
        x = self._read_coordinate_number(coord_region, offset_x=20, width=50)
        if x is None:
            logger.debug("Failed to read X coordinate")
            return self._last_state

        # Read Y coordinate (appears after X, after comma/space)
        # Offset adjusted based on typical spacing: "3165, 3137"
        y = self._read_coordinate_number(coord_region, offset_x=65, width=50)
        if y is None:
            logger.debug("Failed to read Y coordinate")
            return self._last_state

        # Read Plane (single digit, appears after Y)
        # Offset adjusted based on typical spacing: "3165, 3137, 0"
        plane = self._read_coordinate_number(coord_region, offset_x=120, width=20)
        if plane is None:
            logger.debug("Failed to read plane coordinate, defaulting to 0")
            plane = 0  # Default to ground floor

        # Validate coordinates are in valid OSRS range
        if not (1000 <= x <= 5000 and 1000 <= y <= 5000 and 0 <= plane <= 3):
            logger.warning(f"Coordinates out of range: ({x}, {y}, {plane})")
            return self._last_state

        # Create PlayerState (compatible with StatusSocketService)
        state = PlayerState(
            world_x=x,
            world_y=y,
            plane=plane,
            camera_yaw=0,  # TODO: Could be read from compass if needed
            timestamp=time.time(),
            is_moving=False,  # Could detect by comparing positions
            animation_id=-1  # Not available via OCR
        )

        self._last_state = state
        logger.debug(f"Read coordinates: ({state.world_x}, {state.world_y}, {state.plane})")
        return state

    def _enhance_contrast(self, img: np.ndarray, alpha: float = 2.5, beta: int = 50) -> np.ndarray:
        """
        Enhance image contrast to brighten dim text.

        Uses the formula: output = alpha * input + beta
        - alpha: Contrast control (>1 increases contrast)
        - beta: Brightness control (adds constant value)

        Args:
            img: Input image (BGR format)
            alpha: Contrast multiplier (default 2.5)
            beta: Brightness offset (default 50)

        Returns:
            Enhanced image
        """
        # Apply contrast/brightness adjustment
        # Clip values to stay in valid 0-255 range
        enhanced = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
        return enhanced

    def _read_coordinate_number(
        self, base_region: dict, offset_x: int = 0, width: int = 50
    ) -> Optional[int]:
        """
        Read a single coordinate number from screen using template OCR.

        Args:
            base_region: Base region dict with x, y, height
            offset_x: Horizontal offset from base region
            width: Width of region to capture

        Returns:
            Coordinate number or None if OCR failed
        """
        x = base_region["x"] + offset_x
        y = base_region["y"]
        height = base_region.get("height", 20)

        img = self.screen.capture(region=(x, y, width, height), relative=True)
        if img is None:
            logger.debug(f"Failed to capture coordinate region at ({x}, {y})")
            return None

        # Convert PIL to numpy array for OCR
        img_np = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        # Enhance contrast to brighten dim text (RGB ~80 -> ~200)
        # This makes the dim gray text bright enough for color isolation
        img_enhanced = self._enhance_contrast(img_np, alpha=2.5, beta=50)

        # Use template OCR with enhanced image
        # After enhancement, the text should be bright enough for WHITE color
        number = self.ocr.extract_number(
            img_enhanced,
            font_name="plain11",  # RuneLite uses plain11 font
            colors=[WHITE, LIGHT_GRAY],  # Try both white and light gray
            correlation_threshold=0.85  # Lower threshold due to enhancement artifacts
        )

        return number

    def is_available(self) -> bool:
        """
        Check if coordinate reading is working.

        Returns:
            True if coordinates can be read, False otherwise
        """
        coords = self.get_coordinates()
        return coords is not None

    def get_player_state(self) -> Optional[PlayerState]:
        """
        Get current player state - alias for get_coordinates().

        Matches StatusSocketService interface for drop-in replacement.

        Returns:
            PlayerState if successfully read, None otherwise
        """
        return self.get_coordinates()

    def wait_for_arrival(
        self, target_x: int, target_y: int, tolerance: int = 2, timeout: float = 10.0
    ) -> bool:
        """
        Poll until player reaches target coordinates or timeout.

        Compatible interface with StatusSocketService.

        Args:
            target_x: Target world X coordinate
            target_y: Target world Y coordinate
            tolerance: Distance in tiles to consider "arrived" (default 2)
            timeout: Maximum time to wait in seconds (default 10.0)

        Returns:
            True if arrived within tolerance, False on timeout
        """
        import time

        start_time = time.time()
        while (time.time() - start_time) < timeout:
            state = self.get_player_state()
            if not state:
                time.sleep(0.2)
                continue

            # Calculate distance to target
            distance = ((target_x - state.world_x) ** 2 + (target_y - state.world_y) ** 2) ** 0.5

            if distance <= tolerance:
                logger.debug(f"Arrived at ({target_x}, {target_y})")
                return True

            time.sleep(0.2)  # Check every 200ms

        logger.warning(f"Timeout waiting for arrival at ({target_x}, {target_y})")
        return False
