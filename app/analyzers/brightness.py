"""Low-light / brightness detection.

Uses the mean grayscale pixel value (0-255). This is a simple global metric:
it will miss local darkness (e.g. a dark plate on a bright background) and can
flag night scenes that are still usable. Threshold is configurable.
"""

from __future__ import annotations

from pathlib import Path

import cv2

from app.analyzers.common import clamp_confidence, load_bgr
from app.core.config import settings


def analyze_brightness(
    image_path: Path,
    *,
    threshold: float | None = None,
) -> dict:
    threshold = settings.BRIGHTNESS_THRESHOLD if threshold is None else threshold
    image = load_bgr(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    average = float(gray.mean())
    issue = average < threshold

    if issue:
        raw = 0.55 + 0.45 * min(1.0, (threshold - average) / max(threshold, 1.0))
        reason = (
            f"Average brightness {average:.2f} is below threshold {threshold:.2f}, "
            "which often indicates a low-light image"
        )
    else:
        raw = 0.55 + 0.45 * min(
            1.0, (average - threshold) / max(255.0 - threshold, 1.0)
        )
        reason = (
            f"Average brightness {average:.2f} is at or above threshold "
            f"{threshold:.2f}"
        )

    return {
        "issue": issue,
        "average_brightness": round(average, 4),
        "threshold": threshold,
        "confidence": clamp_confidence(raw),
        "reason": reason,
        "method": "mean_grayscale",
        "confidence_note": (
            "Heuristic score based on distance from a configured threshold, "
            "not a calibrated ML probability"
        ),
    }
