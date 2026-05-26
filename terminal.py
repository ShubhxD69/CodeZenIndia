# terminal.py — Integrated interactive terminal panel
#
# Architecture
# ────────────
#  ┌─────────────────────────────────────────────────────┐
#  │  Toolbar  [▶ Run]  [■ Stop]  [⌫ Clear]              │
#  ├─────────────────────────────────────────────────────┤
#  │                                                     │
#  │  Output area  (QPlainTextEdit, read-only)           │
#  │  stdout → white   stderr → red   info → grey        │
#  │  ANSI colour codes parsed and rendered              │
#  │                                                     │
#  ├─────────────────────────────────────────────────────┤
#  │  ›  [  input field  ──────────────────── ] [Send]   │
#  └─────────────────────────────────────────────────────┘
#
# Features
# ────────
#  • QProcess-based execution (never re-launches the IDE)
#  • Unbuffered -u flag for real-time output streaming
#  • Basic ANSI SGR colour code rendering (30-37, 90-97, reset)
#  • Command history — Up/Down arrow navigation in the input field
#  • Ctrl+C in input field sends SIGKILL (KeyboardInterrupt)
#  • Stop button kills the process immediately
#  • Multiple sequential runs work cleanly
#  • input() programs fully supported

import re
import sys
import os
import shutil

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QPlainTextEdit, QLabel, QLineEdit,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QProcess, QProcessEnvironment, pyqtSignal
from PyQt6.QtGui import QColor, QTextCursor, QFont, QKeyEvent

from theme import BG_PANEL, FG_TEXT, FG_MUTED, BORDER


# ─────────────────────────────────────────────────────────────────────────────
# ANSI SGR colour parser
# ─────────────────────────────────────────────────────────────────────────────
_ANSI_RE = re.compile(r"\x1b\[([0-9;]*)m")

_ANSI_FG: dict[int, str] = {
    30: "#4d4d4d",  31: "#cd3131",  32: "#0dbc79",  33: "#e5e510",
    34: "#2472c8",  35: "#bc3fbc",  36: "#11a8cd",  37: "#e5e5e5",
    # bright
    90: "#666666",  91: "#f14c4c",  92: "#23d18b",  93: "#f5f543",
    94: "#3b8eea",  95: "#d670d6",  96: "#29b8db",  97: "#e5e5e5",
}

_DEFAULT_COLOR = FG_TEXT     # white-ish for stdout
_ERR_COLOR     = "#f48771"   # salmon-red for stderr
_INFO_COLOR    = "#858585"   # grey for meta messages
_OK_COLOR      = "#4ec9b0"   # teal-green for exit 0
_ECHO_COLOR    = "#9cdcfe"   # light-blue for stdin echo


def _parse_ansi(text: str, base_color: str) -> list[tuple[str, str]]:
    """
    Split *text* into (segment, hex_color) pairs by interpreting ANSI SGR codes.
    Unknown codes are silently ignored.  Strips all other escape sequences.
    """
    segments: list[tuple[str, str]] = []
    current = base_color
    last = 0

    for m in _ANSI_RE.finditer(text):
        if m.start() > last:
            segments.append((text[last:m.start()], current))

        codes_str = m.group(1)
        codes: list[int] = []
        if codes_str:
            try:
                codes = [int(c) for c in codes_str.split(";") if c]
            except ValueError:
                codes = [0]
        else:
            codes = [0]

        for code in codes:
            if code == 0:
                current = base_color
            elif code in _ANSI_FG:
                current = _ANSI_FG[code]

        last = m.end()

    if last < len(text):
        segments.append((text[last:], current))

    return segments


def _strip_other_escapes(text: str) -> str:
    """Remove any remaining ESC sequences that aren't SGR colour codes."""
    return re.sub(r"\x1b[^m]*m?|\x1b", "", text)


# ─────────────────────────────────────────────────────────────────────────────
# Terminal widget
# ─────────────────────────────────────────────────────────────────────────────
class Terminal(QWidget):
    """
    Interactive terminal panel.

    Public API
    ──────────
    set_file(path)           update the file that Run will execute
    run(file_path=None)      start execution
    stop()                   kill running process
    clear()                  wipe output area
    apply_settings()         reload font size from settings.json
    """

    process_started = pyqtSignal()
    process_stopped = pyqtSignal()

    # Maximum input history entries kept in memory
    _MAX_HISTORY = 200

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process:      QProcess | None = None
        self._current_file: str | None      = None
        self._history:      list[str]       = []
        self._hist_idx:     int             = -1     # -1 = not navigating
        self._pending_input: str            = ""     # saved current input during navigation
        self._setup_ui()
        self.apply_settings()

    # ── UI construction ───────────────────────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar ───────────────────────────────────────────────────────────
        bar = QWidget()
        bar.setFixedHeight(34)
        bar.setStyleSheet(
            f"background:{BG_PANEL}; border-bottom:1px solid {BORDER};"
        )
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(8, 3, 8, 3)
        bar_layout.setSpacing(6)

        lbl = QLabel("OUTPUT / TERMINAL")
        lbl.setStyleSheet(
            f"color:{FG_MUTED}; font-size:11px; font-weight:bold; "
            f"letter-spacing:1px; background:transparent;"
        )
        bar_layout.addWidget(lbl)
        bar_layout.addStretch()

        self._run_btn = QPushButton("▶  Run")
        self._run_btn.setObjectName("run_btn")
        self._run_btn.setToolTip("Run current Python file (F5)")
        self._run_btn.setFixedHeight(24)
        self._run_btn.clicked.connect(self.run)
        bar_layout.addWidget(self._run_btn)

        self._stop_btn = QPushButton("■  Stop")
        self._stop_btn.setObjectName("stop_btn")
        self._stop_btn.setToolTip("Stop running process (Shift+F5)")
        self._stop_btn.setFixedHeight(24)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self.stop)
        bar_layout.addWidget(self._stop_btn)

        clear_btn = QPushButton("⌫  Clear")
        clear_btn.setFixedHeight(24)
        clear_btn.setToolTip("Clear output")
        clear_btn.clicked.connect(self.clear)
        bar_layout.addWidget(clear_btn)

        root.addWidget(bar)

        # ── Output area ───────────────────────────────────────────────────────
        self._out = QPlainTextEdit()
        self._out.setObjectName("terminal_output")
        self._out.setReadOnly(True)
        self._out.setMaximumBlockCount(10_000)
        self._out.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        root.addWidget(self._out)

        # ── Input row (hidden while no process is running) ────────────────────
        self._input_row = QWidget()
        self._input_row.setStyleSheet(
            f"background:{BG_PANEL}; border-top:1px solid {BORDER};"
        )
        self._input_row.setFixedHeight(34)
        self._input_row.setVisible(False)

        inp_layout = QHBoxLayout(self._input_row)
        inp_layout.setContentsMargins(8, 3, 8, 3)
        inp_layout.setSpacing(6)

        prompt_lbl = QLabel("›")
        prompt_lbl.setStyleSheet(
            "color:#00b4d8; font-size:16px; font-weight:bold; background:transparent;"
        )
        prompt_lbl.setFixedWidth(14)
        inp_layout.addWidget(prompt_lbl)

        self._input_field = QLineEdit()
        self._input_field.setObjectName("terminal_input")
        self._input_field.setPlaceholderText("Type input() value and press Enter…")
        self._input_field.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._input_field.returnPressed.connect(self._submit_input)
        self._input_field.installEventFilter(self)
        inp_layout.addWidget(self._input_field)

        send_btn = QPushButton("Send")
        send_btn.setObjectName("send_btn")
        send_btn.setFixedHeight(24)
        send_btn.setFixedWidth(52)
        send_btn.setToolTip("Send input to the program (Enter)")
        send_btn.clicked.connect(self._submit_input)
        inp_layout.addWidget(send_btn)

        root.addWidget(self._input_row)

    # ── Settings ──────────────────────────────────────────────────────────────
    def apply_settings(self):
        """Reload font size from settings.json and update the terminal."""
        try:
            from settings import Settings
            cfg = Settings.instance()
            size = int(cfg.get("terminal_font_size", 12))
        except Exception:
            size = 12

        mono = QFont("Cascadia Code", size)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        mono.setFixedPitch(True)
        if not mono.exactMatch():
            mono = QFont("Consolas", size)
            mono.setFixedPitch(True)

        self._out.setFont(mono)
        self._input_field.setFont(mono)

    # ── eventFilter — keyboard navigation in input field ─────────────────────
    def eventFilter(self, obj, event):
        if obj is self._input_field and isinstance(event, QKeyEvent):
            key = event.key()
            mod = event.modifiers()

            # Ctrl+C → KeyboardInterrupt (kill process)
            if key == Qt.Key.Key_C and mod & Qt.KeyboardModifier.ControlModifier:
                self.stop()
                return True

            # Up arrow → older history entry
            if key == Qt.Key.Key_Up:
                self._history_prev()
                return True

            # Down arrow → newer history entry
            if key == Qt.Key.Key_Down:
                self._history_next()
                return True

        return super().eventFilter(obj, event)

    # ── Public API ────────────────────────────────────────────────────────────
    def set_file(self, path: str | None):
        self._current_file = path

    def run(self, file_path: str | None = None):
        """Start executing the Python file."""
        target = file_path or self._current_file
        if not target:
            self._write_err("No file to run — save your file first.\n")
            return
        if not os.path.isfile(target):
            self._write_err(f"File not found: {target}\n")
            return

        # Kill any still-running process first
        if (
            self._process is not None
            and self._process.state() != QProcess.ProcessState.NotRunning
        ):
            self.stop()

        self.clear()
        self._write_info(f"Running: {target}\n{'─' * 60}\n")

        python = self._find_python()

        self._process = QProcess(self)
        self._process.setProcessChannelMode(
            QProcess.ProcessChannelMode.SeparateChannels
        )
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)

        # Run in the script's own directory for correct relative imports
        self._process.setWorkingDirectory(
            os.path.dirname(os.path.abspath(target))
        )

        # Mark subprocess so that any re-entry into main.py is blocked
        env = QProcessEnvironment.systemEnvironment()
        env.insert("CODEZEN_SUBPROCESS", "1")
        self._process.setProcessEnvironment(env)

        # -u: unbuffered stdout/stderr → real-time output streaming
        self._process.start(python, ["-u", target])

        if self._process.waitForStarted(3000):
            self._set_running(True)
            self.process_started.emit()
        else:
            self._write_err(
                f"Failed to start interpreter: {python}\n"
                "Make sure Python is installed and on your PATH.\n"
                "Use Settings → Python Interpreter to select one.\n"
            )
            self._set_running(False)

    def stop(self):
        """Kill the running process immediately."""
        if (
            self._process is not None
            and self._process.state() != QProcess.ProcessState.NotRunning
        ):
            self._process.kill()
            self._process.waitForFinished(2000)

    def clear(self):
        self._out.clear()

    # ── Stdin submission ──────────────────────────────────────────────────────
    def _submit_input(self):
        if (
            self._process is None
            or self._process.state() == QProcess.ProcessState.NotRunning
        ):
            return

        text = self._input_field.text()
        self._input_field.clear()
        self._hist_idx = -1

        # Add non-blank entries to history
        if text.strip():
            if not self._history or self._history[0] != text:
                self._history.insert(0, text)
            if len(self._history) > self._MAX_HISTORY:
                self._history = self._history[:self._MAX_HISTORY]

        # Echo what the user typed
        self._write(text + "\n", _ECHO_COLOR)

        # Write to stdin
        self._process.write((text + "\n").encode("utf-8"))
        self._input_field.setFocus()

    # ── History navigation ────────────────────────────────────────────────────
    def _history_prev(self):
        """Move to an older history entry."""
        if not self._history:
            return
        if self._hist_idx == -1:
            self._pending_input = self._input_field.text()
        new_idx = min(self._hist_idx + 1, len(self._history) - 1)
        if new_idx != self._hist_idx:
            self._hist_idx = new_idx
            self._input_field.setText(self._history[self._hist_idx])
            self._input_field.end(False)

    def _history_next(self):
        """Move to a newer history entry (or restore pending input)."""
        if self._hist_idx == -1:
            return
        new_idx = self._hist_idx - 1
        if new_idx < 0:
            self._hist_idx = -1
            self._input_field.setText(self._pending_input)
            self._input_field.end(False)
        else:
            self._hist_idx = new_idx
            self._input_field.setText(self._history[self._hist_idx])
            self._input_field.end(False)

    # ── Running state helpers ─────────────────────────────────────────────────
    def _set_running(self, running: bool):
        self._run_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)
        self._input_row.setVisible(running)
        if running:
            self._input_field.setFocus()
        self._hist_idx = -1

    # ── Python interpreter discovery ──────────────────────────────────────────
    @staticmethod
    def _find_python() -> str:
        try:
            from interpreter import get_active_interpreter
            return get_active_interpreter()
        except Exception:
            pass

        # Fallback (should not normally be reached)
        if not getattr(sys, "frozen", False):
            exe = sys.executable or ""
            if exe and os.path.isfile(exe):
                name_lower = os.path.basename(exe).lower()
                _ide_names = {"main", "main.exe", "codezen", "codezen.exe",
                              "codezenindia", "codezenindia.exe"}
                if name_lower not in _ide_names:
                    return exe

        for candidate in ("python3", "python"):
            found = shutil.which(candidate)
            if found:
                return found
        return "python3"

    # ── Output helpers ────────────────────────────────────────────────────────
    def _write(self, text: str, color: str = FG_TEXT):
        """Append coloured text (plain, no ANSI) to the output area."""
        cur = self._out.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        fmt = cur.charFormat()
        fmt.setForeground(QColor(color))
        cur.setCharFormat(fmt)
        cur.insertText(text)
        self._out.setTextCursor(cur)
        self._out.ensureCursorVisible()

    def _write_ansi(self, text: str, base_color: str):
        """Write text that may contain ANSI escape codes."""
        cleaned = _strip_other_escapes(text)
        for segment, color in _parse_ansi(cleaned, base_color):
            if segment:
                self._write(segment, color)

    def _write_err(self, text: str):
        self._write_ansi(text, _ERR_COLOR)

    def _write_info(self, text: str):
        self._write(text, _INFO_COLOR)

    def _write_ok(self, text: str):
        self._write(text, _OK_COLOR)

    # ── QProcess signal slots ─────────────────────────────────────────────────
    def _on_stdout(self):
        if self._process:
            data = self._process.readAllStandardOutput().data()
            self._write_ansi(data.decode("utf-8", errors="replace"), _DEFAULT_COLOR)

    def _on_stderr(self):
        if self._process:
            data = self._process.readAllStandardError().data()
            self._write_ansi(data.decode("utf-8", errors="replace"), _ERR_COLOR)

    def _on_finished(self, code: int, status: QProcess.ExitStatus):
        sep = "─" * 60
        if status == QProcess.ExitStatus.NormalExit and code == 0:
            self._write_ok(f"\n{sep}\nProcess finished  (exit code 0)\n")
        else:
            self._write_err(f"\n{sep}\nProcess finished  (exit code {code})\n")
        self._set_running(False)
        self.process_stopped.emit()

    def _on_error(self, error: QProcess.ProcessError):
        _msg = {
            QProcess.ProcessError.FailedToStart: (
                "Failed to start — is Python on PATH?\n"
                "Tip: use Settings → Python Interpreter to select one."
            ),
            QProcess.ProcessError.Crashed:      "Process crashed unexpectedly.",
            QProcess.ProcessError.Timedout:     "Process timed out.",
            QProcess.ProcessError.WriteError:   "Stdin write error.",
            QProcess.ProcessError.ReadError:    "Stdout/stderr read error.",
            QProcess.ProcessError.UnknownError: "Unknown process error.",
        }
        self._write_err(f"\n{_msg.get(error, str(error))}\n")
        self._set_running(False)
        self.process_stopped.emit()
