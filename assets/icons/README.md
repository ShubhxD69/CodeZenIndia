# assets/icons/

This folder holds the application icon for CodeZen India.

## Generate logo.ico

Run the generator script once (requires PyQt6, which is already installed):

```cmd
cd CodeZenIndia
python create_icon.py
```

This creates `logo.ico` containing the CodeZen India logo at 7 sizes:
`16 × 16`, `24 × 24`, `32 × 32`, `48 × 48`, `64 × 64`, `128 × 128`, `256 × 256`

## Where it is used

| Location | How |
|---|---|
| Title bar | `QMainWindow.setWindowIcon(QIcon("assets/icons/logo.ico"))` |
| Taskbar / Alt+Tab | `QApplication.setWindowIcon(...)` + Windows AppUserModelID |
| EXE file icon | `icon='assets/icons/logo.ico'` in `CodeZenIndia.spec` |
| Splash screen | Rendered dynamically in code (no file needed) |

## Custom icon

Replace `logo.ico` with any standard Windows ICO file (256×256 recommended).
Then rebuild with `pyinstaller CodeZenIndia.spec`.
