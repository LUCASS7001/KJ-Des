"""
ui/app.py
Application controller: wires the engine (ConnectionManager), settings,
localization, main window, dialogs and tray together.

Lifecycle guarantees:
  * Closing the popup never terminates an active connection (it goes to tray).
  * "Exit" (tray) always restores the original network state before quitting.
  * Windows logoff/shutdown and aboutToQuit also run the restore.
"""
from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from core import startup_manager
from core.connection import ConnectionManager, State, Status
from core.paths import resource_path, user_data_path
from services.i18n import I18n
from services.settings import Settings
from ui import icons
from ui.about import AboutDialog
from ui.dialogs import ActivityDialog, SettingsDialog
from ui.tray import Tray
from ui.window import MainWindow

LATIN_FONTS = ["Inter", "Segoe UI"]
ARABIC_FONTS = ["Segoe UI", "Tahoma"]


class _Bridge(QObject):
    """Marshals engine callbacks (worker threads) onto the Qt main thread."""
    status = Signal(object)
    shutdownDone = Signal(bool)


def load_stylesheet() -> str:
    with open(resource_path("ui", "styles.qss"), encoding="utf-8") as f:
        return f.read()


def load_fonts() -> None:
    for name in ("Inter-Regular.ttf", "Inter-Bold.ttf"):
        QFontDatabase.addApplicationFont(resource_path("assets", "fonts", name))


class KJDesApp(QObject):
    def __init__(self, qapp: QApplication, *, ops, log, source_dev: bool = False,
                 settings: Settings | None = None, autostart=startup_manager):
        super().__init__()
        self.qapp = qapp
        self.log = log
        self.autostart = autostart
        self.settings = settings or Settings(user_data_path("config.json"))
        self.i18n = I18n(self.settings.get("language"))
        self._exiting = False
        self._shutdown_done = False
        self._restore_from_settings = False

        qapp.setQuitOnLastWindowClosed(False)
        qapp.setWindowIcon(icons.app_icon())
        load_fonts()
        qapp.setStyleSheet(load_stylesheet())
        self._apply_language_globals()
        self.i18n.on_change(lambda _c: self._apply_language_globals())

        self.bridge = _Bridge()
        self.bridge.status.connect(self._on_status, Qt.QueuedConnection)
        self.bridge.shutdownDone.connect(self._on_shutdown_done, Qt.QueuedConnection)
        self.engine = ConnectionManager(ops, log.write, source_dev=source_dev,
                                        on_change=self.bridge.status.emit)

        self.window = MainWindow(self.i18n)
        self.tray = Tray(self.i18n, self)
        self.about = AboutDialog(self.i18n, self.window)
        self.settings_dlg = SettingsDialog(self.i18n, self.window)
        self.activity = ActivityDialog(self.i18n, lambda: log.read_lines(300), self.window)

        w = self.window
        w.connectRequested.connect(self.connect_engine)
        w.disconnectRequested.connect(self.disconnect_engine)
        w.closeRequested.connect(self.close_window)
        w.languageRequested.connect(self.set_language)
        w.aboutRequested.connect(lambda: self.about.open_over(self.window))
        w.settingsRequested.connect(self.open_settings)
        w.activityRequested.connect(lambda: self.activity.open_over(self.window))
        self.tray.showRequested.connect(self.window.present)
        self.tray.connectRequested.connect(self.connect_engine)
        self.tray.disconnectRequested.connect(self.disconnect_engine)
        self.tray.exitRequested.connect(self.exit)
        sd = self.settings_dlg
        sd.languageChanged.connect(self.set_language)
        sd.closeToTrayChanged.connect(lambda v: self.settings.set("close_to_tray", v))
        sd.startupChanged.connect(self._set_startup)
        sd.loggingChanged.connect(self._set_logging)
        sd.restoreRequested.connect(self.restore_defaults)
        self.activity.clearRequested.connect(log.clear)

        qapp.aboutToQuit.connect(self._final_cleanup)
        qapp.commitDataRequest.connect(lambda _m: self._final_cleanup())

    # ------------------------------------------------------------ start
    def start(self, show: bool = True) -> None:
        self.tray.show()
        self._on_status(self.engine.status)
        if show:
            self.window.present()
        self.engine.start_recover()          # undo leftovers of a crashed session

    # --------------------------------------------------------- language
    def _apply_language_globals(self) -> None:
        rtl = self.i18n.rtl
        self.qapp.setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
        font = QFont()
        font.setFamilies(ARABIC_FONTS if rtl else LATIN_FONTS)
        font.setPointSizeF(10)
        font.setHintingPreference(QFont.PreferNoHinting)
        self.qapp.setFont(font)

    def set_language(self, code: str) -> None:
        self.i18n.set_language(code)
        try:
            self.settings.set("language", self.i18n.code)
        except Exception:
            pass

    # ----------------------------------------------------------- status
    def _on_status(self, st: Status) -> None:
        self.window.apply_status(st)
        self.tray.apply_status(st)
        busy = st.busy
        self.settings_dlg.set_restore_busy(busy)
        if self._restore_from_settings and not busy:
            self._restore_from_settings = False
            ok = st.state == State.DISCONNECTED
            self.settings_dlg.show_feedback("set_restore_done" if ok else "set_restore_failed",
                                            error=not ok)
        if self.activity.isVisible():
            self.activity.refresh()

    # ---------------------------------------------------------- actions
    def connect_engine(self) -> None:
        if not self._exiting:
            self.engine.start_connect()

    def disconnect_engine(self) -> None:
        if not self._exiting:
            self.engine.start_disconnect()

    def restore_defaults(self) -> None:
        if self.engine.status.busy or not self.engine.start_disconnect():
            self.settings_dlg.show_feedback("set_restore_busy", error=True)
            return
        self._restore_from_settings = True

    def open_settings(self) -> None:
        self.settings_dlg.load(language=self.i18n.code,
                               close_to_tray=self.settings.get("close_to_tray"),
                               startup=bool(self._safe(self.autostart.is_startup_enabled, False)),
                               logging=self.settings.get("log_enabled"))
        self.settings_dlg.set_restore_busy(self.engine.status.busy)
        self.settings_dlg.open_over(self.window)

    @staticmethod
    def _safe(fn, default):
        try:
            return fn()
        except Exception:
            return default

    def _set_startup(self, enabled: bool) -> None:
        ok = self._safe(self.autostart.enable_startup if enabled else self.autostart.disable_startup, False)
        if ok:
            self.settings.set("start_with_windows", enabled)
        self.log.write(f"SETTINGS | start with Windows={enabled} | ok={ok}")

    def _set_logging(self, enabled: bool) -> None:
        self.settings.set("log_enabled", enabled)
        self.log.enabled = enabled

    # ---------------------------------------------------- close / exit
    def close_window(self) -> None:
        keep_running = (self.settings.get("close_to_tray")
                        or self.engine.status.state != State.DISCONNECTED)
        if keep_running and self.tray.icon.isVisible():
            self.window.hide()
            for dlg in (self.about, self.settings_dlg, self.activity):
                dlg.hide()
            if not self.settings.get("tray_hint_shown"):
                self.tray.notify(self.i18n.t("tray_running_title"), self.i18n.t("tray_running_msg"))
                self.settings.set("tray_hint_shown", True)
        else:
            self.exit()

    def exit(self) -> None:
        """Explicit exit: restore everything, then quit (non-blocking UI)."""
        if self._exiting:
            return
        self._exiting = True
        self.window.desc_lbl.setText(self.i18n.t("exiting"))
        threading.Thread(target=lambda: self.bridge.shutdownDone.emit(self.engine.shutdown()),
                         daemon=True, name="KJDes-exit").start()

    def _on_shutdown_done(self, ok: bool) -> None:
        self._shutdown_done = True
        self.tray.hide()
        self.qapp.quit()

    def _final_cleanup(self) -> None:
        if not self._shutdown_done:
            self._shutdown_done = True
            self.engine.shutdown(timeout=30)
            self.tray.hide()
