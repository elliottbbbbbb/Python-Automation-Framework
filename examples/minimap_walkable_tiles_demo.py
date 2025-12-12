"""
Demo: Extract Walkable Tiles from Minimap

This example shows how to use MinimapService to convert the OSRS minimap
into a grid of walkable tiles.
"""

import cv2
import numpy as np
from osrsbot.services.minimap_service import MinimapService
from osrsbot.services.screen_service import ScreenService
from osrsbot.core.game_interface import GameInterface
from osrsbot.models.config import Config


def main():
    """Run minimap walkable tiles demo"""

    # Initialize services
    config = Config.load("config.json")
    interface = GameInterface(config)
    screen = ScreenService(interface, config)
    minimap = MinimapService(screen)

    # Minimap center coordinates (adjust for your setup)
    # Typically top-right corner of game window
    minimap_center = (1450, 100)  # Example coordinates

    print("Extracting walkable tiles from minimap...")
    print(f"Minimap center: {minimap_center}")

    # Extract walkable tiles (with debug output)
    tile_grid = minimap.extract_walkable_tiles(
        minimap_center,
        debug=True  # Saves debug images to debug/minimap/
    )

    # Print grid dimensions
    print(f"\nTile grid shape: {tile_grid.shape}")
    print(f"Total tiles: {tile_grid.size}")
    print(f"Walkable tiles: {np.sum(tile_grid)}")
    print(f"Non-walkable tiles: {tile_grid.size - np.sum(tile_grid)}")
    print(f"Walkability percentage: {100 * np.sum(tile_grid) / tile_grid.size:.1f}%")

    # Print grid as ASCII art
    print("\nWalkable tile grid (. = walkable, # = non-walkable):")
    print_tile_grid_ascii(tile_grid)

    # Example: Check if specific tiles are walkable
    print("\nChecking specific tiles:")
    center_tile = (tile_grid.shape[1] // 2, tile_grid.shape[0] // 2)
    print(f"Center tile {center_tile}: {'Walkable' if tile_grid[center_tile[1], center_tile[0]] else 'Blocked'}")

    # Example: Find path between two points
    print("\nFinding path from center to edge...")
    start = (tile_grid.shape[1] // 2, tile_grid.shape[0] // 2)
    goal = (tile_grid.shape[1] - 5, tile_grid.shape[0] // 2)

    path = minimap.find_walkable_path(tile_grid, start, goal)

    if path:
        print(f"Path found! {len(path)} steps")
        print(f"Path: {path[:5]}... (showing first 5 steps)")
    else:
        print("No path found (goal might be blocked)")

    print("\n✓ Debug images saved to debug/minimap/")
    print("  - minimap_original.png: Original minimap")
    print("  - minimap_walkable_mask.png: Walkable area detection")
    print("  - minimap_tile_grid.png: Tile grid overlay")


def print_tile_grid_ascii(tile_grid: np.ndarray, max_size: int = 40):
    """
    Print tile grid as ASCII art

    Args:
        tile_grid: 2D boolean array of walkable tiles
        max_size: Maximum dimension for display
    """
    h, w = tile_grid.shape

    # Downsample if too large
    if h > max_size or w > max_size:
        scale = max(h / max_size, w / max_size)
        new_h = int(h / scale)
        new_w = int(w / scale)

        # Resize
        downsampled = np.zeros((new_h, new_w), dtype=bool)
        for i in range(new_h):
            for j in range(new_w):
                orig_i = int(i * scale)
                orig_j = int(j * scale)
                downsampled[i, j] = tile_grid[orig_i, orig_j]

        tile_grid = downsampled

    # Print grid
    for row in tile_grid:
        line = ""
        for cell in row:
            line += "." if cell else "#"
        print(line)


def calibrate_minimap_center():
    """
    Interactive tool to find minimap center coordinates

    Returns:
        Tuple of (x, y) coordinates for minimap center
    """
    import pyautogui

    print("Move your mouse to the CENTER of the minimap and press Enter...")
    input()

    x, y = pyautogui.position()
    print(f"Minimap center captured: ({x}, {y})")

    return x, y


def visualize_walkable_areas_realtime():
    """
    Real-time visualization of walkable areas

    Updates every second to show current walkable tiles
    """
    import time

    config = Config.load("config.json")
    interface = GameInterface(config)
    screen = ScreenService(interface, config)
    minimap = MinimapService(screen)

    minimap_center = calibrate_minimap_center()

    print("\nReal-time walkable tile visualization")
    print("Press Ctrl+C to stop")

    try:
        while True:
            # Extract tiles
            tile_grid = minimap.extract_walkable_tiles(minimap_center, debug=False)

            # Clear screen and print
            print("\033[2J\033[H")  # Clear screen (ANSI escape code)
            print("Walkable Tiles (updating every 1s):")
            print_tile_grid_ascii(tile_grid)

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    # Run basic demo
    main()

    # Uncomment to run real-time visualization
    # visualize_walkable_areas_realtime()
