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
    the first (original) snapshot of an adapter wins. This also holds when
    the adapter was renamed or re-created after an interrupted restore: an
    adapter whose original is already recorded (same GUID, or proven same
    hardware) gets no second entry, and when that cannot be decided safely
    the backup is refused and the existing entries are kept unchanged.
  * Restoration is verified by reading the configuration back; failed
    adapters stay in the backup so they can be retried.
  * Malformed/incomplete snapshots are rejected, never "assumed DHCP".
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, Iterable, List, Optional

from core.adapter_identity import (GUID, VERIFIED, clean_guid, clean_mac, describe_cfg,
                                   dns_equivalent, identity_from_adapter, is_burned_in,
                                   orphan_verdict, resolve_restore_target)


class DnsBackupError(RuntimeError):
    pass


def _looks_kj_applied(snapshot: Dict) -> bool:
    """True if either family holds exactly the servers KJ Des applies."""
    from core.system_ops import DNS_V4, DNS_V6
    for family, ours in (("ipv4", DNS_V4), ("ipv6", DNS_V6)):
        data = snapshot.get(family) or {}
        if data.get("dhcp") is False and list(data.get("servers") or []) == list(ours):
            return True
    return False


class DnsRecovery:
    def __init__(self, ops, log: Callable[[str], None]):
        self._ops = ops
        self._log = log
        self._mem: Dict = {}
        self._lock = threading.RLock()
        # names whose saved adapter could not be matched safely (last restore)
        self.identity_blocked: List[str] = []

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
            adapters = list(adapters)
            names = [a.get("name") for a in adapters]
            dupes = sorted({n for n in names if names.count(n) > 1})
            if dupes:
                # DNS changes address adapters by name: never guess between two.
                raise DnsBackupError(f"ambiguous adapter name(s): {dupes!r}")
            # 1) read every adapter first (reads only)
            live = {}
            for adapter in adapters:
                name = adapter["name"]
                try:
                    current = self._ops.get_dns(name, adapter.get("guid"))
                except Exception as exc:
                    # Same fail-closed behaviour; the log now names the adapter.
                    raise DnsBackupError(f"adapter={name!r}: {exc}") from exc
                listed_guid = adapter.get("guid")
                if listed_guid and listed_guid != current.get("interface_guid"):
                    raise DnsBackupError("adapter identity changed while reading")
                live[name] = current
            # 2) entries left by an earlier session under a name that is not
            #    listed now (e.g. restore interrupted, adapter renamed since)
            leftovers = {n: s for n, s in backup.items() if n not in live}
            current_ids = [dict(a, guid=live[a["name"]].get("interface_guid")) for a in adapters]
            # 3) decide per adapter; nothing is written unless all succeed
            for adapter, cur_id in zip(adapters, current_ids):
                name = adapter["name"]
                current = live[name]
                if name not in backup:
                    owner = self._leftover_owner(name, current, cur_id, leftovers, current_ids)
                    if owner is not None:
                        # The original of this adapter is already recorded; its
                        # live DNS may be KJ Des' own -> never record it.
                        self._log(f"DNS | {name!r} is covered by existing backup entry "
                                  f"{owner!r}; original kept, nothing added")
                        continue
                    ident = identity_from_adapter(adapter)
                    backup[name] = dict(current, identity=ident) if ident else current
                backup[name] = self._ops.normalize_snapshot(backup[name])
                saved_guid = backup[name].get("interface_guid")
                if saved_guid and saved_guid != current.get("interface_guid"):
                    raise DnsBackupError("adapter identity does not match backup")
                twins = sorted(n for n, s in leftovers.items()
                               if saved_guid and isinstance(s, dict)
                               and clean_guid(s.get("interface_guid")) == saved_guid)
                if twins:
                    raise DnsBackupError(f"adapter={name!r}: backup entries {twins!r} carry the "
                                         f"same GUID; original DNS cannot be established")
            if not self._store(backup):
                raise DnsBackupError("protected DNS backup could not be persisted")
            self._log(f"DNS | original configuration backed up ({len(backup)} adapter(s))")
            return len(backup)

    def _leftover_owner(self, name: str, current: Dict, cur_id: Dict,
                        leftovers: Dict, current_ids: List[Dict]) -> Optional[str]:
        """Which earlier backup entry (if any) already holds this adapter's
        original DNS. Raises DnsBackupError when that cannot be decided safely.

        * entry with this adapter's GUID, or proven same hardware (burned-in
          MAC + name/description)     -> that entry; nothing new is recorded
        * several such entries        -> refuse (which one is original?)
        * same burned-in MAC, unproven -> refuse
        * an entry with no usable GUID (older/invalid) while this adapter shows
          the DNS KJ Des applies       -> refuse (it may be that adapter)
        A valid GUID that differs never matches: TCP/IP settings are stored per
        GUID, so another GUID cannot carry this adapter's modified DNS."""
        if not leftovers:
            return None
        guid = clean_guid(current.get("interface_guid"))
        mac = clean_mac(cur_id.get("permanent_mac"))
        owners, unproven_mac, no_guid = [], [], []
        for entry_name, raw in leftovers.items():
            try:
                snap = self._ops.normalize_snapshot(raw)
            except Exception:
                no_guid.append(entry_name)
                continue
            saved_guid = clean_guid(snap.get("interface_guid"))
            if saved_guid and guid and saved_guid == guid:
                owners.append(entry_name)
                continue
            decision = resolve_restore_target(entry_name, snap, current_ids)
            target = decision.get("adapter") or {}
            if decision["kind"] == VERIFIED and target.get("name") == name:
                owners.append(entry_name)
                continue
            ident = snap.get("identity") or {}
            if mac and is_burned_in(mac) and ident.get("permanent_mac") == mac:
                unproven_mac.append(entry_name)
            if not saved_guid:
                no_guid.append(entry_name)
        if len(owners) > 1:
            raise DnsBackupError(f"adapter={name!r}: several backup entries claim it "
                                 f"{sorted(owners)!r}; original DNS cannot be established")
        if owners:
            return owners[0]
        if unproven_mac:
            raise DnsBackupError(f"adapter={name!r}: same hardware as backup entry "
                                 f"{sorted(unproven_mac)!r} but not proven; "
                                 f"original DNS cannot be established")
        if no_guid and _looks_kj_applied(current):
            raise DnsBackupError(f"adapter={name!r}: shows the DNS KJ Des applies while backup "
                                 f"entry {sorted(no_guid)!r} cannot be matched; "
                                 f"original DNS cannot be established")
        return None

    def restore(self) -> bool:
        """Restore every backed-up adapter. True only if nothing remains.

        For each saved entry the current adapter is identified first (see
        core/adapter_identity.py). Then:
          * identity proven (saved GUID, or burned-in MAC on real hardware):
            live DNS already equal -> entry cleared, NO change; otherwise
            restore, verified by read-back against the CURRENT GUID;
          * saved GUID not listed (and adapters were listed): decided ONLY
            from that GUID's own TCP/IP configuration in the registry —
            demonstrably absent, or demonstrably equal for IPv4 AND IPv6 ->
            entry cleared, NO change; anything else -> entry kept;
          * adapters not listable / GUID ambiguous / no GUID -> entry kept.
        A same-named adapter never authorizes clearing or changing anything.
        An entry is removed only after a verified restore or a verified
        read showing the live state already matches."""
        with self._lock:
            backup = self.current()
            self.identity_blocked = []
            if not backup:
                return True
            remaining = dict(backup)
            adapters = self._ops.list_adapter_identities()
            claimed = self._targets_claimed(backup, adapters)
            for name, raw in backup.items():
                if not isinstance(name, str) or not name.strip():
                    self._log("DNS restore | invalid adapter name; backup kept")
                    continue
                try:
                    snap = self._ops.normalize_snapshot(raw)
                except Exception as exc:
                    self._log(f"DNS restore | {name!r} | invalid backup entry kept | {exc}")
                    continue
                decision = resolve_restore_target(name, snap, adapters)
                kind, target = decision["kind"], decision["adapter"]
                where = (f" -> {target.get('name')!r} if={target.get('if_index')} "
                         f"guid={target.get('guid')}" if target else "")
                self._log(f"DNS restore | {name!r} | identity={kind}{where} | {decision['reason']}")
                if kind in (GUID, VERIFIED) and claimed.get(target.get("guid"), 0) > 1:
                    # e.g. a second entry recorded KJ Des' own DNS as 'original'
                    self._log(f"DNS restore | {name!r} | several backup entries match this "
                              f"adapter; original DNS unclear, nothing changed, backup kept")
                    self.identity_blocked.append(name)
                    continue
                if kind not in (GUID, VERIFIED):
                    if decision.get("saved_guid_listed") is False:
                        if self._orphan_check(name, snap):
                            remaining.pop(name, None)
                        else:
                            self.identity_blocked.append(name)
                    else:
                        self._log(f"DNS restore | {name!r} | identity cannot be established; "
                                  f"nothing changed, backup kept")
                        if kind != "unknown":      # listing failure is transient, not identity
                            self.identity_blocked.append(name)
                    continue
                try:
                    live = self._ops.get_dns(target["name"], target.get("guid"))
                except Exception as exc:
                    self._log(f"DNS restore | {name!r} | current DNS unreadable; nothing changed | {exc}")
                    continue
                same = dns_equivalent(snap, live)
                if same["all"]:
                    self._log(f"DNS restore | {name!r} | already matches the backup; no change needed")
                    remaining.pop(name, None)
                    continue
                if not target.get("guid"):
                    self._log(f"DNS restore | {name!r} | target has no GUID; nothing changed, backup kept")
                    self.identity_blocked.append(name)
                    continue
                wanted = dict(snap, interface_guid=target["guid"])
                try:
                    ok, msg = self._ops.restore_dns(target["name"], wanted)
                except Exception as exc:
                    ok, msg = False, str(exc)
                self._log(f"DNS restore | {name!r} -> {target['name']!r} | {'OK' if ok else msg}")
                if ok:
                    remaining.pop(name, None)
            self._store(remaining)
            return not remaining

    def _targets_claimed(self, backup: Dict, adapters) -> Dict:
        """How many backup entries resolve (GUID / verified) to each adapter GUID."""
        counts: Dict = {}
        for name, raw in backup.items():
            try:
                snap = self._ops.normalize_snapshot(raw)
                decision = resolve_restore_target(name, snap, adapters)
            except Exception:
                continue
            if decision["kind"] in (GUID, VERIFIED) and decision["adapter"]:
                guid = decision["adapter"].get("guid")
                counts[guid] = counts.get(guid, 0) + 1
        return counts

    def _orphan_check(self, name: str, snap: Dict) -> bool:
        """Saved GUID no longer listed: decide from ITS OWN registry config.
        True = entry may be cleared (no DNS change is ever made here)."""
        guid = snap.get("interface_guid")
        try:
            cfg = self._ops.read_guid_dns_config(guid)
            verdict = orphan_verdict(snap, cfg)
        except Exception as exc:
            self._log(f"DNS restore | {name!r} | saved GUID {guid} configuration unreadable "
                      f"({type(exc).__name__}); nothing changed, backup kept")
            return False
        detail = (f"saved GUID {guid}: ipv4={describe_cfg(cfg['ipv4'])} ipv6={describe_cfg(cfg['ipv6'])} "
                  f"(ipv4_same={verdict['ipv4_same']}, ipv6_same={verdict['ipv6_same']})")
        if verdict["clear"]:
            why = ("its configuration no longer exists" if verdict["verdict"] == "clear_absent"
                   else "its configuration already equals the backup")
            self._log(f"DNS restore | {name!r} | {detail} | {why}; entry cleared, no change made")
            return True
        self._log(f"DNS restore | {name!r} | {detail} | verdict={verdict['verdict']}; "
                  f"nothing changed, backup kept")
        return False
