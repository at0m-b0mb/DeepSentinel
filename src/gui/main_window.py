"""DeepSentinel main application window — redesigned with logo header + dashboard."""

import math
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget, QButtonGroup, QStatusBar, QLabel,
    QVBoxLayout, QHBoxLayout, QDialog, QPushButton, QTextEdit,
    QMessageBox, QFrame, QSizePolicy,
)
from PyQt6.QtCore import (
    Qt, QTimer, QRectF, QPointF, pyqtSignal,
    QPropertyAnimation, QEasingCurve,
)
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from PyQt6.QtGui import (
    QFont, QAction, QPainter, QPen, QColor, QLinearGradient,
    QBrush, QConicalGradient, QRadialGradient, QPainterPath, QPolygonF,
)

from .theme import (
    CYAN, CYAN_MID, CYAN_DIM, RED, RED_DIM, GREEN, AMBER, PURPLE,
    TEXT_HI, TEXT_MID, TEXT_LO, TEXT_DIM,
    BG_VOID, BG_DEEP, BG_CARD, BG_CARD2, BG_HOVER, BORDER_MID, BORDER_HI, BORDER_CYAN,
    FONT_MONO, FONT_UI, rgba,
)
from .widgets import PulsingDot, Toast, glow_effect
from ..detection.detector import DeepfakeDetector
from .live_tab import LiveTab
from .analyze_tab import AnalyzeTab
from .create_tab import CreateTab
from .batch_tab import BatchTab
from .education_tab import EducationTab
from .settings_tab import SettingsTab
from .dashboard_tab import DashboardTab


# ── Hex logo widget ───────────────────────────────────────────────────────────

class HexLogo(QWidget):
    """Painted hexagonal eye logo — brand cyan→indigo gradient with a soft shimmer."""

    def __init__(self, size: int = 40, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._angle = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def _tick(self):
        self._angle = (self._angle + 1.4) % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        s = self._size
        cx, cy = s / 2, s / 2
        r = s / 2 - 3

        hex_pts = [QPointF(cx + r * math.cos(math.radians(60 * i - 30)),
                           cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]
        polygon = QPolygonF(hex_pts)

        # Soft radial glow behind the hex
        glow = QRadialGradient(cx, cy, r * 1.5)
        gc = QColor(CYAN); gc.setAlpha(60); glow.setColorAt(0.0, gc)
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(glow)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), r * 1.4, r * 1.4)

        # Gentle gradient fill inside the hex
        fill = QLinearGradient(0, 0, s, s)
        f0 = QColor(CYAN); f0.setAlpha(28)
        f1 = QColor(PURPLE); f1.setAlpha(20)
        fill.setColorAt(0.0, f0); fill.setColorAt(1.0, f1)
        p.setBrush(QBrush(fill)); p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(polygon)

        # Hex outline — rotating cyan→indigo conical shimmer
        grad = QConicalGradient(cx, cy, self._angle)
        grad.setColorAt(0.0, QColor(CYAN))
        grad.setColorAt(0.5, QColor(PURPLE))
        grad.setColorAt(1.0, QColor(CYAN))
        p.setPen(QPen(QBrush(grad), 2.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(polygon)

        # Eye almond
        ir = r * 0.52
        eye_w, eye_h = ir * 1.65, ir * 0.66
        p.setPen(QPen(QColor(CYAN), 1.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(cx - eye_w / 2, cy - eye_h / 2, eye_w, eye_h))

        # Pupil with halo
        ph = QColor(CYAN); ph.setAlpha(70)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(ph)
        p.drawEllipse(QPointF(cx, cy), eye_h * 0.55, eye_h * 0.55)
        p.setBrush(QColor(CYAN))
        p.drawEllipse(QPointF(cx, cy), eye_h * 0.4, eye_h * 0.4)
        p.setBrush(QColor(BG_VOID))
        p.drawEllipse(QPointF(cx, cy), eye_h * 0.17, eye_h * 0.17)
        # Catchlight
        hl = QColor("#d8f8ff")
        p.setBrush(hl)
        p.drawEllipse(QPointF(cx + eye_h * 0.12, cy - eye_h * 0.12), eye_h * 0.07, eye_h * 0.07)


# ── Sidebar navigation ────────────────────────────────────────────────────────

class NavButton(QPushButton):
    """Checkable sidebar nav item — painted icon + label with an active accent bar."""

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self._icon = icon
        self._label = label
        self._hover = False
        self.setObjectName("navBtn")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(46)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def enterEvent(self, e):
        self._hover = True; self.update()

    def leaveEvent(self, e):
        self._hover = False; self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        checked = self.isChecked()

        # Pill background
        if checked:
            grad = QLinearGradient(0, 0, w, 0)
            c0 = QColor(CYAN); c0.setAlpha(34); grad.setColorAt(0.0, c0)
            c1 = QColor(PURPLE); c1.setAlpha(16); grad.setColorAt(1.0, c1)
            p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(4, 3, w - 8, h - 6), 11, 11)
        elif self._hover:
            p.setBrush(QColor(BG_HOVER)); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(4, 3, w - 8, h - 6), 11, 11)

        # Active accent bar (left)
        if checked:
            p.setBrush(QColor(CYAN)); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(4, h / 2 - 11, 3.5, 22), 2, 2)

        # Icon
        icon_color = QColor(CYAN) if checked else QColor(TEXT_LO if not self._hover else TEXT_MID)
        fi = QFont(); fi.setPointSize(14)
        p.setFont(fi); p.setPen(icon_color)
        p.drawText(QRectF(16, 0, 28, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._icon)

        # Label
        fl = QFont(); fl.setFamily("SF Pro Display"); fl.setPointSize(12)
        fl.setWeight(QFont.Weight.DemiBold if checked else QFont.Weight.Medium)
        p.setFont(fl)
        p.setPen(QColor(TEXT_HI) if checked else QColor(TEXT_MID if self._hover else TEXT_LO))
        p.drawText(QRectF(50, 0, w - 56, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._label)


class NavSidebar(QFrame):
    """Left navigation rail: brand, nav items, and a status footer."""

    navigate = pyqtSignal(int)

    NAV_ITEMS = [
        ("◈", "Dashboard"),
        ("🎥", "Live Detection"),
        ("🔍", "Analyze Media"),
        ("🎭", "Face-Swap Lab"),
        ("🗂", "Batch Scan"),
        ("📚", "How It Works"),
        ("⚙", "Settings"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(232)
        self.setObjectName("navSidebar")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 22, 16, 18)
        layout.setSpacing(0)

        # Brand
        brand = QHBoxLayout()
        brand.setSpacing(11)
        self.logo = HexLogo(38)
        brand.addWidget(self.logo)
        bcol = QVBoxLayout(); bcol.setSpacing(0); bcol.setContentsMargins(0, 0, 0, 0)
        name = QLabel("DEEP<span style='color:#eef2ff; font-weight:500'>SENTINEL</span>")
        name.setTextFormat(Qt.TextFormat.RichText)
        name.setStyleSheet(f"color: {CYAN}; font-size: 16px; font-weight: 900; letter-spacing: 2px;")
        ver = QLabel("v1.0  ·  Forensic Suite")
        ver.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; letter-spacing: 1px;")
        bcol.addWidget(name); bcol.addWidget(ver)
        brand.addLayout(bcol)
        brand.addStretch()
        layout.addLayout(brand)

        layout.addSpacing(22)
        nav_lbl = QLabel("NAVIGATION")
        nav_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; font-weight: 800; letter-spacing: 2.5px; padding-left: 8px;")
        layout.addWidget(nav_lbl)
        layout.addSpacing(8)

        # Nav buttons
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: list[NavButton] = []
        for i, (icon, label) in enumerate(self.NAV_ITEMS):
            btn = NavButton(icon, label)
            self._group.addButton(btn, i)
            btn.clicked.connect(lambda _, idx=i: self.navigate.emit(idx))
            layout.addWidget(btn)
            layout.addSpacing(3)
            self._buttons.append(btn)

        layout.addStretch()

        # Footer: live status block
        foot = QFrame(); foot.setObjectName("card2")
        fl = QVBoxLayout(foot); fl.setContentsMargins(12, 10, 12, 10); fl.setSpacing(7)
        srow = QHBoxLayout(); srow.setSpacing(8)
        self._status_dot = PulsingDot(CYAN); self._status_dot.stop()
        srow.addWidget(self._status_dot)
        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet(f"color: {TEXT_MID}; font-size: 10px; font-family: {FONT_MONO};")
        self._status_lbl.setWordWrap(True)
        srow.addWidget(self._status_lbl, 1)
        fl.addLayout(srow)
        layout.addWidget(foot)

        layout.addSpacing(8)
        badge = QLabel("⚠  EDUCATIONAL USE ONLY")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"color: {AMBER}; background: {rgba(AMBER, 0.10)}; border: 1px solid {rgba(AMBER, 0.27)}; "
            f"border-radius: 8px; font-size: 8.5px; font-weight: 800; letter-spacing: 1px; padding: 6px;"
        )
        layout.addWidget(badge)

    def select(self, index: int):
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)

    def set_status(self, msg: str, level: str = "info"):
        colors = {"info": TEXT_MID, "ok": GREEN, "warn": AMBER, "error": RED}
        dot_colors = {"info": CYAN, "ok": GREEN, "warn": AMBER, "error": RED}
        self._status_lbl.setText(msg[-48:] if len(msg) > 48 else msg)
        self._status_lbl.setStyleSheet(
            f"color: {colors.get(level, TEXT_MID)}; font-size: 10px; font-family: {FONT_MONO};"
        )
        self._status_dot._color = QColor(dot_colors.get(level, CYAN))
        if level in ("ok", "warn", "error"):
            self._status_dot.start()
            QTimer.singleShot(3000, self._status_dot.stop)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        # Vertical gradient
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor("#0b1322"))
        grad.setColorAt(1.0, QColor("#070b13"))
        p.fillRect(self.rect(), grad)
        # Top cyan glow
        glow = QRadialGradient(w / 2, 40, 200)
        gc = QColor(CYAN); gc.setAlpha(22); glow.setColorAt(0.0, gc)
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(glow)); p.setPen(Qt.PenStyle.NoPen); p.drawRect(self.rect())
        # Right border: faint cyan→indigo
        border = QLinearGradient(0, 0, 0, h)
        c1 = QColor(CYAN); c1.setAlpha(80); border.setColorAt(0.0, c1)
        c2 = QColor(PURPLE); c2.setAlpha(60); border.setColorAt(1.0, c2)
        p.setPen(QPen(QBrush(border), 1))
        p.drawLine(w - 1, 0, w - 1, h)


class TopBar(QWidget):
    """Slim content-area header: current page title + subtitle."""

    PAGES = [
        ("◈", "Dashboard", "Session overview & recent activity"),
        ("🎥", "Live Detection", "Real-time webcam deepfake analysis"),
        ("🔍", "Analyze Media", "Forensic analysis of images & videos"),
        ("🎭", "Face-Swap Lab", "Red-team: create a deepfake, then detect it"),
        ("🗂", "Batch Scan", "Analyze an entire folder at once"),
        ("📚", "How It Works", "The science behind deepfakes & detection"),
        ("⚙", "Settings", "Methods, models & configuration"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(26, 0, 24, 0)
        layout.setSpacing(12)

        self._icon = QLabel("◈")
        self._icon.setStyleSheet(f"font-size: 20px; color: {CYAN};")
        layout.addWidget(self._icon)

        tcol = QVBoxLayout(); tcol.setSpacing(1); tcol.setContentsMargins(0, 0, 0, 0)
        self._title = QLabel("Dashboard")
        self._title.setStyleSheet(f"color: {TEXT_HI}; font-size: 18px; font-weight: 800; letter-spacing: 0.4px;")
        self._subtitle = QLabel("Session overview & recent activity")
        self._subtitle.setStyleSheet(f"color: {TEXT_LO}; font-size: 11px;")
        tcol.addWidget(self._title); tcol.addWidget(self._subtitle)
        layout.addLayout(tcol)
        layout.addStretch()

    def set_page(self, index: int):
        if 0 <= index < len(self.PAGES):
            icon, title, sub = self.PAGES[index]
            self._icon.setText(icon)
            self._title.setText(title)
            self._subtitle.setText(sub)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor(BG_VOID))
        # subtle bottom divider
        p.setPen(QPen(QColor(BORDER_MID), 1))
        p.drawLine(0, h - 1, w, h - 1)


# ── Disclaimer dialog ─────────────────────────────────────────────────────────

class DisclaimerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DeepSentinel — Educational Disclaimer")
        self.setMinimumWidth(580)
        self.setModal(True)
        self.setStyleSheet(f"background: {BG_VOID}; color: {TEXT_HI};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

        # Logo row
        logo_row = QHBoxLayout()
        logo_row.setSpacing(14)
        logo = HexLogo(52)
        logo_row.addWidget(logo)

        title_block = QWidget()
        tb = QVBoxLayout(title_block)
        tb.setContentsMargins(0, 0, 0, 0)
        tb.setSpacing(2)
        t1 = QLabel("DEEPSENTINEL")
        t1.setStyleSheet(f"color: {CYAN}; font-size: 22px; font-weight: 900; letter-spacing: 4px;")
        t2 = QLabel("AI-Powered Deepfake Detection & Education Platform")
        t2.setStyleSheet(f"color: {TEXT_MID}; font-size: 12px;")
        t3 = QLabel("⚠  IMPORTANT — Please read before continuing")
        t3.setStyleSheet(f"color: {AMBER}; font-size: 11px; font-weight: 700; padding-top: 4px;")
        tb.addWidget(t1); tb.addWidget(t2); tb.addWidget(t3)
        logo_row.addWidget(title_block)
        logo_row.addStretch()
        layout.addLayout(logo_row)

        # Divider
        div = QFrame(); div.setObjectName("divider"); div.setFixedHeight(1)
        layout.addWidget(div)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setFixedHeight(240)
        text.setStyleSheet(
            f"background: {BG_CARD}; border: 1px solid {BORDER_MID}; color: {TEXT_MID}; "
            f"font-size: 12px; border-radius: 10px; padding: 10px; line-height: 1.6;"
        )
        text.setHtml(f"""
<p><b style='color:{CYAN}'>Purpose of this tool:</b></p>
<ul>
  <li>Study how synthetic media is created and detected</li>
  <li>Defend against deepfake threats in media and security contexts</li>
  <li>Academic research, journalism, and digital forensics</li>
  <li>Cybersecurity education and awareness</li>
</ul>
<p><b style='color:{RED}'>Legal Notice:</b></p>
<p>Creating deepfakes of real people without consent is <b>ILLEGAL</b> in many
jurisdictions. This includes non-consensual intimate imagery laws (UK Online
Safety Act 2023, US state laws), computer fraud statutes, defamation laws,
and identity theft provisions. Violations may result in criminal prosecution.</p>
<p><b style='color:{AMBER}'>Not Intended For:</b><br>
Creating non-consensual deepfakes · Fraud or impersonation · Disinformation ·
Harassment or reputational harm</p>
<p>By clicking Continue, you confirm you will use this tool ethically, legally,
and only for legitimate research, education, or defensive security purposes.</p>
""")
        layout.addWidget(text)

        btn_row = QHBoxLayout()
        exit_btn = QPushButton("Exit")
        exit_btn.setObjectName("dangerBtn")
        exit_btn.setFixedSize(100, 40)
        exit_btn.clicked.connect(self.reject)

        cont_btn = QPushButton("✓  I Understand — Continue")
        cont_btn.setObjectName("primaryBtn")
        cont_btn.setFixedHeight(40)
        cont_btn.clicked.connect(self.accept)

        btn_row.addWidget(exit_btn)
        btn_row.addStretch()
        btn_row.addWidget(cont_btn)
        layout.addLayout(btn_row)


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.detector = DeepfakeDetector()
        self._show_disclaimer()

    def _show_disclaimer(self):
        dlg = DisclaimerDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            import sys
            sys.exit(0)
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle("DeepSentinel — AI Deepfake Detection & Education")
        self.setMinimumSize(1160, 760)
        self.resize(1340, 880)

        central = QWidget()
        self.setCentralWidget(central)
        shell = QHBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        # ── Left nav rail ──
        self.sidebar = NavSidebar()
        shell.addWidget(self.sidebar)

        # ── Content column ──
        content = QWidget()
        col = QVBoxLayout(content)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        self.topbar = TopBar()
        col.addWidget(self.topbar)

        self.stack = QStackedWidget()
        col.addWidget(self.stack, 1)
        shell.addWidget(content, 1)

        # Create pages
        self.dashboard_tab = DashboardTab()
        self.live_tab      = LiveTab(self.detector)
        self.analyze_tab   = AnalyzeTab(self.detector)
        self.create_tab    = CreateTab()
        self.batch_tab     = BatchTab(self.detector)
        self.edu_tab       = EducationTab()
        self.settings_tab  = SettingsTab(self.detector)

        for page in [self.dashboard_tab, self.live_tab, self.analyze_tab,
                     self.create_tab, self.batch_tab, self.edu_tab, self.settings_tab]:
            self.stack.addWidget(page)

        # Wire navigation
        self.sidebar.navigate.connect(self._goto)
        self.dashboard_tab.navigate.connect(self._goto)

        # Cross-tab signals
        self.live_tab.status_msg.connect(self._on_status)
        self.live_tab.analysis_done.connect(
            lambda f, v, s: self.dashboard_tab.record_analysis(f, v, s)
        )
        self.live_tab.snapshot_ready.connect(self._on_snapshot)
        self.analyze_tab.status_msg.connect(self._on_status)
        self.analyze_tab.analysis_done.connect(
            lambda f, v, s: self.dashboard_tab.record_analysis(f, v, s)
        )
        self.create_tab.status_msg.connect(self._on_status)
        self.create_tab.detect_requested.connect(self._on_detect_requested)
        self.batch_tab.status_msg.connect(self._on_status)
        self.batch_tab.analysis_done.connect(
            lambda f, v, s: self.dashboard_tab.record_analysis(f, v, s)
        )
        self.settings_tab.status_msg.connect(self._on_status)

        self._build_menu()

        # Status bar
        sb = QStatusBar()
        sb.setStyleSheet(
            f"background: {BG_VOID}; color: {TEXT_DIM}; "
            f"border-top: 1px solid {BORDER_MID}; font-size: 11px; font-family: monospace;"
        )
        self.setStatusBar(sb)
        self._sb_lbl = QLabel(
            f"◈ DeepSentinel v1.0  ·  MesoNet: {self.detector.mesonet.status}  ·  ⚠ Educational use only"
        )
        self._sb_lbl.setStyleSheet(f"color: {TEXT_DIM};")
        sb.addWidget(self._sb_lbl)

        # Start on Dashboard
        self._goto(0)

    def _goto(self, index: int):
        self.stack.setCurrentIndex(index)
        self.sidebar.select(index)
        self.topbar.set_page(index)
        self._fade_current_page()

    def _fade_current_page(self):
        """Subtle fade-in of the freshly shown page."""
        page = self.stack.currentWidget()
        if page is None:
            return
        try:
            fx = QGraphicsOpacityEffect(page)
            page.setGraphicsEffect(fx)
            anim = QPropertyAnimation(fx, b"opacity", self)
            anim.setDuration(190)
            anim.setStartValue(0.35)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            # Drop the effect when done so nested glow effects render normally
            anim.finished.connect(lambda: page.setGraphicsEffect(None))
            anim.start()
            self._page_anim = anim   # keep a ref
        except Exception:
            page.setGraphicsEffect(None)

    # ── Toast notifications ───────────────────────────────────────────────────
    def _toast(self, message: str, kind: str = "info"):
        if not hasattr(self, "_toasts"):
            self._toasts = []
        toast = Toast(self, message, kind)
        self._toasts.append(toast)
        toast.destroyed.connect(lambda *_: self._toasts.remove(toast) if toast in self._toasts else None)
        margin = 20
        x = self.width() - toast.width() - margin
        y = 92
        for existing in self._toasts[:-1]:
            try:
                if existing.isVisible():
                    y += existing.height() + 10
            except RuntimeError:
                pass
        toast.show_at(x, y)

    def _build_menu(self):
        mb = self.menuBar()

        file_m = mb.addMenu("File")
        open_a = QAction("Open Media File…", self)
        open_a.setShortcut("Ctrl+O")
        open_a.triggered.connect(lambda: self._goto(2))
        file_m.addAction(open_a)
        file_m.addSeparator()
        quit_a = QAction("Quit", self)
        quit_a.setShortcut("Ctrl+Q")
        quit_a.triggered.connect(self.close)
        file_m.addAction(quit_a)

        view_m = mb.addMenu("View")
        for i, n in enumerate(["Dashboard", "Live Detection", "Analyze Media",
                               "Face-Swap Lab", "Batch Scan", "How It Works", "Settings"]):
            a = QAction(n, self)
            a.setShortcut(f"Ctrl+{i+1}")
            a.triggered.connect(lambda _, idx=i: self._goto(idx))
            view_m.addAction(a)

        help_m = mb.addMenu("Help")
        about_a = QAction("About DeepSentinel", self)
        about_a.triggered.connect(self._show_about)
        help_m.addAction(about_a)
        disc_a = QAction("View Disclaimer", self)
        disc_a.triggered.connect(lambda: DisclaimerDialog(self).exec())
        help_m.addAction(disc_a)

    # ── Signals ───────────────────────────────────────────────────────────────
    def _on_status(self, msg: str):
        low = msg.lower()
        level = "ok" if "complete" in low or "saved" in low or "installed" in low else (
            "error" if "error" in low or "fail" in low else "info")
        self.sidebar.set_status(msg, level)
        self.statusBar().showMessage(msg, 5000)
        # Surface notable events as toasts (skip chatty progress messages)
        notable = any(k in low for k in
                      ("complete", "saved", "exported", "installed", "error", "fail", "snapshot"))
        if notable:
            self._toast(msg, level)

    def _on_snapshot(self, frame):
        """Live tab sent a snapshot — load into analyze tab and switch to it."""
        self.analyze_tab.load_frame(frame)
        self._goto(2)

    def _on_detect_requested(self, path: str):
        """Face-Swap Lab produced a deepfake — load it into Analyze and run."""
        self.analyze_tab._load_file(path)
        self._goto(2)
        self.analyze_tab._run_analysis()

    def _show_about(self):
        QMessageBox.about(
            self, "About DeepSentinel",
            f"<h3 style='color:{CYAN}'>DeepSentinel v1.0</h3>"
            "<p>AI-Powered Deepfake Detection &amp; Education Platform</p>"
            "<p><b>Detection Methods:</b><br>"
            "FFT Frequency Analysis · Error Level Analysis<br>"
            "Face Geometry (OpenCV Haar) · SRM Noise Analysis<br>"
            "MesoNet Neural Network (optional — PyTorch)</p>"
            "<p><b>Features:</b> Dashboard · Live arc gauge · Snapshot→Analyze<br>"
            "Explainability heatmap · Video temporal analysis (blink + flicker)<br>"
            "Batch folder scan + CSV · Rich HTML/PDF reports · EXIF forensics</p>"
            "<p><b style='color:#f59e0b'>⚠ For educational and research use only.</b></p>"
            "<p>github.com/at0m-b0mb/DeepSentinel</p>"
        )

    def closeEvent(self, event):
        if hasattr(self, 'live_tab') and self.live_tab.worker:
            self.live_tab.worker.stop()
        if hasattr(self, 'batch_tab') and self.batch_tab.worker:
            self.batch_tab.worker.stop()
            self.batch_tab.worker.wait(2000)
        if hasattr(self, 'create_tab') and self.create_tab.worker and self.create_tab.worker.isRunning():
            self.create_tab.worker.wait(2000)
        super().closeEvent(event)
