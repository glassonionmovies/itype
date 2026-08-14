#!/usr/bin/env python3
"""Generate the app icon.

Draws the icon with Qt rather than shipping a binary asset, then folds it into
an ``.icns`` with macOS's ``iconutil``. On other platforms it stops after
writing the PNGs, which is enough for development.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ICONSET = HERE / "icon.iconset"
ICNS = HERE / "icon.icns"

#: macOS wants these sizes, each also at @2x.
SIZES = [16, 32, 128, 256, 512]


def draw(size: int) -> "QImage":  # type: ignore[name-defined]
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import (
        QBrush,
        QColor,
        QFont,
        QImage,
        QLinearGradient,
        QPainter,
        QPen,
    )

    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Rounded background with the app's accent gradient.
    radius = size * 0.22
    rect = QRectF(size * 0.04, size * 0.04, size * 0.92, size * 0.92)
    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0.0, QColor("#2A3350"))
    gradient.setColorAt(1.0, QColor("#151824"))
    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(rect, radius, radius)

    # A single lit keycap: the whole idea of the app in one shape.
    cap = QRectF(size * 0.24, size * 0.22, size * 0.52, size * 0.52)
    cap_gradient = QLinearGradient(cap.topLeft(), cap.bottomLeft())
    cap_gradient.setColorAt(0.0, QColor("#6FBAFF"))
    cap_gradient.setColorAt(1.0, QColor("#4FA8FF"))
    painter.setBrush(QBrush(cap_gradient))
    painter.setPen(QPen(QColor("#FFFFFF"), max(1.0, size * 0.012)))
    painter.drawRoundedRect(cap, size * 0.1, size * 0.1)

    font = QFont("Helvetica", int(size * 0.30))
    font.setWeight(QFont.Weight.Black)
    painter.setFont(font)
    painter.setPen(QPen(QColor("#0C1220")))
    painter.drawText(cap, Qt.AlignmentFlag.AlignCenter, "A")

    # Underline echoing the in-game target cue.
    painter.setPen(QPen(QColor("#4BE08C"), max(2.0, size * 0.045), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    y = size * 0.83
    painter.drawLine(int(size * 0.30), int(y), int(size * 0.70), int(y))

    painter.end()
    return image


def main() -> int:
    try:
        from PySide6.QtGui import QGuiApplication  # noqa: F401
    except ImportError:
        print("PySide6 is required to generate the icon.", file=sys.stderr)
        return 1

    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication([])

    ICONSET.mkdir(exist_ok=True)
    for size in SIZES:
        draw(size).save(str(ICONSET / f"icon_{size}x{size}.png"))
        draw(size * 2).save(str(ICONSET / f"icon_{size}x{size}@2x.png"))
    print(f"Wrote {len(SIZES) * 2} PNGs to {ICONSET}")

    if sys.platform == "darwin" and shutil.which("iconutil"):
        subprocess.run(
            ["iconutil", "-c", "icns", str(ICONSET), "-o", str(ICNS)], check=True
        )
        shutil.rmtree(ICONSET)
        print(f"Wrote {ICNS}")
    else:
        print("iconutil not available; leaving the .iconset directory in place.")

    del app
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
