"""Render real DeepSentinel GUI tabs to PNG screenshots for the README.

Runs offscreen, builds the actual MainWindow, populates each tab with
representative data, and grabs each tab to assets/screenshots/.
"""
import os, sys, time
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap

from src.gui.theme import STYLESHEET

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "screenshots")
os.makedirs(OUT, exist_ok=True)
DEMO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "assets", "demo", "portrait.png")


def settle_dial(dial, value, label):
    dial.set_value(value, label)
    freeze_dial(dial)


def freeze_dial(dial):
    """Snap the animated dial straight to its target (no animation for the grab)."""
    dial._value = dial._target
    if dial._timer.isActive():
        dial._timer.stop()
    dial.update()


def bgr_to_pix(bgr, w, h):
    img = cv2.resize(bgr, (w, h))
    qt = QImage(img.data, w, h, w * 3, QImage.Format.Format_BGR888)
    return QPixmap.fromImage(qt.copy())


def grab(widget, app, name):
    for _ in range(6):
        app.processEvents()
    pix = widget.grab()
    path = os.path.join(OUT, name)
    pix.save(path, "PNG")
    print(f"  saved {name}  ({pix.width()}x{pix.height()})")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")   # match main.py rendering
    app.setStyleSheet(STYLESHEET)

    from src.gui.main_window import MainWindow
    MainWindow._show_disclaimer = lambda self: self._build_ui()
    win = MainWindow()
    win.resize(1320, 880)
    win.show()
    for _ in range(8):
        app.processEvents()

    from src.detection.detector import DeepfakeDetector
    det = win.detector

    portrait = cv2.imread(DEMO)
    if portrait is None:
        portrait = (np.random.rand(480, 640, 3) * 255).astype(np.uint8)

    # ── DASHBOARD ──────────────────────────────────────────────────────────────
    dash = win.dashboard_tab
    samples = [
        ("interview_clip.mp4", "DEEPFAKE", 0.88),
        ("ceo_announcement.jpg", "REAL", 0.09),
        ("viral_video.mp4", "SUSPICIOUS", 0.52),
        ("profile_pic.png", "REAL", 0.14),
        ("news_segment.mp4", "DEEPFAKE", 0.79),
        ("selfie_2024.jpg", "REAL", 0.21),
        ("politician_speech.mp4", "SUSPICIOUS", 0.47),
        ("avatar_render.png", "DEEPFAKE", 0.71),
    ]
    for name, verdict, score in samples:
        dash.record_analysis(name, verdict, score)
    win._goto(0)
    grab(win, app, "dashboard.png")

    # ── LIVE DETECTION ─────────────────────────────────────────────────────────
    live = win.live_tab
    # annotated demo frame using the real full-res overlay path
    from src.gui.live_tab import _draw_live_overlay
    from src.gui.widgets import verdict_view
    from src.detection.face_analyzer import analyze_face
    demo_score = 0.12
    fa = analyze_face(portrait)
    demo_result = type("R", (), {"face_rects": fa.face_rects, "analyzed_wh": (portrait.shape[1], portrait.shape[0]),
                                 "overall_score": demo_score})()
    annotated = _draw_live_overlay(portrait, demo_result)
    live.cam_lbl.setPixmap(bgr_to_pix(annotated, 560, 420))
    live.dial.set_result(demo_score); freeze_dial(live.dial)
    flabel, fconf, fcolor = verdict_view(demo_score)
    live.verdict_lbl.setText(flabel)
    live.verdict_lbl.setStyleSheet(f"color: {fcolor.name()}; letter-spacing: 4px; font-size: 17px; font-weight: 900;")
    import random
    random.seed(3)
    for v in [0.2,0.25,0.31,0.28,0.35,0.3,0.27,0.33,0.29,0.31,0.34,0.3,0.26,0.32,0.31,
              0.29,0.36,0.31,0.28,0.3,0.33,0.31,0.27,0.32,0.3,0.29,0.31,0.34,0.31,0.3]:
        live.graph.push(v)
    live.bar_fft.set_score(0.22); live.bar_face.set_score(0.35)
    live.bar_noise.set_score(0.28); live.bar_meso.set_score(-1)
    live.faces_lbl.setText("Faces: 1"); live.methods_lbl.setText("Methods: 3")
    live._fps_lbl.setText("FPS: 28.4"); live._frame_cnt_lbl.setText("Frame #842")
    live.start_btn.setText("■  Stop Detection")
    live.start_btn.setObjectName("dangerBtn"); live.start_btn.setStyle(live.start_btn.style())
    live.snap_btn.setEnabled(True); live.save_btn.setEnabled(True)
    live._pulse.start()
    win._goto(1)
    grab(win, app, "live_detection.png")
    live._pulse.stop()

    # ── ANALYZE MEDIA (with heatmap) ───────────────────────────────────────────
    analyze = win.analyze_tab
    imgpath = os.path.join(os.path.dirname(DEMO), "portrait.png")
    analyze._load_file(imgpath)
    from src.gui.analyze_tab import AnalysisWorker
    w = AnalysisWorker(det, imgpath)
    w.heatmap_ready.connect(analyze._on_heatmap)
    w.viz_ready.connect(analyze._add_viz)
    w.result_ready.connect(analyze._on_result)
    w.run()
    freeze_dial(analyze.dial)
    analyze._toggle_heatmap()  # show heatmap overlay
    analyze.result_tabs.setCurrentIndex(0)  # scores
    win._goto(2)
    grab(win, app, "analyze_media.png")

    # ── ANALYZE / TEMPORAL (video) — separate showcase ─────────────────────────
    # Build a quick synthetic video
    import tempfile
    vp = os.path.join(tempfile.mkdtemp(), "clip.mp4")
    vw = cv2.VideoWriter(vp, cv2.VideoWriter_fourcc(*'mp4v'), 20.0, (640, 480))
    for i in range(40):
        fr = portrait.copy()
        if i % 11 == 0:  # occasional blink
            cv2.ellipse(fr, (640//2-42, int(480*0.52)-20), (26, 4), 0, 0, 360, (176,158,146), -1)
            cv2.ellipse(fr, (640//2+42, int(480*0.52)-20), (26, 4), 0, 0, 360, (176,158,146), -1)
        noise = (np.random.rand(480,640,3)*8).astype(np.uint8)
        vw.write(cv2.add(fr, noise))
    vw.release()
    analyze._load_file(vp)
    w2 = AnalysisWorker(det, vp)
    w2.temporal_ready.connect(analyze._on_temporal)
    w2.heatmap_ready.connect(analyze._on_heatmap)
    w2.viz_ready.connect(analyze._add_viz)
    w2.result_ready.connect(analyze._on_result)
    w2.run()
    if analyze._last_result:
        freeze_dial(analyze.dial)
    analyze.result_tabs.setCurrentIndex(1)  # temporal
    win._goto(2)
    grab(win, app, "temporal_analysis.png")

    # ── BATCH SCAN ─────────────────────────────────────────────────────────────
    batch = win.batch_tab
    batch._folder = "/Users/research/datasets/faceforensics_sample"
    batch.folder_lbl.setText(batch._folder)
    from src.gui.theme import TEXT_MID
    batch.folder_lbl.setStyleSheet(f"color: {TEXT_MID}; font-size: 12px; font-family: monospace;")
    batch_rows = [
        ("real_youtube_001.jpg", "IMG", "REAL", 0.08, 1, ""),
        ("deepfake_faceswap_a.mp4", "VID", "DEEPFAKE", 0.91, 1, "12 frames"),
        ("original_news.png", "IMG", "REAL", 0.16, 2, ""),
        ("neuraltextures_02.mp4", "VID", "DEEPFAKE", 0.83, 1, "12 frames"),
        ("face2face_clip.mp4", "VID", "SUSPICIOUS", 0.58, 1, "12 frames"),
        ("authentic_portrait.jpg", "IMG", "REAL", 0.12, 1, ""),
        ("gan_generated_07.png", "IMG", "DEEPFAKE", 0.74, 1, ""),
        ("interview_real.mp4", "VID", "REAL", 0.23, 1, "12 frames"),
        ("manipulated_speech.mp4", "VID", "SUSPICIOUS", 0.49, 1, "12 frames"),
        ("stock_photo_hd.jpg", "IMG", "REAL", 0.07, 3, ""),
        ("synthesized_avatar.png", "IMG", "DEEPFAKE", 0.69, 1, ""),
        ("webcam_capture.jpg", "IMG", "REAL", 0.19, 1, ""),
    ]
    batch.table.setSortingEnabled(False)   # avoid mid-insert re-sort scrambling cells
    for name, typ, verdict, score, faces, note in batch_rows:
        row = {"path": f"{batch._folder}/{name}", "name": name, "type": typ,
               "verdict": verdict, "score": score, "faces": faces,
               "methods": 4 if typ == "IMG" else 3, "note": note}
        batch._results.append(row)
        batch._append_table_row(row)
    batch.table.setSortingEnabled(True)
    batch._refresh_stats()
    batch.export_btn.setEnabled(True)
    batch.scan_btn.setEnabled(True)
    win._goto(3)
    grab(win, app, "batch_scan.png")

    # ── HOW IT WORKS ───────────────────────────────────────────────────────────
    win._goto(4)
    grab(win, app, "how_it_works.png")

    # ── SETTINGS ───────────────────────────────────────────────────────────────
    win._goto(5)
    grab(win, app, "settings.png")

    print("All screenshots generated.")
    win.close()


if __name__ == "__main__":
    main()
