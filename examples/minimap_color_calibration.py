"""
Minimap Color Calibration Tool

Interactive tool to help calibrate walkable/non-walkable colors for your
specific OSRS client setup.
"""

import cv2
import numpy as np
import pyautogui


def main():
    """Run color calibration tool"""
    print("=== OSRS Minimap Color Calibration Tool ===\n")

    # Step 1: Capture minimap
    print("Step 1: Capture Minimap")
    print("Move your mouse to the CENTER of the minimap and press Enter...")
    input()

    mouse_x, mouse_y = pyautogui.position()
    print(f"Minimap center: ({mouse_x}, {mouse_y})")

    # Capture minimap region
    radius = 73
    minimap_img = capture_minimap(mouse_x, mouse_y, radius)

    # Save original
    cv2.imwrite("minimap_captured.png", minimap_img)
    print(f"✓ Minimap captured and saved to minimap_captured.png\n")

    # Step 2: Analyze colors
    print("Step 2: Analyze Colors")
    analyze_colors(minimap_img)

    # Step 3: Interactive color picker
    print("\nStep 3: Interactive Color Picker")
    print("Click on different parts of the minimap to see their colors")
    print("This will help you identify walkable vs non-walkable color ranges\n")

    interactive_color_picker(minimap_img)


def capture_minimap(center_x: int, center_y: int, radius: int) -> np.ndarray:
    """
    Capture minimap from screen

    Args:
        center_x: X coordinate of minimap center
        center_y: Y coordinate of minimap center
        radius: Radius of minimap circle

    Returns:
        Minimap image as numpy array (BGR)
    """
    # Capture region
    screenshot = pyautogui.screenshot(
        region=(center_x - radius, center_y - radius, radius * 2, radius * 2)
    )

    # Convert to numpy array (BGR for OpenCV)
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    return img


def analyze_colors(minimap_img: np.ndarray):
    """
    Analyze color distribution in minimap

    Args:
        minimap_img: Minimap image (BGR)
    """
    # Convert to different color spaces
    hsv = cv2.cvtColor(minimap_img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(minimap_img, cv2.COLOR_BGR2GRAY)

    print("Color Statistics:")
    print(
        f"  BGR - Min: {minimap_img.min(axis=(0, 1))}, Max: {minimap_img.max(axis=(0, 1))}"
    )
    print(f"  HSV - Min: {hsv.min(axis=(0, 1))}, Max: {hsv.max(axis=(0, 1))}")
    print(f"  Grayscale - Min: {gray.min()}, Max: {gray.max()}")

    # Find dominant colors
    print("\nDominant Colors (BGR):")
    pixels = minimap_img.reshape(-1, 3)

    # Get unique colors and their counts
    unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)

    # Sort by frequency
    sorted_indices = np.argsort(counts)[::-1]

    # Print top 10 colors
    for i in range(min(10, len(unique_colors))):
        idx = sorted_indices[i]
        color = unique_colors[idx]
        count = counts[idx]
        percentage = 100 * count / pixels.shape[0]

        print(
            f"  {i + 1}. BGR({color[0]:3d}, {color[1]:3d}, {color[2]:3d}) - {percentage:.1f}%"
        )


def interactive_color_picker(minimap_img: np.ndarray):
    """
    Interactive color picker - click on image to see colors

    Args:
        minimap_img: Minimap image (BGR)
    """
    # Create window
    window_name = "Minimap Color Picker (Click to sample, ESC to quit)"
    cv2.namedWindow(window_name)

    # Mouse callback
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Get color at clicked position
            bgr = minimap_img[y, x]
            rgb = (bgr[2], bgr[1], bgr[0])

            # Convert to HSV
            hsv = cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0][0]

            print(f"Clicked at ({x}, {y}):")
            print(f"  BGR: ({bgr[0]}, {bgr[1]}, {bgr[2]})")
            print(f"  RGB: ({rgb[0]}, {rgb[1]}, {rgb[2]})")
            print(f"  HSV: ({hsv[0]}, {hsv[1]}, {hsv[2]})")
            print(f"  Hex: #{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}")
            print()

            # Create color swatch
            swatch = np.full((100, 100, 3), bgr, dtype=np.uint8)
            cv2.imshow("Color Swatch", swatch)

    cv2.setMouseCallback(window_name, mouse_callback)

    # Show image
    print("Click on the minimap to sample colors")
    print("Press ESC when done\n")

    while True:
        cv2.imshow(window_name, minimap_img)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break

    cv2.destroyAllWindows()

    print("\nSuggested color ranges based on your samples:")
    print("(Update these in minimap_service.py)")
    print(
        """
WALKABLE_COLORS = {
    'grass': [(40, 80, 40), (80, 150, 80)],      # Light green grass
    'path': [(60, 60, 40), (100, 100, 70)],      # Brown/tan paths
}

NON_WALKABLE_COLORS = {
    'tree': [(20, 40, 20), (40, 70, 40)],        # Dark green trees
    'wall': [(30, 30, 30), (60, 60, 60)],        # Gray walls
}
    """
    )


def generate_color_masks(minimap_img: np.ndarray):
    """
    Generate color masks for different terrain types

    Args:
        minimap_img: Minimap image (BGR)
    """
    # Walkable areas (green/light areas)
    lower_walkable = np.array([40, 80, 40], dtype=np.uint8)
    upper_walkable = np.array([80, 150, 80], dtype=np.uint8)
    walkable_mask = cv2.inRange(minimap_img, lower_walkable, upper_walkable)

    # Non-walkable areas (dark/obstacles)
    lower_obstacle = np.array([20, 40, 20], dtype=np.uint8)
    upper_obstacle = np.array([40, 70, 40], dtype=np.uint8)
    obstacle_mask = cv2.inRange(minimap_img, lower_obstacle, upper_obstacle)

    # Save masks
    cv2.imwrite("mask_walkable.png", walkable_mask)
    cv2.imwrite("mask_obstacles.png", obstacle_mask)

    print("✓ Color masks saved:")
    print("  - mask_walkable.png")
    print("  - mask_obstacles.png")

    # Show masks
    cv2.imshow("Walkable Areas", walkable_mask)
    cv2.imshow("Obstacles", obstacle_mask)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
