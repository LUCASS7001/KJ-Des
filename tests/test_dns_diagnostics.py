"""
Regression tests for the field failure on a second Windows 11 PC:
  * Windows DNS snapshot failed ("Windows DNS sorgusu basarisiz") -> err_dns_backup
  * Cloudflare DoH failed certificate verification (code 20), Google succeeded
No real DNS, hosts, registry or adapter setting is touched.
"""
import io
import json
import ssl
import unittest
import urllib.error
from unittest import mock

import fakes  # noqa: F401
from fakes import FakeOps, MemoryLog, dhcp_snapshot

from core import diagnose, discord_unblock, dns_manager
from core.connection import ConnectionManager, State


class PowerShellFailureReason(unittest.TestCase):
    R = staticmethod(dns_manager.powershell_failure_reason)

    def test_own_throw_text_with_family(self):
        err = ("Exception calling ... \r\nDNS family unavailable: ipv6 (no DNS client entry)\r\n"
               "At line:18 char:5\r\n+ CategoryInfo : OperationStopped\r\n")
        self.assertEqual(self.R(err), "DNS family unavailable: ipv6 (no DNS client entry)")

    def test_registry_key_missing(self):
        self.assertEqual(self.R("DNS registry key unavailable: ipv4\n"),
                         "DNS registry key unavailable: ipv4")

    def test_unexpected_powershell_error_keeps_error_id(self):
        err = ("Cannot set property. Property setting is supported only on core types in this "
               "language mode.\r\nAt line:3 char:1\r\n"
               "    + FullyQualifiedErrorId : PropertySetterNotSupportedInConstrainedLanguage\r\n")
        reason = self.R(err)
        self.assertIn("Cannot set property", reason)
        self.assertIn("[PropertySetterNotSupportedInConstrainedLanguage]", reason)
        self.assertNotIn("\n", reason)

    def test_empty_and_huge_output(self):
        self.assertEqual(self.R(""), "no error output")
        self.assertEqual(self.R(None), "no error output")
        self.assertLessEqual(len(self.R("x" * 5000)), 200)


class GetDnsFailClosed(unittest.TestCase):
    def _run(self, returncode, stdout="", stderr=""):
        result = mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)
        with mock.patch.object(dns_manager.subprocess, "run", return_value=result) as run:
            try:
                return dns_manager.get_dns("Ethernet 2"), run
            except dns_manager.DnsSnapshotError as exc:
                return exc, run

    def test_failed_query_raises_with_reason(self):
        exc, _ = self._run(1, stderr="DNS family unavailable: ipv6 (no DNS client entry)\n")
        self.assertIsInstance(exc, dns_manager.DnsSnapshotError)
        self.assertIn("Windows DNS sorgusu basarisiz", str(exc))
        self.assertIn("neden=DNS family unavailable: ipv6", str(exc))
        self.assertIn("kod=1", str(exc))

    def test_script_still_fails_closed_on_every_check(self):
        _, run = self._run(1, stderr="x")
        script = run.call_args[0][0][-1]
        self.assertIn("$ErrorActionPreference = 'Stop'", script)
        for marker in ("Adapter not uniquely resolved", "Adapter identity mismatch",
                       "DNS registry key unavailable", "Invalid NameServer type",
                       "DNS family unavailable"):
            self.assertTrue(f"throw '{marker}" in script or f"throw ('{marker}" in script, marker)
        # no registry or network writes from the snapshot script
        for forbidden in ("SetValue", "Set-DnsClient", "netsh", "New-Item", "Remove-"):
            self.assertNotIn(forbidden, script)

    def test_success_path_unchanged(self):
        ok = {"interface_guid": "11111111-2222-3333-4444-555555555555",
              "ipv4": {"dhcp": True, "servers": [], "effective": ["192.168.1.1"]},
              "ipv6": {"dhcp": True, "servers": [], "effective": []}}
        snap, _ = self._run(0, stdout=json.dumps(ok))
        self.assertTrue(snap["ipv4"]["dhcp"])


class OneUnreadableAdapterBlocksEverything(unittest.TestCase):
    def test_second_adapter_unreadable_changes_nothing_and_is_logged(self):
        ops = FakeOps(adapters=[{"name": "Wi-Fi", "source": "powershell"},
                                {"name": "VPN Adapter", "source": "powershell"}],
                      dns={"Wi-Fi": dhcp_snapshot(), "VPN Adapter": dhcp_snapshot()})
        real_get = ops.get_dns

        def get_dns(name, guid=None):
            if name == "VPN Adapter":
                raise dns_manager.DnsSnapshotError(
                    "Windows DNS sorgusu basarisiz | neden=DNS family unavailable: ipv4 (no DNS client entry) | kod=1")
            return real_get(name, guid)
        ops.get_dns = get_dns
        log = MemoryLog()
        mgr = ConnectionManager(ops, log.write, source_dev=True)
        self.assertFalse(mgr.connect())
        self.assertEqual(mgr.status.state, State.ERROR)
        self.assertEqual(mgr.status.error, "err_dns_backup")
        self.assertFalse(any(c.startswith("set_dns") for c in ops.calls), ops.calls)
        self.assertNotIn("add_hosts", ops.calls)
        self.assertEqual(ops.store, {})
        self.assertEqual(ops.dns, ops.original_dns)
        text = "\n".join(log.lines)
        self.assertIn("DNS | active adapters: 'Wi-Fi'[powershell], 'VPN Adapter'[powershell]", text)
        self.assertIn("adapter='VPN Adapter'", text)
        self.assertIn("neden=DNS family unavailable: ipv4", text)
        self.assertIn("system untouched", text)


class _JsonResponse(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class CloudflareCertificateFailure(unittest.TestCase):
    def test_both_cloudflare_endpoints_code20_google_ok(self):
        cert_err = ssl.SSLCertVerificationError(1, "certificate verify failed")
        cert_err.verify_code = 20
        cert_err.verify_message = "unable to get local issuer certificate"

        def urlopen(req, timeout=None):
            if "dns.google" in req.full_url:
                return _JsonResponse(json.dumps({"Status": 0, "Answer": [
                    {"type": 1, "data": f"162.159.135.{i}"} for i in range(1, 6)]}).encode())
            raise urllib.error.URLError(cert_err)
        lines = []
        with mock.patch.object(discord_unblock.urllib.request, "urlopen", urlopen):
            ips = discord_unblock.doh_resolve("discord.com", log=lines.append, total_timeout=10)
        self.assertEqual(len(ips), 5)
        cf = [l for l in lines if "saglayici=Cloudflare" in l]
        self.assertEqual(len(cf), 2)
        for l in cf:
            self.assertIn("verify_code=20", l)
            self.assertIn("unable to get local issuer certificate", l)
        self.assertTrue(any("saglayici=Google" in l and "yedek=true" in l for l in lines))


class DiagnoseReport(unittest.TestCase):
    def _report(self, *, get_dns, tls):
        return diagnose.build_report(
            adapters_fn=lambda: [{"name": "Wi-Fi", "source": "powershell", "type": "NIC"},
                                 {"name": "VPN Adapter", "source": "powershell", "type": "TAP"}],
            get_dns_fn=get_dns, doh_fn=lambda host, log: (log("DoH | ok"), ["1.2.3.4"])[1],
            tls_fn=tls, roots_fn=lambda: {"GlobalSign nv-sa / GlobalSign Root CA"},
            language_fn=lambda: "FullLanguage", is_admin_fn=lambda: True)

    def test_report_pinpoints_unreadable_adapter_and_missing_root(self):
        def get_dns(name, guid=None):
            if name == "VPN Adapter":
                raise dns_manager.DnsSnapshotError("Windows DNS sorgusu basarisiz | neden=DNS family unavailable: ipv4")
            return dhcp_snapshot()

        def tls(host):
            if host == "dns.google":
                return {"result": "ok", "ms": 5, "chain": [
                    {"subject": "dns.google", "issuer": "WE2"},
                    {"subject": "GlobalSign nv-sa / GlobalSign Root CA", "issuer": "GlobalSign nv-sa / GlobalSign Root CA"}]}
            return {"result": "verify_failed", "verify_code": 20,
                    "verify_message": "unable to get local issuer certificate",
                    "presented_chain": [
                        {"subject": "Cloudflare, Inc. / cloudflare-dns.com", "issuer": "SSL Corp / SSL.com SSL Intermediate CA ECC R2"},
                        {"subject": "SSL Corp / SSL.com SSL Intermediate CA ECC R2",
                         "issuer": "SSL Corporation / SSL.com Root Certification Authority ECC"}]}
        text = self._report(get_dns=get_dns, tls=tls)
        self.assertIn("'VPN Adapter'", text)
        self.assertIn("DNS read: FAILED — Windows DNS sorgusu basarisiz | neden=DNS family unavailable: ipv4", text)
        self.assertIn("backup would FAIL", text)
        self.assertIn("1 of 2 adapter(s) unreadable", text)
        self.assertIn("code=20", text)
        self.assertIn("issuer needed: 'SSL Corporation / SSL.com Root Certification Authority ECC'"
                      " -> in Windows ROOT store: False", text)
        self.assertIn("Google (dns.google): OK", text)
        self.assertIn("Read-only: nothing on this computer was changed.", text)
        for private in ("192.168.", "1.1.1.1,"):
            self.assertNotIn(private, text.split("== 2.")[0])

    def test_tls_check_reports_connect_failure(self):
        def boom(*a, **k):
            raise OSError("unreachable")
        self.assertEqual(diagnose.tls_check("1.1.1.1", connect=boom)["result"], "connect_failed")

    def test_diagnose_source_has_no_tls_bypass_and_no_writes(self):
        with open(diagnose.__file__, encoding="utf-8") as f:
            src = f.read()
        for forbidden in ("CERT_NONE", "_create_unverified_context", "check_hostname = False",
                          "verify_mode", "set_dns", "restore_dns", "add_hosts_redirect",
                          "remove_hosts_redirect", "install_logon_failsafe", "netsh", "schtasks"):
            self.assertNotIn(forbidden, src)
        self.assertIn("ssl.create_default_context()", src)


if __name__ == "__main__":
    unittest.main()


class DiagnoseDispatch(unittest.TestCase):
    """`--diagnose` must be handled before the single-instance check,
    elevation and Qt: no window, no signal to a running KJ Des, no engine."""

    def _main(self, argv, run_effect=None):
        import sys as _sys
        import main
        from security import elevation, single_instance
        forbidden = mock.Mock(side_effect=AssertionError("must not be reached"))
        calls = {}

        def fake_run(path, summary=None):
            calls["path"] = path
            if isinstance(run_effect, Exception):
                raise run_effect
            if summary is not None:
                summary.update(run_effect or {"adapters": 1, "adapters_unreadable": 0, "doh_ok": True})
            return path
        with mock.patch.object(_sys, "argv", argv), \
             mock.patch("core.diagnose.run", fake_run), \
             mock.patch.object(single_instance, "signal_existing", forbidden), \
             mock.patch.object(single_instance, "acquire_mutex", forbidden), \
             mock.patch.object(elevation, "elevate", forbidden), \
             mock.patch.object(main, "_message_box", forbidden), \
             mock.patch("core.diagnostics.write_crash", return_value="x"):
            code = main.main()
        return code, calls, forbidden

    def test_diagnose_runs_before_anything_else(self):
        code, calls, forbidden = self._main(["KJDes.exe", "--diagnose"])
        self.assertEqual(code, 0)
        self.assertTrue(calls["path"].endswith("diagnostics.txt"))
        forbidden.assert_not_called()

    def test_problems_found_returns_2(self):
        code, _, _ = self._main(["KJDes.exe", "--diagnose"],
                                {"adapters": 2, "adapters_unreadable": 1, "doh_ok": True})
        self.assertEqual(code, 2)

    def test_failure_returns_1_without_any_window(self):
        code, _, forbidden = self._main(["KJDes.exe", "--diagnose"], OSError("disk full"))
        self.assertEqual(code, 1)
        forbidden.assert_not_called()

    def test_qt_is_not_imported_by_diagnostic_mode(self):
        import subprocess, sys as _sys, os
        code = ("import sys; sys.argv=['x','--diagnose']; sys.path.insert(0, r'%s');"
                "import core.diagnose as d; d.run=lambda p, s=None: (s.update(adapters=1,"
                "adapters_unreadable=0,doh_ok=True), p)[1];"
                "import main; rc=main.main(); "
                "print('QT_LOADED' if any(m.startswith('PySide6') for m in sys.modules) else 'NO_QT', rc)"
                % fakes.APP)
        out = subprocess.run([_sys.executable, "-c", code], capture_output=True, text=True,
                             timeout=120, env={**os.environ, "APPDATA": os.environ.get("TEMP", ".")})
        self.assertIn("NO_QT 0", out.stdout, out.stderr)

    def test_normal_startup_path_is_unchanged(self):
        import sys as _sys
        import main
        from security import single_instance
        with mock.patch.object(_sys, "argv", ["KJDes.exe"]), \
             mock.patch("core.diagnose.run", side_effect=AssertionError("diagnose ran")), \
             mock.patch.object(single_instance, "signal_existing", return_value=True) as sig:
            self.assertEqual(main.main(), 0)      # defers to the running instance
        sig.assert_called_once()

    def test_exit_code_rules(self):
        self.assertEqual(diagnose.exit_code({"adapters": 1, "adapters_unreadable": 0, "doh_ok": True}), 0)
        self.assertEqual(diagnose.exit_code({"adapters": 0, "adapters_unreadable": 0, "doh_ok": True}), 2)
        self.assertEqual(diagnose.exit_code({"adapters": 1, "adapters_unreadable": 0, "doh_ok": False}), 2)
