"""SRM (Steganalysis Rich Model) noise residual analysis.

Manipulated regions from deepfakes have statistically different noise than
authentic camera-captured regions. High-pass SRM filters extract residuals.
"""

import numpy as np
import cv2


# Simplified SRM filter set (3×3 variants from the original SRM paper)
_SRM_KERNELS = np.array([
    # Horizontal neighbor difference
    [[0, 0, 0], [0, -1, 1], [0, 0, 0]],
    # Vertical neighbor difference
    [[0, 0, 0], [0, -1, 0], [0, 1, 0]],
    # Diagonal
    [[0, 0, 0], [0, -1, 0], [0, 0, 1]],
    # 2nd order horizontal
    [[0, 0, 0], [1, -2, 1], [0, 0, 0]],
    # 2nd order vertical
    [[0, 1, 0], [0, -2, 0], [0, 1, 0]],
], dtype=np.float32)


def noise_consistency_score(image_bgr: np.ndarray) -> tuple[float, np.ndarray]:
    """
    Compare noise residuals between face region and background.
    Inconsistency indicates face region was composited from a different source.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = gray.shape

    # Stack residual maps from all SRM filters
    residuals = []
    for k in _SRM_KERNELS:
        res = cv2.filter2D(gray, -1, k)
        residuals.append(res)
    residual_stack = np.stack(residuals, axis=0)  # (5, H, W)
    residual_mag = np.mean(np.abs(residual_stack), axis=0)

    # Build rough face mask using skin color detection
    face_mask = _skin_mask(image_bgr)

    if face_mask.sum() < 100 or (1 - face_mask / 255.0).sum() < 100:
        # Not enough region separation — use center/edge split
        cy, cx = h // 2, w // 2
        face_mask = np.zeros((h, w), dtype=np.uint8)
        face_mask[h // 4:3 * h // 4, w // 4:3 * w // 4] = 255

    bg_mask = (255 - face_mask)

    face_noise = residual_mag[face_mask > 0]
    bg_noise = residual_mag[bg_mask > 0]

    if len(face_noise) < 50 or len(bg_noise) < 50:
        return 0.0, _residual_viz(residual_mag)

    # Kolmogorov-Smirnov-like statistic (simplified): compare distributions
    face_mean, face_std = np.mean(face_noise), np.std(face_noise) + 1e-6
    bg_mean, bg_std = np.mean(bg_noise), np.std(bg_noise) + 1e-6

    mean_diff = abs(face_mean - bg_mean) / (max(face_mean, bg_mean) + 1e-6)
    std_diff = abs(face_std - bg_std) / (max(face_std, bg_std) + 1e-6)

    score = float(np.clip(0.5 * mean_diff + 0.5 * std_diff, 0.0, 1.0))
    return score, _residual_viz(residual_mag)


def _skin_mask(image_bgr: np.ndarray) -> np.ndarray:
    """Rough skin detection in YCrCb colorspace."""
    ycrcb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2YCrCb)
    # Standard skin tone range in YCrCb
    lower = np.array([0, 135, 85], dtype=np.uint8)
    upper = np.array([235, 180, 135], dtype=np.uint8)
    mask = cv2.inRange(ycrcb, lower, upper)
    # Morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return mask


def _residual_viz(residual_mag: np.ndarray) -> np.ndarray:
    norm = cv2.normalize(residual_mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    return cv2.applyColorMap(norm, cv2.COLORMAP_HOT)
