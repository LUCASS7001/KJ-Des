"""
security/elevation.py
Administrator detection and UAC elevation (inherited from the original main.py).

KJ Des needs administrator rights because changing adapter DNS, writing the
protected hosts file, the ACL-protected recovery store and the logon recovery
task all require them. Nothing else runs elevated.
"""
import ctypes
import sys


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_args() -> str:
    args = sys.argv[1:] if getattr(sys, "frozen", False) else sys.argv
    return " ".join(f'"{a}"' for a in args)


def elevate() -> bool:
    """Restart the current process elevated. True if the elevated process was
    launched; ShellExecuteW returns <= 32 on failure (e.g. UAC declined)."""
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, relaunch_args(), None, 1)
        return int(rc) > 32
    except Exception:
        return False
