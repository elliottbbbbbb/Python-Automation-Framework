import json
import logging
import sys
from pathlib import Path
from typing import Any

from osrsbot.models.config_defaults import get_defaults

logger = logging.getLogger(__name__)


def _deep_merge(base: dict, override: dict) -> None:
    """
    Recursively merge *override* into *base* in-place.

    - Dicts are merged recursively so nested keys are preserved.
    - Any other type (str, list, int, bool) in override replaces base.
    - Keys present only in base are kept untouched.
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


class Config:
    """
    Centralized configuration for the OSRS bot.

    Load order:
      1. Start from get_defaults() — complete baseline, every key present.
      2. Deep-merge the user's config.json on top (only overrides need to exist).
      3. If no user config exists yet, write defaults to disk as a starting template.

    This means:
      - Users only need to set what differs from defaults (account_name, colors, …).
      - Adding new keys to get_defaults() just works for everyone automatically.
      - Template image paths fall back to the bundled developer images.
    """

    def __init__(self, config_file: str = None) -> None:
        self.config_file = self._resolve_path(config_file)
        self.data = self._load()

    # ── Path resolution ───────────────────────────────────────────────────────

    @staticmethod
    def _resolve_path(config_file: str = None) -> Path:
        if config_file is not None:
            return Path(config_file)

        if getattr(sys, "frozen", False):
            # Exe: prefer config.json next to OSRS_Bot.exe
            external = Path(sys.executable).parent / "config.json"
            if external.exists():
                logger.info(f"Using user config: {external}")
                return external
            # Fall back to writing defaults next to the exe on first run
            return Path(sys.executable).parent / "config.json"

        # Dev mode: use src/osrsbot/config.json
        return Path(__file__).parent.parent / "config.json"

    # ── Load / save ───────────────────────────────────────────────────────────

    def _load(self) -> dict:
        # Always start from the full defaults
        data = get_defaults()

        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                _deep_merge(data, user_config)
                logger.info(f"Loaded user config from {self.config_file}")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load config ({self.config_file}): {e} — using defaults")
        else:
            # First run: write defaults to disk so user can see what's configurable
            logger.info(f"No config found — writing defaults to {self.config_file}")
            try:
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                logger.info("Default config written. Edit it to customise your setup.")
            except IOError as e:
                logger.warning(f"Could not write default config: {e}")

        return data

    def save(self) -> bool:
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            return True
        except IOError as e:
            logger.error(f"Failed to save config: {e}")
            return False

    # ── Accessors ─────────────────────────────────────────────────────────────

    def get(self, *path, default: Any = None) -> Any:
        current = self.data
        try:
            for key in path:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default

    def get_window_title(self) -> str:
        # If an explicit window_title was set at runtime (e.g. by menu/runner), use it directly
        explicit = self.data.get("window_title")
        if explicit:
            return explicit
        account_name = self.get("account_name", default="")
        if not account_name or account_name == "YourAccountName":
            logger.warning("account_name not set in config.json — defaulting to 'RuneLite - '")
            return "RuneLite - "
        return f"RuneLite - {account_name}"
