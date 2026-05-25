#!/usr/bin/env python3
"""
create_icon.py — Generates  assets/icons/logo.ico  for CodeZen India.

Run once before building the EXE (or any time you want to regenerate it):

    python create_icon.py

Requirements: PyQt6 (already a project dependency — nothing extra needed).

What it does
────────────
1. Renders the CodeZen India logo at 7 sizes (16 → 256 px) using QPainter.
2. Encodes each render as a PNG blob in memory.
3. Packs the blobs into a valid Windows ICO file (Vista+ PNG-in-ICO format).
4. Saves the result to  assets/icons/logo.ico.

The same logo.ico is then used by:
  • QApplication / QMainWindow  →  title bar + taskbar (runtime)
  • PyInstaller --icon           →  the .exe file icon  (build time)
"""

import sys
import os
import struct

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR  = os.path.join(SCRIPT_DIR, "assets", "icons")
ICON_FILE  = os.path.join(ICONS_DIR, "logo.ico")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import (
    QPixmap, QPainter, QColor, QFont, QBrush, QLinearGradient,
)
from PyQt6.QtCore import Qt, QBuffer, QIODevice, QRect


# ─────────────────────────────────────────────────────────────────────────────
# Logo renderer
# ─────────────────────────────────────────────────────────────────────────────
def _render_png(size: int) -> bytes:
    """
    Draw the CodeZen India logo at `size` × `size` pixels and
    return the result encoded as PNG bytes.

    Visual design
    ─────────────
    • Dark-navy rounded-rect background (gradient)
    • Thin cyan accent stripe across the top
    • Centred  "< / >"  in Consolas, cyan (#00b4d8)
    """
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)

    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    r = max(2, size // 7)   # corner radius scales with icon size

    # ── Background gradient ───────────────────────────────────────────────────
    bg = QLinearGradient(0, 0, 0, size)
    bg.setColorAt(0.0, QColor("#1a1a2e"))
    bg.setColorAt(1.0, QColor("#0f3460"))
    p.setBrush(QBrush(bg))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 0, size, size, r, r)

    # ── Cyan accent stripe at the top ─────────────────────────────────────────
    sh = max(2, size // 16)
    stripe = QLinearGradient(0, 0, size, 0)
    stripe.setColorAt(0.0, QColor("#007acc"))
    stripe.setColorAt(1.0, QColor("#00b4d8"))
    p.setBrush(QBrush(stripe))
    p.drawRoundedRect(0, 0, size, sh, 2, 2)

    # ── "< / >" text ──────────────────────────────────────────────────────────
    # For very small sizes use only ">" to keep it readable
    if size <= 24:
        text      = ">"
        font_size = max(6, int(size * 0.55))
    elif size <= 32:
        text      = "</>"
        font_size = max(6, int(size * 0.38))
    else:
        text      = "< / >"
        font_size = max(6, size // 4)

    font = QFont("Consolas", font_size, QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QColor("#00b4d8"))
    p.drawText(
        QRect(0, 0, size, size),
        Qt.AlignmentFlag.AlignCenter,
        text,
    )

    p.end()

    # ── Encode as in-memory PNG ───────────────────────────────────────────────
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    px.save(buf, "PNG")
    return bytes(buf.data())


# ─────────────────────────────────────────────────────────────────────────────
# Pure-Python ICO packer  (no Pillow required)
# ─────────────────────────────────────────────────────────────────────────────
def _pack_ico(images: list[tuple[int, bytes]]) -> bytes:
    """
    Pack a list of  (pixel_size, png_bytes)  into a Windows ICO file.

    Windows Vista+ supports PNG-embedded ICO files natively, so we can
    store the PNG blobs directly — no BMP conversion needed.

    ICO binary layout
    ─────────────────
    ICONDIR        6 bytes   reserved(2) | type=1(2) | count(2)
    ICONDIRENTRY × N  16 bytes each
      width        1 byte    (0 encodes 256 per Windows spec)
      height       1 byte
      colorCount   1 byte    (0 = true-colour / no palette)
      reserved     1 byte    (always 0)
      planes       2 bytes   (1)
      bitCount     2 bytes   (32 for RGBA)
      bytesInRes   4 bytes   size of the image blob
      imageOffset  4 bytes   offset from start of file
    IMAGE DATA
      ... PNG blobs, concatenated ...
    """
    count       = len(images)
    header_size = 6
    entry_size  = 16
    data_start  = header_size + entry_size * count

    # Pre-compute absolute byte offsets for each image blob
    offsets: list[int] = []
    pos = data_start
    for _sz, blob in images:
        offsets.append(pos)
        pos += len(blob)

    # ICONDIR
    ico = struct.pack("<HHH", 0, 1, count)

    # ICONDIRENTRY × count
    for i, (sz, blob) in enumerate(images):
        w = 0 if sz >= 256 else sz
        h = 0 if sz >= 256 else sz
        ico += struct.pack(
            "<BBBBHHII",
            w, h,
            0,              # colorCount
            0,              # reserved
            1,              # planes
            32,             # bitCount
            len(blob),
            offsets[i],
        )

    # Image blobs
    for _sz, blob in images:
        ico += blob

    return ico


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    # QApplication is required for QPixmap / QPainter
    app = QApplication(sys.argv)

    os.makedirs(ICONS_DIR, exist_ok=True)

    print(f"Target : {ICON_FILE}")
    print()

    sizes  = [16, 24, 32, 48, 64, 128, 256]
    images: list[tuple[int, bytes]] = []

    for s in sizes:
        png = _render_png(s)
        images.append((s, png))
        print(f"  rendered  {s:>3} x {s:<3}  ({len(png):>7,} bytes)")

    ico = _pack_ico(images)
    with open(ICON_FILE, "wb") as fh:
        fh.write(ico)

    kb = len(ico) / 1024
    print()
    print(f"Saved  : {ICON_FILE}")
    print(f"Size   : {len(ico):,} bytes  ({kb:.1f} KB)")
    print()
    print("Next steps:")
    print("  1. Run the IDE:   python main.py")
    print("  2. Build the EXE: pyinstaller CodeZenIndia.spec")


if __name__ == "__main__":
    main()
