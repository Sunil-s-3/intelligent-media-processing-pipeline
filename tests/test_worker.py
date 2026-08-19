import uuid
from unittest.mock import patch

import httpx
import pytest

from app.core.config import settings
from app.db.models import AnalysisResult, Image, ProcessingStatus
from app.services.image_access_service import resolve_processing_image_path
from app.services.processing_service import (
    NonRetryableProcessingError,
    RetryableProcessingError,
    _process_with_session,
)
from tests.helpers import noisy_image, png_bytes, save_png


def _insert_image(db_session, tmp_path, *, processing_id: str | None = None, missing_file: bool = False) -> Image:
    processing_id = processing_id or str(uuid.uuid4())
    if missing_file:
        stored = tmp_path / f"{processing_id}.png"
        data = png_bytes()
        size = len(data)
        width, height = 64, 64
    else:
        stored = save_png(tmp_path / f"{processing_id}.png", noisy_image())
        size = stored.stat().st_size
        width, height = 128, 128

    record = Image(
        id=processing_id,
        original_filename="vehicle.png",
        stored_filename=stored.name,
        storage_path=str(stored),
        mime_type="image/png",
        file_size=size,
        width=width,
        height=height,
        status=ProcessingStatus.PENDING.value,
    )
    db_session.add(record)
    db_session.commit()
    return record


def test_worker_successful_processing(db_session, tmp_path):
    record = _insert_image(db_session, tmp_path)
    _process_with_session(db_session, record.id)

    db_session.refresh(record)
    assert record.status == ProcessingStatus.COMPLETED.value
    assert record.failure_reason is None
    assert record.perceptual_hash

    analysis = db_session.query(AnalysisResult).filter_by(image_id=record.id).one()
    assert analysis.blur_result is not None
    assert analysis.brightness_result is not None
    assert analysis.duplicate_result is not None
    assert analysis.ocr_result is not None
    assert analysis.vehicle_number_result is not None


def test_worker_failed_processing_missing_file_without_api_fallback(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_API_BASE_URL", "")
    record = _insert_image(db_session, tmp_path, missing_file=True)
    try:
        _process_with_session(db_session, record.id)
    except NonRetryableProcessingError:
        pass

    db_session.refresh(record)
    assert record.status == ProcessingStatus.FAILED.value
    assert record.failure_reason
    assert "missing" in record.failure_reason.lower()


def test_worker_downloads_missing_local_file_from_api(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_API_BASE_URL", "http://api.test")
    monkeypatch.setattr(settings, "WORKER_TEMP_PATH", str(tmp_path / "worker-temp"))
    record = _insert_image(db_session, tmp_path, missing_file=True)

    class FakeResponse:
        status_code = 200
        content = png_bytes()

    with patch(
        "app.services.image_access_service.httpx.Client.get",
        return_value=FakeResponse(),
    ) as mock_get:
        _process_with_session(db_session, record.id)
        mock_get.assert_called_once_with(
            f"http://api.test/api/v1/images/{record.id}/file"
        )

    db_session.refresh(record)
    assert record.status == ProcessingStatus.COMPLETED.value
    temp_file = tmp_path / "worker-temp" / record.stored_filename
    assert not temp_file.exists()


def test_worker_download_not_found_is_non_retryable(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_API_BASE_URL", "http://api.test")
    monkeypatch.setattr(settings, "WORKER_TEMP_PATH", str(tmp_path / "worker-temp"))
    record = _insert_image(db_session, tmp_path, missing_file=True)

    class FakeResponse:
        status_code = 404
        content = b""

    with patch("app.services.image_access_service.httpx.Client.get", return_value=FakeResponse()):
        with pytest.raises(NonRetryableProcessingError):
            _process_with_session(db_session, record.id)

    db_session.refresh(record)
    assert record.status == ProcessingStatus.FAILED.value
    assert "not found" in record.failure_reason.lower()


def test_worker_download_timeout_is_retryable(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_API_BASE_URL", "http://api.test")
    monkeypatch.setattr(settings, "WORKER_TEMP_PATH", str(tmp_path / "worker-temp"))
    record = _insert_image(db_session, tmp_path, missing_file=True)

    with patch(
        "app.services.image_access_service.httpx.Client.get",
        side_effect=httpx.TimeoutException("timed out"),
    ):
        with pytest.raises(RetryableProcessingError):
            _process_with_session(db_session, record.id)

    db_session.refresh(record)
    assert record.status == ProcessingStatus.PROCESSING.value


def test_worker_download_connection_error_is_retryable(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_API_BASE_URL", "http://api.test")
    monkeypatch.setattr(settings, "WORKER_TEMP_PATH", str(tmp_path / "worker-temp"))
    record = _insert_image(db_session, tmp_path, missing_file=True)

    with patch(
        "app.services.image_access_service.httpx.Client.get",
        side_effect=httpx.ConnectError("connection refused"),
    ):
        with pytest.raises(RetryableProcessingError):
            _process_with_session(db_session, record.id)

    db_session.refresh(record)
    assert record.status == ProcessingStatus.PROCESSING.value


def test_resolve_processing_image_path_cleans_up_temp_file(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_API_BASE_URL", "http://api.test")
    monkeypatch.setattr(settings, "WORKER_TEMP_PATH", str(tmp_path / "worker-temp"))
    record = _insert_image(db_session, tmp_path, missing_file=True)
    temp_file = tmp_path / "worker-temp" / record.stored_filename

    class FakeResponse:
        status_code = 200
        content = png_bytes()

    with patch("app.services.image_access_service.httpx.Client.get", return_value=FakeResponse()):
        with resolve_processing_image_path(record) as image_path:
            assert image_path.is_file()
            assert image_path == temp_file

    assert not temp_file.exists()
