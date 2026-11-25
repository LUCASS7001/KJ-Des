"""
Regression: a backup left by an interrupted restore must never be replaced
(or shadowed) by DNS that KJ Des itself had applied.

Scenario: KJ Des sets Cloudflare on an adapter, the session ends before the
restore completes (crash, power loss, failed netsh), the backup entry stays.
The adapter then comes back - renamed, with a new GUID, or unchanged - while
still carrying KJ Des' Cloudflare servers, and the user connects again.
backup() must keep the ORIGINAL entry as the only record for that adapter, and
refuse (changing nothing) whenever it cannot tell which original state applies.

All system access is faked (tests/fakes.py); no live setting is touched.
"""
import copy
import unittest

import fakes  # noqa: F401
from fakes import FakeOps, MemoryLog, dhcp_snapshot, static_snapshot

from core.recovery import DnsBackupError, DnsRecovery

G1 = "aaaaaaaa-0000-0000-0000-000000000011"
G2 = "aaaaaaaa-0000-0000-0000-000000000012"
G3 = "aaaaaaaa-0000-0000-0000-000000000013"
MAC = "E89C25A31DB0"                       # globally unique (burned-in)
NIC = "Intel(R) Ethernet Connection I219-V"
CF4 = ["1.1.1.1", "1.0.0.1"]               # what KJ Des applies
USER4 = ["9.9.9.9", "149.112.112.112"]     # a user's own static DNS


def kj_modified(guid):
    """What an adapter looks like after KJ Des applied its secure DNS."""
    return static_snapshot(CF4, guid=guid)


def nic(name, guid, *, mac=None, hardware=None, desc=""):
    return {"name": name, "guid": guid, "type": desc, "if_index": 7,
            "permanent_mac": mac, "hardware": hardware, "status": "Up"}


def build(store, live, adapters):
    """adapters: what Windows reports now (active list == identity list)."""
    ops = FakeOps(adapters=[dict(a) for a in adapters], dns=copy.deepcopy(live))
    ops.identities = [dict(a) for a in adapters]
    ops.store = copy.deepcopy(store)
    log = MemoryLog()
    return ops, log, DnsRecovery(ops, log.write)


def mutations(ops):
    return [c for c in ops.calls if c.startswith(("restore_dns", "set_dns"))]


class InterruptedRestoreReproduction(unittest.TestCase):
    def test_renamed_adapter_keeps_original_and_restores_it(self):
        """The reported risk: same GUID, new name, Cloudflare still applied."""
        original = {"Ethernet": dhcp_snapshot(guid=G1)}
        ops, log, rec = build(original, {"Ethernet 2": kj_modified(G1)},
                              [nic("Ethernet 2", G1)])
        rec.backup(ops.active_adapters())
        self.assertEqual(set(ops.store), {"Ethernet"},
                         "no second entry may record KJ Des' Cloudflare as 'original'")
        self.assertTrue(ops.store["Ethernet"]["ipv4"]["dhcp"])
        self.assertIn("covered by existing backup entry 'Ethernet'", "\n".join(log.lines))
        # disconnect: the adapter ends on its ORIGINAL configuration
        self.assertTrue(rec.restore())
        self.assertTrue(ops.dns["Ethernet 2"]["ipv4"]["dhcp"])
        self.assertTrue(ops.dns["Ethernet 2"]["ipv6"]["dhcp"])
        self.assertEqual(ops.store, {})

    def test_same_name_same_guid_first_snapshot_wins(self):
        ops, _, rec = build({"Wi-Fi": static_snapshot(USER4, guid=G1)},
                            {"Wi-Fi": kj_modified(G1)}, [nic("Wi-Fi", G1)])
        rec.backup(ops.active_adapters())
        self.assertEqual(ops.store["Wi-Fi"]["ipv4"]["servers"], USER4)
        self.assertTrue(rec.restore())
        self.assertEqual(ops.dns["Wi-Fi"]["ipv4"]["servers"], USER4)

    def test_same_name_new_guid_refused_and_preserved(self):
        store = {"Ethernet": dhcp_snapshot(guid=G1)}
        ops, _, rec = build(store, {"Ethernet": kj_modified(G2)}, [nic("Ethernet", G2)])
        with self.assertRaises(DnsBackupError):
            rec.backup(ops.active_adapters())
        self.assertEqual(ops.store, store)

    def test_guid_changed_same_hardware_renamed_is_covered(self):
        """Burned-in MAC + description prove it is the saved adapter."""
        saved = dict(dhcp_snapshot(guid=G1),
                     identity={"description": NIC, "permanent_mac": MAC, "hardware": True})
        ops, _, rec = build({"Ethernet": saved}, {"LAN": kj_modified(G2)},
                            [nic("LAN", G2, mac=MAC, hardware=True, desc=NIC)])
        rec.backup(ops.active_adapters())
        self.assertEqual(set(ops.store), {"Ethernet"})
        self.assertTrue(rec.restore())
        self.assertTrue(ops.dns["LAN"]["ipv4"]["dhcp"])

    def test_same_burned_in_mac_without_proof_is_refused(self):
        saved = dict(dhcp_snapshot(guid=G1),
                     identity={"description": NIC, "permanent_mac": MAC, "hardware": True})
        store = {"Ethernet": saved}
        ops, _, rec = build(store, {"LAN": dhcp_snapshot(guid=G2)},
                            [nic("LAN", G2, mac=MAC, hardware=True, desc="other text")])
        with self.assertRaises(DnsBackupError):
            rec.backup(ops.active_adapters())
        self.assertEqual(ops.store, store)
        self.assertEqual(mutations(ops), [])

    def test_unresolved_leftover_and_kj_dns_is_refused(self):
        """Legacy entry (no GUID) for an adapter that is not present by name:
        an adapter showing KJ Des' DNS may be that adapter -> refuse."""
        legacy = dhcp_snapshot()
        del legacy["interface_guid"]
        store = {"Ethernet": legacy}
        ops, log, rec = build(store, {"Ethernet 2": kj_modified(G2)}, [nic("Ethernet 2", G2)])
        with self.assertRaises(DnsBackupError) as cm:
            rec.backup(ops.active_adapters())
        self.assertIn("original DNS cannot be established", str(cm.exception))
        self.assertEqual(ops.store, store)

    def test_kj_dns_on_ipv6_only_counts_as_modified(self):
        """An interrupted apply may have changed only one family."""
        legacy = dhcp_snapshot()
        del legacy["interface_guid"]
        live = dhcp_snapshot(guid=G2)
        live["ipv6"] = {"dhcp": False, "servers": ["2606:4700:4700::1111", "2606:4700:4700::1001"],
                        "primary": "2606:4700:4700::1111", "secondary": "2606:4700:4700::1001"}
        ops, _, rec = build({"Ethernet": legacy}, {"Ethernet 2": live}, [nic("Ethernet 2", G2)])
        with self.assertRaises(DnsBackupError):
            rec.backup(ops.active_adapters())

    def test_unresolved_leftover_other_adapter_with_own_dns_is_added(self):
        """A different adapter that does NOT carry KJ Des' DNS is backed up
        normally; the leftover entry stays untouched."""
        store = {"Ethernet": dhcp_snapshot(guid=G1)}      # adapter not present now
        ops, _, rec = build(store, {"Wi-Fi": static_snapshot(USER4, guid=G3)}, [nic("Wi-Fi", G3)])
        rec.backup(ops.active_adapters())
        self.assertEqual(ops.store["Ethernet"], store["Ethernet"])
        self.assertEqual(ops.store["Wi-Fi"]["ipv4"]["servers"], USER4)

    def test_leftover_entry_for_absent_adapter_is_never_touched(self):
        store = {"Ethernet": dhcp_snapshot(guid=G1)}
        ops, _, rec = build(store, {"Wi-Fi": dhcp_snapshot(guid=G3)}, [nic("Wi-Fi", G3)])
        rec.backup(ops.active_adapters())
        self.assertEqual(ops.store["Ethernet"], ops.normalize_snapshot(store["Ethernet"]))

    def test_two_entries_claiming_one_adapter_refused(self):
        """A backup already corrupted by an older version (two entries, one
        GUID) cannot tell which is original: refuse, keep both."""
        store = {"Ethernet": dhcp_snapshot(guid=G1), "Ethernet 2": kj_modified(G1)}
        ops, _, rec = build(store, {"Ethernet 3": kj_modified(G1)}, [nic("Ethernet 3", G1)])
        with self.assertRaises(DnsBackupError):
            rec.backup(ops.active_adapters())
        self.assertEqual(ops.store, store)

    def test_refusal_writes_nothing(self):
        store = {"Ethernet": dhcp_snapshot(guid=G1)}
        ops, _, rec = build(store, {"Ethernet": kj_modified(G2)}, [nic("Ethernet", G2)])
        writes = []
        real_save = ops.save_dns_backup
        ops.save_dns_backup = lambda b: writes.append(b) or real_save(b)
        with self.assertRaises(DnsBackupError):
            rec.backup(ops.active_adapters())
        self.assertEqual(writes, [])


    def test_leftover_with_other_guid_does_not_block_genuine_cloudflare(self):
        """TCP/IP settings are per GUID: an absent adapter's entry (valid GUID)
        cannot be this adapter, so a real 1.1.1.1 user is recorded as is."""
        store = {"Ethernet": dhcp_snapshot(guid=G1)}
        ops, _, rec = build(store, {"Wi-Fi": kj_modified(G3)}, [nic("Wi-Fi", G3)])
        rec.backup(ops.active_adapters())
        self.assertEqual(set(ops.store), {"Ethernet", "Wi-Fi"})

    def test_name_entry_plus_leftover_with_same_guid_refused(self):
        store = {"Ethernet": dhcp_snapshot(guid=G1), "Old name": static_snapshot(USER4, guid=G1)}
        ops, _, rec = build(store, {"Ethernet": kj_modified(G1)}, [nic("Ethernet", G1)])
        with self.assertRaises(DnsBackupError):
            rec.backup(ops.active_adapters())
        self.assertEqual(ops.store, store)

    def test_unreadable_adapter_refuses_before_any_write(self):
        store = {"Ethernet": dhcp_snapshot(guid=G1)}
        ops, _, rec = build(store, {"Ethernet 2": kj_modified(G1)}, [nic("Ethernet 2", G1)])
        ops.fail["get_dns"] = True
        with self.assertRaises(DnsBackupError):
            rec.backup(ops.active_adapters())
        self.assertEqual(ops.store, store)


class EndToEnd(unittest.TestCase):
    def test_interrupted_restore_rename_reconnect_disconnect(self):
        from core.connection import ConnectionManager
        ops = FakeOps(adapters=[{"name": "Ethernet", "guid": G1}],
                      dns={"Ethernet": static_snapshot(USER4, guid=G1)})
        mgr = ConnectionManager(ops, MemoryLog().write)
        self.assertTrue(mgr.connect())
        ops.fail["restore_dns"] = True                 # restore interrupted
        mgr.disconnect()
        self.assertEqual(ops.dns["Ethernet"]["ipv4"]["servers"], CF4)
        self.assertEqual(set(ops.store), {"Ethernet"})
        # Windows renames the adapter (same GUID) before the next connect
        ops.fail.pop("restore_dns")
        ops.adapters = [{"name": "Ethernet 2", "guid": G1}]
        ops.dns = {"Ethernet 2": ops.dns.pop("Ethernet")}
        self.assertTrue(mgr.connect())
        self.assertEqual(set(ops.store), {"Ethernet"}, "Cloudflare never recorded as original")
        mgr.disconnect()
        self.assertEqual(ops.dns["Ethernet 2"]["ipv4"]["servers"], USER4)
        self.assertEqual(ops.store, {})
        mgr.shutdown(timeout=5)


class RestoreWithConflictingEntries(unittest.TestCase):
    def test_two_entries_same_target_change_nothing(self):
        """Backups written by 1.0.1 under the rename bug: restore must not let
        the Cloudflare 'original' win by iteration order."""
        store = {"Ethernet": dhcp_snapshot(guid=G1), "Ethernet 2": kj_modified(G1)}
        ops, log, rec = build(store, {"Ethernet 2": kj_modified(G1)}, [nic("Ethernet 2", G1)])
        self.assertFalse(rec.restore())
        self.assertEqual(mutations(ops), [])
        self.assertEqual(ops.store, store)
        self.assertEqual(sorted(rec.identity_blocked), ["Ethernet", "Ethernet 2"])
        self.assertIn("several backup entries match", "\n".join(log.lines))


class NormalBehaviour(unittest.TestCase):
    def test_first_time_backup_records_every_adapter(self):
        ops, _, rec = build({}, {"Wi-Fi": static_snapshot(USER4, guid=G1), "Ethernet": dhcp_snapshot(guid=G2)},
                            [nic("Wi-Fi", G1), nic("Ethernet", G2, mac=MAC, hardware=True, desc=NIC)])
        self.assertEqual(rec.backup(ops.active_adapters()), 2)
        self.assertEqual(ops.store["Wi-Fi"]["ipv4"]["servers"], USER4)
        self.assertTrue(ops.store["Ethernet"]["ipv4"]["dhcp"])
        self.assertEqual(ops.store["Ethernet"]["identity"]["permanent_mac"], MAC)
        self.assertEqual(mutations(ops), [])

    def test_first_time_backup_of_genuine_cloudflare_user(self):
        """No leftover backup: a user who really uses 1.1.1.1 is recorded as is."""
        ops, _, rec = build({}, {"Wi-Fi": kj_modified(G1)}, [nic("Wi-Fi", G1)])
        rec.backup(ops.active_adapters())
        self.assertEqual(ops.store["Wi-Fi"]["ipv4"]["servers"], CF4)

    def test_repeated_backup_while_connected_is_stable(self):
        ops, _, rec = build({}, {"Wi-Fi": static_snapshot(USER4, guid=G1)}, [nic("Wi-Fi", G1)])
        rec.backup(ops.active_adapters())
        first = copy.deepcopy(ops.store)
        ops.set_secure_dns("Wi-Fi")
        rec.backup(ops.active_adapters())
        self.assertEqual(ops.store, first)

    def test_connect_disconnect_cycles_restore_original(self):
        ops, _, rec = build({}, {"Wi-Fi": static_snapshot(USER4, guid=G1)}, [nic("Wi-Fi", G1)])
        for _ in range(3):
            rec.backup(ops.active_adapters())
            ops.set_secure_dns("Wi-Fi")
            self.assertTrue(rec.restore())
            self.assertEqual(ops.dns["Wi-Fi"]["ipv4"]["servers"], USER4)
            self.assertEqual(ops.store, {})


if __name__ == "__main__":
    unittest.main()
