"""
Path resolution utilities for template images.

Centralizes all template path resolution so it works consistently
in both development mode and PyInstaller .exe mode.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache the package root so we don't recompute it every call
# In dev: src/osrsbot/
# In exe: sys._MEIPASS/osrsbot/
_PACKAGE_ROOT: Path | None = None


def _get_package_root() -> Path:
    """Get the osrsbot package root directory."""
    global _PACKAGE_ROOT
    if _PACKAGE_ROOT is not None:
        return _PACKAGE_ROOT

    if getattr(sys, "frozen", False):
        _PACKAGE_ROOT = Path(sys._MEIPASS) / "osrsbot"
    else:
        # path_helpers.py is at src/osrsbot/utils/path_helpers.py
        # .parent = utils/, .parent.parent = src/osrsbot/
        _PACKAGE_ROOT = Path(__file__).resolve().parent.parent

    return _PACKAGE_ROOT


def resolve_template_path(template_path: str) -> Path:
    """
    Resolve template path for both development and .exe environments.

    Anchors all paths relative to the osrsbot package directory, so resolution
    works regardless of the current working directory.

    Supports three path formats:
    1. Custom user images: 'custom:my_item.png' -> looks in user_images/ folder next to exe
    2. Short bundled paths: 'images/bot/items/my_item.png' -> resolved from package root
    3. Full bundled paths: 'src/osrsbot/images/bot/items/my_item.png' -> prefix stripped, resolved from package root

    When running as .exe:
    - 'custom:' paths resolve to './user_images/' folder (created if missing)
    - Bundled paths resolve to _MEIPASS directory

    Args:
        template_path: Original template path (relative or absolute)
                      Examples:
                      - 'custom:my_custom_item.png' (user images folder)
                      - 'images/bot/items/my_item.png' (resolved from package root)
                      - 'src/osrsbot/images/bot/items/my_item.png' (prefix stripped automatically)

    Returns:
        Resolved Path object
    """
    resolved_path = Path(template_path)

    # Skip resolution if already an absolute path
    if resolved_path.is_absolute():
        return resolved_path

    # Normalize path to use forward slashes for comparison (Windows uses backslashes)
    normalized_path = template_path.replace("\\", "/")

    # Handle 'custom:' prefix for user images
    if normalized_path.startswith("custom:"):
        custom_filename = normalized_path.replace("custom:", "", 1)

        if getattr(sys, "frozen", False):
            user_images_dir = Path(sys.executable).parent / "user_images"
        else:
            # Project root is 4 levels up from this file:
            # src/osrsbot/utils/path_helpers.py -> project root
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            user_images_dir = project_root / "user_images"

        user_images_dir.mkdir(exist_ok=True)

        resolved_path = user_images_dir / custom_filename
        logger.debug(f"Resolved custom template: {template_path} -> {resolved_path}")
        return resolved_path

    # Strip 'src/osrsbot/' prefix if present - we resolve from package root
    if normalized_path.startswith("src/osrsbot/"):
        normalized_path = normalized_path[len("src/osrsbot/"):]

    resolved_path = _get_package_root() / normalized_path

    logger.debug(f"Resolved template: {template_path} -> {resolved_path}")
    return resolved_path
