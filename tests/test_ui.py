"""
UI tests (offscreen Qt). Engine = FakeOps, so nothing on the machine changes.
"""
import os
import sys
import tempfile
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import fakes  # noqa: F401
from fakes import FakeOps, MemoryLog

try:
    from PySide6.QtCore import QCoreApplication, Qt
    from PySide6.QtWidgets import QApplication
except ImportError:  # pragma: no cover
    QApplication = None

from core.connection import State


class _Autostart:
    def __init__(self):
        self.enabled = False

    def is_startup_enabled(self):
        return self.enabled

    def enable_startup(self):
        self.enabled = True
        return True

    def disable_startup(self):
        self.enabled = False
        return True


def process(ms=50):
    end = time.time() + ms / 1000
    while time.time() < end:
        QCoreApplication.processEvents()
        time.sleep(0.005)


@unittest.skipIf(QApplication is None, "PySide6 not installed")
class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qapp = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        from services.settings import Settings
        from ui.app import KJDesApp
        fd, self.cfg = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.cfg)
        self.ops = FakeOps()
        self.log = MemoryLog()
        self.autostart = _Autostart()
        self.app = KJDesApp(self.qapp, ops=self.ops, log=self.log, source_dev=False,
                            settings=Settings(self.cfg), autostart=self.autostart)
        self.app.tray.icon.isVisible = lambda: True       # offscreen has no tray
        self.app.tray.notify = lambda *a: None
        self.app.start(show=True)
        self.wait_idle()

    def tearDown(self):
        self.app.engine.shutdown(timeout=5)
        self.app.window.hide()
        for path in (self.cfg, self.cfg + ".tmp"):
            if os.path.exists(path):
                os.remove(path)

    def wait_idle(self, timeout=5):
        end = time.time() + timeout
        while time.time() < end:
            process(20)
            w = self.app.engine._worker
            if (w is None or not w.is_alive()) and not self.app.engine.status.busy:
                process(30)
                return
        self.fail("engine did not become idle")

    # ---------------------------------------------------------------
    def test_startup_renders_real_disconnected_state(self):
        w = self.app.window
        self.assertTrue(w.isVisible())
        self.assertEqual((w.width(), w.height()), (520, 560))
        self.assertTrue(w.windowFlags() & Qt.FramelessWindowHint)
        self.assertEqual(w.status_lbl.text(), "غير متصل")
        self.assertEqual(w.card_hosts.value.text(), "0 / 5")
        self.assertEqual(w.card_duration.value.text(), "—")
        self.assertEqual(w.card_dns.value.text(), "تلقائي")
        self.assertEqual(w.ring.mode(), "off")
        self.assertEqual(w.action_btn.text(), "تفعيل الاتصال")
        img = w.grab().toImage()
        self.assertFalse(img.isNull())

    def test_arabic_is_rtl_and_switches_live(self):
        w = self.app.window
        self.assertEqual(self.qapp.layoutDirection(), Qt.RightToLeft)
        self.assertEqual(w.layoutDirection(), Qt.RightToLeft)
        self.assertEqual(w.header.layoutDirection(), Qt.LeftToRight)
        self.assertTrue(w.card_hosts.label.alignment() & Qt.AlignRight)
        w.languageRequested.emit("tr")
        process()
        self.assertEqual(self.qapp.layoutDirection(), Qt.LeftToRight)
        self.assertEqual(w.status_lbl.text(), "Bağlı değil")
        self.assertEqual(w.lang_btn.text(), "TR")
        self.assertEqual(self.app.tray.act_exit.text(), "Çıkış")
        w.languageRequested.emit("en")
        process()
        self.assertEqual(w.action_btn.text(), "Enable connection")
        self.assertEqual(self.app.settings.get("language"), "en")

    def test_connect_shows_connected_only_after_engine_confirms(self):
        w = self.app.window
        seen = []
        orig = w.apply_status
        w.apply_status = lambda st: (seen.append((st.state, w.status_lbl.text())), orig(st))
        w.action_btn.click()
        self.wait_idle()
        self.assertEqual(self.app.engine.status.state, State.CONNECTED)
        self.assertEqual(w.status_lbl.text(), "متصل")
        self.assertEqual(w.ring.mode(), "on")
        self.assertEqual(w.card_hosts.value.text(), "5 / 5")
        self.assertEqual(w.card_dns.value.text(), "1.1.1.1")
        self.assertEqual(w.action_btn.text(), "فصل الاتصال")
        self.assertRegex(w.card_duration.value.text(), r"^\d\d:\d\d:\d\d$")
        self.assertTrue(w._tick.isActive())
        self.assertIn("verify", self.ops.calls)

    def test_failed_connection_shows_error_and_retry(self):
        self.ops.fail["doh"] = True
        self.app.window.action_btn.click()
        self.wait_idle()
        w = self.app.window
        self.assertEqual(w.ring.mode(), "error")
        self.assertEqual(w.desc_lbl.property("error"), True)
        self.assertIn("DNS", w.desc_lbl.text())
        self.assertEqual(w.action_btn.text(), "إعادة المحاولة")
        self.assertNotEqual(w.status_lbl.text(), "متصل")

    def test_busy_state_disables_button(self):
        from core.connection import Status
        w = self.app.window
        w.apply_status(Status(state=State.CONNECTING, step="step_verify", total=5))
        self.assertFalse(w.action_btn.isEnabled())
        self.assertEqual(w.action_mode(), "none")
        self.assertTrue(w.ring.spinning())
        self.assertEqual(w.desc_lbl.text(), "جارٍ التحقق من الوصول إلى Discord…")

    def test_disconnect_from_ui(self):
        self.app.connect_engine(); self.wait_idle()
        self.app.window.action_btn.click(); self.wait_idle()
        self.assertEqual(self.app.engine.status.state, State.DISCONNECTED)
        self.assertEqual(self.ops.dns, self.ops.original_dns)
        self.assertFalse(self.app.window._tick.isActive())

    def test_close_hides_to_tray_and_keeps_connection(self):
        self.app.connect_engine(); self.wait_idle()
        self.app.window.close_btn.click()
        process()
        self.assertFalse(self.app.window.isVisible())
        self.assertEqual(self.app.engine.status.state, State.CONNECTED)
        self.assertEqual(self.ops.hosts_entries.__len__(), 5)
        self.app.tray.showRequested.emit()
        process()
        self.assertTrue(self.app.window.isVisible())

    def test_tray_reflects_state_and_toggles(self):
        tray = self.app.tray
        self.assertEqual(tray.toggle_action(), "connect")
        tray.act_toggle.trigger(); self.wait_idle()
        self.assertEqual(self.app.engine.status.state, State.CONNECTED)
        self.assertEqual(tray.act_status.text(), "متصل")
        self.assertIn("متصل", tray.icon.toolTip())
        self.assertEqual(tray.act_toggle.text(), "فصل الاتصال")
        tray.act_toggle.trigger(); self.wait_idle()
        self.assertEqual(self.app.engine.status.state, State.DISCONNECTED)

    def test_exit_restores_network_before_quit(self):
        quits = []
        self.qapp.quit = lambda: quits.append(1)
        try:
            self.app.connect_engine(); self.wait_idle()
            self.app.tray.exitRequested.emit()
            end = time.time() + 5
            while not quits and time.time() < end:
                process(20)
        finally:
            del self.qapp.quit
        self.assertEqual(quits, [1])
        self.assertEqual(self.ops.hosts_entries, [])
        self.assertEqual(self.ops.dns, self.ops.original_dns)
        self.assertFalse(self.ops.relay.running)

    def test_settings_restore_defaults_and_toggles(self):
        self.app.open_settings()
        dlg = self.app.settings_dlg
        self.assertTrue(dlg.isVisible())
        self.assertLessEqual(dlg.width(), 420)
        dlg.startup_cb.setChecked(True)
        self.assertTrue(self.autostart.enabled)
        dlg.tray_cb.setChecked(False)
        self.assertFalse(self.app.settings.get("close_to_tray"))
        self.app.connect_engine(); self.wait_idle()
        dlg.restore_btn.click(); self.wait_idle()
        self.assertEqual(self.app.engine.status.state, State.DISCONNECTED)
        self.assertEqual(dlg.feedback.text(), "تمت استعادة الإعدادات الأصلية.")

    def test_activity_and_about_dialogs(self):
        self.app.window.activityRequested.emit()
        process()
        self.assertTrue(self.app.activity.isVisible())
        self.assertIn("RECOVERY", self.app.activity.view.toPlainText())
        self.app.window.aboutRequested.emit()
        process()
        self.assertTrue(self.app.about.isVisible())

    def _about_texts(self):
        from PySide6.QtWidgets import QAbstractButton, QLabel
        about = self.app.about
        return [w.text() for w in about.findChildren(QLabel)] + \
               [w.text() for w in about.findChildren(QAbstractButton)] + \
               [w.toolTip() for w in about.findChildren(QAbstractButton)]

    def test_about_shows_kj_des_and_creator_only(self):
        about = self.app.about
        about.open_over(self.app.window)
        process()
        texts = " ".join(self._about_texts())
        from fakes import inherited_copyright_holder
        for forbidden in [f for f in ("DPort", inherited_copyright_holder()) if f]:
            self.assertNotIn(forbidden, texts)
        self.assertIn("Lucas (KJ)", texts)
        self.assertEqual(about.version_badge.text(), "v1.0.3")
        self.assertEqual(about.creator_role.text(), "مطوّر برمجيات · مصمّم · صانع أدوات")
        self.assertEqual(about.footer.text(), "صُنع بشغف بواسطة Lucas")
        self.assertEqual(len(about.features), 3)
        self.assertEqual(about.layoutDirection(), Qt.RightToLeft)
        self.assertTrue(about.creator_name.alignment() & Qt.AlignRight)
        self.assertLessEqual(about.width(), 460)

    def test_about_switches_language_live(self):
        about = self.app.about
        about.open_over(self.app.window)
        self.app.set_language("tr")
        process()
        self.assertEqual(about.layoutDirection(), Qt.LeftToRight)
        self.assertEqual(about.footer.text(), "Lucas tarafından tutkuyla yapıldı")
        self.assertEqual(about.features[1][0].title.text(), "Geri alınabilir")
        self.app.set_language("en")
        process()
        self.assertEqual(about.creator_role.text(), "Software Developer · Designer · Tool Creator")
        self.assertTrue(about.creator_name.alignment() & Qt.AlignLeft)

    def test_social_buttons_open_real_profiles(self):
        from unittest import mock
        from ui import about as about_mod
        opened = []
        with mock.patch.object(about_mod.QDesktopServices, "openUrl",
                               side_effect=lambda u: opened.append(u.toString()) or True):
            for link_id in ("instagram", "github"):
                self.app.about.social_buttons[link_id][0].click()
        self.assertEqual(opened, ["https://www.instagram.com/k_77.0/",
                                  "https://github.com/LUCASS7001"])
        self.assertIn("@k_77.0", self.app.about.social_buttons["instagram"][0].text())

    def test_discord_username_is_plain_text_and_copies(self):
        from unittest import mock
        from PySide6.QtGui import QGuiApplication
        from ui import about as about_mod
        about = self.app.about
        about.open_over(self.app.window)
        process()
        self.assertIn("@l_4", about.discord_btn.text())
        with mock.patch.object(about_mod.QDesktopServices, "openUrl") as opened:
            about.discord_btn.click()
            process()
        opened.assert_not_called()                     # no URL is ever opened
        self.assertEqual(QGuiApplication.clipboard().text(), "@l_4")

    def test_official_artwork_is_used_with_original_proportions(self):
        from PySide6.QtGui import QPixmap
        from ui import components
        path = components._artwork_file()
        self.assertTrue(path and path.endswith("artwork.png"))
        pm = QPixmap(path)
        self.assertEqual((pm.width(), pm.height()), (1198, 1313))
        drawn = []
        orig = components._paint_image_artwork
        components._paint_image_artwork = lambda p, pix, w, h: (drawn.append((pix.width(), pix.height())), orig(p, pix, w, h))
        try:
            self.app.window.surface._art_cache = None
            self.app.window.grab()
        finally:
            components._paint_image_artwork = orig
        self.assertEqual(drawn, [(1198, 1313)])

    def test_idle_window_runs_no_timers_or_animations(self):
        w = self.app.window
        process(500)
        self.assertFalse(w._tick.isActive())
        self.assertFalse(w.ring.spinning())


if __name__ == "__main__":
    unittest.main()
