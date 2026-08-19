import uuid

import httpx
import pytest

from app.db.models import Image, ProcessingStatus
from app.services.image_access_service import get_api_stored_image_path
from tests.helpers import png_bytes, save_png, text_image


def test_download_image_file_success(client, db_session, tmp_path, png_file):
    uploaded = client.post("/api/v1/images", files=png_file)
    assert uploaded.status_code == 202
    processing_id = uploaded.json()["processing_id"]

    response = client.get(f"/api/v1/images/{processing_id}/file")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")
    assert response.content == png_bytes()


def test_download_image_file_unknown_processing_id(client):
    response = client.get(
        "/api/v1/images/00000000-0000-0000-0000-000000000000/file"
    )
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_download_image_file_missing_on_disk(client, db_session, tmp_path):
    processing_id = str(uuid.uuid4())
    stored = tmp_path / f"{processing_id}.png"
    record = Image(
        id=processing_id,
        original_filename="vehicle.png",
        stored_filename=stored.name,
        storage_path=str(stored),
        mime_type="image/png",
        file_size=123,
        width=64,
        height=64,
        status=ProcessingStatus.PENDING.value,
    )
    db_session.add(record)
    db_session.commit()

    response = client.get(f"/api/v1/images/{processing_id}/file")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_get_api_stored_image_path_rejects_unsafe_filename(db_session, tmp_path):
    processing_id = str(uuid.uuid4())
    stored = save_png(tmp_path / f"{processing_id}.png", text_image("KA01AB1234"))
    record = Image(
        id=processing_id,
        original_filename="vehicle.png",
        stored_filename="../escape.png",
        storage_path=str(stored),
        mime_type="image/png",
        file_size=stored.stat().st_size,
        width=64,
        height=64,
        status=ProcessingStatus.PENDING.value,
    )

    with pytest.raises(Exception) as exc_info:
        get_api_stored_image_path(record)

    assert exc_info.value.status_code == 404
