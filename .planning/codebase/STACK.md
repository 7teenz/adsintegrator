# Technology Stack

_Last updated: 2026-04-03_

## Summary

Meta Ads Audit is a full-stack SaaS application with a Python/FastAPI backend and a Next.js 14 frontend. The backend runs on Python 3.12, uses PostgreSQL 16 as the primary database, Redis 7 for task brokering and rate-limiting, and Celery for async background jobs. The frontend is a React 18 app written in TypeScript 5.3 with Tailwind CSS, communicating with the backend exclusively through a Next.js API proxy catch-all route.

---

## Languages

**Primary:**
- Python 3.12 — backend API, services, audit engine, Celery tasks
- TypeScript 5.3 — frontend Next.js application

**Secondary:**
- SQL — database schema managed via Alembic migrations

---

## Runtime

**Backend:**
- Python 3.12 (`backend/Dockerfile`: `FROM python:3.12-slim`)
- ASGI server: Uvicorn 0.27.1 with `[standard]` extras
- Startup command: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`

**Frontend:**
- Node.js 20 (set in `.github/workflows/ci.yml`)
- Next.js 14.1.0 dev server: `next dev -H 0.0.0.0 -p 3000`

**Package Managers:**
- Backend: `pip` — lockfile: `backend/requirements.txt`
- Frontend: `npm` — lockfile: `frontend/package-lock.json` (present)

---

## Frameworks

**Backend:**
- FastAPI 0.109.2 — REST API framework (`backend/app/main.py`)
  - CORS via `CORSMiddleware`; origins from `settings.cors_origins`
  - OpenAPI/ReDoc/openapi.json gated behind `settings.debug`
  - Registered routers: `health`, `auth`, `billing`, `meta`, `sync`, `audit`, `debug` (debug only in debug mode)
- Celery 5.3.6 — async task queue (`backend/app/celery_app.py`)
  - Broker + backend: Redis (`settings.redis_url`)
  - Concurrency: 2 workers (set in `docker-compose.yml`)
  - Auto-discovers tasks in `backend/app/tasks/`
- Alembic 1.13.1 — database migrations (`backend/alembic/versions/`)
  - Run automatically on container start

**Frontend:**
- Next.js 14.1.0 (`frontend/`) — App Router architecture
  - All API traffic proxied through `frontend/src/app/api/proxy/[...path]/route.ts`
  - Path alias `@/*` → `./src/*` (`frontend/tsconfig.json`)
- React 18.2.0 / react-dom 18.2.0 — UI rendering

---

## Key Dependencies

**Backend — critical:**
- `sqlalchemy==2.0.27` — ORM; `DeclarativeBase` pattern; models in `backend/app/models/`; engine in `backend/app/database.py`
- `pydantic==2.10.0` + `pydantic-settings==2.7.0` — request/response validation (`backend/app/schemas/`) and settings management (`backend/app/config.py`)
- `psycopg2-binary==2.9.9` — PostgreSQL driver
- `redis==5.0.1` — Redis client for Celery and rate limiting (`backend/app/services/rate_limit.py`)
- `httpx==0.27.0` — async and sync HTTP client for Meta Graph API and AI provider calls
- `python-jose[cryptography]==3.3.0` — JWT encoding/decoding (`backend/app/services/auth.py`)
- `passlib[bcrypt]==1.7.4` — password hashing; uses `pbkdf2_sha256` scheme (avoids bcrypt build issues)
- `cryptography==42.0.4` — Fernet symmetric encryption for Meta access tokens at rest (`backend/app/services/crypto.py`)
- `python-multipart==0.0.9` — multipart file upload support in FastAPI
- `openpyxl==3.1.5` — XLSX file parsing in the CSV/XLSX import pipeline (`backend/app/services/csv_import.py`)
- `python-magic==0.4.27` — MIME/file-type detection (requires `libmagic1` system lib, installed in `backend/Dockerfile`)
- `sentry-sdk[fastapi]==2.20.0` — error monitoring with FastAPI, Celery, and SQLAlchemy integrations (`backend/app/observability.py`)

**Frontend — critical:**
- `next==14.1.0` — framework
- `react==18.2.0` / `react-dom==18.2.0` — UI library
- `lucide-react==0.330.0` — icon library
- `tailwindcss==3.4.1` — utility-first CSS
- `clsx==2.1.0` + `tailwind-merge==2.2.1` — conditional className utilities
- `@sentry/nextjs==9.17.0` — frontend error tracking

**Backend — testing:**
- `pytest==8.3.5` + `pytest-asyncio==0.25.3` — test runner with async support (`backend/pytest.ini`, tests at `backend/tests/`)

---

## Configuration

**Environment loading:**
- Backend: `pydantic-settings` reads `backend/.env` (`Settings.model_config = {"env_file": ".env", "extra": "ignore"}`)
- Frontend: reads `frontend/.env.local` and `frontend/.env.production` (Docker Compose `env_file` blocks)
- Settings cached via `@lru_cache` on `get_settings()` (`backend/app/config.py`)

**Required env vars (no defaults — will fail to start without them):**
- `SECRET_KEY` — JWT signing key
- `ENCRYPTION_KEY` — Fernet key for Meta token encryption

**Important env vars (have safe defaults):**
- `DATABASE_URL` — default: `postgresql://postgres:postgres@postgres:5432/meta_ads_audit`
- `REDIS_URL` — default: `redis://redis:6379/0`
- `META_APP_ID` / `META_APP_SECRET` — Meta OAuth app credentials (default: `"mock"`)
- `AI_PROVIDER` / `AI_API_KEY` / `AI_MODEL` — AI summary provider (default: `"mock"` / `""` / `"gpt-4o-mini"`)
- `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM`
- `SENTRY_DSN` — optional; Sentry disabled if empty

**Frontend env vars:**
- `NEXT_PUBLIC_API_URL` — public API base; defaults to `/api/proxy`
- `BACKEND_INTERNAL_URL` — server-side proxy target; defaults to `http://backend:8000/api`
- `NEXT_PUBLIC_APP_URL` — app base URL for links

**Build files:**
- `backend/Dockerfile` — Python 3.12-slim base; installs `libmagic1`
- `frontend/` — has its own `Dockerfile` (referenced in `docker-compose.yml`)
- `docker-compose.yml` — root-level orchestration for all services

---

## Platform Requirements

**Development:**
- Docker + Docker Compose (primary dev environment)
- Services: `postgres` (5432), `redis` (6379), `backend` (8000), `celery-worker`, `frontend` (3000)
- Optional local-tools profile: `adminer` (port 8080 — DB UI), `mailpit` (ports 1025 SMTP / 8025 web UI)

**Production:**
- Any Docker-compatible host
- PostgreSQL 16 (Alpine), Redis 7 (Alpine)
- Python 3.12, Node.js 20
- `libmagic1` system library required in backend container

**CI (GitHub Actions — `.github/workflows/ci.yml`):**
- Backend: Python 3.12, runs `pytest -q` with real PostgreSQL 16 service
- Frontend: Node.js 20, runs `npm run lint` then `npm run build`

---

*Stack analysis: 2026-04-03*
