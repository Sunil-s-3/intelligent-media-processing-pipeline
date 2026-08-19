import uuid

from app.db.models import AnalysisResult, Image, ProcessingStatus
from app.services.processing_service import NonRetryableProcessingError, _process_with_session
from tests.helpers import noisy_image, save_png, png_bytes


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


def test_worker_failed_processing_missing_file(db_session, tmp_path):
    record = _insert_image(db_session, tmp_path, missing_file=True)
    try:
        _process_with_session(db_session, record.id)
    except NonRetryableProcessingError:
        pass

    db_session.refresh(record)
    assert record.status == ProcessingStatus.FAILED.value
    assert record.failure_reason
    assert "missing" in record.failure_reason.lower()
