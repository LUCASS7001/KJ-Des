"""
core/system_ops.py

The ONLY boundary between KJ Des orchestration and the operating system.

Every call that can change (or read) network state goes through `SystemOps`.
The ConnectionManager never imports netsh/hosts/schtasks helpers directly, so
automated tests replace this object with a fake and never touch the real
network configuration of the machine running the tests.

All functions delegate to the inherited engine modules unchanged (see NOTICE.md).
"""
from __future__ import annotations

import socket
import ssl
import subprocess
from typing import Dict, List, Optional, Tuple

from core import adapter_manager, dns_manager, failsafe, secure_store
from core import discord_unblock as relay

# Cloudflare resolvers applied to adapters while connected (inherited engine
# strategy). The adapter's ORIGINAL configuration is backed up first and is
# restored exactly — these values are never used for restoration.
DNS_V4 = ("1.1.1.1", "1.0.0.1")
DNS_V6 = ("2606:4700:4700::1111", "2606:4700:4700::1001")

# End-to-end verification target. The relay only accepts allow-listed SNI.
VERIFY_HOST = "discord.com"


class SystemOps:
    """Real Windows implementation. Stateless; safe to share between threads."""

    # ---- adapters / DNS -------------------------------------------------
    def active_adapters(self) -> List[Dict]:
        return adapter_manager.get_active_adapters()

    def all_adapter_names(self) -> Optional[set]:
        try:
            names = {a.get("name") for a in adapter_manager.get_all_adapters()
                     if isinstance(a.get("name"), str) and a.get("name")}
            return names or None
        except Exception:
            return None

    def get_dns(self, adapter: str) -> Dict:
        return dns_manager.get_dns(adapter)

    def set_secure_dns(self, adapter: str) -> Tuple[bool, str]:
        return dns_manager.set_dns(adapter, DNS_V4[0], DNS_V4[1], DNS_V6[0], DNS_V6[1])

    def restore_dns(self, adapter: str, snapshot: Dict) -> Tuple[bool, str]:
        return dns_manager.restore_dns(adapter, snapshot)

    def normalize_snapshot(self, snapshot: Dict) -> Dict:
        return dns_manager.normalize_snapshot(snapshot)

    def flush_dns(self) -> None:
        try:
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=8,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass

    # ---- protected DNS backup (ACL protected %ProgramData%) --------------
    def load_dns_backup(self) -> Dict:
        return secure_store.load_dns_backup()

    def save_dns_backup(self, backup: Optional[Dict]) -> bool:
        return secure_store.save_dns_backup(backup)

    # ---- hosts --------------------------------------------------------
    def add_hosts(self) -> bool:
        return relay.add_hosts_redirect()

    def remove_hosts(self) -> bool:
        return relay.remove_hosts_redirect()

    def hosts_active(self) -> bool:
        return relay.is_hosts_redirect_active()

    def routed_hosts(self) -> List[str]:
        return relay.routed_hosts()

    def total_hosts(self) -> int:
        return len(relay.BLOCKED_HOSTS)

    def relay_port_free(self) -> bool:
        """Read-only pre-check: can 127.0.0.1:443 be bound exclusively?
        False when another relay (e.g. an active DPort, GoodbyeDPI) holds it.
        The probe socket is closed immediately; nothing is changed."""
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
            if exclusive is not None:
                probe.setsockopt(socket.SOL_SOCKET, exclusive, 1)
            probe.bind(("127.0.0.1", 443))
            return True
        except OSError:
            return False
        finally:
            probe.close()

    def last_hosts_error(self) -> Tuple[str, Optional[int]]:
        return relay.last_hosts_error(), relay.last_hosts_winerror()

    # ---- logon failsafe task -----------------------------------------
    def failsafe_target(self) -> Optional[str]:
        return failsafe.verified_failsafe_target()

    def install_failsafe(self) -> bool:
        return failsafe.install_logon_failsafe()

    def reconcile_failsafe(self, hosts_cleared: bool) -> bool:
        return failsafe.reconcile_failsafe_task(hosts_cleared)

    def failsafe_error(self) -> str:
        return failsafe.last_failsafe_error()

    # ---- relay factory / verification ----------------------------------
    def create_relay(self, log):
        return relay.DiscordUnblocker(log=log)

    def verify_path(self, timeout: float = 30.0) -> Tuple[bool, str]:
        """End-to-end proof that Discord is reachable THROUGH the relay.

        Opens a TLS connection to the local relay with SNI=discord.com and
        completes a full handshake with certificate + hostname verification
        against the system trust store. Success means a genuine Discord
        server answered via the fragmented path — not a block page, reset or
        a merely listening socket. No application data is sent.
        """
        ctx = ssl.create_default_context()
        try:
            with socket.create_connection(("127.0.0.1", 443), timeout=timeout) as raw:
                raw.settimeout(timeout)
                with ctx.wrap_socket(raw, server_hostname=VERIFY_HOST) as tls:
                    cert = tls.getpeercert() or {}
                    return True, f"tls={tls.version()} subject_ok={bool(cert)}"
        except ssl.SSLCertVerificationError as exc:
            return False, f"certificate:{getattr(exc, 'verify_code', '?')}"
        except (OSError, ssl.SSLError) as exc:
            return False, f"{type(exc).__name__}"

    # ---- privileges ----------------------------------------------------
    def is_admin(self) -> bool:
        from security.elevation import is_admin
        return is_admin()
