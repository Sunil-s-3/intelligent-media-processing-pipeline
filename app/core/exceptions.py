"""Application-level exceptions mapped to HTTP responses.

Internal stack traces are logged server-side and never returned to API clients.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base error with a safe client-facing message."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ImageMissingError(AppError):
    status_code = 400
    error_code = "missing_file"


class ImageTooLargeError(AppError):
    status_code = 413
    error_code = "file_too_large"


class UnsupportedImageTypeError(AppError):
    status_code = 415
    error_code = "unsupported_media_type"


class CorruptImageError(AppError):
    status_code = 400
    error_code = "corrupt_image"


class ImageNotFoundError(AppError):
    status_code = 404
    error_code = "not_found"


class QueueUnavailableError(AppError):
    status_code = 503
    error_code = "queue_unavailable"


class DatabaseUnavailableError(AppError):
    status_code = 503
    error_code = "database_unavailable"


class ResultsNotReadyError(AppError):
    status_code = 202
    error_code = "results_not_ready"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, (StarletteHTTPException, RequestValidationError)):
            raise exc
        logger.exception("unhandled error path=%s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
            },
        )
