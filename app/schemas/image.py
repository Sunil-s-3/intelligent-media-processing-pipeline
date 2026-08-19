"""Pydantic schemas for image upload, status, and results APIs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"


class UploadAcceptedResponse(BaseModel):
    processing_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    processing_id: str
    status: str
    failure_reason: str | None = None


class ImageQualityResult(BaseModel):
    blur: dict[str, Any]
    brightness: dict[str, Any]


class AnalysisPayload(BaseModel):
    image_quality: ImageQualityResult
    duplicate: dict[str, Any]
    ocr: dict[str, Any]
    vehicle_number: dict[str, Any]
    screenshot: dict[str, Any] | None = None


class ResultsResponse(BaseModel):
    processing_id: str
    status: str
    analysis: AnalysisPayload | None = None
    failure_reason: str | None = None
    message: str | None = None


class ErrorResponse(BaseModel):
    error: str
    message: str
