"""Background image-processing orchestration.

Analyzer failures are isolated: OCR/screenshot issues do not fail the job.
Unrecoverable errors (missing file, decode failure) mark the image as failed.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.analyzers.blur import analyze_blur
from app.analyzers.brightness import analyze_brightness
from app.analyzers.duplicate import analyze_duplicate, compute_phash
from app.analyzers.ocr import analyze_ocr
from app.analyzers.plate_validator import validate_indian_plate
from app.analyzers.screenshot import analyze_screenshot
from app.db.database import SessionLocal
from app.db.models import AnalysisResult, Image, ProcessingStatus
from app.services.image_access_service import (
    ImageDownloadNotFoundError,
    ImageDownloadTransientError,
    ImageFileMissingError,
    resolve_processing_image_path,
)

logger = logging.getLogger(__name__)


class NonRetryableProcessingError(Exception):
    """Invalid image / missing file — do not retry the RQ job."""


class RetryableProcessingError(Exception):
    """Transient infrastructure failure — RQ may retry."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _mark_failed(db: Session, image: Image, reason: str) -> None:
    image.status = ProcessingStatus.FAILED.value
    image.failure_reason = reason
    image.updated_at = _utcnow()
    db.commit()
    logger.error(
        "job failed reason=%s",
        reason,
        extra={"processing_id": image.id},
    )


def _run_analyzer(name: str, processing_id: str, func, *args, **kwargs) -> dict:
    logger.info("analyzer started name=%s", name, extra={"processing_id": processing_id})
    try:
        result = func(*args, **kwargs)
        logger.info(
            "analyzer completed name=%s",
            name,
            extra={"processing_id": processing_id},
        )
        return result
    except Exception as exc:
        logger.exception(
            "analyzer failed name=%s error=%s",
            name,
            exc,
            extra={"processing_id": processing_id},
        )
        return {
            "status": "failed",
            "detected": None,
            "confidence": 0.0,
            "reason": f"{name} analyzer failed: {exc}",
        }


def process_image(processing_id: str) -> None:
    """RQ entry-point compatible function. Opens its own DB session."""
    db = SessionLocal()
    try:
        _process_with_session(db, processing_id)
    finally:
        db.close()


def _process_with_session(db: Session, processing_id: str) -> None:
    logger.info("job started", extra={"processing_id": processing_id})

    image = db.get(Image, processing_id)
    if image is None:
        raise NonRetryableProcessingError(f"Unknown processing_id {processing_id}")

    image.status = ProcessingStatus.PROCESSING.value
    image.failure_reason = None
    image.updated_at = _utcnow()
    db.commit()

    try:
        with resolve_processing_image_path(image) as stored:
            blur = _run_analyzer("blur", processing_id, analyze_blur, stored)
            brightness = _run_analyzer("brightness", processing_id, analyze_brightness, stored)
            screenshot = _run_analyzer("screenshot", processing_id, analyze_screenshot, stored)

            try:
                phash = compute_phash(stored)
            except Exception as exc:
                _mark_failed(db, image, f"Unable to decode image for hashing: {exc}")
                raise NonRetryableProcessingError("Unable to decode image") from exc

            image.perceptual_hash = phash
            db.commit()

            duplicate = _run_analyzer(
                "duplicate",
                processing_id,
                analyze_duplicate,
                stored,
                image_id=processing_id,
                db=db,
            )
            ocr = _run_analyzer("ocr", processing_id, analyze_ocr, stored)
            plate = validate_indian_plate(ocr.get("cleaned_text") or ocr.get("ocr_text"))
            if not plate.get("format_valid") and ocr.get("plate_ocr_text"):
                plate_from_region = validate_indian_plate(ocr.get("plate_ocr_text"))
                if plate_from_region.get("format_valid"):
                    plate = plate_from_region

            if image.analysis is None:
                result = AnalysisResult(
                    image_id=image.id,
                    blur_result=blur,
                    brightness_result=brightness,
                    duplicate_result=duplicate,
                    ocr_result=ocr,
                    vehicle_number_result=plate,
                    screenshot_result=screenshot,
                )
                db.add(result)
            else:
                image.analysis.blur_result = blur
                image.analysis.brightness_result = brightness
                image.analysis.duplicate_result = duplicate
                image.analysis.ocr_result = ocr
                image.analysis.vehicle_number_result = plate
                image.analysis.screenshot_result = screenshot

            image.status = ProcessingStatus.COMPLETED.value
            image.failure_reason = None
            image.updated_at = _utcnow()
            db.commit()
            logger.info("job completed", extra={"processing_id": processing_id})
    except ImageDownloadTransientError as exc:
        logger.warning(
            "temporary image download failure error=%s",
            exc,
            extra={"processing_id": processing_id},
        )
        raise RetryableProcessingError(str(exc)) from exc
    except (ImageFileMissingError, ImageDownloadNotFoundError) as exc:
        _mark_failed(db, image, str(exc))
        raise NonRetryableProcessingError(str(exc)) from exc
    except NonRetryableProcessingError:
        raise
    except Exception as exc:
        logger.exception(
            "unexpected processing error",
            extra={"processing_id": processing_id},
        )
        # Distinguish likely infrastructure vs image problems.
        message = str(exc).lower()
        retryable = any(
            token in message
            for token in ("connection", "timeout", "temporarily", "redis", "could not connect")
        )
        _mark_failed(db, image, f"Processing failed: {exc}")
        if retryable:
            raise RetryableProcessingError(str(exc)) from exc
        raise NonRetryableProcessingError(str(exc)) from exc
