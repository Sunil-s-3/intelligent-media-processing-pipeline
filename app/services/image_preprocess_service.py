"""Downscale large images before analyzer execution to reduce memory use."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import cv2
from PIL import Image

from app.analyzers.common import compute_downscale_size, load_bgr
from app.core.config import settings

logger = logging.getLogger(__name__)


def _write_bgr_jpeg(path: Path, image) -> None:
    success, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not success:
        raise ValueError("Unable to encode downscaled image")
    path.write_bytes(encoded.tobytes())


def _image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as img:
        return img.size


@contextmanager
def prepare_processing_image(source: Path) -> Iterator[Path]:
    """Yield an image path suitable for analyzers, downscaling large inputs once."""
    width, height = _image_dimensions(source)
    max_dimension = settings.MAX_PROCESSING_DIMENSION
    new_size = compute_downscale_size(width, height, max_dimension)

    if new_size is None:
        logger.info(
            "processing image without downscale width=%s height=%s max_dimension=%s",
            width,
            height,
            max_dimension,
            extra={"processing_id": source.stem},
        )
        yield source
        return

    image = load_bgr(source)
    new_width, new_height = new_size
    resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    del image

    temp_dir = Path(settings.WORKER_TEMP_PATH)
    temp_dir.mkdir(parents=True, exist_ok=True)
    dest = temp_dir / f"{source.stem}_proc.jpg"

    logger.info(
        "downscaled image for processing from=%sx%s to=%sx%s max_dimension=%s path=%s",
        width,
        height,
        new_width,
        new_height,
        max_dimension,
        dest,
        extra={"processing_id": source.stem},
    )

    try:
        _write_bgr_jpeg(dest, resized)
        del resized
        yield dest
    finally:
        if dest.exists() and dest.resolve() != source.resolve():
            try:
                dest.unlink()
                logger.info(
                    "downscaled processing image deleted path=%s",
                    dest,
                    extra={"processing_id": source.stem},
                )
            except OSError:
                logger.warning(
                    "failed to delete downscaled processing image path=%s",
                    dest,
                    extra={"processing_id": source.stem},
                )
