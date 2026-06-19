"""DeepSentinel main application window — redesigned with logo header + dashboard."""

import math
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QStatusBar, QLabel,
    QVBoxLayout, QHBoxLayout, QDialog, QPushButton, QTextEdit,
    QMessageBox, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QFont, QAction, QPainter, QPen, QColor, QLinearGradient,
    QBrush, QConicalGradient, QPainterPath, QPolygonF,
)

from .theme import (
    CYAN, CYAN_MID, CYAN_DIM, RED, RED_DIM, GREEN, AMBER, PURPLE,
    TEXT_HI, TEXT_MID, TEXT_LO, TEXT_DIM,
    BG_VOID, BG_DEEP, BG_CARD, BG_CARD2, BORDER_MID, BORDER_HI, BORDER_CYAN,
    FONT_MONO, FONT_UI,
)
from .widgets import PulsingDot, glow_effect
from ..detection.detector import DeepfakeDetector
from .live_tab import LiveTab
from .analyze_tab import AnalyzeTab
from .education_tab import EducationTab
from .settings_tab import SettingsTab
from .dashboard_tab import DashboardTab


# ── Hex logo widget ───────────────────────────────────────────────────────────

class HexLogo(QWidget):
    """Painted hexagonal eye/shield logo for DeepSentinel."""

    def __init__(self, size: int = 40, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._hue = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    def _tick(self):
        self._hue = (self._hue + 0.8) % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        s = self._size
        cx, cy = s / 2, s / 2
        r = s / 2 - 3

        # Hex vertices
        hex_pts = []
        for i in range(6):
            a = math.radians(60 * i - 30)
            hex_pts.append(QPointF(cx + r * math.cos(a), cy + r * math.sin(a)))
        polygon = QPolygonF(hex_pts)

        # Glow fill
        glow_color = QColor(CYAN)
        glow_color.setAlpha(30)
        p.setBrush(glow_color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(polygon)

        # Hex outline with gradient
        h = self._hue
        c1 = QColor.fromHsvF(h / 360.0, 0.9, 1.0)
        c2 = QColor.fromHsvF(((h + 120) % 360) / 360.0, 0.9, 1.0)
        grad = QConicalGradient(cx, cy, 0)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(0.5, c2)
        grad.setColorAt(1.0, c1)
        p.setPen(QPen(QBrush(grad), 2.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(polygon)

        # Inner eye shape
        ir = r * 0.52
        eye_w = ir * 1.6
        eye_h = ir * 0.65
        p.setPen(QPen(QColor(CYAN), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(cx - eye_w / 2, cy - eye_h / 2, eye_w, eye_h))

        # Pupil
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(CYAN))
        p.drawEllipse(QPointF(cx, cy), eye_h * 0.4, eye_h * 0.4)

        # Center dot
        p.setBrush(QColor(BG_VOID))
        p.drawEllipse(QPointF(cx, cy), eye_h * 0.18, eye_h * 0.18)


# ── Header widget ─────────────────────────────────────────────────────────────

class HeaderWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(58)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(12)

        # Animated hex logo
        self.logo = HexLogo(38)
        layout.addWidget(self.logo)

        # Brand text block
        brand_block = QWidget()
        bl = QVBoxLayout(brand_block)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        name_lbl = QLabel("DEEP<span style='color:#e8e8ff; font-weight:400'>SENTINEL</span>")
        name_lbl.setTextFormat(Qt.TextFormat.RichText)
        name_lbl.setStyleSheet(
            f"color: {CYAN}; font-size: 18px; font-weight: 900; "
            f"letter-spacing: 3px; font-family: {FONT_UI};"
        )
        bl.addWidget(name_lbl)

        tag_lbl = QLabel("AI-Powered Deepfake Detection  ·  Educational Platform  ·  v1.0")
        tag_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; letter-spacing: 0.5px;")
        bl.addWidget(tag_lbl)

        layout.addWidget(brand_block)
        layout.addStretch()

        # Status area
        status_block = QWidget()
        sl = QHBoxLayout(status_block)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(8)

        self._status_dot = PulsingDot(CYAN)
        self._status_dot.stop()
        sl.addWidget(self._status_dot)

        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; font-family: monospace;")
        sl.addWidget(self._status_lbl)

        layout.addWidget(status_block)

        # Edu badge
        badge = QLabel("⚠  EDUCATIONAL USE ONLY")
        badge.setStyleSheet(
            f"color: {AMBER}; background: {AMBER}18; border: 1px solid {AMBER}44; "
            f"border-radius: 5px; font-size: 9px; font-weight: 800; "
            f"letter-spacing: 1.5px; padding: 3px 8px;"
        )
        layout.addWidget(badge)

    def set_status(self, msg: str, level: str = "info"):
        colors = {"info": TEXT_DIM, "ok": GREEN, "warn": AMBER, "error": RED}
        dot_colors = {"info": CYAN, "ok": GREEN, "warn": AMBER, "error": RED}
        self._status_lbl.setText(msg[-60:] if len(msg) > 60 else msg)
        self._status_lbl.setStyleSheet(
            f"color: {colors.get(level, TEXT_DIM)}; font-size: 11px; font-family: monospace;"
        )
        self._status_dot._color = QColor(dot_colors.get(level, CYAN))
        if level in ("ok", "warn", "error"):
            self._status_dot.start()
            QTimer.singleShot(3000, self._status_dot.stop)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Dark gradient background
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor("#08081a"))
        grad.setColorAt(0.4, QColor("#0a0a18"))
        grad.setColorAt(1.0, QColor("#06060f"))
        p.fillRect(self.rect(), grad)

        # Subtle bottom border with cyan glow
        p.setPen(QPen(QColor(CYAN + "30"), 1))
        p.drawLine(0, h - 1, w, h - 1)

        # Faint hex grid pattern (decorative)
        p.setPen(QPen(QColor("#ffffff06"), 1))
        hex_r = 14
        for row in range(4):
            for col in range(w // (hex_r * 3) + 2):
                offset = (hex_r * 1.5) if row % 2 else 0
                hx = col * hex_r * 3 + offset - hex_r
                hy = row * hex_r * 1.73 - hex_r * 0.5
                pts = []
                for i in range(6):
                    a = math.radians(60 * i)
                    pts.append(QPointF(hx + hex_r * math.cos(a), hy + hex_r * math.sin(a)))
                p.drawPolygon(QPolygonF(pts))


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
        self.setMinimumSize(1100, 750)
        self.resize(1300, 860)

        central = QWidget()
        self.setCentralWidget(central)
        main_l = QVBoxLayout(central)
        main_l.setContentsMargins(0, 0, 0, 0)
        main_l.setSpacing(0)

        # Header
        self.header = HeaderWidget()
        main_l.addWidget(self.header)

        # Tabs
        self.tabs = QTabWidget()
        main_l.addWidget(self.tabs, 1)

        # Create tabs
        self.dashboard_tab = DashboardTab()
        self.live_tab      = LiveTab(self.detector)
        self.analyze_tab   = AnalyzeTab(self.detector)
        self.edu_tab       = EducationTab()
        self.settings_tab  = SettingsTab(self.detector)

        self.tabs.addTab(self.dashboard_tab, "  ◈  Dashboard  ")
        self.tabs.addTab(self.live_tab,      "  🎥  Live Detection  ")
        self.tabs.addTab(self.analyze_tab,   "  🔍  Analyze Media  ")
        self.tabs.addTab(self.edu_tab,       "  📚  How It Works  ")
        self.tabs.addTab(self.settings_tab,  "  ⚙   Settings  ")

        # Wire up cross-tab signals
        self.dashboard_tab.navigate.connect(self.tabs.setCurrentIndex)
        self.live_tab.status_msg.connect(self._on_status)
        self.live_tab.analysis_done.connect(
            lambda f, v, s: self.dashboard_tab.record_analysis(f, v, s)
        )
        self.live_tab.snapshot_ready.connect(self._on_snapshot)
        self.analyze_tab.status_msg.connect(self._on_status)
        self.analyze_tab.analysis_done.connect(
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

    def _build_menu(self):
        mb = self.menuBar()

        file_m = mb.addMenu("File")
        open_a = QAction("Open Media File…", self)
        open_a.setShortcut("Ctrl+O")
        open_a.triggered.connect(lambda: self.tabs.setCurrentIndex(2))
        file_m.addAction(open_a)
        file_m.addSeparator()
        quit_a = QAction("Quit", self)
        quit_a.setShortcut("Ctrl+Q")
        quit_a.triggered.connect(self.close)
        file_m.addAction(quit_a)

        view_m = mb.addMenu("View")
        for i, n in enumerate(["Dashboard", "Live Detection", "Analyze Media", "How It Works", "Settings"]):
            a = QAction(n, self)
            a.triggered.connect(lambda _, idx=i: self.tabs.setCurrentIndex(idx))
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
        self.header.set_status(msg, "ok" if "complete" in msg.lower() else "info")
        self.statusBar().showMessage(msg, 5000)

    def _on_snapshot(self, frame):
        """Live tab sent a snapshot — load into analyze tab and switch to it."""
        self.analyze_tab.load_frame(frame)
        self.tabs.setCurrentIndex(2)

    def _show_about(self):
        QMessageBox.about(
            self, "About DeepSentinel",
            f"<h3 style='color:{CYAN}'>DeepSentinel v1.0</h3>"
            "<p>AI-Powered Deepfake Detection &amp; Education Platform</p>"
            "<p><b>Detection Methods:</b><br>"
            "FFT Frequency Analysis · Error Level Analysis<br>"
            "Face Geometry (OpenCV Haar) · SRM Noise Analysis<br>"
            "MesoNet Neural Network (optional — PyTorch)</p>"
            "<p><b>New in v1.0:</b> Dashboard, Snapshot→Analyze, EXIF forensics,<br>"
            "Arc confidence gauge, real-time history graph, batch reports</p>"
            "<p><b style='color:#f59e0b'>⚠ For educational and research use only.</b></p>"
            "<p>github.com/at0m-b0mb/DeepSentinel</p>"
        )

    def closeEvent(self, event):
        if hasattr(self, 'live_tab') and self.live_tab.worker:
            self.live_tab.worker.stop()
        super().closeEvent(event)
