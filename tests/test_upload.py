from io import BytesIO

from tests.helpers import png_bytes


def test_upload_valid_image_returns_202(client, png_file, db_session):
    response = client.post("/api/v1/images", files=png_file)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert body["message"] == "Image accepted for processing"
    assert body["processing_id"]


def test_upload_missing_file_rejected(client):
    response = client.post("/api/v1/images")
    assert response.status_code == 400
    assert response.json()["error"] == "missing_file"


def test_upload_unsupported_file_rejected(client):
    files = {"image": ("notes.txt", BytesIO(b"not an image"), "text/plain")}
    response = client.post("/api/v1/images", files=files)
    assert response.status_code == 400
    assert response.json()["error"] == "corrupt_image"


def test_upload_gif_rejected_as_unsupported(client):
    gif = (
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
        b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
        b"\x00\x00\x02\x02D\x01\x00;"
    )
    files = {"image": ("screen.gif", BytesIO(gif), "image/gif")}
    response = client.post("/api/v1/images", files=files)
    assert response.status_code == 415
    assert response.json()["error"] == "unsupported_media_type"


def test_upload_oversized_file_rejected(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 0.0001)
    huge = png_bytes(size=(64, 64))
    files = {"image": ("big.png", BytesIO(huge), "image/png")}
    response = client.post("/api/v1/images", files=files)
    assert response.status_code == 413
    assert response.json()["error"] == "file_too_large"


def test_upload_corrupt_image_rejected(client):
    files = {"image": ("broken.jpg", BytesIO(b"\xff\xd8\xff not a jpeg"), "image/jpeg")}
    response = client.post("/api/v1/images", files=files)
    assert response.status_code == 400
    assert response.json()["error"] == "corrupt_image"
