# Codebase Structure
_Last updated: 2026-04-03_

## Summary

The repository is split into three top-level areas: `backend/` (Python/FastAPI), `frontend/` (Next.js), and `scripts/`. The backend is further divided into `app/` (application code) and `alembic/` (migrations). Within `app/`, code is organized by architectural layer: `routes/`, `services/`, `engine/`, `tasks/`, `models/`, `schemas/`, `middleware/`. The frontend uses Next.js App Router with `src/app/` for pages and `src/components/` for UI components.

---

## Directory Layout

```
meta-ads-audit/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory, middleware, exception handlers
│   │   ├── config.py                # Pydantic Settings (all env vars)
│   │   ├── database.py              # SQLAlchemy engine, SessionLocal, Base, get_db dep
│   │   ├── celery_app.py            # Celery instance and configuration
│   │   ├── logging_config.py        # Structured JSON logger factory
│   │   ├── observability.py         # Sentry init
│   │   ├── engine/
│   │   │   ├── orchestrator.py      # run_audit() and populate_audit_run() — pipeline coordinator
│   │   │   ├── collector.py         # collect_account_data() — reads DB, builds AccountAuditSnapshot
│   │   │   ├── scoring.py           # compute_scores() — five-pillar weighted scoring
│   │   │   ├── recommendations.py   # apply_recommendation() — enriches Finding with text templates
│   │   │   ├── metrics.py           # Pure calc_* helpers (ctr, cpa, cpc, cpm, roas, frequency, wow_delta)
│   │   │   ├── types.py             # Dataclasses: Finding, AccountAuditSnapshot, CampaignAuditMetrics, etc.
│   │   │   └── rules/
│   │   │       ├── base.py          # AuditRule ABC, rule_registry, @register_rule, get_all_rules()
│   │   │       ├── __init__.py      # Imports all rule modules to trigger @register_rule
│   │   │       ├── account_rules.py
│   │   │       ├── aggregate_rules.py
│   │   │       ├── budget_rules.py
│   │   │       ├── cpa_rules.py
│   │   │       ├── ctr_rules.py
│   │   │       ├── frequency_rules.py
│   │   │       ├── opportunity_rules.py
│   │   │       ├── performance_rules.py
│   │   │       ├── spend_rules.py
│   │   │       ├── structure_rules.py
│   │   │       └── trend_rules.py
│   │   ├── routes/
│   │   │   ├── audit.py             # /api/audit/* — run, job status, latest, history, dashboard, AI summary
│   │   │   ├── auth.py              # /api/auth/* — register, login, logout, verify-email, forgot/reset-password
│   │   │   ├── billing.py           # /api/billing/* — subscription management
│   │   │   ├── meta.py              # /api/meta/* — OAuth flow, ad accounts list/select
│   │   │   ├── sync.py              # /api/sync/* — trigger sync, import CSV/XLSX, sync status
│   │   │   ├── health.py            # /api/health — liveness probe
│   │   │   ├── debug.py             # /api/debug/* — debug endpoints (only in debug mode)
│   │   │   └── helpers.py           # Shared route helpers (e.g. get_selected_account)
│   │   ├── services/
│   │   │   ├── ai_summary.py        # AISummaryService — multi-provider AI summary generation
│   │   │   ├── auth.py              # create_user, authenticate_user, create_access_token, password hashing
│   │   │   ├── csv_import.py        # CsvImportService — parse .csv/.xlsx, upsert insights to DB
│   │   │   ├── meta_ads.py          # MetaAdsService — read ad accounts from DB
│   │   │   ├── meta_auth.py         # MetaAuthService — OAuth token exchange, token decryption
│   │   │   ├── meta_sync.py         # MetaSyncFetchService, MetaSyncOrchestrator — Graph API fetch + upsert
│   │   │   ├── meta_mock.py         # generate_mock_sync_payload() — fake data for mock mode
│   │   │   ├── entitlements.py      # EntitlementService — plan tier to feature limits dataclass
│   │   │   ├── rate_limit.py        # enforce_rate_limit() — Redis sliding window
│   │   │   ├── email.py             # send_verification_email, send_password_reset_email (SMTP)
│   │   │   ├── crypto.py            # Fernet encrypt/decrypt for Meta access tokens
│   │   │   ├── resilience.py        # with_http_retries() — httpx retry decorator
│   │   │   └── account_cleanup.py   # Delete orphaned ad account data
│   │   ├── tasks/
│   │   │   ├── audit.py             # run_audit_job Celery task — wraps engine/orchestrator + AI summary
│   │   │   └── sync.py              # run_initial_sync_job, run_incremental_sync_job Celery tasks
│   │   ├── models/
│   │   │   ├── user.py              # User
│   │   │   ├── audit.py             # AuditRun, AuditFinding, AuditScore, Recommendation, AuditAISummary
│   │   │   ├── campaign.py          # Campaign, AdSet, Ad, Creative
│   │   │   ├── insights.py          # DailyAccountInsight, DailyCampaignInsight, DailyAdSetInsight, DailyAdInsight
│   │   │   ├── meta_connection.py   # MetaConnection, MetaAdAccount
│   │   │   ├── subscription.py      # Subscription
│   │   │   └── sync_job.py          # SyncJob, SyncJobLog
│   │   ├── schemas/
│   │   │   ├── audit.py             # Pydantic response models for audit endpoints
│   │   │   ├── auth.py              # Pydantic models for auth endpoints
│   │   │   ├── billing.py           # Pydantic models for billing endpoints
│   │   │   ├── meta.py              # Pydantic models for meta endpoints
│   │   │   ├── sync.py              # Pydantic models for sync endpoints
│   │   │   └── common.py            # Shared response types
│   │   └── middleware/
│   │       └── deps.py              # get_current_user FastAPI dependency (JWT extraction + user resolve)
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       ├── 20260312_0001_phase2_auth_meta.py
│   │       ├── 20260312_0002_phase3_sync_pipeline.py
│   │       ├── 20260312_0003_phase4_audit_engine.py
│   │       ├── 20260313_0004_phase6_ai_summaries.py
│   │       ├── 20260313_0005_phase7_local_subscriptions.py
│   │       ├── 20260320_0006_phase2_auth_hardening.py
│   │       └── 20260320_0007_phase3_async_audit.py
│   ├── tests/
│   │   └── engine/
│   │       └── datasets/            # Test fixture CSV/JSON datasets for engine tests
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── app/                     # Next.js App Router pages
│       │   ├── layout.tsx           # Root layout (fonts, global CSS)
│       │   ├── page.tsx             # Landing/home page
│       │   ├── dashboard/
│       │   │   ├── layout.tsx       # Dashboard shell with sidebar
│       │   │   ├── page.tsx         # Main dashboard (health score, findings, trend, worst performers)
│       │   │   ├── audits/          # Audit history page
│       │   │   ├── meta/            # Meta connection management page
│       │   │   │   └── callback/    # OAuth callback handler page
│       │   │   └── settings/        # User settings page
│       │   ├── login/
│       │   ├── register/
│       │   ├── verify-email/
│       │   ├── forgot-password/
│       │   ├── reset-password/
│       │   ├── terms/
│       │   ├── privacy/
│       │   └── api/
│       │       └── proxy/
│       │           └── [...path]/
│       │               └── route.ts # Catch-all Next.js to FastAPI proxy (forwards cookies + auth headers)
│       ├── components/
│       │   ├── dashboard/           # Dashboard-specific React components
│       │   │   ├── health-score.tsx
│       │   │   ├── findings-list.tsx
│       │   │   ├── ai-summary-block.tsx
│       │   │   ├── pillar-scores.tsx
│       │   │   ├── spend-trend.tsx
│       │   │   ├── trend-widget.tsx
│       │   │   ├── top-opportunities.tsx
│       │   │   ├── worst-performers.tsx
│       │   │   ├── severity-breakdown.tsx
│       │   │   ├── severity-chart.tsx
│       │   │   ├── executive-summary.tsx
│       │   │   ├── data-sync.tsx
│       │   │   ├── meta-connect.tsx
│       │   │   ├── ad-account-selector.tsx
│       │   │   └── sidebar.tsx
│       │   ├── auth/                # Auth form components
│       │   ├── billing/             # Billing/subscription UI components
│       │   ├── landing/             # Landing page components
│       │   └── ui/                  # Generic UI primitives (Spinner, etc.)
│       └── lib/
│           ├── api.ts               # apiFetch() — typed HTTP client with auto-redirect on 401
│           ├── audit.ts             # Type definitions + pure utility functions for audit data
│           └── auth.ts              # getUser(), clearAuth(), session helpers
├── scripts/                         # Root-level utility scripts
├── docker-compose.yml               # All services (postgres, redis, backend, celery-worker, frontend)
├── .github/workflows/               # CI/CD pipeline definitions
└── .planning/codebase/              # GSD codebase analysis documents
```

---

## Module Responsibilities

**`backend/app/engine/orchestrator.py`**
The main pipeline coordinator. `run_audit()` creates an `AuditRun` DB row then delegates to `populate_audit_run()`. `populate_audit_run()` runs the full pipeline: collect → evaluate rules → apply recommendations → dedupe → sort → score → persist findings/scores/recommendations. Called by `backend/app/tasks/audit.py`.

**`backend/app/engine/collector.py`**
Reads from `DailyAccountInsight`, `DailyCampaignInsight`, `DailyAdSetInsight` over a 30-day window. Recalculates all derived metrics (CTR, CPC, CPM, ROAS, CPA) from raw impressions/clicks/spend/conversions — does not trust stored derived values. Returns `AccountAuditSnapshot` with account-level, campaign-level, and ad-set-level `AuditMetrics` dataclasses.

**`backend/app/engine/types.py`**
Shared dataclasses and enums: `DailyMetricPoint`, `CampaignAuditMetrics`, `AdSetAuditMetrics`, `AccountAuditMetrics`, `AccountAuditSnapshot`, `Finding`, `ScoreBreakdown`, `AuditRunResult`, `Severity`, `Category`. This file is the contract between all engine modules — no DB access, no FastAPI imports.

**`backend/app/engine/scoring.py`**
`compute_scores(findings, account_description, total_spend, analysis_days)` — returns `(health_score: float, list[ScoreBreakdown])`. `PILLARS` dict defines five weighted categories. `SEVERITY_PENALTIES` dict (LOW=3, MEDIUM=7, HIGH=12, CRITICAL=18) drives base deductions. No DB access.

**`backend/app/engine/recommendations.py`**
`apply_recommendation(finding)` — looks up `finding.recommendation_key` in a `TEMPLATES` dict and enriches the `Finding` with `recommendation_title` and `recommendation_body` text constructed from metric comparison and qualitative impact. No DB access.

**`backend/app/engine/metrics.py`**
Pure calculation helpers: `calc_ctr`, `calc_cpa`, `calc_cpc`, `calc_cpm`, `calc_roas`, `calc_frequency`, `calc_spend_share`, `calc_wow_delta`. No imports from any other `app` module.

**`backend/app/routes/audit.py`**
The largest route module. Handles 14 endpoints including run, job polling, latest, history, dashboard, and AI summary endpoints. Serializes `AuditRun` ORM rows into Pydantic schemas and adds derived presentation fields (`confidence_label`, `confidence_reason`, `inspection_target`).

**`backend/app/services/ai_summary.py`**
`AISummaryService.generate_for_run(db, run, regenerate=False)` — end-to-end AI summary generation. Routes to `gemini`, `openai`, or `anthropic` provider based on `settings.ai_provider`. Always produces a readable `AuditAISummary` row: if AI fails or provider is `mock`, uses a deterministic fallback built from findings data.

**`backend/app/services/csv_import.py`**
Parses `.csv` or `.xlsx` Meta Ads Manager exports. Handles column alias normalization (English and Russian column names from Meta). Upserts `Campaign`, `AdSet`, `Ad`, and daily insight rows using `UniqueConstraint`-protected upsert patterns.

**`backend/app/services/meta_sync.py`**
`MetaSyncFetchService` — paginated Graph API v19.0 client with `httpx`. `MetaSyncOrchestrator` — orchestrates the full sync sequence: campaigns → adsets → ads → creatives → account insights → campaign insights → adset insights → ad insights. Used by `backend/app/tasks/sync.py`.

**`frontend/src/lib/api.ts`**
`apiFetch<T>(path, options)` — typed `fetch` wrapper. Defaults to `NEXT_PUBLIC_API_URL || "/api/proxy"`. Sends cookies with every request (`credentials: "include"`). Redirects to `/login` on 401 and clears auth state.

**`frontend/src/lib/audit.ts`**
All frontend audit domain types (`AuditReport`, `AuditFinding`, `ScoreBreakdown`, `AuditDashboardData`, etc.) plus pure utility functions: `formatCurrency`, `formatPercent`, `formatFindingMetric`, `formatDate`, `cleanAiSummaryText`, `deriveConfidence`, `deriveDeterministicActionPlan`, `deriveTopActions`, `deriveBiggestLeak`, `analysisWindowDays`.

**`frontend/src/app/api/proxy/[...path]/route.ts`**
Catch-all Next.js Route Handler that proxies every HTTP method to `BACKEND_INTERNAL_URL` (defaults to `http://backend:8000/api`). Forwards cookies and `Authorization` header. Avoids CORS and means the browser never needs a direct route to the backend container.

---

## Naming Conventions

**Backend Python files:** `snake_case.py`. Route files named after the resource: `audit.py`, `auth.py`. Service files named after the service: `ai_summary.py`, `meta_sync.py`. Model files named after the primary model group: `campaign.py` contains Campaign, AdSet, Ad, Creative.

**Frontend files:** Components use `kebab-case.tsx` (e.g. `health-score.tsx`, `ai-summary-block.tsx`). Pages are always `page.tsx`. Layouts are always `layout.tsx`. Lib modules use `kebab-case.ts`.

**Database tables:** Plural `snake_case`: `audit_runs`, `audit_findings`, `meta_ad_accounts`, `insights_daily_campaign`. All PKs are `String(36)` UUIDs. Meta-sourced IDs stored separately: `meta_campaign_id`, `meta_adset_id`, `meta_ad_id`.

---

## Where to Add New Code

**New audit rule:**
1. Add a class to the appropriate module in `backend/app/engine/rules/` (or create a new file)
2. Inherit from `AuditRule`, apply `@register_rule`, set `rule_id`, `category`, `severity`
3. Implement `evaluate(self, snapshot: AccountAuditSnapshot) -> list[Finding]`
4. If creating a new file, import it in `backend/app/engine/rules/__init__.py`
5. Add recommendation template in `backend/app/engine/recommendations.py` TEMPLATES dict keyed by `rule_id`
6. Add `rule_id` to `HIERARCHICAL_RULE_FAMILIES` in `backend/app/engine/orchestrator.py` if the rule fires at both campaign and ad-set level

**New API endpoint:**
1. Add to the relevant file in `backend/app/routes/` (or create a new router module)
2. Add Pydantic request/response schemas to `backend/app/schemas/`
3. If creating a new router, register it in `backend/app/main.py` with `app.include_router(..., prefix="/api")`

**New ORM model:**
1. Add to `backend/app/models/` (new file or appropriate existing file)
2. Ensure the module is imported so Alembic detects it via `Base.metadata`
3. Generate migration: run `alembic revision --autogenerate -m "description"` inside `backend/`
4. Apply: `alembic upgrade head`

**New Celery task:**
1. Add function decorated with `@celery.task` to `backend/app/tasks/audit.py` or `backend/app/tasks/sync.py`
2. Celery auto-discovers everything in the `app.tasks` package (configured in `backend/app/celery_app.py`)

**New frontend page:**
1. Create a directory under `frontend/src/app/` with a `page.tsx` (App Router convention)
2. For dashboard pages: place under `frontend/src/app/dashboard/` to inherit the sidebar layout from `dashboard/layout.tsx`

**New frontend component:**
- Dashboard-specific: `frontend/src/components/dashboard/`
- Auth forms: `frontend/src/components/auth/`
- Generic UI primitive: `frontend/src/components/ui/`

**New shared frontend type or utility:**
- Audit domain types or functions: `frontend/src/lib/audit.ts`
- API call pattern: `frontend/src/lib/api.ts`
- Auth/session utility: `frontend/src/lib/auth.ts`

---

## Special Directories

**`.planning/codebase/`**
GSD codebase analysis documents. Read by `/gsd:plan-phase` and `/gsd:execute-phase`. Not part of application runtime.

**`backend/alembic/versions/`**
Alembic migration scripts. Generated via `alembic revision`. Committed: yes. Apply with `alembic upgrade head` inside `backend/`.

**`backend/tests/engine/datasets/`**
Test fixture data (CSV/JSON files) used by engine unit tests. Committed: yes.

**`frontend/.next/`**
Next.js build output. Generated: yes. Not committed.

**`frontend/node_modules/`**
npm packages. Generated: yes. Not committed.

---

*Structure analysis: 2026-04-03*
