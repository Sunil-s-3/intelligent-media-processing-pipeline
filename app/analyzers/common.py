"""Shared image loading helpers.

Uses cv2.imdecode so Unicode paths work on Windows.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

BgrImage = NDArray[np.uint8]


def load_bgr(path: Path) -> BgrImage:
    """Load a color image as BGR. Raises ValueError if decoding fails."""
    data = np.fromfile(str(path), dtype=np.uint8)
    if data.size == 0:
        raise ValueError(f"Image file is empty: {path}")
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Unable to decode image: {path}")
    return image


def clamp_confidence(value: float) -> float:
    """Keep heuristic confidence in [0, 1] and round for stable JSON."""
    return round(min(1.0, max(0.0, value)), 4)
