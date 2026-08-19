from app.db.models import ProcessingStatus
from app.services.processing_service import _process_with_session


def test_results_after_successful_processing(client, db_session, png_file):
    uploaded = client.post("/api/v1/images", files=png_file)
    processing_id = uploaded.json()["processing_id"]

    _process_with_session(db_session, processing_id)

    response = client.get(f"/api/v1/images/{processing_id}/results")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == ProcessingStatus.COMPLETED.value
    assert body["analysis"]["image_quality"]["blur"]["score"] is not None
    assert "issue" in body["analysis"]["image_quality"]["brightness"]
    assert "detected" in body["analysis"]["duplicate"]
    assert "format_valid" in body["analysis"]["vehicle_number"]
    assert body["analysis"]["ocr"]["status"] in {"completed", "unavailable", "failed"}


def test_failed_results_include_reason(client, db_session, png_file):
    uploaded = client.post("/api/v1/images", files=png_file)
    processing_id = uploaded.json()["processing_id"]

    from pathlib import Path

    from app.db.models import Image

    record = db_session.get(Image, processing_id)
    Path(record.storage_path).unlink()

    try:
        _process_with_session(db_session, processing_id)
    except Exception:
        pass

    status = client.get(f"/api/v1/images/{processing_id}/status")
    assert status.status_code == 200
    assert status.json()["status"] == "failed"
    assert status.json()["failure_reason"]

    results = client.get(f"/api/v1/images/{processing_id}/results")
    assert results.status_code == 200
    assert results.json()["status"] == "failed"
    assert results.json()["failure_reason"]
