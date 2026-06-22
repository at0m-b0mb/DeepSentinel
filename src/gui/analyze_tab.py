"""Static image/video analysis tab — redesigned with EXIF panel and enhanced layout."""

import os
import datetime
import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QFrame, QFileDialog, QGroupBox, QSizePolicy, QScrollArea,
    QTextEdit, QSplitter, QTabWidget, QProgressBar, QMenu,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QMimeData
from PyQt6.QtGui import QImage, QPixmap, QDragEnterEvent, QDropEvent, QFont, QAction

from .theme import (
    CYAN, CYAN_DIM, GREEN, RED, AMBER, PURPLE, TEXT_MID, TEXT_LO, TEXT_DIM,
    BG_CARD, BG_CARD2, BG_VOID, BG_SURFACE, BORDER_MID, TEXT_HI, rgba,
)
from .widgets import ConfidenceDial, GlowScoreBar, TimelineGraph, glow_effect, verdict_view
from ..detection.detector import DeepfakeDetector, DetectionResult
from ..detection.metadata import extract_metadata, flag_suspicious
from ..detection.heatmap import suspicion_heatmap
from ..detection.temporal import analyze_video_temporal, TemporalResult
from ..detection import report as report_mod


# ── Analysis worker ───────────────────────────────────────────────────────────

class AnalysisWorker(QThread):
    progress      = pyqtSignal(int, str)
    result_ready  = pyqtSignal(object)
    viz_ready     = pyqtSignal(str, np.ndarray)
    heatmap_ready = pyqtSignal(np.ndarray, float)    # overlay BGR, concentration
    temporal_ready = pyqtSignal(object)              # TemporalResult
    error         = pyqtSignal(str)

    def __init__(self, detector: DeepfakeDetector, path: str):
        super().__init__()
        self.detector = detector
        self.path = path

    def run(self):
        ext = os.path.splitext(self.path)[1].lower()
        if ext in ('.mp4', '.mov', '.avi', '.mkv', '.webm'):
            self._analyze_video()
        else:
            self._analyze_image()

    def _analyze_image(self):
        self.progress.emit(8, "Loading image…")
        img = cv2.imread(self.path)
        if img is None:
            self.error.emit(f"Cannot read: {os.path.basename(self.path)}")
            return

        self.detector.use_ela = True
        self.progress.emit(30, "Running forensic analysis…")
        result = self.detector.analyze(img, fast=False)
        self.detector.use_ela = False

        self.progress.emit(65, "Building visualizations…")
        for title, viz in result.viz_frames.items():
            if viz is not None:
                resized = cv2.resize(viz, (320, 240))
                self.viz_ready.emit(title, resized)

        # Explainability heatmap
        self.progress.emit(85, "Computing suspicion heatmap…")
        try:
            overlay, heat_color, conc = suspicion_heatmap(img)
            self.heatmap_ready.emit(overlay, conc)
            self.viz_ready.emit("Suspicion Heatmap", cv2.resize(heat_color, (320, 240)))
        except Exception as e:
            print(f"Heatmap failed: {e}")

        self.progress.emit(100, "Done")
        self.result_ready.emit(result)

    def _analyze_video(self):
        # Full temporal analysis (per-frame scores, blink rate, flicker)
        self.progress.emit(4, "Starting temporal analysis…")
        temporal = analyze_video_temporal(
            self.path, self.detector, max_frames=48,
            progress_cb=lambda p, m: self.progress.emit(int(p * 0.8), m),
        )
        if temporal.frames_analyzed == 0:
            self.error.emit("No frames could be analyzed.")
            return
        self.temporal_ready.emit(temporal)

        # Representative still analysis on the peak-suspicion frame
        self.progress.emit(84, "Analyzing peak frame…")
        peak_ts = max(temporal.frame_scores, key=lambda x: x[1])[0] if temporal.frame_scores else 0
        cap = cv2.VideoCapture(self.path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(peak_ts * fps))
        ret, peak_frame = cap.read()
        cap.release()
        if not ret:
            cap2 = cv2.VideoCapture(self.path)
            ret, peak_frame = cap2.read()
            cap2.release()

        small = cv2.resize(peak_frame, (480, 360))
        self.detector.use_ela = True
        result = self.detector.analyze(small, fast=False)
        self.detector.use_ela = False

        # Blend in the temporal verdict (temporal score weighted with frame score)
        combined = float(np.clip(0.5 * result.overall_score + 0.5 * temporal.temporal_score, 0, 1))
        result.overall_score = combined
        if combined >= 0.65:
            result.label, result.confidence_pct = "DEEPFAKE", combined * 100
        elif combined >= 0.40:
            result.label, result.confidence_pct = "SUSPICIOUS", combined * 100
        else:
            result.label, result.confidence_pct = "REAL", (1 - combined) * 100

        self.progress.emit(90, "Building visualizations…")
        for title, viz in result.viz_frames.items():
            if viz is not None:
                self.viz_ready.emit(title, cv2.resize(viz, (320, 240)))
        try:
            overlay, heat_color, conc = suspicion_heatmap(small)
            self.heatmap_ready.emit(overlay, conc)
            self.viz_ready.emit("Suspicion Heatmap", cv2.resize(heat_color, (320, 240)))
        except Exception as e:
            print(f"Heatmap failed: {e}")

        self.progress.emit(100, "Done")
        self.result_ready.emit(result)


# ── Drop Zone ─────────────────────────────────────────────────────────────────

class DropZone(QLabel):
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(120)
        self._idle_style()
        self.setText("Drop image or video here\nor click Browse to open a file")
        f = QFont(); f.setPointSize(12)
        self.setFont(f)

    def _idle_style(self):
        self.setStyleSheet(
            f"border: 2px dashed {BORDER_MID}; border-radius: 12px; "
            f"background: transparent; color: {TEXT_DIM}; padding: 16px;"
        )

    def _hover_style(self):
        self.setStyleSheet(
            f"border: 2px dashed {CYAN}; border-radius: 12px; "
            f"background: {rgba(CYAN, 0.08)}; color: {CYAN}; padding: 16px;"
        )

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._hover_style()

    def dragLeaveEvent(self, _):
        self._idle_style()

    def dropEvent(self, e: QDropEvent):
        self._idle_style()
        urls = e.mimeData().urls()
        if urls:
            self.file_dropped.emit(urls[0].toLocalFile())

    def mousePressEvent(self, _):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Media File", "",
            "Images & Videos (*.png *.jpg *.jpeg *.bmp *.webp *.tiff *.mp4 *.mov *.avi *.mkv)"
        )
        if path:
            self.file_dropped.emit(path)


# ── Viz thumbnail ─────────────────────────────────────────────────────────────

class VizThumb(QFrame):
    def __init__(self, title: str, frame: np.ndarray, parent=None):
        super().__init__(parent)
        self.setObjectName("card2")
        self.setFixedSize(210, 175)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        lbl = QLabel(title.upper())
        lbl.setStyleSheet(f"color: {CYAN_DIM}; font-size: 9px; font-weight: 800; letter-spacing: 1.5px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

        img_lbl = QLabel()
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h, w = frame.shape[:2]
        qt = QImage(frame.data, w, h, w * frame.shape[2], QImage.Format.Format_BGR888)
        pix = QPixmap.fromImage(qt).scaled(196, 148, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)
        img_lbl.setPixmap(pix)
        layout.addWidget(img_lbl, 1)


# ── Main tab ──────────────────────────────────────────────────────────────────

class AnalyzeTab(QWidget):
    status_msg    = pyqtSignal(str)
    analysis_done = pyqtSignal(str, str, float)   # path, verdict, score

    def __init__(self, detector: DeepfakeDetector, parent=None):
        super().__init__(parent)
        self.detector = detector
        self.worker: AnalysisWorker | None = None
        self._current_path: str | None = None
        self._last_result: DetectionResult | None = None
        # New-feature state
        self._preview_img: np.ndarray | None = None       # original BGR preview
        self._heatmap_overlay: np.ndarray | None = None    # heatmap overlay BGR
        self._heatmap_color: np.ndarray | None = None      # standalone heatmap
        self._temporal: TemporalResult | None = None
        self._exif_meta: dict = {}
        self._exif_flags: list = []
        self._viz_store: dict = {}                          # title -> frame
        self._showing_heatmap = False
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setHandleWidth(4)
        splitter.setChildrenCollapsible(False)

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.addWidget(splitter)

        splitter.addWidget(self._left_panel())
        splitter.addWidget(self._right_panel())
        splitter.setSizes([640, 380])

    # ── Left (media + preview + viz) ─────────────────────────────────────────
    def _left_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Drop zone + browse row
        dz_card = QFrame(); dz_card.setObjectName("card")
        dz_l = QVBoxLayout(dz_card)
        dz_l.setContentsMargins(12, 12, 12, 12)
        dz_l.setSpacing(8)

        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self._load_file)
        dz_l.addWidget(self.drop_zone)

        btn_row = QHBoxLayout()
        browse_btn = QPushButton("📂  Browse File")
        browse_btn.clicked.connect(lambda: self.drop_zone.mousePressEvent(None))
        browse_btn.setFixedHeight(34)
        btn_row.addWidget(browse_btn)

        self.file_lbl = QLabel()
        self.file_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; font-family: monospace;")
        btn_row.addWidget(self.file_lbl, 1)
        dz_l.addLayout(btn_row)
        layout.addWidget(dz_card)

        # Preview + heatmap toggle
        preview_card = QFrame()
        preview_card.setObjectName("card")
        pc_l = QVBoxLayout(preview_card)
        pc_l.setContentsMargins(10, 8, 10, 10)
        pc_l.setSpacing(6)

        pv_hdr = QHBoxLayout()
        pv_title = QLabel("PREVIEW")
        pv_title.setObjectName("sectionHeader")
        pv_hdr.addWidget(pv_title)
        pv_hdr.addStretch()

        self.heatmap_btn = QPushButton("🔥  Show Heatmap")
        self.heatmap_btn.setObjectName("ghostBtn")
        self.heatmap_btn.setFixedHeight(26)
        self.heatmap_btn.setEnabled(False)
        self.heatmap_btn.setToolTip("Toggle the explainability suspicion heatmap overlay")
        self.heatmap_btn.clicked.connect(self._toggle_heatmap)
        pv_hdr.addWidget(self.heatmap_btn)
        pc_l.addLayout(pv_hdr)

        self.preview_lbl = QLabel()
        self.preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_lbl.setMinimumHeight(180)
        self.preview_lbl.setStyleSheet(
            f"background: {BG_VOID}; border: 1px solid {BORDER_MID}; border-radius: 10px;"
        )
        pc_l.addWidget(self.preview_lbl, 1)

        self.heatmap_legend = QLabel()
        self.heatmap_legend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.heatmap_legend.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        self.heatmap_legend.setVisible(False)
        pc_l.addWidget(self.heatmap_legend)

        layout.addWidget(preview_card, 1)

        # Forensic viz strip
        viz_group = QGroupBox("Forensic Visualizations")
        viz_l = QVBoxLayout(viz_group)
        viz_l.setContentsMargins(6, 12, 6, 6)

        self.viz_scroll = QScrollArea()
        self.viz_scroll.setWidgetResizable(True)
        self.viz_scroll.setFixedHeight(192)
        self.viz_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.viz_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viz_container = QWidget()
        self.viz_row = QHBoxLayout(self.viz_container)
        self.viz_row.setContentsMargins(4, 4, 4, 4)
        self.viz_row.setSpacing(8)
        self.viz_row.addStretch()
        self.viz_scroll.setWidget(self.viz_container)
        viz_l.addWidget(self.viz_scroll)
        layout.addWidget(viz_group)

        return w

    # ── Right (results + EXIF) ────────────────────────────────────────────────
    def _right_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        hdr = QLabel("ANALYSIS RESULTS")
        hdr.setObjectName("sectionHeader")
        layout.addWidget(hdr)

        # Verdict card
        verdict_card = QFrame()
        verdict_card.setObjectName("glowCard")
        vc_l = QVBoxLayout(verdict_card)
        vc_l.setContentsMargins(16, 12, 16, 12)
        vc_l.setSpacing(6)
        vc_l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.dial = ConfidenceDial()
        glow_effect(self.dial, CYAN, 16)
        vc_l.addWidget(self.dial, 0, Qt.AlignmentFlag.AlignHCenter)

        self.verdict_lbl = QLabel("—")
        self.verdict_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verdict_lbl.setObjectName("verdictLabel")
        self.verdict_lbl.setStyleSheet(f"color: {TEXT_DIM}; letter-spacing: 5px; font-size: 16px; font-weight: 900;")
        vc_l.addWidget(self.verdict_lbl)

        self.conf_lbl = QLabel("Confidence: —")
        self.conf_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.conf_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        vc_l.addWidget(self.conf_lbl)

        layout.addWidget(verdict_card)

        # Progress bar
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setFixedHeight(5)
        self.prog_bar.setTextVisible(False)
        self.prog_bar.setVisible(False)
        layout.addWidget(self.prog_bar)

        self.prog_lbl = QLabel()
        self.prog_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; font-family: monospace;")
        self.prog_lbl.setVisible(False)
        layout.addWidget(self.prog_lbl)

        # Results tab widget (scores | EXIF | report)
        self.result_tabs = QTabWidget()
        self.result_tabs.setStyleSheet("""
            QTabBar::tab { min-width: 80px; padding: 6px 12px; font-size: 11px; }
        """)

        self.result_tabs.addTab(self._scores_panel(),   "Scores")
        self.result_tabs.addTab(self._temporal_panel(), "Temporal")
        self.result_tabs.addTab(self._exif_panel(),     "Metadata")
        self.result_tabs.addTab(self._report_panel(),   "Report")
        self._temporal_tab_idx = 1
        layout.addWidget(self.result_tabs, 1)

        # Buttons
        btn_row = QHBoxLayout()
        self.analyze_btn = QPushButton("🔍  Analyze")
        self.analyze_btn.setObjectName("primaryBtn")
        self.analyze_btn.setFixedHeight(40)
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._run_analysis)
        btn_row.addWidget(self.analyze_btn, 2)

        self.export_btn = QPushButton("💾  Export  ▾")
        self.export_btn.setFixedHeight(40)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._show_export_menu)
        btn_row.addWidget(self.export_btn)

        layout.addLayout(btn_row)
        return w

    def _scores_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(6)

        self.bar_fft   = GlowScoreBar("FFT Artifacts")
        self.bar_ela   = GlowScoreBar("ELA Forensics")
        self.bar_face  = GlowScoreBar("Face Geometry")
        self.bar_noise = GlowScoreBar("Noise Pattern")
        self.bar_meso  = GlowScoreBar("MesoNet (NN)")

        for b in [self.bar_fft, self.bar_ela, self.bar_face, self.bar_noise, self.bar_meso]:
            layout.addWidget(b)

        self.faces_lbl = QLabel("Faces detected: —")
        self.faces_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; padding-top: 4px;")
        layout.addWidget(self.faces_lbl)
        layout.addStretch()
        return w

    def _temporal_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(8)

        self.temporal_hint = QLabel("Load a video file to see per-frame timeline,\nblink-rate, and flicker analysis.")
        self.temporal_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.temporal_hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; padding: 20px;")
        layout.addWidget(self.temporal_hint)

        self.timeline = TimelineGraph()
        self.timeline.setVisible(False)
        layout.addWidget(self.timeline, 1)

        # Temporal stat chips
        self.temporal_stats = QWidget()
        ts_l = QHBoxLayout(self.temporal_stats)
        ts_l.setContentsMargins(0, 0, 0, 0)
        ts_l.setSpacing(8)
        self._tstat_labels = {}
        for key, name in [("verdict", "VERDICT"), ("blink", "BLINK RATE"),
                          ("flicker", "FLICKER"), ("frames", "FRAMES")]:
            chip = QFrame(); chip.setObjectName("card2")
            cl = QVBoxLayout(chip); cl.setContentsMargins(10, 6, 10, 6); cl.setSpacing(1)
            val = QLabel("—")
            val.setStyleSheet(f"color: {CYAN}; font-size: 15px; font-weight: 800; font-family: monospace;")
            nm = QLabel(name)
            nm.setStyleSheet(f"color: {TEXT_DIM}; font-size: 8px; font-weight: 700; letter-spacing: 1px;")
            cl.addWidget(val); cl.addWidget(nm)
            self._tstat_labels[key] = val
            ts_l.addWidget(chip, 1)
        self.temporal_stats.setVisible(False)
        layout.addWidget(self.temporal_stats)

        self.temporal_notes = QLabel()
        self.temporal_notes.setWordWrap(True)
        self.temporal_notes.setStyleSheet(f"color: {AMBER}; font-size: 11px;")
        self.temporal_notes.setVisible(False)
        layout.addWidget(self.temporal_notes)
        return w

    def _exif_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(6)

        self.exif_flags_lbl = QLabel()
        self.exif_flags_lbl.setWordWrap(True)
        self.exif_flags_lbl.setStyleSheet(f"color: {AMBER}; font-size: 11px;")
        layout.addWidget(self.exif_flags_lbl)

        self.exif_scroll = QScrollArea()
        self.exif_scroll.setWidgetResizable(True)
        self.exif_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.exif_container = QWidget()
        self.exif_layout = QVBoxLayout(self.exif_container)
        self.exif_layout.setContentsMargins(0, 0, 0, 0)
        self.exif_layout.setSpacing(3)
        self.exif_layout.addStretch()
        self.exif_scroll.setWidget(self.exif_container)
        layout.addWidget(self.exif_scroll, 1)
        return w

    def _report_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 4, 0, 0)
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setStyleSheet(
            f"font-family: 'JetBrains Mono', Menlo, monospace; font-size: 11px; color: {TEXT_MID}; "
            f"background: {BG_VOID}; border: none; border-radius: 8px; padding: 8px;"
        )
        layout.addWidget(self.report_text)
        return w

    # ── Load file ─────────────────────────────────────────────────────────────
    def _load_file(self, path: str):
        self._current_path = path
        self.analyze_btn.setEnabled(True)

        # Clear old state
        self._clear_viz()
        self.report_text.clear()
        self._clear_exif()
        self.dial.reset()
        self.verdict_lbl.setText("—")
        self.verdict_lbl.setStyleSheet(f"color: {TEXT_DIM}; letter-spacing: 5px; font-size: 16px; font-weight: 900;")
        self.conf_lbl.setText("Confidence: —")

        # Reset new-feature state
        self._heatmap_overlay = None
        self._heatmap_color = None
        self._temporal = None
        self._viz_store = {}
        self._showing_heatmap = False
        self.heatmap_btn.setEnabled(False)
        self.heatmap_btn.setText("🔥  Show Heatmap")
        self.heatmap_legend.setVisible(False)
        self.timeline.setVisible(False)
        self.temporal_stats.setVisible(False)
        self.temporal_notes.setVisible(False)
        self.temporal_hint.setVisible(True)

        # Preview
        img = cv2.imread(path)
        if img is not None:
            self._preview_img = img
            self._show_preview(img)
        else:
            cap = cv2.VideoCapture(path)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    self._preview_img = frame
                    self._show_preview(frame)
                cap.release()

        # File label
        name = os.path.basename(path)
        self.file_lbl.setText(name)
        self.drop_zone.setText(f"✓  {name}")

        # EXIF immediately
        self._show_exif(path)

        self.status_msg.emit(f"Loaded: {path}")

    def load_frame(self, frame: np.ndarray):
        """Called from live tab snapshot."""
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        cv2.imwrite(tmp.name, frame)
        tmp.close()
        self._load_file(tmp.name)
        self.file_lbl.setText("Live Snapshot")
        self.drop_zone.setText("✓  Live Snapshot")

    def _show_preview(self, img: np.ndarray):
        h, w = img.shape[:2]
        qt = QImage(img.data, w, h, w * 3, QImage.Format.Format_BGR888)
        pix = QPixmap.fromImage(qt).scaled(
            max(self.preview_lbl.width(), 300), max(self.preview_lbl.height(), 200),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_lbl.setPixmap(pix)

    # ── EXIF ─────────────────────────────────────────────────────────────────
    def _show_exif(self, path: str):
        self._clear_exif()
        meta = extract_metadata(path)
        flags = flag_suspicious(meta)
        self._exif_meta = meta
        self._exif_flags = flags

        if flags:
            self.exif_flags_lbl.setText("\n".join(flags))
        else:
            self.exif_flags_lbl.setText("")

        for k, v in meta.items():
            if k.startswith("_"):
                continue
            row = QHBoxLayout()
            kl = QLabel(k + ":")
            kl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; min-width: 100px; font-weight: 600;")
            kl.setFixedWidth(120)
            vl = QLabel(str(v))
            vl.setStyleSheet(f"color: {TEXT_MID}; font-size: 11px; font-family: monospace;")
            vl.setWordWrap(True)
            row.addWidget(kl)
            row.addWidget(vl, 1)
            container = QWidget()
            container.setLayout(row)
            self.exif_layout.insertWidget(self.exif_layout.count() - 1, container)

    def _clear_exif(self):
        for i in reversed(range(self.exif_layout.count())):
            item = self.exif_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self.exif_layout.addStretch()
        self.exif_flags_lbl.setText("")

    # ── Analysis ──────────────────────────────────────────────────────────────
    def _run_analysis(self):
        if not self._current_path or (self.worker and self.worker.isRunning()):
            return
        self.analyze_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.prog_bar.setVisible(True)
        self.prog_bar.setValue(0)
        self.prog_lbl.setVisible(True)

        self.worker = AnalysisWorker(self.detector, self._current_path)
        self.worker.progress.connect(self._on_progress)
        self.worker.result_ready.connect(self._on_result)
        self.worker.viz_ready.connect(self._add_viz)
        self.worker.heatmap_ready.connect(self._on_heatmap)
        self.worker.temporal_ready.connect(self._on_temporal)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, pct: int, msg: str):
        self.prog_bar.setValue(pct)
        self.prog_lbl.setText(msg)
        self.status_msg.emit(msg)

    def _on_result(self, r: DetectionResult):
        self.prog_bar.setVisible(False)
        self.prog_lbl.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self._last_result = r

        flabel, conf, qcolor = verdict_view(r.overall_score)
        color = qcolor.name()

        self.dial.set_result(r.overall_score)
        self.verdict_lbl.setText(flabel)
        self.verdict_lbl.setStyleSheet(
            f"color: {color}; letter-spacing: 4px; font-size: 17px; font-weight: 900;"
        )
        self.conf_lbl.setText(f"{conf*100:.0f}% confidence  ·  raw score {r.overall_score:.2f}")
        self.conf_lbl.setStyleSheet(f"color: {color}; font-size: 12px;")

        self.bar_fft.set_score(r.fft_score)
        self.bar_ela.set_score(r.ela_score)
        self.bar_face.set_score(r.face_score)
        self.bar_noise.set_score(r.noise_score)
        self.bar_meso.set_score(r.mesonet_score)
        self.faces_lbl.setText(f"Faces detected: {r.faces_found}   •   Methods used: {r.methods_used}")

        self.report_text.setPlainText(self._build_report(r))
        self.analysis_done.emit(self._current_path or "Unknown", r.label, r.overall_score)
        self.status_msg.emit(f"Analysis complete: {r.label} ({r.confidence_pct:.1f}%)")

    def _add_viz(self, title: str, frame: np.ndarray):
        self._viz_store[title] = frame.copy()
        stretch = self.viz_row.takeAt(self.viz_row.count() - 1)
        self.viz_row.addWidget(VizThumb(title, frame))
        if stretch:
            self.viz_row.addStretch()

    # ── Heatmap ───────────────────────────────────────────────────────────────
    def _on_heatmap(self, overlay: np.ndarray, concentration: float):
        self._heatmap_overlay = overlay
        self.heatmap_btn.setEnabled(True)
        self.heatmap_legend.setText(
            f"🟦 clean → 🟥 suspect    ·    hotspot concentration: {concentration*100:.0f}%"
        )

    def _toggle_heatmap(self):
        if self._heatmap_overlay is None:
            return
        self._showing_heatmap = not self._showing_heatmap
        if self._showing_heatmap:
            self._show_preview(self._heatmap_overlay)
            self.heatmap_btn.setText("🖼  Show Original")
            self.heatmap_legend.setVisible(True)
        else:
            if self._preview_img is not None:
                self._show_preview(self._preview_img)
            self.heatmap_btn.setText("🔥  Show Heatmap")
            self.heatmap_legend.setVisible(False)

    # ── Temporal ──────────────────────────────────────────────────────────────
    def _on_temporal(self, t: TemporalResult):
        self._temporal = t
        self.temporal_hint.setVisible(False)
        self.timeline.setVisible(True)
        self.temporal_stats.setVisible(True)
        self.temporal_notes.setVisible(True)

        self.timeline.set_series(t.frame_scores, t.duration_s)

        colors = {"REAL": GREEN, "SUSPICIOUS": AMBER, "DEEPFAKE": RED}
        vc = colors.get(t.label, TEXT_MID)
        self._tstat_labels["verdict"].setText(t.label)
        self._tstat_labels["verdict"].setStyleSheet(
            f"color: {vc}; font-size: 13px; font-weight: 800; font-family: monospace;"
        )
        blink_c = RED if t.blink_flag else TEXT_HI
        self._tstat_labels["blink"].setText(f"{t.blink_rate:.0f}/m")
        self._tstat_labels["blink"].setStyleSheet(
            f"color: {blink_c}; font-size: 15px; font-weight: 800; font-family: monospace;"
        )
        flick_c = RED if t.flicker_score > 0.5 else AMBER if t.flicker_score > 0.3 else GREEN
        self._tstat_labels["flicker"].setText(f"{t.flicker_score:.2f}")
        self._tstat_labels["flicker"].setStyleSheet(
            f"color: {flick_c}; font-size: 15px; font-weight: 800; font-family: monospace;"
        )
        self._tstat_labels["frames"].setText(str(t.frames_analyzed))

        self.temporal_notes.setText("  •  " + "\n  •  ".join(t.notes))
        # Auto-switch to temporal tab so the user sees it
        self.result_tabs.setCurrentIndex(self._temporal_tab_idx)

    def _clear_viz(self):
        for i in reversed(range(self.viz_row.count())):
            item = self.viz_row.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self.viz_row.addStretch()

    def _on_error(self, msg: str):
        self.prog_bar.setVisible(False)
        self.prog_lbl.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.report_text.setPlainText(f"ERROR: {msg}")
        self.status_msg.emit(f"Error: {msg}")

    def _build_report(self, r: DetectionResult) -> str:
        lines = [
            "╔══════════════════════════════════════════════════════════╗",
            "║           DEEPSENTINEL ANALYSIS REPORT                  ║",
            "╚══════════════════════════════════════════════════════════╝",
            f"  Date     : {datetime.datetime.now():%Y-%m-%d %H:%M:%S}",
            f"  File     : {os.path.basename(self._current_path or 'Unknown')}",
            "",
            "  VERDICT",
            f"  ┌── {r.label} ──────────────────────────────────────────────",
            f"  │  Deepfake Score : {r.overall_score:.4f}  ({r.confidence_pct:.1f}%)",
            f"  │  Faces Found    : {r.faces_found}",
            f"  │  Methods Used   : {r.methods_used}",
            "  └───────────────────────────────────────────────────────",
            "",
            "  METHOD SCORES",
            f"  FFT Artifacts   : {r.fft_score:.4f}",
            f"  ELA Forensics   : {r.ela_score:.4f}",
            f"  Face Geometry   : {r.face_score:.4f}",
            f"  Noise Pattern   : {r.noise_score:.4f}",
            f"  MesoNet (NN)    : {'N/A' if r.mesonet_score < 0 else f'{r.mesonet_score:.4f}'}",
            "",
            "  INTERPRETATION",
        ]
        interp = {
            "REAL": [
                "  No significant deepfake artifacts detected.",
                "  Heuristic methods find this media consistent with",
                "  authentic camera-captured content.",
            ],
            "SUSPICIOUS": [
                "  Anomalies detected that warrant closer inspection.",
                "  Could indicate low-quality deepfake, heavy editing,",
                "  or artistic filters. Manual review recommended.",
            ],
            "DEEPFAKE": [
                "  Multiple deepfake indicators detected.",
                "  High probability of synthetic or manipulated content.",
                "  Cross-verify with additional tools and human judgment.",
            ],
        }
        lines += interp.get(r.label, ["  —"])
        lines += [
            "",
            "  ⚠ FOR EDUCATIONAL AND RESEARCH PURPOSES ONLY",
            "  Heuristic detection is not 100% reliable.",
            "══════════════════════════════════════════════════════════",
        ]
        return "\n".join(lines)

    def _show_export_menu(self):
        if not self._last_result:
            return
        menu = QMenu(self)
        act_pdf  = QAction("📄  Rich PDF Report", self)
        act_html = QAction("🌐  Rich HTML Report", self)
        act_txt  = QAction("📝  Plain Text Report", self)
        act_pdf.triggered.connect(lambda: self._export("pdf"))
        act_html.triggered.connect(lambda: self._export("html"))
        act_txt.triggered.connect(lambda: self._export("txt"))
        menu.addAction(act_pdf)
        menu.addAction(act_html)
        menu.addSeparator()
        menu.addAction(act_txt)
        menu.exec(self.export_btn.mapToGlobal(self.export_btn.rect().bottomLeft()))

    def _export(self, fmt: str):
        if not self._last_result:
            return
        base = os.path.splitext(os.path.basename(self._current_path or "report"))[0]
        default = f"deepsentinel_{base}.{fmt}"

        if fmt == "txt":
            path, _ = QFileDialog.getSaveFileName(self, "Export Text Report", default, "Text (*.txt)")
            if path:
                with open(path, "w") as f:
                    f.write(self.report_text.toPlainText())
                self.status_msg.emit(f"Text report saved: {os.path.basename(path)}")
            return

        # Build rich report (HTML/PDF)
        html = report_mod.build_html_report(
            self._last_result,
            file_path=self._current_path,
            viz_frames=self._viz_store,
            exif=self._exif_meta,
            exif_flags=self._exif_flags,
            temporal=self._temporal,
            heatmap_bgr=self._heatmap_overlay,
            preview_bgr=self._preview_img,
        )

        if fmt == "html":
            path, _ = QFileDialog.getSaveFileName(self, "Export HTML Report", default, "HTML (*.html)")
            if path:
                report_mod.export_html(html, path)
                self.status_msg.emit(f"HTML report saved: {os.path.basename(path)}")
        elif fmt == "pdf":
            path, _ = QFileDialog.getSaveFileName(self, "Export PDF Report", default, "PDF (*.pdf)")
            if path:
                ok = report_mod.export_pdf(html, path)
                if ok:
                    self.status_msg.emit(f"PDF report saved: {os.path.basename(path)}")
                else:
                    # Fallback to HTML
                    alt = os.path.splitext(path)[0] + ".html"
                    report_mod.export_html(html, alt)
                    self.status_msg.emit(f"PDF failed — saved HTML instead: {os.path.basename(alt)}")
