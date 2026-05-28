# Tradeoffs / Known Gaps

This prototype optimizes for: (1) auditability, (2) realistic messy ingestion, and (3) an analyst review loop.

## Security & access control
- No authentication, authorization, or role-based access control.
- Tenant selection is header-based and intended for demos only.

## Background processing
- Ingestion is synchronous (request-time). A production system would enqueue jobs (Celery/RQ) and stream progress.

## Emission factor governance
- Factors are a small seeded catalog with toy values.
- No factor approval workflow, provenance tracking beyond simple `source` strings, or automated versioning.
- Snapshotting is implemented, but “recalculate historical records” is not.

## Data quality / matching depth
- Mapping from source to factor is heuristic and limited (good enough for prototype realism).
- Plant and procurement categorization are simplistic and would be expanded with master data.

## UI scope
- Dashboard is intentionally minimal: upload, job list, review queue with inline edit, and basic exploration.
- No bulk actions, no saved filters, no per-field validation UI, no change-log viewer UI.

## Storage / deployments
- SQLite is used for local convenience; the backend supports `DATABASE_URL` for Postgres.
- File storage is local filesystem only (no S3/GCS integration).

## Travel estimation limitations
- Flight distances can be estimated from a small airport reference list using great-circle distance and a fixed uplift.
- The airport list is intentionally small (prototype), so unknown airports will fail parsing.
