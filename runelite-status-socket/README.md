# RuneLite Status Socket Plugin

A RuneLite plugin that exports real-time player position, camera angle, and movement state to a JSON file for consumption by external automation tools (specifically the OSRS Python Bot Framework).

## Features

- **World Coordinates**: Exports player X, Y, and plane (Z-level)
- **Camera Data**: Camera yaw and pitch for accurate coordinate transformation
- **Animation State**: Current animation ID and movement detection
- **Configurable Update Rate**: 50-1000ms update interval (default: 100ms = 10 updates/second)
- **Thread-Safe File I/O**: Atomic writes prevent partial reads by external tools
- **Lightweight**: Minimal performance impact on RuneLite client

## Installation

### Prerequisites

- RuneLite client installed
- Java 11 or higher (RuneLite requirement)

### Steps

1. **Download the plugin JAR**:
   - Location: `runelite-status-socket/build/libs/runelite-status-socket-1.0.0.jar`

2. **Install as external plugin**:
   ```cmd
   # Create externalplugins directory if it doesn't exist
   mkdir %USERPROFILE%\.runelite\externalplugins

   # Copy plugin JAR
   copy runelite-status-socket-1.0.0.jar %USERPROFILE%\.runelite\externalplugins\
   ```

3. **Restart RuneLite**

4. **Enable the plugin**:
   - Open RuneLite
   - Click the wrench icon (Configuration)
   - Search for "Status Socket"
   - Toggle the plugin ON

## Configuration

Access plugin settings via RuneLite's configuration panel:

### Output File Path
- **Default**: `C:\Users\<your-username>\.runelite\live_data.json`
- **Description**: Where to write the JSON file
- **Note**: Must match the path configured in your Python bot's `config.json`

### Update Interval (ms)
- **Default**: 100ms (10 updates/second)
- **Range**: 50-1000ms
- **Description**: How often to update the file
  - Lower = more responsive but higher CPU usage
  - Higher = less responsive but lower CPU usage

### Enable Debug Logging
- **Default**: false
- **Description**: Log each update to RuneLite console (for debugging)

### Include Extended Data
- **Default**: true
- **Description**: Include camera pitch and timestamp in JSON output

## JSON Output Format

The plugin writes a JSON file with the following structure:

```json
{
  "worldPoint": {
    "x": 3200,
    "y": 3400,
    "plane": 0
  },
  "camera": {
    "yaw": 512,
    "pitch": 256
  },
  "animation": -1,
  "isMoving": false,
  "timestamp": 1704376800000
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `worldPoint.x` | int | World X coordinate (absolute) |
| `worldPoint.y` | int | World Y coordinate (absolute) |
| `worldPoint.plane` | int | Z-level (0 = ground floor, 1+ = upper floors) |
| `camera.yaw` | int | Camera rotation (0-2048, 0 = north, increases clockwise) |
| `camera.pitch` | int | Camera pitch angle |
| `animation` | int | Current animation ID (-1 = idle) |
| `isMoving` | boolean | Whether player is currently moving |
| `timestamp` | long | Unix timestamp in milliseconds |

## Python Bot Integration

### Configuration

Update your Python bot's `config.json` to match the plugin's output path:

```json
{
  "status_socket": {
    "enabled": true,
    "data_file": "C:\\Users\\elliott\\.runelite\\live_data.json",
    "poll_interval": 0.1
  }
}
```

### Testing the Connection

Run this Python script to verify the plugin is working:

```python
from osrsbot.services.status_socket_service import StatusSocketService

# Initialize service
service = StatusSocketService("C:\\Users\\elliott\\.runelite\\live_data.json")

# Check if plugin is available
if service.is_available():
    print("✓ Plugin connected!")

    # Get current player state
    state = service.get_player_state()
    if state:
        print(f"Position: ({state.world_x}, {state.world_y}), Plane: {state.plane}")
        print(f"Camera Yaw: {state.camera_yaw}")
        print(f"Moving: {state.is_moving}")
        print(f"Animation: {state.animation_id}")
    else:
        print("✗ Failed to read player state")
else:
    print("✗ Plugin not detected - ensure:")
    print("  1. RuneLite is running")
    print("  2. Status Socket plugin is enabled")
    print("  3. You are logged into OSRS")
    print("  4. File path matches config")
```

### Using with WalkerService

Once the plugin is working, you can use the bot's pathfinding features:

```python
from osrsbot.core.runner import ScriptRunner

# Initialize bot
runner = ScriptRunner("RuneLite - YourAccountName")

# Access walker (requires Status Socket plugin)
walker = runner.walker

# Walk to a world coordinate
success = walker.walk_to(3200, 3400)  # Example: walk to (3200, 3400)

if success:
    print("Arrived at destination!")
else:
    print("Failed to reach destination")
```

## Troubleshooting

### Plugin not appearing in RuneLite

- **Cause**: JAR not in correct location or RuneLite not restarted
- **Solution**:
  1. Verify JAR is in `%USERPROFILE%\.runelite\externalplugins\`
  2. Restart RuneLite completely
  3. Check RuneLite console for errors

### Python bot can't find live_data.json

- **Cause**: File path mismatch between plugin and Python config
- **Solution**:
  1. Check plugin config for output file path
  2. Update Python `config.json` to match exactly
  3. Ensure `.runelite` folder exists in user home

### File is stale / not updating

- **Cause**: Not logged into OSRS or plugin disabled
- **Solution**:
  1. Ensure you're logged into OSRS (not on login screen)
  2. Check plugin is enabled in RuneLite
  3. Enable debug logging to see updates in console

### Performance issues / lag

- **Cause**: Update interval too low (too frequent updates)
- **Solution**:
  1. Increase update interval to 200-500ms
  2. Disable debug logging
  3. Monitor CPU usage

## Building from Source

If you want to modify the plugin or rebuild it:

```bash
# Navigate to plugin directory
cd runelite-status-socket

# Build using Gradle
gradle-7.6/bin/gradle build

# Or if you have Gradle installed globally:
gradle build

# Output JAR will be in:
# build/libs/runelite-status-socket-1.0.0.jar
```

## Technical Details

### Thread Safety

- Uses `ReentrantLock` for thread-safe file writes
- Atomic write pattern (write to `.tmp`, then rename) prevents partial reads
- All RuneLite API calls executed on client thread via `@Schedule`

### Performance

- Default 100ms update interval = 10 Hz
- Minimal CPU impact (< 1% on modern systems)
- File I/O optimized with buffered writes
- No blocking operations on game thread

### Compatibility

- **RuneLite Version**: 1.10.35+
- **Java Version**: 11+
- **Platform**: Windows, macOS, Linux (any OS supported by RuneLite)

## License

This plugin is part of the OSRS Bot Framework project.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Enable debug logging and check RuneLite console
3. Verify Python bot is configured correctly
4. Check that file permissions allow writes to output path

## Future Enhancements

Planned features (not yet implemented):
- Minimap image export for obstacle detection
- Collision map export from RuneLite Scene API
- Configurable JSON format options
- Multiple output formats (JSON, CSV, binary)
