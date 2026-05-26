# main.py — Application entry point for CodeZen India
#
# Start-up sequence
# ─────────────────
#  1. Guard against recursive subprocess launch (CODEZEN_SUBPROCESS env var)
#  2. Load settings
#  3. Show animated splash screen
#  4. Build MainWindow while splash is visible
#  5. Fade out splash, show IDE
#  6. Trigger silent auto-update check (if enabled in settings)

import sys
import os

# Ensure the project directory is on sys.path so all sibling modules resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Recursive-launch guard ────────────────────────────────────────────────────
# If a user script executed by QProcess somehow triggers main.py again, refuse
# to create a second IDE instance / splash screen.
if os.environ.get("CODEZEN_SUBPROCESS"):
    sys.stderr.write(
        "CodeZen: main.py was invoked inside an IDE subprocess — "
        "refusing to launch a second IDE instance.\n"
    )
    sys.exit(1)
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore    import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui     import (
    QPixmap, QPainter, QColor, QFont, QBrush, QLinearGradient, QIcon,
)

from theme       import APP_STYLE, FG_WHITE, BORDER
from settings    import Settings
from main_window import MainWindow


APP_NAME    = "CodeZen India"
APP_VERSION = "1.1.0"
DEVELOPER   = "Developed By Shubh Mishra"


def _resource(relative: str) -> str:
    """Resolve a bundled-asset path for both script and PyInstaller EXE."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


# ─────────────────────────────────────────────────────────────────────────────
# Splash pixmap (rendered entirely in code — no external image required)
# ─────────────────────────────────────────────────────────────────────────────
def _make_splash(w: int = 580, h: int = 320) -> QPixmap:
    px = QPixmap(w, h)
    px.fill(Qt.GlobalColor.transparent)

    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background gradient
    bg = QLinearGradient(0, 0, 0, h)
    bg.setColorAt(0.0, QColor("#1a1a2e"))
    bg.setColorAt(0.5, QColor("#16213e"))
    bg.setColorAt(1.0, QColor("#0f3460"))
    p.setBrush(QBrush(bg))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 0, w, h, 14, 14)

    # Top accent bar
    bar = QLinearGradient(0, 0, w, 0)
    bar.setColorAt(0.0, QColor("#007acc"))
    bar.setColorAt(1.0, QColor("#00b4d8"))
    p.setBrush(QBrush(bar))
    p.drawRoundedRect(0, 0, w, 5, 2, 2)

    # Icon  < / >
    p.setFont(QFont("Consolas", 36, QFont.Weight.Bold))
    p.setPen(QColor("#00b4d8"))
    p.drawText(0, 40, w, 72, Qt.AlignmentFlag.AlignHCenter, "< / >")

    # App name
    p.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
    p.setPen(QColor(FG_WHITE))
    p.drawText(0, 116, w, 52, Qt.AlignmentFlag.AlignHCenter, APP_NAME)

    # Tag line
    p.setFont(QFont("Segoe UI", 12))
    p.setPen(QColor("#90caf9"))
    p.drawText(0, 170, w, 28, Qt.AlignmentFlag.AlignHCenter, "Professional Python IDE")

    # Version badge
    p.setFont(QFont("Segoe UI", 10))
    p.setPen(QColor("#007acc"))
    badge_rect_x = (w - 80) // 2
    p.setBrush(QColor("#1a3a5c"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(badge_rect_x, 200, 80, 22, 6, 6)
    p.setPen(QColor("#90caf9"))
    p.drawText(badge_rect_x, 200, 80, 22, Qt.AlignmentFlag.AlignCenter,
               f"v{APP_VERSION}")

    # Loading hint
    p.setFont(QFont("Segoe UI", 9))
    p.setPen(QColor("#555"))
    p.drawText(0, 228, w, 22, Qt.AlignmentFlag.AlignHCenter, "Loading…")

    # Developer credit
    p.setFont(QFont("Segoe UI", 10))
    p.setPen(QColor("#aaaaaa"))
    p.drawText(0, h - 44, w, 24, Qt.AlignmentFlag.AlignHCenter, DEVELOPER)

    # Version text (bottom)
    p.setFont(QFont("Segoe UI", 9))
    p.setPen(QColor("#555"))
    p.drawText(0, h - 24, w, 20, Qt.AlignmentFlag.AlignHCenter,
               f"Version {APP_VERSION}")

    # Border
    p.setPen(QColor(BORDER))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(1, 1, w - 2, h - 2, 13, 13)

    p.end()
    return px


# ─────────────────────────────────────────────────────────────────────────────
# Animated splash screen
# ─────────────────────────────────────────────────────────────────────────────
class SplashScreen(QSplashScreen):
    """Fade in → hold 2 s → fade out."""

    def __init__(self):
        super().__init__(_make_splash())
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.SplashScreen
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.0)

    def fade_in(self, on_done):
        self._anim_in = QPropertyAnimation(self, b"windowOpacity")
        self._anim_in.setDuration(700)
        self._anim_in.setStartValue(0.0)
        self._anim_in.setEndValue(1.0)
        self._anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_in.finished.connect(on_done)
        self._anim_in.start()

    def fade_out(self, on_done):
        self._anim_out = QPropertyAnimation(self, b"windowOpacity")
        self._anim_out.setDuration(450)
        self._anim_out.setStartValue(1.0)
        self._anim_out.setEndValue(0.0)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim_out.finished.connect(on_done)
        self._anim_out.start()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # Windows: register AppUserModelID for correct taskbar grouping / icon
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "ShubhMishra.CodeZenIndia.1.1"
            )
        except Exception:
            pass

    # Load settings before anything else
    cfg = Settings.instance()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Shubh Mishra")
    app.setStyleSheet(APP_STYLE)

    # Apply font size from settings
    app.setFont(QFont("Segoe UI", cfg.get("font_size", 10)))

    # Custom application icon
    _icon_path = _resource("assets/icons/logo.ico")
    if os.path.isfile(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))

    # Show the splash screen immediately
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # Build the main window while the splash is visible
    window = MainWindow()

    def _reveal():
        splash.fade_out(lambda: (splash.finish(window), window.show()))

    def _after_show():
        # Trigger silent auto-update check after IDE is fully visible
        window.check_for_updates_silently()

    # Fade in → hold 2 s → fade out → show IDE → check for updates
    splash.fade_in(
        lambda: QTimer.singleShot(2000, _reveal)
    )
    # Delay update check until 3.5 s after launch (after splash finishes)
    QTimer.singleShot(3500, _after_show)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
