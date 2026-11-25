"""
core/adapter_identity.py
Deciding which current network adapter a saved DNS backup belongs to.

Pure decision logic (no system calls) plus one read-only adapter listing.

Identity evidence, strongest first:
  1. InterfaceGuid — unique; stable unless Windows recreates the adapter (the
     Hyper-V "Default Switch" is recreated with a new GUID at boot; physical
     adapters can get one after a driver reinstall, a network reset or
     removing and re-adding the device).
  2. Burned-in MAC (PermanentAddress) — accepted ONLY for real hardware
     (HardwareInterface=True) with a globally unique MAC, and only when it
     matches exactly ONE adapter and the saved name or description agrees.
     Virtual adapters (Hyper-V, Bluetooth PAN, WAN miniports) have generated
     or empty MACs and are never matched this way.
  Never used as proof: interface index, PnP device id, name alone,
  description alone.

When the saved GUID is no longer listed and no hardware proof exists, the
decision is based ONLY on the saved GUID's own Windows TCP/IP configuration
(read_guid_dns_config): the entry is cleared — without any change — when that
configuration is demonstrably absent, or demonstrably identical to the backup
for both IPv4 and IPv6. A same-named current adapter is only a hint and never
authorizes anything. Anything else keeps the backup.
"""
from __future__ import annotations

import json
import re
import subprocess
import uuid
from typing import Dict, List, Optional

GUID = "guid"              # saved GUID found: proven identity
VERIFIED = "verified"      # stale GUID, proven by burned-in MAC + name/description
NAME_ONLY = "name_only"    # stale GUID, one adapter has the saved name: NOT proof
AMBIGUOUS = "ambiguous"    # several candidates
ABSENT = "absent"          # no candidate at all (adapter may come back later)
UNKNOWN = "unknown"        # adapters could not be listed


def clean_guid(value) -> Optional[str]:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def clean_mac(value) -> Optional[str]:
    """12 uppercase hex digits, or None."""
    if not isinstance(value, str):
        return None
    hexdigits = re.sub(r"[^0-9A-Fa-f]", "", value).upper()
    if len(hexdigits) != 12 or hexdigits == "0" * 12:
        return None
    return hexdigits


def is_burned_in(mac: Optional[str]) -> bool:
    """Globally unique (not locally administered, not multicast) MAC."""
    if not mac:
        return False
    first = int(mac[:2], 16)
    return not (first & 0x02) and not (first & 0x01)


def identity_from_adapter(adapter: Dict) -> Dict:
    """Identity metadata stored with NEW backups (all optional)."""
    ident = {}
    desc = adapter.get("type")
    if isinstance(desc, str) and desc.strip():
        ident["description"] = desc.strip()[:256]
    mac = clean_mac(adapter.get("permanent_mac"))
    if mac:
        ident["permanent_mac"] = mac
    if isinstance(adapter.get("hardware"), bool):
        ident["hardware"] = adapter["hardware"]
    if isinstance(adapter.get("if_index"), int):
        ident["if_index_at_backup"] = adapter["if_index"]   # informational only
    return ident


def normalize_identity(value) -> Optional[Dict]:
    """Validate identity metadata read back from dns_state.json."""
    if not isinstance(value, dict):
        return None
    out = {}
    if isinstance(value.get("description"), str):
        out["description"] = value["description"][:256]
    mac = clean_mac(value.get("permanent_mac"))
    if mac:
        out["permanent_mac"] = mac
    if isinstance(value.get("hardware"), bool):
        out["hardware"] = value["hardware"]
    if isinstance(value.get("if_index_at_backup"), int):
        out["if_index_at_backup"] = value["if_index_at_backup"]
    return out or None


def resolve_restore_target(saved_name: str, saved: Dict, adapters: Optional[List[Dict]]) -> Dict:
    """Decide which current adapter (if any) the saved backup belongs to.

    `adapters`: current adapters as from list_adapter_identities(), or None if
    they could not be listed. Returns {"kind", "adapter", "reason",
    "saved_guid_listed"}: saved_guid_listed is False only when the adapters
    WERE listed and none carries the saved GUID (None = unknown / no GUID)."""
    decision = _resolve(saved_name, saved, adapters)
    guid = clean_guid(saved.get("interface_guid"))
    if adapters is None or not guid:
        decision["saved_guid_listed"] = None
    else:
        decision["saved_guid_listed"] = any(a.get("guid") == guid for a in adapters)
    return decision


def _resolve(saved_name: str, saved: Dict, adapters: Optional[List[Dict]]) -> Dict:
    if adapters is None:
        return {"kind": UNKNOWN, "adapter": None, "reason": "adapters could not be listed"}
    saved_guid = clean_guid(saved.get("interface_guid"))
    if saved_guid:
        by_guid = [a for a in adapters if a.get("guid") == saved_guid]
        if len(by_guid) == 1:
            a = by_guid[0]
            renamed = "" if a.get("name") == saved_name else f" (renamed to {a.get('name')!r})"
            return {"kind": GUID, "adapter": a, "reason": "saved GUID found" + renamed}
        if len(by_guid) > 1:
            return {"kind": AMBIGUOUS, "adapter": None, "reason": "saved GUID matches several adapters"}

    ident = saved.get("identity") or {}
    mac = ident.get("permanent_mac")
    if ident.get("hardware") is True and is_burned_in(mac):
        same_mac = [a for a in adapters if a.get("permanent_mac") == mac]
        if len(same_mac) > 1:
            return {"kind": AMBIGUOUS, "adapter": None,
                    "reason": "saved burned-in MAC matches several adapters"}
        if len(same_mac) == 1:
            a = same_mac[0]
            corroborated = (a.get("name") == saved_name
                            or (ident.get("description") and a.get("type") == ident.get("description")))
            if a.get("hardware") is True and corroborated:
                return {"kind": VERIFIED, "adapter": a,
                        "reason": "GUID changed; same real hardware (burned-in MAC) and same "
                                  + ("name" if a.get("name") == saved_name else "description")}

    by_name = [a for a in adapters if a.get("name") == saved_name]
    if len(by_name) > 1:
        return {"kind": AMBIGUOUS, "adapter": None, "reason": "several adapters carry the saved name"}
    if len(by_name) == 1:
        why = ("saved GUID no longer exists" if saved_guid else "backup has no GUID (older version)")
        return {"kind": NAME_ONLY, "adapter": by_name[0],
                "reason": f"{why}; identity cannot be proven from the name alone"}
    return {"kind": ABSENT, "adapter": None, "reason": "no matching adapter is present"}


def dns_equivalent(saved: Dict, live: Dict) -> Dict:
    """Per-family comparison of configured DNS (source + ordered servers).

    Effective (DHCP-provided) servers are transient and not compared."""
    result = {}
    for family in ("ipv4", "ipv6"):
        s, l = saved.get(family) or {}, live.get(family) or {}
        same = (s.get("dhcp") is l.get("dhcp")
                and (s.get("dhcp") or list(s.get("servers") or []) == list(l.get("servers") or [])))
        result[family] = bool(same)
    result["all"] = result["ipv4"] and result["ipv6"]
    return result


# ── the saved GUID's own TCP/IP configuration (registry, read-only) ──────
TCPIP_PATHS = {
    "ipv4": r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{%s}",
    "ipv6": r"SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters\Interfaces\{%s}",
}
ABSENT_CFG, AUTOMATIC, STATIC, UNREADABLE = "absent", "automatic", "static", "unreadable"


def read_guid_dns_config(guid, reg=None) -> Dict:
    r"""Read HKLM\...\Tcpip[6]\Parameters\Interfaces\{GUID}\NameServer.

    Per family:  absent     -> the interface key does not exist (FileNotFoundError)
                 automatic  -> key exists; NameServer missing or empty
                 static     -> key exists; NameServer lists valid addresses
                 unreadable -> access denied, any other error, wrong value
                               type or invalid address (NEVER treated as absent)
    Opens keys with KEY_QUERY_VALUE only; nothing is ever written."""
    import ipaddress
    if reg is None:
        import winreg as reg
    out: Dict = {}
    g = clean_guid(guid)
    for family, version in (("ipv4", 4), ("ipv6", 6)):
        if not g:
            out[family] = {"state": UNREADABLE, "servers": [], "detail": "invalid GUID"}
            continue
        path = TCPIP_PATHS[family] % g
        access = reg.KEY_QUERY_VALUE | getattr(reg, "KEY_WOW64_64KEY", 0)
        try:
            key = reg.OpenKey(reg.HKEY_LOCAL_MACHINE, path, 0, access)
        except FileNotFoundError:
            out[family] = {"state": ABSENT_CFG, "servers": [], "detail": "interface key not found"}
            continue
        except PermissionError:
            out[family] = {"state": UNREADABLE, "servers": [], "detail": "access denied"}
            continue
        except OSError as exc:
            out[family] = {"state": UNREADABLE, "servers": [],
                           "detail": f"open failed (winerror={getattr(exc, 'winerror', None)})"}
            continue
        try:
            try:
                value, vtype = reg.QueryValueEx(key, "NameServer")
            except FileNotFoundError:
                out[family] = {"state": AUTOMATIC, "servers": [], "detail": "NameServer value not set"}
                continue
            except PermissionError:
                out[family] = {"state": UNREADABLE, "servers": [], "detail": "access denied (value)"}
                continue
            except OSError as exc:
                out[family] = {"state": UNREADABLE, "servers": [],
                               "detail": f"query failed (winerror={getattr(exc, 'winerror', None)})"}
                continue
        finally:
            try:
                reg.CloseKey(key)
            except Exception:
                pass
        if vtype not in (getattr(reg, "REG_SZ", 1), getattr(reg, "REG_EXPAND_SZ", 2)) or not isinstance(value, str):
            out[family] = {"state": UNREADABLE, "servers": [], "detail": f"unexpected value type {vtype}"}
            continue
        tokens = [t for t in re.split(r"[,;\s]+", value.strip()) if t]
        if not tokens:
            out[family] = {"state": AUTOMATIC, "servers": [], "detail": "NameServer empty"}
            continue
        try:
            servers = [str(ipaddress.ip_address(t)) for t in tokens]
            if any(ipaddress.ip_address(s).version != version for s in servers):
                raise ValueError("address family mismatch")
        except ValueError:
            out[family] = {"state": UNREADABLE, "servers": [], "detail": "invalid address in NameServer"}
            continue
        out[family] = {"state": STATIC, "servers": servers, "detail": ""}
    states = {out["ipv4"]["state"], out["ipv6"]["state"]}
    out["exists"] = (None if UNREADABLE in states and not (states - {UNREADABLE, ABSENT_CFG})
                     else bool(states - {ABSENT_CFG}))
    return out


CLEAR_ABSENT = "clear_absent"        # configuration demonstrably gone
CLEAR_MATCH = "clear_match"          # both families demonstrably equal the backup
RETAIN_UNREADABLE = "retain_unreadable"
RETAIN_DIFFERS = "retain_differs"    # e.g. still holds KJ Des' Cloudflare settings
RETAIN_PARTIAL = "retain_partial"    # one family absent, the other present


def orphan_verdict(saved: Dict, cfg: Dict) -> Dict:
    """Compare the saved backup with the saved GUID's own configuration."""
    states = (cfg["ipv4"]["state"], cfg["ipv6"]["state"])
    same = {}
    for family in ("ipv4", "ipv6"):
        c, s = cfg[family], saved.get(family) or {}
        if c["state"] == AUTOMATIC:
            same[family] = s.get("dhcp") is True
        elif c["state"] == STATIC:
            same[family] = s.get("dhcp") is False and list(s.get("servers") or []) == c["servers"]
        else:
            same[family] = None
    if UNREADABLE in states:
        verdict = RETAIN_UNREADABLE
    elif states == (ABSENT_CFG, ABSENT_CFG):
        verdict = CLEAR_ABSENT
    elif ABSENT_CFG in states:
        verdict = RETAIN_PARTIAL
    elif same["ipv4"] and same["ipv6"]:
        verdict = CLEAR_MATCH
    else:
        verdict = RETAIN_DIFFERS
    return {"verdict": verdict, "ipv4_same": same["ipv4"], "ipv6_same": same["ipv6"],
            "clear": verdict in (CLEAR_ABSENT, CLEAR_MATCH)}


def describe_cfg(family_cfg: Dict) -> str:
    st = family_cfg["state"]
    return f"static({len(family_cfg['servers'])})" if st == STATIC else st


def list_adapter_identities() -> Optional[List[Dict]]:
    """All adapters (including hidden) with identity attributes. Read-only.
    None when the listing fails — callers must then change nothing."""
    script = (
        "$ErrorActionPreference = 'Stop'; "
        "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
        "@(Get-NetAdapter -IncludeHidden | Select-Object Name,InterfaceDescription,"
        "@{n='Guid';e={([guid]$_.InterfaceGuid).ToString()}},ifIndex,PermanentAddress,"
        "HardwareInterface,Status) | ConvertTo-Json -Compress -Depth 3")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                           capture_output=True, text=True, encoding="utf-8", errors="strict",
                           timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode or not r.stdout.strip():
            return None
        raw = json.loads(r.stdout.lstrip("﻿"))
    except Exception:
        return None
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return None
    out = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("Name"), str):
            continue
        out.append({
            "name": item["Name"],
            "type": item.get("InterfaceDescription") or "",
            "guid": clean_guid(item.get("Guid")),
            "if_index": item.get("ifIndex") if isinstance(item.get("ifIndex"), int) else None,
            "permanent_mac": clean_mac(item.get("PermanentAddress")),
            "hardware": item.get("HardwareInterface") if isinstance(item.get("HardwareInterface"), bool) else None,
            "status": str(item.get("Status") or ""),
        })
    return out
