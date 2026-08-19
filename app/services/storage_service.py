"""Local filesystem image storage.

Chosen for this take-home because it needs no cloud credentials. Production
would typically use object storage (S3/GCS) with the DB storing object keys.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

FORMAT_TO_EXTENSION = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "BMP": ".bmp",
    "TIFF": ".tif",
}

FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "BMP": "image/bmp",
    "TIFF": "image/tiff",
}


def ensure_storage_dir() -> Path:
    path = settings.storage_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def stored_filename(processing_id: str, image_format: str) -> str:
    extension = FORMAT_TO_EXTENSION.get(image_format.upper(), ".bin")
    return f"{processing_id}{extension}"


def save_image(processing_id: str, data: bytes, image_format: str) -> Path:
    directory = ensure_storage_dir()
    filename = stored_filename(processing_id, image_format)
    destination = directory / filename
    destination.write_bytes(data)
    logger.info(
        "image stored path=%s bytes=%s",
        destination,
        len(data),
        extra={"processing_id": processing_id},
    )
    return destination


def delete_image(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        logger.warning("failed to delete stored image path=%s", path)


def mime_for_format(image_format: str) -> str:
    return FORMAT_TO_MIME.get(image_format.upper(), "application/octet-stream")
