"""Temporal video forensics — analysis across frames, not just within them.

Three temporal signals deepfakes commonly fail:
  1. Blink rate   — early/cheap deepfakes blink rarely or never.
                    Human resting rate ≈ 15-20 blinks/min.
  2. Flicker      — per-frame score variance + face-region jitter.
                    Synthesis is applied per-frame, so identity/lighting
                    'shimmers' frame-to-frame.
  3. Score trend  — sustained high deepfake score across the clip.
"""

import numpy as np
import cv2
from dataclasses import dataclass, field

from .face_analyzer import _get_cascades


@dataclass
class TemporalResult:
    frame_scores: list = field(default_factory=list)   # (timestamp_s, score)
    timestamps: list = field(default_factory=list)
    mean_score: float = 0.0
    peak_score: float = 0.0
    flicker_score: float = 0.0          # 0..1, higher = more inconsistent
    blink_count: int = 0
    blink_rate: float = 0.0             # blinks per minute
    blink_flag: bool = False            # True if abnormally low
    duration_s: float = 0.0
    frames_analyzed: int = 0
    temporal_score: float = 0.0         # combined 0..1
    label: str = "REAL"
    notes: list = field(default_factory=list)


def analyze_video_temporal(
    path: str,
    detector,
    max_frames: int = 60,
    progress_cb=None,
) -> TemporalResult:
    """Run temporal analysis over a video file."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return TemporalResult(notes=["Could not open video."])

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    duration = total / fps
    step = max(1, total // max_frames)

    face_cascade, eye_cascade = _get_cascades()

    frame_scores = []
    timestamps = []
    eye_open_series = []      # 1 = eyes open, 0 = closed/absent (face present)
    prev_face_crop = None
    face_jitter = []

    fi = 0
    analyzed = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if fi % step == 0:
            ts = fi / fps
            small = cv2.resize(frame, (320, 240))

            # Deepfake score for this frame
            r = detector.analyze(small, fast=True)
            frame_scores.append(r.overall_score)
            timestamps.append(ts)

            # Blink + jitter tracking
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))
            if len(faces) > 0:
                fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                face_roi = gray[fy:fy + fh, fx:fx + fw]
                upper = face_roi[:fh // 2, :]
                eyes = eye_cascade.detectMultiScale(upper, 1.05, 4,
                                                    minSize=(fw // 10, fh // 14))
                eye_open_series.append(1 if len(eyes) >= 2 else 0)

                # Face-region temporal jitter (identity shimmer)
                crop = cv2.resize(face_roi, (64, 64)).astype(np.float32)
                if prev_face_crop is not None:
                    diff = np.mean(np.abs(crop - prev_face_crop)) / 255.0
                    face_jitter.append(diff)
                prev_face_crop = crop

            analyzed += 1
            if progress_cb:
                progress_cb(min(99, int(analyzed / max_frames * 100)),
                            f"Frame {fi}/{total} · t={ts:.1f}s")
        fi += 1

    cap.release()

    res = TemporalResult(
        timestamps=timestamps,
        duration_s=duration,
        frames_analyzed=analyzed,
    )
    res.frame_scores = list(zip(timestamps, frame_scores))

    if not frame_scores:
        res.notes.append("No frames analyzed.")
        return res

    arr = np.array(frame_scores)
    res.mean_score = float(np.mean(arr))
    res.peak_score = float(np.max(arr))

    # ── Flicker: per-frame score variance + face jitter ──
    score_var = float(np.std(arr))
    jitter = float(np.mean(face_jitter)) if face_jitter else 0.0
    # Real talking-head video: jitter ~0.02-0.05; deepfake shimmer higher
    flicker = 0.5 * np.clip(score_var / 0.25, 0, 1) + 0.5 * np.clip(jitter / 0.12, 0, 1)
    res.flicker_score = float(np.clip(flicker, 0.0, 1.0))

    # ── Blink detection: count 1→0→1 transitions ──
    blinks = _count_blinks(eye_open_series)
    res.blink_count = blinks
    eff_minutes = max(duration, len(eye_open_series) * step / fps) / 60.0
    res.blink_rate = blinks / eff_minutes if eff_minutes > 0 else 0.0

    # Only flag blink anomaly if we actually tracked a face for a while
    if len(eye_open_series) >= 8:
        if res.blink_rate < 6.0:
            res.blink_flag = True
            res.notes.append(
                f"Low blink rate: {res.blink_rate:.1f}/min (human rest ≈ 15-20)."
            )
    else:
        res.notes.append("Insufficient face tracking for reliable blink analysis.")

    if res.flicker_score > 0.5:
        res.notes.append(f"High temporal flicker ({res.flicker_score:.2f}) — frame-to-frame inconsistency.")

    # ── Combined temporal score ──
    blink_component = 0.6 if res.blink_flag else 0.0
    res.temporal_score = float(np.clip(
        0.45 * res.mean_score +
        0.30 * res.flicker_score +
        0.25 * blink_component,
        0.0, 1.0
    ))

    if res.temporal_score >= 0.65:
        res.label = "DEEPFAKE"
    elif res.temporal_score >= 0.40:
        res.label = "SUSPICIOUS"
    else:
        res.label = "REAL"

    if not res.notes:
        res.notes.append("No strong temporal anomalies detected.")

    return res


def _count_blinks(series: list[int]) -> int:
    """Count eye-open → eye-closed → eye-open cycles."""
    if len(series) < 3:
        return 0
    blinks = 0
    state = series[0]
    closed_run = 0
    for v in series[1:]:
        if v == 0:
            closed_run += 1
        else:
            # transition back to open after being closed → one blink
            if closed_run >= 1 and state == 1:
                blinks += 1
            closed_run = 0
            state = 1
        if v == 1:
            state = 1
    return blinks
