"""RQ worker with pipeline-specific failure handling."""

from __future__ import annotations

import logging

from rq.worker import Worker

from app.services.processing_service import mark_processing_failed

logger = logging.getLogger(__name__)


class PipelineWorker(Worker):
    """Mark processing records failed when the work horse dies unexpectedly."""

    def handle_work_horse_killed(self, job, retpid, ret_val, rusage):  # noqa: ARG002
        super().handle_work_horse_killed(job, retpid, ret_val, rusage)
        self._mark_failed_job(
            job,
            "Worker process terminated unexpectedly (likely out of memory)",
        )

    def _mark_failed_job(self, job, reason: str) -> None:
        if job is None or not job.args:
            return
        func_name = job.func_name or ""
        if not func_name.endswith("process_image_job"):
            return
        processing_id = str(job.args[0])
        logger.error(
            "marking processing failed after worker failure reason=%s",
            reason,
            extra={"processing_id": processing_id},
        )
        mark_processing_failed(processing_id, reason)
