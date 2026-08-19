"""Analysis-related schema helpers (kept small; JSON payloads are flexible)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AnalyzerResult(BaseModel):
    """Base shape shared by analyzers. Extra keys are allowed."""

    confidence: float
    reason: str

    model_config = {"extra": "allow"}


class BlurResult(AnalyzerResult):
    detected: bool
    score: float


class BrightnessResult(AnalyzerResult):
    issue: bool
    average_brightness: float


class DuplicateResult(AnalyzerResult):
    detected: bool
    matched_image_id: str | None = None
    similarity: float | None = None
    hamming_distance: int | None = None


class OcrResult(AnalyzerResult):
    status: str
    ocr_text: str | None = None
    cleaned_text: str | None = None


class VehicleNumberResult(AnalyzerResult):
    ocr_text: str | None = None
    format_valid: bool
    matched_pattern: str | None = None


def as_dict(model: BaseModel) -> dict[str, Any]:
    return model.model_dump()
