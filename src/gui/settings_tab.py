"""Settings & configuration tab."""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QCheckBox, QSlider, QLineEdit, QFrame, QFileDialog,
    QComboBox, QTextEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal

from .theme import (
    CYAN, TEXT_MID as TEXT_SECONDARY, GREEN, RED, AMBER as ORANGE,
    BG_CARD, BORDER_HI as BORDER_ACCENT,
)
from ..detection.detector import DeepfakeDetector
from ..detection.mesonet import TORCH_AVAILABLE


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

        # PyTorch status
        torch_lbl = QLabel(
            f"PyTorch: {'✓ Available' if TORCH_AVAILABLE else '✗ Not installed'}"
        )
        torch_lbl.setStyleSheet(
            f"color: {GREEN if TORCH_AVAILABLE else RED}; font-size: 12px;"
        )
        layout.addWidget(torch_lbl)

        if not TORCH_AVAILABLE:
            install_note = QLabel(
                "Install: pip install torch torchvision\n"
                "Then restart DeepSentinel."
            )
            install_note.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
            layout.addWidget(install_note)
        else:
            meso_lbl = QLabel(f"Status: {self.detector.mesonet.status}")
            meso_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
            layout.addWidget(meso_lbl)

        weights_lbl = QLabel("Weights file (.pth):")
        weights_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(weights_lbl)

        weights_row = QHBoxLayout()
        self.weights_path = QLineEdit()
        self.weights_path.setPlaceholderText("No weights loaded")
        self.weights_path.setReadOnly(True)
        weights_row.addWidget(self.weights_path)

        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._load_weights)
        weights_row.addWidget(browse_btn)
        layout.addLayout(weights_row)

        note = QLabel(
            "Download pretrained weights from:\n"
            "github.com/DariusAf/MesoNet"
        )
        note.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(note)

        return grp

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
