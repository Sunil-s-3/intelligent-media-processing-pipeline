"""Pytest fixtures. API tests use SQLite and a mocked RQ enqueue."""

from __future__ import annotations

from collections.abc import Generator
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.database import Base, get_db
from app.db.models import Image  # noqa: F401 — register metadata
from app.main import app
from tests.helpers import png_bytes


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionTesting = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionTesting()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session: Session, tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1.0)

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    from unittest.mock import patch

    with patch("app.services.upload_service.enqueue_image_job", return_value="job-test"):
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def png_file() -> dict:
    return {"image": ("vehicle.png", BytesIO(png_bytes()), "image/png")}
