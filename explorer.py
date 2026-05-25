# explorer.py — File Explorer sidebar
#
# Features
# ────────
#  • Project folder tree (QFileSystemModel)
#  • Right-click context menu: Open, New File, New Folder, Rename, Delete
#  • Double-click to open a file in the editor
#  • Drag-and-drop file acceptance (drop files from OS onto the tree)
#  • Workspace persistence — emits folder_opened signal so MainWindow can save it
#  • Refresh button to force tree reload

import os
import shutil

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeView, QLabel, QMenu, QInputDialog, QMessageBox,
    QAbstractItemView, QFileDialog,
)
from PyQt6.QtCore import Qt, QDir, QModelIndex, pyqtSignal
from PyQt6.QtGui import QFileSystemModel, QAction

from theme import BG_PANEL, FG_MUTED, BORDER


class FileExplorer(QWidget):
    """Left-panel file tree.

    Signals
    ───────
    file_opened(path)    — user double-clicked / opened a file
    folder_opened(path)  — a folder was successfully opened (used for persistence)
    """

    file_opened   = pyqtSignal(str)
    folder_opened = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_path: str | None = None
        self._setup_ui()
        self.setAcceptDrops(True)

    # ── Construction ──────────────────────────────────────────────────────────
    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Header bar
        header = QWidget()
        header.setStyleSheet(
            f"background:{BG_PANEL}; border-bottom:1px solid {BORDER};"
        )
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(8, 6, 8, 6)
        hdr_layout.setSpacing(4)

        title = QLabel("EXPLORER")
        title.setStyleSheet(
            f"color:{FG_MUTED}; font-size:11px; font-weight:bold; "
            f"letter-spacing:1px; background:transparent;"
        )
        hdr_layout.addWidget(title)
        hdr_layout.addStretch()

        # Refresh button
        self._refresh_btn = QPushButton("↺")
        self._refresh_btn.setToolTip("Refresh file tree")
        self._refresh_btn.setFixedSize(22, 22)
        self._refresh_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{FG_MUTED};"
            f"border:none;font-size:14px;border-radius:3px;}}"
            f"QPushButton:hover{{color:#d4d4d4;background:#3a3a3a;}}"
        )
        self._refresh_btn.clicked.connect(self._refresh)
        hdr_layout.addWidget(self._refresh_btn)

        self._open_btn = QPushButton("⊕")
        self._open_btn.setToolTip("Open Folder")
        self._open_btn.setFixedSize(22, 22)
        self._open_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{FG_MUTED};"
            f"border:none;font-size:16px;border-radius:3px;}}"
            f"QPushButton:hover{{color:#d4d4d4;background:#3a3a3a;}}"
        )
        self._open_btn.clicked.connect(lambda _checked=False: self.open_folder())
        hdr_layout.addWidget(self._open_btn)
        root_layout.addWidget(header)

        # Placeholder shown before a folder is opened
        self._placeholder = QLabel(
            "No folder opened.\n\nClick  ⊕  to open a project folder.\n\n"
            "Or drag-and-drop a folder here."
        )
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            f"color:{FG_MUTED}; font-size:12px; padding:24px; background:transparent;"
        )
        self._placeholder.setWordWrap(True)
        root_layout.addWidget(self._placeholder)

        # File-system model + tree
        self._model = QFileSystemModel()
        self._model.setFilter(
            QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot | QDir.Filter.Hidden
        )
        self._model.setReadOnly(False)

        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setRootIsDecorated(True)
        self._tree.setHeaderHidden(True)
        self._tree.setAnimated(True)
        self._tree.setUniformRowHeights(True)
        self._tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._context_menu)
        self._tree.doubleClicked.connect(self._on_double_click)

        # Accept drops on the tree itself
        self._tree.setAcceptDrops(False)   # we handle it at widget level

        # Hide size / type / date columns — show only the name
        for col in range(1, 4):
            self._tree.hideColumn(col)

        self._tree.setVisible(False)
        root_layout.addWidget(self._tree)

    # ── Public ────────────────────────────────────────────────────────────────
    def open_folder(self, path: str | None = None):
        """Open a folder in the tree; prompt if path is not given."""
        if not path:
            path = QFileDialog.getExistingDirectory(
                self, "Open Folder", os.path.expanduser("~")
            )
        if not path:
            return
        if not os.path.isdir(path):
            return

        self._root_path = path
        self._model.setRootPath(path)
        self._tree.setRootIndex(self._model.index(path))
        self._placeholder.setVisible(False)
        self._tree.setVisible(True)
        self.folder_opened.emit(path)

    @property
    def root_path(self) -> str | None:
        return self._root_path

    # ── Refresh ───────────────────────────────────────────────────────────────
    def _refresh(self):
        if self._root_path and os.path.isdir(self._root_path):
            self._model.setRootPath("")
            self._model.setRootPath(self._root_path)
            self._tree.setRootIndex(self._model.index(self._root_path))

    # ── Drag and drop ─────────────────────────────────────────────────────────
    def dragEnterEvent(self, event):       # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):        # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):            # noqa: N802
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if os.path.isfile(local):
                self.file_opened.emit(local)
            elif os.path.isdir(local):
                self.open_folder(local)
                break
        event.acceptProposedAction()

    # ── Double-click ──────────────────────────────────────────────────────────
    def _on_double_click(self, index: QModelIndex):
        path = self._model.filePath(index)
        if os.path.isfile(path):
            self.file_opened.emit(path)

    # ── Context menu ──────────────────────────────────────────────────────────
    def _context_menu(self, pos):
        index = self._tree.indexAt(pos)
        menu  = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:#252526;color:#d4d4d4;border:1px solid {BORDER};}}"
            f"QMenu::item{{padding:5px 24px 5px 12px;}}"
            f"QMenu::item:selected{{background:#094771;color:#fff;}}"
            f"QMenu::separator{{height:1px;background:{BORDER};margin:3px 0;}}"
        )

        if index.isValid():
            path    = self._model.filePath(index)
            is_file = os.path.isfile(path)

            if is_file:
                a = QAction("Open File", self)
                a.triggered.connect(lambda: self.file_opened.emit(path))
                menu.addAction(a)
                menu.addSeparator()

            a = QAction("New File", self)
            a.triggered.connect(lambda: self._new_file(index))
            menu.addAction(a)

            a = QAction("New Folder", self)
            a.triggered.connect(lambda: self._new_folder(index))
            menu.addAction(a)

            menu.addSeparator()

            a = QAction("Rename", self)
            a.triggered.connect(lambda: self._rename(index))
            menu.addAction(a)

            a = QAction("Delete", self)
            a.triggered.connect(lambda: self._delete(index))
            menu.addAction(a)

        else:
            root_idx = (
                self._model.index(self._root_path)
                if self._root_path else QModelIndex()
            )
            a = QAction("New File", self)
            a.triggered.connect(lambda: self._new_file(root_idx))
            menu.addAction(a)

            a = QAction("New Folder", self)
            a.triggered.connect(lambda: self._new_folder(root_idx))
            menu.addAction(a)

            menu.addSeparator()

            a = QAction("Open Folder…", self)
            a.triggered.connect(lambda: self.open_folder())
            menu.addAction(a)

            a = QAction("Refresh", self)
            a.triggered.connect(self._refresh)
            menu.addAction(a)

        menu.exec(self._tree.viewport().mapToGlobal(pos))

    # ── File / folder operations ──────────────────────────────────────────────
    def _dir_for(self, index: QModelIndex) -> str:
        if index.isValid():
            p = self._model.filePath(index)
            return p if os.path.isdir(p) else os.path.dirname(p)
        return self._root_path or os.path.expanduser("~")

    def _new_file(self, index: QModelIndex):
        parent = self._dir_for(index)
        name, ok = QInputDialog.getText(self, "New File", "File name:")
        if ok and name.strip():
            full = os.path.join(parent, name.strip())
            try:
                with open(full, "w", encoding="utf-8"):
                    pass
                self.file_opened.emit(full)
            except OSError as exc:
                QMessageBox.warning(self, "Error", str(exc))

    def _new_folder(self, index: QModelIndex):
        parent = self._dir_for(index)
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name.strip():
            try:
                os.makedirs(os.path.join(parent, name.strip()), exist_ok=True)
            except OSError as exc:
                QMessageBox.warning(self, "Error", str(exc))

    def _rename(self, index: QModelIndex):
        if not index.isValid():
            return
        old_path = self._model.filePath(index)
        old_name = os.path.basename(old_path)
        new_name, ok = QInputDialog.getText(
            self, "Rename", "New name:", text=old_name
        )
        if ok and new_name.strip() and new_name.strip() != old_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name.strip())
            try:
                os.rename(old_path, new_path)
            except OSError as exc:
                QMessageBox.warning(self, "Error", str(exc))

    def _delete(self, index: QModelIndex):
        if not index.isValid():
            return
        path = self._model.filePath(index)
        name = os.path.basename(path)
        reply = QMessageBox.question(
            self, "Delete",
            f"Delete  '{name}'?  This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            except OSError as exc:
                QMessageBox.warning(self, "Error", str(exc))
