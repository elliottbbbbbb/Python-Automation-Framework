# Installation Guide for RuneLite Status Socket Plugin

## Quick Install (For Using the Plugin)

If you just want to use the plugin with your bot (not develop it), follow these steps:

### Step 1: Copy the Plugin JAR

```cmd
# Create the externalplugins directory if it doesn't exist
mkdir %USERPROFILE%\.runelite\externalplugins

# Copy the plugin JAR
copy build\libs\runelite-status-socket-1.0.0.jar %USERPROFILE%\.runelite\externalplugins\
```

### Step 2: Restart RuneLite

- Close RuneLite completely
- Start RuneLite again

### Step 3: Enable the Plugin

1. Click the wrench icon (Configuration) in RuneLite
2. In the search box, type "Status Socket"
3. Toggle the plugin ON (switch to green)
4. You should see it in the plugin list on the left sidebar

### Step 4: Verify It's Working

1. Log into OSRS
2. Check that the file exists:
   ```cmd
   dir %USERPROFILE%\.runelite\live_data.json
   ```
3. View the contents:
   ```cmd
   type %USERPROFILE%\.runelite\live_data.json
   ```

   You should see JSON output like:
   ```json
   {"worldPoint":{"x":3200,"y":3400,"plane":0},"camera":{"yaw":512,"pitch":256},"animation":-1,"isMoving":false,"timestamp":1704376800000}
   ```

### Step 5: Test with Python Bot

Run this test script:

```python
from osrsbot.services.status_socket_service import StatusSocketService

service = StatusSocketService("C:\\Users\\elliott\\.runelite\\live_data.json")

if service.is_available():
    print("✓ Plugin working!")
    state = service.get_player_state()
    print(f"Position: ({state.world_x}, {state.world_y})")
else:
    print("✗ Plugin not working - check RuneLite")
```

## Done!

Your bot can now use pathfinding features:
- `actions.walk_to_world_coordinate(x, y)`
- `actions.walk_path(waypoints)`

---

## For Developers (Editing the Plugin Code)

If you want to modify the plugin source code, the red errors in your IDE are expected because it doesn't know about the Gradle dependencies yet.

### Fix IDE Errors (IntelliJ IDEA)

1. Open IntelliJ IDEA
2. File → Open → Select `runelite-status-socket` folder
3. When prompted "Import Gradle project?", click **Yes**
4. Wait for Gradle to download dependencies
5. Errors should disappear

### Fix IDE Errors (VS Code)

1. Install "Extension Pack for Java" from VS Code extensions
2. Open `runelite-status-socket` folder in VS Code
3. Press Ctrl+Shift+P
4. Type "Java: Clean Java Language Server Workspace"
5. Restart VS Code
6. Gradle will auto-import dependencies

### Fix IDE Errors (Eclipse)

1. File → Import → Existing Gradle Project
2. Select `runelite-status-socket` folder
3. Click Finish
4. Wait for Gradle sync

### Rebuild After Making Changes

```bash
cd runelite-status-socket

# Build new JAR
gradle-7.6/bin/gradle build

# Copy to RuneLite
copy build\libs\runelite-status-socket-1.0.0.jar %USERPROFILE%\.runelite\externalplugins\

# Restart RuneLite to load new version
```

---

## Troubleshooting

### "Plugin not found" after copying JAR

- Make sure you copied to the correct path: `%USERPROFILE%\.runelite\externalplugins\`
- Restart RuneLite completely (not just logout/login)
- Check the file is actually there: `dir %USERPROFILE%\.runelite\externalplugins\`

### Plugin appears but won't enable

- Check RuneLite console for errors (View → Show Developer Tools → Console)
- Make sure you're using Java 11+ (RuneLite requirement)
- Try deleting and re-copying the JAR

### JSON file not updating

- Make sure you're logged into OSRS (not on login screen)
- Check plugin is enabled (green toggle)
- Look for errors in RuneLite console

### Python bot can't find file

- Verify path in `config.json` matches plugin output path
- Default plugin path: `C:\Users\elliott\.runelite\live_data.json`
- Default Python config expects: same path (already configured)

### IDE still shows errors after importing

- Run `gradle-7.6/bin/gradle clean build` to refresh
- Try "Reload All Gradle Projects" in IDE
- Make sure Java 11 is set as project SDK
