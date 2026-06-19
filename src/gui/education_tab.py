"""Educational deepfake pipeline tab — How deepfakes work & how to detect them."""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QFrame, QTextBrowser, QScrollArea, QSplitter, QSizePolicy,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont

from .theme import (
    CYAN, CYAN_DIM, GREEN, RED, AMBER, TEXT_MID as TEXT_SECONDARY,
    TEXT_HI as TEXT_PRIMARY, BG_CARD, BG_DEEP, BG_SURFACE,
    BORDER_HI as BORDER_ACCENT, BORDER_MID as BORDER, FONT_MONO,
)
ORANGE = AMBER
YELLOW = AMBER
from ..education.pipeline import SECTIONS


_CODE_STYLE = f"""
    background-color: #0d0d1a;
    color: #c9d1d9;
    border: 1px solid {BORDER_ACCENT};
    border-radius: 8px;
    padding: 12px;
    font-family: {FONT_MONO};
    font-size: 12px;
    line-height: 1.5;
"""

_SECTION_BTN_ACTIVE = f"""
    QPushButton {{
        background: {CYAN};
        color: #050510;
        border: none;
        border-radius: 8px;
        padding: 10px 14px;
        text-align: left;
        font-weight: 700;
        font-size: 13px;
    }}
"""

_SECTION_BTN_IDLE = f"""
    QPushButton {{
        background: {BG_CARD};
        color: {TEXT_SECONDARY};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 10px 14px;
        text-align: left;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background: #1a1a2e;
        color: {TEXT_PRIMARY};
        border-color: {CYAN_DIM};
    }}
"""

SECTION_ORDER = ["intro", "algorithm", "modern", "detection", "legal"]

SECTION_ICONS = {
    "intro":     "📖",
    "algorithm": "⚙",
    "modern":    "🧠",
    "detection": "🛡",
    "legal":     "⚖",
}


class EducationTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_section = "intro"
        self._section_btns: dict[str, QPushButton] = {}
        self._build_ui()
        self._switch_section("intro")

    def _build_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setHandleWidth(6)
        splitter.setChildrenCollapsible(False)

        root_l = QVBoxLayout(self)
        root_l.setContentsMargins(16, 16, 16, 16)
        root_l.addWidget(splitter)

        # Left sidebar — navigation
        sidebar = self._build_sidebar()
        splitter.addWidget(sidebar)

        # Right — content
        content = self._build_content()
        splitter.addWidget(content)

        splitter.setSizes([220, 700])

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("card")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(6)

        logo_lbl = QLabel("LEARN")
        logo_lbl.setStyleSheet(
            f"color: {CYAN}; font-size: 11px; font-weight: 700; "
            f"letter-spacing: 3px; padding-bottom: 8px;"
        )
        layout.addWidget(logo_lbl)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFixedHeight(1)
        layout.addWidget(sep)
        layout.addSpacing(8)

        for key in SECTION_ORDER:
            sec = SECTIONS[key]
            icon = SECTION_ICONS.get(key, "•")
            btn = QPushButton(f"  {icon}  {sec['title'].replace('&', '&&')}")
            btn.setFlat(False)
            btn.setStyleSheet(_SECTION_BTN_IDLE)
            btn.clicked.connect(lambda _, k=key: self._switch_section(k))
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setFixedHeight(44)
            layout.addWidget(btn)
            self._section_btns[key] = btn

        layout.addStretch()

        # Disclaimer badge
        disc = QLabel("⚠ Educational Only\nNot for misuse")
        disc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        disc.setStyleSheet(
            f"color: {ORANGE}; background: #1a0d00; border: 1px solid {ORANGE}; "
            f"border-radius: 8px; font-size: 11px; padding: 8px 4px;"
        )
        layout.addWidget(disc)

        return sidebar

    def _build_content(self) -> QWidget:
        content = QFrame()
        content.setObjectName("card")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(True)
        self.content_browser.setStyleSheet(
            f"background: {BG_SURFACE}; border: none; color: {TEXT_PRIMARY}; "
            f"padding: 20px; font-size: 13px; line-height: 1.6;"
        )
        layout.addWidget(self.content_browser, 1)

        # Code panel (shown only for algorithm section)
        self.code_panel = QFrame()
        self.code_panel.setObjectName("card")
        self.code_panel.setVisible(False)
        cp_l = QVBoxLayout(self.code_panel)
        cp_l.setContentsMargins(12, 12, 12, 12)
        cp_l.setSpacing(8)

        code_hdr_row = QHBoxLayout()
        code_hdr = QLabel("📄  SIMPLIFIED SOURCE (Educational)")
        code_hdr.setStyleSheet(f"color: {YELLOW}; font-size: 12px; font-weight: 700;")
        code_hdr_row.addWidget(code_hdr)
        code_hdr_row.addStretch()

        warn = QLabel("⚠ FOR LEARNING ONLY — NOT FOR MISUSE")
        warn.setStyleSheet(f"color: {RED}; font-size: 11px; font-weight: 600;")
        code_hdr_row.addWidget(warn)
        cp_l.addLayout(code_hdr_row)

        code_scroll = QScrollArea()
        code_scroll.setWidgetResizable(True)
        code_scroll.setFixedHeight(340)

        self.code_browser = QTextBrowser()
        self.code_browser.setStyleSheet(_CODE_STYLE)
        self.code_browser.setFont(QFont("JetBrains Mono, Menlo, monospace", 11))
        code_scroll.setWidget(self.code_browser)
        cp_l.addWidget(code_scroll)

        layout.addWidget(self.code_panel)

        return content

    def _switch_section(self, key: str):
        self._active_section = key

        for k, btn in self._section_btns.items():
            btn.setStyleSheet(_SECTION_BTN_ACTIVE if k == key else _SECTION_BTN_IDLE)

        sec = SECTIONS.get(key, {})
        html = self._wrap_html(sec.get("content", ""))
        self.content_browser.setHtml(html)

        code = sec.get("code")
        if code:
            self.code_panel.setVisible(True)
            self.code_browser.setPlainText(code)
        else:
            self.code_panel.setVisible(False)

    def _wrap_html(self, html_body: str) -> str:
        return f"""
<html>
<head>
<style>
  body {{
    background: {BG_SURFACE};
    color: {TEXT_PRIMARY};
    font-family: 'SF Pro Display', 'Segoe UI', Helvetica, sans-serif;
    font-size: 13px;
    line-height: 1.7;
    margin: 0;
    padding: 0;
  }}
  h2 {{ color: {CYAN}; font-size: 20px; margin-top: 0; letter-spacing: 0.5px; }}
  h3 {{ color: #aaaacc; font-size: 14px; margin-top: 18px; }}
  p {{ color: {TEXT_PRIMARY}; margin: 8px 0; }}
  ul {{ color: {TEXT_SECONDARY}; padding-left: 20px; }}
  li {{ margin: 5px 0; }}
  b {{ color: {TEXT_PRIMARY}; }}
  pre {{
    background: #0d0d1a;
    color: #00ff88;
    border: 1px solid {BORDER_ACCENT};
    border-radius: 8px;
    padding: 12px;
    font-family: 'JetBrains Mono', 'Menlo', monospace;
    font-size: 12px;
    overflow: auto;
    white-space: pre;
  }}
  code {{ font-family: monospace; color: {CYAN}; }}
  i {{ color: {YELLOW}; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
