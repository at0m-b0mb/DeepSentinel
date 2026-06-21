"""Batch folder analysis tab — analyze every media file in a folder at once."""

import os
import csv
import datetime
import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QFrame, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QSizePolicy, QCheckBox, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from .theme import (
    CYAN, GREEN, RED, AMBER, PURPLE, TEXT_MID, TEXT_LO, TEXT_DIM,
    BG_CARD, BG_CARD2, BG_VOID, BORDER_MID, TEXT_HI, BG_HOVER,
)
from .widgets import StatCard, glow_effect
from ..detection.detector import DeepfakeDetector


IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff', '.tif'}
VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}


# ── Worker ────────────────────────────────────────────────────────────────────

class BatchWorker(QThread):
    progress   = pyqtSignal(int, int, str)        # current, total, filename
    row_ready  = pyqtSignal(dict)                  # one result
    finished_all = pyqtSignal()

    def __init__(self, detector: DeepfakeDetector, files: list[str], recursive: bool):
        super().__init__()
        self.detector = detector
        self.files = files
        self._running = True

    def run(self):
        total = len(self.files)
        for i, path in enumerate(self.files):
            if not self._running:
                break
            self.progress.emit(i + 1, total, os.path.basename(path))
            try:
                row = self._analyze_one(path)
            except Exception as e:
                row = {"path": path, "name": os.path.basename(path),
                       "type": "?", "verdict": "ERROR", "score": 0.0,
                       "faces": 0, "methods": 0, "note": str(e)[:40]}
            self.row_ready.emit(row)
        self.finished_all.emit()

    def _analyze_one(self, path: str) -> dict:
        ext = os.path.splitext(path)[1].lower()
        if ext in VIDEO_EXTS:
            return self._analyze_video(path)
        return self._analyze_image(path)

    def _analyze_image(self, path: str) -> dict:
        img = cv2.imread(path)
        if img is None:
            raise ValueError("unreadable")
        self.detector.use_ela = True
        r = self.detector.analyze(img, fast=False)
        self.detector.use_ela = False
        return {"path": path, "name": os.path.basename(path), "type": "IMG",
                "verdict": r.label, "score": r.overall_score,
                "faces": r.faces_found, "methods": r.methods_used, "note": ""}

    def _analyze_video(self, path: str) -> dict:
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise ValueError("unreadable")
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        step = max(1, total // 12)
        scores, faces, fi = [], 0, 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if fi % step == 0:
                small = cv2.resize(frame, (320, 240))
                r = self.detector.analyze(small, fast=True)
                scores.append(r.overall_score)
                faces = max(faces, r.faces_found)
            fi += 1
        cap.release()
        if not scores:
            raise ValueError("no frames")
        combined = float(0.6 * np.mean(scores) + 0.4 * np.max(scores))
        label = ("DEEPFAKE" if combined >= 0.65 else
                 "SUSPICIOUS" if combined >= 0.40 else "REAL")
        return {"path": path, "name": os.path.basename(path), "type": "VID",
                "verdict": label, "score": combined,
                "faces": faces, "methods": 3, "note": f"{len(scores)} frames"}

    def stop(self):
        self._running = False


# ── Tab ───────────────────────────────────────────────────────────────────────

class BatchTab(QWidget):
    status_msg    = pyqtSignal(str)
    analysis_done = pyqtSignal(str, str, float)

    def __init__(self, detector: DeepfakeDetector, parent=None):
        super().__init__(parent)
        self.detector = detector
        self.worker: BatchWorker | None = None
        self._results: list[dict] = []
        self._folder: str | None = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("BATCH FOLDER ANALYSIS")
        title.setObjectName("sectionHeader")
        hdr.addWidget(title)
        hdr.addStretch()
        self.recursive_chk = QCheckBox("Include subfolders")
        self.recursive_chk.setChecked(True)
        hdr.addWidget(self.recursive_chk)
        root.addLayout(hdr)

        # Folder selection row
        sel_card = QFrame(); sel_card.setObjectName("card")
        sel_l = QHBoxLayout(sel_card)
        sel_l.setContentsMargins(14, 12, 14, 12)
        sel_l.setSpacing(10)

        self.folder_lbl = QLabel("No folder selected — choose a folder of images/videos to scan")
        self.folder_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; font-family: monospace;")
        sel_l.addWidget(self.folder_lbl, 1)

        self.browse_btn = QPushButton("📁  Choose Folder")
        self.browse_btn.setObjectName("ghostBtn")
        self.browse_btn.setFixedHeight(36)
        self.browse_btn.clicked.connect(self._choose_folder)
        sel_l.addWidget(self.browse_btn)

        self.scan_btn = QPushButton("▶  Scan")
        self.scan_btn.setObjectName("primaryBtn")
        self.scan_btn.setFixedHeight(36)
        self.scan_btn.setFixedWidth(110)
        self.scan_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self._toggle_scan)
        sel_l.addWidget(self.scan_btn)

        self.export_btn = QPushButton("⬇  Export CSV")
        self.export_btn.setFixedHeight(36)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export_csv)
        sel_l.addWidget(self.export_btn)
        root.addWidget(sel_card)

        # Stat cards
        cards = QHBoxLayout(); cards.setSpacing(12)
        self.card_total = StatCard("📊", "0", "Files", CYAN)
        self.card_fake  = StatCard("⚠", "0", "Deepfakes", RED)
        self.card_susp  = StatCard("🔶", "0", "Suspicious", AMBER)
        self.card_real  = StatCard("✓", "0", "Real", GREEN)
        for c in [self.card_total, self.card_fake, self.card_susp, self.card_real]:
            c.setMinimumHeight(78)
            c.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cards.addWidget(c)
        root.addLayout(cards)

        # Progress
        self.prog = QProgressBar()
        self.prog.setRange(0, 100)
        self.prog.setFixedHeight(6)
        self.prog.setTextVisible(False)
        self.prog.setVisible(False)
        root.addWidget(self.prog)

        # Results table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["File", "Type", "Verdict", "Score", "Faces", "Detail"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in (1, 2, 3, 4, 5):
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: {BG_CARD}; border: 1px solid {BORDER_MID};
                border-radius: 10px; gridline-color: {BORDER_MID};
                color: {TEXT_MID}; font-size: 12px;
            }}
            QTableWidget::item {{ padding: 5px 8px; }}
            QTableWidget::item:selected {{ background: {BG_HOVER}; color: {TEXT_HI}; }}
            QHeaderView::section {{
                background: {BG_CARD2}; color: {TEXT_LO}; border: none;
                border-bottom: 1px solid {BORDER_MID}; padding: 8px;
                font-size: 10px; font-weight: 700; letter-spacing: 1px;
            }}
        """)
        root.addWidget(self.table, 1)

        # Footer note
        note = QLabel("⚠  Heuristic batch screening — review flagged files manually. For educational use only.")
        note.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(note)

    # ── Folder + scan control ─────────────────────────────────────────────────
    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose Folder to Scan")
        if folder:
            self._folder = folder
            self.folder_lbl.setText(folder)
            self.folder_lbl.setStyleSheet(f"color: {TEXT_MID}; font-size: 12px; font-family: monospace;")
            self.scan_btn.setEnabled(True)

    def _gather_files(self) -> list[str]:
        files = []
        recursive = self.recursive_chk.isChecked()
        exts = IMAGE_EXTS | VIDEO_EXTS
        if recursive:
            for r, _, fs in os.walk(self._folder):
                for f in fs:
                    if os.path.splitext(f)[1].lower() in exts:
                        files.append(os.path.join(r, f))
        else:
            for f in os.listdir(self._folder):
                fp = os.path.join(self._folder, f)
                if os.path.isfile(fp) and os.path.splitext(f)[1].lower() in exts:
                    files.append(fp)
        return sorted(files)

    def _toggle_scan(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.scan_btn.setText("▶  Scan")
            return
        files = self._gather_files()
        if not files:
            self.status_msg.emit("No image/video files found in folder.")
            self.folder_lbl.setText(f"{self._folder}  —  no media files found")
            return

        # Reset
        self._results.clear()
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        self._refresh_stats()
        self.prog.setVisible(True)
        self.prog.setValue(0)
        self.scan_btn.setText("■  Stop")
        self.scan_btn.setObjectName("dangerBtn")
        self.scan_btn.setStyle(self.scan_btn.style())
        self.export_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)

        self.worker = BatchWorker(self.detector, files, self.recursive_chk.isChecked())
        self.worker.progress.connect(self._on_progress)
        self.worker.row_ready.connect(self._on_row)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.start()
        self.status_msg.emit(f"Scanning {len(files)} files…")

    def _on_progress(self, cur: int, total: int, name: str):
        self.prog.setValue(int(cur / total * 100))
        self.status_msg.emit(f"[{cur}/{total}] {name}")

    def _on_row(self, row: dict):
        self._results.append(row)
        self._append_table_row(row)
        self._refresh_stats()
        if row["verdict"] not in ("ERROR",):
            self.analysis_done.emit(row["path"], row["verdict"], row["score"])

    def _on_finished(self):
        self.prog.setVisible(False)
        self.scan_btn.setText("▶  Scan")
        self.scan_btn.setObjectName("primaryBtn")
        self.scan_btn.setStyle(self.scan_btn.style())
        self.browse_btn.setEnabled(True)
        self.export_btn.setEnabled(len(self._results) > 0)
        self.table.setSortingEnabled(True)
        self.status_msg.emit(f"Batch complete — {len(self._results)} files analyzed")

    # ── Table ─────────────────────────────────────────────────────────────────
    def _append_table_row(self, row: dict):
        colors = {"REAL": GREEN, "SUSPICIOUS": AMBER, "DEEPFAKE": RED, "ERROR": TEXT_LO}
        color = QColor(colors.get(row["verdict"], TEXT_MID))
        r = self.table.rowCount()
        self.table.insertRow(r)

        name_item = QTableWidgetItem(row["name"])
        name_item.setToolTip(row["path"])

        type_item = QTableWidgetItem(row["type"])
        type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        verdict_item = QTableWidgetItem(row["verdict"])
        verdict_item.setForeground(color)
        verdict_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont(); f.setBold(True); verdict_item.setFont(f)

        score_item = _NumericItem(f"{row['score']*100:.0f}%", row["score"])
        score_item.setForeground(color)
        score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        faces_item = _NumericItem(str(row["faces"]), row["faces"])
        faces_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        detail_item = QTableWidgetItem(row.get("note", ""))
        detail_item.setForeground(QColor(TEXT_DIM))

        for col, item in enumerate([name_item, type_item, verdict_item,
                                    score_item, faces_item, detail_item]):
            self.table.setItem(r, col, item)

    def _refresh_stats(self):
        total = len(self._results)
        fake = sum(1 for r in self._results if r["verdict"] == "DEEPFAKE")
        susp = sum(1 for r in self._results if r["verdict"] == "SUSPICIOUS")
        real = sum(1 for r in self._results if r["verdict"] == "REAL")
        self.card_total.set_value(str(total))
        self.card_fake.set_value(str(fake))
        self.card_susp.set_value(str(susp))
        self.card_real.set_value(str(real))

    # ── CSV export ────────────────────────────────────────────────────────────
    def _export_csv(self):
        if not self._results:
            return
        default = f"deepsentinel_batch_{datetime.datetime.now():%Y%m%d_%H%M}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Export Batch CSV", default, "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["File", "Path", "Type", "Verdict", "Score", "Faces", "Methods", "Detail"])
            for r in self._results:
                w.writerow([r["name"], r["path"], r["type"], r["verdict"],
                            f"{r['score']:.4f}", r["faces"], r.get("methods", ""), r.get("note", "")])
        self.status_msg.emit(f"CSV exported: {os.path.basename(path)}")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
        super().closeEvent(event)


class _NumericItem(QTableWidgetItem):
    """Table item that sorts by an underlying numeric value, not text."""
    def __init__(self, text: str, value: float):
        super().__init__(text)
        self._value = value

    def __lt__(self, other):
        if isinstance(other, _NumericItem):
            return self._value < other._value
        return super().__lt__(other)
