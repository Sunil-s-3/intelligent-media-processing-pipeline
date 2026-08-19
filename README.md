# Intelligent Media Processing Pipeline

## 1. Overview

This is a FastAPI backend that accepts vehicle images and returns structured heuristic analysis. Uploads return immediately — the API validates the file, stores it, creates a UUID `processing_id`, enqueues a Redis + RQ background job, and responds with `202 Accepted` before any analysis begins. A separate RQ worker picks up each job, runs all image analyzers, and persists results to PostgreSQL. Clients poll a status endpoint and fetch results when ready.

---

## 2. Features

- Asynchronous image processing
- FastAPI REST API with Swagger/OpenAPI
- PostgreSQL metadata and JSONB results
- Redis + RQ background worker
- Blur detection
- Brightness detection
- Duplicate detection using pHash
- OCR using Tesseract
- Indian vehicle registration format validation
- Screenshot/editing heuristic
- Docker Compose
- Automated tests

---

## 3. Architecture

```
Client
  |
  v
FastAPI API
  |
  +---- PostgreSQL
  |
  +---- Local Storage
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
PostgreSQL Results
```

| Component | Purpose |
|---|---|
| FastAPI | HTTP API, upload validation, and Swagger documentation |
| PostgreSQL | Image metadata and analysis results |
| Redis + RQ | Background job queue |
| Worker | Runs image analyzers and stores results |
| Local Storage | Stores uploaded image files |

The API and worker use the same Docker image with different startup commands. A named volume shares uploaded files between them.

---

## 4. Processing Flow

```
Upload
→ Validate (size, type, decodable)
→ Store image to disk
→ Create processing ID (UUID)
→ Queue background job
→ Return 202 Accepted

Worker
→ Set status: processing
→ Run image analyzers
→ Persist results
→ Set status: completed (or failed + failure_reason)

Client
→ Poll GET /status
→ Fetch GET /results
```

Each analyzer runs independently — an OCR failure does not abort blur or duplicate checks. If Redis is unavailable at enqueue time, the uploaded file and database row are cleaned up and the client receives `503`.

---

## 5. Image Analysis

All thresholds are configurable via environment variables (see `.env.example`).

| Analyzer | Purpose | Method |
|---|---|---|
| Blur | Detect potentially blurry images | Variance of Laplacian |
| Brightness | Detect very dark images | Mean grayscale |
| Duplicate | Detect previously processed images | pHash + Hamming distance |
| OCR | Extract text | Tesseract |
| Vehicle Number | Validate Indian registration format | Boundary-aware regex |
| Screenshot | Detect possible screenshot/editing signals | EXIF and resolution heuristics |

> These are heuristics, not calibrated ML probabilities. Confidence values (`0–1`) are heuristic indicators and should not be treated as guaranteed probabilities.

**Vehicle number validation** matches two formats:

- Standard: `KA01AB1234`, `KA 01 AB 1234`, `KA-01-AB-1234`, `DL1CAA1234`
- Bharat series: `22BH1234AA`, `22 BH 1234 AA`, `22-BH-1234-AA`

`format_valid: true` means the OCR text resembles a valid Indian registration pattern. It does **not** prove the plate is genuine, issued, or correctly read. The validator uses boundary-aware token matching so unrelated text such as dates or addresses (e.g. `Tuesday, 17 Feb 2026`) is never misidentified as a plate number.

---

## 6. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /api/v1/health | Health check |
| POST | /api/v1/images | Upload image |
| GET | /api/v1/images/{processing_id}/status | Check processing status |
| GET | /api/v1/images/{processing_id}/results | Get analysis results |

Interactive docs: **http://localhost:8000/docs**

Upload returns HTTP `202`. Status progresses through `pending` → `processing` → `completed` / `failed`.

**Upload**

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

**Status**

```bash
curl http://localhost:8000/api/v1/images/<processing_id>/status
```

```json
{ "processing_id": "...", "status": "completed" }
```

**Results** (field shapes shown; numbers are illustrative, not recorded sample output)

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

Starts four services: API (port 8000), Worker, PostgreSQL (port 5432), Redis (port 6379). The API and worker both run `alembic upgrade head` on startup after PostgreSQL becomes healthy.

Open **http://localhost:8000/docs** to explore the API interactively.

---

## 8. Testing

Tests use SQLite in-memory and mock the RQ enqueue call — no live PostgreSQL, Redis, or Tesseract required.

```bash
docker compose exec api pytest -q
```

**43 tests passed, 1 warning.**

Coverage includes: health endpoint, upload validation (corrupt, oversized, unsupported type), status and results endpoints, blur and brightness analyzers, duplicate pHash detection, plate validator (valid formats, false-positive regression for dates and address text), OCR isolation with mocked Tesseract, and worker success/failure paths.

To run locally without Docker:

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# Unix:    source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

---

## 9. Configuration

Copy `.env.example` to `.env` and edit as needed. Do not commit `.env`.

```bash
cp .env.example .env
```

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `STORAGE_PATH` | Directory for uploaded image files |
| `MAX_UPLOAD_SIZE_MB` | Maximum allowed upload size |
| `BLUR_THRESHOLD` | Laplacian variance below which blur is flagged |
| `BRIGHTNESS_THRESHOLD` | Mean pixel value below which low-light is flagged |
| `DUPLICATE_HASH_DISTANCE` | Maximum pHash Hamming distance treated as a duplicate |

Docker Compose sets all required variables automatically.

---

## 10. Error Handling

| Status | Meaning |
|---|---|
| 202 | Image accepted and queued for processing |
| 400 | Missing, empty, corrupt, or undecodable file |
| 404 | Unknown `processing_id` |
| 413 | File exceeds upload size limit |
| 415 | Unsupported image format |
| 503 | Database or Redis unavailable at upload time |

Internal Python stack traces are logged server-side and are never returned in JSON responses. Failed jobs include a human-readable `failure_reason` in the status and results responses.

---

## 11. Design Decisions

- **Redis + RQ for asynchronous processing.** Keeps the API free of CPU-heavy OCR and analysis work, with built-in retry support.
- **PostgreSQL JSONB for analyzer results.** Payloads can evolve without a schema migration per field.
- **Independent analyzers.** Each analyzer is isolated inside the worker so one failure does not abort the others.
- **Local storage.** No cloud credentials needed for a take-home; the API and worker share files through a named Docker volume.

---

## 12. Limitations

- Local storage is not suitable for multi-host production deployment
- pHash duplicate detection uses a full database scan and will not scale to very large datasets
- OCR quality depends on image quality, angle, and lighting
- Vehicle number validation checks format only and does not verify authenticity
- Screenshot detection is a lightweight heuristic, not a forensic tool

---

## 13. Future Improvements

- Object storage such as S3/GCS
- Multiple workers and queue partitioning
- Plate region detection before OCR
- Scalable pHash similarity search (ANN index or pgvector)
- Authentication, rate limiting, and monitoring

---

## 14. Validation

| Check | Result |
|---|---|
| Automated tests | 43 passed, 1 warning |
| Docker Compose build | Successful |
| Docker Compose startup | Successful |
| PostgreSQL | Healthy |
| Redis | Healthy |
| Health endpoint | `{"status":"ok"}` |
| Image upload | HTTP 202, `processing_id` returned |
| Background processing | Status transitioned to `completed` |
| Status endpoint | `completed` returned |
| Results endpoint | Analysis JSON returned |
| Duplicate detection | Second upload of the same image correctly flagged |

---

## 15. AI Usage Disclosure

Cursor/AI tools were used during development for implementation assistance, boilerplate generation, debugging, test creation, and documentation. Generated code was reviewed, modified where necessary, and validated using automated tests and the Docker Compose workflow.

- 43 automated tests passed (Python 3.11, SQLite in-memory, RQ enqueue mocked)
- Docker Compose was successfully built and run end-to-end
- All API endpoints were manually verified through Swagger (`/docs`) and curl

---

## 16. Submission

This repository contains the application source code, tests, Docker configuration, database migration, configuration example, and documentation required to run and evaluate the assignment.
