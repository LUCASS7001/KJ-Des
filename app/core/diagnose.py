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

# SHA-256 of GENUINE CA certificates in the DoH providers' chains, recorded on a
# known-good Windows installation (2026-11-18). REPORT-ONLY: used to tell a
# missing root apart from TLS interception; never used to trust anything.
# Leaf certificates rotate and are deliberately not listed.
KNOWN_GENUINE_CA = {
    "948B7111AF42F546D579CFF5CE2BDEC82134DD9914842BDDB0C52872EB604E39":
        "SSL.com SSL Intermediate CA ECC R2 (Cloudflare DoH)",
    "3417BB06CC6007DA1B961C920B8AB4CE3FAD820E4AA30B9ACBC4A74EBDCEBC65":
        "SSL.com Root Certification Authority ECC",
}


def ca_verdict(presented: List[Dict]) -> str:
    """Compare the presented CA certificates (index >= 1) with known genuine ones."""
    cas = [c for c in presented[1:] if c.get("sha256")]
    if not cas:
        return "no CA certificate presented; cannot compare"
    if all(c["sha256"] in KNOWN_GENUINE_CA for c in cas):
        return ("presented CA certificate(s) match the genuine ones by fingerprint -> "
                "no interception; the trust anchor is missing from this PC's Windows store")
    if any(c["sha256"] in KNOWN_GENUINE_CA for c in cas):
        return "partly matches the genuine chain; inspect the fingerprints above"
    return ("presented CA certificate(s) do NOT match the genuine ones -> the connection "
            "is likely intercepted (antivirus HTTPS scanning, proxy or network filter)")


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
    import hashlib
    info = _decode(der)
    return {"subject": _name(info, "subject"), "issuer": _name(info, "issuer"),
            "not_after": info.get("notAfter", "?"),
            "sha256": hashlib.sha256(bytes(der)).hexdigest().upper()}


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
                 is_admin_fn=lambda: False, summary: Optional[Dict] = None,
                 backup_fn=lambda: {}, identities_fn=lambda: [],
                 guid_config_fn=None) -> str:
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
        w(f"      ifIndex={a.get('if_index')}  guid={a.get('guid')}")
        try:
            w(f"      DNS read: OK — {_snapshot_summary(get_dns_fn(name, a.get('guid')))}")
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
            if c.get("sha256"):
                w(f"                   sha256={c['sha256']}")
        if chain:
            w(f"      fingerprint check: {ca_verdict(chain)}")
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
    w("")
    _backup_section(w, backup_fn, identities_fn, get_dns_fn, summary, guid_config_fn)
    return "\n".join(L) + "\n"


def _backup_section(w, backup_fn, identities_fn, get_dns_fn, summary,
                    guid_config_fn=None) -> None:
    """What a restore WOULD do for each saved entry. Strictly read-only:
    nothing is written to the registry, DNS, adapters or the backup."""
    from core.adapter_identity import (GUID, VERIFIED, describe_cfg, dns_equivalent,
                                       orphan_verdict, resolve_restore_target)
    from core.dns_manager import normalize_snapshot
    w("== 4. Saved DNS backup (what a restore would do) ==")
    try:
        backup = backup_fn() or {}
    except Exception as exc:
        w(f"  backup unreadable: {type(exc).__name__}")
        return
    if not backup:
        w("  (none) — nothing left to restore")
        return
    adapters = identities_fn()
    pending = 0
    for name, raw in backup.items():
        try:
            snap = normalize_snapshot(raw)
        except Exception as exc:
            w(f"  - {name!r}: invalid entry ({exc}) -> retain backup")
            pending += 1
            continue
        d = resolve_restore_target(name, snap, adapters)
        a = d["adapter"]
        saved = "/".join("automatic" if snap[f]["dhcp"] else f"static({len(snap[f]['servers'])})"
                         for f in ("ipv4", "ipv6"))
        w(f"  - {name!r} saved guid={snap.get('interface_guid')} dns={saved}"
          f" identity_metadata={'yes' if snap.get('identity') else 'no'}")
        if d["kind"] in (GUID, VERIFIED):
            w(f"      match: {d['kind']} -> {a.get('name')!r} if={a.get('if_index')} guid={a.get('guid')}"
              f" ({d['reason']})")
            try:
                same = dns_equivalent(snap, get_dns_fn(a["name"], a.get("guid")))
            except Exception as exc:
                w(f"      would: retain backup (current DNS unreadable: {exc})"[:240])
                pending += 1
                continue
            if same["all"]:
                w("      would: clear without changes — current DNS already matches")
            else:
                w("      would: restore the saved DNS to this adapter (identity proven)")
            continue
        if d.get("saved_guid_listed") is False:
            w("      saved GUID is not present among current adapters")
            if a is not None:
                w(f"      hint only (never used to decide): adapter with the saved name -> "
                  f"{a.get('name')!r} if={a.get('if_index')} guid={a.get('guid')}")
            if guid_config_fn is None:
                w("      saved GUID configuration: not checked -> retain backup")
                pending += 1
                continue
            try:
                cfg = guid_config_fn(snap["interface_guid"])
                v = orphan_verdict(snap, cfg)
            except Exception as exc:
                w(f"      saved GUID configuration: unreadable ({type(exc).__name__})")
                w("      would: retain backup")
                pending += 1
                continue
            exists = {True: "yes", False: "no", None: "unknown"}[cfg.get("exists")]
            w(f"      saved GUID TCP/IP configuration exists: {exists}")
            for fam in ("ipv4", "ipv6"):
                c = cfg[fam]
                extra = f" — {c['detail']}" if c.get("detail") else ""
                w(f"        {fam}: {describe_cfg(c)}{extra}")
            w(f"      matches the backup: ipv4={v['ipv4_same']} ipv6={v['ipv6_same']}")
            if v["clear"]:
                why = "configuration absent" if v["verdict"] == "clear_absent" else "configuration identical"
                w(f"      would: clear without changes ({why})")
            elif v["verdict"] == "retain_unreadable":
                w("      would: retain backup (configuration could not be read reliably; retried next time)")
                pending += 1
            else:
                w("      would: manual recovery required — the saved GUID still holds DNS settings that"
                  " differ from the backup (or only one family exists); KJ Des changes nothing")
                pending += 1
            continue
        w(f"      match: {d['kind']} ({d['reason']})")
        w("      would: retain backup, change nothing")
        pending += 1
    if summary is not None:
        summary["backup_blocked"] = pending


EXIT_OK = 0          # report written, no blocking problem found
EXIT_FAILED = 1      # report could not be produced or written
EXIT_PROBLEMS = 2    # report written; the app would refuse to connect


def exit_code(summary: Dict) -> int:
    """2 when the report shows a condition that makes connecting impossible."""
    if (not summary.get("adapters") or summary.get("adapters_unreadable")
            or not summary.get("doh_ok")):
        return EXIT_PROBLEMS
    return EXIT_OK


def _load_backup():
    from core import secure_store
    return secure_store.load_dns_backup()


def _guid_config(guid):
    from core.adapter_identity import read_guid_dns_config
    return read_guid_dns_config(guid)


def _identities():
    from core.adapter_identity import list_adapter_identities
    return list_adapter_identities()


def run(out_path: str, summary: Optional[Dict] = None) -> str:
    """Collect the report with the real (read-only) system calls."""
    from core import adapter_manager, dns_manager
    from core.discord_unblock import doh_resolve
    from security.elevation import is_admin
    text = build_report(
        adapters_fn=adapter_manager.get_active_adapters,
        get_dns_fn=lambda name, guid=None: dns_manager.get_dns(name, guid),
        doh_fn=lambda host, log: doh_resolve(host, log=log),
        is_admin_fn=is_admin,
        summary=summary,
        backup_fn=_load_backup,
        identities_fn=_identities,
        guid_config_fn=_guid_config,
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return out_path
