"""
Issue #1, security-review follow-up: a stale-GUID backup may be cleared ONLY on
evidence about the saved GUID's own Windows TCP/IP configuration, never because
a same-named adapter happens to have matching DNS.

Registry access goes through tests.fakes.FakeRegistry (winreg semantics,
read-only API, unconfigured paths raise -> 'unreadable').
"""
import copy
import unittest

import fakes  # noqa: F401
from fakes import FakeOps, FakeRegistry, MemoryLog, dhcp_snapshot, static_snapshot

from core import adapter_identity as ai
from core import diagnose, dns_manager
from core.recovery import DnsRecovery

HV = "vEthernet (Default Switch)"
OLD = "0d71477a-b857-4f35-8ca1-fe6e8922ad42"
NEW = "26c1ad26-aa3a-4cb4-a830-d11fec7928e7"
CF4 = ["1.1.1.1", "1.0.0.1"]
CF6 = ["2606:4700:4700::1111", "2606:4700:4700::1001"]


def adapter(name, guid, if_index=17):
    return {"name": name, "guid": guid, "if_index": if_index, "type": "", "permanent_mac": None,
            "hardware": False, "status": "Up"}


def mutations(ops):
    return [c for c in ops.calls if c.startswith(("restore_dns", "set_dns"))]


def setup(store, live, identities):
    ops = FakeOps(adapters=[{"name": a["name"]} for a in identities], dns=copy.deepcopy(live))
    ops.identities = identities
    ops.store = copy.deepcopy(store)
    log = MemoryLog()
    return ops, log, DnsRecovery(ops, log.write)


def assert_read_only(test, reg):
    """Every registry access was a query-only open; nothing else exists to call."""
    for path, access in reg.opened:
        test.assertEqual(access & ~(FakeRegistry.KEY_QUERY_VALUE | FakeRegistry.KEY_WOW64_64KEY), 0, path)
    test.assertFalse(any(hasattr(reg, m) for m in ("SetValueEx", "DeleteKey", "CreateKey", "DeleteValue")))


class RegistryReader(unittest.TestCase):
    def read(self, setup_fn):
        reg = FakeRegistry()
        setup_fn(reg)
        cfg = ai.read_guid_dns_config(OLD, reg=reg)
        assert_read_only(self, reg)
        return cfg, reg

    def test_paths_and_value_interpretation(self):
        def s(reg):
            reg.set_family(OLD, "ipv4", "static", CF4)
            reg.set_family(OLD, "ipv6", "automatic")
        cfg, reg = self.read(s)
        self.assertEqual([p for p, _ in reg.opened], [
            rf"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{{{OLD}}}",
            rf"SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters\Interfaces\{{{OLD}}}"])
        self.assertEqual([q[1] for q in reg.queried], ["NameServer", "NameServer"])
        self.assertEqual(cfg["ipv4"], {"state": "static", "servers": CF4, "detail": ""})
        self.assertEqual(cfg["ipv6"]["state"], "automatic")
        self.assertTrue(cfg["exists"])

    def test_both_keys_absent(self):
        cfg, _ = self.read(lambda r: (r.set_family(OLD, "ipv4", "absent"), r.set_family(OLD, "ipv6", "absent")))
        self.assertEqual((cfg["ipv4"]["state"], cfg["ipv6"]["state"]), ("absent", "absent"))
        self.assertIs(cfg["exists"], False)

    def test_key_exists_but_value_missing_is_automatic_not_absent(self):
        cfg, _ = self.read(lambda r: (r.set_family(OLD, "ipv4", "no_value"), r.set_family(OLD, "ipv6", "no_value")))
        self.assertEqual(cfg["ipv4"]["state"], "automatic")
        self.assertIn("NameServer value not set", cfg["ipv4"]["detail"])
        self.assertIs(cfg["exists"], True)

    def test_access_denied_is_unreadable_never_absent(self):
        cfg, _ = self.read(lambda r: (r.set_family(OLD, "ipv4", "denied"), r.set_family(OLD, "ipv6", "absent")))
        self.assertEqual(cfg["ipv4"], {"state": "unreadable", "servers": [], "detail": "access denied"})
        self.assertIsNone(cfg["exists"], "cannot claim the configuration is gone")

    def test_query_failure_is_unreadable(self):
        cfg, _ = self.read(lambda r: (r.set_family(OLD, "ipv4", "error"), r.set_family(OLD, "ipv6", "error")))
        self.assertEqual(cfg["ipv4"]["state"], "unreadable")
        self.assertIn("winerror", cfg["ipv4"]["detail"])

    def test_unexpected_type_or_garbage_is_unreadable(self):
        def s(reg):
            reg.set_family(OLD, "ipv4", "raw", raw=7, vtype=FakeRegistry.REG_DWORD)
            reg.set_family(OLD, "ipv6", "raw", raw="1.1.1.1")           # IPv4 address in IPv6 key
        cfg, _ = self.read(s)
        self.assertEqual((cfg["ipv4"]["state"], cfg["ipv6"]["state"]), ("unreadable", "unreadable"))

    def test_separators_and_order_preserved(self):
        cfg, _ = self.read(lambda r: (r.set_family(OLD, "ipv4", "raw", raw=" 9.9.9.9 1.1.1.1,8.8.8.8;"),
                                      r.set_family(OLD, "ipv6", "automatic")))
        self.assertEqual(cfg["ipv4"]["servers"], ["9.9.9.9", "1.1.1.1", "8.8.8.8"])


class OrphanDecisions(unittest.TestCase):
    """Saved GUID no longer listed. The same-named adapter has MATCHING DNS in
    every test, so any clearing must come from the registry evidence alone."""

    def run_case(self, store_snap, fam4, fam6, *, live=None, expect_clear):
        ops, log, rec = setup({HV: store_snap}, {HV: live or dhcp_snapshot(guid=NEW)}, [adapter(HV, NEW)])
        for fam, spec in (("ipv4", fam4), ("ipv6", fam6)):
            state, *servers = spec if isinstance(spec, tuple) else (spec,)
            ops.registry.set_family(OLD, fam, state, servers[0] if servers else None)
        self.assertEqual(rec.restore(), expect_clear)
        self.assertEqual(mutations(ops), [], "this path never changes DNS")
        self.assertEqual(ops.reg_reads, [OLD])
        self.assertEqual(ops.reads, [], "the same-named adapter is never consulted")
        assert_read_only(self, ops.registry)
        if expect_clear:
            self.assertEqual(ops.store, {})
        else:
            self.assertEqual(ops.store, {HV: store_snap}, "backup kept unchanged")
            self.assertEqual(rec.identity_blocked, [HV])
        return "\n".join(log.lines)

    def test_1_orphan_config_matches_backup_clears(self):
        text = self.run_case(dhcp_snapshot(guid=OLD), "automatic", "automatic", expect_clear=True)
        self.assertIn("ipv4=automatic ipv6=automatic", text)

    def test_1b_static_orphan_matching_static_backup_clears(self):
        self.run_case(static_snapshot(["192.168.1.53", "9.9.9.9"], guid=OLD),
                      ("static", ["192.168.1.53", "9.9.9.9"]), "automatic", expect_clear=True)

    def test_1c_server_order_matters(self):
        self.run_case(static_snapshot(["192.168.1.53", "9.9.9.9"], guid=OLD),
                      ("static", ["9.9.9.9", "192.168.1.53"]), "automatic", expect_clear=False)

    def test_2_orphan_still_holds_kj_des_cloudflare_retains(self):
        text = self.run_case(dhcp_snapshot(guid=OLD), ("static", CF4), ("static", CF6), expect_clear=False)
        self.assertIn("verdict=retain_differs", text)

    def test_3_ipv4_matches_ipv6_differs_retains(self):
        text = self.run_case(dhcp_snapshot(guid=OLD), "automatic", ("static", CF6), expect_clear=False)
        self.assertIn("ipv4_same=True, ipv6_same=False", text)

    def test_4_both_configurations_absent_clears(self):
        text = self.run_case(dhcp_snapshot(guid=OLD), "absent", "absent", expect_clear=True)
        self.assertIn("its configuration no longer exists", text)

    def test_4b_only_one_family_absent_retains(self):
        text = self.run_case(dhcp_snapshot(guid=OLD), "absent", "automatic", expect_clear=False)
        self.assertIn("verdict=retain_partial", text)

    def test_5_key_exists_value_missing_counts_as_automatic(self):
        self.run_case(dhcp_snapshot(guid=OLD), "no_value", "no_value", expect_clear=True)
        self.run_case(static_snapshot(["192.168.1.53"], guid=OLD), "no_value", "no_value", expect_clear=False)

    def test_6_access_denied_retains(self):
        text = self.run_case(dhcp_snapshot(guid=OLD), "denied", "absent", expect_clear=False)
        self.assertIn("verdict=retain_unreadable", text)

    def test_7_query_failure_retains(self):
        self.run_case(dhcp_snapshot(guid=OLD), "error", "error", expect_clear=False)

    def test_7b_reader_exception_retains(self):
        ops, log, rec = setup({HV: dhcp_snapshot(guid=OLD)}, {HV: dhcp_snapshot(guid=NEW)}, [adapter(HV, NEW)])
        ops.read_guid_dns_config = lambda g: (_ for _ in ()).throw(RuntimeError("boom"))
        self.assertFalse(rec.restore())
        self.assertEqual(mutations(ops), [])
        self.assertIn(HV, ops.store)

    def test_8_same_named_matching_adapter_never_authorizes_clearing(self):
        """The review scenario: matching DNS on a same-named adapter, but the saved
        GUID's own config is unknown/different -> keep."""
        for spec in (("static", CF4), "denied", "error"):
            self.run_case(dhcp_snapshot(guid=OLD), spec, "automatic",
                          live=dhcp_snapshot(guid=NEW), expect_clear=False)

    def test_9_same_named_adapter_with_different_dns_is_irrelevant(self):
        live = static_snapshot(["10.0.0.1"], guid=NEW)
        self.run_case(dhcp_snapshot(guid=OLD), "absent", "absent", live=live, expect_clear=True)
        self.run_case(dhcp_snapshot(guid=OLD), ("static", CF4), "automatic", live=live, expect_clear=False)

    def test_no_same_named_adapter_at_all_uses_same_rule(self):
        ops, _, rec = setup({HV: dhcp_snapshot(guid=OLD)}, {"Wi-Fi": dhcp_snapshot(guid=NEW)},
                            [adapter("Wi-Fi", NEW)])
        ops.registry.set_family(OLD, "ipv4", "absent")
        ops.registry.set_family(OLD, "ipv6", "absent")
        self.assertTrue(rec.restore())
        self.assertEqual(mutations(ops), [])

    def test_listing_failure_never_reads_registry_or_clears(self):
        ops, _, rec = setup({HV: dhcp_snapshot(guid=OLD)}, {HV: dhcp_snapshot(guid=NEW)}, [adapter(HV, NEW)])
        ops.fail["list"] = True
        ops.registry.set_family(OLD, "ipv4", "absent")
        ops.registry.set_family(OLD, "ipv6", "absent")
        self.assertFalse(rec.restore())
        self.assertEqual(ops.reg_reads, [], "GUID presence unknown -> no orphan conclusion")
        self.assertIn(HV, ops.store)

    def test_duplicate_saved_guid_is_ambiguous_not_orphan(self):
        ops, _, rec = setup({HV: dhcp_snapshot(guid=OLD)}, {HV: dhcp_snapshot(guid=OLD)},
                            [adapter(HV, OLD), adapter("Other", OLD, 40)])
        self.assertFalse(rec.restore())
        self.assertEqual(ops.reg_reads, [])
        self.assertEqual(mutations(ops), [])

    def test_10_legacy_backup_without_identity_metadata(self):
        """1.0.x entry (GUID, no identity block): same GUID-scoped rule applies."""
        snap = static_snapshot(["192.168.1.53"], guid=OLD)
        self.assertNotIn("identity", snap)
        self.run_case(snap, ("static", ["192.168.1.53"]), "automatic", expect_clear=True)
        self.run_case(snap, ("static", CF4), "automatic", expect_clear=False)

    def test_guid_and_mac_paths_unchanged(self):
        """Saved GUID present -> restore as before; registry is not consulted."""
        ops, _, rec = setup({"Wi-Fi": static_snapshot(["192.168.1.53"], guid=NEW)},
                            {"Wi-Fi": dhcp_snapshot(guid=NEW)}, [adapter("Wi-Fi", NEW)])
        self.assertTrue(rec.restore())
        self.assertEqual(mutations(ops), ["restore_dns:Wi-Fi"])
        self.assertEqual(ops.reg_reads, [])


class OrphanDiagnostics(unittest.TestCase):
    def report(self, configure):
        reg = FakeRegistry()
        configure(reg)
        reads = []

        def guid_config(g):
            reads.append(g)
            return ai.read_guid_dns_config(g, reg=reg)
        get_calls = []
        backup = {HV: dhcp_snapshot(guid=OLD)}
        before = copy.deepcopy(backup)
        text = diagnose.build_report(
            adapters_fn=lambda: [], get_dns_fn=lambda n, g=None: get_calls.append(n),
            doh_fn=lambda h, log: ["1.2.3.4"],
            tls_fn=lambda h: {"result": "ok", "ms": 1, "chain": [{"subject": "r", "issuer": "r"}]},
            roots_fn=lambda: set(), language_fn=lambda: "FullLanguage",
            backup_fn=lambda: backup, identities_fn=lambda: [adapter(HV, NEW)],
            guid_config_fn=guid_config)
        self.assertEqual(backup, before, "diagnostics never modify the backup")
        self.assertEqual(get_calls, [], "same-named adapter not even read")
        self.assertEqual(reads, [OLD])
        assert_read_only(self, reg)
        return text

    def test_11_reports_each_state_and_action(self):
        t = self.report(lambda r: (r.set_family(OLD, "ipv4", "absent"), r.set_family(OLD, "ipv6", "absent")))
        self.assertIn(f"saved guid={OLD}", t)
        self.assertIn("saved GUID is not present among current adapters", t)
        self.assertIn(f"hint only (never used to decide): adapter with the saved name -> '{HV}' if=17 guid={NEW}", t)
        self.assertIn("saved GUID TCP/IP configuration exists: no", t)
        self.assertIn("ipv4: absent", t)
        self.assertIn("would: clear without changes (configuration absent)", t)

        t = self.report(lambda r: (r.set_family(OLD, "ipv4", "automatic"), r.set_family(OLD, "ipv6", "automatic")))
        self.assertIn("exists: yes", t)
        self.assertIn("matches the backup: ipv4=True ipv6=True", t)
        self.assertIn("would: clear without changes (configuration identical)", t)

        t = self.report(lambda r: (r.set_family(OLD, "ipv4", "static", CF4), r.set_family(OLD, "ipv6", "automatic")))
        self.assertIn("ipv4: static(2)", t)
        self.assertIn("would: manual recovery required", t)

        t = self.report(lambda r: (r.set_family(OLD, "ipv4", "denied"), r.set_family(OLD, "ipv6", "error")))
        self.assertIn("exists: unknown", t)
        self.assertIn("ipv4: unreadable — access denied", t)
        self.assertIn("ipv6: unreadable", t)
        self.assertIn("would: retain backup (configuration could not be read reliably", t)

    def test_12_diagnostics_use_no_mutating_calls(self):
        import inspect
        src = inspect.getsource(diagnose._backup_section) + inspect.getsource(ai.read_guid_dns_config)
        for forbidden in ("SetValue", "DeleteKey", "CreateKey", "DeleteValue", "KEY_WRITE", "KEY_ALL_ACCESS",
                          "KEY_SET_VALUE", "restore_dns", "set_dns", "save_dns_backup", "_store", "netsh"):
            self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
