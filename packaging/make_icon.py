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
    from PySide6.QtCore import Qt, QRectF
    from PySide6.QtGui import QImage, QPainter, QPainterPath, QBrush
    
    base_path = HERE.parent / "app" / "assets" / "images" / "icon_base.png"
    base = QImage(str(base_path))
    scaled = base.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    
    # We want a transparent background with rounded corners, but our image is white.
    # macOS icons usually manage their own masks or we can draw rounded corners on the white square.
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    
    path = QPainterPath()
    radius = size * 0.22
    path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    
    painter.setClipPath(path)
    painter.drawImage(0, 0, scaled)
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

    # Generate an .ico file for Windows
    ICO = HERE / "icon.ico"
    draw(256).save(str(ICO))
    print(f"Wrote {ICO}")

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
