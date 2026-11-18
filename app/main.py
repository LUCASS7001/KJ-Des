"""
main.py — KJ Des entry point.

Order of operations:
  1. `--cleanup-hosts` maintenance mode (used by the logon recovery task):
     removes ONLY the KJ Des marked hosts block, reconciles the task, no UI.
  2. If KJ Des is already running, bring it to the front and exit.
  3. Elevate with UAC if needed (network settings require administrator).
  4. Atomic single-instance mutex.
  5. Start the Qt application.

Developer flags (ignored by the packaged executable):
  --source-dev   run from source without an installed recovery target
  --no-elevate   open the UI without administrator rights (connection will
                 honestly fail with a permission error)
"""
import ctypes
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

_mutex_handle = None  # must stay alive for the whole process


def _frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _dev_flag(name: str) -> bool:
    return not _frozen() and name in sys.argv


def _message_box(title: str, text: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)
    except Exception:
        pass


def _localized(key: str, **kw) -> tuple:
    """Fatal messages also come from the locale files (fallback: English)."""
    try:
        from services.i18n import I18n
        from services.settings import Settings
        from core.paths import user_data_path
        lang = Settings(user_data_path("config.json")).get("language")
        i18n = I18n(lang)
        return i18n.t("fatal_title"), i18n.t(key, **kw)
    except Exception:
        return "KJ Des", key


def cleanup_hosts_mode() -> int:
    """Exit codes: 0 cleaned + task removed, 1 hosts not cleaned (task kept),
    2 cleaned but task removal failed, 3 unexpected error."""
    try:
        from core.discord_unblock import remove_hosts_redirect
        try:
            cleared = bool(remove_hosts_redirect())
        except Exception:
            return 1
        if not cleared:
            return 1
        from core.failsafe import reconcile_failsafe_task
        return 0 if reconcile_failsafe_task(True) else 2
    except Exception:
        return 3


def self_test(out_path: str) -> int:
    """Packaging smoke test: loads every bundled resource (locales, stylesheet,
    fonts, icons), builds the main window offscreen in all languages and saves
    a screenshot. Touches no network setting and starts no engine."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from core.connection import Status
    from services.i18n import I18n, LANGUAGES
    from ui import icons
    from ui.app import load_fonts, load_stylesheet
    from ui.window import MainWindow
    qapp = QApplication(sys.argv[:1])
    load_fonts()
    qapp.setStyleSheet(load_stylesheet())
    i18n = I18n("ar")
    window = MainWindow(i18n)
    window.apply_status(Status(total=5))
    window.setAttribute(Qt.WA_DontShowOnScreen)    # rendered, never displayed
    window.show()
    for code in LANGUAGES:
        i18n.set_language(code)
        assert i18n.t("btn_connect") != "btn_connect", code
    i18n.set_language("ar")
    qapp.processEvents()
    assert not icons.app_icon().isNull()
    ok = window.grab().save(out_path)
    from ui.about import AboutDialog, notice_path
    about = AboutDialog(i18n, window)
    assert about.branding.links, "branding.json not bundled"
    assert notice_path(), "NOTICE.md not bundled"
    about._retranslate_all()
    about.setAttribute(Qt.WA_DontShowOnScreen)
    about.show()
    qapp.processEvents()
    root, ext = os.path.splitext(out_path)
    ok = about.grab().save(f"{root}-about{ext or '.png'}") and ok
    return 0 if ok else 4


def main() -> int:
    global _mutex_handle
    if "--cleanup-hosts" in sys.argv:
        return cleanup_hosts_mode()
    if "--self-test" in sys.argv:
        idx = sys.argv.index("--self-test")
        target = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else "kjdes-self-test.png"
        return self_test(target)

    from security.single_instance import acquire_mutex, signal_existing
    from security.elevation import elevate, is_admin

    if signal_existing():
        return 0

    admin = is_admin()
    if not admin and not _dev_flag("--no-elevate"):
        if not elevate():
            _message_box(*_localized("fatal_elevation"))
            return 1
        return 0

    already, _mutex_handle = acquire_mutex()
    if already:
        signal_existing()
        return 0

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("KJDes.App")
    except Exception:
        pass

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    qapp = QApplication(sys.argv)
    qapp.setApplicationName("KJ Des")
    qapp.setOrganizationName("KJ Des")

    from core.diagnostics import create_log, session_header
    from core.system_ops import SystemOps
    from security.single_instance import IpcServer
    from services.settings import Settings
    from core.paths import user_data_path
    from ui.app import KJDesApp

    settings = Settings(user_data_path("config.json"))
    log = create_log(settings.get("log_enabled"))
    log.write(session_header(admin))
    controller = KJDesApp(qapp, ops=SystemOps(), log=log,
                          source_dev=_dev_flag("--source-dev"), settings=settings)

    from PySide6.QtCore import QObject, Signal

    class _Show(QObject):
        show = Signal()

    shower = _Show()
    shower.show.connect(controller.window.present, Qt.QueuedConnection)
    ipc = IpcServer(shower.show.emit)
    ipc.start()

    controller.start(show="--minimized" not in sys.argv)
    code = qapp.exec()
    ipc.close()
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        from core.diagnostics import write_crash
        last = write_crash()
        _message_box(*_localized("fatal_unexpected", error=last))
        sys.exit(1)
