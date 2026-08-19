"""OCR extraction via Tesseract (pytesseract).

OCR failure or empty text does **not** fail the overall processing job.
Results always represent uncertainty explicitly and never fabricate plate text.
"""

from __future__ import annotations

from pathlib import Path

import pytesseract
from PIL import Image as PILImage

from app.analyzers.common import clamp_confidence


def _tesseract_available() -> tuple[bool, str | None]:
    try:
        pytesseract.get_tesseract_version()
        return True, None
    except pytesseract.TesseractNotFoundError as exc:
        return False, str(exc)
    except Exception as exc:  # pragma: no cover - unexpected Tesseract probe errors
        return False, str(exc)


def _clean_text(text: str) -> str:
    compact = " ".join(text.split())
    return compact.strip()


def analyze_ocr(image_path: Path) -> dict:
    available, availability_error = _tesseract_available()
    if not available:
        return {
            "status": "unavailable",
            "ocr_text": None,
            "cleaned_text": None,
            "confidence": 0.0,
            "reason": (
                "Tesseract OCR is not available on this host. "
                f"Detail: {availability_error}"
            ),
        }

    try:
        with PILImage.open(image_path) as img:
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            raw_text = pytesseract.image_to_string(img)
    except pytesseract.TesseractNotFoundError as exc:
        return {
            "status": "unavailable",
            "ocr_text": None,
            "cleaned_text": None,
            "confidence": 0.0,
            "reason": f"Tesseract OCR became unavailable during extraction: {exc}",
        }
    except Exception as exc:
        return {
            "status": "failed",
            "ocr_text": None,
            "cleaned_text": None,
            "confidence": 0.0,
            "reason": f"OCR extraction failed: {exc}",
        }

    cleaned = _clean_text(raw_text)
    confidences: list[float] = []
    for conf, text in zip(data.get("conf", []), data.get("text", []), strict=False):
        try:
            conf_val = float(conf)
        except (TypeError, ValueError):
            continue
        if text and text.strip() and conf_val >= 0:
            confidences.append(conf_val)

    mean_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0

    if not cleaned:
        return {
            "status": "completed",
            "ocr_text": None,
            "cleaned_text": None,
            "confidence": 0.0,
            "reason": "No readable vehicle registration text detected",
        }

    return {
        "status": "completed",
        "ocr_text": raw_text.strip() or None,
        "cleaned_text": cleaned,
        "confidence": clamp_confidence(mean_conf),
        "word_count": len(confidences),
        "reason": (
            "Tesseract extracted text; confidence is the mean of per-word "
            "Tesseract scores (0-1 heuristic scale), not a guarantee the text "
            "is a number plate"
        ),
    }
