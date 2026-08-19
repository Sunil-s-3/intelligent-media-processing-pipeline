"""Run the RQ worker with pipeline-specific failure handling."""

from __future__ import annotations

from redis import Redis

from app.core.config import settings
from app.workers.pipeline_worker import PipelineWorker


def main() -> None:
    connection = Redis.from_url(settings.REDIS_URL)
    worker = PipelineWorker([settings.RQ_QUEUE_NAME], connection=connection)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
