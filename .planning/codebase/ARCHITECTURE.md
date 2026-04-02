# Architecture

**Analysis Date:** 2026-04-02

## System Overview

Meta Ads Audit is a full-stack SaaS application that pulls advertising data from the Meta (Facebook) Graph API, stores it locally, runs a deterministic rule-based audit engine over that data, and presents findings through a dashboard. The system surfaces wasted ad spend, health scores, and AI-generated summaries for a connected Meta Ads account.

The product is composed of:
- A **Next.js 14 frontend** (App Router, client-side React) served at port 3000
- A **FastAPI backend** served at port 8000
- A **Celery worker** for async audit execution
- **PostgreSQL** as the primary data store
- **Redis** as the Celery broker and result backend

## Architectural Patterns

**Overall:** Layered monolith with async task dispatch

**Key Characteristics:**
- Frontend communicates with backend exclusively via a Next.js catch-all proxy route (`/api/proxy/[...path]`), which forwards to the backend's internal Docker network address
- Backend is organized into layers: routes → services/engine → models, with Pydantic schemas for validation at the boundary
- The audit execution is asynchronous: a POST to `/api/audit/run` creates an `AuditRun` record and dispatches a Celery task; the frontend polls `/api/audit/job/{id}` for completion
- Rule evaluation is a registry pattern: each `AuditRule` subclass registers itself via a `@register_rule` decorator in `backend/app/engine/rules/base.py`; `get_all_rules()` instantiates all registered rule classes at runtime

## Data Flow

**Meta Ads Sync Pipeline:**
1. User authenticates via Meta OAuth (handled by `backend/app/services/meta_auth.py`)
2. User selects an ad account from their connected Meta accounts
3. A sync job is dispatched via `backend/app/tasks/sync.py` → `backend/app/services/meta_sync.py`
4. `MetaSyncFetchService` calls the Meta Graph API v19.0 with paginated HTTP requests (httpx)
5. `MetaSyncPersistenceService` upserts campaigns, ad sets, ads, creatives, and daily insights into PostgreSQL
6. Data is stored at four insight levels: account, campaign, ad set, and ad

**Audit Execution Pipeline:**
1. `POST /api/audit/run` creates an `AuditRun` row with `job_status = "pending"` and dispatches `run_audit_job` Celery task
2. Celery worker calls `populate_audit_run()` in `backend/app/engine/orchestrator.py`
3. `collect_account_data()` in `backend/app/engine/collector.py` reads synced data from PostgreSQL and builds an `AccountAuditSnapshot` with pre-computed metrics for each entity level
4. Each registered `AuditRule` evaluates the snapshot and emits a list of `Finding` objects
5. `apply_recommendation()` enriches each finding with actionable text
6. `compute_scores()` calculates pillar scores (5 pillars: acquisition, conversion, budget, trend, structure) and a weighted composite health score
7. All findings, scores, and recommendations are persisted to PostgreSQL
8. `AISummaryService.generate_for_run()` calls an external LLM (OpenAI / Anthropic / Gemini, or mock) to produce three narrative sections
9. `AuditRun.job_status` is set to `"completed"`

**Frontend Read Path:**
1. Frontend calls `/api/proxy/audit/dashboard` (proxied to backend)
2. Backend `GET /api/audit/dashboard` aggregates the latest completed audit run, live KPIs from daily insight rows, worst-performer queries, and trend data
3. Response serialized via Pydantic schemas and returned as JSON
4. Frontend renders in client components (`"use client"`) using `useState`/`useEffect` and `apiFetch` in `frontend/src/lib/api.ts`

**Authentication:**
1. JWT stored as an HttpOnly cookie (`access_token`)
2. Backend `get_current_user` dependency in `backend/app/middleware/deps.py` decodes the cookie on every authenticated request
3. Email verification flow uses a token stored on the `User` model

## Key Components

**`backend/app/main.py`**
- FastAPI app entry point
- Registers all route routers under `/api` prefix
- Applies CORS, rate-limit, and request-context middleware
- Integrates Sentry for error capture
- Docs endpoints (`/docs`, `/redoc`) are disabled in production

**`backend/app/engine/` — Audit Engine**
- `orchestrator.py`: Top-level coordinator; calls collector, rules, scoring, recommendations in sequence; persists results
- `collector.py`: Reads synced data from DB and aggregates into `AccountAuditSnapshot`
- `rules/base.py`: Abstract `AuditRule` class and registry; `@register_rule` decorator pattern
- `rules/*.py`: 11 concrete rule modules (budget, CPA, CTR, frequency, performance, spend, structure, trend, opportunity, aggregate, account)
- `scoring.py`: Five-pillar weighted scoring model (acquisition 22%, conversion 28%, budget 20%, trend 15%, structure 15%)
- `types.py`: Dataclasses for `Finding`, `AccountAuditSnapshot`, `CampaignAuditMetrics`, `AdSetAuditMetrics`, `ScoreBreakdown`, etc.
- `recommendations.py`: Maps rule IDs to recommendation title/body text

**`backend/app/services/meta_sync.py`**
- Three-class design: `MetaSyncFetchService` (HTTP), `MetaSyncPersistenceService` (upsert), `MetaSyncOrchestrator` (coordination, windowing, progress logging)
- Supports initial sync (90-day lookback) and incremental sync (30-day lookback by default)

**`backend/app/services/ai_summary.py`**
- `AISummaryService` builds a structured prompt from audit findings and posts to the configured AI provider (openai, anthropic, gemini, or mock)
- Returns three fields: `short_executive_summary`, `detailed_audit_explanation`, `prioritized_action_plan`
- Provider selected via `settings.ai_provider`

**`backend/app/services/entitlements.py`**
- `EntitlementService` reads the user's `Subscription` tier and enforces free-tier limits (e.g., max 3 findings, 2 recommendations) on API responses

**`backend/app/services/rate_limit.py`**
- In-memory rate limiting keyed on IP + endpoint; enforced via `enforce_rate_limit()` called at route level and in global middleware
- Separate limits for auth (6 req/5 min), upload (6 req/hr), audit (10 req/hr), global (300 req/min/IP)

**`backend/app/tasks/audit.py` and `backend/app/tasks/sync.py`**
- Celery tasks wrapping orchestrator calls; handle job status transitions (pending → running → completed/failed) and Sentry error capture

**`frontend/src/app/api/proxy/[...path]/route.ts`**
- Catch-all Next.js route handler that proxies all HTTP methods to the backend
- Forwards `Authorization`, `Cookie`, and `Content-Type` headers

**`frontend/src/lib/api.ts`**
- `apiFetch<T>()` wrapper for all frontend API calls; handles 401 (redirect to login), error deserialization, and JSON parsing

**`frontend/src/lib/auth.ts`**
- Client-side auth state: stores user info in `localStorage` (`gsd_user`); `getUser()`, `setUser()`, `clearAuth()`

## Database Schema

**Core entities and relationships:**

```
users
  └─ meta_connections (1:1 per user)
       └─ meta_ad_accounts (1:N per connection)
            ├─ campaigns (N per account)
            │    ├─ ad_sets (N per campaign)
            │    │    ├─ ads (N per ad set)
            │    │    │    └─ daily_ad_insights (N per ad, by date)
            │    │    └─ daily_adset_insights (N per ad set, by date)
            │    └─ daily_campaign_insights (N per campaign, by date)
            ├─ creatives (N per account)
            ├─ daily_account_insights (N per account, by date)
            └─ audit_runs (N per account/user)
                 ├─ audit_findings (N per run)
                 ├─ audit_scores (N per run, one per pillar)
                 ├─ recommendations (N per run, linked to findings)
                 └─ audit_ai_summaries (0-1 per run)

subscriptions (1:1 per user)
sync_jobs (N per user/account)
  └─ sync_job_logs (N per job)
```

All primary keys are UUID strings (36-char). Foreign keys use `CASCADE` deletes. Unique constraints prevent duplicate Meta entity IDs per account (e.g., `uq_campaign_account_meta`).

## API Design

**Style:** REST, versioned at the path level (`/api/` prefix). No API version segment in the URL path; versioning is implicit.

**Auth:** JWT in HttpOnly cookie (`access_token`). No Bearer token in headers except when forwarded by the proxy.

**Key endpoint groups:**

| Prefix | Router file | Purpose |
|---|---|---|
| `POST /api/auth/register` | `routes/auth.py` | User registration with email verification |
| `POST /api/auth/login` | `routes/auth.py` | Login, sets JWT cookie |
| `GET /api/auth/me` | `routes/auth.py` | Current user profile |
| `POST /api/meta/connect` | `routes/meta.py` | Meta OAuth initiation |
| `GET /api/meta/callback` | `routes/meta.py` | Meta OAuth callback |
| `POST /api/sync/trigger` | `routes/sync.py` | Trigger data sync job |
| `GET /api/sync/status/{id}` | `routes/sync.py` | Poll sync job status |
| `POST /api/audit/run` | `routes/audit.py` | Trigger new audit (async) |
| `GET /api/audit/job/{id}` | `routes/audit.py` | Poll audit job status |
| `GET /api/audit/latest` | `routes/audit.py` | Get latest completed audit |
| `GET /api/audit/dashboard` | `routes/audit.py` | Aggregate dashboard data |
| `GET /api/audit/history` | `routes/audit.py` | Audit run history |
| `GET /api/audit/latest/ai-summary` | `routes/audit.py` | Get/generate AI summary |
| `POST /api/billing/...` | `routes/billing.py` | Stripe billing webhooks/checkout |
| `GET /api/health` | `routes/health.py` | Health check |

**Response pattern:** All error responses include `{ detail, code, request_id }`. Validation errors return 422 with the same shape.

**Docs:** OpenAPI (`/docs`, `/redoc`) only available when `settings.debug = True`.

## State Management

**Frontend:**
- No global state manager (no Redux, Zustand, etc.)
- Each page/component manages its own state via `useState` and `useEffect`
- Auth state stored in `localStorage` via helpers in `frontend/src/lib/auth.ts`
- Data is fetched on component mount and on explicit user actions (e.g., sync complete callback)

**Backend:**
- Stateless HTTP layer; all state in PostgreSQL
- Redis used only as Celery broker/result backend (not as application cache)
- Settings loaded once at startup via `@lru_cache()` on `get_settings()`

---

*Architecture analysis: 2026-04-02*
