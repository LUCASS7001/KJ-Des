"""
Regression tests for the field report from a second Windows 11 PC:
  * '??Ethernet' -> "Adapter not uniquely resolved" (lossy adapter listing)
  * Hyper-V 'vEthernet (Default Switch)' with automatic DNS and 0 servers
  * Cloudflare DoH: OpenSSL error 20 (missing trust anchor), Google OK
No real DNS, hosts, registry, task or certificate store is changed.
"""
import json
import os
import socket
import ssl
import subprocess
import threading
import unittest
from unittest import mock

import fakes  # noqa: F401
from fakes import FakeOps, MemoryLog, dhcp_snapshot, static_snapshot

from core import adapter_manager, diagnose
from core.connection import ConnectionManager, State
from core.recovery import DnsBackupError, DnsRecovery

UNICODE_NAME = "إتEthernet"            # two chars outside OEM code page 437
G1 = "11111111-1111-1111-1111-111111111111"
G2 = "22222222-2222-2222-2222-222222222222"
G3 = "33333333-3333-3333-3333-333333333333"
TLS_DIR = os.path.join(os.path.dirname(__file__), "data", "tls")


class AdapterListingEncoding(unittest.TestCase):
    def _listing(self, payload):
        result = mock.Mock(returncode=0, stdout=json.dumps(payload, ensure_ascii=False))
        with mock.patch.object(adapter_manager.subprocess, "run", return_value=result) as run:
            return adapter_manager._get_all_adapters_powershell(), run

    def test_unicode_name_guid_and_index_survive(self):
        ads, run = self._listing([
            {"Name": UNICODE_NAME, "Status": "Up", "AdminStatus": "Up",
             "InterfaceDescription": "Realtek PCIe 2.5GbE Family Controller", "Guid": G1.upper(), "ifIndex": 7},
            {"Name": "vEthernet (Default Switch)", "Status": "Up", "AdminStatus": "Up",
             "InterfaceDescription": "Hyper-V Virtual Ethernet Adapter", "Guid": G2, "ifIndex": 31}])
        self.assertEqual([a["name"] for a in ads], [UNICODE_NAME, "vEthernet (Default Switch)"])
        self.assertEqual([a["guid"] for a in ads], [G1, G2])        # canonical lowercase
        self.assertEqual([a["if_index"] for a in ads], [7, 31])
        script = run.call_args[0][0][-1]
        self.assertIn("[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)", script)
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(run.call_args.kwargs["errors"], "strict")

    def test_invalid_guid_is_dropped_not_guessed(self):
        ads, _ = self._listing({"Name": "Ethernet", "Status": "Up", "AdminStatus": "Up",
                                "InterfaceDescription": "x", "Guid": "not-a-guid", "ifIndex": "7"})
        self.assertIsNone(ads[0]["guid"])
        self.assertIsNone(ads[0]["if_index"])

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell round trip")
    def test_real_powershell_round_trip_root_cause(self):
        """Proves the field symptom: without UTF-8 output the name becomes '??Ethernet'."""
        make = "$n = [string][char]0x0625 + [string][char]0x062A + 'Ethernet'; [pscustomobject]@{Name=$n} | ConvertTo-Json -Compress"

        def run(prefix, errors):
            r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", prefix + make],
                               capture_output=True, text=True, encoding="utf-8", errors=errors, timeout=60,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return json.loads(r.stdout)["Name"]
        old = run("", "ignore")
        new = run("[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); ", "strict")
        self.assertEqual(new, UNICODE_NAME)
        if old != UNICODE_NAME:          # OEM code page cannot represent the name
            self.assertIn("?", old)


class StableAdapterSelection(unittest.TestCase):
    def _ops(self, adapters, dns):
        ops = FakeOps(adapters=adapters, dns=dns)
        seen = []
        real = ops.get_dns

        def get_dns(name, guid=None):
            seen.append((name, guid))
            snap = real(name)
            if guid and guid != snap.get("interface_guid"):
                raise RuntimeError("Adapter not uniquely resolved: guid")
            return snap
        ops.get_dns = get_dns
        return ops, seen

    def test_backup_reads_each_adapter_by_its_guid(self):
        ops, seen = self._ops(
            [{"name": UNICODE_NAME, "guid": G1, "if_index": 7},
             {"name": "vEthernet (Default Switch)", "guid": G2, "if_index": 31}],
            {UNICODE_NAME: static_snapshot(["192.168.1.53"], guid=G1),
             "vEthernet (Default Switch)": dhcp_snapshot(guid=G2)})
        DnsRecovery(ops, MemoryLog().write).backup(ops.active_adapters())
        self.assertEqual(seen, [(UNICODE_NAME, G1), ("vEthernet (Default Switch)", G2)])
        self.assertEqual(ops.store[UNICODE_NAME]["interface_guid"], G1)

    def test_duplicate_display_names_are_refused_before_any_change(self):
        ops, seen = self._ops(
            [{"name": "Ethernet", "guid": G1, "if_index": 7},
             {"name": "Ethernet", "guid": G3, "if_index": 9}],
            {"Ethernet": dhcp_snapshot(guid=G1)})
        # the backup refuses before reading any adapter
        with self.assertRaises(DnsBackupError):
            DnsRecovery(ops, MemoryLog().write).backup(ops.active_adapters())
        self.assertEqual(seen, [])
        # and the full connect flow changes nothing
        log = MemoryLog()
        mgr = ConnectionManager(ops, log.write, source_dev=True)
        self.assertFalse(mgr.connect())
        self.assertEqual(mgr.status.error, "err_dns_backup")
        self.assertFalse(any(c.startswith(("set_dns", "restore_dns", "add_hosts", "relay_start"))
                             for c in ops.calls), ops.calls)
        self.assertEqual(ops.store, {})
        self.assertIn("ambiguous adapter name", "\n".join(log.lines))

    def test_guid_mismatch_while_reading_is_refused(self):
        ops, _ = self._ops([{"name": "Ethernet", "guid": G1}], {"Ethernet": dhcp_snapshot(guid=G2)})
        with self.assertRaises(DnsBackupError):
            DnsRecovery(ops, MemoryLog().write).backup(ops.active_adapters())
        self.assertEqual(ops.store, {})

    def test_garbled_name_changes_nothing(self):
        """The field case: a lossy name cannot be resolved -> fail closed."""
        ops, _ = self._ops([{"name": "??Ethernet", "guid": None},
                            {"name": "vEthernet (Default Switch)", "guid": G2}],
                           {"vEthernet (Default Switch)": dhcp_snapshot(guid=G2)})
        mgr = ConnectionManager(ops, MemoryLog().write, source_dev=True)
        self.assertFalse(mgr.connect())
        self.assertEqual(mgr.status.error, "err_dns_backup")
        self.assertFalse(any(c.startswith("set_dns") for c in ops.calls))
        self.assertEqual(ops.store, {})


class ExactRestorePerAdapter(unittest.TestCase):
    def test_unicode_static_and_hyperv_automatic_zero_servers_restored_exactly(self):
        dns = {UNICODE_NAME: static_snapshot(["192.168.1.53", "9.9.9.9"], guid=G1),
               "vEthernet (Default Switch)": dhcp_snapshot(guid=G2)}
        ops = FakeOps(adapters=[{"name": UNICODE_NAME, "guid": G1},
                                {"name": "vEthernet (Default Switch)", "guid": G2}], dns=dns)
        mgr = ConnectionManager(ops, MemoryLog().write, source_dev=True)
        self.assertTrue(mgr.connect())
        self.assertEqual(ops.dns["vEthernet (Default Switch)"]["ipv4"]["servers"], ["1.1.1.1", "1.0.0.1"])
        self.assertTrue(mgr.disconnect())
        self.assertEqual(ops.dns, ops.original_dns)
        hv = ops.dns["vEthernet (Default Switch)"]
        self.assertTrue(hv["ipv4"]["dhcp"] and hv["ipv6"]["dhcp"])
        self.assertEqual(hv["ipv4"]["servers"], [])
        self.assertEqual(ops.dns[UNICODE_NAME]["ipv4"]["servers"], ["192.168.1.53", "9.9.9.9"])
        self.assertIn(f"restore_dns:{UNICODE_NAME}", ops.calls)
        self.assertEqual(mgr.status.state, State.DISCONNECTED)


class _LocalTls:
    """Local TLS server presenting a leaf issued by an untrusted, absent test CA."""

    def __init__(self):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(os.path.join(TLS_DIR, "leaf.pem"), os.path.join(TLS_DIR, "leaf.key"))
        self.ctx = ctx
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(2)
        self.port = self.sock.getsockname()[1]
        self.received = b""
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        try:
            conn, _ = self.sock.accept()
            with self.ctx.wrap_socket(conn, server_side=True) as tls:
                self.received += tls.recv(100)
        except (OSError, ssl.SSLError):
            pass

    def connect(self, _addr, timeout=None):
        return socket.create_connection(("127.0.0.1", self.port), timeout=timeout)

    def close(self):
        self.sock.close()


class StrictTlsWithMissingRoot(unittest.TestCase):
    def test_missing_root_fails_strictly_with_code_20_and_reports_chain(self):
        server = _LocalTls()
        try:
            r = diagnose.tls_check("localhost", timeout=5, connect=server.connect)
        finally:
            server.close()
        self.assertEqual(r["result"], "verify_failed")
        self.assertEqual(r["verify_code"], 20)                 # unable to get local issuer certificate
        self.assertEqual(r["presented_chain"][0]["subject"], "localhost")
        self.assertIn("not trusted anywhere", r["presented_chain"][0]["issuer"])
        self.assertEqual(len(r["presented_chain"][0]["sha256"]), 64)
        self.assertNotIn("chain", r, "a failed handshake must never be reported as trusted")
        self.assertEqual(server.received, b"", "no application data may be sent")

    def test_fingerprint_verdicts(self):
        leaf = {"subject": "cloudflare-dns.com", "sha256": "AA" * 32}
        genuine = [leaf, {"subject": "SSL.com SSL Intermediate CA ECC R2",
                          "sha256": "948B7111AF42F546D579CFF5CE2BDEC82134DD9914842BDDB0C52872EB604E39"}]
        forged = [leaf, {"subject": "SSL.com SSL Intermediate CA ECC R2", "sha256": "BB" * 32}]
        self.assertIn("no interception", diagnose.ca_verdict(genuine))
        self.assertIn("likely intercepted", diagnose.ca_verdict(forged))
        self.assertIn("cannot compare", diagnose.ca_verdict([leaf]))

    def test_known_fingerprints_are_report_only(self):
        """KNOWN_GENUINE_CA must never feed into a trust decision."""
        import inspect
        from core import discord_unblock, system_ops
        for mod in (discord_unblock, system_ops):
            self.assertNotIn("KNOWN_GENUINE_CA", inspect.getsource(mod))
        src = inspect.getsource(diagnose)
        for forbidden in ("load_verify_locations", "cadata", "CERT_NONE", "add_cert"):
            self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
