# updater.py — Automatic update system for CodeZen India
#
# Architecture
# ────────────
#  UpdateCheckThread  — QThread that fetches the latest release JSON from GitHub
#  DownloadThread     — QThread that streams the installer download with progress
#  UpdateDialog       — Modal dialog: shows version info, changelog, download bar
#  check_for_updates  — Public one-call API used by main.py / Help menu
#
# GitHub Releases JSON shape expected:
#   {
#     "version":      "1.1.0",
#     "download_url": "https://…/CodeZenIndiaSetup.exe",
#     "changelog":    "- Added interpreter manager\n- Fixed terminal ANSI…"
#   }
#
# The URL below points to a raw JSON file hosted as a GitHub Release asset.
# Change UPDATE_URL to your own endpoint.

import os
import subprocess
import sys
import tempfile

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QTextEdit, QWidget,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from theme import FG_MUTED

UPDATE_URL = "https://raw.githubusercontent.com/ShubhxD69/CodeZenIndia/main/version.json"


APP_VERSION = "1.0.0"


# ─────────────────────────────────────────────────────────────────────────────
# Version comparison helper
# ─────────────────────────────────────────────────────────────────────────────
def _version_tuple(v: str) -> tuple[int, ...]:
    """Convert '1.2.3' → (1, 2, 3).  Returns (0,) on parse error."""
    try:
        return tuple(int(x) for x in str(v).strip().split("."))
    except (ValueError, AttributeError):
        return (0,)


def _is_newer(remote: str, local: str = APP_VERSION) -> bool:
    return _version_tuple(remote) > _version_tuple(local)


# ─────────────────────────────────────────────────────────────────────────────
# UpdateCheckThread
# ─────────────────────────────────────────────────────────────────────────────
class UpdateCheckThread(QThread):
    """Fetches the remote JSON and emits update_available or up_to_date."""

    update_available = pyqtSignal(dict)   # payload: {version, download_url, changelog}
    up_to_date       = pyqtSignal()
    check_failed     = pyqtSignal(str)    # error message

    def __init__(self, channel: str = "stable", parent=None):
        super().__init__(parent)
        self._channel = channel

    def run(self):
        try:
            import requests  # noqa: PLC0415
            url = UPDATE_URL
            if self._channel == "beta":
                url = url.replace("update.json", "update-beta.json")
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            remote_ver = str(data.get("version", "0"))
            if _is_newer(remote_ver):
                self.update_available.emit(data)
            else:
                self.up_to_date.emit()
        except ImportError:
            self.check_failed.emit(
                "requests library not installed.\n"
                "Run:  pip install requests"
            )
        except Exception as exc:
            self.check_failed.emit(str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# DownloadThread
# ─────────────────────────────────────────────────────────────────────────────
class DownloadThread(QThread):
    """Streams the installer download and reports progress (0–100)."""

    progress    = pyqtSignal(int)    # percent 0-100
    finished_ok = pyqtSignal(str)    # path to downloaded file
    failed      = pyqtSignal(str)    # error message

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self._url = url

    def run(self):
        try:
            import requests  # noqa: PLC0415
            resp = requests.get(self._url, stream=True, timeout=30)
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            suffix = os.path.splitext(self._url)[-1] or ".exe"
            tmp = tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix, prefix="CodeZenIndia_update_"
            )
            downloaded = 0
            chunk_size = 8192

            with tmp:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    tmp.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = min(int(downloaded * 100 / total), 100)
                        self.progress.emit(pct)

            self.progress.emit(100)
            self.finished_ok.emit(tmp.name)
        except ImportError:
            self.failed.emit("requests not installed.")
        except Exception as exc:
            self.failed.emit(str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# UpdateDialog
# ─────────────────────────────────────────────────────────────────────────────
class UpdateDialog(QDialog):
    """
    Shows the available update, displays changelog, and handles download + launch.
    """

    def __init__(self, payload: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update Available — CodeZen India")
        self.setMinimumSize(500, 380)
        self.setModal(True)
        self._payload = payload
        self._dl_thread: DownloadThread | None = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        # Title row
        title = QLabel(
            f"<b style='font-size:16px;color:#00b4d8;'>CodeZen India "
            f"{self._payload.get('version', '?')}</b>"
            f"  <span style='color:#858585;font-size:12px;'>"
            f"(you have {APP_VERSION})</span>"
        )
        title.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(title)

        # Changelog
        cl_label = QLabel("What's new:")
        root.addWidget(cl_label)

        self._changelog = QTextEdit()
        self._changelog.setReadOnly(True)
        self._changelog.setPlainText(
            self._payload.get("changelog", "No changelog provided.")
        )
        self._changelog.setMaximumHeight(160)
        root.addWidget(self._changelog)

        # Progress bar (hidden until download starts)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        # Status label
        self._status = QLabel("")
        self._status.setStyleSheet(f"color:{FG_MUTED}; font-size:11px;")
        root.addWidget(self._status)

        root.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        self._later_btn = QPushButton("Remind Me Later")
        self._later_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._later_btn)
        btn_row.addStretch()
        self._dl_btn = QPushButton("⬇  Download & Install")
        self._dl_btn.setObjectName("run_btn")
        self._dl_btn.clicked.connect(self._start_download)
        btn_row.addWidget(self._dl_btn)
        root.addLayout(btn_row)

    def _start_download(self):
        url = self._payload.get("download_url", "")
        if not url:
            self._status.setText("Error: no download URL in update manifest.")
            return

        self._dl_btn.setEnabled(False)
        self._later_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._status.setText("Downloading update…")

        self._dl_thread = DownloadThread(url, self)
        self._dl_thread.progress.connect(self._on_progress)
        self._dl_thread.finished_ok.connect(self._on_download_done)
        self._dl_thread.failed.connect(self._on_download_failed)
        self._dl_thread.start()

    def _on_progress(self, pct: int):
        self._progress.setValue(pct)
        self._status.setText(f"Downloading… {pct}%")

    def _on_download_done(self, path: str):
        self._status.setText("Download complete — launching installer…")
        self._progress.setValue(100)
        # Launch installer and close IDE
        try:
            if sys.platform == "win32":
                os.startfile(path)   # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            self._status.setText(f"Could not launch installer: {exc}")
            self._dl_btn.setEnabled(True)
            self._later_btn.setEnabled(True)
            return
        # Give installer 1 s to start, then quit the IDE
        QTimer.singleShot(1000, lambda: sys.exit(0))

    def _on_download_failed(self, msg: str):
        self._progress.setVisible(False)
        self._status.setText(f"Download failed: {msg}")
        self._dl_btn.setEnabled(True)
        self._later_btn.setEnabled(True)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────
def check_for_updates(parent=None, silent: bool = True):
    """
    Check for updates in the background.

    silent=True  → only show a dialog when an update IS available.
    silent=False → also show a 'you are up to date' message.
    """
    from settings import Settings
    cfg = Settings.instance()
    channel = cfg.get("update_channel", "stable")

    thread = UpdateCheckThread(channel, parent)

    def _on_available(payload: dict):
        dlg = UpdateDialog(payload, parent)
        dlg.exec()

    def _on_up_to_date():
        if not silent:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                parent, "Check for Updates",
                f"You are running the latest version ({APP_VERSION})."
            )

    def _on_failed(msg: str):
        if not silent:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                parent, "Check for Updates",
                f"Could not reach the update server:\n{msg}"
            )

    thread.update_available.connect(_on_available)
    thread.up_to_date.connect(_on_up_to_date)
    thread.check_failed.connect(_on_failed)
    thread.start()

    return thread   # keep reference alive until the thread finishes
