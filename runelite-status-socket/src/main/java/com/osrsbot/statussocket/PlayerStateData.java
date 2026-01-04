package com.osrsbot.statussocket;

import lombok.Builder;
import lombok.Value;

/**
 * Player state data captured from RuneLite client.
 * Immutable data class representing player position, camera, and animation state.
 */
@Value
@Builder
public class PlayerStateData {
    int worldX;
    int worldY;
    int plane;
    int cameraYaw;
    int cameraPitch;
    int animationId;
    boolean isMoving;
    long timestamp;

    /**
     * Serialize to JSON format expected by Python StatusSocketService.
     *
     * Expected format:
     * {
     *   "worldPoint": {"x": 3200, "y": 3400, "plane": 0},
     *   "camera": {"yaw": 512, "pitch": 256},
     *   "animation": -1,
     *   "isMoving": false,
     *   "timestamp": 1234567890
     * }
     *
     * @return JSON string representation
     */
    public String toJson() {
        return String.format(
            "{\"worldPoint\":{\"x\":%d,\"y\":%d,\"plane\":%d}," +
            "\"camera\":{\"yaw\":%d,\"pitch\":%d}," +
            "\"animation\":%d," +
            "\"isMoving\":%s," +
            "\"timestamp\":%d}",
            worldX, worldY, plane,
            cameraYaw, cameraPitch,
            animationId,
            isMoving,
            timestamp
        );
    }
}
