"""Explainability heatmap — shows WHERE in an image artifacts are concentrated.

Combines three localized forensic signals on a tile grid:
  1. ELA response      — re-compression mismatch (edited regions glow brighter)
  2. Texture deficit   — over-smoothed regions (deepfake skin loses micro-texture)
  3. Noise residual    — SRM high-pass energy anomalies

The per-tile signals are normalized relative to the whole image, fused, smoothed,
and rendered as a translucent colour overlay (cyan = clean → red = suspect).
"""

import io
import numpy as np
import cv2


def suspicion_heatmap(
    image_bgr: np.ndarray,
    grid: int = 24,
    alpha: float = 0.55,
) -> tuple[np.ndarray, np.ndarray, float]:
    """
    Returns:
        overlay     — original blended with colourized heatmap (BGR)
        heat_color  — standalone colourized heatmap (BGR)
        concentration — 0..1, how spatially peaked the suspicion is
                        (high = localized hotspot, low = diffuse/uniform)
    """
    h, w = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

    ela = _ela_map(image_bgr)                       # high = edited
    texture = _texture_map(gray)                    # high = sharp/real
    noise = _noise_map(gray)                        # high = residual energy

    # Reduce each to the tile grid by block-averaging
    ela_g = _block_reduce(ela, grid)
    tex_g = _block_reduce(texture, grid)
    noi_g = _block_reduce(noise, grid)

    # Normalize each signal across tiles (relative anomaly)
    ela_n = _norm(ela_g)
    # Texture DEFICIT is suspicious → invert
    tex_def = _norm(-tex_g)
    noi_n = _norm(noi_g)

    # Fuse — ELA carries the most localization weight
    fused = 0.45 * ela_n + 0.30 * tex_def + 0.25 * noi_n
    fused = np.clip(fused, 0.0, 1.0)

    # Concentration: peaked heatmaps (few hot tiles) are more telling than uniform ones
    concentration = _concentration(fused)

    # Upscale smoothly to full resolution
    heat = cv2.resize(fused, (w, h), interpolation=cv2.INTER_CUBIC)
    heat = cv2.GaussianBlur(heat, (0, 0), sigmaX=max(3, min(w, h) / 50))
    heat = np.clip(heat, 0.0, 1.0)

    heat_u8 = (heat * 255).astype(np.uint8)
    heat_color = cv2.applyColorMap(heat_u8, cv2.COLORMAP_JET)

    # Blend: stronger overlay where suspicion is high
    weight = (heat[..., None] * alpha)
    overlay = (image_bgr.astype(np.float32) * (1 - weight) +
               heat_color.astype(np.float32) * weight).astype(np.uint8)

    # Annotate the single hottest region with a marker
    overlay = _mark_hotspot(overlay, fused, grid, w, h)

    return overlay, heat_color, float(concentration)


# ── Signal maps ────────────────────────────────────────────────────────────────

def _ela_map(image_bgr: np.ndarray, quality: int = 90) -> np.ndarray:
    """Per-pixel JPEG re-compression difference."""
    from PIL import Image
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    buf = io.BytesIO()
    pil.save(buf, "JPEG", quality=quality)
    buf.seek(0)
    recompressed = np.array(Image.open(buf)).astype(np.float32)
    diff = np.abs(rgb.astype(np.float32) - recompressed).mean(axis=2)
    return diff


def _texture_map(gray: np.ndarray) -> np.ndarray:
    """Local high-frequency texture energy (Laplacian magnitude)."""
    lap = np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))
    return cv2.GaussianBlur(lap, (0, 0), sigmaX=2)


def _noise_map(gray: np.ndarray) -> np.ndarray:
    """SRM high-pass noise residual magnitude."""
    k = np.array([[-1, 2, -2, 2, -1],
                  [2, -6, 8, -6, 2],
                  [-2, 8, -12, 8, -2],
                  [2, -6, 8, -6, 2],
                  [-1, 2, -2, 2, -1]], np.float32) / 12.0
    res = np.abs(cv2.filter2D(gray, cv2.CV_32F, k))
    return cv2.GaussianBlur(res, (0, 0), sigmaX=2)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _block_reduce(arr: np.ndarray, grid: int) -> np.ndarray:
    """Average-pool an array down to a grid×grid map."""
    h, w = arr.shape
    gh = max(1, grid)
    gw = max(1, grid)
    # Resize via INTER_AREA = exact block averaging
    return cv2.resize(arr, (gw, gh), interpolation=cv2.INTER_AREA)


def _norm(arr: np.ndarray) -> np.ndarray:
    """Robust min-max normalize to 0..1 using percentile clipping."""
    lo = np.percentile(arr, 5)
    hi = np.percentile(arr, 95)
    if hi - lo < 1e-6:
        return np.zeros_like(arr)
    return np.clip((arr - lo) / (hi - lo), 0.0, 1.0)


def _concentration(fused: np.ndarray) -> float:
    """How peaked is the suspicion map? Gini-like: few hot tiles → high score."""
    flat = np.sort(fused.flatten())
    n = len(flat)
    if n == 0 or flat.sum() < 1e-6:
        return 0.0
    # Fraction of total 'heat' held by the hottest 15% of tiles
    cut = int(n * 0.85)
    top_share = flat[cut:].sum() / (flat.sum() + 1e-6)
    # Random/uniform ≈ 0.15; fully concentrated ≈ 1.0
    return float(np.clip((top_share - 0.15) / 0.55, 0.0, 1.0))


def _mark_hotspot(overlay: np.ndarray, fused: np.ndarray,
                  grid: int, w: int, h: int) -> np.ndarray:
    """Draw a marker box around the single most suspicious tile cluster."""
    if fused.max() < 0.55:
        return overlay
    gy, gx = np.unravel_index(np.argmax(fused), fused.shape)
    tile_w = w / fused.shape[1]
    tile_h = h / fused.shape[0]
    # Expand to a small cluster box
    x1 = int(max(0, (gx - 0.5) * tile_w))
    y1 = int(max(0, (gy - 0.5) * tile_h))
    x2 = int(min(w, (gx + 1.5) * tile_w))
    y2 = int(min(h, (gy + 1.5) * tile_h))
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 255), 2)
    cv2.putText(overlay, "HOTSPOT", (x1, max(14, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
    return overlay
