"""SQLAlchemy models.

processing_id is the images.id UUID stored as a 36-character string so the same
models work in PostgreSQL (production) and SQLite (tests).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

# JSONB in PostgreSQL, generic JSON elsewhere (SQLite in tests).
JSONType = JSON().with_variant(JSONB(), "postgresql")


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Image(Base):
    __tablename__ = "images"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    perceptual_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProcessingStatus.PENDING.value,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    analysis: Mapped[AnalysisResult | None] = relationship(
        back_populates="image",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_images_status", "status"),
        Index("ix_images_perceptual_hash", "perceptual_hash"),
        Index("ix_images_created_at", "created_at"),
        Index("ix_images_status_created_at", "status", "created_at"),
    )


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    image_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("images.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    blur_result: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    brightness_result: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    duplicate_result: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    ocr_result: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    vehicle_number_result: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    screenshot_result: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    image: Mapped[Image] = relationship(back_populates="analysis")
