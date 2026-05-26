# CodeZen India

A modern, lightweight Python IDE built with PyQt6 — designed for Windows, optimized for low-end PCs, and beginner-friendly.

## Version 1.1.0

### What's New in v1.1.0

- **Smart Automatic Interpreter Selection** — detects and restores the best available Python interpreter on every launch, no manual reselection needed
- **Python Installer Manager** — fetch, install, and update Python directly from python.org inside the IDE
- **Automatic Interpreter Restoration** — saved interpreter persists across launches; falls back gracefully if it no longer exists
- **Dynamic Python Version Fetching** — always shows the latest stable releases, never hardcoded
- **Smart Interpreter Badges** — ACTIVE, LATEST, RECOMMENDED, INSTALLED badges in the interpreter dialog
- **Fixed: Shift Key Autocomplete Bug** — pressing Shift alone no longer triggers the autocomplete popup
- **Fixed: Shift+Enter Behavior** — Shift+Enter now correctly inserts a newline with smart indent
- **Improved Autocomplete Stability** — no popup flickering, no typing lag, proper key propagation
- **Improved Low-End-PC Compatibility** — no bundled Python runtime, minimal RAM/CPU usage

---

## Features

- VS Code-inspired dark theme
- Multi-tab code editor with syntax highlighting
- Smart auto-indent and auto-close brackets/quotes
- Dynamic autocomplete (keywords + document words)
- Line numbers with active-line highlight
- Integrated output terminal with ANSI colour support
- Interactive `input()` support with stdin field
- File explorer with drag-and-drop
- Find & Replace dialog
- Python interpreter manager with install support
- Auto-update system via GitHub Releases
- Persistent settings (font size, tab width, workspace)
- Recent projects list

---

## Requirements

- Windows 10 / 11
- Python 3.9 or later (installed separately — CodeZen India is lightweight by design)
- PyQt6

## Installation

```bash
pip install pyqt6 requests
python main.py
```

## Building (PyInstaller)

```bash
pyinstaller --clean CodeZenIndia.spec
```

---

## Python Interpreter Manager

Open via **Edit → Python Interpreter…** or **Run → Select Python Interpreter…**

**Select Interpreter tab:**  
Scans for all installed Python interpreters on your system.  
Badges shown: `[ACTIVE]` `[LATEST]` `[RECOMMENDED]` `[INSTALLED]`

**Install / Update Python tab:**  
Fetches stable releases from python.org dynamically.  
Click **Install** to download and launch the official installer automatically.  
After installation, click **↺ Refresh** to detect the new Python.

---

## Developed By Shubh Mishra
