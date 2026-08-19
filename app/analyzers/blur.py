"""Blur detection using variance of the Laplacian.

Approach
--------
OpenCV's Laplacian highlights edges. The variance of that response is a common
heuristic sharpness score: lower variance usually means fewer edges / more blur.

Threshold
---------
`BLUR_THRESHOLD` (default 100.0) is a commonly cited starting point from OpenCV
tutorials and is **not** a universal constant. Real camera phones, compression,
and subject distance all change the score. Tune via environment variable.

Confidence
----------
Confidence is a heuristic distance-from-threshold score, not a calibrated
probability from a trained model.
"""

from __future__ import annotations

from pathlib import Path

import cv2

from app.analyzers.common import clamp_confidence, load_bgr
from app.core.config import settings


def analyze_blur(
    image_path: Path,
    *,
    threshold: float | None = None,
) -> dict:
    threshold = settings.BLUR_THRESHOLD if threshold is None else threshold
    image = load_bgr(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    detected = score < threshold

    # Distance from threshold, scaled so values far from the cutoff get higher
    # heuristic confidence. Capped so we never claim certainty.
    if detected:
        raw = 0.55 + 0.45 * min(1.0, (threshold - score) / max(threshold, 1.0))
        reason = (
            f"Laplacian variance {score:.2f} is below threshold {threshold:.2f}, "
            "which often indicates blur"
        )
    else:
        raw = 0.55 + 0.45 * min(1.0, (score - threshold) / max(threshold * 3.0, 1.0))
        reason = (
            f"Laplacian variance {score:.2f} is at or above threshold "
            f"{threshold:.2f}"
        )

    return {
        "detected": detected,
        "score": round(score, 4),
        "threshold": threshold,
        "confidence": clamp_confidence(raw),
        "reason": reason,
        "method": "variance_of_laplacian",
        "confidence_note": (
            "Heuristic score based on distance from a configured threshold, "
            "not a calibrated ML probability"
        ),
    }
