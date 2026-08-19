from unittest.mock import patch

import cv2
import numpy as np
from PIL import Image, ImageDraw

from app.analyzers.ocr import (
    analyze_ocr,
    detect_plate_region_boxes,
    _extract_plate_ocr,
)
from app.analyzers.plate_validator import validate_indian_plate
from app.core.config import settings
from tests.helpers import save_png, text_image


def _plate_scene(
    plate_text: str = "KA01AB1234",
    plate_color: tuple[int, int, int] = (255, 210, 0),
    plate_box: tuple[int, int, int, int] = (180, 430, 320, 52),
    canvas_size: tuple[int, int] = (720, 540),
) -> Image.Image:
    image = Image.new("RGB", canvas_size, (120, 120, 120))
    draw = ImageDraw.Draw(image)
    x, y, width, height = plate_box
    draw.rectangle([x, y, x + width, y + height], fill=plate_color, outline=(0, 0, 0), width=2)
    draw.text((x + 12, y + 10), plate_text, fill=(0, 0, 0))
    draw.text((40, 40), "Tuesday, 17 Feb 2026 11:22 AM", fill=(255, 255, 255))
    return image


def test_detect_plate_region_boxes_finds_yellow_plate(tmp_path):
    path = save_png(tmp_path / "yellow_plate.png", _plate_scene())
    image_bgr = cv2.imread(str(path))
    boxes = detect_plate_region_boxes(image_bgr)
    assert boxes
    best = boxes[0]
    x, y, width, height, score = best
    assert width > height
    assert score > 0


def test_detect_plate_region_boxes_finds_white_plate(tmp_path):
    path = save_png(
        tmp_path / "white_plate.png",
        _plate_scene(plate_color=(245, 245, 245), plate_box=(160, 420, 340, 50)),
    )
    image_bgr = cv2.imread(str(path))
    boxes = detect_plate_region_boxes(image_bgr)
    assert boxes


def test_extract_plate_ocr_returns_validated_plate_text(tmp_path):
    path = save_png(tmp_path / "plate_crop.png", _plate_scene())
    image_bgr = cv2.imread(str(path))

    def fake_run(image, psm):
        return "KA01AB1234", 88.0

    with patch("app.analyzers.ocr._run_plate_tesseract", side_effect=fake_run):
        result = _extract_plate_ocr(image_bgr)

    assert result["plate_ocr_text"] == "KA01AB1234"
    assert result["plate_ocr_confidence"] > 0
    assert result["candidate_count"] >= 1
    assert "KA01AB1234" in result["plate_candidates"]
    assert validate_indian_plate(result["plate_ocr_text"])["format_valid"] is True


def test_extract_plate_ocr_does_not_fabricate_from_date_text(tmp_path):
    path = save_png(tmp_path / "date_only.png", text_image("Tuesday, 17 Feb 2026 11:22 AM", size=(720, 540)))
    image_bgr = cv2.imread(str(path))

    def fake_run(image, psm):
        return "TUESDAY17FEB2026", 70.0

    with patch("app.analyzers.ocr._run_plate_tesseract", side_effect=fake_run):
        result = _extract_plate_ocr(image_bgr)

    assert result["plate_ocr_text"] is None
    assert validate_indian_plate("TUESDAY17FEB2026")["format_valid"] is False


def test_analyze_ocr_includes_plate_debug_fields(tmp_path):
    path = save_png(tmp_path / "scene.png", _plate_scene())
    fake_data = {"conf": ["90"], "text": ["Tuesday"]}
    plate_payload = {
        "plate_ocr_text": "KA01AB1234",
        "plate_ocr_confidence": 0.82,
        "plate_candidates": ["KA01AB1234"],
        "candidate_count": 2,
    }

    with patch("app.analyzers.ocr._tesseract_available", return_value=(True, None)):
        with patch("app.analyzers.ocr.pytesseract.image_to_data", return_value=fake_data):
            with patch("app.analyzers.ocr.pytesseract.image_to_string", return_value="Tuesday"):
                with patch("app.analyzers.ocr._extract_plate_ocr", return_value=plate_payload):
                    result = analyze_ocr(path)

    assert result["status"] == "completed"
    assert result["plate_ocr_text"] == "KA01AB1234"
    assert result["candidate_count"] == 2
    assert "plate-focused OCR" in result["reason"]


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
    empty_plate = {
        "plate_ocr_text": None,
        "plate_ocr_confidence": 0.0,
        "plate_candidates": [],
        "candidate_count": 0,
    }
    with patch("app.analyzers.ocr._tesseract_available", return_value=(True, None)):
        with patch("app.analyzers.ocr.pytesseract.image_to_data", return_value=fake_data):
            with patch("app.analyzers.ocr.pytesseract.image_to_string", return_value="   "):
                with patch("app.analyzers.ocr._extract_plate_ocr", return_value=empty_plate):
                    result = analyze_ocr(path)
    assert result["status"] == "completed"
    assert result["ocr_text"] is None
    assert "no readable" in result["reason"].lower()


def test_ocr_timeout_returns_failed_without_raising(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "OCR_TIMEOUT_SECONDS", 5)
    path = save_png(tmp_path / "scene.png", text_image("KA01AB1234"))

    with patch("app.analyzers.ocr._tesseract_available", return_value=(True, None)):
        with patch(
            "app.analyzers.ocr.pytesseract.image_to_data",
            side_effect=RuntimeError("Tesseract process timeout"),
        ):
            result = analyze_ocr(path)

    assert result["status"] == "failed"
    assert result["ocr_text"] is None
    assert "timed out" in result["reason"].lower()
