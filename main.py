#!/usr/bin/env python3
"""
DeepSentinel — AI-Powered Deepfake Detection & Education Platform
FOR EDUCATIONAL AND RESEARCH PURPOSES ONLY.

Detection methods:
  - FFT frequency artifact analysis
  - Error Level Analysis (ELA)
  - Face geometry & boundary consistency (MediaPipe)
  - SRM noise residual analysis
  - MesoNet neural network (optional, requires PyTorch + pretrained weights)

Usage:
  python main.py
"""

import sys
import os

# Suppress TF/MediaPipe verbose output
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("GLOG_minloglevel", "2")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtGui import QFont


def _check_deps() -> list[str]:
    missing = []
    for pkg, name in [
        ("cv2",         "opencv-python"),
        ("numpy",       "numpy"),
        ("matplotlib",  "matplotlib"),
        ("PIL",         "Pillow"),
        ("PyQt6",       "PyQt6"),
    ]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(name)
    return missing


def main():
    missing = _check_deps()
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        sys.exit(1)

    QCoreApplication.setApplicationName("DeepSentinel")
    QCoreApplication.setApplicationVersion("1.0.0")
    QCoreApplication.setOrganizationName("at0m-b0mb")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Window / dock icon
    from PyQt6.QtGui import QIcon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Apply base font
    font = QFont("SF Pro Display", 13)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(font)

    # Apply stylesheet
    from src.gui.theme import STYLESHEET
    app.setStyleSheet(STYLESHEET)

    from src.gui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
