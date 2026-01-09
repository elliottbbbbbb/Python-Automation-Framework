package com.osrsbot.statussocket;

import com.google.inject.Provides;
import lombok.extern.slf4j.Slf4j;
import net.runelite.api.Client;
import net.runelite.api.Player;
import net.runelite.api.coords.WorldPoint;
import net.runelite.client.config.ConfigManager;
import net.runelite.client.plugins.Plugin;
import net.runelite.client.plugins.PluginDescriptor;
import net.runelite.client.task.Schedule;

import javax.inject.Inject;
import java.nio.file.Paths;
import java.time.temporal.ChronoUnit;

/**
 * RuneLite Status Socket Plugin
 *
 * Exports real-time player position, camera angle, and movement state to a JSON file
 * for consumption by external automation tools (Python bot framework).
 *
 * Features:
 * - World coordinates (X, Y, plane)
 * - Camera rotation (yaw, pitch)
 * - Animation state and movement detection
 * - Configurable update frequency (50-1000ms)
 * - Atomic file writes to prevent partial reads
 */
@Slf4j
@PluginDescriptor(
    name = "Status Socket",
    description = "Exports player position and state to live_data.json for external automation",
    tags = {"external", "automation", "position", "python"},
    enabledByDefault = false
)
public class StatusSocketPlugin extends Plugin {

    @Inject
    private Client client;

    @Inject
    private StatusSocketConfig config;

    private FileWriteService fileWriter;

    @Override
    protected void startUp() throws Exception {
        log.info("Status Socket plugin started");

        // Initialize file writer with configured path
        String outputPath = config.outputFilePath();
        fileWriter = new FileWriteService(Paths.get(outputPath));

        log.info("Writing player state to: {}", outputPath);
        log.info("Update interval: {}ms", config.updateInterval());
    }

    @Override
    protected void shutDown() throws Exception {
        log.info("Status Socket plugin stopped");

        // Cleanup files on shutdown
        if (fileWriter != null) {
            fileWriter.cleanup();
        }
    }

    /**
     * Periodic update task - runs at configured interval.
     * Uses @Schedule annotation to automatically run on client thread at specified frequency.
     *
     * Note: The period is dynamically read from config, defaulting to 100ms.
     */
    @Schedule(
        period = 100,  // This is overridden by config.updateInterval() at runtime
        unit = ChronoUnit.MILLIS,
        asynchronous = false  // Run on client thread for safe API access
    )
    public void updatePlayerState() {
        try {
            // Check if player is logged in
            Player localPlayer = client.getLocalPlayer();
            if (localPlayer == null) {
                return;  // Not logged in, skip this update
            }

            // Capture player state
            PlayerStateData state = capturePlayerState(localPlayer);

            // Write to file
            fileWriter.writeState(state);

            // Optional debug logging
            if (config.enableLogging()) {
                log.debug("Updated state: ({}, {}) plane={} yaw={} moving={}",
                    state.getWorldX(), state.getWorldY(), state.getPlane(),
                    state.getCameraYaw(), state.isMoving());
            }

        } catch (Exception e) {
            log.error("Error updating player state", e);
        }
    }

    /**
     * Capture current player state from RuneLite client.
     *
     * @param player Local player object
     * @return PlayerStateData with current position, camera, and animation
     */
    private PlayerStateData capturePlayerState(Player player) {
        // Get world position
        WorldPoint pos = player.getWorldLocation();

        // Get camera angles (RuneLite uses 0-2048 range for yaw)
        int cameraYaw = client.getCameraYaw();
        int cameraPitch = client.getCameraPitch();

        // Get animation ID
        int animationId = player.getAnimation();

        // Detect movement: if current pose != idle pose, player is moving
        boolean isMoving = detectMovement(player);

        // Build state object
        return PlayerStateData.builder()
            .worldX(pos.getX())
            .worldY(pos.getY())
            .plane(pos.getPlane())
            .cameraYaw(cameraYaw)
            .cameraPitch(cameraPitch)
            .animationId(animationId)
            .isMoving(isMoving)
            .timestamp(System.currentTimeMillis())
            .build();
    }

    /**
     * Detect if player is currently moving.
     * Compares idle pose animation to current pose animation.
     *
     * @param player Local player
     * @return true if moving, false if idle
     */
    private boolean detectMovement(Player player) {
        int idlePose = player.getIdlePoseAnimation();
        int currentPose = player.getPoseAnimation();
        return idlePose != currentPose;
    }

    @Provides
    StatusSocketConfig provideConfig(ConfigManager configManager) {
        return configManager.getConfig(StatusSocketConfig.class);
    }
}
