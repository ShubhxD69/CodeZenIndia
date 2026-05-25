# CodeZen India

**Professional Python IDE — built with PyQt6**

Developed by **Shubh Mishra** · [github.com/ShubhxD69](https://github.com/ShubhxD69)

---

## Features

| Category | Details |
|----------|---------|
| **Editor** | Syntax highlighting, line numbers, active-line highlight, smart auto-indent, bracket/quote auto-close, Ctrl+Space autocomplete, dynamic word list |
| **Tabs** | Multi-tab editing, middle-click close, Ctrl+W, `*` unsaved indicator, drag-to-reorder |
| **Terminal** | Real-time stdout/stderr, interactive `input()`, ANSI colour codes, command history (↑/↓), Ctrl+C interrupt |
| **Interpreter** | Detects system Python, virtual envs (`.venv`/`venv`/`env`), Conda envs; browse for custom path; persists in settings |
| **Explorer** | Project folder tree, context menu (new/rename/delete), drag-and-drop, auto-restores last folder |
| **Settings** | Font size, tab size, word wrap, auto-save, terminal font, update channel — all persisted in `settings.json` |
| **Updater** | Background GitHub-JSON version check, changelog dialog, streamed installer download |
| **Theme** | VS Code-inspired dark theme, animated splash screen, clickable developer status-bar badge |

---

## Requirements

| Package | Minimum version |
|---------|----------------|
| Python | 3.10+ |
| PyQt6 | 6.6.0+ |
| requests | 2.31.0+ |

---

## Quick Start — Run from Source

```bash
# 1. Clone or extract the project
git clone https://github.com/ShubhxD69/CodeZenIndia
cd CodeZenIndia

# 2. Install runtime dependencies
pip install PyQt6>=6.6.0 requests>=2.31.0

# 3. Launch
python main.py
```

A 2-second animated splash screen appears, then the full IDE opens.

---

## Running a Python File

1. Open a `.py` file — **Ctrl+O** or double-click in the Explorer panel
2. Press **F5** or click **▶ Run** in the toolbar
3. Output streams in real time in the terminal panel below
4. For interactive programs: type your input in the bottom field and press **Enter**
5. Press **■ Stop** or **Shift+F5** to kill the process

---

## Keyboard Shortcuts

| Keys | Action |
|------|--------|
| `Ctrl+N` | New file |
| `Ctrl+O` | Open file |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+W` | Close current tab |
| `Ctrl+H` | Find / Replace |
| `Ctrl+,` | Preferences |
| `F5` | Run current file |
| `Shift+F5` | Stop execution |
| `Ctrl+B` | Toggle Explorer panel |
| `Ctrl+J` | Toggle Terminal panel |
| `Ctrl+Space` | Force autocomplete popup |
| `Ctrl+Z` / `Ctrl+Y` | Undo / Redo |
| `Tab` / `Shift+Tab` | Indent / de-indent selection |
| `↑` / `↓` (terminal) | Navigate command history |
| `Ctrl+C` (terminal) | Send keyboard interrupt |
| `Ctrl+Q` | Quit |

---

## Project Structure

```
CodeZenIndia/
├── main.py               Entry point — splash, QApplication, start-up sequence
├── main_window.py        MainWindow — menus, toolbar, status bar, signal wiring
├── editor.py             CodeEditor + EditorTabWidget (multi-tab)
├── terminal.py           Integrated interactive terminal (QProcess-based)
├── explorer.py           File explorer sidebar (QFileSystemModel)
├── interpreter.py        Interpreter detection + InterpreterManagerDialog
├── settings.py           Persistent settings singleton + SettingsDialog
├── syntax.py             Python QSyntaxHighlighter
├── theme.py              VS Code dark colour palette + full QSS stylesheet
├── updater.py            Auto-update system (GitHub JSON check + download)
├── create_icon.py        Generates assets/icons/logo.ico from Python code
├── assets/
│   └── icons/
│       ├── logo.ico              Application icon (generate with create_icon.py)
│       ├── tab_close.svg         Tab close button — grey ×
│       └── tab_close_hover.svg   Tab close button hover — white ×
├── requirements.txt      Runtime + build dependencies
├── CodeZenIndia.spec     PyInstaller EXE build spec
├── installer.iss         Inno Setup Windows installer script
├── version.json          Current version tag (used by build pipeline)
├── README.md             This file
├── BUILD.md              Full EXE + installer + release workflow guide
└── settings.json         Auto-created on first run (stores user preferences)
```

---

## Configuration

All preferences live in `settings.json` (auto-created next to `main.py` or the `.exe`).

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `font_size` | int | 13 | Editor font size in pt |
| `tab_size` | int | 4 | Spaces per Tab keypress |
| `word_wrap` | bool | false | Editor word wrap |
| `auto_save` | bool | false | Auto-save file before running |
| `interpreter_path` | str | `""` | Active Python executable path |
| `auto_update` | bool | true | Check for updates on startup |
| `update_channel` | str | `"stable"` | `"stable"` or `"beta"` |
| `terminal_font_size` | int | 12 | Terminal font size in pt |
| `last_workspace` | str | `""` | Last opened folder (auto-restored) |

Delete `settings.json` to reset everything to defaults.

---

## Python Interpreter Selection

Access via any of:
- **Edit → Python Interpreter…**
- **Run → Select Python Interpreter…**
- Click the interpreter label in the **status bar**

The dialog auto-scans for system Python, virtual environments, and Conda environments.
Use **Browse…** to locate a custom `python.exe`. The selection persists in `settings.json`.

---

## Build a Standalone EXE

```bash
python create_icon.py          # generate icon (first time only)
pyinstaller CodeZenIndia.spec  # build the EXE bundle
```

Output: `dist\CodeZenIndia\CodeZenIndia.exe`

See **BUILD.md** for the complete build, installer, and release workflow.

---

## License

MIT License — free to use, modify, and distribute.
