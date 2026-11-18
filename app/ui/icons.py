"""
ui/icons.py
Vector icons drawn with QPainter (crisp at any DPI, no image files, no
third-party icon fonts). Every icon is drawn in a 24x24 design grid.
"""
from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QIcon, QLinearGradient, QPainter, QRadialGradient,
                           QPainterPath, QPen, QPixmap)


def _pen(color: QColor, width: float = 1.8) -> QPen:
    pen = QPen(color, width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _draw(p: QPainter, name: str, color: QColor) -> None:
    p.setPen(_pen(color))
    p.setBrush(Qt.NoBrush)
    if name == "clock":
        p.drawEllipse(QPointF(12, 12), 9, 9)
        p.drawPolyline([QPointF(12, 7), QPointF(12, 12), QPointF(15.5, 14)])
    elif name == "layers":
        top = QPainterPath()
        top.moveTo(12, 3.5); top.lineTo(21, 8); top.lineTo(12, 12.5); top.lineTo(3, 8); top.closeSubpath()
        p.drawPath(top)
        p.drawPolyline([QPointF(3, 12), QPointF(12, 16.5), QPointF(21, 12)])
        p.drawPolyline([QPointF(3, 16), QPointF(12, 20.5), QPointF(21, 16)])
    elif name == "globe":
        p.drawEllipse(QPointF(12, 12), 9, 9)
        p.drawEllipse(QRectF(8, 3, 8, 18))
        p.drawLine(QPointF(3, 12), QPointF(21, 12))
        p.drawLine(QPointF(4.5, 7.5), QPointF(19.5, 7.5))
        p.drawLine(QPointF(4.5, 16.5), QPointF(19.5, 16.5))
    elif name == "power":
        p.drawArc(QRectF(4.5, 5, 15, 15), 120 * 16, 300 * 16)
        p.drawLine(QPointF(12, 3), QPointF(12, 11))
    elif name == "info":
        p.drawEllipse(QPointF(12, 12), 9, 9)
        p.drawLine(QPointF(12, 11), QPointF(12, 16.5))
        p.setBrush(color); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(12, 7.8), 1.2, 1.2)
    elif name == "gear":
        p.drawEllipse(QPointF(12, 12), 3, 3)
        path = QPainterPath()
        import math
        teeth = 8
        for i in range(teeth * 2):
            r = 9 if i % 2 == 0 else 7
            for k in (-0.18, 0.18):
                a = (i + 0.5 + k) * math.pi / teeth
                pt = QPointF(12 + r * math.cos(a), 12 + r * math.sin(a))
                if path.elementCount() == 0:
                    path.moveTo(pt)
                else:
                    path.lineTo(pt)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "activity":
        p.drawPolyline([QPointF(2.5, 12), QPointF(7, 12), QPointF(9.5, 5),
                        QPointF(14, 19), QPointF(16.5, 12), QPointF(21.5, 12)])
    elif name == "minimize":
        p.drawLine(QPointF(6, 12), QPointF(18, 12))
    elif name == "close":
        p.drawLine(QPointF(6.5, 6.5), QPointF(17.5, 17.5))
        p.drawLine(QPointF(17.5, 6.5), QPointF(6.5, 17.5))
    elif name == "chevron":
        p.drawPolyline([QPointF(7, 10), QPointF(12, 15), QPointF(17, 10)])
    elif name == "check":
        p.setPen(_pen(color, 2.4))
        p.drawPolyline([QPointF(6, 12.5), QPointF(10.3, 16.5), QPointF(18, 8)])
    elif name == "alert":
        p.setPen(_pen(color, 2.4))
        p.drawLine(QPointF(12, 6), QPointF(12, 13.5))
        p.setBrush(color); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(12, 17.8), 1.5, 1.5)
    elif name == "copy":
        p.drawRoundedRect(QRectF(8, 8, 12, 12), 2.5, 2.5)
        p.drawPolyline([QPointF(16, 8), QPointF(16, 4.5), QPointF(4, 4.5), QPointF(4, 16), QPointF(8, 16)])
    elif name == "trash":
        p.drawLine(QPointF(4, 6.5), QPointF(20, 6.5))
        p.drawPolyline([QPointF(9, 6.5), QPointF(9.5, 3.5), QPointF(14.5, 3.5), QPointF(15, 6.5)])
        p.drawPolyline([QPointF(6, 6.5), QPointF(7, 20.5), QPointF(17, 20.5), QPointF(18, 6.5)])
    elif name == "shield":
        path = QPainterPath()
        path.moveTo(12, 3); path.lineTo(20, 6); path.lineTo(19, 13)
        path.cubicTo(18, 17, 15, 19.5, 12, 21); path.cubicTo(9, 19.5, 6, 17, 5, 13)
        path.lineTo(4, 6); path.closeSubpath()
        p.drawPath(path)
    elif name == "instagram":
        p.drawRoundedRect(QRectF(3.5, 3.5, 17, 17), 5, 5)
        p.drawEllipse(QPointF(12, 12), 4, 4)
        p.setBrush(color); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(16.8, 7.2), 1.1, 1.1)
    elif name == "github":
        # simplified cat-head mark (link icon), filled
        head = QPainterPath()
        head.moveTo(5.2, 10.2)
        head.lineTo(5.0, 4.6); head.lineTo(8.6, 6.6)
        head.cubicTo(10.8, 5.9, 13.2, 5.9, 15.4, 6.6)
        head.lineTo(19.0, 4.6); head.lineTo(18.8, 10.2)
        head.cubicTo(20.2, 12.0, 20.0, 15.4, 17.6, 17.0)
        head.cubicTo(16.2, 17.9, 14.8, 18.1, 14.4, 18.2)
        head.lineTo(14.4, 21.4); head.lineTo(9.6, 21.4); head.lineTo(9.6, 18.2)
        head.cubicTo(9.2, 18.1, 7.8, 17.9, 6.4, 17.0)
        head.cubicTo(4.0, 15.4, 3.8, 12.0, 5.2, 10.2)
        head.closeSubpath()
        p.setPen(Qt.NoPen); p.setBrush(color)
        p.drawPath(head)
        tail = QPen(color, 1.6); tail.setCapStyle(Qt.RoundCap)
        p.setPen(tail); p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(2.6, 15.4, 7.0, 6.0), 180 * 16, 120 * 16)
    elif name == "route":
        p.drawEllipse(QPointF(6, 18), 2.4, 2.4)
        p.drawEllipse(QPointF(18, 6), 2.4, 2.4)
        path = QPainterPath()
        path.moveTo(8.4, 18); path.lineTo(14, 18)
        path.cubicTo(17.5, 18, 17.5, 12, 14, 12); path.lineTo(10, 12)
        path.cubicTo(6.5, 12, 6.5, 6, 10, 6); path.lineTo(15.6, 6)
        p.drawPath(path)
    elif name == "restore":
        p.drawArc(QRectF(4, 4, 16, 16), 100 * 16, 290 * 16)
        p.drawPolyline([QPointF(4.2, 4.6), QPointF(4.6, 9.4), QPointF(9.4, 9.0)])
        p.drawPolyline([QPointF(12, 8), QPointF(12, 12), QPointF(14.8, 13.8)])
    elif name == "chat":
        bubble = QPainterPath()
        bubble.addRoundedRect(QRectF(3.5, 4.5, 17, 12.5), 4, 4)
        tail = QPainterPath()
        tail.moveTo(7.5, 16.5); tail.lineTo(6.5, 20.5); tail.lineTo(11.5, 16.5)
        p.drawPath(bubble.united(tail))
        p.setBrush(color); p.setPen(Qt.NoPen)
        for x in (8.5, 12, 15.5):
            p.drawEllipse(QPointF(x, 10.8), 1.1, 1.1)
    elif name == "heart":
        path = QPainterPath()
        path.moveTo(12, 20)
        path.cubicTo(4, 14.5, 2.5, 10, 4.5, 7)
        path.cubicTo(6.5, 4.2, 10.5, 4.6, 12, 7.6)
        path.cubicTo(13.5, 4.6, 17.5, 4.2, 19.5, 7)
        path.cubicTo(21.5, 10, 20, 14.5, 12, 20)
        p.setPen(Qt.NoPen); p.setBrush(color)
        p.drawPath(path)


@lru_cache(maxsize=256)
def pixmap(name: str, color: str, size: int = 20, dpr: float = 2.0) -> QPixmap:
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.fill(Qt.transparent)
    pm.setDevicePixelRatio(dpr)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 24.0, size / 24.0)
    _draw(p, name, QColor(color))
    p.end()
    return pm


def icon(name: str, color: str, size: int = 20) -> QIcon:
    return QIcon(pixmap(name, color, size))


# ---------------------------------------------------------------- brand
def logo_path(s: float) -> QPainterPath:
    """Angular 'K' mark of KJ Des, drawn in an s x s box."""
    u = s / 24.0
    path = QPainterPath()

    def poly(*pts):
        path.moveTo(pts[0][0] * u, pts[0][1] * u)
        for x, y in pts[1:]:
            path.lineTo(x * u, y * u)
        path.closeSubpath()

    # three separate blades: chamfered stem, upper arm, lower leg
    poly((3.0, 4.8), (5.8, 2.0), (9.2, 2.0), (9.2, 22.0), (3.0, 22.0))
    poly((10.8, 9.6), (18.0, 2.0), (23.0, 2.0), (10.8, 14.6))
    poly((12.9, 15.6), (15.9, 12.5), (23.2, 22.0), (17.5, 22.0))
    return path


def _metal_gradient(s: float) -> QLinearGradient:
    """Purple 'brushed metal': bright edge, dark core, a second sheen band."""
    grad = QLinearGradient(0, 0, s, s)
    grad.setColorAt(0.00, QColor("#f5ecff"))
    grad.setColorAt(0.18, QColor("#c9a6ff"))
    grad.setColorAt(0.42, QColor("#7c3aed"))
    grad.setColorAt(0.58, QColor("#b794ff"))
    grad.setColorAt(0.74, QColor("#6d28d9"))
    grad.setColorAt(1.00, QColor("#3b0f8c"))
    return grad


def paint_logo(p: QPainter, rect: QRectF, glow: bool = False) -> None:
    """Draw the KJ Des K mark (metallic purple) centred in rect."""
    s = min(rect.width(), rect.height())
    path = logo_path(s)
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.translate(rect.x() + (rect.width() - s) / 2, rect.y() + (rect.height() - s) / 2)
    if glow:
        p.setBrush(Qt.NoBrush)
        for width, alpha in ((s * 0.16, 18), (s * 0.10, 28), (s * 0.05, 45)):
            pen = QPen(QColor(155, 92, 255, alpha), width)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.drawPath(path)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(_metal_gradient(s)))
    p.drawPath(path)
    # fine top-left highlight edge for the metallic bevel
    if s >= 28:
        edge = QLinearGradient(0, 0, s, s)
        edge.setColorAt(0.0, QColor(255, 255, 255, 170))
        edge.setColorAt(0.5, QColor(255, 255, 255, 25))
        edge.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(QPen(QBrush(edge), max(0.8, s / 90)))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
    p.restore()


def chat_glyph_path(cx: float, cy: float, w: float) -> QPainterPath:
    """Original controller-face chat glyph (Discord-inspired, not the logo)."""
    h = w * 0.74
    x, y = cx - w / 2, cy - h / 2
    body = QPainterPath()
    body.moveTo(x + w * 0.16, y + h * 0.08)
    body.cubicTo(x + w * 0.30, y, x + w * 0.38, y + h * 0.04, x + w * 0.40, y + h * 0.10)
    body.lineTo(x + w * 0.60, y + h * 0.10)
    body.cubicTo(x + w * 0.62, y + h * 0.04, x + w * 0.70, y, x + w * 0.84, y + h * 0.08)
    body.cubicTo(x + w * 0.98, y + h * 0.32, x + w * 1.02, y + h * 0.62, x + w * 0.97, y + h * 0.84)
    body.cubicTo(x + w * 0.88, y + h * 0.93, x + w * 0.78, y + h * 0.99, x + w * 0.70, y + h)
    body.lineTo(x + w * 0.63, y + h * 0.88)
    body.cubicTo(x + w * 0.55, y + h * 0.91, x + w * 0.45, y + h * 0.91, x + w * 0.37, y + h * 0.88)
    body.lineTo(x + w * 0.30, y + h)
    body.cubicTo(x + w * 0.22, y + h * 0.99, x + w * 0.12, y + h * 0.93, x + w * 0.03, y + h * 0.84)
    body.cubicTo(x - w * 0.02, y + h * 0.62, x + w * 0.02, y + h * 0.32, x + w * 0.16, y + h * 0.08)
    body.closeSubpath()
    eyes = QPainterPath()
    eyes.addEllipse(QPointF(x + w * 0.34, y + h * 0.56), w * 0.085, h * 0.12)
    eyes.addEllipse(QPointF(x + w * 0.66, y + h * 0.56), w * 0.085, h * 0.12)
    return body.subtracted(eyes)


def app_icon_pixmap(size: int, accent: str | None = None) -> QPixmap:
    """Rounded-square app/tray icon: dark tile + K mark (+ optional state dot)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    r = QRectF(0.5, 0.5, size - 1, size - 1)
    bg = QLinearGradient(0, 0, size, size)
    bg.setColorAt(0, QColor("#1f1438")); bg.setColorAt(1, QColor("#08060f"))
    p.setBrush(bg)
    border = QLinearGradient(0, 0, size, size)
    border.setColorAt(0, QColor("#c4a1ff")); border.setColorAt(1, QColor("#5b21b6"))
    p.setPen(QPen(QBrush(border), max(1.0, size / 40)))
    p.drawRoundedRect(r, size * 0.24, size * 0.24)
    if size >= 32:   # soft violet glow behind the mark
        halo = QRadialGradient(QPointF(size * 0.5, size * 0.5), size * 0.45)
        halo.setColorAt(0, QColor(139, 92, 246, 95)); halo.setColorAt(1, QColor(139, 92, 246, 0))
        p.setPen(Qt.NoPen); p.setBrush(halo)
        p.drawRoundedRect(r, size * 0.24, size * 0.24)
    m = size * (0.17 if size >= 32 else 0.14)
    paint_logo(p, QRectF(m, m, size - 2 * m, size - 2 * m), glow=size >= 48)
    if accent:
        d = size * 0.34
        p.setPen(QPen(QColor("#0b0913"), max(1.0, size / 16)))
        p.setBrush(QColor(accent))
        p.drawEllipse(QRectF(size - d - 0.5, size - d - 0.5, d, d))
    p.end()
    return pm


def app_icon(accent: str | None = None) -> QIcon:
    ic = QIcon()
    for s in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        ic.addPixmap(app_icon_pixmap(s, accent))
    return ic
