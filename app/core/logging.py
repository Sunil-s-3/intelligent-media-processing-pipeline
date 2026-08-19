"""Application logging.

Uses a simple, grep-friendly format with an optional processing_id field so a
single job can be traced from upload through worker completion.
"""

from __future__ import annotations

import logging
import sys


class ProcessingIdFilter(logging.Filter):
    """Ensure every log record has processing_id, defaulting to '-'."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "processing_id"):
            record.processing_id = "-"
        return True


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ProcessingIdFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s processing_id=%(processing_id)s "
            "[%(name)s] %(message)s"
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Keep third-party libraries quieter in normal operation.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
