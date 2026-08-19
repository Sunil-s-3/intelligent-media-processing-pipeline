"""RQ job helpers.

Retry trade-off
---------------
RQ retries transient enqueue/worker crashes a small number of times. Invalid
images are marked failed inside the job and are not retried (the worker catches
NonRetryableProcessingError and returns). Endless retries are avoided with
JOB_RETRY_MAX (default 2).
"""

from __future__ import annotations

import logging

from redis import Redis
from rq import Queue, Retry

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_queue() -> Queue:
    connection = Redis.from_url(settings.REDIS_URL)
    return Queue(settings.RQ_QUEUE_NAME, connection=connection)


def enqueue_image_job(processing_id: str) -> str:
    queue = get_queue()
    retry = Retry(max=settings.JOB_RETRY_MAX, interval=[10, 30])
    job = queue.enqueue(
        "app.queue.jobs.process_image_job",
        processing_id,
        job_timeout=settings.JOB_TIMEOUT_SECONDS,
        retry=retry,
        result_ttl=86400,
        failure_ttl=86400,
    )
    logger.info(
        "job enqueued rq_job_id=%s",
        job.id,
        extra={"processing_id": processing_id},
    )
    return job.id


def process_image_job(processing_id: str) -> str:
    """RQ target. Import is deferred so the worker process loads app code once."""
    from app.services.processing_service import (
        NonRetryableProcessingError,
        RetryableProcessingError,
        process_image,
    )

    try:
        process_image(processing_id)
        return processing_id
    except NonRetryableProcessingError as exc:
        logger.error(
            "job not retried (non-retryable) error=%s",
            exc,
            extra={"processing_id": processing_id},
        )
        return processing_id
    except RetryableProcessingError:
        logger.warning(
            "job will be retried if attempts remain",
            extra={"processing_id": processing_id},
        )
        raise
