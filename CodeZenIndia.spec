# CodeZenIndia.spec — PyInstaller build specification
#
# Prerequisites
# ─────────────
#   1. Install requirements:
#          pip install -r requirements.txt
#   2. Generate the icon (one-time, needs PyQt6):
#          python create_icon.py
#   3. Build:
#          pyinstaller CodeZenIndia.spec
#
# Output:  dist\CodeZen India.exe
#
# Notes
# ─────
#  • console=False  → windowed EXE, no black console window
#  • upx=True       → smaller binary if UPX is on PATH (https://upx.github.io/)
#  • All new modules (settings, updater, interpreter) are auto-collected
#    via Analysis; they do NOT need to be listed in hiddenimports.

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Bundle the icon so QIcon() can load it at runtime inside the EXE
        ('assets/icons/logo.ico', 'assets/icons'),
        # Bundle settings.json if it exists (allows shipping defaults)
        # ('settings.json', '.'),
    ],
    hiddenimports=[
        # PyQt6 core modules
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtNetwork',
        'PyQt6.QtPrintSupport',
        'PyQt6.sip',
        # Project modules (explicit to help PyInstaller's static analysis)
        'settings',
        'updater',
        'interpreter',
        'terminal',
        'editor',
        'explorer',
        'syntax',
        'theme',
        'main_window',
        # requests and its dependencies (used by updater)
        'requests',
        'requests.adapters',
        'requests.auth',
        'requests.cookies',
        'requests.exceptions',
        'requests.models',
        'requests.sessions',
        'urllib3',
        'certifi',
        'charset_normalizer',
        'idna',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'unittest', 'html',
        'xmlrpc', 'pydoc', 'doctest', 'test',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CodeZen India',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icons/logo.ico',
    version_file=None,           # set to a version_info.txt for Windows details
)
