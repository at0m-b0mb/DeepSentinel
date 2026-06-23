"""Face-Swap Lab tab — the RED-TEAM side: create a deepfake, then detect it.

FOR EDUCATIONAL USE ONLY. Demonstrates how a face-swap deepfake is made so its
artifacts can be studied and caught by the detector (the create → detect loop).
"""

import os
import tempfile
import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QFrame, QFileDialog, QSizePolicy, QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

from .theme import (
    CYAN, CYAN_DIM, GREEN, RED, RED_DIM, AMBER, PURPLE, TEXT_MID, TEXT_LO,
    TEXT_DIM, BG_CARD, BG_CARD2, BG_VOID, BORDER_MID, TEXT_HI, rgba,
)
from .widgets import glow_effect
from ..detection.faceswap import (
    create_deepfake_image, create_deepfake_video, VIDEO_EXTS,
)

IMG_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff'}


# ── Worker ────────────────────────────────────────────────────────────────────

class SwapWorker(QThread):
    progress = pyqtSignal(int, str)
    preview  = pyqtSignal(np.ndarray)
    done     = pyqtSignal(bool, str, bool)   # success, path_or_error, is_video

    def __init__(self, src_path: str, target_path: str, out_path: str):
        super().__init__()
        self.src_path = src_path
        self.target_path = target_path
        self.out_path = out_path

    def run(self):
        ext = os.path.splitext(self.target_path)[1].lower()
        is_video = ext in VIDEO_EXTS
        if is_video:
            ok, res = create_deepfake_video(
                self.src_path, self.target_path, self.out_path,
                progress_cb=lambda p, m: self.progress.emit(p, m),
                preview_cb=lambda fr: self.preview.emit(fr),
            )
        else:
            self.progress.emit(40, "Swapping face…")
            ok, res = create_deepfake_image(self.src_path, self.target_path, self.out_path)
            if ok:
                img = cv2.imread(res)
                if img is not None:
                    self.preview.emit(img)
        self.progress.emit(100, "Done")
        self.done.emit(ok, res, is_video)


# ── Pickers ───────────────────────────────────────────────────────────────────

class MediaPicker(QFrame):
    picked = pyqtSignal(str)

    def __init__(self, number: str, title: str, subtitle: str, accept_video: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("card2")
        self.accept_video = accept_video
        self._path = None
        self.setAcceptDrops(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 14)
        lay.setSpacing(8)

        hdr = QHBoxLayout()
        num = QLabel(number)
        num.setStyleSheet(
            f"color: {CYAN}; background: {rgba(CYAN, 0.12)}; border-radius: 11px; "
            f"font-size: 12px; font-weight: 900; min-width: 22px; max-width: 22px; "
            f"min-height: 22px; max-height: 22px;"
        )
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.addWidget(num)
        tcol = QVBoxLayout(); tcol.setSpacing(0)
        t = QLabel(title); t.setStyleSheet(f"color: {TEXT_HI}; font-size: 13px; font-weight: 700;")
        s = QLabel(subtitle); s.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        tcol.addWidget(t); tcol.addWidget(s)
        hdr.addLayout(tcol)
        hdr.addStretch()
        lay.addLayout(hdr)

        self.thumb = QLabel()
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setFixedHeight(150)
        self.thumb.setStyleSheet(
            f"background: {BG_VOID}; border: 1px dashed {BORDER_MID}; border-radius: 10px; color: {TEXT_DIM};"
        )
        self.thumb.setText("Drop here  ·  or Browse")
        lay.addWidget(self.thumb)

        browse = QPushButton("📂  Browse")
        browse.setObjectName("ghostBtn")
        browse.setFixedHeight(32)
        browse.clicked.connect(self._browse)
        lay.addWidget(browse)

    def _filter(self):
        if self.accept_video:
            return "Images & Videos (*.png *.jpg *.jpeg *.bmp *.webp *.mp4 *.mov *.avi *.mkv)"
        return "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tiff)"

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select file", "", self._filter())
        if path:
            self.set_path(path)

    def set_path(self, path: str):
        ext = os.path.splitext(path)[1].lower()
        if not self.accept_video and ext in VIDEO_EXTS:
            return
        self._path = path
        self._show_thumb(path)
        self.picked.emit(path)

    def _show_thumb(self, path: str):
        ext = os.path.splitext(path)[1].lower()
        img = None
        if ext in VIDEO_EXTS:
            cap = cv2.VideoCapture(path)
            ok, fr = cap.read(); cap.release()
            if ok:
                img = fr
        else:
            img = cv2.imread(path)
        if img is not None:
            h, w = img.shape[:2]
            qt = QImage(img.data, w, h, w * 3, QImage.Format.Format_BGR888)
            pix = QPixmap.fromImage(qt.copy()).scaled(
                self.thumb.width() - 6, self.thumb.height() - 6,
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.thumb.setPixmap(pix)
            tag = "  🎬 video" if ext in VIDEO_EXTS else ""
            self.thumb.setToolTip(os.path.basename(path) + tag)
        else:
            self.thumb.setText("Preview unavailable")

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            self.set_path(urls[0].toLocalFile())


# ── Tab ───────────────────────────────────────────────────────────────────────

class CreateTab(QWidget):
    status_msg      = pyqtSignal(str)
    detect_requested = pyqtSignal(str)   # output path → send to Analyze tab

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: SwapWorker | None = None
        self._src_path = None
        self._target_path = None
        self._output_path = None
        self._output_is_video = False
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)

        # Ethics banner
        banner = QFrame()
        banner.setObjectName("card")
        banner.setStyleSheet(
            f"#card {{ background: {rgba(RED, 0.07)}; border: 1px solid {rgba(RED, 0.35)}; border-radius: 14px; }}"
        )
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(16, 12, 16, 12)
        icon = QLabel("⚠")
        icon.setStyleSheet(f"color: {RED}; font-size: 22px; font-weight: 900;")
        bl.addWidget(icon)
        txt = QLabel(
            "<b style='color:#fb7185'>Red-Team Lab — Educational Use Only.</b>  "
            "<span style='color:#94a3b8'>This builds a face-swap to study how deepfakes are made and detected. "
            "Creating a deepfake of a real person <b>without consent is illegal</b> in many places. "
            "Use only with consenting subjects or your own footage.</span>"
        )
        txt.setWordWrap(True)
        txt.setTextFormat(Qt.TextFormat.RichText)
        bl.addWidget(txt, 1)
        root.addWidget(banner)

        # Main columns
        cols = QHBoxLayout()
        cols.setSpacing(16)
        cols.addWidget(self._inputs_panel(), 2)
        cols.addWidget(self._result_panel(), 3)
        root.addLayout(cols, 1)

    def _inputs_panel(self) -> QFrame:
        panel = QFrame(); panel.setObjectName("card")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        hdr = QLabel("BUILD A DEEPFAKE")
        hdr.setObjectName("sectionHeader")
        lay.addWidget(hdr)

        self.src_picker = MediaPicker("1", "Source Face", "The identity to paste (a clear face photo)", False)
        self.src_picker.picked.connect(self._on_src)
        lay.addWidget(self.src_picker)

        self.tgt_picker = MediaPicker("2", "Target", "Photo or video to swap the face into", True)
        self.tgt_picker.picked.connect(self._on_tgt)
        lay.addWidget(self.tgt_picker)

        self.generate_btn = QPushButton("⚡  Generate Deepfake")
        self.generate_btn.setObjectName("primaryBtn")
        self.generate_btn.setFixedHeight(44)
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self._generate)
        lay.addWidget(self.generate_btn)

        self.prog = QProgressBar()
        self.prog.setRange(0, 100); self.prog.setFixedHeight(6)
        self.prog.setTextVisible(False); self.prog.setVisible(False)
        lay.addWidget(self.prog)
        self.prog_lbl = QLabel(); self.prog_lbl.setVisible(False)
        self.prog_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; font-family: monospace;")
        lay.addWidget(self.prog_lbl)

        lay.addStretch()
        return panel

    def _result_panel(self) -> QFrame:
        panel = QFrame(); panel.setObjectName("card")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        hdr = QLabel("RESULT  ·  DEEPFAKE OUTPUT")
        hdr.setObjectName("sectionHeader")
        lay.addWidget(hdr)

        self.result_lbl = QLabel()
        self.result_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.result_lbl.setMinimumHeight(320)
        self.result_lbl.setStyleSheet(
            f"background: {BG_VOID}; border: 1px solid {BORDER_MID}; border-radius: 12px; color: {TEXT_DIM};"
        )
        self.result_lbl.setText("Your generated deepfake will appear here.\nLoad a source face + target, then Generate.")
        lay.addWidget(self.result_lbl, 1)

        # Action buttons
        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.detect_btn = QPushButton("🔍  Detect this Deepfake →")
        self.detect_btn.setObjectName("primaryBtn")
        self.detect_btn.setFixedHeight(40)
        self.detect_btn.setEnabled(False)
        self.detect_btn.setToolTip("Send the generated file to the Analyze tab and run detection")
        self.detect_btn.clicked.connect(self._send_to_detect)
        actions.addWidget(self.detect_btn, 2)

        self.save_btn = QPushButton("💾  Save")
        self.save_btn.setFixedHeight(40)
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save)
        actions.addWidget(self.save_btn, 1)
        lay.addLayout(actions)

        hint = QLabel("ℹ  The swap leaves blending & boundary artifacts — exactly what the detector looks for.")
        hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)
        return panel

    # ── Logic ─────────────────────────────────────────────────────────────────
    def _on_src(self, path):
        self._src_path = path
        self._refresh_generate()

    def _on_tgt(self, path):
        self._target_path = path
        self._refresh_generate()

    def _refresh_generate(self):
        self.generate_btn.setEnabled(bool(self._src_path and self._target_path))

    def _generate(self):
        if not (self._src_path and self._target_path):
            return
        if self.worker and self.worker.isRunning():
            return
        ext = os.path.splitext(self._target_path)[1].lower()
        is_video = ext in VIDEO_EXTS
        suffix = ".mp4" if is_video else ".png"
        out = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        out.close()
        self._output_path = out.name

        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("⚙  Generating…")
        self.detect_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.prog.setVisible(True); self.prog.setValue(0)
        self.prog_lbl.setVisible(True)
        self.result_lbl.setText("Generating deepfake…\n(faces are detected & aligned per frame)")

        self.worker = SwapWorker(self._src_path, self._target_path, self._output_path)
        self.worker.progress.connect(self._on_progress)
        self.worker.preview.connect(self._show_result_frame)
        self.worker.done.connect(self._on_done)
        self.worker.start()
        self.status_msg.emit("Generating deepfake…")

    def _on_progress(self, pct, msg):
        self.prog.setValue(pct)
        self.prog_lbl.setText(msg)

    def _show_result_frame(self, frame: np.ndarray):
        h, w = frame.shape[:2]
        qt = QImage(frame.data, w, h, w * 3, QImage.Format.Format_BGR888)
        pix = QPixmap.fromImage(qt.copy()).scaled(
            max(self.result_lbl.width(), 320), max(self.result_lbl.height(), 300),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.result_lbl.setPixmap(pix)

    def _on_done(self, ok: bool, res: str, is_video: bool):
        self.prog.setVisible(False); self.prog_lbl.setVisible(False)
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("⚡  Generate Deepfake")
        if ok:
            self._output_path = res
            self._output_is_video = is_video
            self.detect_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            kind = "video" if is_video else "image"
            self.status_msg.emit(f"Deepfake {kind} created — try 'Detect this' to catch it")
        else:
            self.result_lbl.setText(f"⚠  {res}")
            self.status_msg.emit(f"Generation failed: {res}")

    def _send_to_detect(self):
        if self._output_path and os.path.exists(self._output_path):
            self.detect_requested.emit(self._output_path)
            self.status_msg.emit("Sent to Analyze — running detection…")

    def _save(self):
        if not self._output_path:
            return
        ext = ".mp4" if self._output_is_video else ".png"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Deepfake", f"deepfake_output{ext}",
            f"Media (*{ext})")
        if path:
            import shutil
            shutil.copy(self._output_path, path)
            self.status_msg.emit(f"Saved: {os.path.basename(path)}")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.wait(2000)
        super().closeEvent(event)
