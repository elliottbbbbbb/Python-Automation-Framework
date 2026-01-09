package com.osrsbot.statussocket;

import net.runelite.client.config.Config;
import net.runelite.client.config.ConfigGroup;
import net.runelite.client.config.ConfigItem;
import net.runelite.client.config.Range;

/**
 * Configuration interface for Status Socket plugin.
 * Provides user-configurable options for file path, update frequency, and features.
 */
@ConfigGroup("statussocket")
public interface StatusSocketConfig extends Config {

    @ConfigItem(
        keyName = "outputFilePath",
        name = "Output File Path",
        description = "Where to write live_data.json. Use absolute path or leave default for .runelite folder."
    )
    default String outputFilePath() {
        // Default: .runelite folder in user home
        String userHome = System.getProperty("user.home");
        String runeliteDir = userHome + "/.runelite";
        return runeliteDir + "/live_data.json";
    }

    @ConfigItem(
        keyName = "updateInterval",
        name = "Update Interval (ms)",
        description = "How often to update the file (milliseconds). Lower = more responsive but higher CPU usage."
    )
    @Range(min = 50, max = 1000)
    default int updateInterval() {
        return 100;  // 10 updates per second
    }

    @ConfigItem(
        keyName = "enableLogging",
        name = "Enable Debug Logging",
        description = "Log each update to RuneLite console (for debugging)."
    )
    default boolean enableLogging() {
        return false;
    }

    @ConfigItem(
        keyName = "includeExtendedData",
        name = "Include Extended Data",
        description = "Include camera pitch and timestamp in JSON output."
    )
    default boolean includeExtendedData() {
        return true;
    }
}
