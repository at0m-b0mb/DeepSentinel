"""DeepSentinel visual theme — dark cyberpunk palette."""

# ── Palette ───────────────────────────────────────────────────────────────────
BG_VOID    = "#03030a"     # absolute black
BG_DEEP    = "#06060f"
BG_SURFACE = "#0a0a15"
BG_CARD    = "#0d0d1b"
BG_CARD2   = "#101022"
BG_HOVER   = "#14142a"
BG_ACTIVE  = "#181830"

BORDER     = "#18182c"
BORDER_LO  = "#12122010"
BORDER_MID = "#20203a"
BORDER_HI  = "#2a2a50"
BORDER_CYAN= "#00d4ff28"

CYAN       = "#00d4ff"
CYAN_MID   = "#0099cc"
CYAN_DIM   = "#006688"
CYAN_GLOW  = "#00d4ff22"

PURPLE     = "#a855f7"
PURPLE_DIM = "#7c3aed"
PURPLE_GLOW= "#a855f722"

GREEN      = "#10b981"
GREEN_LO   = "#059669"
GREEN_GLOW = "#10b98122"

RED        = "#f43f5e"
RED_DIM    = "#be123c"
RED_GLOW   = "#f43f5e22"

AMBER      = "#f59e0b"
AMBER_DIM  = "#b45309"

TEXT_HI    = "#f0f0ff"
TEXT_MID   = "#9090b8"
TEXT_LO    = "#505070"
TEXT_DIM   = "#2a2a45"

FONT_UI    = "'SF Pro Display', 'Segoe UI', Helvetica, sans-serif"
FONT_MONO  = "'JetBrains Mono', 'Fira Code', Menlo, Consolas, monospace"

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

/* ─── Tab bar ─── */
QTabWidget {{
    background: {BG_VOID};
    border: none;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER_MID};
    border-top: none;
    background: {BG_SURFACE};
    border-radius: 0 10px 10px 10px;
}}
QTabBar {{
    background: {BG_VOID};
}}
QTabBar::tab {{
    background: {BG_CARD};
    color: {TEXT_LO};
    border: 1px solid {BORDER};
    border-bottom: none;
    padding: 10px 22px;
    margin-right: 3px;
    border-radius: 10px 10px 0 0;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.3px;
    min-width: 130px;
}}
QTabBar::tab:selected {{
    background: {BG_SURFACE};
    color: {CYAN};
    border-color: {BORDER_HI};
    border-bottom: none;
    border-top: 2px solid {CYAN};
}}
QTabBar::tab:hover:!selected {{
    background: {BG_HOVER};
    color: {TEXT_MID};
    border-color: {BORDER_MID};
}}

/* ─── Buttons ─── */
QPushButton {{
    background: {BG_CARD2};
    color: {TEXT_MID};
    border: 1px solid {BORDER_MID};
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}
QPushButton:hover {{
    background: {BG_HOVER};
    border-color: {CYAN_DIM};
    color: {TEXT_HI};
}}
QPushButton:pressed {{
    background: {BG_DEEP};
    border-color: {CYAN};
}}
QPushButton:disabled {{
    color: {TEXT_DIM};
    border-color: {BORDER};
    background: {BG_CARD};
}}

QPushButton#primaryBtn {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {CYAN_MID}, stop:1 {CYAN});
    color: {BG_VOID};
    border: none;
    font-weight: 800;
    font-size: 13px;
    letter-spacing: 0.5px;
    border-radius: 10px;
}}
QPushButton#primaryBtn:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {CYAN}, stop:1 #40e8ff);
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
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {RED_DIM}, stop:1 {RED});
    color: white;
    border: none;
    font-weight: 800;
    border-radius: 10px;
}}
QPushButton#dangerBtn:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {RED}, stop:1 #ff6680);
}}

QPushButton#ghostBtn {{
    background: transparent;
    color: {CYAN};
    border: 1px solid {CYAN_DIM};
    border-radius: 8px;
    font-weight: 600;
}}
QPushButton#ghostBtn:hover {{
    background: {CYAN_GLOW};
    border-color: {CYAN};
}}

QPushButton#iconBtn {{
    background: {BG_CARD2};
    color: {TEXT_MID};
    border: 1px solid {BORDER_MID};
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
}}
QPushButton#iconBtn:hover {{
    background: {BG_HOVER};
    color: {CYAN};
    border-color: {CYAN_DIM};
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
    letter-spacing: 3px;
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
    background: {BG_CARD};
    border: 1px solid {BORDER_MID};
    border-radius: 8px;
    color: {TEXT_HI};
    padding: 7px 11px;
    selection-background-color: {CYAN_DIM};
    font-size: 13px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {CYAN_DIM};
    background: {BG_CARD2};
}}

/* ─── Progress bars ─── */
QProgressBar {{
    background: {BG_CARD};
    border: none;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    font-size: 10px;
    color: {TEXT_MID};
}}
QProgressBar::chunk {{
    border-radius: 6px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {CYAN_MID}, stop:1 {CYAN});
}}

/* ─── Scroll bars ─── */
QScrollBar:vertical {{
    background: {BG_DEEP};
    width: 6px;
    border: none;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_HI};
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {CYAN_DIM};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {BG_DEEP};
    height: 6px;
    border: none;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_HI};
    border-radius: 3px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {CYAN_DIM};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ─── CheckBox ─── */
QCheckBox {{
    color: {TEXT_MID};
    spacing: 9px;
    font-size: 12px;
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {BORDER_MID};
    border-radius: 4px;
    background: {BG_CARD};
}}
QCheckBox::indicator:checked {{
    background: {CYAN};
    border-color: {CYAN};
}}
QCheckBox:hover {{ color: {TEXT_HI}; }}

/* ─── Slider ─── */
QSlider::groove:horizontal {{
    background: {BORDER_MID};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {CYAN};
    width: 14px; height: 14px;
    border-radius: 7px;
    margin: -5px 0;
    border: 2px solid {BG_CARD};
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {CYAN_DIM}, stop:1 {CYAN});
    height: 4px;
    border-radius: 2px;
}}

/* ─── ComboBox ─── */
QComboBox {{
    background: {BG_CARD};
    border: 1px solid {BORDER_MID};
    border-radius: 8px;
    padding: 6px 12px;
    color: {TEXT_HI};
    min-width: 150px;
    font-size: 12px;
}}
QComboBox:hover {{ border-color: {CYAN_DIM}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: {BG_CARD2};
    border: 1px solid {BORDER_HI};
    color: {TEXT_HI};
    selection-background-color: {BG_HOVER};
    outline: none;
}}

/* ─── Group box ─── */
QGroupBox {{
    border: 1px solid {BORDER_MID};
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 10px;
    color: {TEXT_LO};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {CYAN_DIM};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
}}

/* ─── Text browser (education) ─── */
QTextBrowser {{
    background: {BG_SURFACE};
    border: 1px solid {BORDER_MID};
    border-radius: 10px;
    color: {TEXT_HI};
    padding: 12px;
    selection-background-color: {CYAN_DIM};
    font-size: 13px;
    line-height: 1.6;
}}

/* ─── Cards ─── */
QFrame#card {{
    background: {BG_CARD};
    border: 1px solid {BORDER_MID};
    border-radius: 14px;
}}
QFrame#card2 {{
    background: {BG_CARD2};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QFrame#glowCard {{
    background: {BG_CARD};
    border: 1px solid {BORDER_CYAN};
    border-radius: 14px;
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
    padding: 2px 10px;
}}

/* ─── Menu ─── */
QMenuBar {{
    background: {BG_VOID};
    color: {TEXT_MID};
    border-bottom: 1px solid {BORDER};
    font-size: 13px;
}}
QMenuBar::item:selected {{
    background: {BG_HOVER};
    color: {TEXT_HI};
    border-radius: 4px;
}}
QMenu {{
    background: {BG_CARD2};
    border: 1px solid {BORDER_HI};
    color: {TEXT_HI};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{ padding: 6px 20px; border-radius: 4px; }}
QMenu::item:selected {{ background: {BG_HOVER}; color: {CYAN}; }}
QMenu::separator {{ background: {BORDER_MID}; height: 1px; margin: 4px 8px; }}

/* ─── Splitter ─── */
QSplitter::handle {{ background: {BORDER}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}

/* ─── Tooltip ─── */
QToolTip {{
    background: {BG_CARD2};
    color: {TEXT_HI};
    border: 1px solid {BORDER_HI};
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
}}

/* ─── List widget ─── */
QListWidget {{
    background: {BG_CARD};
    border: 1px solid {BORDER_MID};
    border-radius: 10px;
    color: {TEXT_HI};
    outline: none;
    padding: 4px;
}}
QListWidget::item {{
    border-radius: 6px;
    padding: 6px 10px;
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
