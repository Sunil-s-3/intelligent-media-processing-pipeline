"""Lightweight screenshot / photo-of-photo / editing heuristics.

This is intentionally conservative. None of these signals prove the image is a
screenshot, a photo of a photo, or tampered. The output uses language such as
"potentially suspicious" and keeps confidence modest.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image as PILImage
from PIL.ExifTags import TAGS

from app.analyzers.common import clamp_confidence

# Common desktop / phone screenshot resolutions. A match is a weak signal only.
_COMMON_SCREEN_SIZES = {
    (1920, 1080),
    (1080, 1920),
    (1280, 720),
    (1366, 768),
    (2560, 1440),
    (1440, 2560),
    (1170, 2532),
    (1284, 2778),
    (390, 844),
    (393, 852),
    (428, 926),
}

_SCREENSHOT_SOFTWARE = (
    "snipping",
    "snippingtool",
    "screenshot",
    "grab",
    "lightshot",
    "sharex",
    "greenshot",
)

_EDITING_SOFTWARE = (
    "photoshop",
    "gimp",
    "snapseed",
    "lightroom",
    "pixelmator",
    "affinity",
    "picsart",
)


def _exif_dict(image: PILImage.Image) -> dict[str, str]:
    try:
        raw = image.getexif()
    except Exception:
        return {}
    if not raw:
        return {}
    decoded: dict[str, str] = {}
    for tag_id, value in raw.items():
        name = TAGS.get(tag_id, str(tag_id))
        decoded[str(name)] = str(value)
    return decoded


def analyze_screenshot(image_path: Path) -> dict:
    with PILImage.open(image_path) as img:
        width, height = img.size
        exif = _exif_dict(img)
        fmt = img.format

    signals: list[str] = []
    score = 0.0

    software = (exif.get("Software") or "").lower()
    if any(token in software for token in _SCREENSHOT_SOFTWARE):
        signals.append(f"EXIF Software looks screenshot-related: {software}")
        score += 0.55

    if any(token in software for token in _EDITING_SOFTWARE):
        signals.append(f"EXIF Software mentions editing tools: {software}")
        score += 0.25

    if not exif:
        signals.append("No EXIF metadata present (common for screenshots, also common after re-export)")
        score += 0.15

    if (width, height) in _COMMON_SCREEN_SIZES:
        signals.append(f"Exact common screen resolution {width}x{height}")
        score += 0.2

    # Very wide/tall phone-like aspect with no camera EXIF make/model.
    if not exif.get("Make") and not exif.get("Model"):
        signals.append("No camera Make/Model EXIF tags")
        score += 0.1

    detected = score >= 0.55
    editing_indicators = any(token in software for token in _EDITING_SOFTWARE)

    if detected:
        reason = "Heuristic signals suggest this may be a screenshot or re-exported image"
    elif editing_indicators:
        reason = "Possible editing indicators in metadata; not proof of tampering"
    else:
        reason = "No strong screenshot or editing heuristic signals"

    return {
        "detected": detected,
        "issue": detected,
        "heuristic_score": clamp_confidence(score),
        "confidence": clamp_confidence(min(0.7, 0.4 + score * 0.4)),
        "reason": reason,
        "signals": signals,
        "possible_editing_indicators": editing_indicators,
        "image_format": fmt,
        "width": width,
        "height": height,
        "confidence_note": (
            "Weak heuristic only. Missing EXIF is normal after messaging-app "
            "recompression. Do not treat this as forensic evidence."
        ),
    }
