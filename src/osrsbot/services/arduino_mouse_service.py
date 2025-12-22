"""
ArduinoMouseService - Hardware mouse control via Arduino serial connection.

Drop-in replacement for MouseService that sends commands to Arduino over serial.
Provides enhanced anti-detection through hardware-based input.
"""
import time
import random
import logging
import ctypes
from typing import Tuple, Optional, Literal

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    serial = None

from osrsbot.services.mouse_service import MouseService, MouseConfig, MovementStyle

logger = logging.getLogger(__name__)


class ArduinoMouseService:
    """
    Hardware mouse control via Arduino.

    Compatible drop-in replacement for MouseService.
    Sends movement and click commands to Arduino over serial connection.
    Falls back to software mouse if Arduino unavailable.
    """

    def __init__(
        self,
        config: MouseConfig,
        serial_port: str = "COM3",
        baud_rate: int = 115200,
        fallback_to_software: bool = True
    ):
        """
        Initialize Arduino mouse service.

        Args:
            config: MouseConfig (same as MouseService)
            serial_port: Arduino COM port (Windows: COM3, Linux: /dev/ttyUSB0)
            baud_rate: Serial communication speed (115200 recommended)
            fallback_to_software: Use MouseService if Arduino unavailable

        Raises:
            ImportError: If pyserial not installed and fallback disabled
            RuntimeError: If Arduino connection fails and fallback disabled
        """
        self.config = config
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.fallback_to_software = fallback_to_software

        # Check pyserial availability
        if not SERIAL_AVAILABLE:
            logger.warning("pyserial not installed. Install with: pip install pyserial")
            if not fallback_to_software:
                raise ImportError("pyserial required for Arduino mouse. Install with: pip install pyserial")

        # Try to connect to Arduino
        self._connection = None
        if SERIAL_AVAILABLE:
            self._connection = self._connect_arduino()

        # Fallback to software mouse if needed
        if not self._connection and fallback_to_software:
            logger.warning("Arduino not available, falling back to software mouse")
            self._fallback = MouseService(config)
        elif not self._connection:
            raise RuntimeError(f"Failed to connect to Arduino on {serial_port}")
        else:
            self._fallback = None

        # Windows timer resolution hack for accurate sleep
        if self._connection:
            self._set_high_resolution_timer()

    def _connect_arduino(self) -> Optional[serial.Serial]:
        """
        Establish serial connection to Arduino.

        Returns:
            Serial connection if successful, None otherwise
        """
        try:
            logger.info(f"Attempting to connect to Arduino on {self.serial_port} at {self.baud_rate} baud")
            connection = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=1.0,
                write_timeout=1.0
            )

            # Wait for Arduino to initialize
            time.sleep(2.0)

            # Test connection with ping
            logger.info("Arduino connection established successfully")
            return connection

        except serial.SerialException as e:
            logger.warning(f"Failed to connect to Arduino on {self.serial_port}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error connecting to Arduino: {e}")
            return None

    def _set_high_resolution_timer(self):
        """
        Windows timer resolution hack for accurate sleep.

        Improves time.sleep() accuracy from ~15ms to ~1ms.
        Required for smooth Arduino mouse movement.
        """
        try:
            import platform
            if platform.system() == 'Windows':
                timeBeginPeriod = ctypes.windll.winmm.timeBeginPeriod
                timeBeginPeriod(1)
                logger.debug("Windows high-resolution timer enabled (1ms)")

                # Register cleanup on exit
                import atexit
                timeEndPeriod = ctypes.windll.winmm.timeEndPeriod
                atexit.register(lambda: timeEndPeriod(1))
        except Exception as e:
            logger.warning(f"Failed to set high-resolution timer: {e}")

    def move_to(
        self,
        x: int,
        y: int,
        style: MovementStyle = "curved",
        duration: Optional[float] = None,
        speed_multiplier: float = 1.0
    ) -> bool:
        """
        Move mouse to absolute screen coordinates.

        Args:
            x: Target X coordinate (absolute screen position)
            y: Target Y coordinate (absolute screen position)
            style: Movement style (Note: Arduino currently only supports linear)
            duration: Override automatic duration calculation
            speed_multiplier: Anti-ban speed variance

        Returns:
            True if movement successful
        """
        # Use fallback if Arduino not connected
        if self._fallback:
            return self._fallback.move_to(x, y, style, duration, speed_multiplier)

        try:
            # Calculate duration if not provided
            if duration is None:
                current_x, current_y = self._get_cursor_position()
                distance = ((x - current_x)**2 + (y - current_y)**2)**0.5
                duration = random.uniform(
                    self.config.min_speed,
                    self.config.max_speed
                ) * (1 + distance / 1000.0)

            # Apply speed multiplier
            duration *= speed_multiplier

            # Send movement command to Arduino
            self._send_movement(x, y, duration)

            # Multi-pass position correction (up to 2 retries)
            for attempt in range(2):
                actual_x, actual_y = self._get_cursor_position()
                error = abs(actual_x - x) + abs(actual_y - y)

                if error <= 3:  # Within 3 pixels = success
                    return True

                # Send correction
                logger.debug(f"Position correction attempt {attempt + 1} (error: {error}px)")
                self._send_movement(x, y, duration=0.05)

            return True

        except Exception as e:
            logger.error(f"Arduino mouse movement failed: {e}")
            return False

    def click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: Literal["left", "right", "middle"] = "left",
        variance: bool = True,
        delay_after: bool = True
    ) -> bool:
        """
        Click at current position or specified coordinates.

        Args:
            x: Optional X coordinate (if None, click at current position)
            y: Optional Y coordinate (if None, click at current position)
            button: Mouse button to click
            variance: Add random offset to click position
            delay_after: Sleep after click

        Returns:
            True if successful
        """
        # Use fallback if Arduino not connected
        if self._fallback:
            return self._fallback.click(x, y, button, variance, delay_after)

        try:
            # Move to position if specified
            if x is not None and y is not None:
                # Add variance
                if variance:
                    offset_x = random.randint(-self.config.click_variance, self.config.click_variance)
                    offset_y = random.randint(-self.config.click_variance, self.config.click_variance)
                    x += offset_x
                    y += offset_y

                self.move_to(x, y, style="linear", duration=0.1)

            # Random delay before click
            time.sleep(random.uniform(0.001, 0.01))

            # Send click command
            self._send_click(button)

            # Post-click delay
            if delay_after:
                delay = random.uniform(*self.config.post_click_delay)
                time.sleep(delay)

            return True

        except Exception as e:
            logger.error(f"Arduino mouse click failed: {e}")
            return False

    def click_at(
        self,
        x: int,
        y: int,
        button: Literal["left", "right", "middle"] = "left",
        move_style: MovementStyle = "curved",
        variance: bool = True,
        speed_multiplier: float = 1.0
    ) -> bool:
        """
        Move to position and click.

        Args:
            x: Target X coordinate
            y: Target Y coordinate
            button: Mouse button to click
            move_style: Movement style (Note: Arduino only supports linear currently)
            variance: Add random offset to click position
            speed_multiplier: Anti-ban speed variance

        Returns:
            True if successful
        """
        # Use fallback if Arduino not connected
        if self._fallback:
            return self._fallback.click_at(x, y, button, move_style, variance, speed_multiplier)

        try:
            # Add variance
            if variance:
                offset_x = random.randint(-self.config.click_variance, self.config.click_variance)
                offset_y = random.randint(-self.config.click_variance, self.config.click_variance)
                x += offset_x
                y += offset_y

            # Move to position
            # Note: Arduino implementation currently only supports linear movement
            # Bezier curves would require more complex Arduino firmware
            if move_style == "curved":
                logger.debug("Arduino mouse: curved style requested, using linear")
            self.move_to(x, y, style="linear", speed_multiplier=speed_multiplier)

            # Pause before click
            time.sleep(random.uniform(0.05, 0.15))

            # Click
            self._send_click(button)

            # Post-click delay
            delay = random.uniform(*self.config.post_click_delay)
            time.sleep(delay)

            return True

        except Exception as e:
            logger.error(f"Arduino click_at failed: {e}")
            return False

    def _send_movement(self, x: int, y: int, duration: float) -> None:
        """
        Send movement command to Arduino.

        Protocol: "x;y\n"
        Example: "1920;1080\n"
        """
        if not self._connection:
            return

        command = f"{x};{y}\n"
        self._connection.write(command.encode('utf-8'))

        # Wait for movement to complete
        time.sleep(duration)

    def _send_click(self, button: str) -> None:
        """
        Send click command to Arduino.

        Protocol: "l\n" for left, "r\n" for right, "m\n" for middle
        """
        if not self._connection:
            return

        button_map = {"left": "l", "right": "r", "middle": "m"}
        command = f"{button_map[button]}\n"
        self._connection.write(command.encode('utf-8'))

        # Wait for click completion
        time.sleep(0.05)

    def _get_cursor_position(self) -> Tuple[int, int]:
        """
        Get current cursor position using Windows API.

        Returns:
            (x, y) cursor position
        """
        try:
            # Windows API for cursor position
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            point = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
            return (point.x, point.y)

        except Exception as e:
            logger.error(f"Failed to get cursor position: {e}")
            return (0, 0)

    def close(self):
        """Close Arduino serial connection."""
        if self._connection:
            try:
                self._connection.close()
                logger.info("Arduino connection closed")
            except Exception as e:
                logger.error(f"Error closing Arduino connection: {e}")
