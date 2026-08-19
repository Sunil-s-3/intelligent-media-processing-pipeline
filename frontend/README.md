# Frontend Dashboard

Optional bonus dashboard for the Intelligent Media Processing Pipeline.

## Stack

- React + Vite
- Tailwind CSS
- Lucide React icons

## Setup

```bash
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API base URL |

## Requirements

The backend must be running:

```bash
# In the project root
docker compose up --build
```

## Features

- Drag-and-drop / click image upload
- Image preview, filename, and size display
- Automatic status polling after upload
- Analysis result cards for every analyzer:
  - Image quality (blur + brightness)
  - Duplicate detection
  - OCR
  - Vehicle number format validation
  - Screenshot/editing heuristic
- Error handling for all HTTP error codes
- Backend health indicator
- Responsive layout (desktop, tablet, mobile)
