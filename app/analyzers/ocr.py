"""OCR extraction via Tesseract (pytesseract).

Full-image OCR captures general text in the frame. A second plate-focused pass
locates likely registration-plate regions, upscales and preprocesses them, and
runs Tesseract with plate-oriented settings. Results always represent uncertainty
explicitly and never fabricate plate text.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image as PILImage

from app.analyzers.common import clamp_confidence, load_bgr
from app.analyzers.plate_validator import validate_indian_plate

logger = logging.getLogger(__name__)

_PLATE_WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_PLATE_PSM_MODES = (7, 8)
_UPSCALE_FACTOR = 4
_MIN_ASPECT = 2.0
_MAX_ASPECT = 7.0
_MIN_AREA_RATIO = 0.0005
_MAX_AREA_RATIO = 0.20
_MAX_REGIONS = 10


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


def _boxes_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    overlap_w = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    overlap_h = max(0, min(ay + ah, by + bh) - max(ay, by))
    overlap_area = overlap_w * overlap_h
    if overlap_area == 0:
        return False
    smaller = min(aw * ah, bw * bh)
    return overlap_area / smaller > 0.35


def _score_box(width: int, height: int, area: int, img_area: int, priority: float) -> float:
    aspect = width / max(height, 1)
    aspect_score = 1.0 - min(abs(aspect - 4.5) / 4.5, 1.0)
    area_score = min(area / max(img_area * 0.05, 1), 1.0)
    return (aspect_score * 0.6 + area_score * 0.4) * priority


def _collect_boxes_from_mask(
    mask: np.ndarray,
    img_area: int,
    priority: float,
) -> list[tuple[int, int, int, int, float]]:
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes: list[tuple[int, int, int, int, float]] = []
    min_area = img_area * _MIN_AREA_RATIO
    max_area = img_area * _MAX_AREA_RATIO

    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        area = width * height
        if area < min_area or area > max_area:
            continue
        aspect = width / max(height, 1)
        if aspect < _MIN_ASPECT or aspect > _MAX_ASPECT:
            continue
        rect_area = width * height
        contour_area = cv2.contourArea(contour)
        if rect_area <= 0 or contour_area / rect_area < 0.45:
            continue
        score = _score_box(width, height, area, img_area, priority)
        boxes.append((x, y, width, height, score))

    return boxes


def detect_plate_region_boxes(image_bgr: np.ndarray) -> list[tuple[int, int, int, int, float]]:
    """Return likely plate bounding boxes sorted by heuristic score (highest first)."""
    height, width = image_bgr.shape[:2]
    img_area = height * width
    candidates: list[tuple[int, int, int, int, float]] = []

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)

    yellow_mask = cv2.inRange(hsv, np.array([15, 70, 70]), np.array([40, 255, 255]))
    candidates.extend(_collect_boxes_from_mask(yellow_mask, img_area, priority=2.0))

    white_mask = cv2.inRange(hsv, np.array([0, 0, 170]), np.array([180, 70, 255]))
    candidates.extend(_collect_boxes_from_mask(white_mask, img_area, priority=1.2))

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 140)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=1)
    candidates.extend(_collect_boxes_from_mask(edges, img_area, priority=0.8))

    candidates.sort(key=lambda item: item[4], reverse=True)

    selected: list[tuple[int, int, int, int, float]] = []
    for candidate in candidates:
        box = candidate[:4]
        if any(_boxes_overlap(box, existing[:4]) for existing in selected):
            continue
        selected.append(candidate)
        if len(selected) >= _MAX_REGIONS:
            break

    return selected


def _preprocess_plate_variants(crop_bgr: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    variants = [enhanced]

    _, otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(otsu)

    adaptive = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2,
    )
    variants.append(adaptive)

    sharpen_kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    variants.append(cv2.filter2D(enhanced, -1, sharpen_kernel))

    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    yellow_mask = cv2.inRange(hsv, np.array([15, 70, 70]), np.array([40, 255, 255]))
    yellow_only = cv2.bitwise_and(enhanced, enhanced, mask=yellow_mask)
    variants.append(yellow_only)

    return variants


def _upscale(image: np.ndarray, factor: int = _UPSCALE_FACTOR) -> np.ndarray:
    return cv2.resize(
        image,
        None,
        fx=factor,
        fy=factor,
        interpolation=cv2.INTER_CUBIC,
    )


def _ocr_confidence_from_data(data: dict) -> float:
    confidences: list[float] = []
    for conf, text in zip(data.get("conf", []), data.get("text", []), strict=False):
        try:
            conf_val = float(conf)
        except (TypeError, ValueError):
            continue
        if text and text.strip() and conf_val >= 0:
            confidences.append(conf_val)
    if not confidences:
        return 0.0
    return clamp_confidence(sum(confidences) / len(confidences) / 100.0)


def _run_plate_tesseract(image: np.ndarray, psm: int) -> tuple[str, float]:
    if image.ndim == 2:
        pil_image = PILImage.fromarray(image)
    else:
        pil_image = PILImage.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    config = (
        f"--oem 3 --psm {psm} "
        f"-c tessedit_char_whitelist={_PLATE_WHITELIST}"
    )
    raw_text = pytesseract.image_to_string(pil_image, config=config)
    data = pytesseract.image_to_data(pil_image, config=config, output_type=pytesseract.Output.DICT)
    cleaned = _clean_text(raw_text)
    confidence = _ocr_confidence_from_data(data)
    return cleaned, confidence


def _extract_plate_ocr(image_bgr: np.ndarray) -> dict:
    regions = detect_plate_region_boxes(image_bgr)
    ocr_attempts: list[tuple[str, float]] = []

    for x, y, width, height, _score in regions:
        pad_x = max(2, int(width * 0.05))
        pad_y = max(2, int(height * 0.10))
        x0 = max(0, x - pad_x)
        y0 = max(0, y - pad_y)
        x1 = min(image_bgr.shape[1], x + width + pad_x)
        y1 = min(image_bgr.shape[0], y + height + pad_y)
        crop = image_bgr[y0:y1, x0:x1]
        if crop.size == 0:
            continue

        upscaled = _upscale(crop)
        for variant in _preprocess_plate_variants(upscaled):
            if variant.size == 0:
                continue
            for psm in _PLATE_PSM_MODES:
                try:
                    text, confidence = _run_plate_tesseract(variant, psm)
                except Exception as exc:
                    logger.debug("plate OCR attempt failed: %s", exc)
                    continue
                if text:
                    ocr_attempts.append((text, confidence))

    candidate_texts = [text for text, _confidence in ocr_attempts]
    unique_candidates: list[str] = []
    seen: set[str] = set()
    for text in candidate_texts:
        key = text.upper()
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(text)

    best_valid_text: str | None = None
    best_valid_confidence = 0.0
    for text, confidence in ocr_attempts:
        validation = validate_indian_plate(text)
        if validation.get("format_valid"):
            if confidence >= best_valid_confidence:
                best_valid_text = text
                best_valid_confidence = confidence

    return {
        "plate_ocr_text": best_valid_text,
        "plate_ocr_confidence": best_valid_confidence if best_valid_text else 0.0,
        "plate_candidates": unique_candidates[:20],
        "candidate_count": len(regions),
    }


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

    plate_fields = {
        "plate_ocr_text": None,
        "plate_ocr_confidence": 0.0,
        "plate_candidates": [],
        "candidate_count": 0,
    }
    try:
        image_bgr = load_bgr(image_path)
        plate_fields = _extract_plate_ocr(image_bgr)
    except Exception as exc:
        logger.warning("plate-focused OCR failed: %s", exc)

    full_image_valid = validate_indian_plate(cleaned or raw_text.strip() or None)
    plate_focus_valid = (
        validate_indian_plate(plate_fields["plate_ocr_text"])
        if plate_fields["plate_ocr_text"]
        else {"format_valid": False}
    )

    if not cleaned:
        if plate_focus_valid.get("format_valid"):
            reason = (
                "Full-image OCR found no readable text, but plate-focused OCR "
                "extracted a candidate matching an Indian registration pattern"
            )
        elif plate_fields["candidate_count"] > 0:
            reason = (
                "Full-image OCR found no readable text; plate-focused OCR "
                "examined likely plate regions but no valid registration pattern was found"
            )
        else:
            reason = "No readable vehicle registration text detected"
        return {
            "status": "completed",
            "ocr_text": None,
            "cleaned_text": None,
            "confidence": 0.0,
            **plate_fields,
            "reason": reason,
        }

    if plate_focus_valid.get("format_valid") and not full_image_valid.get("format_valid"):
        reason = (
            "Tesseract extracted text from the full image; plate-focused OCR "
            "found a candidate matching an Indian registration pattern in a "
            "likely plate region"
        )
    elif full_image_valid.get("format_valid"):
        reason = (
            "Tesseract extracted text; confidence is the mean of per-word "
            "Tesseract scores (0-1 heuristic scale), not a guarantee the text "
            "is a number plate"
        )
    else:
        reason = (
            "Tesseract extracted text from the full image; plate-focused OCR "
            "did not find a valid Indian registration pattern in likely plate regions"
        )

    return {
        "status": "completed",
        "ocr_text": raw_text.strip() or None,
        "cleaned_text": cleaned,
        "confidence": clamp_confidence(mean_conf),
        "word_count": len(confidences),
        **plate_fields,
        "reason": reason,
    }
