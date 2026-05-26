# main_window.py — MainWindow for CodeZen India
#
# Wires together: menu bar, toolbar, explorer dock, editor tabs,
#                 output-terminal dock, status bar, settings, interpreter,
#                 updater, and workspace persistence.

import os
import sys

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QDockWidget, QToolBar,
    QLabel, QFileDialog, QMessageBox, QDialog,
    QVBoxLayout, QHBoxLayout, QPushButton,
    QSizePolicy, QLineEdit, QGridLayout, QMenu,
)
from PyQt6.QtCore import Qt, QSize, QUrl, QPoint, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QTextCursor, QIcon, QDesktopServices

from editor   import EditorTabWidget, CodeEditor
from explorer import FileExplorer
from terminal import Terminal
from theme    import BG_PANEL, FG_MUTED, FG_WHITE, BORDER
from settings import Settings, SettingsDialog
from updater import check_for_updates


def _resource(relative: str) -> str:
    """Resolve a bundled-asset path for both script and PyInstaller EXE."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


APP_NAME    = "CodeZen India"
APP_VERSION = "1.1.0"
DEVELOPER   = "Developed By Shubh Mishra"


# ─────────────────────────────────────────────────────────────────────────────
# _StatusBarLabel — proper QLabel subclass for interactive status-bar items
#
# WHY a subclass instead of monkey-patched lambdas?
#   PyQt6/SIP raises  TypeError: invalid argument to sipBadCatcherResult()
#   when enterEvent / leaveEvent overrides are plain lambdas, because SIP
#   validates the C++ return type of virtual overrides at runtime.
#   A proper subclass with explicit super() calls satisfies that contract.
# ─────────────────────────────────────────────────────────────────────────────
class _StatusBarLabel(QLabel):
    """
    Status-bar QLabel with pointing-hand cursor, hover stylesheet swap,
    and a left-click action.  All Qt event overrides call super() so SIP
    never sees an unexpected return value.
    """

    def __init__(self, text: str, style_normal: str, style_hover: str,
                 on_click=None, parent=None):
        super().__init__(text, parent)
        self._style_normal = style_normal
        self._style_hover  = style_hover
        self._on_click     = on_click
        self.setStyleSheet(style_normal)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_click_handler(self, fn):
        self._on_click = fn

    def mousePressEvent(self, event):          # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._on_click:
            self._on_click()
        super().mousePressEvent(event)

    def enterEvent(self, event):               # noqa: N802
        self.setStyleSheet(self._style_hover)
        super().enterEvent(event)

    def leaveEvent(self, event):               # noqa: N802
        self.setStyleSheet(self._style_normal)
        super().leaveEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
# About Dialog
# ─────────────────────────────────────────────────────────────────────────────
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setFixedSize(360, 280)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 20)
        layout.setSpacing(10)

        for text, style in (
            ("< / >",
             "color:#00b4d8;font-family:Consolas;font-size:32px;font-weight:bold;"),
            (APP_NAME,
             "color:#ffffff;font-size:20px;font-weight:bold;"),
            (f"Version {APP_VERSION}",
             "color:#858585;font-size:12px;"),
        ):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(style)
            layout.addWidget(lbl)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER};")
        layout.addWidget(sep)

        for text, style in (
            (DEVELOPER,       "color:#aaaaaa;font-size:13px;"),
            ("Professional Python IDE", "color:#555;font-size:11px;"),
        ):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(style)
            layout.addWidget(lbl)

        layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close_btn)
        row.addStretch()
        layout.addLayout(row)


# ─────────────────────────────────────────────────────────────────────────────
# Find / Replace Dialog
# ─────────────────────────────────────────────────────────────────────────────
class FindReplaceDialog(QDialog):
    def __init__(self, tabs: EditorTabWidget, parent=None):
        super().__init__(parent)
        self._tabs = tabs
        self.setWindowTitle("Find / Replace")
        self.setFixedSize(460, 170)

        grid = QGridLayout(self)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(8)

        grid.addWidget(QLabel("Find:"), 0, 0)
        self._find = QLineEdit()
        self._find.setPlaceholderText("Search text…")
        grid.addWidget(self._find, 0, 1)

        grid.addWidget(QLabel("Replace:"), 1, 0)
        self._repl = QLineEdit()
        self._repl.setPlaceholderText("Replacement text…")
        grid.addWidget(self._repl, 1, 1)

        btns = QHBoxLayout()
        for label, slot in (
            ("Find Next",   self._find_next),
            ("Replace",     self._replace_one),
            ("Replace All", self._replace_all),
            ("Close",       self.close),
        ):
            b = QPushButton(label)
            b.clicked.connect(slot)
            btns.addWidget(b)
        grid.addLayout(btns, 2, 0, 1, 2)

        self._find.setFocus()
        self._find.returnPressed.connect(self._find_next)

    def _editor(self) -> "CodeEditor | None":
        return self._tabs.current_editor()

    def _find_next(self):
        ed = self._editor()
        if not ed:
            return
        query = self._find.text()
        if not query:
            return
        if not ed.find(query):
            c = ed.textCursor()
            c.movePosition(QTextCursor.MoveOperation.Start)
            ed.setTextCursor(c)
            ed.find(query)

    def _replace_one(self):
        ed = self._editor()
        if not ed:
            return
        c = ed.textCursor()
        if c.hasSelection() and c.selectedText() == self._find.text():
            c.insertText(self._repl.text())
        self._find_next()

    def _replace_all(self):
        ed = self._editor()
        if not ed:
            return
        query = self._find.text()
        if not query:
            return
        content = ed.toPlainText()
        count   = content.count(query)
        if count:
            ed.setPlainText(content.replace(query, self._repl.text()))
            QMessageBox.information(
                self, "Replace All", f"Replaced {count} occurrence(s)."
            )
        else:
            QMessageBox.information(self, "Replace All", "No matches found.")


# ─────────────────────────────────────────────────────────────────────────────
# MainWindow
# ─────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 800)

        self._cfg      = Settings.instance()
        self._prev_ed: CodeEditor | None = None
        self._update_thread  = None   # keep reference so GC doesn't kill thread
        self._interp_scan    = None   # background interpreter scan thread
        self._cached_interpreters: list = []   # populated by background scan

        _icon_path = _resource("assets/icons/logo.ico")
        if os.path.isfile(_icon_path):
            self.setWindowIcon(QIcon(_icon_path))

        self._setup_central()
        self._setup_explorer_dock()
        self._setup_terminal_dock()
        self._setup_menubar()
        self._setup_toolbar()
        self._setup_statusbar()
        from interpreter import get_active_interpreter
        self._active_interpreter = get_active_interpreter()
        self._connect_signals()
        self._restore_workspace()
        # Kick off a background scan to populate the interpreter cache
        # (delayed 800 ms so the window finishes painting first)
        QTimer.singleShot(800, self._start_interpreter_cache_scan)

    # ── Layout ────────────────────────────────────────────────────────────────
    def _setup_central(self):
        self._tabs = EditorTabWidget()
        self.setCentralWidget(self._tabs)

    def _setup_explorer_dock(self):
        self._explorer = FileExplorer()
        dock = QDockWidget("Explorer", self)
        dock.setObjectName("ExplorerDock")
        dock.setWidget(self._explorer)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self._explorer_dock = dock
        self._explorer.setMinimumWidth(200)

    def _setup_terminal_dock(self):
        self._terminal = Terminal()
        dock = QDockWidget("Output", self)
        dock.setObjectName("TerminalDock")
        dock.setWidget(self._terminal)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea
            | Qt.DockWidgetArea.TopDockWidgetArea
        )
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        dock.setMinimumHeight(160)
        self._terminal_dock = dock

    # ── Menu bar ──────────────────────────────────────────────────────────────
    def _setup_menubar(self):
        mb = self.menuBar()

        # ── File ──────────────────────────────────────────────────────────────
        fm = mb.addMenu("&File")
        self._act(fm, "New File",      "Ctrl+N",       lambda: self._tabs.new_file())
        self._act(fm, "Open File…",    "Ctrl+O",       self._open_file)
        self._act(fm, "Open Folder…",  None,           self._open_folder)
        fm.addSeparator()
        self._act(fm, "Save",          "Ctrl+S",       self._save)
        self._act(fm, "Save As…",      "Ctrl+Shift+S", self._save_as)
        fm.addSeparator()

        # Recent projects sub-menu
        self._recent_menu = fm.addMenu("Recent Projects")
        self._rebuild_recent_menu()
        fm.addSeparator()
        self._act(fm, "Quit", "Ctrl+Q", self.close)

        # ── Edit ──────────────────────────────────────────────────────────────
        em = mb.addMenu("&Edit")
        self._act(em, "Undo",           "Ctrl+Z",  lambda: self._fwd(lambda e: e.undo()))
        self._act(em, "Redo",           "Ctrl+Y",  lambda: self._fwd(lambda e: e.redo()))
        em.addSeparator()
        self._act(em, "Cut",            "Ctrl+X",  lambda: self._fwd(lambda e: e.cut()))
        self._act(em, "Copy",           "Ctrl+C",  lambda: self._fwd(lambda e: e.copy()))
        self._act(em, "Paste",          "Ctrl+V",  lambda: self._fwd(lambda e: e.paste()))
        self._act(em, "Select All",     "Ctrl+A",  lambda: self._fwd(lambda e: e.selectAll()))
        em.addSeparator()
        self._act(em, "Find / Replace…","Ctrl+H",  self._find_replace)
        em.addSeparator()
        self._act(em, "Python Interpreter…", None, self._open_interpreter_manager)
        self._act(em, "Preferences…",        "Ctrl+,", self._open_settings)

        # ── View ──────────────────────────────────────────────────────────────
        vm = mb.addMenu("&View")
        self._act(vm, "Toggle Explorer",     "Ctrl+B",
                  lambda: self._explorer_dock.setVisible(
                      not self._explorer_dock.isVisible()))
        self._act(vm, "Toggle Output Panel", "Ctrl+J",
                  lambda: self._terminal_dock.setVisible(
                      not self._terminal_dock.isVisible()))

        # ── Run ───────────────────────────────────────────────────────────────
        rm = mb.addMenu("&Run")
        self._act(rm, "Run File",  "F5",       self._run_file)
        self._act(rm, "Stop",      "Shift+F5", self._terminal.stop)
        rm.addSeparator()
        self._act(rm, "Select Python Interpreter…", None, self._open_interpreter_manager)

        # ── Help ──────────────────────────────────────────────────────────────
        hm = mb.addMenu("&Help")
        self._act(hm, "Check for Updates…", None, self._check_updates_manual)
        hm.addSeparator()
        self._act(hm, f"About {APP_NAME}", None, self._show_about)

    def _act(self, menu, label: str, shortcut: str | None, slot) -> QAction:
        a = QAction(label, self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        a.triggered.connect(slot)
        menu.addAction(a)
        return a

    def _fwd(self, fn):
        ed = self._tabs.current_editor()
        if ed:
            fn(ed)

    # ── Toolbar ───────────────────────────────────────────────────────────────
    def _setup_toolbar(self):
        tb = QToolBar("Main Toolbar", self)
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(tb)

        def add(label: str, tip: str, slot):
            a = QAction(label, self)
            a.setToolTip(tip)
            a.triggered.connect(slot)
            tb.addAction(a)

        add("  New",    "New File  (Ctrl+N)",         lambda: self._tabs.new_file())
        add("  Open",   "Open File  (Ctrl+O)",         self._open_file)
        add("  Folder", "Open Folder",                 self._open_folder)
        add("  Save",   "Save  (Ctrl+S)",              self._save)
        tb.addSeparator()
        add("▶  Run",   "Run Python file  (F5)",       self._run_file)
        add("■  Stop",  "Stop execution  (Shift+F5)",  self._terminal.stop)
        tb.addSeparator()
        add("  Find",   "Find / Replace  (Ctrl+H)",    self._find_replace)
        add("⚙  Settings", "Preferences  (Ctrl+,)",   self._open_settings)
        add("  About",  f"About {APP_NAME}",           self._show_about)

    # ── Status bar ────────────────────────────────────────────────────────────
    def _setup_statusbar(self):
        sb = self.statusBar()

        self._sb_file = QLabel("No file open")
        self._sb_file.setStyleSheet(f"color:{FG_WHITE}; padding:0 8px;")
        sb.addWidget(self._sb_file)

        stretch = QWidget()
        stretch.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        sb.addWidget(stretch, 1)

        self._sb_pos = QLabel("Ln 1, Col 1")
        self._sb_pos.setStyleSheet(f"color:{FG_WHITE}; padding:0 8px;")
        sb.addPermanentWidget(self._sb_pos)

        # Interpreter label — single click opens quick-select menu
        self._sb_interp = _StatusBarLabel(
            "",
            style_normal=(
                f"color:{FG_WHITE};"
                "padding:0 10px;"
                "font-size:12px;"
            ),
            style_hover=(
                "color:#00d4ff;"
                "padding:0 10px;"
                "font-size:12px;"
                "background:rgba(0,180,216,0.10);"
                "border-radius:3px;"
            ),
            on_click=self._show_interpreter_quick_menu,
        )
        self._sb_interp.setToolTip(
            "Active Python interpreter — click to switch"
        )
        sb.addPermanentWidget(self._sb_interp)
        self._refresh_interpreter_label()

        # Subtle vertical separator before branding pill
        _sep = QLabel(" │ ")
        _sep.setStyleSheet(
            "color:rgba(255,255,255,0.22); font-size:14px; padding:0 2px;"
        )
        sb.addPermanentWidget(_sep)

        # Branding pill — clicking opens developer GitHub in default browser
        _BRAND_URL    = "https://github.com/ShubhxD69"
        brand = _StatusBarLabel(
            f"  {DEVELOPER}  ",
            style_normal=(
                "color:#00d4ff;"
                "font-size:11px;"
                "font-weight:600;"
                "background:rgba(0,122,204,0.18);"
                "border:1px solid rgba(0,180,216,0.35);"
                "border-radius:3px;"
                "padding:1px 8px;"
                "margin:2px 6px 2px 0px;"
            ),
            style_hover=(
                "color:#33e8ff;"
                "font-size:11px;"
                "font-weight:600;"
                "background:rgba(0,150,220,0.28);"
                "border:1px solid rgba(0,210,255,0.6);"
                "border-radius:3px;"
                "padding:1px 8px;"
                "margin:2px 6px 2px 0px;"
                "text-decoration:underline;"
            ),
            on_click=lambda: QDesktopServices.openUrl(QUrl(_BRAND_URL)),
        )
        brand.setToolTip(f"Visit developer profile\n{_BRAND_URL}")
        sb.addPermanentWidget(brand)

    def _refresh_interpreter_label(self):
        try:
            from interpreter import get_active_interpreter, _probe_version, PythonInfo
            path = get_active_interpreter()

            # Try cached interpreters first (no subprocess cost)
            friendly = None
            for info in self._cached_interpreters:
                if os.path.realpath(info.path) == os.path.realpath(path):
                    friendly = self._format_interp_name(info)
                    break

            # Cache miss — probe once and format
            if not friendly:
                ver = _probe_version(path)  # "Python 3.11.4"
                if ver:
                    friendly = ver          # e.g. "Python 3.11.4"
                else:
                    friendly = "Python"

            self._sb_interp.setText(f"🐍  {friendly}")
            self._sb_interp.setToolTip(
                f"Active interpreter: {path}\nClick to switch"
            )
        except Exception:
            self._sb_interp.setText("🐍  Python")

    @staticmethod
    def _format_interp_name(info) -> str:
        """Return a clean display name from a PythonInfo, e.g. 'Python 3.11.4 (System)'."""
        kind_labels = {
            "system": "System",
            "venv":   "Venv",
            "conda":  "Conda",
            "custom": "Custom",
        }
        ver = info.version or "Python"
        kind = kind_labels.get(info.kind, "")
        return f"{ver} ({kind})" if kind else ver

    # ── Background interpreter cache scan ─────────────────────────────────────
    def _start_interpreter_cache_scan(self):
        try:
            from interpreter import _ScanThread
            self._interp_scan = _ScanThread(self)
            self._interp_scan.done.connect(self._on_cache_scan_done)
            self._interp_scan.start()
        except Exception:
            pass

    def _on_cache_scan_done(self, infos: list):
        self._cached_interpreters = infos
        # Refresh the label now that we have friendly version data
        self._refresh_interpreter_label()

    # ── Quick-select interpreter popup menu ───────────────────────────────────
    def _show_interpreter_quick_menu(self):
        """
        Show a lightweight QMenu listing available interpreters.
        Appears just above the status-bar interpreter label.
        Inspired by VS Code / PyCharm interpreter picker.
        """
        from interpreter import get_active_interpreter

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu {"
            "  background:#252526;"
            "  border:1px solid #474747;"
            "  border-radius:5px;"
            "  padding:4px 0;"
            "}"
            "QMenu::item {"
            "  color:#d4d4d4;"
            "  padding:7px 16px 7px 14px;"
            "  font-size:12px;"
            "}"
            "QMenu::item:selected {"
            "  background:#094771;"
            "  color:#ffffff;"
            "}"
            "QMenu::item:disabled {"
            "  color:#555555;"
            "}"
            "QMenu::separator {"
            "  height:1px;"
            "  background:#474747;"
            "  margin:4px 0;"
            "}"
        )

        active_path = get_active_interpreter()

        if self._cached_interpreters:
            for info in self._cached_interpreters:
                is_active = (
                    os.path.realpath(info.path) == os.path.realpath(active_path)
                )
                label = self._format_interp_name(info)
                if is_active:
                    display = f"✓  {label}"
                else:
                    display = f"    {label}"

                action = menu.addAction(display)
                if is_active:
                    action.setEnabled(True)
                    # Bold the active item via rich-text trick in tooltip
                    action.setToolTip(info.path)
                else:
                    action.setToolTip(info.path)

                # Capture path for the slot
                action.triggered.connect(
                    lambda checked=False, p=info.path: self._quick_select_interpreter(p)
                )
        else:
            # Cache not ready yet — show a placeholder while scanning
            placeholder = menu.addAction("  Scanning…")
            placeholder.setEnabled(False)

        menu.addSeparator()
        manage_action = menu.addAction("⚙  Manage Interpreters…")
        manage_action.triggered.connect(self._open_interpreter_manager)

        # Position the menu just above the interpreter label in the status bar
        label_pos  = self._sb_interp.mapToGlobal(QPoint(0, 0))
        label_h    = self._sb_interp.height()
        menu_hint  = menu.sizeHint()
        popup_pos  = QPoint(
            label_pos.x(),
            label_pos.y() - menu_hint.height() - 4
        )
        menu.exec(popup_pos)

    def _quick_select_interpreter(self, path: str):
        """Persist a new interpreter chosen from the quick menu."""
        from interpreter import get_active_interpreter
        if os.path.realpath(path) == os.path.realpath(get_active_interpreter()):
            return   # already active — nothing to do

        Settings.instance().set("interpreter_path", path)
        self._refresh_interpreter_label()

        # Find the friendly name for the status-bar toast
        name = path
        for info in self._cached_interpreters:
            if os.path.realpath(info.path) == os.path.realpath(path):
                name = self._format_interp_name(info)
                break
        self.statusBar().showMessage(f"Interpreter switched to: {name}", 4000)

    # ── Signal wiring ─────────────────────────────────────────────────────────
    def _connect_signals(self):
        self._explorer.file_opened.connect(self._tabs.open_file)
        self._explorer.folder_opened.connect(self._on_folder_opened)
        self._tabs.current_file_changed.connect(self._on_file_changed)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._terminal.process_started.connect(self._on_process_started)
        self._terminal.process_stopped.connect(
            lambda: self._on_file_changed(self._tabs.current_file_path())
        )

    def _on_tab_changed(self, _idx: int):
        if self._prev_ed is not None:
            try:
                self._prev_ed.cursorPositionChanged.disconnect(self._update_cursor_pos)
            except RuntimeError:
                pass
        ed = self._tabs.current_editor()
        if ed is not None:
            ed.cursorPositionChanged.connect(self._update_cursor_pos)
            self._prev_ed = ed
            self._update_cursor_pos()
        else:
            self._prev_ed = None

    # ── Action handlers ───────────────────────────────────────────────────────
    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "",
            "Python Files (*.py);;Text Files (*.txt);;All Files (*)"
        )
        if path:
            self._tabs.open_file(path)

    def _open_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Open Folder", "")
        if path:
            self._explorer.open_folder(path)
            self._explorer_dock.setVisible(True)

    def _save(self):
        self._tabs.save_file()

    def _save_as(self):
        self._tabs.save_as()

    def _run_file(self):
        path = self._tabs.current_file_path()

        # Auto-save before running
        if path and path.endswith(".py"):
            self._tabs.save_file()
        elif path is None:
            if not self._tabs.save_file():
                return
            path = self._tabs.current_file_path()

        run_path = self._tabs.current_file_path()
        if not (run_path and run_path.endswith(".py")):
            QMessageBox.information(
                self, "Run",
                "Please open or save a Python (.py) file to run it."
            )
            return

        # Prevent recursive launch: never execute the IDE's own entry point
        _ide_main = os.path.abspath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        )
        if os.path.abspath(run_path) == _ide_main:
            QMessageBox.warning(
                self, "Run",
                "Running the IDE's own main.py is not allowed.\n"
                "Please open a different Python file."
            )
            return

        self._terminal_dock.setVisible(True)
        self._terminal.set_file(run_path)
        self._terminal.run(run_path)

    def _find_replace(self):
        FindReplaceDialog(self._tabs, self).exec()

    def _show_about(self):
        AboutDialog(self).exec()

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # Apply settings immediately to all open editors and terminal
            self._tabs.apply_settings_to_all()
            self._terminal.apply_settings()

    def _open_interpreter_manager(self):
        try:
            from interpreter import InterpreterManagerDialog
            dlg = InterpreterManagerDialog(self)
            dlg.interpreter_changed.connect(self._on_interpreter_changed)
            dlg.exec()
        except Exception as exc:
            QMessageBox.warning(self, "Interpreter Manager", str(exc))

    def _on_interpreter_changed(self, path: str):
        self._refresh_interpreter_label()
        name = os.path.basename(path)
        self.statusBar().showMessage(f"Interpreter changed to: {name}", 4000)

    def _check_updates_manual(self):
        try:
            self._update_thread = check_for_updates(self, silent=False)
        except Exception as exc:
            QMessageBox.warning(self, "Update Check", str(exc))

    # ── Workspace restore ─────────────────────────────────────────────────────
    def _restore_workspace(self):
        last = self._cfg.get("last_workspace", "")
        if last and os.path.isdir(last):
            self._explorer.open_folder(last)
            self._explorer_dock.setVisible(True)

    def _on_folder_opened(self, path: str):
        """Called when the explorer opens a folder — persist it."""
        self._cfg.set("last_workspace", path)
        self._cfg.add_recent_project(path)
        self._rebuild_recent_menu()

    # ── Recent projects menu ──────────────────────────────────────────────────
    def _rebuild_recent_menu(self):
        self._recent_menu.clear()
        recent = self._cfg.recent_projects()
        if not recent:
            empty = QAction("(none)", self)
            empty.setEnabled(False)
            self._recent_menu.addAction(empty)
            return

        for path in recent:
            a = QAction(os.path.basename(path), self)
            a.setToolTip(path)
            a.triggered.connect(lambda checked, p=path: self._open_recent(p))
            self._recent_menu.addAction(a)

        self._recent_menu.addSeparator()
        clear_a = QAction("Clear Recent Projects", self)
        clear_a.triggered.connect(self._clear_recent)
        self._recent_menu.addAction(clear_a)

    def _open_recent(self, path: str):
        if not os.path.isdir(path):
            QMessageBox.warning(
                self, "Recent Projects",
                f"Folder no longer exists:\n{path}"
            )
            recent = self._cfg.recent_projects()
            recent = [p for p in recent if p != path]
            self._cfg.set("recent_projects", recent)
            self._rebuild_recent_menu()
            return
        self._explorer.open_folder(path)
        self._explorer_dock.setVisible(True)

    def _clear_recent(self):
        self._cfg.set("recent_projects", [])
        self._rebuild_recent_menu()

    # ── Status bar helpers ────────────────────────────────────────────────────
    def _on_file_changed(self, path: str | None):
        if path:
            self._sb_file.setText(os.path.basename(path))
            self.setWindowTitle(f"{os.path.basename(path)} — {APP_NAME}")
        else:
            self._sb_file.setText("Untitled")
            self.setWindowTitle(APP_NAME)
        self._terminal.set_file(path)

    def _on_process_started(self):
        name = os.path.basename(self._tabs.current_file_path() or "")
        self._sb_file.setText(f"▶  Running:  {name}")

    def _update_cursor_pos(self):
        ed = self._tabs.current_editor()
        if ed:
            c = ed.textCursor()
            self._sb_pos.setText(
                f"Ln {c.blockNumber() + 1},  Col {c.columnNumber() + 1}"
            )

    # ── Auto-update check (called by main.py) ─────────────────────────────────
    def check_for_updates_silently(self):
        """Run a silent background update check if enabled in settings."""
        if not self._cfg.get("auto_update", True):
            return
        try:
            from updater import check_for_updates
            self._update_thread = check_for_updates(self, silent=True)
        except Exception:
            pass

    # ── Close ─────────────────────────────────────────────────────────────────
    def closeEvent(self, event):         # noqa: N802
        self._terminal.stop()
        event.accept()
