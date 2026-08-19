"""Centralized application configuration.

All analyzer thresholds live here (or in environment variables) so they are not
scattered through analyzer modules. Values are heuristics for a take-home
assignment, not scientifically calibrated ML thresholds.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and optional .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Intelligent Media Processing Pipeline"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "postgresql+psycopg2://app:app@localhost:5432/media_pipeline"
    REDIS_URL: str = "redis://localhost:6379/0"
    RQ_QUEUE_NAME: str = "image_jobs"

    STORAGE_PATH: str = "./storage/original"

    MAX_UPLOAD_SIZE_MB: float = 10.0

    # Laplacian variance below this is treated as possibly blurry.
    BLUR_THRESHOLD: float = 100.0

    # Mean grayscale pixel value (0-255) below this is treated as low-light.
    BRIGHTNESS_THRESHOLD: float = 50.0

    # pHash Hamming distance at or below this is treated as a near-duplicate.
    DUPLICATE_HASH_DISTANCE: int = 5

    JOB_TIMEOUT_SECONDS: int = 300
    JOB_RETRY_MAX: int = 2

    # Base URL of the API service, used by workers to download uploaded images
    # when local storage is not shared (e.g. separate Render services).
    INTERNAL_API_BASE_URL: str = ""
    IMAGE_DOWNLOAD_TIMEOUT_SECONDS: int = 60
    WORKER_TEMP_PATH: str = "/tmp/media_pipeline_worker"

    ALLOWED_IMAGE_FORMATS: set[str] = {"JPEG", "PNG", "WEBP", "BMP", "TIFF"}

    # Comma-separated browser origins allowed to call the API (CORS).
    FRONTEND_ORIGINS: str = (
        "https://intelligent-media-processing-pipeline-oido.onrender.com,"
        "http://localhost:5173,"
        "http://localhost:5174"
    )

    @property
    def max_upload_bytes(self) -> int:
        return int(self.MAX_UPLOAD_SIZE_MB * 1024 * 1024)

    @property
    def storage_dir(self) -> Path:
        return Path(self.STORAGE_PATH).resolve()

    @property
    def frontend_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.FRONTEND_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def internal_api_base_url(self) -> str | None:
        value = self.INTERNAL_API_BASE_URL.strip().rstrip("/")
        return value or None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
