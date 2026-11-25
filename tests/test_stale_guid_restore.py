"""
GitHub Issue #1 — DNS restore fails because the saved adapter GUID is stale
(e.g. the Hyper-V "Default Switch" is recreated by Windows with a new GUID).

Every test checks the actual DNS mutation calls (restore_dns / set_dns) and
the persisted backup, not only return values. All system access is faked.
"""
import copy
import unittest
from unittest import mock

import fakes  # noqa: F401
from fakes import FakeOps, MemoryLog, dhcp_snapshot, static_snapshot

from core import adapter_identity as ai
from core import dns_manager
from core.connection import ConnectionManager, State
from core.recovery import DnsRecovery

HV = "vEthernet (Default Switch)"
OLD = "0d71477a-b857-4f35-8ca1-fe6e8922ad42"           # from the issue
NEW = "26c1ad26-aa3a-4cb4-a830-d11fec7928e7"           # from the issue (lowercased)
ETH_OLD = "aaaaaaaa-0000-0000-0000-000000000001"
ETH_NEW = "aaaaaaaa-0000-0000-0000-000000000002"
MAC = "E89C25A31DB0"                                    # globally unique (burned-in)
OTHER = "bbbbbbbb-0000-0000-0000-000000000003"


def adapter(name, guid, *, if_index=17, desc="", mac=None, hardware=None):
    return {"name": name, "guid": guid, "if_index": if_index, "type": desc,
            "permanent_mac": mac, "hardware": hardware, "status": "Up"}


def mutations(ops):
    return [c for c in ops.calls if c.startswith(("restore_dns", "set_dns"))]


def build(store, live_dns, identities):
    ops = FakeOps(adapters=[{"name": a["name"]} for a in identities], dns=copy.deepcopy(live_dns))
    ops.identities = identities
    ops.store = copy.deepcopy(store)
    log = MemoryLog()
    return ops, log, DnsRecovery(ops, log.write)


class Issue1Reproduction(unittest.TestCase):
    def test_stale_guid_own_config_matches_backup_no_mutation(self):
        """The reported case, decided by the SAVED GUID's own configuration."""
        ops, log, rec = build({HV: dhcp_snapshot(guid=OLD)}, {HV: dhcp_snapshot(guid=NEW)},
                              [adapter(HV, NEW, desc="Hyper-V Virtual Ethernet Adapter", hardware=False)])
        ops.registry.set_family(OLD, "ipv4", "automatic")
        ops.registry.set_family(OLD, "ipv6", "automatic")
        self.assertTrue(rec.restore())
        self.assertEqual(mutations(ops), [], "no DNS change may be executed")
        self.assertEqual(ops.store, {}, "entry cleared only after the verified registry read")
        self.assertEqual(ops.reg_reads, [OLD], "only the saved GUID's configuration is consulted")
        self.assertEqual(ops.reads, [], "the same-named adapter is not even read")
        text = "\n".join(log.lines)
        self.assertIn("identity=name_only", text)
        self.assertIn("its configuration already equals the backup; entry cleared, no change made", text)

    def test_issue_flow_through_startup_recovery_and_ui_state(self):
        ops, log, _ = build({HV: dhcp_snapshot(guid=OLD)}, {HV: dhcp_snapshot(guid=NEW)},
                            [adapter(HV, NEW, hardware=False)])
        ops.registry.set_family(OLD, "ipv4", "absent")
        ops.registry.set_family(OLD, "ipv6", "absent")
        mgr = ConnectionManager(ops, log.write, source_dev=True)
        self.assertTrue(mgr.recover_on_startup())
        self.assertEqual(mgr.status.state, State.DISCONNECTED)
        self.assertFalse(mgr.status.restore_pending)
        self.assertEqual(mutations(ops), [])

    def test_old_code_path_failed_here(self):
        """Documents the bug: forcing a restore by the stale GUID is refused."""
        ops, _, _ = build({}, {HV: dhcp_snapshot(guid=NEW)}, [adapter(HV, NEW)])
        ok, msg = ops.restore_dns(HV, dhcp_snapshot(guid=OLD))
        self.assertFalse(ok)
        self.assertIn("Adapter not uniquely resolved: guid", msg)


class StaleGuidDifferentDns(unittest.TestCase):
    def test_verified_by_burned_in_mac_and_name_restores_to_current_guid(self):
        store = {"Ethernet": dict(static_snapshot(["192.168.1.53", "9.9.9.9"], guid=ETH_OLD),
                                  identity={"permanent_mac": MAC, "hardware": True,
                                            "description": "Realtek PCIe GbE Family Controller"})}
        live = {"Ethernet": static_snapshot(["1.1.1.1", "1.0.0.1"], guid=ETH_NEW)}
        ops, log, rec = build(store, live, [adapter("Ethernet", ETH_NEW, desc="Realtek PCIe GbE Family Controller",
                                                    mac=MAC, hardware=True)])
        self.assertTrue(rec.restore())
        self.assertEqual(mutations(ops), ["restore_dns:Ethernet"])
        self.assertEqual(ops.dns["Ethernet"]["ipv4"]["servers"], ["192.168.1.53", "9.9.9.9"])
        self.assertEqual(ops.dns["Ethernet"]["interface_guid"], ETH_NEW, "verified against the CURRENT GUID")
        self.assertIn("identity=verified", "\n".join(log.lines))
        self.assertEqual(ops.store, {})

    def test_recreated_and_renamed_physical_adapter_verified_by_mac_and_description(self):
        store = {"Ethernet": dict(static_snapshot(["192.168.1.53"], guid=ETH_OLD),
                                  identity={"permanent_mac": MAC, "hardware": True, "description": "Realtek X"})}
        live = {"Ethernet 2": static_snapshot(["1.1.1.1"], guid=ETH_NEW)}
        ops, _, rec = build(store, live, [adapter("Ethernet 2", ETH_NEW, desc="Realtek X", mac=MAC, hardware=True)])
        self.assertTrue(rec.restore())
        self.assertEqual(mutations(ops), ["restore_dns:Ethernet 2"])
        self.assertEqual(ops.dns["Ethernet 2"]["ipv4"]["servers"], ["192.168.1.53"])

    def test_mac_alone_without_name_or_description_is_not_enough(self):
        store = {"Ethernet": dict(static_snapshot(["192.168.1.53"], guid=ETH_OLD),
                                  identity={"permanent_mac": MAC, "hardware": True, "description": "Realtek X"})}
        live = {"Docking LAN": static_snapshot(["1.1.1.1"], guid=ETH_NEW)}
        ops, _, rec = build(store, live, [adapter("Docking LAN", ETH_NEW, desc="Other NIC", mac=MAC, hardware=True)])
        self.assertFalse(rec.restore())
        self.assertEqual(mutations(ops), [])
        self.assertIn("Ethernet", ops.store)

    def test_virtual_adapter_mac_is_never_proof(self):
        store = {HV: dict(static_snapshot(["10.0.0.1"], guid=OLD),
                          identity={"permanent_mac": "00155D010203", "hardware": False})}
        live = {HV: dhcp_snapshot(guid=NEW)}
        ops, _, rec = build(store, live, [adapter(HV, NEW, mac="00155D010203", hardware=False)])
        self.assertFalse(rec.restore())
        self.assertEqual(mutations(ops), [])
        self.assertIn(HV, ops.store)
        self.assertEqual(rec.identity_blocked, [HV])

    def test_backup_must_have_recorded_real_hardware_too(self):
        """Both the saved and the current adapter must be real hardware."""
        for saved_hw in (False, None):
            ident = {"permanent_mac": MAC, "description": "Realtek X"}
            if saved_hw is not None:
                ident["hardware"] = saved_hw
            store = {"Ethernet": dict(static_snapshot(["192.168.1.53"], guid=ETH_OLD), identity=ident)}
            ops, _, rec = build(store, {"Ethernet": dhcp_snapshot(guid=ETH_NEW)},
                                [adapter("Ethernet", ETH_NEW, desc="Realtek X", mac=MAC, hardware=True)])
            self.assertFalse(rec.restore(), saved_hw)
            self.assertEqual(mutations(ops), [], saved_hw)

    def test_locally_administered_mac_is_never_proof(self):
        mac = "02AABBCCDDEE"                                   # locally administered bit set
        store = {"Ethernet": dict(static_snapshot(["192.168.1.53"], guid=ETH_OLD),
                                  identity={"permanent_mac": mac, "hardware": True})}
        ops, _, rec = build(store, {"Ethernet": dhcp_snapshot(guid=ETH_NEW)},
                            [adapter("Ethernet", ETH_NEW, mac=mac, hardware=True)])
        self.assertFalse(rec.restore())
        self.assertEqual(mutations(ops), [])


class AmbiguityAndMissingMetadata(unittest.TestCase):
    def test_multiple_adapters_with_saved_name_no_mutation(self):
        ops, log, rec = build({HV: dhcp_snapshot(guid=OLD)}, {HV: dhcp_snapshot(guid=NEW)},
                              [adapter(HV, NEW), adapter(HV, OTHER, if_index=40)])
        self.assertFalse(rec.restore())
        self.assertEqual(mutations(ops), [])
        self.assertEqual(ops.reads, [], "ambiguous identity: not even a read of either candidate")
        self.assertIn(HV, ops.store)
        self.assertIn("identity=ambiguous", "\n".join(log.lines))

    def test_same_burned_in_mac_on_two_adapters_no_mutation(self):
        store = {"Ethernet": dict(static_snapshot(["192.168.1.53"], guid=ETH_OLD),
                                  identity={"permanent_mac": MAC, "hardware": True})}
        ops, _, rec = build(store, {"Ethernet": dhcp_snapshot(guid=ETH_NEW), "Ethernet 3": dhcp_snapshot(guid=OTHER)},
                            [adapter("Ethernet", ETH_NEW, mac=MAC, hardware=True),
                             adapter("Ethernet 3", OTHER, mac=MAC, hardware=True)])
        self.assertFalse(rec.restore())
        self.assertEqual(mutations(ops), [])

    def test_insufficient_metadata_and_different_dns_no_mutation(self):
        ops, log, rec = build({"Ethernet": static_snapshot(["192.168.1.53"], guid=ETH_OLD)},
                              {"Ethernet": dhcp_snapshot(guid=ETH_NEW)},
                              [adapter("Ethernet", ETH_NEW, mac=MAC, hardware=True)])
        ops.registry.set_family(ETH_OLD, "ipv4", "static", ["1.1.1.1", "1.0.0.1"])   # KJ Des left Cloudflare
        ops.registry.set_family(ETH_OLD, "ipv6", "automatic")
        self.assertFalse(rec.restore())
        self.assertEqual(mutations(ops), [])
        self.assertIn("Ethernet", ops.store, "backup must be kept")
        self.assertIn("verdict=retain_differs; nothing changed, backup kept", "\n".join(log.lines))

    def test_ui_reports_identity_problem_and_keeps_restore_pending(self):
        ops, log, _ = build({"Ethernet": static_snapshot(["192.168.1.53"], guid=ETH_OLD)},
                            {"Ethernet": dhcp_snapshot(guid=ETH_NEW)}, [adapter("Ethernet", ETH_NEW)])
        mgr = ConnectionManager(ops, log.write, source_dev=True)
        self.assertFalse(mgr.recover_on_startup())
        self.assertEqual(mgr.status.error, "err_restore_identity")
        self.assertTrue(mgr.status.restore_pending)
        self.assertEqual(mutations(ops), [])


class RenameAndIndexChanges(unittest.TestCase):
    def test_renamed_adapter_same_guid_restored_under_new_name(self):
        ops, _, rec = build({"Ethernet": static_snapshot(["192.168.1.53"], guid=ETH_OLD)},
                            {"LAN": static_snapshot(["1.1.1.1"], guid=ETH_OLD)},
                            [adapter("LAN", ETH_OLD)])
        self.assertTrue(rec.restore())
        self.assertEqual(mutations(ops), ["restore_dns:LAN"])
        self.assertEqual(ops.dns["LAN"]["ipv4"]["servers"], ["192.168.1.53"])

    def test_interface_index_change_is_irrelevant_with_same_guid(self):
        store = {"Ethernet": dict(static_snapshot(["192.168.1.53"], guid=ETH_OLD),
                                  identity={"if_index_at_backup": 7})}
        ops, _, rec = build(store, {"Ethernet": static_snapshot(["1.1.1.1"], guid=ETH_OLD)},
                            [adapter("Ethernet", ETH_OLD, if_index=42)])
        self.assertTrue(rec.restore())
        self.assertEqual(mutations(ops), ["restore_dns:Ethernet"])

    def test_interface_index_is_never_used_as_identity(self):
        store = {"Ethernet": dict(static_snapshot(["192.168.1.53"], guid=ETH_OLD),
                                  identity={"if_index_at_backup": 7})}
        ops, _, rec = build(store, {"Wi-Fi": dhcp_snapshot(guid=OTHER)},
                            [adapter("Wi-Fi", OTHER, if_index=7)])      # same index, other adapter
        self.assertFalse(rec.restore())
        self.assertEqual(mutations(ops), [])
        self.assertEqual(ops.dns["Wi-Fi"], dhcp_snapshot(guid=OTHER))
        self.assertIn("Ethernet", ops.store)


class FamiliesIndependent(unittest.TestCase):
    def test_equivalence_is_per_family(self):
        saved = dns_manager.normalize_snapshot(dhcp_snapshot())
        live = dns_manager.normalize_snapshot(dhcp_snapshot())
        live["ipv6"] = {"dhcp": False, "servers": ["2606:4700:4700::1111"]}
        self.assertEqual(ai.dns_equivalent(saved, live), {"ipv4": True, "ipv6": False, "all": False})
        static = dns_manager.normalize_snapshot(static_snapshot(["9.9.9.9", "1.1.1.1"]))
        swapped = dns_manager.normalize_snapshot(static_snapshot(["1.1.1.1", "9.9.9.9"]))
        self.assertFalse(ai.dns_equivalent(static, swapped)["ipv4"], "server order matters")

    def test_ipv4_matches_ipv6_differs_without_proof_no_mutation(self):
        live = dhcp_snapshot(guid=NEW)
        live["ipv6"] = {"dhcp": False, "servers": ["2606:4700:4700::1111"], "primary": "2606:4700:4700::1111",
                        "secondary": None}
        ops, log, rec = build({HV: dhcp_snapshot(guid=OLD)}, {HV: live}, [adapter(HV, NEW)])
        ops.registry.set_family(OLD, "ipv4", "automatic")
        ops.registry.set_family(OLD, "ipv6", "static", ["2606:4700:4700::1111"])
        self.assertFalse(rec.restore())
        self.assertEqual(mutations(ops), [])
        self.assertIn(HV, ops.store)
        self.assertIn("ipv4_same=True, ipv6_same=False", "\n".join(log.lines))

    def test_ipv6_differs_with_guid_proof_is_restored(self):
        live = dhcp_snapshot(guid=NEW)
        live["ipv6"] = {"dhcp": False, "servers": ["2606:4700:4700::1111"], "primary": "2606:4700:4700::1111",
                        "secondary": None}
        ops, _, rec = build({HV: dhcp_snapshot(guid=NEW)}, {HV: live}, [adapter(HV, NEW)])
        self.assertTrue(rec.restore())
        self.assertEqual(mutations(ops), [f"restore_dns:{HV}"])
        self.assertTrue(ops.dns[HV]["ipv6"]["dhcp"])


class LegacyBackups(unittest.TestCase):
    def test_pre_guid_backup_is_retained_even_if_same_named_adapter_matches(self):
        """No saved GUID -> no own configuration to check -> never cleared by name."""
        legacy = {"ipv4": {"dhcp": True, "primary": None, "secondary": None},
                  "ipv6": {"dhcp": True, "primary": None, "secondary": None}}
        ops, log, rec = build({"Wi-Fi": legacy}, {"Wi-Fi": dhcp_snapshot(guid=NEW)}, [adapter("Wi-Fi", NEW)])
        self.assertFalse(rec.restore())
        self.assertEqual(mutations(ops), [])
        self.assertEqual(ops.reg_reads, [])
        self.assertEqual(ops.store, {"Wi-Fi": legacy})
        self.assertIn("backup has no GUID (older version)", "\n".join(log.lines))

    def test_pre_guid_backup_differing_is_not_guessed(self):
        legacy = {"ipv4": {"dhcp": False, "primary": "192.168.1.53", "secondary": None},
                  "ipv6": {"dhcp": True, "primary": None, "secondary": None}}
        ops, _, rec = build({"Wi-Fi": legacy}, {"Wi-Fi": dhcp_snapshot(guid=NEW)}, [adapter("Wi-Fi", NEW)])
        self.assertFalse(rec.restore())
        self.assertEqual(mutations(ops), [])
        self.assertEqual(ops.store, {"Wi-Fi": legacy}, "old backup kept byte-for-byte")

    def test_1_0_x_backup_without_identity_still_restores_by_guid(self):
        ops, _, rec = build({"Wi-Fi": static_snapshot(["192.168.1.53"], guid=NEW)},
                            {"Wi-Fi": dhcp_snapshot(guid=NEW)}, [adapter("Wi-Fi", NEW)])
        self.assertTrue(rec.restore())
        self.assertEqual(mutations(ops), ["restore_dns:Wi-Fi"])


class PhysicalAndPartialFailure(unittest.TestCase):
    def test_physical_adapter_round_trip_unchanged(self):
        ops = FakeOps(adapters=[{"name": "Ethernet", "guid": ETH_OLD, "type": "Realtek",
                                 "permanent_mac": MAC, "hardware": True, "if_index": 3}],
                      dns={"Ethernet": static_snapshot(["192.168.1.53", "9.9.9.9"], guid=ETH_OLD)})
        mgr = ConnectionManager(ops, MemoryLog().write, source_dev=True)
        self.assertTrue(mgr.connect())
        saved = ops.store["Ethernet"]
        self.assertEqual(saved["identity"]["permanent_mac"], MAC, "new backups carry identity metadata")
        self.assertTrue(saved["identity"]["hardware"])
        self.assertTrue(mgr.disconnect())
        self.assertEqual(ops.dns, ops.original_dns)
        self.assertEqual(mutations(ops), ["set_dns:Ethernet", "restore_dns:Ethernet"])

    def test_partial_failure_protects_blocked_entry_and_unrelated_adapter(self):
        store = {"Wi-Fi": static_snapshot(["192.168.1.53"], guid=OTHER),               # restorable
                 "Ethernet": static_snapshot(["10.1.1.1"], guid=ETH_OLD)}             # stale, unprovable
        live = {"Wi-Fi": dhcp_snapshot(guid=OTHER), "Ethernet": dhcp_snapshot(guid=ETH_NEW),
                "VPN": static_snapshot(["10.8.0.1"], guid="cccccccc-0000-0000-0000-000000000004")}
        ops, _, rec = build(store, live, [adapter("Wi-Fi", OTHER), adapter("Ethernet", ETH_NEW),
                                          adapter("VPN", "cccccccc-0000-0000-0000-000000000004")])
        unrelated_before = copy.deepcopy(ops.dns["VPN"])
        self.assertFalse(rec.restore())
        self.assertEqual(mutations(ops), ["restore_dns:Wi-Fi"])
        self.assertEqual(ops.dns["VPN"], unrelated_before)
        self.assertEqual(set(ops.store), {"Ethernet"}, "only the verified entry was removed")
        self.assertEqual(ops.store["Ethernet"], store["Ethernet"])

    def test_adapter_listing_failure_changes_nothing(self):
        ops, log, rec = build({"Wi-Fi": static_snapshot(["192.168.1.53"], guid=OTHER)},
                              {"Wi-Fi": dhcp_snapshot(guid=OTHER)}, [adapter("Wi-Fi", OTHER)])
        ops.fail["list"] = True
        self.assertFalse(rec.restore())
        self.assertEqual(mutations(ops), [])
        self.assertIn("Wi-Fi", ops.store)
        self.assertIn("identity=unknown", "\n".join(log.lines))

    def test_unreadable_target_changes_nothing(self):
        ops, _, rec = build({"Wi-Fi": static_snapshot(["192.168.1.53"], guid=OTHER)},
                            {"Wi-Fi": dhcp_snapshot(guid=OTHER)}, [adapter("Wi-Fi", OTHER)])
        ops.fail["get_dns"] = True
        self.assertFalse(rec.restore())
        self.assertEqual(mutations(ops), [])
        self.assertIn("Wi-Fi", ops.store)


class RealRestoreGuard(unittest.TestCase):
    def test_dns_manager_restore_still_refuses_a_guid_mismatch_before_netsh(self):
        with mock.patch.object(dns_manager, "get_dns",
                               side_effect=dns_manager.DnsSnapshotError("Adapter not uniquely resolved: guid")) as g, \
             mock.patch.object(dns_manager.subprocess, "run",
                               side_effect=AssertionError("netsh must not run")):
            ok, msg = dns_manager.restore_dns(HV, dhcp_snapshot(guid=OLD))
        self.assertFalse(ok)
        self.assertEqual(g.call_args[0], (HV, OLD))

    def test_identity_metadata_is_validated(self):
        snap = dns_manager.normalize_snapshot(dict(dhcp_snapshot(), identity={
            "permanent_mac": "e8-9c-25-a3-1d-b0", "hardware": "yes", "description": "x" * 999,
            "if_index_at_backup": "7", "evil": "rm -rf"}))
        self.assertEqual(snap["identity"], {"permanent_mac": MAC, "description": "x" * 256})


if __name__ == "__main__":
    unittest.main()
