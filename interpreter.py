# interpreter.py — Python interpreter manager for CodeZen India
#
# Public API
# ──────────
#   get_active_interpreter()         → str  (path to use for running scripts)
#   find_interpreters()              → list[PythonInfo]
#   InterpreterManagerDialog(parent) → modal dialog for selection

import os
import subprocess
import sys
import shutil
from dataclasses import dataclass, field
from typing import ClassVar

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QFileDialog, QWidget, QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from settings import Settings
from theme import BG_PANEL, FG_TEXT, FG_MUTED, BORDER, BG_HOVER


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
        # output is either "Python 3.11.4" or on stderr for old Pythons
        if out.startswith("Python"):
            return out
        return out[:40] if out else ""
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Interpreter discovery
# ─────────────────────────────────────────────────────────────────────────────
def find_interpreters() -> list[PythonInfo]:
    """
    Scan for Python interpreters.  Returns a deduplicated, sorted list.
    Order: current sys.executable first, then PATH candidates, then
    discovered venvs from common project locations, then Conda envs.
    """
    seen: set[str] = set()
    results: list[PythonInfo] = []

    def _add(path: str, kind: str = "system"):
        real = os.path.realpath(path)
        if real in seen or not os.path.isfile(path):
            return
        seen.add(real)
        ver = _probe_version(path)
        if ver:
            results.append(PythonInfo(path=path, version=ver, kind=kind))

    # 1. Current interpreter (skip if frozen — it's the IDE itself)
    if not getattr(sys, "frozen", False):
        _add(sys.executable)

    # 2. PATH candidates
    for name in ("python3", "python", "python3.13", "python3.12",
                 "python3.11", "python3.10", "python3.9"):
        found = shutil.which(name)
        if found:
            _add(found)

    # 3. Windows-style common install paths
    if sys.platform == "win32":
        for base in (r"C:\Python313", r"C:\Python312", r"C:\Python311",
                     r"C:\Python310", r"C:\Python39"):
            _add(os.path.join(base, "python.exe"))
        # Windows Store Python locations
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            pkgs = os.path.join(local_app, "Programs", "Python")
            if os.path.isdir(pkgs):
                for d in os.listdir(pkgs):
                    _add(os.path.join(pkgs, d, "python.exe"))

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
        for subdir in os.listdir(base)[:40]:   # cap scan depth
            for venv_name in (".venv", "venv", "env", ".env"):
                # Direct match — the subdir IS the venv (e.g. ~/projects/.venv)
                if subdir == venv_name:
                    venv_root = os.path.join(base, subdir)
                else:
                    # Nested — the venv lives inside the subdir (e.g. ~/projects/myapp/.venv)
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
        "/opt/anaconda3",
        "/opt/miniconda3",
        "/usr/local/anaconda3",
    ]
    for conda_base in conda_base_candidates:
        if not os.path.isdir(conda_base):
            continue
        # base env
        _exe = os.path.join(
            conda_base,
            "python.exe" if sys.platform == "win32" else "bin/python3"
        )
        _add(_exe, kind="conda")
        # named envs
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
# Public helper
# ─────────────────────────────────────────────────────────────────────────────
def get_active_interpreter() -> str:
    """
    Return the interpreter path that should be used for running scripts.
    Priority:
      1. User-selected path saved in settings.json (if still valid)
      2. sys.executable (if not frozen)
      3. python3 / python from PATH
    """
    cfg = Settings.instance()
    saved = cfg.get("interpreter_path", "")
    if saved and os.path.isfile(saved):
        return saved

    if not getattr(sys, "frozen", False):
        exe = sys.executable or ""
        if exe and os.path.isfile(exe):
            name_lower = os.path.basename(exe).lower()
            _ide_names = {"main", "main.exe", "codezen", "codezen.exe",
                          "codezenindia", "codezenindia.exe"}
            if name_lower not in _ide_names:
                return exe

    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            return found

    return "python3"


# ─────────────────────────────────────────────────────────────────────────────
# Discovery thread (keeps UI responsive)
# ─────────────────────────────────────────────────────────────────────────────
class _ScanThread(QThread):
    done = pyqtSignal(list)

    def run(self):
        self.done.emit(find_interpreters())


# ─────────────────────────────────────────────────────────────────────────────
# InterpreterManagerDialog
# ─────────────────────────────────────────────────────────────────────────────
class InterpreterManagerDialog(QDialog):
    """
    Displays all detected interpreters.  The user can select one, browse for
    a custom path, or refresh the list.  Selection is persisted to settings.json.
    """

    interpreter_changed = pyqtSignal(str)   # emits the new interpreter path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Python Interpreter")
        self.setMinimumSize(580, 400)
        self.setModal(True)
        self._infos: list[PythonInfo] = []
        self._build_ui()
        self._start_scan()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 16, 16, 16)

        hdr = QLabel("Python Interpreter")
        hdr.setStyleSheet("font-size:15px; font-weight:bold; color:#d4d4d4;")
        root.addWidget(hdr)

        sub = QLabel(
            "Select the Python interpreter used when running scripts in the IDE."
        )
        sub.setStyleSheet(f"color:{FG_MUTED}; font-size:11px;")
        sub.setWordWrap(True)
        root.addWidget(sub)

        self._list = QListWidget()
        self._list.setStyleSheet(
            f"QListWidget{{background:{BG_PANEL};border:1px solid {BORDER};"
            f"border-radius:4px;color:{FG_TEXT};}}"
            f"QListWidget::item{{padding:8px 12px;border-bottom:1px solid #1e1e1e;}}"
            f"QListWidget::item:selected{{background:{BG_HOVER};color:#fff;}}"
        )
        mono = QFont("Consolas", 11)
        mono.setFixedPitch(True)
        self._list.setFont(mono)
        root.addWidget(self._list)

        self._status = QLabel("Scanning for interpreters…")
        self._status.setStyleSheet(f"color:{FG_MUTED}; font-size:11px;")
        root.addWidget(self._status)

        # Bottom button row
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
        btns.addWidget(self._select_btn)
        root.addLayout(btns)

    # ── Scan ──────────────────────────────────────────────────────────────────
    def _start_scan(self):
        self._list.clear()
        self._status.setText("Scanning for interpreters…")
        self._refresh_btn.setEnabled(False)
        self._select_btn.setEnabled(False)

        self._scan = _ScanThread(self)
        self._scan.done.connect(self._on_scan_done)
        self._scan.start()

    def _on_scan_done(self, infos: list):
        self._infos = infos
        self._list.clear()
        active = get_active_interpreter()

        for info in infos:
            item = QListWidgetItem(info.label)
            item.setData(Qt.ItemDataRole.UserRole, info.path)
            self._list.addItem(item)
            if os.path.realpath(info.path) == os.path.realpath(active):
                self._list.setCurrentItem(item)

        count = len(infos)
        self._status.setText(
            f"Found {count} interpreter{'s' if count != 1 else ''}."
        )
        self._refresh_btn.setEnabled(True)
        self._select_btn.setEnabled(True)

    # ── Browse ────────────────────────────────────────────────────────────────
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
        item = QListWidgetItem(info.label)
        item.setData(Qt.ItemDataRole.UserRole, info.path)
        self._list.addItem(item)
        self._list.setCurrentItem(item)

    # ── Confirm ───────────────────────────────────────────────────────────────
    def _confirm_selection(self):
        item = self._list.currentItem()
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        Settings.instance().set("interpreter_path", path)
        self.interpreter_changed.emit(path)
        self.accept()
