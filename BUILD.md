# CodeZen India — Build, Package & Release Guide

Complete instructions for building, packaging, distributing, and releasing CodeZen India.

---

## 1. Development Setup

```bash
# Install all dependencies (runtime + build tools)
pip install -r requirements.txt

# Verify the app runs from source
python main.py
```

`requirements.txt` breakdown:

| Package | Role |
|---------|------|
| `PyQt6>=6.6.0` | GUI framework (runtime) |
| `requests>=2.31.0` | HTTP for the auto-updater (runtime) |
| `pyinstaller>=6.3.0` | EXE bundler (build-time only) |

---

## 2. Project Structure

```
CodeZenIndia/
├── main.py               Entry point — splash, QApplication, start-up
├── main_window.py        MainWindow — menus, toolbar, status bar, wiring
├── editor.py             CodeEditor + EditorTabWidget (multi-tab)
├── terminal.py           Integrated interactive terminal (QProcess)
├── explorer.py           File explorer sidebar (QFileSystemModel)
├── interpreter.py        Interpreter detection + manager dialog
├── settings.py           Persistent settings singleton + Preferences dialog
├── syntax.py             Python QSyntaxHighlighter
├── theme.py              VS Code dark colour palette + full QSS stylesheet
├── updater.py            Auto-update system (GitHub JSON + download)
├── create_icon.py        Generates assets/icons/logo.ico from code
├── assets/icons/         SVG tab-close buttons + logo.ico
├── requirements.txt      Runtime + build dependencies
├── CodeZenIndia.spec     PyInstaller build spec
├── installer.iss         Inno Setup Windows installer script
├── version.json          Current version tag
├── README.md             User-facing documentation
└── BUILD.md              This file
```

---

## 3. Generate the Application Icon

The icon is created entirely in Python — no image editor required:

```bash
python create_icon.py
# Output: assets/icons/logo.ico
```

Run this once before every EXE build to ensure the icon matches the current version.

---

## 4. Build the Standalone Windows EXE

### Recommended — use the spec file

```bash
pyinstaller CodeZenIndia.spec
```

Output: `dist\CodeZenIndia\CodeZenIndia.exe` (one-folder bundle for fast start-up)

### Quick one-liner (no spec file)

```bash
pyinstaller --onefile --windowed --name "CodeZenIndia" ^
    --icon=assets/icons/logo.ico ^
    --add-data "assets;assets" ^
    --add-data "version.json;." ^
    main.py
```

### UPX compression (optional — smaller EXE)

- Download UPX from [upx.github.io](https://upx.github.io/)
- Place `upx.exe` on your PATH or in the project folder
- `upx=True` is already set in `CodeZenIndia.spec`

### EXE Build Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: PyQt6` | `pip install PyQt6` then rebuild |
| Icon not found | Run `python create_icon.py` first |
| App crashes silently | Set `console=True` in spec temporarily to see the traceback |
| Missing Visual C++ DLLs | Install the Visual C++ Redistributable on the target machine |
| Tab close buttons invisible | Ensure `assets/icons/` is included in the spec `datas` list |

---

## 5. Build the Windows Installer

Requires [Inno Setup 6](https://jrsoftware.org/isinfo.php) installed.

```bash
# After building the EXE:
iscc installer.iss
# Output: Output\CodeZenIndiaSetup_v1.0.0.exe
```

`installer.iss` configures:
- Install directory: `C:\Program Files\CodeZen India\`
- Desktop shortcut
- Start Menu entry
- Uninstaller registration

---

## 6. GitHub Auto-Updater Setup

The built-in updater checks a JSON file on GitHub at startup.

### Step 1 — Create `update.json` in your repository

Place this file at the root of your `main` branch (or host it as a GitHub Release asset):

```json
{
  "version": "1.1.0",
  "download_url": "https://github.com/ShubhxD69/CodeZenIndia/releases/download/v1.1.0/CodeZenIndiaSetup_v1.1.0.exe",
  "changelog": "- New feature: multi-cursor editing\n- Fixed: terminal flicker on Windows 11\n- Improved: startup time reduced by 40%"
}
```

### Step 2 — Set `UPDATE_URL` in `updater.py`

```python
UPDATE_URL = (
    "https://raw.githubusercontent.com/ShubhxD69/CodeZenIndia"
    "/main/update.json"
)
```

### Step 3 — Beta channel (optional)

Create `update-beta.json` at the same base URL.  
The updater automatically requests the beta filename when the user selects the beta channel in Preferences → Updates.

### Step 4 — Verify the URL

Open the raw URL in a browser — it must return the JSON directly (not an HTML page).

---

## 7. Version Release Workflow

Follow these steps for every release.

### 7.1 — Bump the version number

Update the version string in **three files**:

| File | Variable |
|------|----------|
| `main.py` | `APP_VERSION = "X.Y.Z"` |
| `main_window.py` | `APP_VERSION = "X.Y.Z"` |
| `updater.py` | `APP_VERSION = "X.Y.Z"` |

Also update `version.json`:
```json
{ "version": "X.Y.Z" }
```

### 7.2 — Build and smoke-test

```bash
python create_icon.py
pyinstaller CodeZenIndia.spec
# Test the EXE: dist\CodeZenIndia\CodeZenIndia.exe
```

### 7.3 — Build the installer

```bash
iscc installer.iss
# Test the installer: Output\CodeZenIndiaSetup_vX.Y.Z.exe
```

### 7.4 — Create a GitHub Release

1. Create a git tag: `vX.Y.Z`
2. Create a GitHub Release from that tag
3. Upload: `Output\CodeZenIndiaSetup_vX.Y.Z.exe`
4. Update `update.json` in the repo:
   - Set `"version"` to `"X.Y.Z"`
   - Set `"download_url"` to the uploaded installer URL
   - Write the `"changelog"` text

### 7.5 — Verify the auto-updater end-to-end

1. Install the **previous** version
2. Launch it
3. The update dialog should appear within a few seconds
4. Download and install — confirm the new version launches correctly

---

## 8. Recursive-Launch Protection

CodeZen India has three safeguards to prevent the IDE from accidentally relaunching itself when a user runs a Python file:

1. **`CODEZEN_SUBPROCESS` env var** — `QProcess` stamps every child process with this variable; `main.py` exits immediately if it detects it on startup
2. **Frozen-EXE guard** — `_find_python()` in `terminal.py` never returns `sys.executable` when the process is frozen (PyInstaller sets `sys.frozen = True`)
3. **IDE name blacklist** — `get_active_interpreter()` in `interpreter.py` refuses to return a path whose basename matches known IDE executable names

---

## 9. Troubleshooting Guide

### App won't start from source

```bash
python --version          # must be 3.10+
python -c "import PyQt6; print(PyQt6.__version__)"
python -c "import requests; print(requests.__version__)"
```

### Terminal shows "Failed to start interpreter"

1. Open **Edit → Python Interpreter…** (or click the interpreter name in the status bar)
2. Check the list — if empty, click **↺ Refresh**
3. If still empty, click **Browse…** and locate `python.exe` manually
4. Or install Python from [python.org](https://python.org) and restart CodeZen India

### Auto-update fails silently

- Confirm internet access
- Open the `UPDATE_URL` in a browser — it must return raw JSON
- Check **Preferences → Updates** — auto-update may be disabled
- Verify `update.json` is valid (no trailing commas, correct structure)

### Tab close button (×) not visible

- `assets/icons/tab_close.svg` and `tab_close_hover.svg` must exist
- When building an EXE, verify the `assets/` folder is in the spec `datas` list
- The tab bar uses `url()` paths generated by `theme.py:_icon_url()` — these are absolute paths that work in both source and EXE modes

### Settings not persisting

- `settings.json` is saved next to `main.py` (source) or next to the `.exe`
- The directory must be writable by the current user
- Delete `settings.json` to reset all preferences to defaults

### Antivirus flags the EXE

Normal for PyInstaller builds. Options:
1. Add a Windows Defender / antivirus exclusion
2. Code-sign the EXE with a trusted certificate (eliminates SmartScreen warnings)
3. Submit to antivirus vendors for whitelisting

---

## 10. System Requirements (Deployment)

| Component | Minimum |
|-----------|---------|
| OS | Windows 10 64-bit (also runs on Windows 11, Linux, macOS) |
| RAM | 128 MB |
| Disk | 80 MB (EXE bundle) |
| Python | Not required for the EXE; 3.10+ for running from source |
| Visual C++ | Visual C++ Redistributable 2015–2022 (usually pre-installed) |

---

## 11. Project Info

| Field | Value |
|-------|-------|
| App name | CodeZen India |
| Version | 1.0.0 |
| Developer | Shubh Mishra |
| GitHub | [github.com/ShubhxD69](https://github.com/ShubhxD69) |
| Stack | Python 3.10+ · PyQt6 6.6+ · requests 2.31+ · PyInstaller 6.3+ |
| Installer | Inno Setup 6 |

---

*CodeZen India — Developed By Shubh Mishra*
