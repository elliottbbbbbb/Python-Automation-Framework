package com.osrsbot.statussocket;

import lombok.extern.slf4j.Slf4j;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Thread-safe file writer with atomic write operations.
 * Uses temp file + atomic rename pattern to prevent partial reads.
 */
@Slf4j
public class FileWriteService {
    private final Path outputFile;
    private final Path tempFile;
    private final ReentrantLock writeLock = new ReentrantLock();

    public FileWriteService(Path outputFile) {
        this.outputFile = outputFile;
        this.tempFile = outputFile.resolveSibling(outputFile.getFileName() + ".tmp");

        // Ensure parent directory exists
        try {
            if (outputFile.getParent() != null) {
                Files.createDirectories(outputFile.getParent());
            }
        } catch (IOException e) {
            log.error("Failed to create output directory: {}", outputFile.getParent(), e);
        }
    }

    /**
     * Write player state to file atomically.
     * Uses temp file + rename to prevent partial reads by Python bot.
     *
     * @param state Player state to write
     */
    public void writeState(PlayerStateData state) {
        writeLock.lock();
        try {
            String json = state.toJson();
            byte[] bytes = json.getBytes(StandardCharsets.UTF_8);

            // Write to temp file first
            Files.write(tempFile, bytes,
                StandardOpenOption.CREATE,
                StandardOpenOption.TRUNCATE_EXISTING);

            // Atomic rename (Windows: need to delete existing file first)
            if (Files.exists(outputFile)) {
                Files.delete(outputFile);
            }
            Files.move(tempFile, outputFile,
                StandardCopyOption.ATOMIC_MOVE,
                StandardCopyOption.REPLACE_EXISTING);

        } catch (IOException e) {
            log.error("Failed to write state file: {}", outputFile, e);
        } finally {
            writeLock.unlock();
        }
    }

    /**
     * Clean up files on plugin shutdown.
     */
    public void cleanup() {
        writeLock.lock();
        try {
            Files.deleteIfExists(outputFile);
            Files.deleteIfExists(tempFile);
            log.debug("Cleaned up output files");
        } catch (IOException e) {
            log.error("Failed to cleanup files", e);
        } finally {
            writeLock.unlock();
        }
    }
}
