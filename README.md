# Meta Ads Audit (Local MVP)

Local MVP for uploading Meta Ads exports, running a deterministic audit, and reviewing a focused dashboard with AI interpretation layered on top.

This repo includes:
- FastAPI backend
- Next.js frontend
- PostgreSQL + Redis
- Celery workers for audit + sync jobs
- AI explanation layer that only explains deterministic findings
- local auth, upload, audit, and report loop
- optional Mailpit/Adminer helpers for local debugging

## 1. Quick Start (Docker)

1. Copy env files:
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

2. Build and run:
```bash
docker compose up -d --build
```

Windows PowerShell helper if Docker rebuilds fail because `docker-credential-desktop` is not on `PATH`:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\docker-compose.ps1 up -d --build
```

Optional local tools:
```bash
docker compose --profile local-tools up -d
```

3. Open:
- Frontend: `http://127.0.0.1:3000`
- Health: `http://127.0.0.1:8000/api/health`
- Mailpit: `http://127.0.0.1:8025`
- Adminer: `http://127.0.0.1:8080`

Note: backend docs are only available when `DEBUG=true`.

## 2. Local Run Without Docker

Backend:
```bash
cd backend
python -m venv .venv
. .venv/bin/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Worker:
```bash
cd backend
celery -A app.celery_app:celery worker --loglevel=info --concurrency=2
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## 3. Database Migrations

Inside backend container:
```bash
docker compose exec backend sh -lc "PYTHONPATH=/app alembic upgrade head"
```

Without Docker:
```bash
cd backend
alembic upgrade head
```

## 4. Test Commands

Run all backend tests:
```bash
cd backend
pytest -q
```

Run smoke subset:
```bash
cd backend
pytest -m smoke -q
```

## 5. Operational Endpoints

- `GET /api/health` basic liveness
- `GET /api/health/db` database connectivity
- `GET /api/health/ready` readiness (DB + Redis + worker ping)
- `GET /api/debug/jobs` authenticated user-scoped job overview
- `GET /api/debug/jobs/{job_id}` authenticated job detail + logs
- `GET /api/debug/audits` authenticated audit overview
- `GET /api/debug/audits/{audit_run_id}` authenticated audit detail
- `POST /api/sync/import-csv` authenticated CSV import (`file` + `replace_existing`)

## 6. Logging and Error Conventions

- API and workers use centralized structured logging.
- Request ID is propagated by `x-request-id` response header.
- Error payload shape is normalized:
```json
{"detail": "...", "code": "...", "request_id": "..."}
```
- Sensitive values (tokens, API keys) must never be logged.

## 7. Local MVP Notes

- Customer-facing billing/upgrade UX is intentionally hidden in this build.
- Entitlements still exist internally, but the local MVP is presented as a single included experience.
- Uploaded data stays in the local project environment for this build.
- Users can clear imported data from inside the app.

## 8. Environment Notes

Required backend envs:
- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `ENCRYPTION_KEY`

Optional but recommended:
- `META_*` for real Meta OAuth (or `META_APP_ID=mock` for local)
- `AI_*` for OpenAI, Anthropic, or Gemini summaries
- `SENTRY_*` for optional local error tracking

## 9. Deployment Topology Notes

Minimum services:
- API process (FastAPI/Uvicorn)
- Celery worker
- PostgreSQL
- Redis
- Frontend server

Readiness expectations:
- API ready only when DB, Redis, and at least one Celery worker respond.

## 10. Troubleshooting

Backend unreachable from frontend:
- verify backend container is running
- ensure frontend `NEXT_PUBLIC_API_URL` points to `http://127.0.0.1:8000/api`
- verify CORS origins in backend env

Migration import errors in container:
- run Alembic with `PYTHONPATH=/app`

Docker rebuild fails with `docker-credential-desktop` not found on Windows:
- run `powershell -ExecutionPolicy Bypass -File .\scripts\docker-compose.ps1 up -d --build`
- for backend-only rebuild plus the focused AI summary test, run `powershell -ExecutionPolicy Bypass -File .\scripts\rebuild-backend.ps1`

`usePlan must be used inside <PlanProvider>` in frontend:
- ensure dashboard layout wraps children with `PlanProvider`

Sync stuck/failing:
- check worker logs and `/api/debug/jobs`
- check `/api/health/ready`

## 11. Troubleshooting Local Helpers

Mailpit and Adminer are local-only helper services. Start them with:
```bash
docker compose --profile local-tools up -d
```

Mailpit captures verification/reset emails locally.
Adminer provides a lightweight browser UI for the local Postgres database.
