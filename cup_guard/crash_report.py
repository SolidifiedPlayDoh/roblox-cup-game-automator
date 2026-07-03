"""Log startup failures and show a macOS alert when the GUI would otherwise vanish."""

from __future__ import annotations

import platform
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path


def log_dir() -> Path:
    path = Path.home() / "Library" / "Logs" / "CupGuard"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_path() -> Path:
    return log_dir() / "launch.log"


def _append(text: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_path().open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {text}\n")


def notify(title: str, message: str) -> None:
    _append(f"{title}: {message}")
    if sys.platform != "darwin":
        print(f"{title}\n{message}", file=sys.stderr)
        return
    safe_title = title.replace('"', '\\"')
    safe_message = message.replace('"', '\\"').replace("\n", "\\n")
    script = (
        f'display dialog "{safe_message}" with title "{safe_title}" '
        'buttons {"OK"} default button 1 with icon caution'
    )
    try:
        subprocess.run(["osascript", "-e", script], check=False)
    except Exception:
        pass


def install_handlers() -> None:
    import faulthandler

    try:
        faulthandler.enable(log_path().open("a", encoding="utf-8"))
    except Exception:
        faulthandler.enable()

    def excepthook(exc_type, exc, tb) -> None:
        report_exception(exc_type, exc, tb)

    sys.excepthook = excepthook


def report_exception(exc_type, exc, tb) -> None:
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    _append(f"Unhandled exception:\n{text}")
    notify(
        "Cup Guard crashed",
        f"Something went wrong on launch.\n\nDetails were saved to:\n{log_path()}",
    )


def check_mac_compatibility() -> str | None:
    if sys.platform != "darwin":
        return None
    if platform.machine() != "arm64":
        return (
            "This Cup Guard build only runs on Apple Silicon Macs (M1/M2/M3/M4).\n\n"
            "Your Mac appears to be Intel. Ask for the Intel build or run from source."
        )
    return None
