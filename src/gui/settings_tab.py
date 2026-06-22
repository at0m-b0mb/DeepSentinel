"""Settings & configuration tab."""

import os
import sys
import subprocess
import webbrowser

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QCheckBox, QSlider, QLineEdit, QFrame, QFileDialog,
    QComboBox, QTextEdit, QProgressBar,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from .theme import (
    CYAN, TEXT_MID as TEXT_SECONDARY, TEXT_DIM, GREEN, RED, AMBER as ORANGE,
    BG_CARD, BG_VOID, BORDER_HI as BORDER_ACCENT, BORDER_MID, FONT_MONO,
)
from ..detection.detector import DeepfakeDetector
from ..detection.mesonet import TORCH_AVAILABLE


# ── Background pip-install worker ──────────────────────────────────────────────

class InstallWorker(QThread):
    """Runs a pip install in a subprocess and streams its output line-by-line."""
    line     = pyqtSignal(str)
    finished_ok = pyqtSignal(bool)   # success?

    def __init__(self, packages: list[str]):
        super().__init__()
        self.packages = packages

    def run(self):
        cmd = [sys.executable, "-u", "-m", "pip", "install", "--upgrade", *self.packages]
        self.line.emit(f"$ {' '.join(cmd)}\n")
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            for ln in iter(proc.stdout.readline, ""):
                if ln:
                    self.line.emit(ln.rstrip("\n"))
            proc.wait()
            self.finished_ok.emit(proc.returncode == 0)
        except Exception as e:
            self.line.emit(f"ERROR: {e}")
            self.finished_ok.emit(False)


class SettingsTab(QWidget):
    status_msg = pyqtSignal(str)

    def __init__(self, detector: DeepfakeDetector, parent=None):
        super().__init__(parent)
        self.detector = detector
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        hdr = QLabel("SETTINGS & CONFIGURATION")
        hdr.setObjectName("sectionHeader")
        root.addWidget(hdr)

        row = QHBoxLayout()
        row.setSpacing(18)
        row.addWidget(self._build_detection_group(), 1)
        row.addWidget(self._build_model_group(), 1)
        root.addLayout(row)
        root.addWidget(self._build_camera_group())
        root.addWidget(self._build_about_group())
        root.addStretch()

    def _build_detection_group(self) -> QGroupBox:
        grp = QGroupBox("Detection Methods")
        layout = QVBoxLayout(grp)
        layout.setSpacing(10)

        self.chk_fft = self._method_toggle("FFT Frequency Analysis", True)
        self.chk_ela = self._method_toggle("ELA (Static images only)", True)
        self.chk_face = self._method_toggle("Face Geometry Analysis", True)
        self.chk_noise = self._method_toggle("SRM Noise Analysis", True)
        self.chk_meso = self._method_toggle("MesoNet Neural Network", True)

        for chk in [self.chk_fft, self.chk_ela, self.chk_face, self.chk_noise, self.chk_meso]:
            layout.addWidget(chk)

        self.chk_fft.toggled.connect(lambda v: setattr(self.detector, 'use_fft', v))
        self.chk_ela.toggled.connect(lambda v: setattr(self.detector, 'use_ela', v))
        self.chk_face.toggled.connect(lambda v: setattr(self.detector, 'use_face', v))
        self.chk_noise.toggled.connect(lambda v: setattr(self.detector, 'use_noise', v))
        self.chk_meso.toggled.connect(lambda v: setattr(self.detector, 'use_mesonet', v))

        layout.addSpacing(8)

        # Threshold slider
        thr_lbl = QLabel("Detection Threshold (deepfake)")
        thr_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(thr_lbl)

        thr_row = QHBoxLayout()
        self.thr_slider = QSlider(Qt.Orientation.Horizontal)
        self.thr_slider.setRange(30, 90)
        self.thr_slider.setValue(65)
        self.thr_val = QLabel("0.65")
        self.thr_val.setStyleSheet(f"color: {CYAN}; font-family: monospace; font-size: 12px; min-width: 35px;")
        self.thr_slider.valueChanged.connect(
            lambda v: self.thr_val.setText(f"{v/100:.2f}")
        )
        thr_row.addWidget(self.thr_slider)
        thr_row.addWidget(self.thr_val)
        layout.addLayout(thr_row)

        return grp

    def _build_model_group(self) -> QGroupBox:
        grp = QGroupBox("MesoNet Neural Network")
        layout = QVBoxLayout(grp)
        layout.setSpacing(10)

        # PyTorch status row with a coloured dot
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self.torch_lbl = QLabel(
            f"PyTorch  ·  {'Installed ✓' if TORCH_AVAILABLE else 'Not installed'}"
        )
        self.torch_lbl.setStyleSheet(
            f"color: {GREEN if TORCH_AVAILABLE else ORANGE}; font-size: 13px; font-weight: 700;"
        )
        status_row.addWidget(self.torch_lbl)
        status_row.addStretch()
        layout.addLayout(status_row)

        if not TORCH_AVAILABLE:
            hint = QLabel("One click installs the neural-network engine (PyTorch + torchvision).")
            hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
            hint.setWordWrap(True)
            layout.addWidget(hint)

            self.install_btn = QPushButton("⬇  Install PyTorch (one-click)")
            self.install_btn.setObjectName("primaryBtn")
            self.install_btn.setFixedHeight(40)
            self.install_btn.clicked.connect(self._install_pytorch)
            layout.addWidget(self.install_btn)

            self.install_prog = QProgressBar()
            self.install_prog.setRange(0, 0)   # indeterminate while running
            self.install_prog.setFixedHeight(5)
            self.install_prog.setTextVisible(False)
            self.install_prog.setVisible(False)
            layout.addWidget(self.install_prog)

            self.install_log = QTextEdit()
            self.install_log.setReadOnly(True)
            self.install_log.setFixedHeight(120)
            self.install_log.setVisible(False)
            self.install_log.setStyleSheet(
                f"background: {BG_VOID}; border: 1px solid {BORDER_MID}; border-radius: 10px; "
                f"color: {TEXT_SECONDARY}; font-family: {FONT_MONO}; font-size: 10px; padding: 8px;"
            )
            layout.addWidget(self.install_log)
        else:
            meso_lbl = QLabel(f"Engine status:  {self.detector.mesonet.status}")
            meso_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
            layout.addWidget(meso_lbl)

        # Weights row
        weights_lbl = QLabel("Pretrained weights (.pth):")
        weights_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(weights_lbl)

        weights_row = QHBoxLayout()
        self.weights_path = QLineEdit()
        self.weights_path.setPlaceholderText("No weights loaded — Browse or Get weights")
        self.weights_path.setReadOnly(True)
        weights_row.addWidget(self.weights_path)

        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(78)
        browse_btn.clicked.connect(self._load_weights)
        weights_row.addWidget(browse_btn)

        get_btn = QPushButton("Get weights ↗")
        get_btn.setObjectName("ghostBtn")
        get_btn.setFixedWidth(110)
        get_btn.setToolTip("Open the MesoNet repository to download pretrained weights")
        get_btn.clicked.connect(lambda: webbrowser.open("https://github.com/DariusAf/MesoNet"))
        weights_row.addWidget(get_btn)
        layout.addLayout(weights_row)

        return grp

    # ── One-click PyTorch install ─────────────────────────────────────────────
    def _install_pytorch(self):
        if getattr(self, "_install_worker", None) and self._install_worker.isRunning():
            return
        self.install_btn.setEnabled(False)
        self.install_btn.setText("Installing…  this can take a few minutes")
        self.install_prog.setVisible(True)
        self.install_log.setVisible(True)
        self.install_log.clear()
        self.status_msg.emit("Installing PyTorch — see the log in Settings…")

        self._install_worker = InstallWorker(["torch", "torchvision"])
        self._install_worker.line.connect(self._on_install_line)
        self._install_worker.finished_ok.connect(self._on_install_done)
        self._install_worker.start()

    def _on_install_line(self, text: str):
        self.install_log.append(text)
        sb = self.install_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_install_done(self, ok: bool):
        self.install_prog.setVisible(False)
        self.install_btn.setEnabled(True)
        if ok:
            self.torch_lbl.setText("PyTorch  ·  Installed ✓  (restart to enable)")
            self.torch_lbl.setStyleSheet(f"color: {GREEN}; font-size: 13px; font-weight: 700;")
            self.install_btn.setText("✓  Installed — restart DeepSentinel to enable")
            self.install_btn.setObjectName("ghostBtn")
            self.install_btn.setStyle(self.install_btn.style())
            self.status_msg.emit("PyTorch installed — restart DeepSentinel to enable MesoNet.")
        else:
            self.install_btn.setText("⬇  Retry install")
            self.status_msg.emit("PyTorch install failed — see the log in Settings.")

    def _build_camera_group(self) -> QGroupBox:
        grp = QGroupBox("Camera Settings")
        layout = QHBoxLayout(grp)
        layout.setSpacing(20)

        cam_lbl = QLabel("Camera Index:")
        cam_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(cam_lbl)

        self.cam_combo = QComboBox()
        self.cam_combo.addItems(["0 (Default)", "1", "2", "3"])
        layout.addWidget(self.cam_combo)

        layout.addStretch()

        quality_lbl = QLabel("Live Analysis Quality:")
        quality_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(quality_lbl)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Fast (every 3 frames)", "Balanced (every 5 frames)", "Thorough (every 10 frames)"])
        self.quality_combo.setCurrentIndex(1)
        layout.addWidget(self.quality_combo)

        return grp

    def _build_about_group(self) -> QGroupBox:
        grp = QGroupBox("About DeepSentinel")
        layout = QVBoxLayout(grp)

        about = QTextEdit()
        about.setReadOnly(True)
        about.setFixedHeight(130)
        about.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
        about.setPlainText(
            "DeepSentinel v1.0.0\n"
            "AI-Powered Deepfake Detection & Education Platform\n\n"
            "Detection methods: FFT Analysis · Error Level Analysis · Face Geometry · "
            "SRM Noise Analysis · MesoNet (optional)\n\n"
            "⚠  FOR EDUCATIONAL AND RESEARCH PURPOSES ONLY.\n"
            "This tool is designed for:\n"
            "  • Security research and deepfake detection R&D\n"
            "  • Journalism fact-checking and media verification\n"
            "  • Education about synthetic media risks\n"
            "  • Understanding AI-generated content\n\n"
            "Creating non-consensual deepfakes is illegal in many jurisdictions.\n"
            "Misuse of deepfake technology may constitute fraud, defamation,\n"
            "or harassment. Always use responsibly and ethically.\n\n"
            "Detection accuracy is heuristic-based and not 100% reliable.\n"
            "Always corroborate findings with additional verification methods.\n\n"
            "Repository: github.com/at0m-b0mb/DeepSentinel"
        )
        layout.addWidget(about)

        return grp

    def _method_toggle(self, label: str, default: bool) -> QCheckBox:
        chk = QCheckBox(label)
        chk.setChecked(default)
        return chk

    def _load_weights(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load MesoNet Weights", "", "PyTorch weights (*.pth *.pt)"
        )
        if path:
            self.weights_path.setText(path)
            ok = self.detector.mesonet._load_weights(path)
            if ok:
                self.status_msg.emit(f"MesoNet weights loaded: {os.path.basename(path)}")
            else:
                self.status_msg.emit("Failed to load weights — check file format.")
