# theme.py — Color palette and stylesheet for CodeZen India
# VS Code-inspired dark theme

import os as _os

# Resolve the project root at import time so icon URLs in the stylesheet
# work correctly both when running from source and inside a frozen EXE.
_PROJECT_ROOT = _os.path.dirname(_os.path.abspath(__file__))


def _icon_url(rel: str) -> str:
    """Return a forward-slash path for a Qt stylesheet url() call."""
    return _os.path.join(_PROJECT_ROOT, "assets", "icons", rel).replace("\\", "/")


# ─── Color Palette ────────────────────────────────────────────────────────────
BG_DARK       = "#1e1e1e"   # main editor background
BG_PANEL      = "#252526"   # sidebar / panels
BG_TAB_ACTIVE = "#1e1e1e"   # active tab background
BG_TAB_IDLE   = "#2d2d2d"   # inactive tab background
BG_TOOLBAR    = "#3c3c3c"   # toolbar
BG_STATUSBAR  = "#007acc"   # status bar (VS Code blue)
BG_INPUT      = "#3c3c3c"   # input fields
BG_HOVER      = "#094771"   # hover highlight

FG_TEXT       = "#d4d4d4"   # normal text
FG_MUTED      = "#858585"   # muted / line numbers
FG_WHITE      = "#ffffff"   # white text
FG_ACCENT     = "#569cd6"   # accent blue

BORDER        = "#474747"   # border color
SELECTION     = "#264f78"   # editor selection
CURSOR        = "#aeafad"   # cursor line tint

# ─── Syntax Colors ────────────────────────────────────────────────────────────
SYN_KEYWORD   = "#569cd6"   # keywords (def, class, if, …)
SYN_BUILTIN   = "#4ec9b0"   # built-in names
SYN_STRING    = "#ce9178"   # strings
SYN_COMMENT   = "#6a9955"   # comments
SYN_NUMBER    = "#b5cea8"   # numbers
SYN_CLASS     = "#4ec9b0"   # class names
SYN_FUNC      = "#dcdcaa"   # function names
SYN_DECORATOR = "#c586c0"   # decorators
SYN_IMPORT    = "#c586c0"   # import / from
SYN_SELF      = "#9cdcfe"   # self / cls

# ─── Main Application Stylesheet ─────────────────────────────────────────────
APP_STYLE = f"""
/* ── Global ── */
QWidget {{
    background-color: {BG_DARK};
    color: {FG_TEXT};
    font-family: "Segoe UI", "Consolas", sans-serif;
    font-size: 13px;
    border: none;
    outline: none;
}}

/* ── Main window splitter handle ── */
QSplitter::handle {{
    background-color: {BORDER};
    width: 1px;
    height: 1px;
}}

/* ── Toolbar ── */
QToolBar {{
    background-color: {BG_TOOLBAR};
    border-bottom: 1px solid {BORDER};
    spacing: 4px;
    padding: 3px 6px;
}}
QToolBar QToolButton {{
    background-color: transparent;
    color: {FG_TEXT};
    border: none;
    border-radius: 4px;
    padding: 5px 10px;
    font-size: 13px;
    min-width: 28px;
}}
QToolBar QToolButton:hover {{
    background-color: {BG_HOVER};
    color: {FG_WHITE};
}}
QToolBar QToolButton:pressed {{
    background-color: #0e6191;
}}
QToolBar QToolButton:disabled {{
    color: {FG_MUTED};
}}
QToolBar::separator {{
    background: {BORDER};
    width: 1px;
    margin: 4px 6px;
}}

/* ── Menu bar ── */
QMenuBar {{
    background-color: {BG_PANEL};
    color: {FG_TEXT};
    border-bottom: 1px solid {BORDER};
    padding: 2px;
}}
QMenuBar::item {{
    padding: 4px 10px;
    border-radius: 3px;
}}
QMenuBar::item:selected {{
    background-color: {BG_HOVER};
}}
QMenu {{
    background-color: {BG_PANEL};
    color: {FG_TEXT};
    border: 1px solid {BORDER};
    padding: 4px 0;
}}
QMenu::item {{
    padding: 5px 24px 5px 12px;
}}
QMenu::item:selected {{
    background-color: {BG_HOVER};
    color: {FG_WHITE};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 0;
}}

/* ── Tab bar — VS Code-inspired ── */
QTabWidget::pane {{
    border: none;
    background: {BG_DARK};
}}
QTabBar {{
    background: {BG_PANEL};
    border-bottom: 1px solid {BORDER};
}}
QTabBar::tab {{
    background: {BG_TAB_IDLE};
    color: #9d9d9d;
    padding: 0px 6px 0px 14px;
    height: 35px;
    border-right: 1px solid {BG_PANEL};
    border-top: 2px solid transparent;
    min-width: 100px;
    max-width: 200px;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    background: {BG_TAB_ACTIVE};
    color: {FG_WHITE};
    border-top: 2px solid {FG_ACCENT};
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BG_TAB_ACTIVE};
}}
QTabBar::tab:!selected {{
    margin-top: 2px;
    border-top: 2px solid #3c3c3c;
}}
QTabBar::tab:hover:!selected {{
    background: #313131;
    color: #d4d4d4;
    border-top: 2px solid #555555;
}}
/* Close (×) button — custom SVG for reliable visibility on dark tabs */
QTabBar::close-button {{
    image: url({_icon_url("tab_close.svg")});
    subcontrol-position: right;
    subcontrol-origin: padding;
    width: 14px;
    height: 14px;
    border-radius: 3px;
    margin-left: 6px;
    margin-right: 4px;
}}
QTabBar::close-button:hover {{
    image: url({_icon_url("tab_close_hover.svg")});
    background: #c42b1c;
    border-radius: 3px;
}}
QTabBar::close-button:pressed {{
    image: url({_icon_url("tab_close_hover.svg")});
    background: #8b1a1a;
    border-radius: 3px;
}}

/* ── File explorer tree ── */
QTreeView {{
    background-color: {BG_PANEL};
    color: {FG_TEXT};
    border: none;
    font-size: 13px;
    show-decoration-selected: 1;
}}
QTreeView::item {{
    padding: 3px 4px;
    border-radius: 3px;
}}
QTreeView::item:hover {{
    background-color: #2a2d2e;
}}
QTreeView::item:selected {{
    background-color: {BG_HOVER};
    color: {FG_WHITE};
}}
QTreeView::branch {{
    background: transparent;
}}

/* ── Scrollbars ── */
QScrollBar:vertical {{
    background: {BG_PANEL};
    width: 10px;
    border: none;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: #555;
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #777;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {BG_PANEL};
    height: 10px;
    border: none;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: #555;
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #777;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Status bar ── */
QStatusBar {{
    background-color: {BG_STATUSBAR};
    color: {FG_WHITE};
    font-size: 12px;
    padding: 2px 8px;
    border-top: 1px solid #006ab3;
}}
QStatusBar::item {{
    border: none;
}}

/* ── Dock widgets ── */
QDockWidget {{
    color: {FG_TEXT};
    font-size: 12px;
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}}
QDockWidget::title {{
    background: {BG_PANEL};
    padding: 4px 8px;
    border-bottom: 1px solid {BORDER};
    text-align: left;
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: {FG_MUTED};
}}

/* ── Output / terminal text area ── */
QPlainTextEdit#terminal_output {{
    background-color: #0c0c0c;
    color: #cccccc;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 13px;
    border: none;
    selection-background-color: {SELECTION};
    padding: 4px;
}}

/* ── Terminal stdin input field ── */
QLineEdit#terminal_input {{
    background-color: #1a1a1a;
    color: #d4d4d4;
    border: 1px solid {BORDER};
    border-radius: 3px;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
    padding: 3px 8px;
    selection-background-color: {SELECTION};
}}
QLineEdit#terminal_input:focus {{
    border-color: #00b4d8;
}}

/* ── Send button ── */
QPushButton#send_btn {{
    background-color: #007acc;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 12px;
    padding: 3px 10px;
    font-weight: bold;
}}
QPushButton#send_btn:hover {{
    background-color: #0095ee;
}}
QPushButton#send_btn:pressed {{
    background-color: #005a9e;
}}

/* ── Push buttons ── */
QPushButton {{
    background-color: {BG_TOOLBAR};
    color: {FG_TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 5px 14px;
    font-size: 12px;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    color: {FG_WHITE};
    border-color: #007acc;
}}
QPushButton:pressed {{
    background-color: #0e6191;
}}
QPushButton:disabled {{
    color: {FG_MUTED};
    border-color: {BORDER};
}}
QPushButton#run_btn {{
    background-color: #388a34;
    color: white;
    border: none;
    border-radius: 5px;
    font-weight: bold;
    padding: 5px 18px;
}}
QPushButton#run_btn:hover {{
    background-color: #4aad46;
}}
QPushButton#stop_btn {{
    background-color: #c72e2e;
    color: white;
    border: none;
    border-radius: 5px;
    font-weight: bold;
    padding: 5px 18px;
}}
QPushButton#stop_btn:hover {{
    background-color: #e03535;
}}

/* ── Input fields ── */
QLineEdit {{
    background-color: {BG_INPUT};
    color: {FG_TEXT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: {SELECTION};
}}
QLineEdit:focus {{
    border-color: {FG_ACCENT};
}}

/* ── Label ── */
QLabel {{
    color: {FG_TEXT};
    background: transparent;
}}

/* ── Autocomplete popup ── */
QAbstractItemView {{
    background-color: {BG_PANEL};
    color: {FG_TEXT};
    border: 1px solid {BORDER};
    selection-background-color: {BG_HOVER};
    selection-color: {FG_WHITE};
    outline: none;
    padding: 2px;
}}

/* ── Dialogs ── */
QDialog {{
    background-color: {BG_DARK};
    color: {FG_TEXT};
}}
QDialog QLabel {{
    color: {FG_TEXT};
}}

/* ── Tab widget (used in Preferences dialog) ── */
QTabWidget::tab-bar {{
    alignment: left;
}}
QTabWidget > QWidget {{
    background-color: {BG_DARK};
}}

/* ── Spin boxes ── */
QSpinBox {{
    background-color: {BG_INPUT};
    color: {FG_TEXT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 3px 6px;
    selection-background-color: {SELECTION};
}}
QSpinBox:focus {{
    border-color: {FG_ACCENT};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: {BG_TOOLBAR};
    border: none;
    width: 16px;
}}
QSpinBox::up-arrow {{
    width: 8px;
    height: 8px;
}}
QSpinBox::down-arrow {{
    width: 8px;
    height: 8px;
}}

/* ── Combo boxes ── */
QComboBox {{
    background-color: {BG_INPUT};
    color: {FG_TEXT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: {SELECTION};
}}
QComboBox:focus {{
    border-color: {FG_ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 4px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_PANEL};
    color: {FG_TEXT};
    border: 1px solid {BORDER};
    selection-background-color: {BG_HOVER};
}}

/* ── Check boxes ── */
QCheckBox {{
    color: {FG_TEXT};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {BORDER};
    border-radius: 3px;
    background: {BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background: {FG_ACCENT};
    border-color: {FG_ACCENT};
}}
QCheckBox::indicator:hover {{
    border-color: {FG_ACCENT};
}}

/* ── Progress bar (download progress in UpdateDialog) ── */
QProgressBar {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    text-align: center;
    color: {FG_TEXT};
    font-size: 11px;
    height: 18px;
}}
QProgressBar::chunk {{
    background-color: {FG_ACCENT};
    border-radius: 3px;
}}

/* ── Text edit (changelog in UpdateDialog) ── */
QTextEdit {{
    background-color: #0c0c0c;
    color: {FG_TEXT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    font-size: 12px;
    padding: 4px;
    selection-background-color: {SELECTION};
}}

/* ── List widget (interpreter list) ── */
QListWidget {{
    background-color: {BG_PANEL};
    color: {FG_TEXT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid #1e1e1e;
}}
QListWidget::item:selected {{
    background-color: {BG_HOVER};
    color: #ffffff;
}}
QListWidget::item:hover:!selected {{
    background-color: #2a2d2e;
}}
"""

# ─── Splash stylesheet ────────────────────────────────────────────────────────
SPLASH_STYLE = f"""
QSplashScreen {{
    border: 2px solid {BORDER};
    border-radius: 12px;
}}
"""
