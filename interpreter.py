# interpreter.py — Python Interpreter Manager for CodeZen India v1.1.0
#
# Public API
# ──────────
#   get_active_interpreter()         → str  (path for running scripts)
#   find_interpreters()              → list[PythonInfo]
#   InterpreterManagerDialog(parent) → modal dialog (select + install Python)

import os
import re
import sys
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import ClassVar

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QFileDialog, QWidget, QMessageBox,
    QTabWidget, QProgressBar, QScrollArea,
    QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor

from settings import Settings
from theme import BG_PANEL, BG_DARK, FG_TEXT, FG_MUTED, BORDER, BG_HOVER


# ─────────────────────────────────────────────────────────────────────────────
# PythonInfo
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class PythonInfo:
    path:    str
    version: str = ""
    kind:    str = "system"   # "system" | "venv" | "conda" | "custom"

    KIND_LABELS: ClassVar[dict[str, str]] = {
        "system": "System",
        "venv":   "Virtual Env",
        "conda":  "Conda",
        "custom": "Custom",
    }

    @property
    def label(self) -> str:
        tag = self.KIND_LABELS.get(self.kind, self.kind)
        ver = self.version or "unknown version"
        return f"{ver}  [{tag}]  {self.path}"

    @property
    def short_label(self) -> str:
        return self.version or os.path.basename(self.path)

    @property
    def version_tuple(self) -> tuple:
        """Return numeric version tuple for comparison, e.g. (3, 11, 4)."""
        m = re.search(r"(\d+)\.(\d+)\.?(\d*)", self.version)
        if m:
            return tuple(int(x) for x in m.groups() if x)
        return (0,)


# ─────────────────────────────────────────────────────────────────────────────
# Version detection
# ─────────────────────────────────────────────────────────────────────────────
def _probe_version(path: str) -> str:
    """Return 'Python X.Y.Z' for the given interpreter, or '' on failure."""
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True, text=True, timeout=5
        )
        out = (result.stdout or result.stderr or "").strip()
        if out.startswith("Python"):
            return out
        return out[:40] if out else ""
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Interpreter discovery
# ─────────────────────────────────────────────────────────────────────────────
def find_interpreters() -> list:
    """
    Scan for Python interpreters.  Returns a deduplicated, sorted list.
    Excludes WindowsApps Microsoft Store aliases and broken executables.
    """
    seen: set[str] = set()
    results: list[PythonInfo] = []

    def _add(path: str, kind: str = "system"):
        real = os.path.realpath(path)
        if "WindowsApps" in real:
            return
        if real in seen or not os.path.isfile(path):
            return
        seen.add(real)
        ver = _probe_version(path)
        if "was not found" in ver or "Microsoft Store" in ver:
            return
        if ver:
            results.append(PythonInfo(path=path, version=ver, kind=kind))

    # 1. Current interpreter (skip if frozen — it's the IDE itself)
    if not getattr(sys, "frozen", False):
        _add(sys.executable)

    # 2. PATH candidates
    for name in ("python3", "python", "python3.14", "python3.13",
                 "python3.12", "python3.11", "python3.10", "python3.9"):
        found = shutil.which(name)
        if found:
            _add(found)

    # 3. Windows-style common install paths
    if sys.platform == "win32":
        for base in (r"C:\Python314", r"C:\Python313", r"C:\Python312",
                     r"C:\Python311", r"C:\Python310", r"C:\Python39"):
            _add(os.path.join(base, "python.exe"))
        # User-installed Python via the official installer
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            pkgs = os.path.join(local_app, "Programs", "Python")
            if os.path.isdir(pkgs):
                for d in sorted(os.listdir(pkgs), reverse=True):
                    _add(os.path.join(pkgs, d, "python.exe"))
        # Program Files installs
        for pf in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")):
            if pf:
                py_dir = os.path.join(pf, "Python")
                if os.path.isdir(py_dir):
                    for d in sorted(os.listdir(py_dir), reverse=True):
                        _add(os.path.join(py_dir, d, "python.exe"))

    # 4. Scan for .venv directories in common locations
    _venv_search_dirs = [
        os.getcwd(),
        os.path.expanduser("~"),
        os.path.expanduser("~/projects"),
        os.path.expanduser("~/Documents"),
    ]
    for base in _venv_search_dirs:
        if not os.path.isdir(base):
            continue
        for subdir in os.listdir(base)[:40]:
            for venv_name in (".venv", "venv", "env", ".env"):
                if subdir == venv_name:
                    venv_root = os.path.join(base, subdir)
                else:
                    venv_root = os.path.join(base, subdir, venv_name)
                if sys.platform == "win32":
                    candidate = os.path.join(venv_root, "Scripts", "python.exe")
                else:
                    candidate = os.path.join(venv_root, "bin", "python3")
                    if not os.path.isfile(candidate):
                        candidate = os.path.join(venv_root, "bin", "python")
                _add(candidate, kind="venv")

    # 5. Conda environments
    conda_base_candidates = [
        os.path.expanduser("~/anaconda3"),
        os.path.expanduser("~/miniconda3"),
        os.path.expanduser("~/miniforge3"),
        os.path.join(os.environ.get("USERPROFILE", ""), "anaconda3"),
        os.path.join(os.environ.get("USERPROFILE", ""), "miniconda3"),
        "/opt/anaconda3", "/opt/miniconda3", "/usr/local/anaconda3",
    ]
    for conda_base in conda_base_candidates:
        if not os.path.isdir(conda_base):
            continue
        _exe = os.path.join(
            conda_base,
            "python.exe" if sys.platform == "win32" else "bin/python3"
        )
        _add(_exe, kind="conda")
        envs_dir = os.path.join(conda_base, "envs")
        if os.path.isdir(envs_dir):
            for env_name in os.listdir(envs_dir)[:20]:
                env_root = os.path.join(envs_dir, env_name)
                if sys.platform == "win32":
                    _add(os.path.join(env_root, "python.exe"), kind="conda")
                else:
                    _add(os.path.join(env_root, "bin", "python3"), kind="conda")
                    _add(os.path.join(env_root, "bin", "python"), kind="conda")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Smart auto-selection
# ─────────────────────────────────────────────────────────────────────────────
def _auto_select_best(interpreters: list) -> "PythonInfo | None":
    """
    From a list of valid PythonInfo objects, pick the best one.
    Priority: latest stable system Python > user-installed > venv > conda
    """
    if not interpreters:
        return None

    kind_order = {"system": 0, "custom": 1, "venv": 2, "conda": 3}

    def _score(info: PythonInfo):
        kind_rank = kind_order.get(info.kind, 9)
        ver = info.version_tuple
        # negate version so higher version sorts first (lower sort key = higher priority)
        neg_ver = tuple(-v for v in ver)
        return (kind_rank,) + neg_ver

    return min(interpreters, key=_score)


# ─────────────────────────────────────────────────────────────────────────────
# Public helper — always use this for running scripts
# ─────────────────────────────────────────────────────────────────────────────
def get_active_interpreter() -> str:
    """
    Return the interpreter path that should be used for running scripts.
    Priority:
      1. User-selected path saved in settings.json (if still valid)
      2. Auto-selected best available interpreter
      3. python3 / python from PATH
    """
    cfg = Settings.instance()
    saved = cfg.get("interpreter_path", "")

    # 1 — use saved if still valid and not a fake Windows Store alias
    if saved and os.path.isfile(saved) and "WindowsApps" not in os.path.realpath(saved):
        ver = _probe_version(saved)
        if ver and "was not found" not in ver and "Microsoft Store" not in ver:
            return saved

    # 2 — auto-select best available and persist it
    interpreters = find_interpreters()
    best = _auto_select_best(interpreters)
    if best:
        cfg.set("interpreter_path", best.path)
        return best.path

    # 3 — fallback to PATH
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found and "WindowsApps" not in os.path.realpath(found):
            return found

    return "python3"


# ─────────────────────────────────────────────────────────────────────────────
# Discovery thread
# ─────────────────────────────────────────────────────────────────────────────
class _ScanThread(QThread):
    done = pyqtSignal(list)

    def run(self):
        self.done.emit(find_interpreters())


# ─────────────────────────────────────────────────────────────────────────────
# Python.org version fetcher
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class PyOrgRelease:
    version:  str
    url_64:   str = ""
    url_32:   str = ""

    @property
    def version_tuple(self) -> tuple:
        try:
            return tuple(int(x) for x in self.version.split(".") if x.isdigit())
        except Exception:
            return (0,)


class _VersionFetchThread(QThread):
    """
    Fetch available stable Python releases.

    Strategy 1 (primary): endoflife.date JSON API
      — fast, reliable, no HTML parsing, no JavaScript dependency.
      — https://endoflife.date/api/python.json
      — returns all Python cycles with exact latest patch version + EOL date.

    Strategy 2 (fallback): hardcoded recent stable versions
      — used when the network is unavailable; gives the user something
        rather than a blank list so they can still manually download.

    NOTE: python.org/downloads/windows/ was previously used but that page
    is JavaScript-rendered — its raw HTML contains zero EXE links.
    The endoflife.date API is the correct replacement.
    """

    done   = pyqtSignal(list)   # list[PyOrgRelease]
    failed = pyqtSignal(str)

    _ENDOFLIFE_URL = "https://endoflife.date/api/python.json"
    _FTP_BASE      = "https://www.python.org/ftp/python"
    _MIN_MINOR     = 9       # show Python 3.9 and newer
    _MAX_RESULTS   = 8

    def run(self):
        errors: list[str] = []

        # ── Strategy 1: endoflife.date JSON API ───────────────────────────────
        try:
            releases = self._fetch_via_endoflife()
            if releases:
                self.done.emit(releases)
                return
            errors.append("endoflife.date API returned an empty list.")
        except Exception as exc:
            errors.append(f"endoflife.date API: {exc}")

        # ── Strategy 2: hardcoded recent stable table (offline fallback) ──────
        try:
            releases = self._hardcoded_fallback()
            if releases:
                self.done.emit(releases)
                return
        except Exception as exc:
            errors.append(f"Fallback table: {exc}")

        # Both strategies failed — surface the real error to the user
        self.failed.emit(
            "Could not fetch Python version list.\n\n"
            + "\n".join(errors)
            + "\n\nCheck your internet connection and try again."
        )

    def _fetch_via_endoflife(self) -> list:
        """
        Fetch https://endoflife.date/api/python.json and build PyOrgRelease
        objects using the official python.org FTP installer URL pattern.
        """
        import urllib.request
        import json
        from datetime import date

        req = urllib.request.Request(
            self._ENDOFLIFE_URL,
            headers={
                "User-Agent": "CodeZenIndia/1.1.0",
                "Accept":     "application/json",
            }
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        today_iso = date.today().isoformat()   # e.g. "2026-05-26"
        releases: list[PyOrgRelease] = []

        for cycle in data:
            latest = (cycle.get("latest") or "").strip()
            if not latest:
                continue

            # Skip any pre-release version strings (contain a/b/rc)
            if re.search(r"[a-zA-Z]", latest):
                continue

            parts = [int(x) for x in latest.split(".") if x.isdigit()]
            if len(parts) < 2 or parts[0] != 3 or parts[1] < self._MIN_MINOR:
                continue

            # Skip end-of-life versions (eol can be False or a date string)
            eol = cycle.get("eol", False)
            if isinstance(eol, str) and eol < today_iso:
                continue

            url_64 = f"{self._FTP_BASE}/{latest}/python-{latest}-amd64.exe"
            url_32 = f"{self._FTP_BASE}/{latest}/python-{latest}.exe"
            releases.append(
                PyOrgRelease(version=latest, url_64=url_64, url_32=url_32)
            )

        return sorted(
            releases, key=lambda r: r.version_tuple, reverse=True
        )[:self._MAX_RESULTS]

    @staticmethod
    def _hardcoded_fallback() -> list:
        """
        Static table of known recent stable releases.
        Used when the network is unavailable to avoid a blank installer tab.
        URLs follow the standard python.org FTP naming convention.
        """
        _FTP = "https://www.python.org/ftp/python"
        known = [
            "3.14.5", "3.13.13", "3.12.13", "3.11.15", "3.10.20",
        ]
        return [
            PyOrgRelease(
                version=ver,
                url_64=f"{_FTP}/{ver}/python-{ver}-amd64.exe",
                url_32=f"{_FTP}/{ver}/python-{ver}.exe",
            )
            for ver in known
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Python installer download + launch thread
# ─────────────────────────────────────────────────────────────────────────────
class _InstallerDownloadThread(QThread):
    """Download a Python installer from python.org and launch it."""

    progress     = pyqtSignal(int)   # 0-100
    finished_ok  = pyqtSignal(str)   # path to installer
    failed       = pyqtSignal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self._url = url

    def run(self):
        try:
            import urllib.request

            req = urllib.request.Request(
                self._url,
                headers={"User-Agent": "CodeZenIndia/1.1.0"}
            )

            tmp_path = os.path.join(
                tempfile.gettempdir(),
                f"CodeZenIndia_python_{os.path.basename(self._url)}"
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 65536

                with open(tmp_path, "wb") as fh:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        fh.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = min(int(downloaded * 100 / total), 99)
                            self.progress.emit(pct)

            self.progress.emit(100)
            self.finished_ok.emit(tmp_path)

        except Exception as exc:
            self.failed.emit(str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# InterpreterManagerDialog  (Select + Install tabs)
# ─────────────────────────────────────────────────────────────────────────────
class InterpreterManagerDialog(QDialog):
    """
    Two-tab dialog:
      Tab 1 — Select Python Interpreter (scan + badges + browse)
      Tab 2 — Python Install Manager   (fetch from python.org + install)
    """

    interpreter_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Python Interpreter Manager")
        self.setMinimumSize(680, 520)
        self.setModal(True)

        self._infos: list[PythonInfo] = []
        self._releases: list[PyOrgRelease] = []
        self._dl_thread: "_InstallerDownloadThread | None" = None

        self._build_ui()
        self._start_scan()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_select_tab(), "  Select Interpreter  ")
        self._tabs.addTab(self._build_install_tab(), "  Install / Update Python  ")
        root.addWidget(self._tabs)

    # ── Tab 1: Select ─────────────────────────────────────────────────────────
    def _build_select_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(16, 16, 16, 16)

        hdr = QLabel("Select Python Interpreter")
        hdr.setStyleSheet("font-size:15px;font-weight:bold;color:#d4d4d4;")
        lay.addWidget(hdr)

        sub = QLabel(
            "Choose the Python interpreter used when running scripts.\n"
            "Badges:  ACTIVE = currently selected  |  LATEST = newest found  |  RECOMMENDED = best choice"
        )
        sub.setStyleSheet(f"color:{FG_MUTED};font-size:11px;")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        self._list = QListWidget()
        self._list.setStyleSheet(
            f"QListWidget{{background:{BG_PANEL};border:1px solid {BORDER};"
            f"border-radius:4px;color:{FG_TEXT};}}"
            f"QListWidget::item{{padding:10px 12px;border-bottom:1px solid #1e1e1e;}}"
            f"QListWidget::item:selected{{background:{BG_HOVER};color:#fff;}}"
        )
        mono = QFont("Consolas", 11)
        mono.setFixedPitch(True)
        self._list.setFont(mono)
        lay.addWidget(self._list)

        self._scan_status = QLabel("Scanning for interpreters…")
        self._scan_status.setStyleSheet(f"color:{FG_MUTED};font-size:11px;")
        lay.addWidget(self._scan_status)

        btns = QHBoxLayout()
        self._browse_btn = QPushButton("Browse…")
        self._browse_btn.clicked.connect(self._browse)
        btns.addWidget(self._browse_btn)

        self._refresh_btn = QPushButton("↺  Refresh")
        self._refresh_btn.clicked.connect(self._start_scan)
        btns.addWidget(self._refresh_btn)

        btns.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        self._select_btn = QPushButton("Select")
        self._select_btn.setObjectName("run_btn")
        self._select_btn.clicked.connect(self._confirm_selection)
        self._select_btn.setEnabled(False)
        btns.addWidget(self._select_btn)
        lay.addLayout(btns)
        return w

    # ── Tab 2: Install ────────────────────────────────────────────────────────
    def _build_install_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(16, 16, 16, 16)

        hdr = QLabel("Python Install / Update Manager")
        hdr.setStyleSheet("font-size:15px;font-weight:bold;color:#d4d4d4;")
        lay.addWidget(hdr)

        sub = QLabel(
            "Download and install official Python releases from python.org.\n"
            "Only stable releases are shown.  Downloads run in the background."
        )
        sub.setStyleSheet(f"color:{FG_MUTED};font-size:11px;")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        # Scroll area for version cards
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet(
            f"QScrollArea{{background:{BG_PANEL};border:1px solid {BORDER};border-radius:4px;}}"
        )
        self._cards_widget = QWidget()
        self._cards_widget.setStyleSheet(f"background:{BG_PANEL};")
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setSpacing(6)
        self._cards_layout.setContentsMargins(8, 8, 8, 8)
        self._cards_layout.addStretch()
        self._scroll_area.setWidget(self._cards_widget)
        lay.addWidget(self._scroll_area)

        self._install_status = QLabel("Fetching available Python versions…")
        self._install_status.setStyleSheet(f"color:{FG_MUTED};font-size:11px;")
        lay.addWidget(self._install_status)

        # Download progress (hidden by default)
        self._dl_progress = QProgressBar()
        self._dl_progress.setRange(0, 100)
        self._dl_progress.setValue(0)
        self._dl_progress.setVisible(False)
        lay.addWidget(self._dl_progress)

        self._dl_status = QLabel("")
        self._dl_status.setStyleSheet(f"color:{FG_MUTED};font-size:11px;")
        self._dl_status.setVisible(False)
        lay.addWidget(self._dl_status)

        fetch_row = QHBoxLayout()
        self._fetch_btn = QPushButton("↺  Fetch Latest Versions")
        self._fetch_btn.clicked.connect(self._fetch_versions)
        fetch_row.addWidget(self._fetch_btn)
        fetch_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        fetch_row.addWidget(close_btn)
        lay.addLayout(fetch_row)

        # Kick off fetch
        self._fetch_versions()
        return w

    # ── Scan (Tab 1) ──────────────────────────────────────────────────────────
    def _start_scan(self):
        self._list.clear()
        self._scan_status.setText("Scanning for interpreters…")
        self._refresh_btn.setEnabled(False)
        self._select_btn.setEnabled(False)

        self._scan = _ScanThread(self)
        self._scan.done.connect(self._on_scan_done)
        self._scan.start()

    def _on_scan_done(self, infos: list):
        self._infos = infos
        self._list.clear()
        active = get_active_interpreter()

        best = _auto_select_best(infos)
        latest_ver = max((i.version_tuple for i in infos), default=(0,)) if infos else (0,)

        for info in infos:
            badges = []
            is_active = (os.path.realpath(info.path) == os.path.realpath(active))
            is_latest = (info.version_tuple == latest_ver)
            is_recommended = (best and os.path.realpath(info.path) == os.path.realpath(best.path))

            if is_active:
                badges.append("ACTIVE")
            if is_latest:
                badges.append("LATEST")
            if is_recommended:
                badges.append("RECOMMENDED")
            badges.append("INSTALLED")

            badge_str = "  ".join(f"[{b}]" for b in badges)
            label = f"{badge_str}  {info.label}" if badge_str else info.label
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, info.path)
            if is_active:
                item.setForeground(QColor("#00d4ff"))
            elif is_recommended:
                item.setForeground(QColor("#4ec9b0"))
            self._list.addItem(item)
            if is_active:
                self._list.setCurrentItem(item)

        count = len(infos)
        self._scan_status.setText(
            f"Found {count} interpreter{'s' if count != 1 else ''}."
        )
        self._refresh_btn.setEnabled(True)
        self._select_btn.setEnabled(True)

        # If install tab is open and has cards, refresh badge states
        if self._releases:
            self._render_version_cards()

    # ── Browse (Tab 1) ────────────────────────────────────────────────────────
    def _browse(self):
        if sys.platform == "win32":
            filt = "Python Executable (python.exe);;All files (*.*)"
        else:
            filt = "Python Executable (python3 python);;All files (*)"

        path, _ = QFileDialog.getOpenFileName(
            self, "Select Python Interpreter", "", filt
        )
        if not path:
            return

        ver = _probe_version(path)
        if not ver:
            QMessageBox.warning(
                self, "Invalid Interpreter",
                f"Could not verify Python version for:\n{path}"
            )
            return

        info = PythonInfo(path=path, version=ver, kind="custom")
        self._infos.append(info)
        item = QListWidgetItem(f"[CUSTOM]  {info.label}")
        item.setData(Qt.ItemDataRole.UserRole, info.path)
        self._list.addItem(item)
        self._list.setCurrentItem(item)

    # ── Confirm selection (Tab 1) ──────────────────────────────────────────────
    def _confirm_selection(self):
        item = self._list.currentItem()
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        Settings.instance().set("interpreter_path", path)
        self.interpreter_changed.emit(path)
        self.accept()

    # ── Fetch python.org versions (Tab 2) ─────────────────────────────────────
    def _fetch_versions(self):
        self._fetch_btn.setEnabled(False)
        self._install_status.setText("Fetching available Python versions from python.org…")

        # Clear cards
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._ver_thread = _VersionFetchThread(self)
        self._ver_thread.done.connect(self._on_versions_fetched)
        self._ver_thread.failed.connect(self._on_versions_failed)
        self._ver_thread.start()

    def _on_versions_fetched(self, releases: list):
        self._releases = releases
        self._fetch_btn.setEnabled(True)
        if not releases:
            self._install_status.setText(
                "No releases found. Check your internet connection."
            )
            return
        self._install_status.setText(
            f"Found {len(releases)} available release(s). "
            "Click Install to download and run the official installer."
        )
        self._render_version_cards()

    def _on_versions_failed(self, msg: str):
        self._fetch_btn.setEnabled(True)
        self._install_status.setText(
            f"Could not fetch versions: {msg}\n"
            "Check your internet connection and try again."
        )

    def _render_version_cards(self):
        """(Re-)build the version card list with current installed state."""
        # Remove existing cards (keep the trailing stretch)
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get installed version strings for comparison
        installed_vers = {info.version_tuple for info in self._infos}
        active_path = get_active_interpreter()
        active_ver = None
        for info in self._infos:
            if os.path.realpath(info.path) == os.path.realpath(active_path):
                active_ver = info.version_tuple
                break

        latest_tuple = self._releases[0].version_tuple if self._releases else (0,)

        for idx, release in enumerate(self._releases):
            card = self._make_version_card(release, installed_vers, active_ver, latest_tuple, idx == 0)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)

    def _make_version_card(self, release: PyOrgRelease,
                           installed_vers: set, active_ver,
                           latest_tuple: tuple, is_latest: bool) -> QFrame:
        """Build a single version card widget."""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(
            f"QFrame{{background:#2d2d2d;border:1px solid {BORDER};"
            f"border-radius:6px;padding:2px;}}"
        )

        row = QHBoxLayout(card)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(10)

        ver_lbl = QLabel(f"Python  {release.version}")
        ver_lbl.setStyleSheet("font-size:14px;font-weight:bold;color:#d4d4d4;"
                              "background:transparent;border:none;")
        row.addWidget(ver_lbl)

        # Compute badges
        badges = []
        is_installed = release.version_tuple in installed_vers
        is_active_ver = (active_ver == release.version_tuple)

        if is_active_ver:
            badges.append(("ACTIVE", "#00d4ff", "#0a2a3a"))
        if is_latest:
            badges.append(("LATEST", "#4ec9b0", "#0a2a1a"))
        if is_latest and not is_installed:
            badges.append(("RECOMMENDED", "#c586c0", "#2a1a2a"))
        if is_installed:
            badges.append(("INSTALLED", "#4d9e4d", "#0a1a0a"))

        for badge_text, fg_col, bg_col in badges:
            blbl = QLabel(badge_text)
            blbl.setStyleSheet(
                f"color:{fg_col};background:{bg_col};"
                f"border:1px solid {fg_col};"
                f"border-radius:3px;padding:2px 7px;"
                f"font-size:10px;font-weight:bold;"
            )
            row.addWidget(blbl)

        row.addStretch()

        if not release.url_64 and not release.url_32:
            na_lbl = QLabel("No installer available")
            na_lbl.setStyleSheet(f"color:{FG_MUTED};background:transparent;border:none;")
            row.addWidget(na_lbl)
        else:
            url_to_use = release.url_64 or release.url_32
            arch_label = "64-bit" if release.url_64 else "32-bit"

            if is_installed and not is_latest:
                btn_label = f"⬆  Update/Reinstall  ({arch_label})"
                btn_obj   = "run_btn"
            elif is_installed:
                btn_label = f"↺  Reinstall  ({arch_label})"
                btn_obj   = ""
            else:
                btn_label = f"⬇  Install  ({arch_label})"
                btn_obj   = "run_btn" if is_latest else ""

            btn = QPushButton(btn_label)
            if btn_obj:
                btn.setObjectName(btn_obj)
            btn.setFixedHeight(28)
            btn.clicked.connect(
                lambda checked=False, u=url_to_use, v=release.version:
                    self._start_install(u, v)
            )
            row.addWidget(btn)

            # 32-bit option if 64-bit is the default
            if release.url_64 and release.url_32:
                btn32 = QPushButton("32-bit")
                btn32.setFixedHeight(28)
                btn32.setToolTip(f"Install Python {release.version} 32-bit")
                btn32.clicked.connect(
                    lambda checked=False, u=release.url_32, v=release.version:
                        self._start_install(u, v)
                )
                row.addWidget(btn32)

        return card

    # ── Download + Install (Tab 2) ─────────────────────────────────────────────
    def _start_install(self, url: str, version: str):
        if self._dl_thread and self._dl_thread.isRunning():
            QMessageBox.information(
                self, "Download in Progress",
                "A download is already running. Please wait for it to finish."
            )
            return

        reply = QMessageBox.question(
            self, "Install Python",
            f"Download and install Python {version} from python.org?\n\n"
            f"The official Python installer will launch automatically.\n"
            f"It will add Python to PATH and install for all users.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._dl_progress.setValue(0)
        self._dl_progress.setVisible(True)
        self._dl_status.setText(f"Downloading Python {version}…")
        self._dl_status.setVisible(True)
        self._fetch_btn.setEnabled(False)

        self._dl_thread = _InstallerDownloadThread(url, self)
        self._dl_thread.progress.connect(self._on_dl_progress)
        self._dl_thread.finished_ok.connect(
            lambda path, v=version: self._on_dl_done(path, v)
        )
        self._dl_thread.failed.connect(self._on_dl_failed)
        self._dl_thread.start()

    def _on_dl_progress(self, pct: int):
        self._dl_progress.setValue(pct)
        self._dl_status.setText(f"Downloading… {pct}%")

    def _on_dl_done(self, path: str, version: str):
        self._dl_progress.setValue(100)
        self._dl_status.setText(f"Download complete — launching Python {version} installer…")
        self._fetch_btn.setEnabled(True)

        if not os.path.isfile(path):
            self._dl_status.setText("Error: downloaded installer not found.")
            return

        try:
            subprocess.Popen(
                [path, "InstallAllUsers=1", "PrependPath=1"],
                shell=False
            )
        except Exception as exc:
            QMessageBox.warning(
                self, "Launch Error",
                f"Could not launch installer:\n{exc}\n\n"
                f"You can run it manually:\n{path}"
            )
            return

        QMessageBox.information(
            self, "Installer Launched",
            f"Python {version} installer has been launched.\n\n"
            f"After installation completes, click '↺ Refresh' in the\n"
            f"'Select Interpreter' tab to detect the new Python."
        )
        self._dl_status.setText(f"Python {version} installer launched successfully.")

        # Auto-refresh interpreter list after a delay
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, self._start_scan)

    def _on_dl_failed(self, msg: str):
        self._dl_progress.setVisible(False)
        self._dl_status.setText(f"Download failed: {msg}")
        self._dl_status.setVisible(True)
        self._fetch_btn.setEnabled(True)
        QMessageBox.warning(
            self, "Download Failed",
            f"Could not download the installer:\n{msg}\n\n"
            "Check your internet connection and try again."
        )
