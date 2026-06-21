"""Dashboard tab — session overview, history, and quick actions."""

import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy, QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from .theme import (
    CYAN, GREEN, RED, AMBER, PURPLE, TEXT_MID, TEXT_LO, TEXT_DIM,
    BG_CARD, BG_CARD2, BORDER_MID, TEXT_HI, BG_HOVER,
)
from .widgets import StatCard, HistoryRow, glow_effect


class DashboardTab(QWidget):
    """Session statistics and recent analysis history."""

    navigate = pyqtSignal(int)  # emitted to switch to another tab

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: list[dict] = []
        self._stats = {"total": 0, "fakes": 0, "suspicious": 0, "real": 0}
        self._session_start = datetime.datetime.now()
        self._build_ui()

    # ── Construction ──────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        # Header row
        hdr_row = QHBoxLayout()
        title = QLabel("SESSION DASHBOARD")
        title.setObjectName("sectionHeader")
        hdr_row.addWidget(title)
        hdr_row.addStretch()

        self._clock_lbl = QLabel()
        self._clock_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; font-family: monospace;")
        hdr_row.addWidget(self._clock_lbl)
        root.addLayout(hdr_row)

        # Stat cards row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        self.card_total = StatCard("📊", "0", "Files Analyzed", CYAN)
        self.card_fakes = StatCard("⚠", "0", "Deepfakes Found", RED)
        self.card_susp  = StatCard("🔶", "0", "Suspicious", AMBER)
        self.card_real  = StatCard("✓", "0", "Confirmed Real", GREEN)
        self.card_time  = StatCard("⏱", "0:00", "Session Time", PURPLE)

        for card in [self.card_total, self.card_fakes, self.card_susp,
                     self.card_real, self.card_time]:
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            glow_effect(card, CYAN, 12)
            cards_row.addWidget(card)

        root.addLayout(cards_row)

        # Middle row: history + quick actions
        mid = QHBoxLayout()
        mid.setSpacing(16)
        mid.addWidget(self._build_history_panel(), 3)
        mid.addWidget(self._build_quick_actions(), 1)
        root.addLayout(mid, 1)

        # Bottom: tips
        root.addWidget(self._build_tips_panel())

        # Clock timer
        from PyQt6.QtCore import QTimer
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

    def _build_history_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        hdr = QHBoxLayout()
        title = QLabel("RECENT ANALYSES")
        title.setObjectName("sectionHeader")
        hdr.addWidget(title)
        hdr.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("ghostBtn")
        clear_btn.setFixedSize(60, 26)
        clear_btn.clicked.connect(self.clear_history)
        hdr.addWidget(clear_btn)
        layout.addLayout(hdr)

        # Divider
        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        layout.addWidget(div)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._history_container = QWidget()
        self._history_layout = QVBoxLayout(self._history_container)
        self._history_layout.setContentsMargins(0, 0, 0, 0)
        self._history_layout.setSpacing(0)
        self._history_layout.addStretch()

        self._empty_lbl = QLabel("No analyses yet — start the camera or drop a file")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; padding: 40px;")
        self._history_layout.insertWidget(0, self._empty_lbl)

        self._scroll.setWidget(self._history_container)
        layout.addWidget(self._scroll, 1)
        return panel

    def _build_quick_actions(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("QUICK ACTIONS")
        title.setObjectName("sectionHeader")
        layout.addWidget(title)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        layout.addWidget(div)

        # (label, absolute tab index in MainWindow) — keep in sync with main_window tab order
        actions = [
            ("🎥  Start Live Detection",  1, "primaryBtn"),
            ("🔍  Analyze a File",         2, "ghostBtn"),
            ("🗂  Batch Folder Scan",      3, "ghostBtn"),
            ("📚  Open How It Works",      4, "ghostBtn"),
            ("⚙   Open Settings",          5, "ghostBtn"),
        ]
        for label, tab_idx, style in actions:
            btn = QPushButton(label)
            btn.setObjectName(style)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda _, i=tab_idx: self.navigate.emit(i))
            layout.addWidget(btn)

        layout.addStretch()

        # System info
        info_group = QGroupBox("System")
        ig_layout = QVBoxLayout(info_group)

        import cv2
        self._sys_labels = {}
        rows = [
            ("OpenCV",  cv2.__version__),
            ("Python",  __import__("sys").version.split()[0]),
        ]
        try:
            import torch
            rows.append(("PyTorch", torch.__version__))
            rows.append(("MPS", "✓" if torch.backends.mps.is_available() else "—"))
        except ImportError:
            rows.append(("PyTorch", "Not installed"))

        for k, v in rows:
            row = QHBoxLayout()
            kl = QLabel(k)
            kl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
            vl = QLabel(str(v))
            vl.setStyleSheet(f"color: {TEXT_MID}; font-size: 11px; font-family: monospace;")
            row.addWidget(kl)
            row.addStretch()
            row.addWidget(vl)
            ig_layout.addLayout(row)

        layout.addWidget(info_group)
        return panel

    def _build_tips_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("card2")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(24)

        tips = [
            ("🎯", "Live Mode", "Use a stable, well-lit environment for best face detection accuracy."),
            ("📎", "Static Files", "Drag & drop images or videos onto the Analyze tab for full forensic analysis."),
            ("🧠", "MesoNet", "Install PyTorch and download pretrained weights to enable the neural network detector."),
            ("⚖", "Results", "Heuristic detection is not 100% reliable. Always verify with additional methods."),
        ]
        for icon, head, body in tips:
            tip_w = QWidget()
            tip_l = QVBoxLayout(tip_w)
            tip_l.setContentsMargins(0, 0, 0, 0)
            tip_l.setSpacing(3)

            top = QHBoxLayout()
            top.setSpacing(6)
            ql = QLabel(icon)
            ql.setStyleSheet("font-size: 14px;")
            top.addWidget(ql)
            hl = QLabel(head)
            hl.setStyleSheet(f"color: {CYAN}; font-size: 11px; font-weight: 700;")
            top.addWidget(hl)
            tip_l.addLayout(top)

            bl = QLabel(body)
            bl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
            bl.setWordWrap(True)
            tip_l.addWidget(bl)

            layout.addWidget(tip_w, 1)

        return panel

    # ── Public API ────────────────────────────────────────────────────────────
    def record_analysis(self, filename: str, verdict: str, score: float):
        """Add one analysis entry — called by live_tab and analyze_tab."""
        import os
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        name = os.path.basename(filename) if filename else "Live Frame"
        self._history.insert(0, {"ts": ts, "name": name, "verdict": verdict, "score": score})
        self._stats["total"] += 1
        if verdict == "DEEPFAKE":
            self._stats["fakes"] += 1
        elif verdict == "SUSPICIOUS":
            self._stats["suspicious"] += 1
        else:
            self._stats["real"] += 1

        self._refresh_history()
        self._refresh_stats()

    def clear_history(self):
        self._history.clear()
        self._stats = {"total": 0, "fakes": 0, "suspicious": 0, "real": 0}
        self._refresh_history()
        self._refresh_stats()

    def _refresh_history(self):
        # Remove old rows
        for i in reversed(range(self._history_layout.count())):
            item = self._history_layout.itemAt(i)
            if item and item.widget() and item.widget() is not self._empty_lbl:
                item.widget().deleteLater()

        if not self._history:
            self._empty_lbl.show()
            return
        self._empty_lbl.hide()

        for entry in self._history[:50]:
            row = HistoryRow(entry["ts"], entry["name"], entry["verdict"], entry["score"])
            self._history_layout.insertWidget(0, row)

    def _refresh_stats(self):
        self.card_total.set_value(str(self._stats["total"]))
        self.card_fakes.set_value(str(self._stats["fakes"]))
        self.card_susp.set_value(str(self._stats["suspicious"]))
        self.card_real.set_value(str(self._stats["real"]))

    def _update_clock(self):
        elapsed = datetime.datetime.now() - self._session_start
        s = int(elapsed.total_seconds())
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        if h > 0:
            self.card_time.set_value(f"{h}:{m:02d}:{sec:02d}")
        else:
            self.card_time.set_value(f"{m}:{sec:02d}")
        self._clock_lbl.setText(datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
