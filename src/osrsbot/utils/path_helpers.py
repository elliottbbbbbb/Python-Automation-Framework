"""
Path resolution utilities for template images.

Centralizes all template path resolution so it works consistently
in both development mode and PyInstaller .exe mode.

User overrides: place an image with the same relative filename inside a
`user_images/` folder next to the exe (or project root in dev mode) and it
will be used instead of the bundled version automatically.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache roots so we don't recompute every call
_PACKAGE_ROOT: Path | None = None
_USER_IMAGES_DIR: Path | None = None


def _get_package_root() -> Path:
    global _PACKAGE_ROOT
    if _PACKAGE_ROOT is None:
        if getattr(sys, "frozen", False):
            _PACKAGE_ROOT = Path(sys._MEIPASS) / "osrsbot"
        else:
            # path_helpers.py lives at src/osrsbot/utils/path_helpers.py
            _PACKAGE_ROOT = Path(__file__).resolve().parent.parent
    return _PACKAGE_ROOT


def _get_user_images_dir() -> Path:
    global _USER_IMAGES_DIR
    if _USER_IMAGES_DIR is None:
        if getattr(sys, "frozen", False):
            _USER_IMAGES_DIR = Path(sys.executable).parent / "user_images"
        else:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            _USER_IMAGES_DIR = project_root / "user_images"
        _USER_IMAGES_DIR.mkdir(exist_ok=True)
    return _USER_IMAGES_DIR


def resolve_template_path(template_path: str) -> Path:
    """
    Resolve a template image path for both development and .exe environments.

    Resolution order:
    1. Absolute paths are returned as-is.
    2. user_images/<relative_path> next to the exe — if it exists, it wins.
    3. Bundled image from the package (inside the exe or src/osrsbot/).

    To override any bundled image, place a file with the same relative path
    inside the user_images/ folder next to the exe.  For example, to override
    'images/bot/items/prayer_potion.png', place your replacement at:
        user_images/images/bot/items/prayer_potion.png

    The 'src/osrsbot/' prefix is stripped automatically if present.
    """
    resolved = Path(template_path)

    if resolved.is_absolute():
        return resolved

    normalized = template_path.replace("\\", "/")

    # Strip legacy src/osrsbot/ prefix if present
    if normalized.startswith("src/osrsbot/"):
        normalized = normalized[len("src/osrsbot/"):]

    # Check user_images/ override first
    user_override = _get_user_images_dir() / normalized
    if user_override.exists():
        logger.debug(f"User override found: {template_path} -> {user_override}")
        return user_override

    bundled = _get_package_root() / normalized
    logger.debug(f"Resolved template: {template_path} -> {bundled}")
    return bundled
