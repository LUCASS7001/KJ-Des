"""
ui/window.py
The compact KJ Des popup window (≈520×560, frameless, rounded, purple border).

Every value shown comes from ConnectionManager.Status — nothing decorative is
hard-coded. "Connected" appears only when the engine reports State.CONNECTED,
which itself requires a verified TLS handshake through the relay.
"""
from __future__ import annotations

import time

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QPainter
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMenu, QToolButton,
                               QVBoxLayout, QWidget)

from core.app_info import APP_NAME, APP_VERSION
from core.connection import State, Status
from services.i18n import LANGUAGES
from ui import icons
from ui.components import (AMBER, MINT, MUTED, ROSE, ActionButton, DragArea, Dot,
                           InfoCard, StatusRing, Surface, pill_button, window_button)

WINDOW_SIZE = QSize(520, 560)


class LangButton(QToolButton):
    """Globe + language code + chevron pill (chevron painted after the text)."""

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        size = 16
        x = self.width() - size - 10
        y = (self.height() - size) / 2
        p.drawPixmap(QRectF(x, y, size, size), icons.pixmap("chevron", "#d9ccff", size),
                     QRectF(0, 0, size * 2, size * 2))


class LogoMark(QWidget):
    def __init__(self, parent=None, size: int = 40):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        icons.paint_logo(p, QRectF(self.rect()))


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


class MainWindow(QWidget):
    connectRequested = Signal()
    disconnectRequested = Signal()
    closeRequested = Signal()
    aboutRequested = Signal()
    settingsRequested = Signal()
    activityRequested = Signal()
    languageRequested = Signal(str)

    def __init__(self, i18n):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Window)
        self.i18n = i18n
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(icons.app_icon())
        self.setFixedSize(WINDOW_SIZE)
        self._status = Status()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.surface = Surface(self, artwork=True)
        root.addWidget(self.surface)

        lay = QVBoxLayout(self.surface)
        lay.setContentsMargins(26, 18, 22, 20)
        lay.setSpacing(0)

        # header -----------------------------------------------------
        self.header = DragArea(self.surface)
        self.header.setLayoutDirection(Qt.LeftToRight)     # matches the reference in every language
        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(10)
        hl.addWidget(LogoMark(self.header, 40))
        titles = QVBoxLayout()
        titles.setSpacing(0)
        self.title_lbl = QLabel(APP_NAME, self.header); self.title_lbl.setObjectName("Title")
        self.version_lbl = QLabel(self.header); self.version_lbl.setObjectName("Version")
        titles.addWidget(self.title_lbl)
        titles.addWidget(self.version_lbl)
        hl.addLayout(titles)
        hl.addStretch(1)
        self.lang_btn = LangButton(self.header)
        self.lang_btn.setObjectName("LangButton")
        self.lang_btn.setFixedHeight(36)
        self.lang_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.lang_btn.setIcon(icons.icon("globe", "#d9ccff", 18))
        self.lang_btn.setIconSize(QSize(18, 18))
        self.lang_btn.setPopupMode(QToolButton.InstantPopup)
        self.lang_btn.setCursor(Qt.PointingHandCursor)
        self.lang_menu = QMenu(self.lang_btn)
        group = QActionGroup(self.lang_menu)
        self.lang_actions = {}
        for code in LANGUAGES:
            act = QAction(self.lang_menu, checkable=True)
            act.triggered.connect(lambda _=False, c=code: self.languageRequested.emit(c))
            group.addAction(act)
            self.lang_menu.addAction(act)
            self.lang_actions[code] = act
        self.lang_btn.setMenu(self.lang_menu)
        hl.addWidget(self.lang_btn)
        hl.addSpacing(8)
        self.min_btn = window_button("minimize", self.header)
        self.min_btn.clicked.connect(self.showMinimized)
        self.close_btn = window_button("close", self.header, danger=True)
        self.close_btn.clicked.connect(self.closeRequested.emit)
        hl.addWidget(self.min_btn)
        hl.addWidget(self.close_btn)
        lay.addWidget(self.header)

        # status ring ------------------------------------------------
        lay.addSpacing(6)
        self.ring = StatusRing(self.surface, 150)
        lay.addWidget(self.ring, 0, Qt.AlignHCenter)
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_row.addStretch(1)
        self.dot = Dot(self.surface, 11)
        self.status_lbl = QLabel(self.surface); self.status_lbl.setObjectName("StatusText")
        status_row.addWidget(self.dot, 0, Qt.AlignVCenter)
        status_row.addWidget(self.status_lbl, 0, Qt.AlignVCenter)
        status_row.addStretch(1)
        lay.addLayout(status_row)
        lay.addSpacing(4)
        self.desc_lbl = QLabel(self.surface)
        self.desc_lbl.setObjectName("StatusDesc")
        self.desc_lbl.setAlignment(Qt.AlignCenter)
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setFixedHeight(38)
        lay.addWidget(self.desc_lbl)
        lay.addSpacing(14)

        # cards ------------------------------------------------------
        cards = QWidget(self.surface)
        cards.setLayoutDirection(Qt.LeftToRight)   # order as in the reference
        cl = QHBoxLayout(cards)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(12)
        self.card_duration = InfoCard("clock", cards)
        self.card_hosts = InfoCard("layers", cards)
        self.card_dns = InfoCard("globe", cards)
        for c in (self.card_duration, self.card_hosts, self.card_dns):
            cl.addWidget(c)
        lay.addWidget(cards)
        lay.addSpacing(20)

        # main action ------------------------------------------------
        self.action_btn = ActionButton(self.surface)
        self.action_btn.setFixedWidth(340)
        self.action_btn.clicked.connect(self._on_action)
        lay.addWidget(self.action_btn, 0, Qt.AlignHCenter)
        lay.addStretch(1)

        # bottom buttons ---------------------------------------------
        bottom_w = QWidget(self.surface)
        bottom_w.setLayoutDirection(Qt.LeftToRight)   # info · settings · activity, as in the reference
        bottom = QHBoxLayout(bottom_w)
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(14)
        bottom.addStretch(1)
        self.about_btn = pill_button("info", self.surface)
        self.settings_btn = pill_button("gear", self.surface)
        self.activity_btn = pill_button("activity", self.surface)
        self.about_btn.clicked.connect(self.aboutRequested.emit)
        self.settings_btn.clicked.connect(self.settingsRequested.emit)
        self.activity_btn.clicked.connect(self.activityRequested.emit)
        for b in (self.about_btn, self.settings_btn, self.activity_btn):
            bottom.addWidget(b)
        bottom.addStretch(1)
        lay.addWidget(bottom_w)

        # live duration: 1 s timer, only while connected AND visible
        self._tick = QTimer(self, interval=1000)
        self._tick.timeout.connect(self._update_duration)
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(180)
        self._fade.setEasingCurve(QEasingCurve.OutCubic)

        i18n.on_change(lambda _code: self.retranslate())
        self.retranslate()

    # ---------------------------------------------------------- i18n
    def retranslate(self) -> None:
        t = self.i18n.t
        rtl = self.i18n.rtl
        self.setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
        self.header.setLayoutDirection(Qt.LeftToRight)
        self.version_lbl.setText(t("version_fmt", version=APP_VERSION))
        self.lang_btn.setText(self.i18n.code.upper())
        self.lang_btn.setToolTip(t("tip_language"))
        for code, act in self.lang_actions.items():
            act.setText(f"{t('lang_' + code)}  ({code.upper()})")
            act.setChecked(code == self.i18n.code)
        self.min_btn.setToolTip(t("tip_minimize"))
        self.close_btn.setToolTip(t("tip_close"))
        self.about_btn.setToolTip(t("tip_about"))
        self.settings_btn.setToolTip(t("tip_settings"))
        self.activity_btn.setToolTip(t("tip_activity"))
        self.card_duration.label.setText(t("card_duration"))
        self.card_hosts.label.setText(t("card_hosts"))
        self.card_dns.label.setText(t("card_dns"))
        for c in (self.card_duration, self.card_hosts, self.card_dns):
            c.set_alignment(rtl)
        self.action_btn.setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
        self.apply_status(self._status)

    # -------------------------------------------------------- status
    def apply_status(self, st: Status) -> None:
        self._status = st
        t = self.i18n.t
        s = st.state
        error_desc = False
        if s == State.CONNECTED:
            ring, dot, title, desc = "on", MINT, t("status_connected"), t("desc_connected")
            variant, btn = "outline", t("btn_disconnect")
        elif s == State.CONNECTING:
            ring, dot, title = "busy", AMBER, t("status_connecting")
            desc = t(st.step) if st.step else ""
            variant, btn = "busy", t("btn_connecting")
        elif s == State.DISCONNECTING:
            ring, dot, title = "busy", AMBER, t("status_disconnecting")
            desc = t(st.step) if st.step else ""
            variant, btn = "busy", t("btn_disconnecting")
        elif s == State.ERROR:
            ring, dot, title = "error", ROSE, t("status_error")
            desc = t(st.error) if st.error else t("desc_restore_pending")
            error_desc = True
            if st.restore_pending:
                variant, btn = "error", t("btn_restore")
            else:
                variant, btn = "primary", t("btn_retry")
        else:
            ring, dot, title, desc = "off", MUTED, t("status_disconnected"), t("desc_disconnected")
            variant, btn = "primary", t("btn_connect")
        self.ring.set_mode(ring)
        self.dot.set_color(dot)
        self.status_lbl.setText(title)
        self.desc_lbl.setText(desc)
        if self.desc_lbl.property("error") != error_desc:
            self.desc_lbl.setProperty("error", error_desc)
            self.desc_lbl.style().unpolish(self.desc_lbl)
            self.desc_lbl.style().polish(self.desc_lbl)
        self.action_btn.setText(btn)
        self.action_btn.set_variant(variant)

        total = st.total or 0
        self.card_hosts.set_value(f"{st.routed} / {total}" if total else t("value_none"),
                                  muted=st.routed == 0)
        if st.dns == "auto":
            self.card_dns.set_value(t("dns_auto"))
        elif st.dns:
            self.card_dns.set_value(st.dns, accent=st.dns_secure)
        else:
            self.card_dns.set_value(t("value_none"), muted=True)
        self._update_duration()
        self._sync_timer()

    def action_mode(self) -> str:
        st = self._status
        if st.state == State.CONNECTED or (st.state == State.ERROR and st.restore_pending):
            return "disconnect"
        if st.busy:
            return "none"
        return "connect"

    def _on_action(self) -> None:
        mode = self.action_mode()
        if mode == "connect":
            self.connectRequested.emit()
        elif mode == "disconnect":
            self.disconnectRequested.emit()

    def _update_duration(self) -> None:
        st = self._status
        if st.state == State.CONNECTED and st.connected_since:
            self.card_duration.set_value(format_duration(time.time() - st.connected_since))
        else:
            self.card_duration.set_value(self.i18n.t("value_none"), muted=True)

    def _sync_timer(self) -> None:
        want = self.isVisible() and self._status.state == State.CONNECTED
        if want and not self._tick.isActive():
            self._tick.start()
        elif not want and self._tick.isActive():
            self._tick.stop()

    # ------------------------------------------------------- showing
    def present(self) -> None:
        if self.isMinimized():
            self.showNormal()
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
            self._fade.stop()
            self._fade.setStartValue(0.0)
            self._fade.setEndValue(1.0)
            self._fade.start()
        self.raise_()
        self.activateWindow()

    def showEvent(self, e):
        super().showEvent(e)
        self._update_duration()
        self._sync_timer()

    def hideEvent(self, e):
        super().hideEvent(e)
        self._sync_timer()

    def closeEvent(self, e):
        # Alt+F4 / taskbar close behave like the close button (never kills the
        # connection by accident); the controller decides tray vs. exit.
        e.ignore()
        self.closeRequested.emit()
