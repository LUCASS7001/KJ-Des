"""
core/diagnostics.py
Logging setup and crash reporting for KJ Des.

The activity log (%APPDATA%\\KJ Des\\kjdes.log) is size-capped by the inherited
LogManager (~1 MB, oldest half dropped). It records every network
modification (DNS set/restore per adapter, hosts write/remove, recovery task,
relay start/stop) and engine diagnostics. No message content, account data or
user IP is logged.
"""
from __future__ import annotations

import os
import platform
import sys
import traceback
from datetime import datetime

from core.app_info import APP_VERSION
from core.log_manager import LogManager
from core.paths import user_data_path

LOG_FILE = "kjdes.log"
CRASH_FILE = "crash.log"


def create_log(enabled: bool = True) -> LogManager:
    return LogManager(user_data_path(LOG_FILE), enabled=enabled,
                      mirror_console=not getattr(sys, "frozen", False))


def session_header(admin: bool) -> str:
    mode = "installed" if getattr(sys, "frozen", False) else "source"
    return (f"SESSION | KJ Des v{APP_VERSION} started | mode={mode} | pid={os.getpid()} | "
            f"admin={admin} | windows={platform.release()} ({platform.version()}) | "
            f"python={platform.python_version()}")


def write_crash(exc_text: str | None = None) -> str:
    """Append a traceback to crash.log; returns the last line for display."""
    text = exc_text or traceback.format_exc()
    try:
        path = user_data_path(CRASH_FILE)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"--- {datetime.now().isoformat(timespec='seconds')} v{APP_VERSION}\n{text}\n")
    except Exception:
        pass
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else "?"
