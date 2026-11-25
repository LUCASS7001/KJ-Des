"""
core/connection.py

KJ Des connection lifecycle — a UI-independent state machine.

The sequence is the inherited engine's activation/restore flow (previously
embedded in its Tk GUI), moved here unchanged in substance, plus one addition:
an end-to-end TLS verification through the relay before "connected" is
reported. See NOTICE.md for the origin of the inherited engine.

Connect:
  0. read-only: a verified crash-recovery target must exist (installed build)
  1. read-only: secure DoH must work (nothing is changed if it does not)
  2. snapshot + persist the ORIGINAL DNS of every active adapter
  3. apply secure DNS to those adapters (any failure -> exact restore)
  4. start the local relay on 127.0.0.1:443
  5. install the logon recovery task BEFORE writing hosts
  6. write the marked hosts block (only Discord names, 3rd-party lines kept)
  7. verify: full TLS handshake to discord.com through the relay
  -> any failure after step 2 rolls everything back.

The manager only ever reports CONNECTED after step 7 succeeds.
"""
from __future__ import annotations

import enum
import threading
import time
from dataclasses import dataclass, replace
from typing import Callable, Optional

from core.recovery import DnsRecovery


class State(str, enum.Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    ERROR = "error"


@dataclass(frozen=True)
class Status:
    state: State = State.DISCONNECTED
    step: Optional[str] = None            # locale key of the current step
    error: Optional[str] = None           # locale key of the last error
    connected_since: Optional[float] = None
    routed: int = 0                       # hosts entries actually present
    total: int = 0                        # hosts entries KJ Des manages
    dns: Optional[str] = None             # primary IPv4 DNS, "auto" or None
    dns_secure: bool = False
    restore_pending: bool = False         # something is left to restore

    @property
    def busy(self) -> bool:
        return self.state in (State.CONNECTING, State.DISCONNECTING)


class ConnectionManager:
    def __init__(self, ops, log: Callable[[str], None], *, source_dev: bool = False,
                 on_change: Optional[Callable[[Status], None]] = None,
                 verify_attempts: int = 2, watchdog_interval: float = 2.0,
                 hosts_check_every: int = 3):
        self._ops = ops
        self._log_fn = log
        self._source_dev = source_dev
        self._on_change = on_change
        self._verify_attempts = max(1, verify_attempts)
        self._wd_interval = watchdog_interval
        self._hosts_every = max(1, hosts_check_every)
        self._relay = ops.create_relay(lambda m: self._log(f"engine: {m}"))
        self.dns = DnsRecovery(ops, self._log)
        self._op_lock = threading.Lock()          # one system operation at a time
        self._status_lock = threading.Lock()
        self._cancel = threading.Event()          # set on application shutdown
        self._wd_stop = threading.Event()
        self._wd_thread: Optional[threading.Thread] = None
        self._worker: Optional[threading.Thread] = None
        self._closed = False
        self._status = Status(total=self._safe(ops.total_hosts, 0))

    # ------------------------------------------------------------ utils
    def _log(self, msg: str) -> None:
        try:
            self._log_fn(msg)
        except Exception:
            pass

    @staticmethod
    def _safe(fn, default=None, *args):
        try:
            return fn(*args)
        except Exception:
            return default

    @property
    def status(self) -> Status:
        with self._status_lock:
            return self._status

    def _set(self, **changes) -> Status:
        with self._status_lock:
            self._status = replace(self._status, **changes)
            snapshot = self._status
        if self._on_change:
            try:
                self._on_change(snapshot)
            except Exception:
                pass
        return snapshot

    def relay_active(self) -> bool:
        return bool(self._safe(self._relay.is_active, False))

    # ---------------------------------------------------- async wrappers
    def _spawn(self, target) -> bool:
        if self._closed or self.status.busy or self._op_lock.locked():
            return False
        self._worker = threading.Thread(target=target, daemon=True, name="KJDes-op")
        self._worker.start()
        return True

    def start_connect(self) -> bool:
        return self._spawn(self.connect)

    def start_disconnect(self) -> bool:
        return self._spawn(self.disconnect)

    def start_refresh_dns(self) -> None:
        threading.Thread(target=self.refresh_dns, daemon=True, name="KJDes-dns").start()

    # --------------------------------------------------------- startup
    def recover_on_startup(self) -> bool:
        """Undo anything a previous crashed/killed session left behind.

        Mirrors the inherited engine's start-up self-heal: remove our marked hosts block,
        reconcile the recovery task, restore a persisted DNS backup.
        Returns True when the system is verified clean.
        """
        with self._op_lock:
            hosts_cleared = bool(self._safe(self._ops.remove_hosts, False))
            task_ok = self._reconcile(hosts_cleared, "startup")
            dns_ok = True
            if self.dns.has_backup():
                self._log("RECOVERY | DNS backup from a previous session found; restoring")
                dns_ok = self.dns.restore()
                self._ops.flush_dns()
            clean = hosts_cleared and task_ok and dns_ok
            self._log(f"RECOVERY | startup check | hosts_clean={hosts_cleared} "
                      f"task_ok={task_ok} dns_ok={dns_ok}")
            if clean:
                self._set(state=State.DISCONNECTED, error=None, restore_pending=False)
            else:
                self._set(state=State.ERROR, error=self._restore_error(), restore_pending=True)
            self._read_dns_locked()
            return clean

    def start_recover(self) -> bool:
        return self._spawn(self.recover_on_startup)

    # --------------------------------------------------------- connect
    def connect(self) -> bool:
        if self._closed or not self._op_lock.acquire(blocking=False):
            return False
        ok = False
        try:
            self._set(state=State.CONNECTING, step="step_preflight", error=None)
            error = self._connect_steps()
            if error is None:
                ok = True
                self._set(state=State.CONNECTED, step=None, error=None,
                          connected_since=time.time(), restore_pending=False,
                          routed=len(self._safe(self._ops.routed_hosts, []) or []))
                self._log("CONNECTION | verified and active")
                self._start_watchdog()
                self._read_dns_locked()
            else:
                pending = self.dns.has_backup() or bool(self._safe(self._ops.hosts_active, False))
                self._set(state=State.ERROR, step=None, error=error, connected_since=None,
                          routed=0, restore_pending=pending)
                self._log(f"CONNECTION | failed | {error}")
                self._read_dns_locked()
        except Exception as exc:  # never leave the UI in "connecting"
            self._log(f"CONNECTION | unexpected error | {type(exc).__name__}: {exc}")
            self._rollback_all("unexpected error")
            self._set(state=State.ERROR, step=None, error="err_unexpected",
                      connected_since=None, routed=0,
                      restore_pending=self.dns.has_backup())
        finally:
            self._op_lock.release()
        return ok

    def _connect_steps(self) -> Optional[str]:
        ops = self._ops
        # 0) read-only recovery-target check (installed build only)
        if self._source_dev:
            self._log("CONNECTION | source developer mode: logon recovery task skipped; "
                      "hosts are cleaned on next start after a hard crash")
        else:
            try:
                target = ops.failsafe_target()
            except Exception as exc:
                target = None
                self._log(f"FAILSAFE | pre-check error | {exc}")
            if not target:
                self._log("FAILSAFE | no verified recovery target, system untouched | "
                          f"{self._safe(ops.failsafe_error, '') or 'KJDes.exe not installed in Program Files'}")
                return "err_no_recovery"

        # 1) secure DoH must work before anything changes
        try:
            if not self._relay.preflight("discord.com"):
                raise RuntimeError("empty answer")
        except Exception as exc:
            self._log(f"CONNECTION | secure DNS (DoH) unavailable, nothing changed | {exc}")
            return "err_doh"
        if self._cancel.is_set():
            return "err_cancelled"

        # 1b) the relay port must be free BEFORE any change: if another tool
        #     (e.g. an active DPort) holds it, KJ Des leaves DNS/hosts alone.
        if not self._safe(ops.relay_port_free, True):
            self._log("RELAY | 127.0.0.1:443 is used by another program; nothing changed")
            return "err_port"

        # 2) backup original DNS
        self._set(step="step_dns")
        adapters = self._safe(ops.active_adapters, []) or []
        if not adapters:
            return "err_no_adapter"
        self._log("DNS | active adapters: " + ", ".join(
            f"{a.get('name')!r}[{a.get('source', '?')}"
            f"{', if=' + str(a['if_index']) if a.get('if_index') is not None else ''}]"
            for a in adapters))
        try:
            self.dns.backup(adapters)
        except Exception as exc:
            self._log(f"DNS | backup failed, system untouched | {exc}")
            return "err_dns_backup"

        # 3) apply secure DNS
        for adapter in adapters:
            try:
                ok, msg = ops.set_secure_dns(adapter["name"])
            except Exception as exc:
                ok, msg = False, str(exc)
            self._log(f"DNS | set {adapter['name']} | {'OK' if ok else msg}")
            if not ok:
                self.dns.restore()
                ops.flush_dns()
                return "err_dns_apply"
        ops.flush_dns()
        if self._cancel.is_set():
            self.dns.restore()
            ops.flush_dns()
            return "err_cancelled"

        # 4-6) relay + recovery task + hosts
        self._set(step="step_relay")
        error = self._enable_path()
        if error:
            self._disable_path("enable failed")
            self.dns.restore()
            ops.flush_dns()
            return error

        # 7) end-to-end verification
        self._set(step="step_verify")
        for attempt in range(1, self._verify_attempts + 1):
            if self._cancel.is_set():
                break
            ok, detail = self._safe(ops.verify_path, (False, "exception"))
            self._log(f"VERIFY | attempt {attempt}/{self._verify_attempts} | "
                      f"{'OK' if ok else 'failed'} | {detail}")
            if ok:
                return None
        self._disable_path("verification failed")
        self.dns.restore()
        ops.flush_dns()
        return "err_cancelled" if self._cancel.is_set() else "err_verify"

    def _enable_path(self) -> Optional[str]:
        ops = self._ops
        task_installed = False
        try:
            if not self._relay.start():
                self._log("RELAY | could not start (127.0.0.1:443 busy)")
                return "err_port"
            if not self._source_dev:
                ok = bool(self._safe(ops.install_failsafe, False))
                if not ok:
                    self._log(f"FAILSAFE | task not installed, hosts untouched | "
                              f"{self._safe(ops.failsafe_error, '')}")
                    return "err_failsafe"
                task_installed = True
            if not ops.add_hosts():
                err, winerr = self._safe(ops.last_hosts_error, ("", None))
                self._log(f"HOSTS | write failed | {err or 'permission or antivirus lock'}")
                if winerr == 5 and not self._safe(ops.is_admin, True):
                    return "err_admin"
                return "err_hosts_locked"
            ops.flush_dns()
            self._log("HOSTS | Discord routing block written")
            return None
        except Exception as exc:
            self._log(f"RELAY | enable error | {exc} | task_installed={task_installed}")
            return "err_unexpected"

    def _reconcile(self, hosts_cleared: bool, context: str) -> bool:
        try:
            if self._ops.reconcile_failsafe(hosts_cleared):
                return True
            self._log(f"FAILSAFE | {context}: task could not be reconciled | "
                      f"{self._safe(self._ops.failsafe_error, '')}")
        except Exception as exc:
            self._log(f"FAILSAFE | {context}: reconcile error | {exc}")
        return False

    def _disable_path(self, context: str) -> bool:
        """Remove hosts block, reconcile task, stop relay. True = verified clean."""
        hosts_cleared = bool(self._safe(self._ops.remove_hosts, False))
        task_ok = self._reconcile(hosts_cleared, context)
        self._safe(self._relay.stop)
        self._ops.flush_dns()
        self._log(f"PATH | disabled ({context}) | hosts_clean={hosts_cleared} task_ok={task_ok}")
        return hosts_cleared and task_ok

    def _rollback_all(self, context: str) -> bool:
        self._stop_watchdog()
        path_ok = self._disable_path(context)
        dns_ok = self.dns.restore()
        self._ops.flush_dns()
        return path_ok and dns_ok

    # ------------------------------------------------------ disconnect
    def disconnect(self) -> bool:
        """Disconnect AND restore defaults. Also the manual 'Restore Defaults'."""
        if not self._op_lock.acquire(blocking=False):
            return False
        try:
            return self._disconnect_locked("disconnect")
        finally:
            self._op_lock.release()

    restore_defaults = disconnect

    def _disconnect_locked(self, context: str, error_if_clean: Optional[str] = None) -> bool:
        self._set(state=State.DISCONNECTING, step="step_restoring", error=None)
        ok = self._rollback_all(context)
        if ok:
            self._set(state=State.ERROR if error_if_clean else State.DISCONNECTED,
                      step=None, error=error_if_clean, connected_since=None,
                      routed=0, restore_pending=False)
        else:
            self._set(state=State.ERROR, step=None, error=self._restore_error(),
                      connected_since=None,
                      routed=len(self._safe(self._ops.routed_hosts, []) or []),
                      restore_pending=True)
        self._log(f"CONNECTION | {context} | fully_restored={ok}")
        self._read_dns_locked()
        return ok

    def _restore_error(self) -> str:
        return "err_restore_identity" if self.dns.identity_blocked else "err_restore_partial"

    # --------------------------------------------------------- watchdog
    def _start_watchdog(self) -> None:
        self._stop_watchdog()
        self._wd_stop = threading.Event()
        self._wd_thread = threading.Thread(target=self._watchdog, args=(self._wd_stop,),
                                           daemon=True, name="KJDes-watchdog")
        self._wd_thread.start()

    def _stop_watchdog(self) -> None:
        self._wd_stop.set()
        thread = self._wd_thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=5)
        self._wd_thread = None

    def _watchdog(self, stop: threading.Event) -> None:
        """Only runs while connected. The relay check is in-memory; the hosts
        file is re-read every few ticks to reflect real routing state."""
        tick = 0
        while not stop.wait(self._wd_interval):
            tick += 1
            if self.status.state != State.CONNECTED:
                continue
            reason = None
            if not self.relay_active():
                reason = "err_relay_stopped"
            elif tick % self._hosts_every == 0:
                routed = len(self._safe(self._ops.routed_hosts, []) or [])
                if routed != self.status.routed:
                    self._set(routed=routed)
                if routed == 0:
                    reason = "err_hosts_removed"
            if reason and self._op_lock.acquire(blocking=False):
                try:
                    if self.status.state == State.CONNECTED:
                        self._log(f"WATCHDOG | {reason}; restoring original settings")
                        stop.set()
                        self._disconnect_locked("watchdog", error_if_clean=reason)
                finally:
                    self._op_lock.release()
                return

    # -------------------------------------------------------------- DNS
    def refresh_dns(self) -> None:
        self._read_dns_locked()

    def _read_dns_locked(self) -> None:
        """One read of the first active adapter's DNS (no polling)."""
        try:
            adapters = self._ops.active_adapters()
            if not adapters:
                self._set(dns=None, dns_secure=False)
                return
            v4 = self._ops.get_dns(adapters[0]["name"], adapters[0].get("guid"))["ipv4"]
            if v4["dhcp"] or not v4.get("primary"):
                self._set(dns="auto", dns_secure=False)
            else:
                from core.system_ops import DNS_V4
                self._set(dns=v4["primary"], dns_secure=v4["primary"] in DNS_V4)
        except Exception:
            self._set(dns=None, dns_secure=False)

    # --------------------------------------------------------- shutdown
    def shutdown(self, timeout: float = 120.0) -> bool:
        """Stop everything and restore the original state. Waits for a
        running operation (bounded) so no half-applied change is left."""
        if self._closed:
            return True
        self._closed = True
        self._cancel.set()
        acquired = self._op_lock.acquire(timeout=timeout)
        try:
            if not acquired:
                self._log("SESSION | running operation did not finish; forcing cleanup")
            needs = (self.relay_active() or self.dns.has_backup()
                     or bool(self._safe(self._ops.hosts_active, False)))
            ok = self._rollback_all("shutdown") if needs else True
            self._log(f"SESSION | shutdown | restored={ok}")
            return ok
        finally:
            if acquired:
                self._op_lock.release()
