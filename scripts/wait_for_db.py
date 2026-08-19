"""Wait until PostgreSQL accepts connections. Used for local non-Docker startup."""

from __future__ import annotations

import sys
import time

from sqlalchemy import create_engine, text

from app.core.config import settings


def main() -> int:
    timeout = 30
    started = time.time()
    engine = create_engine(settings.DATABASE_URL)
    while time.time() - started < timeout:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("database is ready")
            return 0
        except Exception as exc:
            print(f"waiting for database: {exc}")
            time.sleep(1)
    print("database did not become ready in time", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
