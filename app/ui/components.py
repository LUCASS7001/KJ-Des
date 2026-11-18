"""
ui/components.py
Reusable KJ Des widgets. Everything is drawn with Qt (no screenshots, no web
views). Animations run only while something is actually changing, so an idle
window costs no CPU.
"""
from __future__ import annotations

import math
import os
import random

from PySide6.QtCore import (Property, QEasingCurve, QPointF, QRectF, QSize,
                            QVariantAnimation, Qt, Signal)
from PySide6.QtGui import (QBrush, QColor, QFontMetrics, QLinearGradient,
                           QPainter, QPainterPath, QPen, QPixmap,
                           QRadialGradient)
from PySide6.QtWidgets import (QAbstractButton, QFrame, QHBoxLayout, QLabel,
                               QSizePolicy, QToolButton, QVBoxLayout, QWidget)

from core.paths import resource_path
from ui import icons

# ── palette ────────────────────────────────────────────────────────────
BG_TOP = QColor("#100d1c")
BG_BOTTOM = QColor("#0a0812")
BORDER = QColor(139, 92, 246, 150)
PURPLE = "#9b5cff"
PURPLE_LIGHT = "#c4a1ff"
LAVENDER = "#b69cff"
TEXT = "#f4f1fb"
MUTED = "#8f88a8"
MINT = "#4ade80"
AMBER = "#fbbf24"
ROSE = "#fb7185"
RADIUS = 18


# ── window surface ─────────────────────────────────────────────────────
class Surface(QWidget):
    """Rounded dark surface with a thin purple border. Optionally draws the
    decorative artwork on the right side (cached; repainted only on resize)."""

    def __init__(self, parent=None, artwork=False):
        """artwork: False, True (main window style) or "dialog" (subtle)."""
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self._artwork = artwork
        self._art_cache: QPixmap | None = None
        self._art_size = QSize()

    def resizeEvent(self, event):
        self._art_cache = None
        super().resizeEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, RADIUS, RADIUS)
        grad = QLinearGradient(0, 0, 0, r.height())
        grad.setColorAt(0, BG_TOP)
        grad.setColorAt(1, BG_BOTTOM)
        p.fillPath(path, grad)
        if self._artwork:
            p.save()
            p.setClipPath(path)
            p.drawPixmap(0, 0, self._artwork_pixmap())
            p.restore()
        p.setPen(QPen(BORDER, 1.2))
        p.drawPath(path)

    def _artwork_pixmap(self) -> QPixmap:
        dpr = self.devicePixelRatioF()
        if self._art_cache is None or self._art_size != self.size():
            self._art_size = self.size()
            pm = QPixmap(int(self.width() * dpr), int(self.height() * dpr))
            pm.setDevicePixelRatio(dpr)
            pm.fill(Qt.transparent)
            painter = QPainter(pm)
            painter.setRenderHint(QPainter.Antialiasing)
            rect = QRectF(0, 0, self.width(), self.height())
            if self._artwork == "dialog":
                paint_dialog_artwork(painter, rect)
            else:
                paint_artwork(painter, rect)
            painter.end()
            self._art_cache = pm
        return self._art_cache


def _artwork_file() -> str | None:
    for name in ("artwork.png", "artwork.jpg", "artwork.webp"):
        path = resource_path("assets", name)
        if os.path.exists(path):
            return path
    return None


def paint_artwork(p: QPainter, rect: QRectF) -> None:
    """Right-side decoration. Uses assets/artwork.png when supplied (faded into
    the background), otherwise an original procedural anime-style scene:
    rim-lit silhouette, violet glow, brush strokes and drifting petals."""
    w, h = rect.width(), rect.height()
    glow = QRadialGradient(QPointF(w * 0.86, h * 0.42), w * 0.55)
    glow.setColorAt(0, QColor(124, 58, 237, 70))
    glow.setColorAt(1, QColor(124, 58, 237, 0))
    p.fillRect(rect, glow)

    art = _artwork_file()
    if art:
        pm = QPixmap(art)
        if not pm.isNull():
            _paint_image_artwork(p, pm, w, h)
            _paint_strokes(p, w, h)
            return

    # procedural silhouette (original art, drawn with paths): a figure in
    # three-quarter profile looking left, wind-swept hair, high-collar coat.
    p.save()
    p.translate(w * 0.70, h * 0.20)
    s = h / 600.0
    p.scale(s, s)
    head = QPainterPath()
    head.moveTo(60, 150)                                 # forehead
    head.cubicTo(52, 175, 50, 196, 44, 214)              # nose bridge
    head.lineTo(56, 222)                                 # nose tip
    head.cubicTo(58, 236, 62, 246, 70, 252)              # lips / chin
    head.cubicTo(84, 266, 104, 270, 118, 262)            # jaw
    head.lineTo(150, 236)
    head.lineTo(150, 120)
    head.closeSubpath()
    hair = QPainterPath()
    spikes = [(30, 120), (70, 60), (60, 18), (110, 40), (130, -10), (150, 36),
              (200, 0), (190, 50), (250, 40), (222, 86), (268, 110), (226, 124),
              (250, 170), (214, 160), (224, 214), (190, 186), (168, 240), (150, 196),
              (122, 210), (124, 168), (96, 190), (102, 150), (64, 176), (82, 134)]
    hair.moveTo(*spikes[0])
    prev = spikes[0]
    for x, y in spikes[1:] + spikes[:1]:
        mx, my = (prev[0] + x) / 2, (prev[1] + y) / 2
        hair.quadTo(mx + (y - prev[1]) * 0.12, my - (x - prev[0]) * 0.12, x, y)
        prev = (x, y)
    neck = QPainterPath()
    neck.moveTo(104, 250); neck.lineTo(170, 220); neck.lineTo(184, 300); neck.lineTo(110, 316)
    neck.closeSubpath()
    coat = QPainterPath()
    coat.moveTo(84, 300)
    coat.cubicTo(60, 318, 20, 330, -20, 372)
    coat.lineTo(-40, 520); coat.lineTo(320, 520); coat.lineTo(310, 330)
    coat.cubicTo(280, 290, 240, 270, 214, 252)
    coat.lineTo(190, 330); coat.lineTo(130, 350)
    coat.closeSubpath()
    figure = hair.united(head).united(neck).united(coat)
    fill = QLinearGradient(40, 0, 260, 520)
    fill.setColorAt(0, QColor(30, 23, 52, 230))
    fill.setColorAt(1, QColor(12, 10, 22, 240))
    p.setPen(Qt.NoPen)
    p.setBrush(fill)
    p.drawPath(figure)
    p.setPen(QPen(QColor(155, 92, 255, 95), 2.0))
    p.setBrush(Qt.NoBrush)
    p.drawPath(figure)
    fold = QPen(QColor(124, 58, 237, 70), 1.6)
    p.setPen(fold)
    p.drawLine(QPointF(130, 350), QPointF(100, 520))
    p.drawLine(QPointF(214, 252), QPointF(236, 520))
    # glowing eye
    eye = QRadialGradient(QPointF(92, 196), 30)
    eye.setColorAt(0, QColor(196, 161, 255, 210))
    eye.setColorAt(1, QColor(124, 58, 237, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(eye)
    p.drawEllipse(QPointF(92, 196), 30, 13)
    p.setPen(QPen(QColor(232, 218, 255, 230), 2.4, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(80, 198), QPointF(104, 192))
    p.restore()
    # darken the left edge of the figure so content stays readable
    fade = QLinearGradient(w * 0.52, 0, w * 0.82, 0)
    fade.setColorAt(0, QColor(13, 11, 23, 255))
    fade.setColorAt(1, QColor(13, 11, 23, 0))
    p.fillRect(QRectF(w * 0.52, 0, w * 0.30, h), fade)
    _paint_strokes(p, w, h)


# Where the subject's face sits inside the supplied artwork (fractions of the
# image) and where it should land in the window (fractions of the window).
# The image is only scaled uniformly (proportions preserved) and the parts
# outside the window are clipped, never stretched.
ART_FOCUS = (0.55, 0.36)
ART_TARGET = (0.80, 0.40)
ART_HEIGHT = 1.04           # image height relative to the window height
ART_OPACITY = 0.62


def _paint_image_artwork(p: QPainter, pm: QPixmap, w: float, h: float) -> None:
    img_h = h * ART_HEIGHT
    img_w = img_h * pm.width() / pm.height()
    x = w * ART_TARGET[0] - img_w * ART_FOCUS[0]
    y = h * ART_TARGET[1] - img_h * ART_FOCUS[1]
    area = QRectF(x, y, img_w, img_h)

    p.save()
    p.setOpacity(ART_OPACITY)
    p.drawPixmap(area, pm, QRectF(pm.rect()))
    p.restore()

    # 1) purple wash so the art takes the window's tint
    p.save()
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)
    p.fillRect(area, QColor(76, 29, 149, 38))
    p.restore()

    bg = QColor(BG_TOP)

    def shade(alpha: int) -> QColor:
        c = QColor(bg)
        c.setAlpha(alpha)
        return c

    # 2) left fade: hides the image edge and its grey smoke, keeps the
    #    status text and left cards on a clean dark background
    left = QLinearGradient(x, 0, w * 0.70, 0)
    left.setColorAt(0.00, shade(255))
    left.setColorAt(0.45, shade(235))
    left.setColorAt(0.80, shade(110))
    left.setColorAt(1.00, shade(0))
    p.fillRect(QRectF(0, 0, w * 0.70, h), left)

    # 3) top fade under the header, bottom fade under the cards and buttons
    top = QLinearGradient(0, 0, 0, h * 0.20)
    top.setColorAt(0, shade(230))
    top.setColorAt(1, shade(0))
    p.fillRect(QRectF(0, 0, w, h * 0.20), top)
    bottom = QLinearGradient(0, h * 0.55, 0, h)
    bottom.setColorAt(0.0, shade(0))
    bottom.setColorAt(0.45, shade(150))
    bottom.setColorAt(1.0, QColor(BG_BOTTOM.red(), BG_BOTTOM.green(), BG_BOTTOM.blue(), 235))
    p.fillRect(QRectF(0, h * 0.55, w, h * 0.45), bottom)

    # 4) soft dark halo behind the centred status ring / text
    halo = QRadialGradient(QPointF(w * 0.5, h * 0.36), w * 0.34)
    halo.setColorAt(0.0, shade(200))
    halo.setColorAt(1.0, shade(0))
    p.fillRect(QRectF(0, 0, w, h), halo)

    # 5) purple rim light from the right edge
    rim = QRadialGradient(QPointF(w * 1.02, h * 0.42), w * 0.42)
    rim.setColorAt(0.0, QColor(139, 92, 246, 60))
    rim.setColorAt(1.0, QColor(139, 92, 246, 0))
    p.fillRect(QRectF(0, 0, w, h), rim)


def paint_dialog_artwork(p: QPainter, rect: QRectF) -> None:
    """Very subtle variant for popups: the figure sits in the top-right corner
    behind the logo area, heavily veiled so text and cards stay clean."""
    art = _artwork_file()
    w, h = rect.width(), rect.height()
    if not art:
        return
    pm = QPixmap(art)
    if pm.isNull():
        return
    img_h = h * 0.62
    img_w = img_h * pm.width() / pm.height()     # proportions preserved
    area = QRectF(w - img_w * 0.82, -h * 0.04, img_w, img_h)
    p.save()
    p.setOpacity(0.34)
    p.drawPixmap(area, pm, QRectF(pm.rect()))
    p.restore()
    bg = QColor(BG_TOP)

    def shade(alpha):
        c = QColor(bg)
        c.setAlpha(alpha)
        return c

    left = QLinearGradient(area.left(), 0, area.left() + img_w * 0.55, 0)
    left.setColorAt(0, shade(255))
    left.setColorAt(1, shade(0))
    p.fillRect(QRectF(0, 0, area.left() + img_w * 0.55, h), left)
    down = QLinearGradient(0, img_h * 0.45, 0, img_h)
    down.setColorAt(0, shade(0))
    down.setColorAt(1, shade(255))
    p.fillRect(QRectF(0, img_h * 0.45, w, img_h * 0.55), down)
    rim = QRadialGradient(QPointF(w, h * 0.12), w * 0.5)
    rim.setColorAt(0, QColor(139, 92, 246, 55))
    rim.setColorAt(1, QColor(139, 92, 246, 0))
    p.fillRect(rect, rim)


def _paint_strokes(p: QPainter, w: float, h: float) -> None:
    p.save()
    p.setPen(Qt.NoPen)
    for i, (x0, y0, length, thick, alpha) in enumerate(
            ((0.82, 0.86, 0.30, 16, 150), (0.74, 0.95, 0.34, 10, 110), (0.93, 0.74, 0.18, 7, 90))):
        grad = QLinearGradient(w * x0, h * y0, w * (x0 + length), h * (y0 - length * 0.55))
        grad.setColorAt(0, QColor(124, 58, 237, 0))
        grad.setColorAt(0.5, QColor(139, 92, 246, alpha))
        grad.setColorAt(1, QColor(196, 161, 255, 0))
        path = QPainterPath()
        path.moveTo(w * x0, h * y0)
        path.lineTo(w * (x0 + length), h * (y0 - length * 0.55))
        path.lineTo(w * (x0 + length) - thick * 0.4, h * (y0 - length * 0.55) + thick)
        path.lineTo(w * x0 - thick, h * y0 + thick * 0.6)
        path.closeSubpath()
        p.setBrush(grad)
        p.drawPath(path)
    rnd = random.Random(7)                    # deterministic petals
    for _ in range(5):
        x = w * rnd.uniform(0.18, 0.95)
        y = h * rnd.uniform(0.25, 0.85)
        size = rnd.uniform(5, 10)
        p.save()
        p.translate(x, y)
        p.rotate(rnd.uniform(-60, 60))
        petal = QPainterPath()
        petal.moveTo(0, -size)
        petal.quadTo(size * 0.6, 0, 0, size * 0.7)
        petal.quadTo(-size * 0.6, 0, 0, -size)
        p.setBrush(QColor(167, 120, 255, rnd.randint(70, 140)))
        p.drawPath(petal)
        p.restore()
    p.restore()


# ── status ring ────────────────────────────────────────────────────────
class StatusRing(QWidget):
    """Glowing purple ring with the chat glyph and a state badge.
    mode: 'off' | 'busy' | 'on' | 'error'. The spinner animates only in 'busy'."""

    def __init__(self, parent=None, diameter: int = 150):
        super().__init__(parent)
        self._d = diameter
        self.setFixedSize(diameter + 36, diameter + 36)
        self._mode = "off"
        self._angle = 0.0
        self._level = 0.0          # 0 = dim, 1 = fully lit (animated)
        self._spin = QVariantAnimation(self, startValue=0.0, endValue=360.0, duration=1100,
                                       loopCount=-1)
        self._spin.valueChanged.connect(self._on_spin)
        self._fade = QVariantAnimation(self, duration=420, easingCurve=QEasingCurve.OutCubic)
        self._fade.valueChanged.connect(self._on_fade)

    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        target = 1.0 if mode in ("on", "busy") else 0.35
        self._fade.stop()
        self._fade.setStartValue(self._level)
        self._fade.setEndValue(target)
        self._fade.start()
        if mode == "busy":
            self._spin.start()
        else:
            self._spin.stop()
        self.update()

    def spinning(self) -> bool:
        return self._spin.state() == QVariantAnimation.Running

    def _on_spin(self, value):
        self._angle = float(value)
        self.update()

    def _on_fade(self, value):
        self._level = float(value)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        r = self._d / 2
        lvl = self._level
        # outer glow
        glow = QRadialGradient(c, r + 18)
        glow.setColorAt(0.70, QColor(139, 92, 246, int(110 * lvl)))
        glow.setColorAt(1.0, QColor(139, 92, 246, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(c, r + 18, r + 18)
        # inner disc
        disc = QRadialGradient(c, r)
        disc.setColorAt(0, QColor("#1b1530"))
        disc.setColorAt(1, QColor("#110e1d"))
        p.setBrush(disc)
        p.drawEllipse(c, r - 4, r - 4)
        # ring
        ring_rect = QRectF(c.x() - r + 4, c.y() - r + 4, 2 * r - 8, 2 * r - 8)
        base = QColor(155, 92, 255)
        base.setAlphaF(0.30 + 0.70 * lvl)
        grad = QLinearGradient(ring_rect.topLeft(), ring_rect.bottomRight())
        grad.setColorAt(0, QColor(196, 161, 255, base.alpha()))
        grad.setColorAt(1, base)
        pen = QPen(QBrush(grad), 7)
        if self._mode == "busy":
            p.setPen(QPen(QColor(155, 92, 255, 60), 7))
            p.drawEllipse(ring_rect)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawArc(ring_rect, int(-self._angle * 16), 110 * 16)
        else:
            p.setPen(pen)
            p.drawEllipse(ring_rect)
        # glyph
        glyph = icons.chat_glyph_path(c.x(), c.y() - 2, r * 0.92)
        p.setPen(Qt.NoPen)
        g = QColor("#ffffff") if self._mode == "on" else QColor(214, 206, 236)
        g.setAlphaF(0.55 + 0.45 * lvl)
        p.setBrush(g)
        p.drawPath(glyph)
        # badge
        badge = {"on": ("check", PURPLE_LIGHT, QColor(155, 92, 255)),
                 "error": ("alert", ROSE, QColor(251, 113, 133))}.get(self._mode)
        if badge:
            name, icolor, bcolor = badge
            bc = QPointF(c.x() + r * 0.66, c.y() + r * 0.66)
            br = 17
            p.setBrush(QColor("#151124"))
            p.setPen(QPen(bcolor, 2.6))
            p.drawEllipse(bc, br, br)
            p.drawPixmap(QRectF(bc.x() - 11, bc.y() - 11, 22, 22),
                         icons.pixmap(name, icolor, 22), QRectF(0, 0, 44, 44))


# ── status dot ─────────────────────────────────────────────────────────
class Dot(QWidget):
    def __init__(self, parent=None, size: int = 12):
        super().__init__(parent)
        self.setFixedSize(size + 6, size + 6)
        self._color = QColor(MUTED)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def color(self) -> str:
        return self._color.name()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        halo = QColor(self._color); halo.setAlpha(60)
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawEllipse(c, self.width() / 2, self.height() / 2)
        p.setBrush(self._color)
        p.drawEllipse(c, self.width() / 2 - 3, self.height() / 2 - 3)


# ── info card ──────────────────────────────────────────────────────────
class InfoCard(QFrame):
    def __init__(self, icon_name: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setFixedHeight(76)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 16, 10)
        lay.setSpacing(10)
        self.icon = QLabel(self)
        self.icon.setPixmap(icons.pixmap(icon_name, LAVENDER, 26))
        self.icon.setFixedSize(28, 28)
        col = QVBoxLayout()
        col.setSpacing(2)
        self.label = QLabel(self); self.label.setObjectName("CardLabel")
        self.value = QLabel(self); self.value.setObjectName("CardValue")
        col.addWidget(self.label)
        col.addWidget(self.value)
        lay.addWidget(self.icon, 0, Qt.AlignVCenter)
        lay.addLayout(col, 1)

    def set_alignment(self, rtl: bool) -> None:
        align = (Qt.AlignRight if rtl else Qt.AlignLeft) | Qt.AlignVCenter
        self.label.setAlignment(align)
        self.value.setAlignment(align)

    def set_value(self, text: str, *, accent: bool = False, muted: bool = False) -> None:
        self.value.setText(text)
        for prop, val in (("accent", accent), ("muted", muted)):
            if self.value.property(prop) != val:
                self.value.setProperty(prop, val)
                self.value.style().unpolish(self.value)
                self.value.style().polish(self.value)


# ── primary action button ──────────────────────────────────────────────
class ActionButton(QAbstractButton):
    """Large gradient button. variant: 'primary' | 'outline' | 'busy' | 'error'."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(54)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._variant = "primary"
        self._hover = 0.0
        self._angle = 0.0
        self._hover_anim = QVariantAnimation(self, duration=160)
        self._hover_anim.valueChanged.connect(self._set_hover)
        self._spin = QVariantAnimation(self, startValue=0.0, endValue=360.0, duration=900,
                                       loopCount=-1)
        self._spin.valueChanged.connect(self._set_angle)

    def variant(self) -> str:
        return self._variant

    def set_variant(self, variant: str) -> None:
        self._variant = variant
        busy = variant == "busy"
        self.setEnabled(not busy)
        self.setCursor(Qt.ArrowCursor if busy else Qt.PointingHandCursor)
        if busy:
            self._spin.start()
        else:
            self._spin.stop()
        self.update()

    def _set_hover(self, v):
        self._hover = float(v)
        self.update()

    def _set_angle(self, v):
        self._angle = float(v)
        self.update()

    def _animate_hover(self, target: float):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def enterEvent(self, e):
        self._animate_hover(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._animate_hover(0.0)
        super().leaveEvent(e)

    def sizeHint(self):
        return QSize(330, 54)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        rad = 18
        h = self._hover
        v = self._variant
        grad = QLinearGradient(r.topLeft(), r.topRight())
        if v == "primary":
            grad.setColorAt(0, QColor(124, 58, 237, int(215 + 40 * h)))
            grad.setColorAt(1, QColor(168, 85, 247, int(200 + 55 * h)))
            border = QColor("#c4a1ff")
        elif v == "error":
            grad.setColorAt(0, QColor(136, 40, 80, int(150 + 60 * h)))
            grad.setColorAt(1, QColor(76, 29, 149, int(90 + 50 * h)))
            border = QColor("#f472b6")
        else:  # outline / busy
            grad.setColorAt(0, QColor(109, 40, 217, int(120 + 60 * h)))
            grad.setColorAt(1, QColor(46, 22, 92, int(70 + 50 * h)))
            border = QColor("#a78bfa")
        p.setPen(QPen(border, 2))
        p.setBrush(grad)
        p.drawRoundedRect(r, rad, rad)

        text = self.text()
        font = self.font()
        font.setPointSizeF(12.5)
        font.setBold(True)
        p.setFont(font)
        fm = QFontMetrics(font)
        icon_size = 26
        gap = 12
        tw = fm.horizontalAdvance(text)
        total = icon_size + gap + tw
        x0 = r.center().x() - total / 2
        cy = r.center().y()
        rtl = self.layoutDirection() == Qt.RightToLeft
        icon_x = x0 + tw + gap if rtl else x0
        text_x = x0 if rtl else x0 + icon_size + gap
        icon_rect = QRectF(icon_x, cy - icon_size / 2, icon_size, icon_size)
        if v == "busy":
            p.setPen(QPen(QColor(255, 255, 255, 60), 2.6))
            p.drawEllipse(icon_rect.adjusted(3, 3, -3, -3))
            pen = QPen(QColor("#ffffff"), 2.6)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawArc(icon_rect.adjusted(3, 3, -3, -3), int(-self._angle * 16), 100 * 16)
        else:
            p.drawPixmap(icon_rect, icons.pixmap("power", "#ffffff", icon_size),
                         QRectF(0, 0, icon_size * 2, icon_size * 2))
        p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(text_x, r.top(), tw + 2, r.height()), Qt.AlignVCenter | Qt.AlignLeft, text)


# ── small icon buttons ─────────────────────────────────────────────────
def pill_button(icon_name: str, parent=None) -> QToolButton:
    btn = QToolButton(parent)
    btn.setObjectName("PillButton")
    btn.setIcon(icons.icon(icon_name, "#e9e2ff", 22))
    btn.setIconSize(QSize(22, 22))
    btn.setFixedSize(70, 38)
    btn.setCursor(Qt.PointingHandCursor)
    return btn


def window_button(icon_name: str, parent=None, danger: bool = False) -> QToolButton:
    btn = QToolButton(parent)
    btn.setObjectName("WinButton")
    btn.setProperty("danger", danger)
    btn.setIcon(icons.icon(icon_name, "#ece6ff", 20))
    btn.setIconSize(QSize(20, 20))
    btn.setFixedSize(34, 34)
    btn.setCursor(Qt.PointingHandCursor)
    return btn


class DragArea(QWidget):
    """Lets the user move a frameless window by dragging this area."""
    dragged = Signal()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemMove()
        super().mousePressEvent(e)


__all__ = [
    "Surface", "StatusRing", "Dot", "InfoCard", "ActionButton", "pill_button",
    "window_button", "DragArea", "paint_artwork", "paint_dialog_artwork", "MINT", "AMBER", "ROSE", "MUTED",
]
