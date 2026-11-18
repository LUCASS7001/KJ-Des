"""
core/recovery.py

Backup and exact restoration of the user's original network state.
Logic ported from the inherited engine's GUI layer into a UI-independent class.

Rules (inherited and kept intact):
  * The DNS backup lives in the ACL-protected %ProgramData%\\KJ Des store that a
    standard user cannot write. A user-writable file is NEVER used as input to
    the elevated `netsh` calls. If the protected store cannot be written, the
    connection is refused (no change without a crash-safe backup).
  * Only adapters that KJ Des changed are restored. Unrelated adapters are
    never touched; adapters not present right now stay in the backup.
  * An existing backup is never overwritten by the already-modified state:
    the first (original) snapshot of an adapter wins.
  * Restoration is verified by reading the configuration back; failed
    adapters stay in the backup so they can be retried.
  * Malformed/incomplete snapshots are rejected, never "assumed DHCP".
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, Iterable


class DnsBackupError(RuntimeError):
    pass


class DnsRecovery:
    def __init__(self, ops, log: Callable[[str], None]):
        self._ops = ops
        self._log = log
        self._mem: Dict = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    def current(self) -> Dict:
        with self._lock:
            try:
                stored = self._ops.load_dns_backup()
            except Exception:
                stored = {}
            return dict(stored or self._mem)

    def has_backup(self) -> bool:
        return bool(self.current())

    def _store(self, backup: Dict) -> bool:
        data = dict(backup) if backup else {}
        try:
            persisted = bool(self._ops.save_dns_backup(data or None))
        except Exception:
            persisted = False
        self._mem = data
        if data and not persisted:
            self._log("DNS | protected recovery file could not be written; "
                      "backup kept in memory only")
        return persisted

    # ------------------------------------------------------------------
    def backup(self, adapters: Iterable[Dict]) -> int:
        """Snapshot every adapter BEFORE any mutation. Raises on any doubt."""
        with self._lock:
            backup = self.current()
            for adapter in adapters:
                name = adapter["name"]
                current = self._ops.get_dns(name)
                if name not in backup:
                    backup[name] = current
                backup[name] = self._ops.normalize_snapshot(backup[name])
                saved_guid = backup[name].get("interface_guid")
                if saved_guid and saved_guid != current.get("interface_guid"):
                    raise DnsBackupError("adapter identity does not match backup")
            if not self._store(backup):
                raise DnsBackupError("protected DNS backup could not be persisted")
            self._log(f"DNS | original configuration backed up ({len(backup)} adapter(s))")
            return len(backup)

    def restore(self) -> bool:
        """Restore every backed-up adapter. True only if nothing remains."""
        with self._lock:
            backup = self.current()
            if not backup:
                return True
            remaining = dict(backup)
            live = self._ops.all_adapter_names()
            for name, snap in backup.items():
                if not isinstance(name, str) or not name.strip():
                    self._log("DNS restore | invalid adapter name; backup kept")
                    continue
                if live is not None and name not in live:
                    self._log(f"DNS restore | {name} | skipped (adapter not present)")
                    continue
                try:
                    ok, msg = self._ops.restore_dns(name, self._ops.normalize_snapshot(snap))
                except Exception as exc:
                    ok, msg = False, str(exc)
                self._log(f"DNS restore | {name} | {'OK' if ok else msg}")
                if ok:
                    remaining.pop(name, None)
            self._store(remaining)
            return not remaining
