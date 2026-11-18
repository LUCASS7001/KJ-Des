"""
packaging/make_icon.py
Exports every KJ Des brand asset from the vector mark in ui/icons.py, so the
icons always match the UI:

  app/assets/icon.ico              Windows icon, 16–256 px (PNG-compressed entries)
  app/assets/icon.png              256 px app tile
  app/assets/brand/kjdes-icon-512.png / -1024.png   app tile (store/web/README use)
  app/assets/brand/kjdes-mark-512.png               K mark only, transparent, with glow
  packaging/assets/wizard-small-55.bmp / -110.bmp    Inno Setup header image (100 % / 200 %)

    python packaging/make_icon.py
"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPixmap  # noqa: E402

from ui.icons import app_icon_pixmap, paint_logo  # noqa: E402

ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


def png_bytes(pm: QPixmap) -> bytes:
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.WriteOnly)
    pm.save(buf, "PNG")
    return bytes(data)


def write_ico(path: str) -> None:
    images = [(s, png_bytes(app_icon_pixmap(s))) for s in ICO_SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, blobs = b"", b""
    for size, blob in images:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
        blobs += blob
    with open(path, "wb") as f:
        f.write(header + entries + blobs)


def mark_pixmap(size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    m = size * 0.12
    paint_logo(p, QRectF(m, m, size - 2 * m, size - 2 * m), glow=True)
    p.end()
    return pm


def wizard_bmp(size: int, path: str) -> None:
    """Inno Setup header image: BMP has no alpha, so flatten on white."""
    img = QImage(size, size, QImage.Format_RGB32)
    img.fill(QColor("#ffffff"))
    p = QPainter(img)
    p.drawPixmap(0, 0, app_icon_pixmap(size))
    p.end()
    img.save(path, "BMP")


def main() -> list:
    _app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    assets = os.path.join(ROOT, "app", "assets")
    brand = os.path.join(assets, "brand")
    pkg = os.path.join(ROOT, "packaging", "assets")
    os.makedirs(brand, exist_ok=True)
    os.makedirs(pkg, exist_ok=True)
    out = []
    write_ico(os.path.join(assets, "icon.ico")); out.append("icon.ico")
    app_icon_pixmap(256).save(os.path.join(assets, "icon.png")); out.append("icon.png")
    for s in (512, 1024):
        app_icon_pixmap(s).save(os.path.join(brand, f"kjdes-icon-{s}.png"))
        out.append(f"brand/kjdes-icon-{s}.png")
    mark_pixmap(512).save(os.path.join(brand, "kjdes-mark-512.png"))
    out.append("brand/kjdes-mark-512.png")
    for s in (55, 110):
        wizard_bmp(s, os.path.join(pkg, f"wizard-small-{s}.bmp"))
        out.append(f"packaging/assets/wizard-small-{s}.bmp")
    return out


if __name__ == "__main__":
    for item in main():
        print("wrote", item)
