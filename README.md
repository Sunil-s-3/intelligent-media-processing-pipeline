# Intelligent Media Processing Pipeline

## 1. Overview

This project is a FastAPI backend that accepts vehicle images, processes them asynchronously, and returns structured heuristic analysis. Uploads return immediately with a UUID `processing_id` — the API validates, stores, and queues the job, then returns `202 Accepted` without waiting for analysis to complete. A separate RQ worker picks up each job, runs image analyzers (blur, brightness, duplicate detection, OCR, Indian plate format validation, and a screenshot heuristic), and persists structured results to PostgreSQL. Clients poll a status endpoint and fetch results when ready.

---

## 2. Features

- Async image processing (upload never blocks on analysis)
- FastAPI REST API with OpenAPI/Swagger documentation
- PostgreSQL for image metadata and JSONB analysis results
- Redis + RQ background worker
- Blur detection
- Brightness / low-light detection
- Duplicate detection using perceptual hash (pHash)
- OCR using Tesseract
- Indian vehicle registration format validation (standard + Bharat series)
- Screenshot / editing heuristic
- Docker Compose support
- Automated tests (43 passing, no Docker or Tesseract required)

---

## 3. Architecture

```
Client
  |
  v
FastAPI API
  |
  +----> PostgreSQL (image metadata)
  |
  +----> Local Storage (image file)
  |
  v
Redis Queue
  |
  v
RQ Worker
  |
  v
Image Analyzers
  |
  v
PostgreSQL (analysis results)
```

| Component | Role |
|---|---|
| FastAPI | Versioned HTTP API (`/api/v1`), upload validation, OpenAPI docs |
| PostgreSQL | Image metadata rows + JSONB analyzer results |
| Local storage | Uploaded image bytes, shared between API and worker via a named Docker volume |
| Redis + RQ | Job queue that decouples the API process from analysis work |
| Worker | Transitions image status, runs all analyzers, persists results |

The API and worker use the same Docker image with different startup commands.

---

## 4. Processing Flow

```
Upload
→ Validate (size, type, decodable)
→ Store to disk
→ Create processing ID (UUID)
→ Write pending row to PostgreSQL
→ Enqueue RQ job
→ Return 202 immediately
       ↓
Worker
→ Set status: processing
→ Run all image analyzers
→ Persist structured results
→ Set status: completed (or failed + failure_reason)
       ↓
Client polls GET /status → fetches GET /results
```

- Each analyzer runs independently. An OCR failure does not abort blur or duplicate checks.
- If Redis is unavailable at enqueue time, the file and database row are cleaned up and the client receives `503`.

---

## 5. Image Analysis

All thresholds are configurable via environment variables (see `.env.example`).

| Analyzer | Purpose | Method |
|---|---|---|
| Blur | Detect potentially blurry images | Variance of Laplacian (OpenCV) |
| Brightness | Detect very dark images | Mean grayscale value (0–255) |
| Duplicate | Detect previously processed images | 64-bit pHash + Hamming distance |
| OCR | Extract text from the image | Tesseract via pytesseract |
| Vehicle Number | Validate Indian registration format | Boundary-aware token regex |
| Screenshot | Detect possible screenshot or editing signals | EXIF Software tag + resolution heuristics |

> These are heuristics, not calibrated ML probabilities. Confidence values (`0–1`) are heuristic indicators and should not be interpreted as guaranteed probabilities.

**Vehicle number validation** matches two formats:

- Standard: `KA01AB1234`, `KA 01 AB 1234`, `KA-01-AB-1234`, `DL1CAA1234`
- Bharat series: `22BH1234AA`, `22 BH 1234 AA`, `22-BH-1234-AA`

`format_valid: true` means the OCR text resembles a valid Indian registration pattern. It does **not** prove the plate is genuine, issued, or correctly read. The validator uses boundary-aware token matching so date or address text (e.g. `Tuesday, 17 Feb 2026`) is never misidentified as a plate number.

---

## 6. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/images` | Upload image for processing |
| `GET` | `/api/v1/images/{processing_id}/status` | Check processing status |
| `GET` | `/api/v1/images/{processing_id}/results` | Fetch analysis results |

Interactive docs: **http://localhost:8000/docs**

Upload returns HTTP `202`. Status values: `pending` → `processing` → `completed` / `failed`.

**Upload example**

```bash
curl -X POST -F "image=@vehicle.jpg" http://localhost:8000/api/v1/images
```

```json
{
  "processing_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "pending",
  "message": "Image accepted for processing"
}
```

**Status example**

```bash
curl http://localhost:8000/api/v1/images/<processing_id>/status
```

```json
{ "processing_id": "...", "status": "completed" }
```

**Results example** (shape shown; numbers are illustrative, not recorded sample output)

```bash
curl http://localhost:8000/api/v1/images/<processing_id>/results
```

```json
{
  "processing_id": "...",
  "status": "completed",
  "analysis": {
    "image_quality": {
      "blur":       { "detected": false, "score": 182.4, "confidence": 0.91 },
      "brightness": { "issue": false, "average_brightness": 128.4, "confidence": 0.93 }
    },
    "duplicate":      { "detected": false, "matched_image_id": null },
    "ocr":            { "status": "completed", "ocr_text": "KA01AB1234" },
    "vehicle_number": { "format_valid": true, "matched_value": "KA01AB1234", "matched_pattern": "standard" },
    "screenshot":     { "detected": false }
  }
}
```

---

## 7. Running with Docker

Docker Compose is the primary and validated setup method.

```bash
docker compose up --build
```

This starts four services:

| Service | Port |
|---|---|
| API | 8000 |
| Worker | — |
| PostgreSQL | 5432 |
| Redis | 6379 |

Both the API and worker run `alembic upgrade head` after waiting for PostgreSQL to be healthy. The image storage volume is shared between them automatically.

Open **http://localhost:8000/docs** to explore the API interactively.

---

## 8. Running Tests

Tests use SQLite in-memory and mock the RQ enqueue call. No live PostgreSQL, Redis, or Tesseract installation is required.

```bash
docker compose exec api pytest -q
```

**Result: 43 passed, 1 warning**

To run locally without Docker:

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# Unix:    source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Test coverage includes health endpoint, upload validation (corrupt, oversized, unsupported type), status and results endpoints, blur and brightness analyzers, duplicate pHash detection, plate validator (valid formats, false-positive regression for dates and address text, embedded OCR text), OCR isolation with mocked Tesseract, and worker success/failure paths.

---

## 9. Configuration

Copy `.env.example` to `.env` and edit as needed. Do not commit `.env`.

```bash
cp .env.example .env
```

Key variables:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://app:app@localhost:5432/media_pipeline` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `STORAGE_PATH` | `./storage/original` | Where uploaded files are saved |
| `MAX_UPLOAD_SIZE_MB` | `10` | Upload size limit |
| `BLUR_THRESHOLD` | `100.0` | Laplacian variance below which blur is flagged |
| `BRIGHTNESS_THRESHOLD` | `50.0` | Mean pixel value below which low-light is flagged |
| `DUPLICATE_HASH_DISTANCE` | `5` | Max pHash Hamming distance treated as a duplicate |

Docker Compose sets all required variables automatically.

---

## 10. Error Handling

| Status | Meaning |
|---|---|
| 202 | Accepted and queued; also returned while status is `pending` or `processing` |
| 400 | Missing, empty, or corrupt / undecodable file |
| 404 | Unknown `processing_id` |
| 413 | File exceeds `MAX_UPLOAD_SIZE_MB` |
| 415 | Unsupported image format (e.g. GIF) |
| 503 | Database or Redis unavailable at upload time |

Internal Python stack traces are logged server-side and are never returned in JSON responses. Failed jobs include a human-readable `failure_reason` in the status and results responses.

---

## 11. Design Decisions

- **Redis + RQ for async processing.** Keeps the API process free of CPU-heavy OCR and analysis work. Built-in retry support without adding a second message bus.
- **PostgreSQL JSONB for results.** Analyzer output shapes can evolve without a new migration per field.
- **Independent analyzers.** Each analyzer is isolated inside the worker; an OCR failure does not abort blur or duplicate checks.
- **Local storage.** No cloud credentials needed for a take-home assignment. API and worker share files through a named Docker volume.
- **Heuristic analysis.** The assignment calls for honest engineering judgment, not claims of production-grade ML accuracy. All results expose confidence as a heuristic indicator.

---

## 12. Limitations

- Local storage is not suitable for multi-host production deployment
- pHash duplicate detection uses a full database scan and will not scale to large datasets without an approximate nearest-neighbor index
- OCR quality depends on image quality, angle, and lighting — Tesseract may return empty text on difficult images
- Vehicle number validation is format matching only and does not verify authenticity
- Screenshot detection is a lightweight heuristic, not a forensic tool
- All analyzer thresholds are defaults and require tuning on real production data

---

## 13. Future Improvements

- Object storage (S3/GCS) to replace local disk
- Multiple concurrent workers and queue partitioning
- Plate region localization before OCR to improve text extraction
- Scalable pHash similarity search (ANN index or pgvector)
- Authentication, rate limiting, and structured metrics/monitoring

---

## 14. Validation

The following was verified during development:

| Check | Result |
|---|---|
| `docker compose exec api pytest -q` | **43 passed, 1 warning** |
| `docker compose build` | Success |
| `docker compose up` | All four services started |
| PostgreSQL health | Healthy |
| Redis health | Healthy |
| `GET /api/v1/health` | `{"status":"ok"}` |
| `POST /api/v1/images` | HTTP 202, `processing_id` returned |
| Background worker processing | Status transitioned to `completed` |
| `GET /status` | Returned `completed` |
| `GET /results` | Full analysis JSON returned |
| Duplicate detection | Second upload of the same image correctly flagged |

---

## 15. AI Usage Disclosure

Cursor/AI tools were used during development for implementation assistance, boilerplate generation, debugging, test creation, and documentation. Generated code was reviewed, modified where necessary, and validated using automated tests and the Docker Compose workflow.

- **43 automated tests passed** (Python 3.11, SQLite in-memory, RQ enqueue mocked)
- Docker Compose was successfully built and run end-to-end
- All API endpoints were manually verified through Swagger (`/docs`) and curl

---

## 16. Submission

This repository contains the application source code, tests, Docker configuration, database migration, configuration example, and documentation required to run and evaluate the assignment.
