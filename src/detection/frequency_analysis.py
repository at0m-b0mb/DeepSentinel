"""FFT/DCT frequency domain analysis for deepfake artifact detection.

GAN and diffusion models introduce periodic artifacts from transposed convolution
upsampling (checkerboard artifacts). These show as spectral spikes in the FFT.
"""

import numpy as np
import cv2


def fft_artifact_score(image_bgr: np.ndarray) -> tuple[float, np.ndarray]:
    """Compute deepfake likelihood from FFT frequency spectrum."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = gray.shape

    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)
    magnitude = np.log1p(np.abs(fshift))

    # Suppress DC component (center low-freq region)
    cy, cx = h // 2, w // 2
    radius = min(h, w) // 8
    mask = np.ones((h, w), dtype=np.float32)
    for y in range(h):
        for x in range(w):
            if (y - cy) ** 2 + (x - cx) ** 2 < radius ** 2:
                mask[y, x] = 0.0
    masked = magnitude * mask

    # Kurtosis of non-DC spectrum: periodic GAN artifacts → sharp peaks → high kurtosis
    flat = masked[masked > 0].flatten()
    if len(flat) < 100:
        return 0.0, magnitude

    mean_val = np.mean(flat)
    std_val = np.std(flat)
    if std_val < 1e-6:
        return 0.0, magnitude

    kurtosis = np.mean(((flat - mean_val) / std_val) ** 4)

    # Look for grid-pattern spikes (classic GAN upsampling artifact)
    grid_score = _detect_grid_pattern(masked, cy, cx)

    # Combine: empirical thresholds calibrated on FaceForensics++ data
    kurtosis_score = np.clip((kurtosis - 2.5) / 8.0, 0.0, 1.0)
    combined = 0.6 * kurtosis_score + 0.4 * grid_score

    viz = (magnitude / magnitude.max() * 255).astype(np.uint8)
    viz_colored = cv2.applyColorMap(viz, cv2.COLORMAP_JET)

    return float(np.clip(combined, 0.0, 1.0)), viz_colored


def _detect_grid_pattern(spectrum: np.ndarray, cy: int, cx: int) -> float:
    """Detect regular grid patterns in spectrum indicative of GAN upsampling."""
    h, w = spectrum.shape
    # Sample spectrum along cardinal axes at strides typical of 2x upsampling
    scores = []
    for stride in [w // 8, w // 4, h // 8, h // 4]:
        if stride < 4:
            continue
        # Check for peaks at multiples of stride distance from center
        for offset in [stride, stride * 2]:
            if cx + offset < w:
                local_max = np.max(spectrum[cy - 2:cy + 2, cx + offset - 2:cx + offset + 2])
                surrounding = np.mean(spectrum[cy - 5:cy + 5, cx + offset - 8:cx + offset + 8])
                if surrounding > 0:
                    scores.append(min(1.0, local_max / (surrounding + 1e-6) / 5.0))

    return float(np.mean(scores)) if scores else 0.0


def ela_score(image_bgr: np.ndarray, quality: int = 90) -> tuple[float, np.ndarray]:
    """Error Level Analysis: detect JPEG re-compression inconsistencies."""
    import io
    from PIL import Image, ImageChops, ImageEnhance

    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)

    buf = io.BytesIO()
    pil_img.save(buf, "JPEG", quality=quality)
    buf.seek(0)
    compressed = Image.open(buf)
    compressed.load()

    ela_img = ImageChops.difference(pil_img, compressed)
    extrema = ela_img.getextrema()
    max_diff = max(e[1] for e in extrema) if extrema else 1
    scale = 255.0 / (max_diff + 1e-6)
    ela_img = ImageEnhance.Brightness(ela_img).enhance(scale)

    ela_arr = np.array(ela_img)
    ela_gray = cv2.cvtColor(ela_arr, cv2.COLOR_RGB2GRAY)

    # High spatial variance in ELA map = manipulation
    local_std = cv2.Laplacian(ela_gray, cv2.CV_64F).var()
    score = float(np.clip(local_std / 3000.0, 0.0, 1.0))

    viz = cv2.cvtColor(ela_arr, cv2.COLOR_RGB2BGR)
    return score, viz
