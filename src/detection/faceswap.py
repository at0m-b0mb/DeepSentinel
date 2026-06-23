"""Face-swap deepfake generation — the RED-TEAM / attacker side.

FOR EDUCATIONAL USE ONLY. This demonstrates how a simple face-swap deepfake is
built so its artifacts can be studied and detected. It uses a deliberately
classic, model-free pipeline (Haar face/eye detection → similarity alignment →
elliptical seamless clone), NOT a high-fidelity GAN. The colour/boundary/blending
artifacts it leaves behind are exactly what the DeepSentinel detector keys on,
closing the create → detect learning loop.

Pipeline (per target frame):
  1. Detect the largest face in source + target (Haar cascade)
  2. Estimate a similarity transform (scale + rotation from eye line) mapping
     the source face onto the target face position
  3. Warp the source image into target-aligned space
  4. seamlessClone the warped face into the target through an elliptical mask
"""

import numpy as np
import cv2

from .face_analyzer import _get_cascades


VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}


# ── Detection helpers ───────────────────────────────────────────────────────────

def _detect_face(gray: np.ndarray):
    """Return the largest face rect (x, y, w, h) or None."""
    face_cascade, _ = _get_cascades()
    h, w = gray.shape
    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5,
        minSize=(max(40, w // 12), max(40, h // 12)),
    )
    if len(faces) == 0:
        return None
    return tuple(max(faces, key=lambda f: f[2] * f[3]))


def _eye_angle(gray: np.ndarray, face):
    """Angle (degrees) of the eye line within a face, or None."""
    _, eye_cascade = _get_cascades()
    fx, fy, fw, fh = face
    roi = gray[fy:fy + fh // 2, fx:fx + fw]
    if roi.size == 0:
        return None
    eyes = eye_cascade.detectMultiScale(roi, 1.05, 4, minSize=(fw // 10, fh // 14))
    if len(eyes) < 2:
        return None
    eyes = sorted(eyes, key=lambda e: e[0])[:2]
    (x1, y1, w1, h1), (x2, y2, w2, h2) = eyes[0], eyes[1]
    c1 = (x1 + w1 / 2, y1 + h1 / 2)
    c2 = (x2 + w2 / 2, y2 + h2 / 2)
    return float(np.degrees(np.arctan2(c2[1] - c1[1], c2[0] - c1[0])))


# ── Core swap ────────────────────────────────────────────────────────────────

def swap_faces(src_img: np.ndarray, dst_img: np.ndarray,
               src_face=None, src_angle=None) -> tuple[np.ndarray, bool]:
    """Swap the source identity onto the target. Returns (result, success)."""
    src_gray = cv2.cvtColor(src_img, cv2.COLOR_BGR2GRAY)
    dst_gray = cv2.cvtColor(dst_img, cv2.COLOR_BGR2GRAY)

    if src_face is None:
        src_face = _detect_face(src_gray)
    if src_face is None:
        return dst_img, False
    dst_face = _detect_face(dst_gray)
    if dst_face is None:
        return dst_img, False

    sfx, sfy, sfw, sfh = src_face
    dfx, dfy, dfw, dfh = dst_face
    src_c = (sfx + sfw / 2.0, sfy + sfh / 2.0)
    dst_c = (dfx + dfw / 2.0, dfy + dfh / 2.0)

    # Scale source → target face size
    scale = ((dfw / sfw) + (dfh / sfh)) / 2.0

    # Rotation from eye-line difference (if measurable)
    if src_angle is None:
        src_angle = _eye_angle(src_gray, src_face)
    dst_angle = _eye_angle(dst_gray, dst_face)
    angle = 0.0
    if src_angle is not None and dst_angle is not None:
        angle = dst_angle - src_angle
        angle = float(np.clip(angle, -25, 25))   # guard against bad detections

    # Similarity transform: rotate+scale about source centre, then translate to target
    M = cv2.getRotationMatrix2D(src_c, -angle, scale)
    M[0, 2] += dst_c[0] - src_c[0]
    M[1, 2] += dst_c[1] - src_c[1]

    h, w = dst_img.shape[:2]
    warped = cv2.warpAffine(src_img, M, (w, h), flags=cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_REFLECT_101)

    # Elliptical face mask over the target face region (inset a touch)
    mask = np.zeros((h, w), dtype=np.uint8)
    axes = (int(dfw * 0.52), int(dfh * 0.64))
    center = (int(dst_c[0]), int(dst_c[1]))
    cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)

    try:
        output = cv2.seamlessClone(warped, dst_img, mask, center, cv2.NORMAL_CLONE)
    except cv2.error:
        m = cv2.GaussianBlur(mask, (0, 0), 9).astype(np.float32)[..., None] / 255.0
        output = (warped * m + dst_img * (1 - m)).astype(np.uint8)

    return output, True


# ── High-level jobs ──────────────────────────────────────────────────────────

def create_deepfake_image(src_path: str, target_path: str, out_path: str) -> tuple[bool, str]:
    src = cv2.imread(src_path)
    dst = cv2.imread(target_path)
    if src is None:
        return False, "Could not read the source face image."
    if dst is None:
        return False, "Could not read the target image."
    result, ok = swap_faces(src, dst)
    if not ok:
        return False, "Face not detected in the source and/or target."
    cv2.imwrite(out_path, result)
    return True, out_path


def create_deepfake_video(src_path: str, target_path: str, out_path: str,
                          progress_cb=None, preview_cb=None,
                          max_seconds: float = 30.0) -> tuple[bool, str]:
    """Swap the source face into every frame of the target video."""
    src = cv2.imread(src_path)
    if src is None:
        return False, "Could not read the source face image."
    src_gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    src_face = _detect_face(src_gray)
    if src_face is None:
        return False, "No face detected in the source image."
    src_angle = _eye_angle(src_gray, src_face)

    cap = cv2.VideoCapture(target_path)
    if not cap.isOpened():
        return False, "Could not open the target video."

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    max_frames = max(1, min(total, int(fps * max_seconds)))

    writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

    fi = 0
    swapped_any = False
    while fi < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        out, ok = swap_faces(src, frame, src_face=src_face, src_angle=src_angle)
        swapped_any = swapped_any or ok
        writer.write(out)

        fi += 1
        if progress_cb and fi % 2 == 0:
            progress_cb(int(fi / max_frames * 100), f"Frame {fi}/{max_frames}")
        if preview_cb and fi % 6 == 0:
            preview_cb(out)

    cap.release()
    writer.release()
    if not swapped_any:
        return False, "No face could be swapped (no face detected in the video)."
    return True, out_path
