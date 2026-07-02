from __future__ import annotations

import os
import sys
from pathlib import Path


def app_data_dir() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "CupGuard"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home())) / "CupGuard"
    else:
        base = Path.home() / ".config" / "cup-guard"
    base.mkdir(parents=True, exist_ok=True)
    return base


def config_path() -> Path:
    return app_data_dir() / "config.json"


def debug_image_path() -> Path:
    return app_data_dir() / "calibration_debug.png"


def asset_path(name: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    else:
        base = Path(__file__).resolve().parent
    return base / "assets" / name
