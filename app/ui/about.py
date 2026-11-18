"""
ui/about.py
The KJ Des About dialog: brand hero, version badge, short description,
three feature cards, creator card with social links and a minimal footer.

All text comes from app/locales/*.json; the creator name and social links come
from app/branding.json. Nothing here states performance, security or privacy
figures: the feature cards only describe what the app factually does.
"""
from __future__ import annotations

import os

from PySide6.QtCore import QRectF, QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPainter
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QVBoxLayout, QWidget)

from core.app_info import APP_NAME, APP_VERSION
from core.paths import app_dir, resource_path
from services.branding import Branding, load_branding
from ui import icons
from ui.components import LAVENDER
from ui.dialogs import PopupDialog

FEATURES = (
    ("route", "feat_route_title", "feat_route_desc"),
    ("restore", "feat_restore_title", "feat_restore_desc"),
    ("globe", "feat_lang_title", "feat_lang_desc"),
)


def notice_path() -> str | None:
    """Third-party notices / licenses document (bundled next to the app)."""
    for path in (resource_path("NOTICE.md"),
                 os.path.join(os.path.dirname(app_dir()), "NOTICE.md")):
        if os.path.exists(path):
            return path
    return None


def open_url(url: str) -> bool:
    return QDesktopServices.openUrl(QUrl(url))


class LogoHero(QWidget):
    """Large KJ Des mark with glow."""

    def __init__(self, parent=None, size: int = 92):
        super().__init__(parent)
        self.setFixedSize(size + 24, size + 24)
        self._s = size

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        m = (self.width() - self._s) / 2
        icons.paint_logo(p, QRectF(m, m, self._s, self._s), glow=True)


class Avatar(QWidget):
    """Round creator badge: gradient ring with the K mark."""

    def __init__(self, parent=None, size: int = 50):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, _e):
        from PySide6.QtGui import QColor, QLinearGradient, QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        ring = QLinearGradient(r.topLeft(), r.bottomRight())
        ring.setColorAt(0, QColor("#e9d5ff"))
        ring.setColorAt(1, QColor("#6d28d9"))
        p.setPen(QPen(ring, 2.2))
        p.setBrush(QColor("#140f24"))
        p.drawEllipse(r)
        m = r.width() * 0.26
        icons.paint_logo(p, r.adjusted(m, m, -m, -m))


class FeatureCard(QFrame):
    def __init__(self, icon_name: str, parent=None):
        super().__init__(parent)
        self.setObjectName("FeatureCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(112)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 12, 8, 10)
        lay.setSpacing(4)
        self.icon = QLabel(self)
        self.icon.setPixmap(icons.pixmap(icon_name, LAVENDER, 24))
        self.icon.setAlignment(Qt.AlignCenter)
        self.title = QLabel(self); self.title.setObjectName("FeatureTitle")
        self.desc = QLabel(self); self.desc.setObjectName("FeatureDesc")
        for w in (self.title, self.desc):
            w.setAlignment(Qt.AlignCenter)
            w.setWordWrap(True)
        lay.addWidget(self.icon)
        lay.addWidget(self.title)
        lay.addWidget(self.desc, 1)


class AboutDialog(PopupDialog):
    def __init__(self, i18n, parent=None, branding: Branding | None = None):
        super().__init__(i18n, "about_title", parent, QSize(440, 610),
                         artwork="dialog", show_title=False)
        self.branding = branding or load_branding()
        s = self.surface
        self.body.setSpacing(8)

        # hero ------------------------------------------------------
        self.logo = LogoHero(s, 88)
        self.body.addWidget(self.logo, 0, Qt.AlignHCenter)
        self.name_lbl = QLabel(APP_NAME, s); self.name_lbl.setObjectName("AboutTitle")
        self.name_lbl.setAlignment(Qt.AlignCenter)
        self.body.addWidget(self.name_lbl)
        badges = QHBoxLayout()
        badges.setSpacing(8)
        badges.addStretch(1)
        self.version_badge = QLabel(s); self.version_badge.setObjectName("Badge")
        self.tagline = QLabel(s); self.tagline.setObjectName("Tagline")
        badges.addWidget(self.version_badge)
        badges.addWidget(self.tagline)
        badges.addStretch(1)
        self.body.addLayout(badges)
        self.desc = QLabel(s); self.desc.setObjectName("Body")
        self.desc.setWordWrap(True)
        self.desc.setAlignment(Qt.AlignCenter)
        self.body.addWidget(self.desc)
        self.body.addSpacing(4)

        # features --------------------------------------------------
        row = QHBoxLayout()
        row.setSpacing(10)
        self.features = []
        for icon_name, title_key, desc_key in FEATURES:
            card = FeatureCard(icon_name, s)
            self.features.append((card, title_key, desc_key))
            row.addWidget(card)
        self.body.addLayout(row)
        self.body.addSpacing(4)

        # creator ---------------------------------------------------
        self.creator = QFrame(s); self.creator.setObjectName("CreatorCard")
        cl = QVBoxLayout(self.creator)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(10)
        who = QHBoxLayout()
        who.setSpacing(12)
        who.addWidget(Avatar(self.creator, 50))
        names = QVBoxLayout()
        names.setSpacing(1)
        self.creator_caption = QLabel(self.creator); self.creator_caption.setObjectName("Caption")
        self.creator_name = QLabel(self.branding.creator_name, self.creator)
        self.creator_name.setObjectName("CreatorName")
        self.creator_role = QLabel(self.creator); self.creator_role.setObjectName("Muted")
        self.creator_role.setWordWrap(True)
        for w in (self.creator_caption, self.creator_name, self.creator_role):
            names.addWidget(w)
        who.addLayout(names, 1)
        cl.addLayout(who)
        social = QHBoxLayout()
        social.setSpacing(10)
        self.social_buttons = {}
        for link in self.branding.links:
            # LRM keeps handles like "@k_77.0" in left-to-right order in Arabic
            btn = QPushButton("‎" + link.label, self.creator)
            btn.setObjectName("Social")
            btn.setIcon(icons.icon(link.id, "#ece6ff", 18))
            btn.setIconSize(QSize(18, 18))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setLayoutDirection(Qt.LeftToRight)       # handles are Latin text
            btn.clicked.connect(lambda _=False, u=link.url: open_url(u))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            social.addWidget(btn)
            self.social_buttons[link.id] = (btn, link)
        # Discord username: plain text (no verified profile URL). Clicking
        # copies the username to the clipboard; nothing is opened.
        self.discord_btn = None
        if self.branding.discord_username:
            self.discord_btn = QPushButton("‎" + self.branding.discord_username, self.creator)
            self.discord_btn.setObjectName("Social")
            self.discord_btn.setIcon(icons.icon("chat", "#ece6ff", 18))
            self.discord_btn.setIconSize(QSize(18, 18))
            self.discord_btn.setCursor(Qt.PointingHandCursor)
            self.discord_btn.setLayoutDirection(Qt.LeftToRight)
            self.discord_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.discord_btn.clicked.connect(self._copy_discord)
            social.addWidget(self.discord_btn)
        cl.addLayout(social)
        self.body.addWidget(self.creator)
        self.body.addStretch(1)

        # footer ----------------------------------------------------
        foot = QHBoxLayout()
        foot.setSpacing(6)
        foot.addStretch(1)
        heart = QLabel(s)
        heart.setPixmap(icons.pixmap("heart", "#c084fc", 14))
        self.footer = QLabel(s); self.footer.setObjectName("Footer")
        foot.addWidget(heart)
        foot.addWidget(self.footer)
        self.licenses_btn = None
        if notice_path():
            dot = QLabel("·", s); dot.setObjectName("Footer")
            self.licenses_btn = QPushButton(s); self.licenses_btn.setObjectName("Link")
            self.licenses_btn.setCursor(Qt.PointingHandCursor)
            self.licenses_btn.clicked.connect(
                lambda: open_url(QUrl.fromLocalFile(notice_path()).toString()))
            foot.addWidget(dot)
            foot.addWidget(self.licenses_btn)
        foot.addStretch(1)
        self.body.addLayout(foot)

    def retranslate(self):
        t = self.i18n.t
        self.version_badge.setText(t("version_fmt", version=APP_VERSION))
        self.version_badge.setToolTip(t("about_version", version=APP_VERSION))
        self.tagline.setText(t("about_tagline"))
        self.desc.setText(t("about_desc"))
        for card, title_key, desc_key in self.features:
            card.title.setText(t(title_key))
            card.desc.setText(t(desc_key))
        self.creator_caption.setText(t("creator_title"))
        self.creator_role.setText(t("creator_role"))
        # Absolute alignment: Qt would otherwise follow each label's own text
        # direction, putting the Latin name on the opposite side in Arabic.
        align = Qt.AlignAbsolute | Qt.AlignVCenter | (Qt.AlignRight if self.i18n.rtl else Qt.AlignLeft)
        for w in (self.creator_caption, self.creator_name, self.creator_role):
            w.setAlignment(align)
        for link_id, (btn, link) in self.social_buttons.items():
            btn.setToolTip(t("social_open", url=link.url))
            btn.setAccessibleName(t(f"social_{link_id}"))
        if self.discord_btn is not None:
            self.discord_btn.setText("‎" + self.branding.discord_username)
            self.discord_btn.setToolTip(t("social_discord_copy"))
            self.discord_btn.setAccessibleName(t("social_discord"))
        self.footer.setText(t("about_footer", name=self.branding.creator_short_name))
        if self.licenses_btn is not None:
            self.licenses_btn.setText(t("about_licenses"))

    def _copy_discord(self):
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QGuiApplication
        QGuiApplication.clipboard().setText(self.branding.discord_username)
        self.discord_btn.setText(self.i18n.t("activity_copied"))
        QTimer.singleShot(1400, lambda: self.discord_btn and self.discord_btn.setText(
            "‎" + self.branding.discord_username))
