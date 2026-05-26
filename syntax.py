# syntax.py — Python syntax highlighter (QSyntaxHighlighter)
# Covers: keywords, builtins, strings (incl. multi-line triple-quoted),
#         comments, numbers, class/function names, decorators, self/cls.

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor

from theme import (
    SYN_KEYWORD, SYN_BUILTIN, SYN_STRING, SYN_COMMENT,
    SYN_NUMBER, SYN_CLASS, SYN_FUNC, SYN_DECORATOR,
    SYN_IMPORT, SYN_SELF,
)


def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    if bold:
        fmt.setFontWeight(QFont.Weight.Bold)
    if italic:
        fmt.setFontItalic(True)
    return fmt


# ── Word lists (also imported by editor.py for autocomplete) ──────────────────
KEYWORDS = [
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
    "try", "while", "with", "yield",
]

BUILTINS = [
    "abs", "all", "any", "bin", "bool", "bytearray", "bytes", "callable",
    "chr", "compile", "complex", "delattr", "dict", "dir", "divmod",
    "enumerate", "eval", "exec", "filter", "float", "format", "frozenset",
    "getattr", "globals", "hasattr", "hash", "help", "hex", "id", "input",
    "int", "isinstance", "issubclass", "iter", "len", "list", "locals",
    "map", "max", "memoryview", "min", "next", "object", "oct", "open",
    "ord", "pow", "print", "property", "range", "repr", "reversed",
    "round", "set", "setattr", "slice", "sorted", "staticmethod", "str",
    "sum", "super", "tuple", "type", "vars", "zip", "__import__",
    "NotImplemented", "Ellipsis", "__debug__",
    # common exception types
    "Exception", "BaseException", "ValueError", "TypeError", "KeyError",
    "IndexError", "AttributeError", "NameError", "OSError", "IOError",
    "FileNotFoundError", "FileExistsError", "RuntimeError", "StopIteration",
    "GeneratorExit", "SystemExit", "KeyboardInterrupt", "AssertionError",
    "ImportError", "ModuleNotFoundError", "OverflowError", "ZeroDivisionError",
    "MemoryError", "RecursionError", "PermissionError", "TimeoutError",
    "NotImplementedError", "UnicodeError", "UnicodeDecodeError",
    "UnicodeEncodeError", "ConnectionError", "LookupError",
]


# ── Rule record ──────────────────────────────────────────────────────────────
# (compiled_pattern, format, use_capture_group_1)
# use_capture_group_1=True  → only colour the first capture group
# use_capture_group_1=False → colour the whole match
_Rule = tuple[QRegularExpression, QTextCharFormat, bool]


class PythonHighlighter(QSyntaxHighlighter):
    """Full Python syntax highlighter with multi-line string support."""

    # Block states for multi-line strings
    _STATE_NONE       = 0
    _STATE_TRIPLE_DQ  = 1   # inside """..."""
    _STATE_TRIPLE_SQ  = 2   # inside '''...'''

    def __init__(self, document):
        super().__init__(document)
        self._rules: list[_Rule] = []
        self._build_rules()
        self._re_triple_dq  = QRegularExpression('"""')
        self._re_triple_sq  = QRegularExpression("'''")
        self._fmt_string    = _fmt(SYN_STRING)

    # ── Rule construction ─────────────────────────────────────────────────────
    def _build_rules(self):
        add = self._rules.append

        # Decorators: @name
        add((QRegularExpression(r"@[A-Za-z_]\w*"),
             _fmt(SYN_DECORATOR), False))

        # import / from (different colour from other keywords)
        add((QRegularExpression(r"\b(import|from)\b"),
             _fmt(SYN_IMPORT, bold=True), True))

        # Function name (the identifier after 'def')
        add((QRegularExpression(r"\bdef\s+([A-Za-z_]\w*)"),
             _fmt(SYN_FUNC, bold=True), True))

        # Class name (the identifier after 'class')
        add((QRegularExpression(r"\bclass\s+([A-Za-z_]\w*)"),
             _fmt(SYN_CLASS, bold=True), True))

        # All keywords (including def/class to colour the keyword word itself)
        kw_pat = r"\b(" + "|".join(KEYWORDS) + r")\b"
        add((QRegularExpression(kw_pat), _fmt(SYN_KEYWORD, bold=True), True))

        # Built-ins
        bi_pat = r"\b(" + "|".join(BUILTINS) + r")\b"
        add((QRegularExpression(bi_pat), _fmt(SYN_BUILTIN), True))

        # self / cls
        add((QRegularExpression(r"\b(self|cls)\b"),
             _fmt(SYN_SELF, italic=True), True))

        # Numbers: int, float, hex, oct, bin, complex
        add((QRegularExpression(
            r"\b(0[xX][0-9A-Fa-f]+"
            r"|0[oO][0-7]+"
            r"|0[bB][01]+"
            r"|\d+\.?\d*([eE][+-]?\d+)?[jJ]?"
            r"|\.\d+([eE][+-]?\d+)?[jJ]?)\b"),
            _fmt(SYN_NUMBER), False))

        # Single-line strings (before comment so # inside a string is ignored)
        add((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'),
             _fmt(SYN_STRING), False))
        add((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"),
             _fmt(SYN_STRING), False))

        # Single-line comment
        add((QRegularExpression(r"#[^\n]*"),
             _fmt(SYN_COMMENT, italic=True), False))

    # ── highlightBlock ────────────────────────────────────────────────────────
    def highlightBlock(self, text: str):           # noqa: N802
        # 1. Apply all single-line rules
        for pattern, fmt, use_group in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                if use_group and m.lastCapturedIndex() >= 1:
                    s = m.capturedStart(1)
                    n = m.capturedLength(1)
                    if s >= 0 and n > 0:
                        self.setFormat(s, n, fmt)
                else:
                    self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

        # 2. Multi-line triple-quoted strings (overwrite single-line formats)
        self._apply_multiline(text, self._re_triple_dq, self._STATE_TRIPLE_DQ)
        self._apply_multiline(text, self._re_triple_sq, self._STATE_TRIPLE_SQ)

    def _apply_multiline(
        self, text: str, delim: QRegularExpression, state: int
    ):
        if self.previousBlockState() == state:
            start, offset = 0, 0
        else:
            m = delim.match(text)
            if not m.hasMatch():
                return
            start, offset = m.capturedStart(), m.capturedLength()

        while start >= 0:
            end_m = delim.match(text, start + offset)
            if end_m.hasMatch():
                length = end_m.capturedStart() - start + end_m.capturedLength()
                self.setCurrentBlockState(self._STATE_NONE)
            else:
                self.setCurrentBlockState(state)
                length = len(text) - start

            self.setFormat(start, length, self._fmt_string)

            next_m = delim.match(text, start + length)
            if next_m.hasMatch():
                start, offset = next_m.capturedStart(), next_m.capturedLength()
            else:
                break
