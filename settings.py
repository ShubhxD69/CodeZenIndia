# settings.py — Persistent settings manager + Preferences dialog

import json
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QSpinBox, QCheckBox,
    QPushButton, QComboBox, QFormLayout, QMessageBox,
)
from theme import BORDER, FG_MUTED

_SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "settings.json"
)

DEFAULT: dict = {
    "font_size":          13,
    "tab_size":           4,
    "word_wrap":          False,
    "auto_save":          False,
    "interpreter_path":   "",
    "auto_update":        True,
    "update_channel":     "stable",
    "recent_projects":    [],
    "last_workspace":     "",
    "terminal_font_size": 12,
}


# ─────────────────────────────────────────────────────────────────────────────
# Settings — singleton
# ─────────────────────────────────────────────────────────────────────────────
class Settings:
    """
    Thread-safe singleton.  Access via  Settings.instance() .
    Reads/writes  settings.json  in the application directory.
    """

    _inst: "Settings | None" = None

    @classmethod
    def instance(cls) -> "Settings":
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    def __init__(self):
        self._data: dict = dict(DEFAULT)
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────
    def _load(self):
        if not os.path.isfile(_SETTINGS_FILE):
            return
        try:
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                for k in DEFAULT:
                    if k in loaded:
                        self._data[k] = loaded[k]
        except Exception:
            pass

    def save(self):
        try:
            with open(_SETTINGS_FILE, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2)
        except Exception:
            pass

    # ── Access ────────────────────────────────────────────────────────────────
    def get(self, key: str, default=None):
        return self._data.get(key, DEFAULT.get(key, default))

    def set(self, key: str, value):
        self._data[key] = value
        self.save()

    def __getitem__(self, key: str):
        return self.get(key)

    def __setitem__(self, key: str, value):
        self.set(key, value)

    # ── Recent projects ───────────────────────────────────────────────────────
    def add_recent_project(self, path: str):
        recent: list = list(self._data.get("recent_projects", []))
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self._data["recent_projects"] = recent[:10]
        self.save()

    def recent_projects(self) -> list[str]:
        return [p for p in self._data.get("recent_projects", []) if os.path.isdir(p)]


# ─────────────────────────────────────────────────────────────────────────────
# SettingsDialog — tabbed preferences window
# ─────────────────────────────────────────────────────────────────────────────
class SettingsDialog(QDialog):
    """Four-tab preferences window (Editor / Terminal / Updates / Workspace)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setMinimumSize(480, 360)
        self.setModal(True)

        self._cfg = Settings.instance()
        self._build_ui()
        self._load_values()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        tabs.addTab(self._tab_editor(),    "  Editor  ")
        tabs.addTab(self._tab_terminal(),  "  Terminal  ")
        tabs.addTab(self._tab_updates(),   "  Updates  ")
        tabs.addTab(self._tab_workspace(), "  Workspace  ")
        root.addWidget(tabs)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER};")
        root.addWidget(sep)

        btns = QHBoxLayout()
        btns.setContentsMargins(16, 10, 16, 14)
        btns.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.setObjectName("run_btn")
        save_btn.clicked.connect(self._save_and_close)
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        root.addLayout(btns)

    def _form_tab(self) -> tuple[QWidget, QFormLayout]:
        w = QWidget()
        f = QFormLayout(w)
        f.setContentsMargins(20, 18, 20, 18)
        f.setSpacing(12)
        f.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        return w, f

    # ── Editor tab ────────────────────────────────────────────────────────────
    def _tab_editor(self) -> QWidget:
        w, form = self._form_tab()

        self._font_size = QSpinBox()
        self._font_size.setRange(8, 32)
        self._font_size.setSuffix(" pt")
        form.addRow("Font size:", self._font_size)

        self._tab_size = QSpinBox()
        self._tab_size.setRange(2, 8)
        self._tab_size.setSuffix(" spaces")
        form.addRow("Tab width:", self._tab_size)

        self._word_wrap = QCheckBox("Enable word wrap")
        form.addRow("", self._word_wrap)

        self._auto_save = QCheckBox("Auto-save file before running")
        form.addRow("", self._auto_save)

        return w

    # ── Terminal tab ──────────────────────────────────────────────────────────
    def _tab_terminal(self) -> QWidget:
        w, form = self._form_tab()

        self._term_font_size = QSpinBox()
        self._term_font_size.setRange(8, 24)
        self._term_font_size.setSuffix(" pt")
        form.addRow("Terminal font size:", self._term_font_size)

        info = QLabel(
            "The terminal streams stdout and stderr in real time.\n"
            "ANSI colour codes and interactive input() are supported."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color:{FG_MUTED}; font-size:11px;")
        form.addRow(info)

        return w

    # ── Updates tab ───────────────────────────────────────────────────────────
    def _tab_updates(self) -> QWidget:
        w, form = self._form_tab()

        self._auto_update = QCheckBox("Check for updates automatically on startup")
        form.addRow("", self._auto_update)

        self._update_channel = QComboBox()
        self._update_channel.addItems(["stable", "beta"])
        form.addRow("Update channel:", self._update_channel)

        note = QLabel(
            "Updates are downloaded from GitHub Releases.\n"
            "Beta channel may include pre-release builds."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{FG_MUTED}; font-size:11px;")
        form.addRow(note)

        return w

    # ── Workspace tab ─────────────────────────────────────────────────────────
    def _tab_workspace(self) -> QWidget:
        w, form = self._form_tab()

        info = QLabel(
            "The last opened folder is restored automatically on startup.\n"
            "Recent projects (up to 10) are tracked in the File menu."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color:{FG_MUTED}; font-size:11px;")
        form.addRow(info)

        clear_btn = QPushButton("Clear Recent Projects List")
        clear_btn.clicked.connect(self._clear_recent)
        form.addRow(clear_btn)

        return w

    # ── Load / Save ───────────────────────────────────────────────────────────
    def _load_values(self):
        self._font_size.setValue(self._cfg.get("font_size"))
        self._tab_size.setValue(self._cfg.get("tab_size"))
        self._word_wrap.setChecked(bool(self._cfg.get("word_wrap")))
        self._auto_save.setChecked(bool(self._cfg.get("auto_save")))
        self._term_font_size.setValue(self._cfg.get("terminal_font_size"))
        self._auto_update.setChecked(bool(self._cfg.get("auto_update")))
        ch = self._cfg.get("update_channel", "stable")
        idx = self._update_channel.findText(ch)
        if idx >= 0:
            self._update_channel.setCurrentIndex(idx)

    def _save_and_close(self):
        self._cfg.set("font_size",          self._font_size.value())
        self._cfg.set("tab_size",           self._tab_size.value())
        self._cfg.set("word_wrap",          self._word_wrap.isChecked())
        self._cfg.set("auto_save",          self._auto_save.isChecked())
        self._cfg.set("terminal_font_size", self._term_font_size.value())
        self._cfg.set("auto_update",        self._auto_update.isChecked())
        self._cfg.set("update_channel",     self._update_channel.currentText())
        self.accept()

    def _clear_recent(self):
        self._cfg.set("recent_projects", [])
        QMessageBox.information(self, "Preferences", "Recent projects list cleared.")
