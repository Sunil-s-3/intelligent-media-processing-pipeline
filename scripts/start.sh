#!/bin/sh
# Combined API + RQ worker startup for single-container deployments (e.g. Render Web Service).
# Local docker-compose overrides this via service-specific commands.

set -e

python scripts/wait_for_db.py
alembic upgrade head

RQ_QUEUE="${RQ_QUEUE_NAME:-image_jobs}"

python -m app.workers.run_worker &
WORKER_PID=$!

uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

trap 'kill "$WORKER_PID" "$API_PID" 2>/dev/null || true' INT TERM EXIT

wait "$API_PID"
