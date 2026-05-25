# CodeZen India — Final Production Audit Report

**Date:** 2026-05-25
**Version audited:** 1.0.0
**Files audited:** `main.py`, `main_window.py`, `editor.py`, `terminal.py`, `explorer.py`, `interpreter.py`, `settings.py`, `syntax.py`, `theme.py`, `updater.py`

---

## Executive Summary

| Check | Result |
|-------|--------|
| Application launches without crash | PASS |
| No `sipBadCatcherResult()` errors | PASS — fixed |
| No Qt stylesheet warnings | PASS — fixed |
| PyQt6 enum usage correct | PASS |
| Signal connections (no duplicates) | PASS |
| Event handler overrides safe | PASS — fixed |
| Deferred/misplaced imports | PASS — fixed (7 removed) |
| Resource leaks | PASS — fixed (1 removed) |
| Interpreter manager accessible | PASS — added to Edit menu |
| Terminal stdin / interactive input | PASS |
| Settings persistence | PASS |
| Updater (no-internet handling) | PASS |
| Dead code | PASS — none found |
| Unused imports | PASS — none remain |

---

## Issues Found and Resolved

### Issue 1 — Qt Stylesheet `cursor:pointer` Warning

- **Severity:** Warning (console spam)
- **File:** `main_window.py`
- **Location:** Interpreter status-bar label stylesheet string
- **Root cause:** Qt's QSS engine does not support the CSS `cursor:` property. Using it produces an `Unknown property: cursor` warning on every widget paint cycle.
- **Fix:** Removed `cursor:pointer` from the stylesheet string. Added `widget.setCursor(Qt.CursorShape.PointingHandCursor)` in Python code instead.
- **Status:** RESOLVED

---

### Issue 2 — `sipBadCatcherResult()` Runtime Crash

- **Severity:** Critical (crash on hover)
- **File:** `main_window.py`
- **Location:** Brand label and interpreter label event overrides
- **Root cause:** PyQt6/SIP validates the C++ virtual override return signature at runtime. When `enterEvent` and `leaveEvent` are monkey-patched via `widget.enterEvent = lambda _: ...`, SIP rejects the override because the lambda's return annotation does not match the expected `void` (C++ `None`) type signature strictly enough in certain PyQt6 6.6+ builds.
- **Fix:** Introduced `_StatusBarLabel(QLabel)` subclass with proper `def enterEvent(self, event):` / `def leaveEvent(self, event):` / `def mousePressEvent(self, event):` overrides, each calling `super()`. Applied to both the interpreter label and the developer brand label.
- **Status:** RESOLVED

---

### Issue 3 — `import re` Deferred Inside Hot-Path Method

- **Severity:** Minor (style / correctness)
- **File:** `editor.py`
- **Location:** `_rebuild_word_list()` — called on a 500 ms debounce timer while typing
- **Root cause:** `import re` was placed inside the method body. Although Python caches module imports after the first call, the lookup overhead is unnecessary inside a frequently-called function, and it violates PEP 8 import ordering.
- **Fix:** Moved `import re` to module top-level.
- **Status:** RESOLVED

---

### Issue 4 — `import subprocess` Deferred in `updater.py`

- **Severity:** Minor (style / correctness)
- **File:** `updater.py`
- **Location:** `_on_download_done()` — inside the download-completion callback
- **Root cause:** `import subprocess` placed inside the method body.
- **Fix:** Moved to module top-level imports.
- **Status:** RESOLVED

---

### Issue 5 — `from theme import FG_MUTED` Deferred in `updater.py`

- **Severity:** Minor (style)
- **File:** `updater.py`
- **Location:** `_build_ui()` method
- **Fix:** Added `from theme import FG_MUTED` to module top-level; removed deferred import.
- **Status:** RESOLVED

---

### Issue 6 — Four Deferred Theme Imports in `settings.py`

- **Severity:** Minor (style)
- **File:** `settings.py`
- **Locations:**
  - `_build_ui()` → `from theme import BORDER`
  - `_tab_terminal()` → `from theme import FG_MUTED`
  - `_tab_updates()` → `from theme import FG_MUTED`
  - `_tab_workspace()` → `from theme import FG_MUTED`
- **Fix:** Added `from theme import BORDER, FG_MUTED` to module top-level; removed all four deferred imports.
- **Status:** RESOLVED

---

### Issue 7 — File Handle Resource Leak in `explorer.py`

- **Severity:** Minor (resource safety)
- **File:** `explorer.py`
- **Location:** `_new_file()` — `open(full, "w", encoding="utf-8").close()`
- **Root cause:** The file handle is not guaranteed to close if an exception occurs between `open()` and `.close()`. The CPython garbage collector will eventually close it, but this is not reliable in PyPy and creates a resource-warning in strict mode.
- **Fix:** Replaced with `with open(full, "w", encoding="utf-8"): pass` (context manager guarantees close on any exit path).
- **Status:** RESOLVED

---

### Issue 8 — Interpreter Manager Not in Edit Menu

- **Severity:** UX (discoverability)
- **File:** `main_window.py`
- **Location:** Edit menu construction
- **Root cause:** Interpreter manager was only reachable via Run menu and status-bar click. Users expecting it near Preferences could not find it.
- **Fix:** Added `Edit → Python Interpreter…` menu item directly above `Preferences…`.
- **Status:** RESOLVED

---

## No Issues Found In

| File | Notes |
|------|-------|
| `main.py` | Clean startup sequence; `_resource()` helper correct for frozen EXE |
| `theme.py` | No `cursor:` in QSS; `_icon_url()` helper produces correct forward-slash URLs for both source and EXE |
| `terminal.py` | QProcess lifecycle correct; `_set_running()` properly enables/disables UI; no signal leaks |
| `interpreter.py` | `_ScanThread` correctly parented to dialog; `done` signal connected once per scan; `_probe_version()` has correct timeout |
| `syntax.py` | Standard `QSyntaxHighlighter` pattern; no issues |
| `explorer.py` (remainder) | Drag-drop, context menu, rename, delete all clean |
| `editor.py` (remainder) | `_ClosableTabBar` subclass correct; `deleteLater()` used correctly in `_close_tab` |

---

## PyQt6 Compatibility Verification

| Pattern | Status |
|---------|--------|
| Enum: `Qt.CursorShape.PointingHandCursor` | Correct |
| Enum: `Qt.MouseButton.LeftButton` | Correct |
| Enum: `QProcess.ProcessChannelMode.SeparateChannels` | Correct |
| Enum: `Qt.DockWidgetArea.LeftDockWidgetArea` | Correct |
| Enum: `QAbstractItemView.EditTrigger.NoEditTriggers` | Correct |
| `QFileSystemModel` from `PyQt6.QtGui` | Correct (moved from `QtWidgets` in PyQt6) |
| `QTextEdit.ExtraSelection` for current-line highlight | Correct |
| `QCompleter.CompletionMode.PopupCompletion` | Correct |
| All event overrides call `super()` | Confirmed |

---

## Signal Safety

| Signal | Connected | Where |
|--------|-----------|-------|
| `tabCloseRequested` | Once | `EditorTabWidget.__init__` |
| `currentChanged` | Once | `EditorTabWidget.__init__` |
| `_ScanThread.done` | Once per scan | `_start_scan()` — thread re-created each time |
| `interpreter_changed` | Once per dialog open | `_open_interpreter_manager()` |
| `process.*` signals | Once per run | `Terminal.run()` — process re-created each time |
| `update_available` / `up_to_date` | Once per check | `check_for_updates()` — thread local variable |

No duplicate connections detected.

---

## Memory & Resource Safety

| Item | Status |
|------|--------|
| `deleteLater()` on closed tab editors | Used correctly in `_close_tab()` |
| `_paths` / `_dirty` dicts cleaned on close | Confirmed |
| QProcess killed before re-use | `Terminal.run()` calls `self.stop()` if process is still running |
| File handles in `_new_file()` | Fixed — now uses context manager |
| `_ScanThread` parented to dialog | Confirmed — auto-cleaned when dialog closes |
| `_update_thread` reference kept on `MainWindow` | Confirmed — prevents premature GC |

---

*Generated by CodeZen India Production Audit — v1.0.0 · 2026-05-25*
