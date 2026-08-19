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


def compute_downscale_size(
    width: int,
    height: int,
    max_dimension: int,
) -> tuple[int, int] | None:
    """Return a new (width, height) if downscaling is needed, else None."""
    if max(width, height) <= max_dimension:
        return None
    scale = max_dimension / max(width, height)
    return max(1, int(width * scale)), max(1, int(height * scale))


def downscale_bgr(image: BgrImage, max_dimension: int) -> BgrImage:
    """Downscale a BGR image preserving aspect ratio. Returns the original if already small."""
    height, width = image.shape[:2]
    new_size = compute_downscale_size(width, height, max_dimension)
    if new_size is None:
        return image
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def clamp_confidence(value: float) -> float:
    """Keep heuristic confidence in [0, 1] and round for stable JSON."""
    return round(min(1.0, max(0.0, value)), 4)
