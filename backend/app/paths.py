"""Writable paths for the bundled and development backends."""

from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    raw = (os.environ.get("SAVUOR_DATA_DIR") or "").strip()
    if raw:
        path = Path(raw)
    elif os.name == "nt":
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        path = Path(appdata) / "Savuor"
    else:
        path = Path.home() / ".savuor"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
