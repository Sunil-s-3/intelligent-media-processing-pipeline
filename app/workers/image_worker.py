"""Background worker notes.

The API process and the worker process share this codebase but run separately:

    rq worker image_jobs --url "$REDIS_URL"

`process_image_job` in app.queue.jobs is the RQ target. This module exists so
the worker role is explicit in the project layout.
"""

from app.queue.jobs import process_image_job

__all__ = ["process_image_job"]
