"""
core/diagnose.py
Read-only connectivity diagnostics:  KJDes.exe --diagnose

Runs the SAME code paths the app uses before it changes anything, and writes a
report to %APPDATA%\\KJ Des\\diagnostics.txt. It never changes DNS, the hosts
file, the registry, scheduled tasks or adapter settings, and never starts the
relay.

TLS checks use the app's strict context (certificate + hostname verification).
When verification fails, the chain the server PRESENTED is listed from the
already-failed handshake — no data is sent and nothing is trusted — so a
missing root certificate can be told apart from TLS interception.

Privacy: adapter names and descriptions are included; DNS server addresses,
IP addresses and user names are not.
"""
from __future__ import annotations

import os
import platform
import socket
import ssl
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional
from urllib.parse import urlparse

from core.app_info import APP_VERSION

DOH_HOSTS_SOURCE = "core.discord_unblock._DOH_ENDPOINTS"


# ── certificate helpers ───────────────────────────────────────────────────
def _decode(der: bytes) -> Dict:
    """Decode a DER certificate to Python's dict form (via a temp PEM file)."""
    fd, path = tempfile.mkstemp(suffix=".pem")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(ssl.DER_cert_to_PEM_cert(bytes(der)))
        return ssl._ssl._test_decode_cert(path)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _name(info: Dict, key: str) -> str:
    parts = [v for rdn in info.get(key, ()) for k, v in rdn if k in ("commonName", "organizationName")]
    return " / ".join(parts) or "?"


def windows_root_names() -> set:
    """Common names of the certificates in the Windows ROOT store."""
    names = set()
    try:
        for der, _enc, _trust in ssl.enum_certificates("ROOT"):
            try:
                names.add(_name(_decode(der), "subject"))
            except Exception:
                continue
    except Exception:
        pass
    return names


def tls_check(host: str, timeout: float = 8.0,
              connect: Callable = socket.create_connection) -> Dict:
    """Strict TLS handshake to host:443. Never weakens verification."""
    ctx = ssl.create_default_context()
    out: Dict = {"host": host}
    started = time.monotonic()
    try:
        raw = connect((host, 443), timeout=timeout)
    except OSError as exc:
        out.update(result="connect_failed", error=type(exc).__name__)
        return out
    tls = ctx.wrap_socket(raw, server_hostname=host, do_handshake_on_connect=False)
    try:
        tls.settimeout(timeout)
        tls.do_handshake()
        out["result"] = "ok"
        out["chain"] = [_describe(der) for der in (tls.get_verified_chain() or [])]
    except ssl.SSLCertVerificationError as exc:
        out.update(result="verify_failed", verify_code=exc.verify_code,
                   verify_message=exc.verify_message)
        try:   # what the server presented (diagnostic only; connection is dead)
            out["presented_chain"] = [_describe(der) for der in (tls.get_unverified_chain() or [])]
        except Exception:
            out["presented_chain"] = []
    except (ssl.SSLError, OSError) as exc:
        out.update(result="tls_error", error=type(exc).__name__)
    finally:
        tls.close()
    out["ms"] = round((time.monotonic() - started) * 1000)
    return out


def _describe(der) -> Dict:
    info = _decode(der)
    return {"subject": _name(info, "subject"), "issuer": _name(info, "issuer"),
            "not_after": info.get("notAfter", "?")}


# ── report ────────────────────────────────────────────────────────────────
def _language_mode() -> str:
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                            "$ExecutionContext.SessionState.LanguageMode"],
                           capture_output=True, text=True, timeout=15,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return (r.stdout.strip() or f"unknown (exit {r.returncode})")[:40]
    except Exception as exc:
        return f"unavailable ({type(exc).__name__})"


def _snapshot_summary(snap: Dict) -> str:
    parts = []
    for fam in ("ipv4", "ipv6"):
        d = snap.get(fam) or {}
        parts.append(f"{fam}={'automatic' if d.get('dhcp') else 'static'}"
                     f"({len(d.get('servers') or [])} server(s))")
    return ", ".join(parts)


def build_report(*, adapters_fn, get_dns_fn, doh_fn, tls_fn=tls_check,
                 roots_fn=windows_root_names, language_fn=_language_mode,
                 is_admin_fn=lambda: False, summary: Optional[Dict] = None) -> str:
    """Pure report builder; every system access is injected (testable)."""
    from core.discord_unblock import _DOH_ENDPOINTS
    L: List[str] = []
    w = L.append
    w(f"KJ Des diagnostics — {datetime.now().isoformat(timespec='seconds')}")
    w("Read-only: nothing on this computer was changed.")
    w("")
    w(f"KJ Des {APP_VERSION} | {'installed' if getattr(sys, 'frozen', False) else 'source'}"
      f" | admin={is_admin_fn()}")
    w(f"Windows {platform.release()} ({platform.version()}) | Python {platform.python_version()}"
      f" | {ssl.OPENSSL_VERSION}")
    w(f"PowerShell language mode: {language_fn()}")
    w("")

    w("== 1. Adapters KJ Des would back up ==")
    try:
        adapters = adapters_fn()
    except Exception as exc:
        adapters = []
        w(f"  adapter listing failed: {type(exc).__name__}: {exc}"[:240])
    if not adapters:
        w("  (none) -> the app would stop with 'No active network adapter'")
    blocked = 0
    for a in adapters:
        name = a.get("name", "?")
        w(f"  - {name!r}  source={a.get('source', '?')}  type={a.get('type', '')!r}")
        try:
            w(f"      DNS read: OK — {_snapshot_summary(get_dns_fn(name))}")
        except Exception as exc:
            blocked += 1
            w(f"      DNS read: FAILED — {exc}"[:300])
    if summary is not None:
        summary.update(adapters=len(adapters), adapters_unreadable=blocked)
    if adapters:
        w(f"  => backup would {'FAIL (connection refused, nothing changed)' if blocked else 'succeed'}"
          f" — {blocked} of {len(adapters)} adapter(s) unreadable")
    w("")

    w("== 2. Secure DNS (DoH) providers, strict TLS ==")
    roots = roots_fn()
    w(f"  Windows ROOT store: {len(roots)} certificate(s)")
    for label, url in _DOH_ENDPOINTS:
        host = urlparse(url).hostname
        r = tls_fn(host)
        if r.get("result") == "ok":
            top = (r.get("chain") or [{}])[-1]
            w(f"  - {label} ({host}): OK, root={top.get('subject', '?')!r}, {r.get('ms')} ms")
            continue
        w(f"  - {label} ({host}): {r.get('result')}"
          + (f" code={r.get('verify_code')} '{r.get('verify_message')}'" if "verify_code" in r else "")
          + (f" error={r.get('error')}" if "error" in r else ""))
        chain = r.get("presented_chain") or []
        for i, c in enumerate(chain):
            w(f"      presented[{i}] {c['subject']!r} <- issued by {c['issuer']!r}")
        if chain:
            needed = chain[-1]["issuer"]
            present = needed in roots
            w(f"      issuer needed: {needed!r} -> in Windows ROOT store: {present}")
            if not present:
                w("      => the trust anchor is missing from this PC's certificate store,"
                  " or the connection is being intercepted (compare the names above with"
                  " a PC where it works).")
    w("")

    w("== 3. DoH resolution as the app does it ==")
    lines: List[str] = []
    if summary is not None:
        summary["doh_ok"] = False
    try:
        ips = doh_fn("discord.com", lines.append)
        w(f"  discord.com -> {len(ips)} address(es)")
        if summary is not None:
            summary["doh_ok"] = bool(ips)
    except Exception as exc:
        w(f"  FAILED: {type(exc).__name__}: {exc}"[:240])
    for ln in lines:
        w("  " + ln[:240])
    return "\n".join(L) + "\n"


EXIT_OK = 0          # report written, no blocking problem found
EXIT_FAILED = 1      # report could not be produced or written
EXIT_PROBLEMS = 2    # report written; the app would refuse to connect


def exit_code(summary: Dict) -> int:
    """2 when the report shows a condition that makes connecting impossible."""
    if (not summary.get("adapters") or summary.get("adapters_unreadable")
            or not summary.get("doh_ok")):
        return EXIT_PROBLEMS
    return EXIT_OK


def run(out_path: str, summary: Optional[Dict] = None) -> str:
    """Collect the report with the real (read-only) system calls."""
    from core import adapter_manager, dns_manager
    from core.discord_unblock import doh_resolve
    from security.elevation import is_admin
    text = build_report(
        adapters_fn=adapter_manager.get_active_adapters,
        get_dns_fn=dns_manager.get_dns,
        doh_fn=lambda host, log: doh_resolve(host, log=log),
        is_admin_fn=is_admin,
        summary=summary,
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return out_path
