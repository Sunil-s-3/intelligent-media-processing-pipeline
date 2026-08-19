"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, images
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.services.storage_service import ensure_storage_dir

setup_logging(settings.LOG_LEVEL)
ensure_storage_dir()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Asynchronous vehicle-image processing pipeline. "
        "Upload returns immediately; analysis runs in a background worker."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(health.router, prefix="/api/v1")
app.include_router(images.router, prefix="/api/v1")
