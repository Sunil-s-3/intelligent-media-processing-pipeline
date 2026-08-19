"""Upload validation, persistence, and job enqueue.

The HTTP request never waits for analysis. After the image is stored and a
pending row exists, a background job is enqueued and 202 is returned.
"""

from __future__ import annotations

import logging
import uuid
from io import BytesIO

from fastapi import UploadFile
from PIL import Image as PILImage
from PIL import UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    CorruptImageError,
    DatabaseUnavailableError,
    ImageMissingError,
    ImageTooLargeError,
    QueueUnavailableError,
    UnsupportedImageTypeError,
)
from app.db.models import Image, ProcessingStatus
from app.queue.jobs import enqueue_image_job
from app.services import storage_service

logger = logging.getLogger(__name__)


def _read_upload(file: UploadFile | None) -> bytes:
    if file is None or not file.filename:
        raise ImageMissingError("No image file was provided. Use form field 'image'.")

    # Read in chunks so oversized uploads are rejected without buffering the
    # entire payload in memory first.
    max_bytes = settings.max_upload_bytes
    chunks: list[bytes] = []
    total = 0
    file.file.seek(0)
    while True:
        chunk = file.file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ImageTooLargeError(
                f"File exceeds the maximum upload size of {settings.MAX_UPLOAD_SIZE_MB} MB"
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _inspect_image(data: bytes) -> tuple[str, int, int]:
    """Decode bytes to confirm this is a real image. Do not trust the filename."""
    stream = BytesIO(data)
    try:
        with PILImage.open(stream) as img:
            img.verify()
            image_format = img.format
        stream.seek(0)
        with PILImage.open(stream) as img:
            img.load()
            width, height = img.size
            image_format = img.format or image_format
    except UnidentifiedImageError as exc:
        raise CorruptImageError("File could not be decoded as an image") from exc
    except OSError as exc:
        raise CorruptImageError("Image appears corrupt or truncated") from exc

    if not image_format or image_format.upper() not in settings.ALLOWED_IMAGE_FORMATS:
        raise UnsupportedImageTypeError(
            "Unsupported image type. Allowed formats: JPEG, PNG, WEBP, BMP, TIFF"
        )
    return image_format.upper(), width, height


def upload_image(db: Session, file: UploadFile | None) -> Image:
    data = _read_upload(file)
    if not data:
        raise ImageMissingError("Uploaded file is empty")

    image_format, width, height = _inspect_image(data)
    processing_id = str(uuid.uuid4())
    original_filename = file.filename or "upload"
    stored_path = storage_service.save_image(processing_id, data, image_format)

    record = Image(
        id=processing_id,
        original_filename=original_filename,
        stored_filename=stored_path.name,
        storage_path=str(stored_path),
        mime_type=storage_service.mime_for_format(image_format),
        file_size=len(data),
        width=width,
        height=height,
        status=ProcessingStatus.PENDING.value,
    )

    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except Exception as exc:
        db.rollback()
        storage_service.delete_image(stored_path)
        logger.exception(
            "database error while storing image metadata",
            extra={"processing_id": processing_id},
        )
        raise DatabaseUnavailableError("Unable to store image metadata") from exc

    logger.info(
        "image uploaded original=%s size=%s mime=%s",
        original_filename,
        len(data),
        record.mime_type,
        extra={"processing_id": processing_id},
    )

    try:
        enqueue_image_job(processing_id)
    except Exception as exc:
        logger.exception(
            "failed to enqueue processing job",
            extra={"processing_id": processing_id},
        )
        storage_service.delete_image(stored_path)
        db.delete(record)
        db.commit()
        raise QueueUnavailableError(
            "Image was accepted locally but the processing queue is unavailable. Retry later."
        ) from exc

    logger.info("job created", extra={"processing_id": processing_id})
    return record
