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

## Live deployment (required)

This assignment requires a live deployment (local-only is not accepted).

- Render Blueprint: `render.yaml`
- After deploying, update this section with your URLs:
  - Frontend: <ADD_FRONTEND_URL>
  - Backend API: <ADD_BACKEND_URL>

### Render steps (fast path)

1. Push this repo to GitHub.
2. In Render Dashboard: **New → Blueprint** and select this repo.
3. When prompted for env vars:
   - Frontend (`VITE_API_BASE_URL`): set to your backend service URL (e.g. `https://<backend>.onrender.com`)
   - Backend (`CORS_ALLOWED_ORIGINS`): set to your frontend URL (e.g. `https://<frontend>.onrender.com`)
4. Backend service starts by running migrations + seeding demo data.

Notes:
- The UI also lets you override API base URL / tenant / actor from the header (stored in localStorage).
- Backend automatically adds `RENDER_EXTERNAL_HOSTNAME` to Django `ALLOWED_HOSTS`.

### Vercel + Render (common split)

Vercel is a good fit for the React frontend. For the Django + Postgres backend, use Render.

1) Deploy backend on Render

1. Create a Postgres database in Render.
2. Create a Render Web Service from this repo:
  - Runtime: Docker
  - Root directory / context: `backend`
  - Dockerfile: `backend/Dockerfile`
  - Docker Command:
    `sh -c "set -e; python manage.py migrate --noinput; python manage.py seed_demo; python manage.py collectstatic --noinput; gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2"`
3. Set backend env vars:
  - `DATABASE_URL` = Render Postgres connection string
  - `DJANGO_DEBUG` = `false`
  - `DJANGO_SECRET_KEY` = random
  - `CORS_ALLOWED_ORIGINS` = your Vercel frontend URL (comma-separated if multiple)

2) Deploy frontend on Vercel

1. In Vercel: **Add New → Project → Import** this GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Add env var `VITE_API_BASE_URL` = your Render backend URL (e.g. `https://<backend>.onrender.com`).
4. Deploy.

If refreshing a non-root route 404s, this repo includes `frontend/vercel.json` with a SPA rewrite.

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
