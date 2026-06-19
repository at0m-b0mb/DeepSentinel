"""Live webcam deepfake detection tab — redesigned with arc gauge and history graph."""

import time
import os
import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QFrame, QCheckBox, QGroupBox, QSizePolicy, QFileDialog, QSplitter,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QImage, QPixmap, QFont

from .theme import (
    CYAN, GREEN, RED, AMBER, TEXT_MID, TEXT_LO, TEXT_DIM,
    BG_CARD, BORDER_MID, BG_VOID,
)
from .widgets import ConfidenceDial, HistoryGraph, GlowScoreBar, PulsingDot, glow_effect
from ..detection.detector import DeepfakeDetector, DetectionResult


# ── Camera thread ─────────────────────────────────────────────────────────────

class CameraWorker(QThread):
    frame_ready   = pyqtSignal(np.ndarray, object)
    error         = pyqtSignal(str)
    fps_update    = pyqtSignal(float)

    def __init__(self, detector: DeepfakeDetector, camera_index: int = 0,
                 analyze_every: int = 5):
        super().__init__()
        self.detector = detector
        self.camera_index = camera_index
        self.analyze_every = analyze_every
        self._running = False

    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self.error.emit("Cannot open camera. Allow access in System Settings → Privacy → Camera.")
            return

        self._running = True
        fc = 0
        last_result = None
        fps_t = time.time()
        fps_fc = 0

        while self._running:
            ret, frame = cap.read()
            if not ret:
                self.error.emit("Camera disconnected.")
                break

            fc += 1
            fps_fc += 1

            if fc % self.analyze_every == 0:
                small = cv2.resize(frame, (320, 240))
                last_result = self.detector.analyze(small, fast=True)

            if last_result is not None:
                self.frame_ready.emit(frame, last_result)

            elapsed = time.time() - fps_t
            if elapsed >= 1.0:
                self.fps_update.emit(fps_fc / elapsed)
                fps_fc = 0
                fps_t = time.time()

        cap.release()

    def stop(self):
        self._running = False
        self.wait(3000)


# ── Tab ───────────────────────────────────────────────────────────────────────

class LiveTab(QWidget):
    status_msg      = pyqtSignal(str)
    analysis_done   = pyqtSignal(str, str, float)   # filename, verdict, score
    snapshot_ready  = pyqtSignal(np.ndarray)         # send frame to analyze tab

    def __init__(self, detector: DeepfakeDetector, parent=None):
        super().__init__(parent)
        self.detector = detector
        self.worker: CameraWorker | None = None
        self._last_frame: np.ndarray | None = None
        self._frame_count = 0
        self.detector.use_ela = False  # ELA is too slow for live
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        root.addWidget(self._camera_panel(), 5)
        root.addWidget(self._results_panel(), 3)

    def _camera_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header row
        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        title = QLabel("LIVE CAMERA FEED")
        title.setObjectName("sectionHeader")
        hdr.addWidget(title)

        self._pulse = PulsingDot(GREEN)
        hdr.addWidget(self._pulse)

        self._fps_lbl = QLabel("FPS: —")
        self._fps_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; font-family: monospace;")
        hdr.addWidget(self._fps_lbl)
        hdr.addStretch()

        self._frame_cnt_lbl = QLabel("")
        self._frame_cnt_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; font-family: monospace;")
        hdr.addWidget(self._frame_cnt_lbl)
        layout.addLayout(hdr)

        # Camera view
        self.cam_lbl = QLabel()
        self.cam_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cam_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.cam_lbl.setStyleSheet(
            f"background: {BG_VOID}; border: 1px solid {BORDER_MID}; border-radius: 10px;"
        )
        self.cam_lbl.setText("Camera not started")
        self.cam_lbl.setMinimumHeight(280)
        layout.addWidget(self.cam_lbl, 1)

        # Controls row
        ctrl = QHBoxLayout()
        ctrl.setSpacing(10)

        self.start_btn = QPushButton("▶  Start Detection")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setFixedHeight(42)
        self.start_btn.clicked.connect(self._toggle_camera)
        ctrl.addWidget(self.start_btn, 2)

        self.snap_btn = QPushButton("📷  Snapshot → Analyze")
        self.snap_btn.setObjectName("ghostBtn")
        self.snap_btn.setFixedHeight(42)
        self.snap_btn.setEnabled(False)
        self.snap_btn.setToolTip("Freeze current frame and run full analysis in the Analyze tab")
        self.snap_btn.clicked.connect(self._send_snapshot)
        ctrl.addWidget(self.snap_btn, 2)

        self.save_btn = QPushButton("💾")
        self.save_btn.setObjectName("iconBtn")
        self.save_btn.setFixedSize(42, 42)
        self.save_btn.setEnabled(False)
        self.save_btn.setToolTip("Save current frame to disk")
        self.save_btn.clicked.connect(self._save_frame)
        ctrl.addWidget(self.save_btn)

        layout.addLayout(ctrl)
        return panel

    def _results_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        hdr = QLabel("DETECTION RESULTS")
        hdr.setObjectName("sectionHeader")
        layout.addWidget(hdr)

        # Arc gauge
        self.dial = ConfidenceDial()
        glow_effect(self.dial, CYAN, 16)
        layout.addWidget(self.dial, 0, Qt.AlignmentFlag.AlignHCenter)

        # Verdict label
        self.verdict_lbl = QLabel("AWAITING INPUT")
        self.verdict_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verdict_lbl.setObjectName("verdictLabel")
        self.verdict_lbl.setStyleSheet(f"color: {TEXT_DIM}; letter-spacing: 5px; font-size: 16px; font-weight: 900;")
        layout.addWidget(self.verdict_lbl)

        # Divider
        div = QFrame(); div.setObjectName("divider"); div.setFixedHeight(1)
        layout.addWidget(div)

        # History graph
        graph_hdr = QHBoxLayout()
        gl = QLabel("CONFIDENCE HISTORY")
        gl.setObjectName("sectionHeader")
        graph_hdr.addWidget(gl)
        graph_hdr.addStretch()
        clr = QPushButton("Clear")
        clr.setObjectName("ghostBtn")
        clr.setFixedSize(52, 22)
        clr.clicked.connect(lambda: self.graph.clear())
        graph_hdr.addWidget(clr)
        layout.addLayout(graph_hdr)

        self.graph = HistoryGraph()
        layout.addWidget(self.graph)

        # Divider
        div2 = QFrame(); div2.setObjectName("divider"); div2.setFixedHeight(1)
        layout.addWidget(div2)

        # Method breakdown
        methods_hdr = QLabel("METHOD BREAKDOWN")
        methods_hdr.setObjectName("sectionHeader")
        layout.addWidget(methods_hdr)

        self.bar_fft   = GlowScoreBar("FFT Artifacts")
        self.bar_face  = GlowScoreBar("Face Geometry")
        self.bar_noise = GlowScoreBar("Noise Pattern")
        self.bar_meso  = GlowScoreBar("MesoNet (NN)")
        for b in [self.bar_fft, self.bar_face, self.bar_noise, self.bar_meso]:
            layout.addWidget(b)

        # Frame info row
        info_row = QHBoxLayout()
        self.faces_lbl   = QLabel("Faces: —")
        self.methods_lbl = QLabel("Methods: —")
        for lbl in [self.faces_lbl, self.methods_lbl]:
            lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; font-family: monospace;")
        info_row.addWidget(self.faces_lbl)
        info_row.addStretch()
        info_row.addWidget(self.methods_lbl)
        layout.addLayout(info_row)

        # Toggles
        toggle_group = QGroupBox("Active Methods")
        tg = QVBoxLayout(toggle_group)
        tg.setSpacing(4)
        self.chk_fft   = QCheckBox("FFT Analysis")
        self.chk_face  = QCheckBox("Face Geometry")
        self.chk_noise = QCheckBox("Noise Analysis")
        self.chk_meso  = QCheckBox("MesoNet (NN)")
        for c in [self.chk_fft, self.chk_face, self.chk_noise, self.chk_meso]:
            c.setChecked(True)
            tg.addWidget(c)
        self.chk_fft.toggled.connect(lambda v: setattr(self.detector, 'use_fft', v))
        self.chk_face.toggled.connect(lambda v: setattr(self.detector, 'use_face', v))
        self.chk_noise.toggled.connect(lambda v: setattr(self.detector, 'use_noise', v))
        self.chk_meso.toggled.connect(lambda v: setattr(self.detector, 'use_mesonet', v))
        layout.addWidget(toggle_group)

        return panel

    # ── Camera control ────────────────────────────────────────────────────────
    def _toggle_camera(self):
        if self.worker and self.worker.isRunning():
            self._stop_camera()
        else:
            self._start_camera()

    def _start_camera(self):
        self.graph.clear()
        self.worker = CameraWorker(self.detector)
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.error.connect(self._on_error)
        self.worker.fps_update.connect(lambda f: self._fps_lbl.setText(f"FPS: {f:.1f}"))
        self.worker.start()

        self.start_btn.setText("■  Stop Detection")
        self.start_btn.setObjectName("dangerBtn")
        self.start_btn.setStyle(self.start_btn.style())
        self.snap_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self._pulse.start()
        self.status_msg.emit("Live detection started")

    def _stop_camera(self):
        if self.worker:
            self.worker.stop()
            self.worker = None
        self.start_btn.setText("▶  Start Detection")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setStyle(self.start_btn.style())
        self.snap_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self._pulse.stop()
        self.cam_lbl.setText("Camera stopped")
        self.cam_lbl.setPixmap(QPixmap())
        self._fps_lbl.setText("FPS: —")
        self.dial.reset()
        self.verdict_lbl.setText("AWAITING INPUT")
        self.verdict_lbl.setStyleSheet(f"color: {TEXT_DIM}; letter-spacing: 5px; font-size: 16px; font-weight: 900;")
        self.status_msg.emit("Live detection stopped")

    # ── Frame handling ────────────────────────────────────────────────────────
    def _on_frame(self, frame: np.ndarray, r: DetectionResult):
        self._last_frame = frame
        self._frame_count += 1

        # Display
        display = r.annotated_frame if r.annotated_frame is not None else frame
        h, w, ch = display.shape
        qt_img = QImage(display.data, w, h, ch * w, QImage.Format.Format_BGR888)
        pix = QPixmap.fromImage(qt_img).scaled(
            self.cam_lbl.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.cam_lbl.setPixmap(pix)
        self._frame_cnt_lbl.setText(f"Frame #{self._frame_count}")

        # Update scores
        colors = {"REAL": GREEN, "SUSPICIOUS": AMBER, "DEEPFAKE": RED}
        color = colors.get(r.label, TEXT_MID)

        self.dial.set_value(r.overall_score, r.label)
        self.graph.push(r.overall_score)

        self.verdict_lbl.setText(r.label)
        self.verdict_lbl.setStyleSheet(
            f"color: {color}; letter-spacing: 5px; font-size: 16px; font-weight: 900;"
        )
        self.bar_fft.set_score(r.fft_score)
        self.bar_face.set_score(r.face_score)
        self.bar_noise.set_score(r.noise_score)
        self.bar_meso.set_score(r.mesonet_score)

        self.faces_lbl.setText(f"Faces: {r.faces_found}")
        self.methods_lbl.setText(f"Methods: {r.methods_used}")

    def _on_error(self, msg: str):
        self.cam_lbl.setText(f"⚠  {msg}")
        self.status_msg.emit(f"Camera error: {msg}")
        self._stop_camera()

    def _send_snapshot(self):
        if self._last_frame is not None:
            self.snapshot_ready.emit(self._last_frame.copy())
            self.status_msg.emit("Snapshot sent to Analyze tab — switching…")

    def _save_frame(self):
        if self._last_frame is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Frame", f"deepsentinel_frame_{self._frame_count}.png",
            "Images (*.png *.jpg)"
        )
        if path:
            cv2.imwrite(path, self._last_frame)
            self.status_msg.emit(f"Saved: {os.path.basename(path)}")

    def closeEvent(self, event):
        self._stop_camera()
        super().closeEvent(event)
