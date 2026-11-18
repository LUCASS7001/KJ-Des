"""
hosts-file handling (real engine functions on a TEMPORARY file, never the
system hosts file) and DNS recovery invariants.
"""
import os
import tempfile
import unittest
from unittest import mock

import fakes  # noqa: F401  (sets sys.path)
from fakes import FakeOps, MemoryLog, dhcp_snapshot, static_snapshot

from core import discord_unblock as du
from core.recovery import DnsBackupError, DnsRecovery

THIRD_PARTY = ("# user comment\r\n127.0.0.1 localhost\r\n0.0.0.0 ads.example\r\n"
               "10.0.0.5 nas.local\r\n")


class TempHosts(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(prefix="hosts_")
        os.close(fd)
        with open(self.path, "w", encoding="utf-8", newline="") as f:
            f.write(THIRD_PARTY)
        self.patch = mock.patch.object(du, "HOSTS_PATH", self.path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        os.remove(self.path)

    def read(self):
        with open(self.path, encoding="utf-8", newline="") as f:
            return f.read()

    def test_backup_restore_roundtrip_is_byte_exact(self):
        self.assertTrue(du.add_hosts_redirect())
        content = self.read()
        self.assertIn(du.HOSTS_MARK_BEGIN, content)
        self.assertTrue(content.startswith(THIRD_PARTY))
        self.assertEqual(sorted(du.routed_hosts()), sorted(du.BLOCKED_HOSTS))
        self.assertTrue(du.remove_hosts_redirect())
        self.assertEqual(self.read(), THIRD_PARTY)
        self.assertEqual(du.routed_hosts(), [])

    def test_add_twice_keeps_single_block(self):
        du.add_hosts_redirect()
        du.add_hosts_redirect()
        self.assertEqual(self.read().count(du.HOSTS_MARK_BEGIN), 1)

    def test_foreign_dport_block_is_not_removed(self):
        foreign = ("# >>> DPort Discord unblock >>>\n127.0.0.1 discord.com\n"
                   "# <<< DPort Discord unblock <<<\n")
        with open(self.path, "a", encoding="utf-8", newline="") as f:
            f.write(foreign)
        du.add_hosts_redirect()
        du.remove_hosts_redirect()
        self.assertTrue(self.read().endswith(foreign))

    def test_missing_end_marker_keeps_following_user_lines(self):
        with open(self.path, "a", encoding="utf-8", newline="") as f:
            f.write(du.HOSTS_MARK_BEGIN + "\n127.0.0.1 discord.com\n10.1.1.1 printer.lan\n")
        self.assertTrue(du.remove_hosts_redirect())
        content = self.read()
        self.assertIn("10.1.1.1 printer.lan", content)
        self.assertNotIn("127.0.0.1 discord.com", content)

    def test_routed_counts_only_allowlisted_lines_in_block(self):
        with open(self.path, "a", encoding="utf-8", newline="") as f:
            f.write(f"{du.HOSTS_MARK_BEGIN}\n127.0.0.1 discord.com\n127.0.0.1 evil.example\n"
                    f"{du.HOSTS_MARK_END}\n127.0.0.1 cdn.discordapp.com\n")
        self.assertEqual(du.routed_hosts(), ["discord.com"])


class DnsRecoveryTests(unittest.TestCase):
    def test_failed_batch_backup_saves_nothing(self):
        ops = FakeOps(adapters=[{"name": "A"}, {"name": "B"}],
                      dns={"A": dhcp_snapshot(), "B": {"ipv4": {"dhcp": "yes"}}})
        rec = DnsRecovery(ops, MemoryLog().write)
        with self.assertRaises(Exception):
            rec.backup(ops.active_adapters())
        self.assertEqual(ops.store, {})

    def test_adapter_identity_change_is_rejected(self):
        ops = FakeOps(dns={"Wi-Fi": dhcp_snapshot(guid="11111111-1111-1111-1111-111111111111")})
        ops.store = {"Wi-Fi": dhcp_snapshot(guid="22222222-2222-2222-2222-222222222222")}
        with self.assertRaises(DnsBackupError):
            DnsRecovery(ops, MemoryLog().write).backup(ops.active_adapters())

    def test_missing_adapter_is_kept_for_later(self):
        ops = FakeOps(adapters=[])
        ops.store = {"USB-LAN": static_snapshot(["1.2.3.4"])}
        ops.all_adapter_names = lambda: {"Wi-Fi"}
        rec = DnsRecovery(ops, MemoryLog().write)
        self.assertFalse(rec.restore())
        self.assertIn("USB-LAN", ops.store)
        self.assertNotIn("restore_dns:USB-LAN", ops.calls)

    def test_malformed_snapshot_is_never_sent_to_netsh(self):
        ops = FakeOps()
        ops.store = {"Wi-Fi": {"ipv4": {"dhcp": False, "servers": ["not-an-ip"]},
                               "ipv6": {"dhcp": True, "servers": []}}}
        rec = DnsRecovery(ops, MemoryLog().write)
        self.assertFalse(rec.restore())
        self.assertNotIn("restore_dns:Wi-Fi", ops.calls)
        self.assertIn("Wi-Fi", ops.store)

    def test_never_falls_back_to_hardcoded_resolver(self):
        ops = FakeOps(dns={"Wi-Fi": static_snapshot(["192.168.50.1"])})
        rec = DnsRecovery(ops, MemoryLog().write)
        rec.backup(ops.active_adapters())
        ops.set_secure_dns("Wi-Fi")
        self.assertTrue(rec.restore())
        self.assertEqual(ops.dns["Wi-Fi"]["ipv4"]["servers"], ["192.168.50.1"])


if __name__ == "__main__":
    unittest.main()
