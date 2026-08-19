"""Image query helpers used by status/results routes."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import ImageNotFoundError, ResultsNotReadyError
from app.db.models import Image, ProcessingStatus


def get_image_or_404(db: Session, processing_id: str) -> Image:
    image = db.get(Image, processing_id)
    if image is None:
        raise ImageNotFoundError(f"No image found for processing_id {processing_id}")
    return image


def build_results_payload(image: Image) -> dict:
    status = image.status

    if status in {ProcessingStatus.PENDING.value, ProcessingStatus.PROCESSING.value}:
        raise ResultsNotReadyError(
            f"Analysis is not ready yet (status={status})"
        )

    if status == ProcessingStatus.FAILED.value:
        return {
            "processing_id": image.id,
            "status": status,
            "analysis": None,
            "failure_reason": image.failure_reason or "Processing failed",
            "message": "Image processing failed. See failure_reason.",
        }

    analysis_row = image.analysis
    if analysis_row is None:
        return {
            "processing_id": image.id,
            "status": status,
            "analysis": None,
            "failure_reason": "Completed without stored analysis results",
            "message": "Processing finished but analysis rows are missing",
        }

    return {
        "processing_id": image.id,
        "status": status,
        "analysis": {
            "image_quality": {
                "blur": analysis_row.blur_result or {},
                "brightness": analysis_row.brightness_result or {},
            },
            "duplicate": analysis_row.duplicate_result or {},
            "ocr": analysis_row.ocr_result or {},
            "vehicle_number": analysis_row.vehicle_number_result or {},
            "screenshot": analysis_row.screenshot_result,
        },
        "failure_reason": None,
        "message": None,
    }
