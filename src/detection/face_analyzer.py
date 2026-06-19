"""Face geometry and boundary consistency analysis using OpenCV.

Uses Haar cascade + eye detection for face region identification,
then checks boundary artifacts, skin uniformity, and geometry consistency.
"""

import numpy as np
import cv2
import os
from dataclasses import dataclass


@dataclass
class FaceAnalysisResult:
    score: float               # 0 = real, 1 = deepfake
    faces_found: int
    face_rects: list           # list of (x, y, w, h)
    boundary_score: float
    geometry_score: float
    skin_score: float


_face_cascade: cv2.CascadeClassifier | None = None
_eye_cascade: cv2.CascadeClassifier | None = None


def _get_cascades():
    global _face_cascade, _eye_cascade
    if _face_cascade is None:
        data_dir = cv2.data.haarcascades
        _face_cascade = cv2.CascadeClassifier(
            os.path.join(data_dir, 'haarcascade_frontalface_default.xml')
        )
        _eye_cascade = cv2.CascadeClassifier(
            os.path.join(data_dir, 'haarcascade_eye.xml')
        )
    return _face_cascade, _eye_cascade


def analyze_face(image_bgr: np.ndarray) -> FaceAnalysisResult:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    face_cascade, eye_cascade = _get_cascades()

    h, w = gray.shape
    scale_factor = 1.1
    min_size = (max(20, w // 10), max(20, h // 10))
    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=scale_factor, minNeighbors=5,
        minSize=min_size, flags=cv2.CASCADE_SCALE_IMAGE
    )

    if len(faces) == 0:
        return FaceAnalysisResult(0.0, 0, [], 0.0, 0.0, 0.0)

    scores = []
    for (fx, fy, fw, fh) in faces:
        boundary = _boundary_artifact_score(image_bgr, fx, fy, fw, fh)
        geometry = _geometry_consistency_score(
            gray, eye_cascade, fx, fy, fw, fh
        )
        skin = _skin_uniformity_score(image_bgr, fx, fy, fw, fh)

        face_score = 0.40 * boundary + 0.35 * geometry + 0.25 * skin
        scores.append((face_score, boundary, geometry, skin))

    best = max(scores, key=lambda x: x[0])
    return FaceAnalysisResult(
        score=float(np.clip(best[0], 0.0, 1.0)),
        faces_found=len(faces),
        face_rects=list(map(tuple, faces)),
        boundary_score=best[1],
        geometry_score=best[2],
        skin_score=best[3],
    )


def _boundary_artifact_score(
    image: np.ndarray, fx: int, fy: int, fw: int, fh: int
) -> float:
    """Detect blending/sharpness mismatch at face boundary."""
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    laplacian = np.abs(cv2.Laplacian(gray, cv2.CV_32F))

    # Face interior (eroded)
    margin = max(4, min(fw, fh) // 12)
    ix1 = max(0, fx + margin)
    iy1 = max(0, fy + margin)
    ix2 = min(w, fx + fw - margin)
    iy2 = min(h, fy + fh - margin)

    # Boundary ring (original box minus interior)
    face_mask = np.zeros((h, w), dtype=np.uint8)
    face_mask[fy:fy+fh, fx:fx+fw] = 1
    inner_mask = np.zeros((h, w), dtype=np.uint8)
    inner_mask[iy1:iy2, ix1:ix2] = 1
    ring_mask = face_mask & ~inner_mask

    inner_lap = laplacian[inner_mask > 0]
    ring_lap = laplacian[ring_mask > 0]

    if len(inner_lap) < 10 or len(ring_lap) < 10:
        return 0.0

    inner_mean = np.mean(inner_lap)
    ring_mean = np.mean(ring_lap)

    if inner_mean < 1e-6:
        return 0.0

    # Significant sharpness drop at boundary → blending artifact
    ratio = abs(ring_mean - inner_mean) / (inner_mean + 1e-6)
    return float(np.clip(ratio / 1.5, 0.0, 1.0))


def _geometry_consistency_score(
    gray: np.ndarray, eye_cascade, fx: int, fy: int, fw: int, fh: int
) -> float:
    """Check facial proportions and eye placement against real face distributions."""
    face_roi = gray[fy:fy + fh, fx:fx + fw]
    if face_roi.size == 0:
        return 0.0

    # Detect eyes within the face region (expected in upper ~50%)
    upper_half = face_roi[:fh // 2, :]
    eyes = eye_cascade.detectMultiScale(
        upper_half, scaleFactor=1.05, minNeighbors=4,
        minSize=(fw // 8, fh // 12)
    )

    if len(eyes) < 2:
        return 0.05  # can't see eyes — mild suspicion

    # Sort eyes left to right
    eyes_sorted = sorted(eyes, key=lambda e: e[0])
    e1, e2 = eyes_sorted[0], eyes_sorted[1]

    e1_cx = e1[0] + e1[2] // 2
    e2_cx = e2[0] + e2[2] // 2
    eye_dist_px = abs(e2_cx - e1_cx)

    # Eyes should be symmetric around face center
    face_cx = fw // 2
    e1_offset = abs(e1_cx - face_cx)
    e2_offset = abs(e2_cx - face_cx)

    symmetry_ratio = abs(e1_offset - e2_offset) / (max(e1_offset, e2_offset) + 1e-6)

    # Eye vertical position: should be ~35–45% from top
    e_y = ((e1[1] + e1[3] // 2) + (e2[1] + e2[3] // 2)) / 2
    eye_vpos = e_y / fh
    vpos_score = 0.0 if 0.25 <= eye_vpos <= 0.55 else min(1.0, abs(eye_vpos - 0.40) / 0.25)

    # Eye distance relative to face width: typically 30–50%
    eye_rel_dist = eye_dist_px / (fw + 1e-6)
    dist_score = 0.0 if 0.25 <= eye_rel_dist <= 0.55 else min(1.0, abs(eye_rel_dist - 0.40) / 0.25)

    combined = 0.4 * symmetry_ratio + 0.3 * vpos_score + 0.3 * dist_score
    return float(np.clip(combined, 0.0, 1.0))


def _skin_uniformity_score(
    image: np.ndarray, fx: int, fy: int, fw: int, fh: int
) -> float:
    """Detect over-smoothed skin (deepfake hallmark) vs. authentic texture variance."""
    h, w = image.shape[:2]
    margin = max(4, min(fw, fh) // 10)
    face_region = image[
        max(0, fy + margin):min(h, fy + fh - margin),
        max(0, fx + margin):min(w, fx + fw - margin)
    ]

    if face_region.size == 0:
        return 0.0

    # Filter to skin-colored pixels
    ycrcb = cv2.cvtColor(face_region, cv2.COLOR_BGR2YCrCb)
    skin_mask = cv2.inRange(ycrcb, np.array([0, 135, 85]), np.array([235, 180, 135]))

    y_chan = ycrcb[:, :, 0]
    skin_pixels = y_chan[skin_mask > 0].astype(np.float32)

    if len(skin_pixels) < 50:
        # Fall back to full face region
        skin_pixels = y_chan.flatten().astype(np.float32)

    if len(skin_pixels) < 10:
        return 0.0

    texture_std = np.std(skin_pixels)

    # Real skin: texture_std typically 10–50
    # Over-smoothed (deepfake): < 8; blending artifacts: > 55
    if texture_std < 8.0:
        return float(np.clip((8.0 - texture_std) / 8.0 * 0.75, 0.0, 1.0))
    elif texture_std > 55.0:
        return float(np.clip((texture_std - 55.0) / 40.0 * 0.5, 0.0, 1.0))
    return 0.0


def draw_face_overlay(image: np.ndarray, result: FaceAnalysisResult, score: float) -> np.ndarray:
    """Draw detection overlay on frame."""
    out = image.copy()
    if result.faces_found == 0:
        return out

    color = _score_color(score)
    for (fx, fy, fw, fh) in result.face_rects:
        cv2.rectangle(out, (fx, fy), (fx + fw, fy + fh), color, 2)

        # Corner accents
        corner_len = max(8, min(fw, fh) // 6)
        for (cx, cy, dx, dy) in [
            (fx, fy, 1, 1), (fx + fw, fy, -1, 1),
            (fx, fy + fh, 1, -1), (fx + fw, fy + fh, -1, -1)
        ]:
            cv2.line(out, (cx, cy), (cx + dx * corner_len, cy), color, 3)
            cv2.line(out, (cx, cy), (cx, cy + dy * corner_len), color, 3)

    label = f"{score*100:.0f}%  {'DEEPFAKE' if score >= 0.65 else 'SUSPICIOUS' if score >= 0.40 else 'REAL'}"
    cv2.putText(out, label, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(out, label, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2, cv2.LINE_AA)

    return out


def _score_color(score: float) -> tuple[int, int, int]:
    if score >= 0.65:
        return (0, 0, 255)
    elif score >= 0.40:
        return (0, 140, 255)
    return (0, 220, 80)
