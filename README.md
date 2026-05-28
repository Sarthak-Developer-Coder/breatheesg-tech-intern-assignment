# Tech Intern Assignment — Breathe ESG Prototype

Prototype goals:
- ingest messy activity data from multiple sources
- preserve raw source records for audit and reprocessing
- normalize into canonical `ActivityRecord` rows (Scope 1/2/3)
- detect anomalies + confidence for analyst attention
- support analyst edit/approve/reject
- lock approved rows for audit stability

Stack:
- Backend: Django + DRF + PostgreSQL
- Frontend: React + TypeScript + Tailwind

Required docs (these carry the “why”):
- `MODEL.md`
- `DECISIONS.md`
- `TRADEOFFS.md`
- `SOURCES.md`

## Live deployment 

- Render Blueprint: `render.yaml`
- Deployed URLs:
  - Frontend: https://breatheesg-tech-intern-frontend.onrender.com
  - Backend API: https://breatheesg-tech-intern-backend.onrender.com



## Run locally

### Docker (recommended for a clean demo)

Requires Docker Desktop.

```powershell
docker compose up --build
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

The backend container automatically runs `migrate` and `seed_demo`.

### Local dev (no Docker)

Backend:

```powershell
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open the UI at `http://localhost:5173`.

Suggested demo config in the UI header:
- API: `http://127.0.0.1:8000`
- Tenant: `demo`
- Analyst: `analyst@demo.local` (used for audit fields)

## Demo flow

1. Upload sample files from `sample_data/`:
   - `sap_export.csv`
   - `utility_export.csv`
   - `travel_payload.json`
2. Go to **Review Queue** to edit/approve/reject suspicious rows.
3. Approved rows become locked; view them in **Approved Records**.

## API surface (minimal)

- Uploads
  - `POST /api/upload/sap` (multipart: `file`, `actor`, optional `source_label`)
  - `POST /api/upload/utility` (multipart: `file`, `actor`, optional `source_label`)
  - `POST /api/upload/travel` (json: `actor`, optional `source_label`, `transactions: [...]`)
- Lists
  - `GET /api/ingestion-jobs`
  - `GET /api/activity-records`
  - `GET /api/review-queue`
- Review actions
  - `PATCH /api/activity-records/<id>/edit`
  - `POST /api/review/<id>/approve`
  - `POST /api/review/<id>/reject`

Multi-tenancy is demonstrated via the `X-Tenant-Slug` header (defaults to `demo` in dev).
