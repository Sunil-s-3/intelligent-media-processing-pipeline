from unittest.mock import patch

from app.analyzers.ocr import analyze_ocr
from tests.helpers import save_png, text_image


def test_ocr_unavailable_does_not_raise(tmp_path):
    path = save_png(tmp_path / "plate.png", text_image("KA01AB1234"))
    with patch("app.analyzers.ocr._tesseract_available", return_value=(False, "missing binary")):
        result = analyze_ocr(path)
    assert result["status"] == "unavailable"
    assert result["ocr_text"] is None
    assert result["confidence"] == 0.0


def test_ocr_empty_text_is_completed_without_fabrication(tmp_path):
    path = save_png(tmp_path / "blank.png", text_image(""))
    fake_data = {"conf": ["-1"], "text": [""]}
    with patch("app.analyzers.ocr._tesseract_available", return_value=(True, None)):
        with patch("app.analyzers.ocr.pytesseract.image_to_data", return_value=fake_data):
            with patch("app.analyzers.ocr.pytesseract.image_to_string", return_value="   "):
                result = analyze_ocr(path)
    assert result["status"] == "completed"
    assert result["ocr_text"] is None
    assert "no readable" in result["reason"].lower()
