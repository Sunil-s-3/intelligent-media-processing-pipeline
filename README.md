# Intelligent Media Processing Pipeline

A FastAPI backend for vehicle-image analysis. Clients upload an image, receive a `processing_id` immediately, and poll for status while a background worker runs heuristic checks (blur, brightness, duplicate, OCR, plate format, screenshot signals). Results are stored in PostgreSQL and returned as structured JSON. Confidence values are heuristic indicators, not calibrated ML probabilities.

## Features

- Image upload API (`multipart/form-data`, field name: `image`)
- Asynchronous processing via Redis + RQ
- PostgreSQL metadata and JSONB analysis results
- Local image storage (Docker volume)
- Blur detection (variance of Laplacian)
- Brightness detection (mean grayscale)
- Duplicate detection (perceptual hash + Hamming distance)
- OCR (Tesseract)
- Indian vehicle registration format validation (boundary-aware regex)
- Screenshot/editing heuristics (EXIF and resolution signals)
- Processing status API (`pending`, `processing`, `completed`, `failed`)
- Structured results API
- Docker Compose setup (API, worker, PostgreSQL, Redis)
- Automated tests (58 tests)
- Optional React dashboard in `frontend/` (bonus)

## Architecture

```
Client
  ↓
FastAPI API
  ├── PostgreSQL (metadata + results)
  ├── Local image storage
  └── Redis queue
          ↓
       RQ Worker
          ↓
    Image Analyzers
          ↓
      PostgreSQL
          ↓
      Results API
```

| Component | Role |
|---|---|
| **FastAPI** | Upload validation, status/results APIs, Swagger docs |
| **PostgreSQL** | Image metadata and analysis JSONB |
| **Redis + RQ** | Background job queue (`image_jobs`) |
| **Worker** | Runs analyzers and persists results |
| **Local storage** | Uploaded image files (shared Docker volume) |

The API and worker share the same Docker image. Locally they run as separate Compose services; the API enqueues jobs and the worker consumes them.

## Tech Stack

| Layer | Technologies |
|---|---|
| API | Python, FastAPI, Uvicorn, Pydantic |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| Queue | Redis, RQ |
| Image analysis | OpenCV, Pillow, imagehash, pytesseract |
| Testing | pytest, httpx |
| Deployment | Docker, Docker Compose |

## Project Structure

```
app/
  analyzers/      # blur, brightness, duplicate, OCR, plate validator, screenshot
  api/routes/     # health, images endpoints
  core/           # config, logging, exceptions
  db/             # models, database session
  queue/          # RQ job enqueue + worker target
  schemas/        # Pydantic request/response models
  services/       # upload, processing, query, storage
  workers/        # worker entry point
tests/            # pytest suite
samples/          # place assignment sample images here
frontend/         # optional React dashboard (bonus)
storage/original/ # uploaded images (gitignored contents)
scripts/          # wait_for_db.py, start.sh
alembic/          # database migrations
docker-compose.yml
Dockerfile
requirements.txt
.env.example
pytest.ini
README.md
```

## Getting Started

**Requirements:** Git, Docker Desktop (or Docker Engine + Compose)

```bash
git clone https://github.com/Sunil-s-3/intelligent-media-processing-pipeline.git
cd intelligent-media-processing-pipeline
```

Optional — copy environment template (Docker Compose sets variables automatically):

```bash
cp .env.example .env
```

Start all services:

```bash
docker compose up -d --build
```

Verify containers are running:

```bash
docker compose ps
```

Expected services: `api`, `worker`, `postgres`, `redis` — all healthy/running.

Open Swagger UI:

**http://localhost:8000/docs**

Upload an image via **POST /api/v1/images**, copy the returned `processing_id`, poll **GET /api/v1/images/{processing_id}/status**, then fetch **GET /api/v1/images/{processing_id}/results** when status is `completed`.

The worker processes images asynchronously — allow a few seconds after upload before checking results.

**Render deployment:** When the API and worker run as separate services, set `INTERNAL_API_BASE_URL` on the worker to the API service URL (e.g. `https://your-api.onrender.com`). The worker downloads images from `GET /api/v1/images/{processing_id}/file` when the local file is not present.

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/images` | Upload image (returns `202`) |
| GET | `/api/v1/images/{processing_id}/file` | Download stored image (worker/internal use) |
| GET | `/api/v1/images/{processing_id}/status` | Processing status |
| GET | `/api/v1/images/{processing_id}/results` | Analysis results |

**Upload example:**

```bash
curl -X POST -F "image=@path/to/vehicle.jpg" http://localhost:8000/api/v1/images
```

```json
{
  "processing_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "pending",
  "message": "Image accepted for processing"
}
```

**Status values:** `pending` → `processing` → `completed` or `failed` (with `failure_reason` when failed).

## Processing Flow

```
Upload → validate file → save to disk → create processing_id → enqueue RQ job → return 202
Worker → status: processing → run analyzers → save results → status: completed/failed
Client → poll /status → fetch /results
```

Each analyzer runs independently — an OCR failure does not stop blur or duplicate checks.

## Image Analysis

| Analyzer | Method | Notes |
|---|---|---|
| **Blur** | Variance of Laplacian | Lower score may indicate blur |
| **Brightness** | Mean grayscale | Flags very dark images |
| **Duplicate** | pHash + Hamming distance | Compares against stored hashes |
| **OCR** | Tesseract (full image + plate-focused regions) | General text + small plate crops |
| **Vehicle number** | Boundary-aware regex | Standard + Bharat series; format only |
| **Screenshot / editing** | EXIF + resolution heuristics | Weak signals, not forensic proof |

> **Important:** These are heuristic checks. Confidence values (0–1) are indicators, not calibrated probabilities. `format_valid: true` does not prove a plate is genuine or correctly read.

## Testing

**Automated tests** (inside Docker — recommended):

```bash
docker compose exec api pytest -q
```

**58 passed, 1 warning** (verified). Tests use SQLite in-memory and mock RQ enqueue — no live PostgreSQL, Redis, or Tesseract required in the test suite.

**Local pytest** (without Docker):

```bash
python -m venv .venv
pip install -r requirements.txt
python -m pytest -q
```

### Sample image testing (assignment requirement)

The assignment asks for testing with **3 sample vehicle images**. Place the company-provided images in `samples/` (this directory currently contains instructions only — add the actual image files before testing).

For each sample image:

1. Open **http://localhost:8000/docs**
2. Use **POST /api/v1/images** — upload the file (field name: `image`)
3. Copy the returned `processing_id`
4. Call **GET /api/v1/images/{processing_id}/status** until status is `completed` or `failed`
5. Call **GET /api/v1/images/{processing_id}/results** and review the analysis JSON
6. Capture a screenshot of the results (Swagger response or optional dashboard)

Or via curl:

```bash
curl -X POST -F "image=@samples/<your-sample-filename>.jpg" http://localhost:8000/api/v1/images
curl http://localhost:8000/api/v1/images/<processing_id>/status
curl http://localhost:8000/api/v1/images/<processing_id>/results
```

Do not assume specific outputs — results depend on each image.

## Sample Test Result

The following was observed during dashboard testing with one real vehicle image (not all three assignment samples):

| Check | Observed result |
|---|---|
| Processing | Completed |
| Blur | Not blurry (Laplacian variance ~1928, threshold 100) |
| Brightness | No low-light issue (average ~117, threshold 50) |
| Duplicate | Duplicate detected on re-upload (similarity 100%, Hamming distance 0) |
| OCR | Text extracted from image |
| Vehicle number | No valid standard/Bharat pattern detected (heuristic — OCR may miss small plates) |
| Screenshot/editing | No strong signal detected |

This confirms end-to-end processing, duplicate detection, and structured results. Individual sample-image outputs should be captured separately when testing all three assignment images.

## AI Usage Disclosure

Cursor/AI tools were used during development for:

- Project structure and design discussion
- Implementation assistance (FastAPI routes, analyzers, Docker setup)
- Debugging and code review
- Test generation and review
- README and documentation

AI-generated suggestions were **not** accepted blindly. Code was reviewed, modified, and validated through automated tests and manual API/dashboard testing.

**Example:** An early plate validator concatenated all OCR text before regex matching, producing a false positive (`AY17FEB2026`) from date text like `Tuesday, 17 Feb 2026`. This was caught during manual testing, fixed with boundary-aware token matching, and locked in with regression tests (`test_observed_ocr_dump_does_not_fabricate_ay17feb2026`).

Heuristic thresholds and analyzer behavior were validated by running the application, not by assuming AI output was correct.

## Engineering Decisions / Trade-offs

- **Redis + RQ** — simple async processing without heavier queue infrastructure
- **Local storage** — no cloud credentials needed for the take-home; API and worker share a Docker volume
- **PostgreSQL JSONB** — flexible analyzer result shapes without frequent schema changes
- **Isolated analyzers** — one analyzer failure does not abort the entire job
- **RQ retries** — transient worker failures may retry up to `JOB_RETRY_MAX`
- **Heuristic confidence** — explicitly labeled as non-calibrated
- **Linear pHash scan** — acceptable at take-home scale; would need an ANN index at larger scale

## Limitations / Future Improvements

- Dedicated license plate detection before OCR
- Stronger OCR preprocessing for small/degraded plates
- Calibrated ML confidence scores
- Object storage (S3/GCS) instead of local disk
- Scalable pHash indexing (pgvector, FAISS)
- Stronger tamper detection (beyond lightweight EXIF heuristics)
- Authentication, rate limiting, observability
- Multiple distributed workers

## Assumptions

- Uploaded files are still images (JPEG, PNG, WEBP, BMP, TIFF)
- Indian registration validation is **format-based only** — not proof of authenticity
- OCR can be inaccurate, especially on small or angled plates
- Missing EXIF does not prove a screenshot or edit
- Duplicate detection uses perceptual similarity, not byte-identical matching
- Heuristic confidence is not a probability

## Stopping the Project

Stop containers:

```bash
docker compose down
```

Remove containers **and** volumes (deletes PostgreSQL data and uploaded images):

```bash
docker compose down -v
```

Use `-v` only when you want a clean reset.
