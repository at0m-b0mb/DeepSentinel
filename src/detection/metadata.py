"""EXIF metadata extraction for deepfake forensics."""

import os
from typing import Any


def extract_metadata(path: str) -> dict[str, Any]:
    """Return a dict of interesting metadata fields from an image or video."""
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.mp4', '.mov', '.avi', '.mkv', '.webm'):
        return _video_metadata(path)
    return _image_metadata(path)


def _image_metadata(path: str) -> dict[str, Any]:
    result = {
        "file_size": _fmt_size(os.path.getsize(path)),
        "format": os.path.splitext(path)[1].upper().lstrip('.'),
    }
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        img = Image.open(path)
        result["dimensions"] = f"{img.width} × {img.height}"
        result["mode"] = img.mode

        raw_exif = img._getexif() if hasattr(img, '_getexif') else None
        if raw_exif:
            interesting = {
                "Make", "Model", "Software", "DateTime", "DateTimeOriginal",
                "DateTimeDigitized", "ExifVersion", "FlashPixVersion",
                "ColorSpace", "PixelXDimension", "PixelYDimension",
                "GPSInfo", "ImageDescription", "XResolution", "YResolution",
                "Orientation",
            }
            for tag_id, value in raw_exif.items():
                tag = TAGS.get(tag_id, str(tag_id))
                if tag in interesting:
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='replace').strip('\x00')
                        except Exception:
                            value = repr(value)
                    result[tag] = str(value)[:120]
    except Exception as e:
        result["_parse_error"] = str(e)

    return result


def _video_metadata(path: str) -> dict[str, Any]:
    result = {
        "file_size": _fmt_size(os.path.getsize(path)),
        "format": os.path.splitext(path)[1].upper().lstrip('.'),
    }
    try:
        import cv2
        cap = cv2.VideoCapture(path)
        if cap.isOpened():
            result["width"]      = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            result["height"]     = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            result["fps"]        = f"{cap.get(cv2.CAP_PROP_FPS):.2f}"
            result["frames"]     = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration_s = result["frames"] / (cap.get(cv2.CAP_PROP_FPS) or 25)
            result["duration"]   = f"{duration_s:.1f}s"
            result["dimensions"] = f"{result['width']} × {result['height']}"
            cap.release()
    except Exception as e:
        result["_parse_error"] = str(e)

    return result


def _fmt_size(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# Keys to highlight in a suspicious analysis
SUSPICIOUS_EXIF_KEYS = {"Software", "ImageDescription"}
AI_SOFTWARE_HINTS = {
    "photoshop", "gimp", "stable diffusion", "midjourney", "dall-e",
    "deepfake", "facefusion", "simswap", "faceswap", "generated",
    "synthesized", "artificial",
}


def flag_suspicious(meta: dict) -> list[str]:
    """Return list of suspicious EXIF findings."""
    flags = []
    sw = str(meta.get("Software", "")).lower()
    for hint in AI_SOFTWARE_HINTS:
        if hint in sw:
            flags.append(f"⚠  Software field mentions AI/editing tool: '{meta['Software']}'")

    if "GPSInfo" not in meta and "Make" not in meta:
        flags.append("ℹ  No camera EXIF — image may have been generated or stripped")

    desc = str(meta.get("ImageDescription", "")).lower()
    if any(h in desc for h in AI_SOFTWARE_HINTS):
        flags.append(f"⚠  ImageDescription contains suspicious keywords")

    return flags
