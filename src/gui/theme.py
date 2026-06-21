"""DeepSentinel visual theme — refined slate-navy palette with cyan→indigo identity."""

# ── Palette ───────────────────────────────────────────────────────────────────
# Backgrounds lift gently off a deep slate-navy base (not harsh pure black) for a
# more premium, layered feel.
BG_VOID    = "#070b14"     # app base
BG_DEEP    = "#0a0f1b"
BG_SURFACE = "#0d1320"     # tab pane
BG_CARD    = "#111827"     # cards
BG_CARD2   = "#161f30"     # raised cards
BG_HOVER   = "#1c2740"
BG_ACTIVE  = "#222e4a"

BORDER     = "#1b2435"
BORDER_LO  = "#141c2a"
BORDER_MID = "#253049"
BORDER_HI  = "#34415e"


def rgba(hex6: str, alpha: float) -> str:
    """Return an 'rgba(r,g,b,a)' string Qt parses correctly.

    Qt reads 8-digit '#RRGGBBAA'-looking hex as '#AARRGGBB' (alpha first),
    which silently shifts colours — so always build tints via rgba() instead.
    """
    h = hex6.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"


# Primary identity: cyan, paired with indigo for gradients.
CYAN       = "#22d3ee"
CYAN_MID   = "#0ea5e9"
CYAN_DIM   = "#0c7da3"

PURPLE     = "#818cf8"     # indigo companion
PURPLE_DIM = "#6366f1"

GREEN      = "#34d399"
GREEN_LO   = "#10b981"

RED        = "#fb7185"
RED_DIM    = "#e11d48"

AMBER      = "#fbbf24"
AMBER_DIM  = "#d97706"

# Correct tints (alpha via rgba, not broken 8-digit hex)
BORDER_CYAN= rgba(CYAN, 0.20)
CYAN_GLOW  = rgba(CYAN, 0.13)
PURPLE_GLOW= rgba(PURPLE, 0.13)
GREEN_GLOW = rgba(GREEN, 0.13)
RED_GLOW   = rgba(RED, 0.13)

TEXT_HI    = "#f1f5f9"     # slate-50
TEXT_MID   = "#94a3b8"     # slate-400
TEXT_LO    = "#64748b"     # slate-500
TEXT_DIM   = "#3f4c63"     # muted slate (still legible)

FONT_UI    = "'SF Pro Display', 'Inter', 'Segoe UI', Helvetica, sans-serif"
FONT_MONO  = "'JetBrains Mono', 'SF Mono', 'Fira Code', Menlo, Consolas, monospace"

# Signature gradients (stylesheet-only helpers)
GRAD_PRIMARY = f"qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {CYAN}, stop:1 {PURPLE_DIM})"
GRAD_PRIMARY_HI = f"qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #4fe3f5, stop:1 {PURPLE})"
GRAD_DANGER  = f"qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {RED_DIM}, stop:1 {RED})"

# ── Stylesheet ────────────────────────────────────────────────────────────────
STYLESHEET = f"""
/* ─── Base ─── */
QMainWindow, QDialog {{
    background: {BG_VOID};
    color: {TEXT_HI};
}}
QWidget {{
    background: transparent;
    color: {TEXT_HI};
    font-family: {FONT_UI};
    font-size: 13px;
}}

/* ─── Tabs ─── */
QTabWidget {{
    background: {BG_VOID};
    border: none;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER_MID};
    border-top: none;
    background: {BG_SURFACE};
    border-radius: 0 14px 14px 14px;
    top: -1px;
}}
QTabBar {{
    background: {BG_VOID};
    qproperty-drawBase: 0;
}}
QTabBar::tab {{
    background: {BG_DEEP};
    color: {TEXT_LO};
    border: 1px solid transparent;
    border-bottom: none;
    padding: 11px 24px;
    margin-right: 4px;
    border-radius: 12px 12px 0 0;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.4px;
    min-width: 120px;
}}
QTabBar::tab:selected {{
    background: {BG_SURFACE};
    color: {CYAN};
    border: 1px solid {BORDER_MID};
    border-bottom: none;
}}
QTabBar::tab:hover:!selected {{
    background: {BG_CARD};
    color: {TEXT_MID};
}}

/* ─── Buttons ─── */
QPushButton {{
    background: {BG_CARD2};
    color: {TEXT_MID};
    border: 1px solid {BORDER_MID};
    border-radius: 10px;
    padding: 9px 18px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}
QPushButton:hover {{
    background: {BG_HOVER};
    border-color: {BORDER_HI};
    color: {TEXT_HI};
}}
QPushButton:pressed {{
    background: {BG_DEEP};
}}
QPushButton:disabled {{
    color: {TEXT_DIM};
    border-color: {BORDER};
    background: {BG_CARD};
}}

QPushButton#primaryBtn {{
    background: {GRAD_PRIMARY};
    color: #04121a;
    border: none;
    font-weight: 800;
    font-size: 13px;
    letter-spacing: 0.5px;
    border-radius: 11px;
    padding: 10px 20px;
}}
QPushButton#primaryBtn:hover {{
    background: {GRAD_PRIMARY_HI};
}}
QPushButton#primaryBtn:pressed {{
    background: {CYAN_DIM};
}}
QPushButton#primaryBtn:disabled {{
    background: {BORDER_MID};
    color: {TEXT_LO};
    border: none;
}}

QPushButton#dangerBtn {{
    background: {GRAD_DANGER};
    color: #fff5f7;
    border: none;
    font-weight: 800;
    border-radius: 11px;
    padding: 10px 20px;
}}
QPushButton#dangerBtn:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {RED}, stop:1 #ff94a6);
}}

QPushButton#ghostBtn {{
    background: {rgba(CYAN, 0.05)};
    color: {CYAN};
    border: 1px solid {rgba(CYAN, 0.23)};
    border-radius: 10px;
    font-weight: 600;
}}
QPushButton#ghostBtn:hover {{
    background: {rgba(CYAN, 0.11)};
    border-color: {rgba(CYAN, 0.40)};
    color: #6fe6f7;
}}

QPushButton#iconBtn {{
    background: {BG_CARD2};
    color: {TEXT_MID};
    border: 1px solid {BORDER_MID};
    border-radius: 10px;
    padding: 7px 12px;
    font-size: 14px;
}}
QPushButton#iconBtn:hover {{
    background: {BG_HOVER};
    color: {CYAN};
    border-color: {rgba(CYAN, 0.33)};
}}

/* ─── Labels ─── */
QLabel {{
    color: {TEXT_HI};
    background: transparent;
}}
QLabel#sectionHeader {{
    color: {CYAN};
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 2.5px;
    padding: 2px 0 6px 0;
}}
QLabel#tagline {{
    color: {TEXT_LO};
    font-size: 12px;
}}
QLabel#metricVal {{
    color: {GREEN};
    font-size: 36px;
    font-weight: 900;
    font-family: {FONT_MONO};
    letter-spacing: -1px;
}}
QLabel#metricLbl {{
    color: {TEXT_LO};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
}}
QLabel#verdictLabel {{
    letter-spacing: 5px;
    font-size: 16px;
    font-weight: 900;
}}
QLabel#pctLabel {{
    font-family: {FONT_MONO};
    font-size: 38px;
    font-weight: 900;
}}
QLabel#capsLabel {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    color: {TEXT_LO};
}}

/* ─── Inputs ─── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background: {BG_DEEP};
    border: 1px solid {BORDER_MID};
    border-radius: 10px;
    color: {TEXT_HI};
    padding: 8px 12px;
    selection-background-color: {CYAN_DIM};
    font-size: 13px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {rgba(CYAN, 0.47)};
    background: {BG_CARD};
}}

/* ─── Progress bars ─── */
QProgressBar {{
    background: {BG_DEEP};
    border: none;
    border-radius: 6px;
    height: 8px;
    text-align: center;
    font-size: 10px;
    color: {TEXT_MID};
}}
QProgressBar::chunk {{
    border-radius: 6px;
    background: {GRAD_PRIMARY};
}}

/* ─── Scroll bars ─── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    border: none;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_HI};
    border-radius: 4px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background: {CYAN_DIM};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    border: none;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_HI};
    border-radius: 4px;
    min-width: 28px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {CYAN_DIM};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

/* ─── CheckBox ─── */
QCheckBox {{
    color: {TEXT_MID};
    spacing: 10px;
    font-size: 12px;
}}
QCheckBox::indicator {{
    width: 17px; height: 17px;
    border: 1px solid {BORDER_HI};
    border-radius: 5px;
    background: {BG_DEEP};
}}
QCheckBox::indicator:checked {{
    background: {GRAD_PRIMARY};
    border-color: {CYAN};
}}
QCheckBox::indicator:hover {{
    border-color: {rgba(CYAN, 0.53)};
}}
QCheckBox:hover {{ color: {TEXT_HI}; }}

/* ─── Slider ─── */
QSlider::groove:horizontal {{
    background: {BORDER_MID};
    height: 5px;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {CYAN};
    width: 16px; height: 16px;
    border-radius: 8px;
    margin: -6px 0;
    border: 3px solid {BG_CARD};
}}
QSlider::handle:horizontal:hover {{
    background: #5fe1f3;
}}
QSlider::sub-page:horizontal {{
    background: {GRAD_PRIMARY};
    height: 5px;
    border-radius: 3px;
}}

/* ─── ComboBox ─── */
QComboBox {{
    background: {BG_DEEP};
    border: 1px solid {BORDER_MID};
    border-radius: 10px;
    padding: 7px 13px;
    color: {TEXT_HI};
    min-width: 150px;
    font-size: 12px;
}}
QComboBox:hover {{ border-color: {rgba(CYAN, 0.40)}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox QAbstractItemView {{
    background: {BG_CARD2};
    border: 1px solid {BORDER_HI};
    color: {TEXT_HI};
    selection-background-color: {BG_HOVER};
    border-radius: 10px;
    padding: 4px;
    outline: none;
}}

/* ─── Group box ─── */
QGroupBox {{
    border: 1px solid {BORDER_MID};
    border-radius: 14px;
    margin-top: 16px;
    padding-top: 12px;
    background: {rgba(BG_CARD, 0.33)};
    color: {TEXT_LO};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 8px;
    color: {CYAN};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
}}

/* ─── Text browser (education) ─── */
QTextBrowser {{
    background: {BG_SURFACE};
    border: 1px solid {BORDER_MID};
    border-radius: 14px;
    color: {TEXT_HI};
    padding: 14px;
    selection-background-color: {CYAN_DIM};
    font-size: 13px;
    line-height: 1.7;
}}

/* ─── Cards ─── */
QFrame#card {{
    background: {BG_CARD};
    border: 1px solid {BORDER_MID};
    border-radius: 16px;
}}
QFrame#card2 {{
    background: {BG_CARD2};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#glowCard {{
    background: {BG_CARD};
    border: 1px solid {BORDER_CYAN};
    border-radius: 16px;
}}
QFrame#panel {{
    background: {BG_SURFACE};
    border: none;
    border-radius: 0;
}}
QFrame#divider {{
    background: {BORDER_MID};
    max-height: 1px;
    border: none;
}}

/* ─── Status bar ─── */
QStatusBar {{
    background: {BG_VOID};
    color: {TEXT_LO};
    border-top: 1px solid {BORDER};
    font-size: 11px;
    padding: 3px 12px;
}}
QStatusBar::item {{ border: none; }}

/* ─── Menu ─── */
QMenuBar {{
    background: {BG_VOID};
    color: {TEXT_MID};
    border-bottom: 1px solid {BORDER};
    font-size: 13px;
    padding: 2px;
}}
QMenuBar::item {{ padding: 5px 12px; border-radius: 6px; }}
QMenuBar::item:selected {{
    background: {BG_HOVER};
    color: {TEXT_HI};
}}
QMenu {{
    background: {BG_CARD2};
    border: 1px solid {BORDER_HI};
    color: {TEXT_HI};
    border-radius: 10px;
    padding: 5px;
}}
QMenu::item {{ padding: 7px 22px; border-radius: 7px; }}
QMenu::item:selected {{ background: {BG_HOVER}; color: {CYAN}; }}
QMenu::separator {{ background: {BORDER_MID}; height: 1px; margin: 5px 10px; }}

/* ─── Splitter ─── */
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 6px; }}
QSplitter::handle:vertical {{ height: 6px; }}

/* ─── Tooltip ─── */
QToolTip {{
    background: {BG_CARD2};
    color: {TEXT_HI};
    border: 1px solid {BORDER_HI};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ─── List widget ─── */
QListWidget {{
    background: {BG_CARD};
    border: 1px solid {BORDER_MID};
    border-radius: 14px;
    color: {TEXT_HI};
    outline: none;
    padding: 6px;
}}
QListWidget::item {{
    border-radius: 9px;
    padding: 8px 12px;
    color: {TEXT_MID};
    font-size: 12px;
}}
QListWidget::item:selected {{
    background: {BG_HOVER};
    color: {TEXT_HI};
    border: 1px solid {BORDER_MID};
}}
QListWidget::item:hover {{
    background: {BG_ACTIVE};
    color: {TEXT_HI};
}}
"""
