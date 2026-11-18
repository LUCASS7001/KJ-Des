"""Localization completeness, settings validation, single instance, elevation."""
import json
import os
import re
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

import fakes  # noqa: F401

from services.i18n import LANGUAGES, I18n, load_locale
from services.settings import Settings
from security import elevation, single_instance as si

APP = fakes.APP


class Localization(unittest.TestCase):
    def test_all_locales_have_identical_non_empty_keys(self):
        tables = {c: load_locale(c) for c in LANGUAGES}
        keys = set(tables["en"])
        for code, table in tables.items():
            self.assertEqual(set(table), keys, code)
            self.assertTrue(all(v.strip() for v in table.values()), code)

    def test_placeholders_match_english(self):
        en = load_locale("en")
        for code in ("ar", "tr"):
            table = load_locale(code)
            for key, text in en.items():
                self.assertEqual(set(re.findall(r"{(\w+)}", text)),
                                 set(re.findall(r"{(\w+)}", table[key])), f"{code}:{key}")

    def test_language_specific_script(self):
        self.assertRegex(load_locale("ar")["status_connected"], "[؀-ۿ]")
        tr = "".join(load_locale("tr").values())
        for ch in "ğüşıöçİ":
            self.assertIn(ch, tr)

    def test_rtl_and_fallback(self):
        i = I18n("ar")
        self.assertTrue(i.rtl)
        i.set_language("en")
        self.assertFalse(i.rtl)
        self.assertEqual(i.t("does_not_exist"), "does_not_exist")
        i.set_language("xx")
        self.assertEqual(i.code, "ar")

    def test_change_notifies_listeners(self):
        seen = []
        i = I18n("en")
        i.on_change(seen.append)
        i.set_language("tr")
        i.set_language("tr")
        self.assertEqual(seen, ["tr"])

    def test_no_hardcoded_ui_text_in_ui_sources(self):
        """UI modules may only show text obtained from the locale files."""
        pattern = re.compile(r"""\.(setText|setToolTip|setWindowTitle|showMessage|addItem)\(\s*["'][^"']""")
        for name in ("window.py", "dialogs.py", "tray.py", "app.py", "components.py"):
            with open(os.path.join(APP, "ui", name), encoding="utf-8") as f:
                src = f.read()
            self.assertIsNone(pattern.search(src), f"literal UI string in ui/{name}")


class SettingsValidation(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)

    def tearDown(self):
        os.remove(self.path)

    def test_invalid_values_fall_back_to_defaults(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"language": "de", "close_to_tray": "yes"}, f)
        s = Settings(self.path)
        self.assertEqual(s.get("language"), "ar")
        self.assertIs(s.get("close_to_tray"), True)

    def test_set_rejects_bad_values(self):
        s = Settings(self.path)
        with self.assertRaises(ValueError):
            s.set("language", "de")
        with self.assertRaises(TypeError):
            s.set("log_enabled", 1)
        s.set("language", "tr")
        self.assertEqual(Settings(self.path).get("language"), "tr")

    def test_settings_file_never_holds_dns_backup(self):
        import inspect
        from services import settings as mod
        self.assertNotIn("dns", " ".join(mod.SCHEMA))
        self.assertNotIn("import secure_store", inspect.getsource(mod))


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class SingleInstance(unittest.TestCase):
    def test_show_request_round_trip(self):
        port = _free_port()
        hits = []
        server = si.IpcServer(lambda: hits.append(1), port=port)
        self.assertTrue(server.start())
        try:
            self.assertTrue(si.signal_existing(port))
            time.sleep(0.1)
            self.assertEqual(hits, [1])
            second = si.IpcServer(lambda: None, port=port)
            self.assertFalse(second.start(), "port must be exclusive")
        finally:
            server.close()
        self.assertFalse(si.signal_existing(port))

    def test_foreign_listener_is_not_treated_as_running_instance(self):
        port = _free_port()
        srv = socket.socket()
        srv.bind(("127.0.0.1", port))
        srv.listen(1)

        def junk():
            c, _ = srv.accept()
            c.sendall(b"HELLO\n")
            c.close()
        threading.Thread(target=junk, daemon=True).start()
        try:
            self.assertFalse(si.signal_existing(port))
        finally:
            srv.close()

    def test_request_with_trailing_bytes_is_rejected(self):
        a, b = socket.socketpair()
        try:
            a.sendall(si.IPC_REQUEST + b"X")
            a.shutdown(socket.SHUT_WR)
            self.assertFalse(si.serve_ipc_connection(b))
        finally:
            a.close(); b.close()

    @unittest.skipUnless(os.name == "nt", "Windows mutex")
    def test_named_mutex_detects_second_owner(self):
        name = f"KJDes_Test_{os.getpid()}"
        first, h1 = si.acquire_mutex(name)
        second, h2 = si.acquire_mutex(name)
        self.assertFalse(first)
        self.assertTrue(second)


class Elevation(unittest.TestCase):
    def test_declined_uac_reports_failure(self):
        fake = mock.Mock()
        fake.shell32.ShellExecuteW.return_value = 5        # SE_ERR_ACCESSDENIED
        with mock.patch.object(elevation.ctypes, "windll", fake, create=True):
            self.assertFalse(elevation.elevate())

    def test_successful_elevation(self):
        fake = mock.Mock()
        fake.shell32.ShellExecuteW.return_value = 42
        with mock.patch.object(elevation.ctypes, "windll", fake, create=True):
            self.assertTrue(elevation.elevate())
        args = fake.shell32.ShellExecuteW.call_args[0]
        self.assertEqual(args[1], "runas")

    def test_is_admin_handles_missing_api(self):
        with mock.patch.object(elevation.ctypes, "windll", None, create=True):
            self.assertFalse(elevation.is_admin())

    def test_main_refuses_to_run_unelevated_when_uac_declined(self):
        import main
        with mock.patch.object(si, "signal_existing", return_value=False), \
             mock.patch.object(elevation, "is_admin", return_value=False), \
             mock.patch.object(elevation, "elevate", return_value=False), \
             mock.patch.object(main, "_message_box") as box, \
             mock.patch.object(sys, "argv", ["main.py"]):
            self.assertEqual(main.main(), 1)
        box.assert_called_once()

    def test_main_defers_to_running_instance(self):
        import main
        with mock.patch.object(si, "signal_existing", return_value=True), \
             mock.patch.object(elevation, "elevate") as elev, \
             mock.patch.object(sys, "argv", ["main.py"]):
            self.assertEqual(main.main(), 0)
        elev.assert_not_called()


if __name__ == "__main__":
    unittest.main()
