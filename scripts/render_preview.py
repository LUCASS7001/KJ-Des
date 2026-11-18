"""
scripts/render_preview.py
Renders the KJ Des window to PNG files (docs/screenshots) using the in-memory
FakeOps, so no real network setting is touched. Used for design review.

    python scripts/render_preview.py
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from fakes import FakeOps, MemoryLog  # noqa: E402
from core.connection import State  # noqa: E402
from services.settings import Settings  # noqa: E402
from ui.app import KJDesApp  # noqa: E402


class _NoAutostart:
    is_startup_enabled = staticmethod(lambda: False)
    enable_startup = disable_startup = staticmethod(lambda: True)


def pump(ms=150):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def main():
    out = os.path.join(ROOT, "docs", "screenshots")
    os.makedirs(out, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    tmp = os.path.join(out, "_preview_config.json")
    ctl = KJDesApp(app, ops=FakeOps(), log=MemoryLog(), source_dev=True,
                   settings=Settings(tmp), autostart=_NoAutostart())
    ctl.window.show()
    for lang in ("ar", "tr", "en"):
        ctl.set_language(lang)
        ctl.engine.recover_on_startup()
        pump()
        ctl.window.grab().save(os.path.join(out, f"{lang}-disconnected.png"))
        ctl.engine.connect()
        st = ctl.engine.status
        assert st.state == State.CONNECTED, st
        ctl.engine._set(connected_since=time.time() - 13189)   # preview only: show a long session
        pump()
        ctl.window.grab().save(os.path.join(out, f"{lang}-connected.png"))
        ctl.engine.disconnect()
        ctl.engine._ops.fail["doh"] = True
        ctl.engine.connect()
        ctl.engine._ops.fail.clear()
        pump()
        ctl.window.grab().save(os.path.join(out, f"{lang}-error.png"))
        ctl.about.open_over(ctl.window)
        pump()
        ctl.about.grab().save(os.path.join(out, f"{lang}-about.png"))
        ctl.about.hide()
    ctl.engine.shutdown(timeout=5)
    os.remove(tmp)
    print("saved to", out)


if __name__ == "__main__":
    main()
