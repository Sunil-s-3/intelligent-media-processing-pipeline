"""Resolve stored image files for API download and worker processing."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.exceptions import ImageNotFoundError
from app.db.models import Image

logger = logging.getLogger(__name__)

_PROCESSING_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class ImageFileMissingError(Exception):
    """Local file absent and remote download is not configured or unavailable."""


class ImageDownloadNotFoundError(Exception):
    """API service reports the image file does not exist."""


class ImageDownloadTransientError(Exception):
    """Temporary failure downloading the image from the API service."""


def _safe_stored_filename(stored_filename: str) -> str:
    name = Path(stored_filename).name
    if not name or name != stored_filename or ".." in stored_filename:
        raise ImageNotFoundError("Stored image file is not available")
    return name


def get_api_stored_image_path(image: Image) -> Path:
    """Return the on-disk image path for API file download."""
    if not _PROCESSING_ID_RE.fullmatch(image.id):
        raise ImageNotFoundError("No image found for processing_id")

    filename = _safe_stored_filename(image.stored_filename)
    storage_root = settings.storage_dir.resolve()
    file_path = (storage_root / filename).resolve()

    try:
        file_path.relative_to(storage_root)
    except ValueError as exc:
        raise ImageNotFoundError("Stored image file is not available") from exc

    if not file_path.is_file():
        raise ImageNotFoundError("Stored image file is not available")

    return file_path


def _worker_temp_dir() -> Path:
    directory = Path(settings.WORKER_TEMP_PATH).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def download_image_from_api(processing_id: str, stored_filename: str) -> Path:
    """Download an image from the API service into the worker temp directory."""
    base_url = settings.internal_api_base_url
    if not base_url:
        raise ImageFileMissingError("Stored image file is missing on disk")

    if not _PROCESSING_ID_RE.fullmatch(processing_id):
        raise ImageDownloadNotFoundError("Image file not found on API service")

    try:
        filename = _safe_stored_filename(stored_filename)
    except ImageNotFoundError as exc:
        raise ImageDownloadNotFoundError(exc.message) from exc

    url = f"{base_url}/api/v1/images/{processing_id}/file"

    try:
        with httpx.Client(timeout=settings.IMAGE_DOWNLOAD_TIMEOUT_SECONDS) as client:
            response = client.get(url)
    except (
        httpx.TimeoutException,
        httpx.ConnectError,
        httpx.NetworkError,
        httpx.ReadError,
    ) as exc:
        raise ImageDownloadTransientError(
            f"Failed to download image from API service: {exc}"
        ) from exc

    if response.status_code == 404:
        raise ImageDownloadNotFoundError("Image file not found on API service")
    if response.status_code >= 500:
        raise ImageDownloadTransientError(
            f"API image download failed with status {response.status_code}"
        )
    if response.status_code != 200:
        raise ImageDownloadNotFoundError(
            f"API image download failed with status {response.status_code}"
        )

    if not response.content:
        raise ImageDownloadNotFoundError("API image download returned an empty file")

    temp_path = _worker_temp_dir() / filename
    temp_path.write_bytes(response.content)
    logger.info(
        "image downloaded from API bytes=%s",
        len(response.content),
        extra={"processing_id": processing_id},
    )
    return temp_path


def _local_image_path(image: Image) -> Path | None:
    try:
        filename = _safe_stored_filename(image.stored_filename)
    except ImageNotFoundError:
        return None

    direct = Path(image.storage_path)
    if direct.is_file() and direct.name == filename:
        return direct.resolve()

    storage_root = settings.storage_dir.resolve()
    candidate = (storage_root / filename).resolve()
    try:
        candidate.relative_to(storage_root)
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    return None


@contextmanager
def resolve_processing_image_path(image: Image) -> Iterator[Path]:
    """Yield a readable local image path, downloading from the API if needed."""
    local_path = _local_image_path(image)
    if local_path is not None:
        yield local_path
        return

    temp_path: Path | None = None
    try:
        temp_path = download_image_from_api(image.id, image.stored_filename)
        yield temp_path
    finally:
        if temp_path is not None and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                logger.warning(
                    "failed to delete temporary downloaded image",
                    extra={"processing_id": image.id},
                )
