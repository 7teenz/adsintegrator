# Meta Ads Audit (Local MVP)

Deterministic Meta Ads audit SaaS with:
- FastAPI backend
- Next.js frontend
- PostgreSQL + Redis
- Celery workers for sync jobs
- AI explanation layer that only explains deterministic findings

This repo currently includes:
- auth + JWT
- Meta OAuth connection (with local `mock` mode)
- data sync pipeline (campaigns/ad sets/ads/creatives/insights)
- CSV history import option from exported Ads Manager reports
- deterministic audit engine
- freemium frontend gating
- local MVP billing mode (no Stripe required)
- production-hardening baseline (structured logs, retries, health/debug endpoints, tests)

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

3. Open:
- Frontend: `http://127.0.0.1:3000`
- Backend docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/health`

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

## 7. Local MVP Plan Controls

Local-only plan switch endpoint:
- `POST /api/billing/dev/plan` with body `{"plan_tier":"free|premium|agency"}`
- available only when `DEBUG=true`

Entitlements are enforced server-side for:
- findings/report limits
- history depth
- chart depth
- ad account cap

## 8. Environment Notes

Required backend envs:
- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `ENCRYPTION_KEY`

Optional but recommended:
- `META_*` for real Meta OAuth (or `META_APP_ID=mock` for local)
- `AI_*` for OpenAI/Anthropic summaries

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

`usePlan must be used inside <PlanProvider>` in frontend:
- ensure dashboard layout wraps children with `PlanProvider`

Sync stuck/failing:
- check worker logs and `/api/debug/jobs`
- check `/api/health/ready`

## 11. Technical Debt (Known)

- No global multi-tenant admin panel yet (user-scoped debug only)
- No Stripe production rollout yet (local billing mode only)
- Observability stack is stdlib logging; no external telemetry exporter yet
