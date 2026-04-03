# Architecture
_Last updated: 2026-04-03_

## Summary

Meta Ads Audit is a layered monolith with a FastAPI backend and Next.js frontend. All long-running work (audit engine, Meta API sync) runs inside Celery workers backed by Redis, keeping HTTP routes non-blocking. The audit engine is a pure-Python deterministic pipeline (collector → rules → recommendations → scoring → persist) that never writes to the DB except through the orchestrator.

---

## System Components

```
Browser → Next.js (port 3000)
             ↓ /api/proxy/[...path]  (Next.js catch-all route)
          FastAPI (port 8000)
             ↓ Celery .delay()
          Redis (port 6379) — broker + result backend
             ↓
          Celery Worker (concurrency=2)
             ↓
          PostgreSQL (port 5432)
```

**Docker Compose services:**
- `frontend` — Next.js 14, port 3000
- `backend` — FastAPI/uvicorn, port 8000
- `celery-worker` — same Docker image as backend; command overridden to `celery worker --concurrency=2`
- `redis` — Redis 7, broker and Celery result backend
- `postgres` — PostgreSQL 16
- `mailpit` (local-tools profile) — local SMTP trap, ports 1025/8025
- `adminer` (local-tools profile) — DB GUI, port 8080

---

## Layers

**API Layer:**
- Purpose: Validate requests, enforce auth and rate limits, dispatch to services or Celery tasks, serialize responses
- Location: `backend/app/routes/`
- Files: `audit.py`, `auth.py`, `billing.py`, `meta.py`, `sync.py`, `health.py`, `debug.py`, `helpers.py`
- Depends on: services, tasks, middleware, schemas
- Used by: frontend via Next.js proxy at `frontend/src/app/api/proxy/[...path]/route.ts`

**Service Layer:**
- Purpose: Business logic not tied to the HTTP request lifecycle
- Location: `backend/app/services/`
- Files: `ai_summary.py`, `auth.py`, `csv_import.py`, `meta_ads.py`, `meta_auth.py`, `meta_sync.py`, `entitlements.py`, `rate_limit.py`, `email.py`, `crypto.py`, `resilience.py`, `account_cleanup.py`, `meta_mock.py`
- Depends on: models, config
- Used by: routes, tasks

**Engine Layer:**
- Purpose: Pure-Python deterministic audit pipeline — reads DB through collector, never writes directly
- Location: `backend/app/engine/`
- Files: `orchestrator.py`, `collector.py`, `rules/`, `scoring.py`, `recommendations.py`, `types.py`, `metrics.py`
- Depends on: models (read-only via collector), types
- Used by: `backend/app/tasks/audit.py`

**Task Layer:**
- Purpose: Celery task entry points; wrap engine and service calls with job-status lifecycle management
- Location: `backend/app/tasks/`
- Files: `audit.py`, `sync.py`
- Depends on: engine, services, models
- Used by: routes (via `.delay()`)

**Data Layer:**
- Purpose: SQLAlchemy ORM models; all PKs are UUID strings
- Location: `backend/app/models/`
- Files: `user.py`, `audit.py`, `campaign.py`, `insights.py`, `meta_connection.py`, `subscription.py`, `sync_job.py`
- Depends on: `backend/app/database.py`
- Used by: all other layers

**Frontend Layer:**
- Purpose: Next.js App Router UI; data fetched client-side via `apiFetch` in `frontend/src/lib/api.ts`
- Location: `frontend/src/`
- Pages: `app/` (dashboard, login, register, verify-email, reset-password, terms, privacy)
- Components: `components/dashboard/`, `components/auth/`, `components/billing/`, `components/ui/`
- Lib: `lib/api.ts`, `lib/audit.ts`, `lib/auth.ts`
- Depends on: backend via catch-all proxy

---

## Data Flow: Audit Run (Primary Flow)

```
1. POST /api/audit/run
      → audit.py route: validates auth, checks entitlements, creates AuditRun row (job_status="pending")
      → run_audit_job.delay(run.id) dispatched to Celery via Redis
      → Returns AuditJobResponse { job_id, status: "pending" }

2. Celery picks up audit.run_audit_job (backend/app/tasks/audit.py)
      → Sets AuditRun.job_status="running"
      → Calls populate_audit_run(db, run) from backend/app/engine/orchestrator.py

3. Engine pipeline inside populate_audit_run:
      a. collect_account_data(db, ad_account_id)
            - Queries DailyAccountInsight, DailyCampaignInsight, DailyAdSetInsight (30-day window)
            - Recalculates CTR/CPC/CPM/ROAS/CPA from raw counts (ignores stored values)
            - Builds AccountAuditSnapshot with account + campaigns[] + ad_sets[] + data_mode
      b. For each rule in get_all_rules():
            rule.evaluate(snapshot) → list[Finding]
      c. apply_recommendation(finding) for each Finding
            - Enriches recommendation_title + recommendation_body from TEMPLATES dict
      d. _dedupe_hierarchical_findings()
            - Suppresses ad_set-level findings when matching campaign-level finding already fired
      e. findings.sort() by SEVERITY_ORDER (critical → high → medium → low)
      f. compute_scores(findings, account_description, total_spend, analysis_days)
            - Five pillars subtract weighted penalties from 100 per finding
            - Returns (health_score: float, list[ScoreBreakdown])
      g. Persist: AuditFinding rows, Recommendation rows, AuditScore rows → db.commit()

4. AISummaryService.generate_for_run(db, run, regenerate=True)
      → Builds JSON payload from findings metadata
      → Routes to Gemini / OpenAI / Anthropic or deterministic fallback
      → Persists AuditAISummary row (status="completed" or "failed")

5. Task sets AuditRun.job_status="completed"; on exception sets "failed" + job_error

6. Frontend polls GET /api/audit/job/{job_id} until status not in {"pending","running"}
      → On "completed": fetches GET /api/audit/latest (full AuditRunResponse)
      → Dashboard renders findings, scores, AI summary
```

---

## Data Flow: Meta Sync

```
1. POST /api/sync/start → creates SyncJob row → run_initial_sync_job.delay(job_id) or run_incremental_sync_job.delay(job_id)

2. Celery worker (backend/app/tasks/sync.py)
      → MetaSyncOrchestrator.run(db, job, mock_payload=None)
      → MetaSyncFetchService fetches from Meta Graph API (v19.0):
           - Campaigns, AdSets, Ads, Creatives via /act_{id}/campaigns etc.
           - Daily insights via /act_{id}/insights with day breakdown
      → Upserts Campaign, AdSet, Ad, Creative, DailyInsight rows (INSERT ... ON CONFLICT UPDATE)
      → Retries on httpx.TimeoutException, HTTP 429/5xx (max_retries=2)

3. POST /api/sync/import-report (CSV/XLSX upload path)
      → CsvImportService.import_report() normalizes column aliases (EN + RU)
      → Upserts same DB tables without calling Meta API
```

---

## Rule Engine Architecture

**Registration system:**
- `backend/app/engine/rules/base.py` — defines `AuditRule` ABC and `rule_registry: list`
- `@register_rule` decorator appends a class to `rule_registry` at import time
- `get_all_rules()` instantiates all registered classes fresh on each audit run
- `backend/app/engine/rules/__init__.py` imports all rule modules, triggering `@register_rule` decorators

**Rule contract:**
```python
class AuditRule(ABC):
    rule_id: str        # e.g. "ctr_low_campaign"
    category: Category  # enum: CTR, CPA, BUDGET, TREND, STRUCTURE, etc.
    severity: Severity  # enum: LOW, MEDIUM, HIGH, CRITICAL

    def evaluate(self, snapshot: AccountAuditSnapshot) -> list[Finding]: ...
    def finding(self, **kwargs) -> Finding: ...  # convenience builder
```

**Rule modules** (all in `backend/app/engine/rules/`):

| Module | Focus |
|---|---|
| `account_rules.py` | Account-level weak CTR, weak CVR funnel |
| `aggregate_rules.py` | Cross-entity comparisons (winner/loser reallocation) |
| `budget_rules.py` | Budget concentration risk, underfunded winners |
| `cpa_rules.py` | CPA above threshold at campaign and ad set level |
| `ctr_rules.py` | CTR below threshold at campaign/ad set; declining CTR trend |
| `frequency_rules.py` | High frequency / ad fatigue |
| `opportunity_rules.py` | Inefficient ad set vs siblings, objective mismatch |
| `performance_rules.py` | High spend + low conversions, low ROAS + high spend |
| `spend_rules.py` | Uneven daily spend pacing, spend spike anomalies |
| `structure_rules.py` | Placement efficiency |
| `trend_rules.py` | ROAS drop anomaly, CPA deterioration |

**Deduplication** (`backend/app/engine/orchestrator.py`):
- `HIERARCHICAL_RULE_FAMILIES` maps child rule IDs to family keys (e.g. `"ctr_low_adset"` → `"ctr_low"`)
- `_dedupe_hierarchical_findings()` suppresses ad_set findings when matching campaign finding in same family already fired

---

## Scoring System

**File:** `backend/app/engine/scoring.py`

Five pillars, each subtracts weighted penalties from 100 per relevant finding:

| Pillar | Weight | Category mapping |
|---|---|---|
| acquisition | 22% | PERFORMANCE, ACCOUNT, CTR |
| conversion | 28% | PERFORMANCE, OPPORTUNITY, CPA |
| budget | 20% | BUDGET, OPPORTUNITY |
| trend | 15% | TREND, FREQUENCY |
| structure | 15% | STRUCTURE, PLACEMENT |

Penalty formula per finding:
```
base_penalty × scope_multiplier × (1 + impact_ratio)
  × confidence_multiplier × persistence_multiplier × metric_signal_multiplier
```

Composite health score = weighted sum of pillar scores, clamped [0, 100], rounded to 1 decimal.

Severity base penalties: LOW=3, MEDIUM=7, HIGH=12, CRITICAL=18.

---

## AI Summary Pipeline

**File:** `backend/app/services/ai_summary.py`, class `AISummaryService`

1. `_build_structured_input(run)` — JSON payload: `{ data_mode, limitations, health_score, total_spend, findings[] }` (top findings sorted by severity then estimated_waste)
2. Provider routing via `settings.ai_provider`: `"gemini"` → `_gemini_request`, `"openai"` → `_openai_request`, `"anthropic"` → `_anthropic_request`, `"mock"/"none"` → deterministic fallback
3. Gemini uses `responseSchema` enforcing three JSON keys: `short_executive_summary`, `detailed_audit_explanation`, `prioritized_action_plan`; `temperature=0.1`
4. `_normalize_output()` resolves key aliases across providers
5. `_action_plan_is_generic()` checks for vague phrases; replaces with `_fallback_action_plan()` when triggered
6. Fallback always produces actionable output from findings data (severity, entity name, metric vs threshold, per-category next-step text)
7. Persists `AuditAISummary` with `status="completed"` or `status="failed"`; the UI never receives an empty summary

---

## Auth Flow

**Token type:** HS256 JWT, delivered as HttpOnly `access_token` cookie; also accepted via `Authorization: Bearer` header.

**Registration → Verification → Login:**
1. `POST /api/auth/register` → hashes password with `pbkdf2_sha256`, sends verification email; returns `verification_url` in JSON if SMTP is not configured
2. `GET /api/auth/verify-email?token=…` → sets `email_verified=True`, issues JWT, sets HttpOnly cookie
3. `POST /api/auth/login` → validates hash, requires `email_verified=True` (bypassed in `debug` mode), issues JWT

**Auth dependency:** `backend/app/middleware/deps.py` — `get_current_user()`
- Reads cookie first, then `Authorization: Bearer` header
- Decodes JWT with `python-jose`; resolves active `User` from DB
- Stores `user_id` on `request.state` for structured logging

**Logout:** deletes `access_token` cookie; stateless JWT — no server-side revocation.

**Password reset:** `forgot-password` stores `secrets.token_urlsafe(32)` in `user.email_verify_token`, emails reset link; `reset-password` re-hashes and clears token.

---

## Data Model

```
User
├── MetaConnection (1:1 per user)
│   └── MetaAdAccount[] (one marked is_selected=True)
│       ├── Campaign[]
│       │   ├── AdSet[] → Ad[] → Creative
│       │   └── DailyCampaignInsight[]
│       ├── DailyAccountInsight[]
│       ├── DailyAdSetInsight[]
│       └── DailyAdInsight[]
├── AuditRun[]
│   ├── AuditFinding[]
│   ├── AuditScore[]
│   ├── Recommendation[]
│   └── AuditAISummary (1:1)
├── SyncJob[]
│   └── SyncJobLog[]
└── Subscription (1:1)
```

Key tables and their primary columns:

| Model | Table | Key Columns |
|---|---|---|
| `User` | `users` | `id`, `email`, `hashed_password`, `email_verified`, `email_verify_token` |
| `MetaConnection` | `meta_connections` | `user_id`, `encrypted_access_token`, `token_expires_at`, `oauth_state_hash` |
| `MetaAdAccount` | `meta_ad_accounts` | `connection_id`, `account_id`, `is_selected`, `currency`, `timezone` |
| `Campaign` | `campaigns` | `ad_account_id`, `meta_campaign_id`, `status`, `objective`, `daily_budget` |
| `AdSet` | `ad_sets` | `campaign_id`, `meta_adset_id`, `optimization_goal`, `bid_strategy` |
| `Ad` | `ads` | `ad_set_id`, `meta_ad_id`, `creative_pk` |
| `DailyAccountInsight` | `insights_daily_account` | `ad_account_id`, `date`, `impressions`, `clicks`, `spend`, `conversions`, `roas`, `frequency` |
| `DailyCampaignInsight` | `insights_daily_campaign` | `campaign_id`, `date`, same metrics |
| `DailyAdSetInsight` | `insights_daily_adset` | `ad_set_id`, `date`, same metrics |
| `AuditRun` | `audit_runs` | `user_id`, `ad_account_id`, `health_score`, `job_status`, `celery_task_id`, `analysis_start`, `analysis_end` |
| `AuditFinding` | `audit_findings` | `audit_run_id`, `rule_id`, `severity`, `category`, `entity_type`, `entity_id`, `estimated_waste`, `score_impact` |
| `AuditScore` | `audit_scores` | `audit_run_id`, `score_key`, `score`, `weight` |
| `Recommendation` | `recommendations` | `audit_run_id`, `audit_finding_id`, `recommendation_key`, `title`, `body` |
| `AuditAISummary` | `audit_ai_summaries` | `audit_run_id`, `provider`, `model`, `status`, three summary text columns, `input_payload_json` |
| `SyncJob` | `sync_jobs` | `user_id`, `ad_account_id`, `sync_type`, `status`, `celery_task_id`, `progress`, `current_step` |
| `Subscription` | `subscriptions` | `user_id`, `plan_tier`, `stripe_customer_id`, `stripe_subscription_id` |

All insight tables have a `UniqueConstraint` on `(entity_id, date)` to support safe upserts.

---

## Cross-Cutting Concerns

**Logging:** Structured JSON via `backend/app/logging_config.py` — every event carries `code`, `request_id`, `user_id` extras. Request lifecycle logged by `request_context_middleware` in `backend/app/main.py`.

**Error handling:** Global exception handler in `backend/app/main.py` normalizes all errors to `{ detail, code, request_id }`. Sentry captures all 5xx exceptions and Celery task failures (`backend/app/observability.py`).

**Rate limiting:** `backend/app/services/rate_limit.py` — Redis-backed sliding window per IP or user. Keys: `auth`, `sync:import_report`, `sync:start`, `audit:run`, `global` (300 req/min backstop via middleware).

**CORS:** Configured in `backend/app/main.py` with `settings.cors_origins`; credentials allowed.

**Entitlements:** `backend/app/services/entitlements.py` — `EntitlementService.get_entitlements()` returns an `Entitlements` dataclass (max_findings, max_ad_accounts, etc.) based on `Subscription.plan_tier`. Routes check entitlements before serializing findings.

**DB migrations:** Alembic in `backend/alembic/versions/` — 7 migration files (`20260312_0001` through `20260320_0007`) covering auth, sync pipeline, audit engine, AI summaries, subscriptions, auth hardening, and async audit.

---

*Architecture analysis: 2026-04-03*
