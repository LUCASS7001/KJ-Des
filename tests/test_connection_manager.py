"""
KJ Des connection lifecycle tests. Every OS operation is the in-memory FakeOps;
no real DNS, hosts file or scheduled task is touched.
"""
import threading
import time
import unittest

from fakes import FakeOps, MemoryLog, dhcp_snapshot, static_snapshot

from core.connection import ConnectionManager, State


def make(ops=None, **kw):
    ops = ops or FakeOps()
    states = []
    mgr = ConnectionManager(ops, MemoryLog().write, on_change=lambda s: states.append(s), **kw)
    return mgr, ops, states


class CleanSystemMixin:
    def assert_clean(self, ops):
        self.assertEqual(ops.dns, ops.original_dns, "DNS not restored exactly")
        self.assertEqual(ops.hosts_entries, [], "hosts block left behind")
        self.assertFalse(ops.relay.running, "relay still running")
        self.assertFalse(ops.task, "recovery task left behind")
        self.assertEqual(ops.store, {}, "DNS backup left behind")


class ConnectSuccess(CleanSystemMixin, unittest.TestCase):
    def test_successful_connection_is_verified_then_reported(self):
        mgr, ops, states = make()
        self.assertTrue(mgr.connect())
        st = mgr.status
        self.assertEqual(st.state, State.CONNECTED)
        self.assertEqual((st.routed, st.total), (5, 5))
        self.assertEqual(st.dns, "1.1.1.1")
        self.assertTrue(st.dns_secure)
        self.assertIsNotNone(st.connected_since)
        # CONNECTED only after verification ran
        self.assertLess(ops.calls.index("add_hosts"), ops.calls.index("verify"))
        first_connected = next(i for i, s in enumerate(states) if s.state == State.CONNECTED)
        self.assertTrue(all(s.state == State.CONNECTING for s in states[:first_connected]))
        self.assertEqual(states[first_connected - 1].step, "step_verify")
        mgr.shutdown(timeout=5)

    def test_order_backup_before_dns_and_task_before_hosts(self):
        mgr, ops, _ = make()
        mgr.connect()
        c = ops.calls
        self.assertLess(c.index("preflight"), c.index("set_dns:Wi-Fi"))
        self.assertLess(c.index("relay_start"), c.index("install_task"))
        self.assertLess(c.index("install_task"), c.index("add_hosts"))
        mgr.shutdown(timeout=5)

    def test_disconnect_restores_original_static_dns_exactly(self):
        ops = FakeOps(dns={"Wi-Fi": static_snapshot(["192.168.1.53", "9.9.9.9"])})
        mgr, ops, _ = make(ops)
        mgr.connect()
        self.assertEqual(ops.dns["Wi-Fi"]["ipv4"]["servers"], ["1.1.1.1", "1.0.0.1"])
        self.assertTrue(mgr.disconnect())
        self.assertEqual(mgr.status.state, State.DISCONNECTED)
        self.assertEqual(mgr.status.dns, "192.168.1.53")
        self.assert_clean(ops)

    def test_unrelated_adapter_is_never_touched(self):
        ops = FakeOps(adapters=[{"name": "Ethernet"}],
                      dns={"Ethernet": dhcp_snapshot(),
                           "VPN": static_snapshot(["10.0.0.1"], guid="99999999-2222-3333-4444-555555555555")})
        ops.all_adapter_names = lambda: {"Ethernet", "VPN"}
        mgr, ops, _ = make(ops)
        mgr.connect()
        mgr.disconnect()
        touched = [c for c in ops.calls if ":" in c and c.split(":")[0] in ("set_dns", "restore_dns")]
        self.assertTrue(all(c.endswith("Ethernet") for c in touched), touched)
        self.assertEqual(ops.dns["VPN"], ops.original_dns["VPN"])

    def test_existing_backup_is_not_overwritten_by_modified_state(self):
        ops = FakeOps(dns={"Wi-Fi": static_snapshot(["8.8.4.4"])})
        mgr, ops, _ = make(ops)
        mgr.connect()
        # simulate a second connect attempt while DNS is already 1.1.1.1
        mgr._relay.stop()
        mgr.dns.backup(ops.active_adapters())
        self.assertEqual(ops.store["Wi-Fi"]["ipv4"]["servers"], ["8.8.4.4"])
        mgr.shutdown(timeout=5)


class ConnectFailures(CleanSystemMixin, unittest.TestCase):
    def run_failure(self, fail, expected, ops=None):
        mgr, ops, states = make(ops)
        ops.fail.update(fail)
        self.assertFalse(mgr.connect())
        self.assertEqual(mgr.status.state, State.ERROR)
        self.assertEqual(mgr.status.error, expected)
        self.assertNotIn(State.CONNECTED, [s.state for s in states])
        self.assert_clean(ops)
        return mgr, ops

    def test_no_recovery_target_touches_nothing(self):
        _, ops = self.run_failure({"no_target": True}, "err_no_recovery")
        self.assertEqual(ops.calls, [])

    def test_doh_failure_touches_nothing(self):
        _, ops = self.run_failure({"doh": True}, "err_doh")
        self.assertEqual(ops.calls, ["preflight"])

    def test_unwritable_protected_backup_refuses_connection(self):
        ops = FakeOps()
        ops.store_writable = False
        _, ops = self.run_failure({}, "err_dns_backup", ops)
        self.assertNotIn("set_dns:Wi-Fi", ops.calls)

    def test_unreadable_dns_refuses_connection(self):
        _, ops = self.run_failure({"get_dns": True}, "err_dns_backup")
        self.assertFalse(any(c.startswith("set_dns") for c in ops.calls))

    def test_no_adapter(self):
        self.run_failure({}, "err_no_adapter", FakeOps(adapters=[], dns={}))

    def test_dns_apply_failure_restores(self):
        ops = FakeOps(adapters=[{"name": "A"}, {"name": "B"}],
                      dns={"A": dhcp_snapshot(), "B": static_snapshot(["4.2.2.2"])})
        _, ops = self.run_failure({"set_dns": "B"}, "err_dns_apply", ops)
        self.assertIn("restore_dns:A", ops.calls)

    def test_port_busy(self):
        _, ops = self.run_failure({"port": True}, "err_port")
        self.assertNotIn("add_hosts", ops.calls)

    def test_port_taken_by_other_tool_touches_nothing(self):
        _, ops = self.run_failure({"port_taken": True}, "err_port")
        self.assertEqual(ops.calls, ["preflight"])

    def test_task_failure_never_writes_hosts(self):
        _, ops = self.run_failure({"task": True}, "err_failsafe")
        self.assertNotIn("add_hosts", ops.calls)

    def test_hosts_locked(self):
        self.run_failure({"hosts": True}, "err_hosts_locked")

    def test_hosts_access_denied_without_admin(self):
        ops = FakeOps()
        ops.admin = False
        self.run_failure({"hosts": True, "hosts_winerror": 5}, "err_admin", ops)

    def test_verification_failure_rolls_everything_back(self):
        _, ops = self.run_failure({"verify": True}, "err_verify")
        self.assertEqual(ops.calls.count("verify"), 2)

    def test_verification_retry_can_succeed(self):
        mgr, ops, _ = make()
        ops.verify_results = [(False, "timeout"), (True, "ok")]
        self.assertTrue(mgr.connect())
        self.assertEqual(mgr.status.state, State.CONNECTED)
        mgr.shutdown(timeout=5)

    def test_unexpected_exception_rolls_back(self):
        mgr, ops, _ = make()
        ops.install_failsafe = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
        self.assertFalse(mgr.connect())
        self.assertEqual(mgr.status.state, State.ERROR)
        self.assert_clean(ops)


class PartialAndRecovery(unittest.TestCase):
    def test_partial_restore_keeps_backup_and_flags_restore(self):
        mgr, ops, _ = make()
        mgr.connect()
        ops.fail["restore_dns"] = True
        self.assertFalse(mgr.disconnect())
        st = mgr.status
        self.assertEqual((st.state, st.error, st.restore_pending), (State.ERROR, "err_restore_partial", True))
        self.assertIn("Wi-Fi", ops.store, "failed adapter must stay in backup for retry")
        ops.fail.clear()
        self.assertTrue(mgr.restore_defaults())
        self.assertEqual(mgr.status.state, State.DISCONNECTED)
        self.assertEqual(ops.store, {})
        self.assertEqual(ops.dns, ops.original_dns)

    def test_hosts_cleanup_failure_is_reported(self):
        mgr, ops, _ = make()
        mgr.connect()
        ops.fail["remove_hosts"] = True
        self.assertFalse(mgr.disconnect())
        self.assertTrue(mgr.status.restore_pending)
        self.assertEqual(mgr.status.routed, 5)

    def test_startup_recovers_crashed_session(self):
        ops = FakeOps(dns={"Wi-Fi": static_snapshot(["192.168.0.1"])})
        crashed, ops, _ = make(ops)
        crashed.connect()                      # "crash": no disconnect
        self.assertTrue(ops.hosts_entries and ops.store)
        fresh, _, _ = make(ops)
        self.assertTrue(fresh.recover_on_startup())
        self.assertEqual(ops.hosts_entries, [])
        self.assertEqual(ops.store, {})
        self.assertEqual(ops.dns, ops.original_dns)
        self.assertEqual(fresh.status.state, State.DISCONNECTED)

    def test_startup_with_clean_system_changes_nothing(self):
        mgr, ops, _ = make()
        self.assertTrue(mgr.recover_on_startup())
        self.assertFalse(any(c.startswith(("set_dns", "restore_dns")) for c in ops.calls))

    def test_startup_failure_sets_restore_pending(self):
        ops = FakeOps()
        ops.store = {"Wi-Fi": dhcp_snapshot()}
        ops.fail["restore_dns"] = True
        mgr, ops, _ = make(ops)
        self.assertFalse(mgr.recover_on_startup())
        self.assertTrue(mgr.status.restore_pending)


class Concurrency(unittest.TestCase):
    def test_duplicate_operations_are_rejected(self):
        mgr, ops, _ = make()
        gate = threading.Event()
        original = ops.verify_path

        def slow_verify(timeout=30.0):
            gate.wait(5)
            return original(timeout)
        ops.verify_path = slow_verify
        self.assertTrue(mgr.start_connect())
        time.sleep(0.2)
        self.assertFalse(mgr.start_connect())
        self.assertFalse(mgr.start_disconnect())
        self.assertFalse(mgr.connect())
        gate.set()
        mgr._worker.join(5)
        self.assertEqual(ops.calls.count("relay_start"), 1)
        self.assertEqual(mgr.status.state, State.CONNECTED)
        mgr.shutdown(timeout=5)

    def test_shutdown_waits_for_running_operation_then_restores(self):
        mgr, ops, _ = make()
        gate = threading.Event()
        ops.verify_path = lambda timeout=30.0: (gate.wait(5), (True, "ok"))[1]
        mgr.start_connect()
        time.sleep(0.2)
        threading.Timer(0.3, gate.set).start()
        self.assertTrue(mgr.shutdown(timeout=10))
        self.assertEqual(ops.hosts_entries, [])
        self.assertEqual(ops.dns, ops.original_dns)
        self.assertFalse(mgr.start_connect(), "no new operation after shutdown")


class Watchdog(unittest.TestCase):
    def wait_for(self, mgr, state, timeout=5):
        end = time.time() + timeout
        while time.time() < end:
            if mgr.status.state == state:
                return True
            time.sleep(0.05)
        return False

    def test_relay_death_restores_and_reports(self):
        mgr, ops, _ = make(watchdog_interval=0.05)
        mgr.connect()
        ops.relay.running = False
        self.assertTrue(self.wait_for(mgr, State.ERROR))
        self.assertEqual(mgr.status.error, "err_relay_stopped")
        self.assertFalse(mgr.status.restore_pending)
        self.assertEqual(ops.dns, ops.original_dns)
        self.assertEqual(ops.hosts_entries, [])

    def test_hosts_removed_externally_is_detected(self):
        mgr, ops, _ = make(watchdog_interval=0.05, hosts_check_every=1)
        mgr.connect()
        ops.hosts_entries = []
        self.assertTrue(self.wait_for(mgr, State.ERROR))
        self.assertEqual(mgr.status.error, "err_hosts_removed")
        self.assertFalse(ops.relay.running)

    def test_routed_count_reflects_hosts_file(self):
        mgr, ops, _ = make(watchdog_interval=0.05, hosts_check_every=1)
        mgr.connect()
        ops.hosts_entries = ops.hosts_entries[:3]
        end = time.time() + 3
        while time.time() < end and mgr.status.routed != 3:
            time.sleep(0.05)
        self.assertEqual(mgr.status.routed, 3)
        mgr.shutdown(timeout=5)


class SourceDevMode(unittest.TestCase):
    def test_source_dev_skips_task_but_still_restores(self):
        mgr, ops, _ = make(source_dev=True)
        ops.fail["no_target"] = True
        self.assertTrue(mgr.connect())
        self.assertNotIn("install_task", ops.calls)
        self.assertTrue(mgr.disconnect())
        self.assertEqual(ops.hosts_entries, [])


if __name__ == "__main__":
    unittest.main()
