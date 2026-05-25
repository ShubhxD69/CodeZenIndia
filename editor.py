# editor.py — Multi-tab code editor
#
# Features
# ────────
#  • Line numbers with active-line highlight
#  • Python syntax highlighting
#  • Tab = 4 spaces (configurable from settings), indent/de-indent selection
#  • Smart auto-indent (extra level after colon-terminated lines)
#  • Auto-close brackets and quotes; skip-over; paired backspace
#  • Dynamic autocomplete: static keyword/builtin list + words from the document
#  • Current-line highlight
#  • Unsaved-file indicator (*) in tab label
#  • Settings-aware font size and tab width

import os
import re
from PyQt6.QtWidgets import (
    QPlainTextEdit, QWidget, QTabWidget, QTabBar,
    QCompleter, QFileDialog, QMessageBox,
    QTextEdit,
)
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal, QTimer, QStringListModel
from PyQt6.QtGui import (
    QColor, QPainter, QTextCursor, QKeyEvent, QMouseEvent,
    QFont, QPalette, QFontMetrics, QTextFormat,
    QShortcut, QKeySequence,
)

from syntax import PythonHighlighter, KEYWORDS, BUILTINS
from theme import BG_DARK, BG_PANEL, FG_TEXT, FG_MUTED, SELECTION, CURSOR

# ── Static autocomplete word list ─────────────────────────────────────────────
_EXTRA_WORDS = [
    "self", "cls",
    "__init__", "__str__", "__repr__", "__len__", "__getitem__",
    "__setitem__", "__delitem__", "__iter__", "__next__", "__enter__",
    "__exit__", "__call__", "__class__", "__name__", "__file__",
    "__doc__", "__all__", "__version__",
    # Common snippets as words
    "print", "input", "range", "enumerate", "isinstance", "hasattr",
    "getattr", "setattr", "super", "property", "staticmethod", "classmethod",
]
_STATIC_WORDS: list[str] = sorted(set(KEYWORDS + BUILTINS + _EXTRA_WORDS))


def _load_tab_size() -> int:
    try:
        from settings import Settings
        return int(Settings.instance().get("tab_size", 4))
    except Exception:
        return 4


def _load_font_size() -> int:
    try:
        from settings import Settings
        return int(Settings.instance().get("font_size", 13))
    except Exception:
        return 13


# ─────────────────────────────────────────────────────────────────────────────
# Line Number Area
# ─────────────────────────────────────────────────────────────────────────────
class LineNumberArea(QWidget):
    """Gutter that delegates painting back to the owning editor."""

    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):          # noqa: N802
        self._editor.line_number_area_paint_event(event)


# ─────────────────────────────────────────────────────────────────────────────
# CodeEditor
# ─────────────────────────────────────────────────────────────────────────────
class CodeEditor(QPlainTextEdit):
    """
    Full-featured code-editor widget.

    Keyboard behaviour
    ──────────────────
    Tab              → insert N spaces (or indent selection)
    Shift+Tab        → de-indent selection
    Enter            → auto-indent (extra level after colon-terminated line)
    (, [, {, ", '   → insert matching close char; wrap selection if any
    ), ], }, ", '   → skip over the char if it already sits at cursor
    Backspace        → delete the matched pair when cursor is between them
    Ctrl+Space       → force autocomplete popup
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tab_size = _load_tab_size()
        self._setup_appearance()
        self._setup_line_numbers()
        self._setup_completer()
        self._highlighter = PythonHighlighter(self.document())
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._highlight_current_line()

        # Debounce timer: rebuild dynamic word list 500 ms after last keystroke
        self._doc_words_timer = QTimer(self)
        self._doc_words_timer.setSingleShot(True)
        self._doc_words_timer.setInterval(500)
        self._doc_words_timer.timeout.connect(self._rebuild_word_list)
        self.document().contentsChanged.connect(self._doc_words_timer.start)

    # ── Appearance ────────────────────────────────────────────────────────────
    def _setup_appearance(self):
        size = _load_font_size()
        font = QFont("Cascadia Code", size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        if not font.exactMatch():
            font = QFont("Consolas", size)
            font.setFixedPitch(True)
        self.setFont(font)
        self._update_tab_stop()

        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor(BG_DARK))
        pal.setColor(QPalette.ColorRole.Text, QColor(FG_TEXT))
        pal.setColor(QPalette.ColorRole.Highlight, QColor(SELECTION))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        self.setPalette(pal)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def _update_tab_stop(self):
        self.setTabStopDistance(
            QFontMetrics(self.font()).horizontalAdvance(" ") * self._tab_size
        )

    def apply_settings(self):
        """Reload font size and tab size from settings and update the editor."""
        new_size = _load_font_size()
        new_tab  = _load_tab_size()
        font = self.font()
        if font.pointSize() != new_size:
            font.setPointSize(new_size)
            self.setFont(font)
        if self._tab_size != new_tab:
            self._tab_size = new_tab
        self._update_tab_stop()
        # Update gutter width in case the font changed
        self._update_gutter_width(0)

    # ── Line numbers ──────────────────────────────────────────────────────────
    def _setup_line_numbers(self):
        self._gutter = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_gutter_width)
        self.updateRequest.connect(self._update_gutter)
        self._update_gutter_width(0)

    def line_number_area_width(self) -> int:
        digits = max(len(str(self.blockCount())), 3)
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_gutter_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_gutter(self, rect, dy: int):
        if dy:
            self._gutter.scroll(0, dy)
        else:
            self._gutter.update(0, rect.y(), self._gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_gutter_width(0)

    def resizeEvent(self, event):           # noqa: N802
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._gutter.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self._gutter)
        painter.fillRect(event.rect(), QColor(BG_PANEL))
        painter.setFont(self.font())

        block   = self.firstVisibleBlock()
        num     = block.blockNumber()
        top     = int(
            self.blockBoundingGeometry(block)
            .translated(self.contentOffset())
            .top()
        )
        bottom  = top + int(self.blockBoundingRect(block).height())
        cur_line = self.textCursor().blockNumber()
        fh      = self.fontMetrics().height()
        gw      = self._gutter.width()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(
                    QColor(FG_TEXT) if num == cur_line else QColor(FG_MUTED)
                )
                painter.drawText(
                    0, top, gw - 4, fh,
                    Qt.AlignmentFlag.AlignRight, str(num + 1),
                )
            block  = block.next()
            top    = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            num   += 1

    # ── Current-line highlight ────────────────────────────────────────────────
    def _highlight_current_line(self):
        extras = []
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            colour = QColor(CURSOR)
            colour.setAlpha(35)
            sel.format.setBackground(colour)
            sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            extras.append(sel)
        self.setExtraSelections(extras)

    # ── Autocomplete ──────────────────────────────────────────────────────────
    def _setup_completer(self):
        self._word_model = QStringListModel(_STATIC_WORDS, self)
        self._completer  = QCompleter(self._word_model, self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseSensitive)
        self._completer.activated.connect(self._insert_completion)

    def _word_under_cursor(self) -> str:
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        return tc.selectedText()

    def _insert_completion(self, completion: str):
        if self._completer.widget() is not self:
            return
        tc    = self.textCursor()
        extra = len(completion) - len(self._completer.completionPrefix())
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)

    def _show_completer(self, prefix: str):
        if prefix != self._completer.completionPrefix():
            self._completer.setCompletionPrefix(prefix)
            self._completer.popup().setCurrentIndex(
                self._completer.completionModel().index(0, 0)
            )
        cr = self.cursorRect()
        cr.setWidth(
            self._completer.popup().sizeHintForColumn(0)
            + self._completer.popup().verticalScrollBar().sizeHint().width()
        )
        self._completer.complete(cr)

    def _trigger_completer(self):
        prefix = self._word_under_cursor()
        if len(prefix) >= 2:
            self._show_completer(prefix)
        else:
            self._completer.popup().hide()

    def _rebuild_word_list(self):
        """
        Merge static words with identifiers extracted from the current document.
        Called on a debounced timer so it never blocks typing.
        """
        raw   = self.toPlainText()
        doc_words = set(re.findall(r"\b[A-Za-z_]\w{1,}\b", raw))
        merged = sorted(set(_STATIC_WORDS) | doc_words)
        self._word_model.setStringList(merged)

    # ── Key handling ──────────────────────────────────────────────────────────
    _BRACKET_CLOSE = {"(": ")", "[": "]", "{": "}"}
    _QUOTE_CHARS   = {'"', "'"}
    _ALL_OPEN      = {**_BRACKET_CLOSE, '"': '"', "'": "'"}
    _ALL_CLOSE     = set(_ALL_OPEN.values())

    def keyPressEvent(self, event: QKeyEvent):       # noqa: N802
        # Pass navigation keys to the completer popup
        if self._completer.popup().isVisible():
            if event.key() in (
                Qt.Key.Key_Return, Qt.Key.Key_Enter,
                Qt.Key.Key_Tab,    Qt.Key.Key_Backtab,
                Qt.Key.Key_Escape,
            ):
                event.ignore()
                return

        key  = event.key()
        text = event.text()
        mods = event.modifiers()

        # Ctrl+Space → force autocomplete
        if (key == Qt.Key.Key_Space
                and mods & Qt.KeyboardModifier.ControlModifier):
            self._trigger_completer()
            return

        # ── Tab → N spaces (or indent selection) ──────────────────────────────
        if key == Qt.Key.Key_Tab and not (mods & Qt.KeyboardModifier.ShiftModifier):
            cur = self.textCursor()
            if cur.hasSelection():
                self._change_indent(cur, add=True)
            else:
                cur.insertText(" " * self._tab_size)
            return

        # ── Shift+Tab → de-indent ─────────────────────────────────────────────
        if key == Qt.Key.Key_Backtab:
            self._change_indent(self.textCursor(), add=False)
            return

        # ── Enter → smart auto-indent ─────────────────────────────────────────
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._smart_return()
            return

        # ── Quotes: skip-over BEFORE auto-close ───────────────────────────────
        if text in self._QUOTE_CHARS:
            cur = self.textCursor()
            if not cur.hasSelection():
                line = cur.block().text()
                pos  = cur.positionInBlock()
                if pos < len(line) and line[pos] == text:
                    cur.movePosition(QTextCursor.MoveOperation.Right)
                    self.setTextCursor(cur)
                    self._trigger_completer()
                    return
            self._insert_pair(text, text, cur)
            return

        # ── Brackets: auto-close ──────────────────────────────────────────────
        if text in self._BRACKET_CLOSE:
            self._insert_pair(text, self._BRACKET_CLOSE[text], self.textCursor())
            return

        # ── Closing bracket: skip over ────────────────────────────────────────
        if text in self._ALL_CLOSE and text not in self._QUOTE_CHARS:
            cur = self.textCursor()
            if not cur.hasSelection():
                line = cur.block().text()
                pos  = cur.positionInBlock()
                if pos < len(line) and line[pos] == text:
                    cur.movePosition(QTextCursor.MoveOperation.Right)
                    self.setTextCursor(cur)
                    return

        # ── Backspace: delete matched pair ────────────────────────────────────
        if key == Qt.Key.Key_Backspace:
            cur = self.textCursor()
            if not cur.hasSelection():
                line = cur.block().text()
                pos  = cur.positionInBlock()
                if 0 < pos < len(line):
                    left  = line[pos - 1]
                    right = line[pos]
                    if self._ALL_OPEN.get(left) == right:
                        cur.movePosition(
                            QTextCursor.MoveOperation.Right,
                            QTextCursor.MoveMode.KeepAnchor,
                        )
                        cur.removeSelectedText()
                        cur.deletePreviousChar()
                        return

        super().keyPressEvent(event)
        self._trigger_completer()

    def _insert_pair(self, open_: str, close: str, cur: QTextCursor):
        if cur.hasSelection():
            sel = cur.selectedText()
            cur.insertText(open_ + sel + close)
        else:
            cur.insertText(open_ + close)
            cur.movePosition(QTextCursor.MoveOperation.Left)
            self.setTextCursor(cur)
        self._trigger_completer()

    def _smart_return(self):
        cur  = self.textCursor()
        line = cur.block().text()

        indent = ""
        for ch in line:
            if ch in (" ", "\t"):
                indent += ch
            else:
                break

        if line.rstrip().endswith(":"):
            indent += " " * self._tab_size

        cur.insertText("\n" + indent)
        self.setTextCursor(cur)

    def _change_indent(self, cur: QTextCursor, add: bool):
        start = cur.selectionStart()
        end   = cur.selectionEnd()

        cur.setPosition(start)
        cur.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        first_block = cur.blockNumber()

        cur.setPosition(end)
        if cur.positionInBlock() == 0 and end > start:
            cur.movePosition(QTextCursor.MoveOperation.PreviousBlock)
        last_block = cur.blockNumber()

        cur.setPosition(start)
        cur.beginEditBlock()
        spaces = " " * self._tab_size
        for _ in range(last_block - first_block + 1):
            cur.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            if add:
                cur.insertText(spaces)
            else:
                line   = cur.block().text()
                n_del  = min(self._tab_size, len(line) - len(line.lstrip(" ")))
                for __ in range(n_del):
                    cur.deleteChar()
            cur.movePosition(QTextCursor.MoveOperation.NextBlock)
        cur.endEditBlock()


# ─────────────────────────────────────────────────────────────────────────────
# Custom tab bar — adds middle-click close
# ─────────────────────────────────────────────────────────────────────────────
class _ClosableTabBar(QTabBar):
    """
    QTabBar subclass that emits tabCloseRequested on middle-click,
    providing VS Code-style middle-click-to-close behaviour.
    """

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            idx = self.tabAt(event.pos())
            if idx >= 0:
                self.tabCloseRequested.emit(idx)
                return
        super().mousePressEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
# EditorTabWidget
# ─────────────────────────────────────────────────────────────────────────────
class EditorTabWidget(QTabWidget):
    """
    Multi-tab editor container.
    Uses the *editor object* as the key (never the index) so that tab
    reordering or closing never corrupts path / dirty state.
    """

    current_file_changed = pyqtSignal(object)   # str | None

    def __init__(self, parent=None):
        super().__init__(parent)

        # Install custom tab bar (enables middle-click close)
        self.setTabBar(_ClosableTabBar())

        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)

        # Single connection — no duplicates because __init__ runs once
        self.tabCloseRequested.connect(self._close_tab)
        self.currentChanged.connect(self._on_current_changed)

        # Ctrl+W closes the active tab
        _ctrl_w = QShortcut(QKeySequence("Ctrl+W"), self)
        _ctrl_w.activated.connect(lambda: self._close_tab(self.currentIndex()))

        self._paths: dict[CodeEditor, str | None] = {}
        self._dirty: dict[CodeEditor, bool]       = {}

        self.new_file()

    # ── Public API ────────────────────────────────────────────────────────────
    def new_file(self, path: str | None = None, content: str = "") -> int:
        ed = CodeEditor()
        ed.setPlainText(content)
        ed.document().modificationChanged.connect(
            lambda dirty, e=ed: self._on_editor_modified(dirty, e)
        )

        label = os.path.basename(path) if path else "Untitled"
        idx   = self.addTab(ed, label)

        self._paths[ed] = path
        self._dirty[ed] = False

        self.setCurrentIndex(idx)
        ed.document().setModified(False)
        return idx

    def open_file(self, path: str):
        """Open a file — switch to existing tab if already open."""
        for ed, p in self._paths.items():
            if p == path:
                self.setCurrentIndex(self.indexOf(ed))
                return

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError as exc:
            QMessageBox.warning(self, "Open Error", str(exc))
            return

        cur_ed = self.current_editor()
        if (
            cur_ed is not None
            and self._paths.get(cur_ed) is None
            and not cur_ed.toPlainText()
        ):
            cur_ed.setPlainText(content)
            cur_ed.document().setModified(False)
            self._paths[cur_ed] = path
            self._dirty[cur_ed] = False
            self.setTabText(self.currentIndex(), os.path.basename(path))
            self.current_file_changed.emit(path)
            return

        self.new_file(path, content)

    def save_file(self, path: str | None = None) -> bool:
        ed = self.current_editor()
        if ed is None:
            return False

        target = path or self._paths.get(ed)
        if not target:
            return self._save_as()

        try:
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(ed.toPlainText())
        except OSError as exc:
            QMessageBox.warning(self, "Save Error", str(exc))
            return False

        self._paths[ed] = target
        self._dirty[ed] = False
        ed.document().setModified(False)
        # Use indexOf(ed) — safer than currentIndex() when save is called
        # programmatically (e.g. from _close_tab after a tab switch)
        tab_idx = self.indexOf(ed)
        if tab_idx >= 0:
            self.setTabText(tab_idx, os.path.basename(target))
        return True

    def save_as(self) -> bool:
        return self._save_as()

    def current_file_path(self) -> str | None:
        ed = self.current_editor()
        return self._paths.get(ed) if ed else None

    def current_editor(self) -> "CodeEditor | None":
        w = self.currentWidget()
        return w if isinstance(w, CodeEditor) else None

    def apply_settings_to_all(self):
        """Propagate font/tab settings to every open editor tab."""
        for ed in self._paths:
            try:
                ed.apply_settings()
            except Exception:
                pass

    # ── Internal ──────────────────────────────────────────────────────────────
    def _save_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save File", "",
            "Python Files (*.py);;Text Files (*.txt);;All Files (*)"
        )
        return self.save_file(path) if path else False

    def _close_tab(self, idx: int):
        # Guard: index may be stale if tabs were closed quickly
        if idx < 0 or idx >= self.count():
            return

        ed = self.widget(idx)
        if not isinstance(ed, CodeEditor):
            return

        if self._dirty.get(ed, False):
            # Strip the leading '*' marker to get the clean display name
            name  = self.tabText(idx).lstrip("*").strip() or "Untitled"
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"'{name}' has unsaved changes.  Save before closing?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                # Switch to this tab so save_file() operates on it
                self.setCurrentIndex(idx)
                if not self.save_file():
                    return          # Save failed or was cancelled — abort close
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        # Remove state before removeTab() so currentChanged callbacks see
        # a consistent _paths / _dirty state when they fire
        self._paths.pop(ed, None)
        self._dirty.pop(ed, None)
        self.removeTab(idx)
        ed.deleteLater()            # Release Qt object; prevents memory leaks

        # Always keep at least one tab open
        if self.count() == 0:
            self.new_file()

    def _on_editor_modified(self, dirty: bool, ed: "CodeEditor"):
        idx = self.indexOf(ed)
        if idx < 0:
            return
        self._dirty[ed] = dirty
        # Strip any existing '*' prefix to get the clean file name
        label = self.tabText(idx).lstrip("*").strip() or "Untitled"
        # Prefix '*' for unsaved files — VS Code convention
        self.setTabText(idx, ("*" + label) if dirty else label)

    def _on_current_changed(self, idx: int):
        w    = self.widget(idx)
        path = self._paths.get(w) if isinstance(w, CodeEditor) else None
        self.current_file_changed.emit(path)
