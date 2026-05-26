# Changelog — CodeZen India

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.1.0] — 2025-05-26

### Added
- **Smart automatic Python interpreter selection** — detects, scores, and
  restores the best available interpreter on every launch; no manual
  reselection required after restart.
- **Python Installer Manager** (new tab in Interpreter Manager dialog) —
  fetches latest stable releases dynamically from python.org, shows
  Install / Update / Reinstall buttons, downloads in a background thread,
  launches the official installer automatically with `InstallAllUsers=1
  PrependPath=1`.
- **Automatic interpreter restoration** — saved interpreter path persists
  across launches; gracefully falls back to the best available alternative
  if the saved path no longer exists.
- **Dynamic Python version fetching** — never hardcoded; always reflects
  the current stable release list from python.org.
- **Smart interpreter badges** — `[ACTIVE]` `[LATEST]` `[RECOMMENDED]`
  `[INSTALLED]` color-coded labels in the Select Interpreter tab.
- **Quick-select interpreter popup menu** — single click on the status-bar
  interpreter label opens a lightweight VS Code-style popup listing all
  detected interpreters with a checkmark on the active one; `⚙ Manage
  Interpreters…` at the bottom opens the full dialog.
- **Friendly interpreter label** — status bar now shows
  `🐍  Python 3.11.4 (System)` instead of the raw executable filename.
- **Background interpreter cache** — interpreter scan runs 800 ms after
  startup in a background thread so it never delays window display.

### Fixed
- **Shift key autocomplete bug** — pressing Shift alone no longer triggers
  the autocomplete popup.
- **Shift+Enter editor behavior** — Shift+Enter now correctly inserts a
  smart-indent newline instead of being swallowed by the completer popup.
- Standalone modifier keys (Ctrl, Alt, Meta, CapsLock) no longer trigger
  autocomplete or interfere with normal editing.

### Improved
- Autocomplete popup is hidden correctly when Shift+Enter is pressed while
  it is visible, giving smooth, professional editor feel.
- Interpreter discovery additionally scans `%ProgramFiles%\Python` and
  user `%LOCALAPPDATA%\Programs\Python` subdirectories (sorted, newest
  first), improving detection on all common Windows layouts.
- WindowsApps Microsoft Store Python aliases are blocked at every
  check-point — they are never exposed to the user.
- Low-end-PC performance preserved: no bundled runtime, no heavy startup
  work, all expensive operations are deferred to background threads.

---

## [1.0.0] — 2025-05-25

### Added
- Initial release.
- VS Code-inspired dark theme PyQt6 IDE.
- Multi-tab code editor with Python syntax highlighting.
- Smart auto-indent, auto-close brackets/quotes.
- Dynamic autocomplete (keywords + document words).
- Line numbers with active-line highlight.
- Integrated output terminal with full ANSI colour support.
- Interactive `input()` support via stdin field.
- File explorer with drag-and-drop.
- Find & Replace dialog.
- Python interpreter manager (scan, browse, select).
- Auto-update system via GitHub Releases.
- Persistent settings (font, tab width, workspace, recent projects).
- PyInstaller EXE packaging support (`CodeZenIndia.spec`).
- Inno Setup Windows installer script (`installer.iss`).
