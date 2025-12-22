"""Unit tests for ArduinoMouseService."""
import pytest
from unittest.mock import Mock, MagicMock, patch

from osrsbot.services.mouse_service import MouseConfig
from osrsbot.services.arduino_mouse_service import ArduinoMouseService, SERIAL_AVAILABLE


class TestArduinoMouseService:
    """Test ArduinoMouseService functionality."""

    @pytest.fixture
    def mouse_config(self):
        """Default mouse configuration."""
        return MouseConfig(
            min_speed=0.2,
            max_speed=0.6,
            overshoot_chance=0.15,
            overshoot_distance=20,
            click_variance=3,
            post_click_delay=(0.05, 0.15)
        )

    @pytest.fixture
    def mock_serial(self, monkeypatch):
        """Mock pyserial for Arduino communication."""
        mock_serial_class = Mock()
        mock_connection = Mock()
        mock_serial_class.Serial.return_value = mock_connection

        # Mock the serial module
        if SERIAL_AVAILABLE:
            monkeypatch.setattr("serial.Serial", mock_serial_class.Serial)
        else:
            # If serial not available, patch the import check
            monkeypatch.setattr(
                "osrsbot.services.arduino_mouse_service.SERIAL_AVAILABLE",
                True
            )
            monkeypatch.setattr(
                "osrsbot.services.arduino_mouse_service.serial.Serial",
                mock_serial_class.Serial
            )

        return mock_connection

    def test_initialization_with_available_arduino(self, mouse_config, mock_serial):
        """Test service initializes when Arduino connected."""
        service = ArduinoMouseService(
            config=mouse_config,
            serial_port="COM3",
            fallback_to_software=False
        )

        assert service._connection is mock_serial
        assert service._fallback is None

    def test_initialization_pyserial_not_installed(self, mouse_config, monkeypatch):
        """Test handling when pyserial not installed."""
        # Mock pyserial as unavailable
        monkeypatch.setattr(
            "osrsbot.services.arduino_mouse_service.SERIAL_AVAILABLE",
            False
        )

        # Should fall back to software mouse
        service = ArduinoMouseService(
            config=mouse_config,
            fallback_to_software=True
        )

        assert service._fallback is not None
        assert service._connection is None

    def test_initialization_arduino_unavailable_with_fallback(self, mouse_config, mock_serial):
        """Test fallback when Arduino not connected."""
        # Simulate connection failure
        mock_serial_class = Mock()
        mock_serial_class.Serial.side_effect = Exception("Port not found")

        with patch("serial.Serial", mock_serial_class.Serial):
            service = ArduinoMouseService(
                config=mouse_config,
                serial_port="COM999",
                fallback_to_software=True
            )

        assert service._fallback is not None
        assert service._connection is None

    def test_initialization_arduino_unavailable_no_fallback(self, mouse_config, mock_serial):
        """Test exception when Arduino unavailable and fallback disabled."""
        # Simulate connection failure
        mock_serial_class = Mock()
        mock_serial_class.Serial.side_effect = Exception("Port not found")

        with patch("serial.Serial", mock_serial_class.Serial):
            with pytest.raises(RuntimeError, match="Failed to connect to Arduino"):
                ArduinoMouseService(
                    config=mouse_config,
                    serial_port="COM999",
                    fallback_to_software=False
                )

    def test_send_movement_protocol(self, mouse_config, mock_serial):
        """Test correct serial protocol for movement."""
        service = ArduinoMouseService(
            config=mouse_config,
            serial_port="COM3",
            fallback_to_software=False
        )

        service._send_movement(1920, 1080, duration=0.1)

        # Verify serial write called with correct format: "x;y\n"
        mock_serial.write.assert_called_once()
        call_args = mock_serial.write.call_args[0][0]
        assert call_args == b"1920;1080\n"

    def test_send_click_protocol_left(self, mouse_config, mock_serial):
        """Test correct serial protocol for left click."""
        service = ArduinoMouseService(
            config=mouse_config,
            serial_port="COM3",
            fallback_to_software=False
        )

        service._send_click("left")

        mock_serial.write.assert_called_once_with(b"l\n")

    def test_send_click_protocol_right(self, mouse_config, mock_serial):
        """Test correct serial protocol for right click."""
        service = ArduinoMouseService(
            config=mouse_config,
            serial_port="COM3",
            fallback_to_software=False
        )

        service._send_click("right")

        mock_serial.write.assert_called_once_with(b"r\n")

    def test_send_click_protocol_middle(self, mouse_config, mock_serial):
        """Test correct serial protocol for middle click."""
        service = ArduinoMouseService(
            config=mouse_config,
            serial_port="COM3",
            fallback_to_software=False
        )

        service._send_click("middle")

        mock_serial.write.assert_called_once_with(b"m\n")

    def test_move_to_uses_arduino(self, mouse_config, mock_serial):
        """Test move_to uses Arduino when connected."""
        service = ArduinoMouseService(
            config=mouse_config,
            serial_port="COM3",
            fallback_to_software=False
        )

        # Mock cursor position
        with patch.object(service, '_get_cursor_position', return_value=(100, 100)):
            result = service.move_to(200, 200, style="linear", duration=0.1)

        assert result is True
        assert mock_serial.write.called

    def test_move_to_uses_fallback(self, mouse_config, mock_serial):
        """Test move_to uses fallback when Arduino unavailable."""
        # Simulate connection failure
        mock_serial_class = Mock()
        mock_serial_class.Serial.side_effect = Exception("Port not found")

        with patch("serial.Serial", mock_serial_class.Serial):
            service = ArduinoMouseService(
                config=mouse_config,
                fallback_to_software=True
            )

        # Should use fallback mouse
        assert service._fallback is not None
        result = service.move_to(200, 200, style="curved")

        # Fallback should handle the call
        assert result is True

    def test_click_at_sends_movement_and_click(self, mouse_config, mock_serial):
        """Test click_at sends both movement and click commands."""
        service = ArduinoMouseService(
            config=mouse_config,
            serial_port="COM3",
            fallback_to_software=False
        )

        with patch.object(service, '_get_cursor_position', return_value=(100, 100)):
            result = service.click_at(500, 500, button="left")

        assert result is True
        # Should have written movement and click commands
        assert mock_serial.write.call_count >= 2

    def test_click_variance_applied(self, mouse_config, mock_serial):
        """Test click variance is applied to target position."""
        service = ArduinoMouseService(
            config=mouse_config,
            serial_port="COM3",
            fallback_to_software=False
        )

        target_x, target_y = 500, 500

        with patch.object(service, '_get_cursor_position', return_value=(100, 100)):
            with patch('random.randint', return_value=2):  # Fixed variance for testing
                service.click_at(target_x, target_y, variance=True)

        # Check that movement was sent with variance applied
        # With variance of 2, position should be (502, 502)
        call_args = mock_serial.write.call_args_list[0][0][0].decode('utf-8')
        # Should contain modified coordinates (not exact 500,500)
        assert "500;500" not in call_args or "502;502" in call_args

    def test_position_correction_retry(self, mouse_config, mock_serial):
        """Test multi-pass position correction."""
        service = ArduinoMouseService(
            config=mouse_config,
            serial_port="COM3",
            fallback_to_software=False
        )

        # Simulate inaccurate first movement, then accurate
        positions = [(100, 100), (195, 195), (200, 200)]
        position_iter = iter(positions)

        with patch.object(service, '_get_cursor_position', side_effect=lambda: next(position_iter)):
            result = service.move_to(200, 200, duration=0.1)

        assert result is True
        # Should have sent correction commands
        assert mock_serial.write.call_count > 1

    def test_get_cursor_position_windows_api(self, mouse_config, mock_serial):
        """Test cursor position retrieval using ctypes."""
        service = ArduinoMouseService(
            config=mouse_config,
            serial_port="COM3",
            fallback_to_software=False
        )

        # Mock ctypes POINT structure
        with patch('ctypes.windll.user32.GetCursorPos') as mock_get_cursor:
            # Simulate cursor at (300, 400)
            def set_cursor_pos(point_ref):
                point_ref.contents.x = 300
                point_ref.contents.y = 400

            # Note: Actual implementation varies, this is simplified
            position = service._get_cursor_position()

            # Should return a tuple
            assert isinstance(position, tuple)
            assert len(position) == 2

    def test_close_connection(self, mouse_config, mock_serial):
        """Test closing Arduino connection."""
        service = ArduinoMouseService(
            config=mouse_config,
            serial_port="COM3",
            fallback_to_software=False
        )

        service.close()

        mock_serial.close.assert_called_once()

    def test_close_connection_when_fallback(self, mouse_config):
        """Test close when using fallback mouse."""
        # Simulate connection failure
        mock_serial_class = Mock()
        mock_serial_class.Serial.side_effect = Exception("Port not found")

        with patch("serial.Serial", mock_serial_class.Serial):
            service = ArduinoMouseService(
                config=mouse_config,
                fallback_to_software=True
            )

        # Should not raise exception
        service.close()

    def test_click_without_position_uses_current(self, mouse_config, mock_serial):
        """Test click without coordinates clicks at current position."""
        service = ArduinoMouseService(
            config=mouse_config,
            serial_port="COM3",
            fallback_to_software=False
        )

        result = service.click(button="left")

        assert result is True
        # Should only send click command, not movement
        mock_serial.write.assert_called_once()
        call_args = mock_serial.write.call_args[0][0]
        assert call_args == b"l\n"

    def test_config_values_used(self, mouse_config, mock_serial):
        """Test that config values are respected."""
        service = ArduinoMouseService(
            config=mouse_config,
            serial_port="COM3",
            fallback_to_software=False
        )

        assert service.config.min_speed == 0.2
        assert service.config.max_speed == 0.6
        assert service.config.click_variance == 3
        assert service.config.post_click_delay == (0.05, 0.15)
