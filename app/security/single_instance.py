"""
security/single_instance.py
Duplicate-process prevention (inherited protocol, KJ Des's own identifiers).

Two layers:
  1. A named Windows mutex (atomic; defeats double-click races).
  2. A loopback IPC listener with an exact request/ACK handshake so a second
     launch can bring the running window to the front. Merely being able to
     connect to the port is NOT treated as "already running".
"""
import socket
import threading
from typing import Callable, Optional

IPC_HOST = "127.0.0.1"
IPC_PORT = 49327
IPC_MAGIC = b"KJDES-IPC-1"
IPC_REQUEST = IPC_MAGIC + b" SHOW\n"
IPC_ACK = IPC_MAGIC + b" OK\n"
IPC_TIMEOUT = 1.5
MUTEX_NAME = "KJDes_SingleInstance_v1"


def signal_existing(port: int = IPC_PORT) -> bool:
    """Ask a running instance to show itself. True only on a valid ACK."""
    try:
        with socket.create_connection((IPC_HOST, port), timeout=IPC_TIMEOUT) as s:
            s.settimeout(IPC_TIMEOUT)
            s.sendall(IPC_REQUEST)
            s.shutdown(socket.SHUT_WR)
            ack = b""
            while len(ack) < len(IPC_ACK):
                chunk = s.recv(len(IPC_ACK) - len(ack))
                if not chunk:
                    break
                ack += chunk
        return ack == IPC_ACK
    except OSError:
        return False


def acquire_mutex(name: str = MUTEX_NAME):
    """Returns (already_running, handle). Keep the handle alive."""
    try:
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.CreateMutexW.restype = wintypes.HANDLE
        k.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        handle = k.CreateMutexW(None, False, name)
        return ctypes.get_last_error() == 183, handle   # ERROR_ALREADY_EXISTS
    except Exception:
        return False, None


def serve_ipc_connection(conn) -> bool:
    """Accept only the exact request followed by EOF; anything else is rejected."""
    limit = len(IPC_REQUEST) + 1
    try:
        conn.settimeout(IPC_TIMEOUT)
        data = b""
        while len(data) < limit:
            chunk = conn.recv(limit - len(data))
            if not chunk:
                break
            data += chunk
        if data != IPC_REQUEST:
            return False
        conn.sendall(IPC_ACK)
        return True
    except OSError:
        return False


class IpcServer:
    """Exclusive loopback listener; calls on_show() for each valid request."""

    def __init__(self, on_show: Callable[[], None], port: int = IPC_PORT):
        self._on_show = on_show
        self._port = port
        self._srv: Optional[socket.socket] = None

    def start(self) -> bool:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
            if exclusive is not None:
                srv.setsockopt(socket.SOL_SOCKET, exclusive, 1)
            srv.bind((IPC_HOST, self._port))
            srv.listen(5)
        except OSError:
            srv.close()
            return False
        self._srv = srv
        threading.Thread(target=self._loop, daemon=True, name="KJDes-ipc").start()
        return True

    def _loop(self):
        srv = self._srv
        while srv is not None:
            try:
                conn, _ = srv.accept()
            except OSError:
                return
            with conn:
                if serve_ipc_connection(conn):
                    try:
                        self._on_show()
                    except Exception:
                        pass

    def close(self):
        srv, self._srv = self._srv, None
        if srv:
            try:
                srv.close()
            except OSError:
                pass
