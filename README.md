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

## 11. Queue Strategy

Redis + RQ was chosen for the background queue because:

- It matches the assignment's specified stack
- It keeps the API process free of CPU-heavy OCR and image analysis work
- Built-in `Retry` support handles transient worker failures without a second message bus
- The operational model is simple: one named queue (`image_jobs`), one worker command

RQ is not Kafka, Celery, or a custom broker. For a take-home assignment that is a deliberate feature — fewer moving parts with the same async decoupling. Non-retryable failures (corrupt or missing images) are caught inside the job and marked `failed` without re-queuing; transient infrastructure errors are re-raised so RQ can retry up to `JOB_RETRY_MAX` times.

---

## 12. Assumptions

- Uploaded files are expected to be still images (JPEG, PNG, WEBP, BMP, TIFF); video is not supported
- Indian vehicle registration validation is format validation only — it does not verify that a plate is genuine, issued, or correctly read by OCR
- Local filesystem storage is acceptable for a take-home environment where the API and worker run on the same host via Docker Compose
- Heuristic analysis (blur, brightness, duplicate, screenshot) is intended to flag possible issues, not prove them; confidence values are not calibrated ML probabilities
- English Tesseract language data is sufficient for this use case
- A linear pHash database scan is acceptable at take-home dataset scale

---

## 13. Design Decisions & Trade-offs

| Decision | Rationale | Trade-off |
|---|---|---|
| Redis + RQ | Simple, assignment-specified, process isolation, retry support | Less tooling than Celery; no delayed routing beyond Retry |
| Local filesystem | No cloud credentials required; easy Docker volume sharing | Not suitable for multi-host or production deployments |
| PostgreSQL JSONB for results | Analyzer output shapes can evolve without schema migrations | Weaker column-level constraints than typed columns |
| Independent analyzers | One analyzer failure does not abort the others | Each failure is isolated; the job still completes |
| Heuristic analysis | Honest about uncertainty; matches assignment intent | False positives and negatives are possible; thresholds need tuning |
| SQLite in tests | Tests run without Docker, PostgreSQL, Redis, or Tesseract | JSONB-specific PostgreSQL behaviour is not exercised in pytest |
| Processing ID = `images.id` | One UUID, no extra lookup column | None for this scale |

---

## 14. Scalability Considerations

The current implementation is intentionally scoped for a take-home assignment and is not designed for large-scale production use.

| Area | Current approach | Production path |
|---|---|---|
| Image storage | Local filesystem via Docker volume | Object storage (S3/GCS); DB stores object keys |
| Duplicate detection | Linear pHash scan across all stored hashes | Approximate nearest-neighbour index (FAISS, pgvector) |
| Workers | Single RQ worker process | Multiple workers; queue partitioning by priority |
| API scaling | Single Uvicorn process | Horizontal replicas behind a load balancer |
| Queue monitoring | RQ built-in | Dead-letter registry, metrics, structured log collector |

---

## 15. Limitations

- Local storage is not suitable for multi-host production deployment
- pHash duplicate detection uses a full database scan and will not scale to very large datasets
- OCR quality depends on image quality, angle, and lighting
- Vehicle number validation checks format only and does not verify authenticity
- Screenshot detection is a lightweight heuristic, not a forensic tool

---

## 16. Future Improvements

- Object storage such as S3/GCS
- Multiple workers and queue partitioning
- Plate region detection before OCR
- Scalable pHash similarity search (ANN index or pgvector)
- Authentication, rate limiting, and monitoring

---

## 17. Validation (Verified Results)

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

## 18. AI Usage Disclosure

Cursor/AI tools were used during development for:

- Implementation assistance and boilerplate generation (FastAPI app, SQLAlchemy models, Alembic migration, Docker Compose, config and logging setup)
- Image analyzer implementations (OpenCV Laplacian blur, mean brightness, imagehash pHash duplicates, pytesseract OCR, plate regex, EXIF screenshot heuristic)
- Test creation (pytest + TestClient cases for upload, status, results, analyzers, OCR isolation, worker paths)
- Debugging and review (exception handler tightening, chunked upload size check, worker migration wait)
- Documentation (this README)

All generated code was reviewed, modified where necessary, and validated using the automated test suite and Docker Compose end-to-end workflow.

**Concrete example of an AI-generated error and how it was corrected:**

The initial vehicle-number validator used broad normalization: it stripped all non-alphanumeric characters from the entire OCR text and then searched the resulting concatenated string with a regex. This caused a false positive during API testing — the OCR text `"Tuesday, 17 Feb 2026 11:22 AM Perambur High Road"` was normalized to `"TUESDAY17FEB202611..."` and the regex found `"AY17FEB2026"` within that string, incorrectly returning `format_valid: true` with `matched_value: "AY17FEB2026"`.

**How it was detected:** Manual API testing with a real image whose OCR output contained a date and address string — common in field-photographed images — produced an obviously wrong plate number.

**What was changed:** The validator was refactored to use boundary-aware token matching. The OCR text is first split into alphanumeric tokens on whitespace and punctuation boundaries. Only short windows of consecutive tokens (up to 6) are joined and tested against the full plate pattern. This means `"Tuesday"`, `"17"`, `"Feb"`, `"2026"` are never concatenated across word boundaries into a candidate string.

**How the fix was validated:** A regression test (`test_observed_ocr_dump_does_not_fabricate_ay17feb2026`) was added using the exact OCR text that triggered the false positive. Additional tests cover date strings, hyphenated dates, address text, and embedded legitimate plates. All 43 tests pass, including this regression test, and the API was re-verified manually through Swagger.

**Validation summary:**

- 43 automated tests passed (Python 3.11, SQLite in-memory, RQ enqueue mocked)
- Docker Compose was successfully built and run end-to-end
- All API endpoints were manually verified through Swagger (`/docs`) and curl

---

## 19. Submission

This repository contains the application source code, tests, Docker configuration, database migration, configuration example, and documentation required to run and evaluate the assignment.
