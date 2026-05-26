# CodeZen India v1.1.0 — Build Note

## About This Package

This is the **source distribution** of CodeZen India v1.1.0.

The Windows executable (`CodeZenIndia.exe`) and installer (`CodeZenIndiaSetup.exe`)
must be compiled on a Windows machine using the steps below.

---

## Building the Windows EXE (PyInstaller)

### Prerequisites

```
pip install pyqt6 pyinstaller requests
```

### Build Command

```
pyinstaller --clean CodeZenIndia.spec
```

The compiled EXE will appear at `dist\CodeZenIndia.exe`.

---

## Building the Windows Installer (Inno Setup)

1. Install [Inno Setup](https://jrsoftware.org/isinfo.php) on Windows.
2. Open `installer.iss` in Inno Setup Compiler.
3. Click **Build → Compile**.
4. The installer `CodeZenIndiaSetup.exe` will be generated in the `Output\` folder.

---

## Running from Source (No Build Required)

```
pip install pyqt6 requests
python main.py
```

---

## Final Release ZIP Structure (after building on Windows)

```
CodeZenIndia_v1.1.0_Production.zip
├── CodeZenIndia.exe          (from dist\ after PyInstaller build)
├── CodeZenIndiaSetup.exe     (from Output\ after Inno Setup compile)
├── README.md
├── LICENSE
├── CHANGELOG.md
└── version.json
```
