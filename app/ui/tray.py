"""
ui/tray.py
System tray integration: status icon + tooltip, open, connect/disconnect, exit.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from core.connection import State, Status
from ui import icons
from ui.components import AMBER, MINT, ROSE

_ACCENT = {State.CONNECTED: MINT, State.CONNECTING: AMBER,
           State.DISCONNECTING: AMBER, State.ERROR: ROSE}
_STATUS_KEY = {State.CONNECTED: "status_connected", State.CONNECTING: "status_connecting",
               State.DISCONNECTING: "status_disconnecting", State.ERROR: "status_error",
               State.DISCONNECTED: "status_disconnected"}


class Tray(QObject):
    showRequested = Signal()
    connectRequested = Signal()
    disconnectRequested = Signal()
    exitRequested = Signal()

    def __init__(self, i18n, parent=None):
        super().__init__(parent)
        self.i18n = i18n
        self._status = Status()
        self._icons = {}
        self.icon = QSystemTrayIcon(self._icon_for(State.DISCONNECTED))
        self.menu = QMenu()
        self.act_status = QAction(self.menu); self.act_status.setEnabled(False)
        self.act_show = QAction(self.menu)
        self.act_toggle = QAction(self.menu)
        self.act_exit = QAction(self.menu)
        self.menu.addAction(self.act_status)
        self.menu.addSeparator()
        self.menu.addAction(self.act_show)
        self.menu.addAction(self.act_toggle)
        self.menu.addSeparator()
        self.menu.addAction(self.act_exit)
        self.act_show.triggered.connect(self.showRequested.emit)
        self.act_toggle.triggered.connect(self._toggle)
        self.act_exit.triggered.connect(self.exitRequested.emit)
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._activated)
        i18n.on_change(lambda _c: self.apply_status(self._status))
        self.apply_status(self._status)

    def _icon_for(self, state):
        accent = _ACCENT.get(state)
        if accent not in self._icons:
            self._icons[accent] = icons.app_icon(accent)
        return self._icons[accent]

    def show(self):
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.icon.show()

    def hide(self):
        self.icon.hide()

    def _activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.showRequested.emit()

    def toggle_action(self) -> str:
        s = self._status
        if s.state == State.CONNECTED or (s.state == State.ERROR and s.restore_pending):
            return "disconnect"
        return "none" if s.busy else "connect"

    def _toggle(self):
        mode = self.toggle_action()
        if mode == "connect":
            self.connectRequested.emit()
        elif mode == "disconnect":
            self.disconnectRequested.emit()

    def apply_status(self, st: Status):
        self._status = st
        t = self.i18n.t
        status_text = t(_STATUS_KEY[st.state])
        self.icon.setIcon(self._icon_for(st.state))
        self.icon.setToolTip(t("tray_tooltip", status=status_text))
        self.act_status.setText(status_text)
        self.act_show.setText(t("tray_show"))
        mode = self.toggle_action()
        self.act_toggle.setText(t("tray_disconnect") if mode == "disconnect" else t("tray_connect"))
        self.act_toggle.setEnabled(mode != "none")
        self.act_exit.setText(t("tray_exit"))

    def notify(self, title: str, message: str):
        if self.icon.isVisible() and QSystemTrayIcon.supportsMessages():
            self.icon.showMessage(title, message, self._icon_for(self._status.state), 4000)
