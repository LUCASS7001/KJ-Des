"""
ui/dialogs.py
Small popup dialogs (About / Settings / Activity) in the same visual style.
They stay compact (≈400 px wide) and open centered over the main window.
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFrame,
                               QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
                               QVBoxLayout, QWidget)

from services.i18n import LANGUAGES
from ui import icons
from ui.components import DragArea, Surface, window_button


class PopupDialog(QDialog):
    def __init__(self, i18n, title_key: str, parent=None, size=QSize(400, 440),
                 artwork=False, show_title: bool = True):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.i18n = i18n
        self._title_key = title_key
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(size)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.surface = Surface(self, artwork=artwork)
        outer.addWidget(self.surface)
        self.body = QVBoxLayout(self.surface)
        self.body.setContentsMargins(22, 16, 18, 20)
        self.body.setSpacing(10)
        head = DragArea(self.surface)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        self.title_lbl = QLabel(head); self.title_lbl.setObjectName("DialogTitle")
        hl.addWidget(self.title_lbl)
        hl.addStretch(1)
        self.close_btn = window_button("close", head, danger=True)
        self.close_btn.clicked.connect(self.reject)
        hl.addWidget(self.close_btn)
        self.body.addWidget(head)
        if show_title:
            sep = QFrame(self.surface); sep.setObjectName("Separator")
            self.body.addWidget(sep)
        else:
            self.title_lbl.hide()
        i18n.on_change(lambda _c: self._retranslate_all())

    def _retranslate_all(self):
        self.setLayoutDirection(Qt.RightToLeft if self.i18n.rtl else Qt.LeftToRight)
        self.title_lbl.setText(self.i18n.t(self._title_key))
        self.setWindowTitle(self.i18n.t(self._title_key))
        self.close_btn.setToolTip(self.i18n.t("btn_close"))
        self.retranslate()

    def retranslate(self):
        pass

    def open_over(self, anchor: QWidget | None):
        self._retranslate_all()
        if anchor is not None and anchor.isVisible():
            g = anchor.frameGeometry()
            x = g.center().x() - self.width() // 2
            y = g.center().y() - self.height() // 2
            screen = anchor.screen()
            if screen is not None:                    # keep fully on screen
                a = screen.availableGeometry()
                x = max(a.left(), min(x, a.right() - self.width()))
                y = max(a.top(), min(y, a.bottom() - self.height()))
            self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()


def _label(name: str, parent, wrap=True) -> QLabel:
    lbl = QLabel(parent)
    lbl.setObjectName(name)
    lbl.setWordWrap(wrap)
    return lbl


class SettingsDialog(PopupDialog):
    languageChanged = Signal(str)
    closeToTrayChanged = Signal(bool)
    startupChanged = Signal(bool)
    loggingChanged = Signal(bool)
    restoreRequested = Signal()

    def __init__(self, i18n, parent=None):
        super().__init__(i18n, "settings_title", parent, QSize(410, 460))
        s = self.surface
        row = QHBoxLayout()
        self.lang_lbl = _label("Body", s, False)
        self.lang_combo = QComboBox(s)
        for code in LANGUAGES:
            self.lang_combo.addItem("", code)
        self.lang_combo.activated.connect(
            lambda i: self.languageChanged.emit(self.lang_combo.itemData(i)))
        row.addWidget(self.lang_lbl)
        row.addStretch(1)
        row.addWidget(self.lang_combo)
        self.body.addLayout(row)
        self.tray_cb = QCheckBox(s)
        self.startup_cb = QCheckBox(s)
        self.log_cb = QCheckBox(s)
        self.tray_cb.toggled.connect(self.closeToTrayChanged.emit)
        self.startup_cb.toggled.connect(self.startupChanged.emit)
        self.log_cb.toggled.connect(self.loggingChanged.emit)
        for cb in (self.tray_cb, self.startup_cb, self.log_cb):
            cb.setCursor(Qt.PointingHandCursor)
            self.body.addWidget(cb)
        sep = QFrame(s); sep.setObjectName("Separator")
        self.body.addSpacing(6)
        self.body.addWidget(sep)
        self.restore_title = _label("SectionTitle", s)
        self.restore_desc = _label("Muted", s)
        self.restore_btn = QPushButton(s)
        self.restore_btn.setObjectName("Danger")
        self.restore_btn.setIcon(icons.icon("shield", "#ffffff", 18))
        self.restore_btn.setCursor(Qt.PointingHandCursor)
        self.restore_btn.clicked.connect(self.restoreRequested.emit)
        self.feedback = _label("Feedback", s)
        self.body.addWidget(self.restore_title)
        self.body.addWidget(self.restore_desc)
        self.body.addWidget(self.restore_btn)
        self.body.addWidget(self.feedback)
        self.body.addStretch(1)

    def load(self, *, language: str, close_to_tray: bool, startup: bool, logging: bool):
        for w, v in ((self.tray_cb, close_to_tray), (self.startup_cb, startup), (self.log_cb, logging)):
            w.blockSignals(True); w.setChecked(v); w.blockSignals(False)
        idx = self.lang_combo.findData(language)
        self.lang_combo.setCurrentIndex(max(0, idx))
        self.feedback.clear()

    def set_restore_busy(self, busy: bool):
        self.restore_btn.setEnabled(not busy)

    def show_feedback(self, key: str, error: bool = False):
        self.feedback.setText(self.i18n.t(key))
        self.feedback.setProperty("error", error)
        self.feedback.style().unpolish(self.feedback)
        self.feedback.style().polish(self.feedback)

    def retranslate(self):
        t = self.i18n.t
        self.lang_lbl.setText(t("set_language"))
        for i in range(self.lang_combo.count()):
            self.lang_combo.setItemText(i, t("lang_" + self.lang_combo.itemData(i)))
        self.tray_cb.setText(t("set_close_to_tray"))
        self.startup_cb.setText(t("set_startup"))
        self.log_cb.setText(t("set_logging"))
        self.restore_title.setText(t("set_restore_title"))
        self.restore_desc.setText(t("set_restore_desc"))
        self.restore_btn.setText(t("set_restore_btn"))


class ActivityDialog(PopupDialog):
    clearRequested = Signal()

    def __init__(self, i18n, read_lines, parent=None):
        super().__init__(i18n, "activity_title", parent, QSize(470, 470))
        self._read = read_lines
        s = self.surface
        self.view = QPlainTextEdit(s)
        self.view.setObjectName("Log")
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.view.setLayoutDirection(Qt.LeftToRight)    # log lines are technical, LTR
        self.body.addWidget(self.view, 1)
        row = QHBoxLayout()
        self.copy_btn = QPushButton(s); self.copy_btn.setObjectName("Secondary")
        self.copy_btn.setIcon(icons.icon("copy", "#e9e2ff", 16))
        self.clear_btn = QPushButton(s); self.clear_btn.setObjectName("Secondary")
        self.clear_btn.setIcon(icons.icon("trash", "#e9e2ff", 16))
        self.copy_btn.clicked.connect(self._copy)
        self.clear_btn.clicked.connect(self._clear)
        row.addWidget(self.copy_btn)
        row.addWidget(self.clear_btn)
        row.addStretch(1)
        self.body.addLayout(row)

    def refresh(self):
        lines = self._read()
        text = "".join(lines).rstrip()
        self.view.setPlainText(text or self.i18n.t("activity_empty"))
        bar = self.view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _copy(self):
        QGuiApplication.clipboard().setText(self.view.toPlainText())
        self.copy_btn.setText(self.i18n.t("activity_copied"))
        QTimer.singleShot(1400, lambda: self.copy_btn.setText(self.i18n.t("activity_copy")))

    def _clear(self):
        self.clearRequested.emit()
        self.refresh()

    def retranslate(self):
        self.copy_btn.setText(self.i18n.t("activity_copy"))
        self.clear_btn.setText(self.i18n.t("activity_clear"))
        self.refresh()
