"""Filesystem locations for user data.

Everything the app writes lives under a single per-user directory so an
uninstall is one ``rm -rf``. Nothing is ever written next to the bundled
code, which matters once the app runs from a read-only ``.app`` bundle.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "TypeScholar"


def user_data_dir() -> Path:
    """Return the per-user data directory, creating it if needed."""
    override = os.environ.get("TYPING_ADVENTURE_DATA_DIR")
    if override:
        base = Path(override).expanduser()
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    elif sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home())) / APP_DIR_NAME
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        base = (Path(xdg) if xdg else Path.home() / ".local" / "share") / APP_DIR_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def settings_path() -> Path:
    return user_data_dir() / "settings.json"


def database_path() -> Path:
    return user_data_dir() / "progress.sqlite3"


def sound_cache_dir() -> Path:
    path = user_data_dir() / "sounds"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_path() -> Path:
    return user_data_dir() / "type-scholar.log"


def bundled_assets_dir() -> Path:
    """Locate bundled assets, both in-repo and inside a PyInstaller bundle."""
    frozen_base = getattr(sys, "_MEIPASS", None)
    if frozen_base:
        return Path(frozen_base) / "assets"
    return Path(__file__).resolve().parent / "assets"
