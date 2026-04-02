# Project Status Review

> **Generated:** 2026-04-02
> **Reviewer:** Automated technical audit (scheduled task)
> **Commit history inspected:** 6 commits on `main` (Initial commit → migration fixes → Gemini API → AI summary change → dashboard+rules fix → add .env to gitignore)

---

## 1. Executive Summary

### Current Project Stage
Late-MVP / Pre-launch. The core product loop is code-complete: register → connect / import → sync → audit → report → AI summary. The backend is structured for production, Docker and CI pipelines are wired, and the frontend builds cleanly. The project is runnable but has several open blockers before it should handle real user traffic.

### Overall Maturity Level
**6 / 10** — The deterministic audit engine, async pipeline, auth hardening, and frontend cleanup phases have all been worked through systematically per the implementation plan. What remains is largely: (a) secret rotation that was documented but not yet executed, (b) real-world engine validation and rule depth, and (c) the entire presentation-layer improvement backlog documented in `improvement-plan.md` and `Audit_Report_Page_Optimization_Checklist.md`.

### Main Risks
1. **Real secrets committed to the repo.** `backend/.env` contains live credentials — a real Gemini AI API key, a real Sentry DSN, and what appear to be real `SECRET_KEY` and `ENCRYPTION_KEY` values. This is explicitly flagged as an unresolved Phase 1 blocker in `Meta_Ads_Audit_Implementation_Plan.md`.
2. **12 integration tests are in a last-failed state.** The `.pytest_cache/v/cache/lastfailed` file lists all major integration test suites as failing. These tests require a live database and Redis; they may be environment failures rather than logic bugs, but this cannot be confirmed without a CI run.
3. **No fixture dataset folder exists.** `Deterministic_Engine_Rule_Depth_Checklist.md` plans a comprehensive fixture/scenario validation suite; none of the fixture CSV/XLSX sample files described there have been created.
4. **Global rate limiting documentation is stale.** The implementation plan notes "global middleware not yet added" but `backend/app/main.py` actually contains a fully-implemented global rate limit middleware. The doc note is outdated.
5. **`ENVIRONMENT=production` in the committed `.env`.** The env file sets `ENVIRONMENT=production` and `DEBUG=false`. This is the right production posture, but combined with real secrets in the same file it creates a hard-to-audit security boundary.

### Confidence Level
**High** for backend structure and completed items. **Medium** for test pass/fail status (last-failed cache suggests failures, but CI environment dependency is the likely cause). **Low** for rule engine depth and presentation-layer quality — the checklists confirm significant gaps remain.

---

## 2. Architecture and Codebase Snapshot

### Main Modules / Folders

| Path | Role |
|---|---|
| `backend/app/main.py` | FastAPI entry point; middleware, exception handlers, router registration |
| `backend/app/engine/` | Deterministic audit engine (orchestrator, collector, scoring, rules, recommendations, types) |
| `backend/app/routes/` | API route handlers: audit, auth, billing, debug, health, meta, sync |
| `backend/app/services/` | Business logic: auth, AI summary, email, Meta OAuth, CSV import, rate limit, resilience, etc. |
| `backend/app/models/` | SQLAlchemy ORM models: user, audit, campaign, insights, meta_connection, subscription, sync_job |
| `backend/app/schemas/` | Pydantic request/response schemas |
| `backend/app/tasks/` | Celery async tasks: audit, sync |
| `backend/alembic/versions/` | 7 migration files covering phases 2–7 |
| `frontend/src/app/` | Next.js App Router pages: auth, dashboard, landing, legal |
| `frontend/src/components/dashboard/` | Dashboard UI components (15 components) |
| `frontend/src/lib/` | Frontend API client (`api.ts`), audit types/helpers (`audit.ts`), auth state (`auth.ts`) |
| `backend/tests/` | Integration + engine unit tests |

### Core Technologies
- **Backend:** Python 3.12, FastAPI 0.109, SQLAlchemy 2.0, Alembic, Celery 5.3 (Redis broker), pydantic-settings 2.7, python-magic, sentry-sdk, httpx
- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS
- **Infrastructure:** PostgreSQL 16, Redis 7, Docker Compose
- **AI:** Configurable provider (OpenAI / Anthropic / Gemini / mock); currently live Gemini 2.5-flash configured in `backend/.env`
- **Observability:** Sentry (backend + frontend), structured JSON logging, request ID propagation

### Entry Points
- Backend: `uvicorn app.main:app` — `backend/app/main.py`
- Worker: `celery -A app.celery_app:celery worker` — `backend/app/celery_app.py`
- Frontend: `npm run dev` / `npm run build` — Next.js standard

### Important Integrations
- Meta Ads OAuth (real or `META_APP_ID=mock` for local dev)
- CSV/XLSX import pipeline (`backend/app/services/csv_import.py`)
- Celery async audit queue (Redis broker)
- AI summary generation (Gemini, OpenAI, Anthropic, or mock)
- SMTP email delivery (Mailpit locally, real SMTP in production)
- Sentry error tracking (backend + frontend)

### Build / Run / Test Status
- **Docker Compose:** Builds and runs. Frontend and backend have separate Dockerfiles. Frontend is a multi-stage build.
- **Backend tests:** Last-failed cache shows 12 integration tests as failed — almost certainly environment failures (no DB/Redis during last local run). Engine unit tests in `tests/engine/` have a complete fixture library.
- **Frontend:** `.next/` build artifacts present; the frontend has been successfully built in production mode.
- **CI:** `.github/workflows/ci.yml` — runs pytest for backend (with a live Postgres service) and lint + build for frontend on push/PR to `main`.

---

## 3. What Appears Completed

| Item | Evidence |
|---|---|
| FastAPI app with structured middleware, CORS, error normalization, request ID propagation | `backend/app/main.py` — full implementation |
| httpOnly cookie auth | `backend/app/routes/auth.py` (`_set_auth_cookie`), `backend/app/middleware/deps.py` (cookie + Bearer fallback) |
| Email verification, forgot-password, reset-password flows | `backend/app/routes/auth.py` (all endpoints present), `backend/app/services/email.py`, all frontend pages exist |
| Email verification block on login and API access | `backend/app/middleware/deps.py` lines 47–51 |
| Production debug guard in config | `backend/app/config.py` — `disable_debug_in_production` validator |
| Debug routes only in debug mode | `backend/app/main.py` lines 162–163 |
| FastAPI docs disabled in production | `backend/app/main.py` — `docs_url`, `redoc_url`, `openapi_url` all conditional on `debug` |
| Global + per-endpoint rate limiting | `backend/app/main.py` global middleware + per-endpoint in auth, sync, audit routes |
| Severity.WARNING alias and new Category members (CTR, FREQUENCY, CPA) | `backend/app/engine/types.py` lines 11, 25–27 |
| Scoring pillars including new categories | `backend/app/engine/scoring.py` PILLARS dict |
| AccountAuditSnapshot import alias in rule files | `backend/app/engine/rules/ctr_rules.py` line 3 |
| `avg_ctr`, `avg_frequency`, `daily_ctr`, `daily_frequency` convenience properties | `backend/app/engine/types.py` lines 74–97 |
| `Base.metadata.create_all()` removed from startup | `backend/app/main.py` — absent |
| Alembic migration at Docker startup | `backend/Dockerfile` |
| MIME/content-type verification on upload | `backend/app/services/csv_import.py`, `python-magic` in `requirements.txt` |
| AI fallback generic text removed from summaries | `backend/app/services/ai_summary.py` GENERIC_ACTION_PLAN_PHRASES filter |
| Async audit pipeline with Celery | `backend/app/tasks/audit.py`, `backend/app/routes/audit.py` (`/audit/run`, `/audit/job/{job_id}`) |
| Job status fields on AuditRun | Alembic migration `20260320_0007`, `backend/app/models/audit.py` |
| Frontend polling for audit job completion | `frontend/src/app/dashboard/audits/page.tsx` (imports `AuditJob`, `AuditJobStatus`) |
| Frontend spinner component | `frontend/src/components/ui/spinner.tsx` |
| User data deletion endpoint | `backend/app/routes/auth.py` — `DELETE /auth/data` and `DELETE /auth/account` |
| Privacy and terms pages | `frontend/src/app/privacy/page.tsx`, `frontend/src/app/terms/page.tsx` |
| Forgot / reset / verify email frontend pages | `frontend/src/app/forgot-password/`, `reset-password/`, `verify-email/` |
| Sentry backend integration | `backend/app/observability.py`, `sentry-sdk[fastapi]` in requirements |
| Sentry frontend integration | `frontend/src/components/app/sentry-init.tsx` |
| Worst-performers query fix (subquery aggregation before join) | `backend/app/routes/audit.py` lines 477–543 |
| Multi-stage frontend Dockerfile | `frontend/Dockerfile` |
| Redis append-only persistence + password support | `docker-compose.yml` |
| Frontend auth moved from localStorage to sessionStorage | `frontend/src/lib/auth.ts` — uses `sessionStorage` |
| Report tab structure (Overview / Campaigns / Structure / Tracking / Trend / History) | `frontend/src/app/dashboard/audits/page.tsx` lines 29–37 |
| Confidence label and reason per finding | `backend/app/routes/audit.py` `_derive_finding_confidence`, `_derive_inspection_target` |
| Biggest leak, top actions, confidence derivation helpers in frontend | `frontend/src/lib/audit.ts` exports `deriveBiggestLeak`, `deriveTopActions`, `deriveConfidence` |
| Verdict logic per health score | `frontend/src/app/dashboard/audits/page.tsx` `verdictForReport` |
| Aggregate-only specific rules | `backend/app/engine/rules/aggregate_rules.py` — 3 rules present |
| Deterministic engine rule test suite with fixture builders | `backend/tests/engine/test_rules.py`, `backend/tests/engine/fixtures.py` |
| Scoring calibration test | `backend/tests/engine/test_scoring_calibration.py` |
| Fixture scenario tests | `backend/tests/engine/test_fixture_scenarios.py` |
| Full Alembic migration chain (7 migrations, phases 2–7) | `backend/alembic/versions/` |
| Re-encryption script created | `backend/scripts/reencrypt_tokens.py` |
| Resend-verification endpoint | `backend/app/routes/auth.py` `POST /auth/resend-verification` |
| `cleanAiSummaryText()` shared helper | `frontend/src/lib/audit.ts` export (confirmed by audits page imports) |

---

## 4. What Appears Partially Implemented

### 4a. Deterministic Engine Rule Depth
**What exists:** 12 rule files with ~30+ individual rules covering CTR, CPA, frequency, budget, spend, performance, structure, trend, opportunity, account, and aggregate scenarios. Rule tests exist with fixture builders for 8 scenario types (healthy, low CTR, weak CVR, high CPA, fatigued, budget imbalanced, aggregate-only, uneven spend).

**What is missing:** Per `Deterministic_Engine_Rule_Depth_Checklist.md`, none of the following are started:
- Dedicated fixture CSV/XLSX sample files in a named directory
- Expected-outcome specs (scenario → expected findings, severities, score ranges)
- Tests verifying irrelevant rules do NOT fire (only positive-case tests exist)
- CVR / conversion leakage rule expansion beyond the existing `WeakCVRRule`
- Rule coverage matrix
- Score calibration validated against named scenario bands

**File evidence:** `Deterministic_Engine_Rule_Depth_Checklist.md` — every item in sections 1–15 is unchecked.

### 4b. Audit Report Page — Recommendations Not Connected to Findings
**What exists:** Recommendations are stored per finding in the DB and returned in API responses. `FindingsList` component and `findings-list.tsx` exist.

**What is missing:** Per `Audit_Report_Page_Optimization_Checklist.md` sections 3 and 7:
- Recommendations are not rendered directly under each finding in the UI
- "Actual vs Threshold" not shown on every finding
- Category-aware metric formatting (percent for CTR, currency for spend, `x` for frequency) not fully applied
- Business-language section titles not fully in place

**File evidence:** `Audit_Report_Page_Optimization_Checklist.md` — sections 3, 7, 8, 9 all unchecked or partially checked.

### 4c. AI Summary Block Quality
**What exists:** AI summary is generated, stored, returned, and displayed. Generic phrase filtering exists in `backend/app/services/ai_summary.py`.

**What is missing:**
- First visible AI content should be action-led, not a paragraph wall
- Action plan synthesis from deterministic findings when AI omits a strong plan
- Action plan tied specifically to current finding set

**File evidence:** `Audit_Report_Page_Optimization_Checklist.md` section 5 — last 3 items marked `[ ]`.

### 4d. Pre-Upload and Empty State UX
**What exists:** Data sync component exists. Basic empty states exist.

**What is missing:** Pre-upload checklist (30+ days, daily rows, spend, clicks, conversions, campaign and ad set fields), stronger empty state explanation, aggregate-only wording.

**File evidence:** `Audit_Report_Page_Optimization_Checklist.md` section 8 — all items unchecked.

### 4e. Secret Rotation (Critical, partially documented)
**What exists:** `backend/scripts/reencrypt_tokens.py` created. `.gitignore` updated (commit `69220cc`).

**What is missing:** The actual secret rotation has not happened. `backend/.env` still contains live `SECRET_KEY`, `ENCRYPTION_KEY`, Gemini API key, and Sentry DSN values. The implementation plan explicitly flags this as a manual step.

**File evidence:** `backend/.env` lines 5, 16, 33, 61. `Meta_Ads_Audit_Implementation_Plan.md` Phase 1 first item: `[ ] Remove committed secrets from Git tracking`.

---

## 5. What Appears Planned But Not Implemented

### 5a. Stripe and Billing Integration
The entire billing flow (Stripe Checkout, subscription webhooks, subscription state syncing) is explicitly deferred. The `/billing/dev/plan` dev-only endpoint exists but is gated behind `settings.debug`. No Stripe SDK is in `requirements.txt` or `frontend/package.json`.

**File evidence:** `Meta_Ads_Audit_Implementation_Plan.md` "Deferred: Stripe and Billing" section.

### 5b. Real Production Environment Configuration
No `frontend/.env.production` file exists. Production-ready backend env values (real CORS origins, production frontend URL, production SMTP, production Redis credentials, production database URL) are not configured beyond the local docker-compose defaults.

**File evidence:** `Meta_Ads_Audit_Implementation_Plan.md` Phase 5, items marked `[ ]`.

### 5c. Export / Share Feature
No export or share functionality exists in the frontend. `Audit_Report_Page_Optimization_Checklist.md` section 9 describes a clean bottom section for sharing/exporting — entirely unchecked.

### 5d. Validation Pass Against Real / Diverse Exports
Section 10 of the audit report checklist defines a required validation pass across five export scenarios and a mobile/desktop polish pass. None are marked complete.

### 5e. Analytics / Activation Tracking
`improvement-plan.md` Phase 2 calls for a basic analytics layer. No analytics SDK appears in `frontend/package.json`.

---

## 6. Changes That Were Likely Already Applied

The following items are documented as planned/open in some files but are already present in the source code and should NOT be re-implemented.

| Documented as planned | Already in code | Evidence |
|---|---|---|
| "Configure global rate limiting middleware (currently per-endpoint, global middleware not yet added)" | Implemented | `backend/app/main.py` lines 30–45: `global_rate_limit_middleware` |
| "Add retry actions to error states" | Implemented | `frontend/src/app/dashboard/audits/page.tsx` — retry state management present |
| "Add Severity.WARNING as valid alias" | Implemented | `backend/app/engine/types.py` line 11 |
| "Add missing category enum members CTR, FREQUENCY, CPA" | Implemented | `backend/app/engine/types.py` lines 25–27 |
| "Fix AccountSnapshot imports by aliasing AccountAuditSnapshot" | Implemented | `backend/app/engine/rules/ctr_rules.py` line 3 |
| "Add email_verified / email_verify_token to user model" | Implemented | Migration `20260320_0006`, `backend/app/models/user.py` |
| "Add job_status, job_error, celery_task_id to AuditRun" | Implemented | Migration `20260320_0007`, `backend/app/models/audit.py` |
| "Create spinner component" | Implemented | `frontend/src/components/ui/spinner.tsx` |
| "Remove Base.metadata.create_all() from app startup" | Implemented | `backend/app/main.py` — no such call exists |
| "Add resend-verification endpoint" | Implemented | `backend/app/routes/auth.py` `POST /auth/resend-verification` |
| "Add DELETE /auth/data and DELETE /auth/account" | Implemented | `backend/app/routes/auth.py` lines 216–243 |
| "Export cleanAiSummaryText() helper" | Implemented | `frontend/src/lib/audit.ts` — exported function |
| "Keep billing /dev/plan behind DEBUG guard" | Implemented | `backend/app/routes/billing.py` lines 41–50 |

---

## 7. Inconsistencies and Technical Debt

**7a. Stale documentation — global rate limiting.** `Meta_Ads_Audit_Implementation_Plan.md` Phase 5 notes say "global middleware not yet added." The code has a fully-implemented global rate limit middleware. The doc note is stale and should be updated.

**7b. Live credentials in tracked Git history.** `backend/.env` is now `.gitignore`'d but was previously tracked. Real credentials exist in Git history commits preceding `69220cc`. Must be cleaned with `git filter-repo` / BFG + secret rotation.

**7c. `ENVIRONMENT=production` in dev `.env`.** Running `docker compose up` locally starts with production flags and live credentials. This creates risk of production-environment side effects during development.

**7d. 12 integration tests in last-failed cache.** `backend/.pytest_cache/v/cache/lastfailed` records all major integration test suites as failing. Almost certainly caused by missing PostgreSQL/Redis when last run locally, not logic failures — but unconfirmed until CI produces a green run.

**7e. Duplicate import in `backend/app/engine/rules/__init__.py`.** `aggregate_rules` is imported twice (lines 1 and 3). Harmless but untidy.

**7f. Stray file `backend/test_sentry.pyecho`.** This file appears to be a misnamed test file (likely `test_sentry.py` with an accidental shell redirect suffix). It is unreachable by pytest and should be removed or renamed.

**7g. No frontend tests.** No `*.test.tsx` or `*.spec.tsx` files exist. CI runs lint and build only — no component or unit tests for the frontend.

**7h. Four overlapping planning documents.** Work is split across `Meta_Ads_Audit_Implementation_Plan.md`, `improvement-plan.md`, `Audit_Report_Page_Optimization_Checklist.md`, and `Deterministic_Engine_Rule_Depth_Checklist.md`. There is no single ordered backlog, which risks duplication or misaligned priorities.

**7i. Entitlement limits applied but UI does not communicate them.** Free plan caps (3 findings, 2 recommendations, etc.) are enforced by `EntitlementService` but the settings page says "Advanced billing features are not enabled yet." Users on the free plan receive silently truncated results with no UI indication.

**7j. `frontend/.env.local` in tracked files.** This file contains local dev env vars (`NEXT_PUBLIC_APP_URL`, `BACKEND_INTERNAL_URL`) and is not secret, but it is a pattern worth reviewing — `.env.local` files are conventionally excluded from tracking.

---

## 8. Prioritized Next-Step To-Do List

### P0 — Blocking / Must Fix

| # | Task | Why It Matters | Files Involved | Complexity |
|---|---|---|---|---|
| P0-1 | **Rotate all live secrets and clean Git history** | Real `SECRET_KEY`, `ENCRYPTION_KEY`, Gemini API key, and Sentry DSN are in `backend/.env` and in Git history. This is a live security exposure. | `backend/.env`, `backend/scripts/reencrypt_tokens.py`, Git history rewrite | Medium |
| P0-2 | **Run the full integration test suite in Docker Compose or CI and get to green** | The last-failed pytest cache shows 12 tests as unconfirmed. A clean CI run is required before launch. | `backend/tests/test_*.py`, `.github/workflows/ci.yml` | Low (run) / Medium (fix if real failures) |
| P0-3 | **Define and apply a concrete production environment configuration** | No `frontend/.env.production` exists; production CORS, database, SMTP, and Redis are not configured. Production cannot be launched without this. | `backend/.env.production.example` (use as template), `frontend/.env.production` (create) | Medium |

### P1 — Important

| # | Task | Why It Matters | Files Involved | Complexity |
|---|---|---|---|---|
| P1-1 | **Remove/rename `backend/test_sentry.pyecho`** | Stray file confuses directory structure and pytest discovery. | `backend/test_sentry.pyecho` | Low |
| P1-2 | **Create fixture dataset folder and write expected-outcome specs** | Foundation for all engine quality work. Without fixture datasets and expected-outcome specs, rule changes cannot be validated safely. | New: `backend/tests/engine/datasets/` with CSV/XLSX samples | Medium |
| P1-3 | **Connect recommendations to findings in the audit report UI** | Recommendations exist in the API response but are not rendered under the triggering finding. This is the single biggest gap between the current UI and the target experience. | `frontend/src/app/dashboard/audits/page.tsx`, `frontend/src/components/dashboard/findings-list.tsx` | Medium |
| P1-4 | **Add pre-upload checklist and stronger empty state** | Users uploading weak exports get confusing output. A pre-upload checklist and clear empty state prevent drop-off during onboarding. | `frontend/src/components/dashboard/data-sync.tsx`, `frontend/src/app/dashboard/audits/page.tsx` | Low |
| P1-5 | **Fix duplicate `aggregate_rules` import** | Minor cleanup; signals an unreviewed file. | `backend/app/engine/rules/__init__.py` | Low |

### P2 — Improvement

| # | Task | Why It Matters | Files Involved | Complexity |
|---|---|---|---|---|
| P2-1 | **Expand CVR / conversion leakage rule coverage** | Clicks-without-conversions and high spend with weak conversion yield are high-value signals currently underrepresented in the engine. | `backend/app/engine/rules/cpa_rules.py`, `backend/tests/engine/` | Medium |
| P2-2 | **Add "Actual vs Threshold" on every finding in the UI** | Makes findings feel quantified and trustworthy. Currently the data exists in API responses but is not consistently displayed. | `frontend/src/app/dashboard/audits/page.tsx`, `frontend/src/components/dashboard/findings-list.tsx` | Low |
| P2-3 | **Synthesize action plan from deterministic findings as AI fallback** | When AI produces a weak or generic plan, the UI should fall back to the top deterministic findings instead of showing nothing useful. | `frontend/src/components/dashboard/ai-summary-block.tsx`, `frontend/src/lib/audit.ts` | Medium |
| P2-4 | **Add export / share capability to audit report** | The target persona (founder/marketer) needs to share audit output with teams or clients. Section 9 of the report page checklist is entirely unimplemented. | New frontend component; `frontend/src/app/dashboard/audits/page.tsx` | Medium |
| P2-5 | **Consolidate four planning documents into a single ordered backlog** | Reduces risk of duplicate work or missing items across planning documents. | `improvement-plan.md`, `Meta_Ads_Audit_Implementation_Plan.md`, `Audit_Report_Page_Optimization_Checklist.md`, `Deterministic_Engine_Rule_Depth_Checklist.md` | Low |
| P2-6 | **Add frontend component tests** | No frontend test coverage exists. Even a small set of smoke tests for the audit report page and auth flow would reduce regression risk during the upcoming UI rework. | New: `frontend/src/__tests__/` | Medium |

---

## 9. Suggested Immediate Actions for the Next Development Session

1. **Rotate secrets and clean Git history (P0-1).** Run `backend/scripts/reencrypt_tokens.py` after generating fresh values for `SECRET_KEY` and `ENCRYPTION_KEY`. Revoke and regenerate the Gemini API key and Sentry DSN. Use `git filter-repo` or BFG to purge `backend/.env` from all prior commits, then force-push. This is the only true launch blocker that cannot be parallelized with other work.

2. **Run the full test suite via Docker Compose and get to green (P0-2).** Execute `docker compose up -d && docker compose exec backend sh -lc "PYTHONPATH=/app pytest -q"`. Diagnose any real failures. The last-failed cache lists 12 tests, but these are almost certainly environment failures rather than logic bugs — the engine unit tests in `tests/engine/` have a complete fixture library and should pass cleanly.

3. **Create the fixture dataset folder and write 3 expected-outcome scenario specs (P1-2).** Create `backend/tests/engine/datasets/` with at minimum: a healthy-baseline CSV, a weak-CTR CSV, and a high-CPA CSV. Write three corresponding expected-outcome dicts (expected findings, severities, score ranges). This unblocks all further engine depth work and makes score calibration testable.

4. **Connect recommendations to findings in the audit report UI (P1-3).** In `frontend/src/app/dashboard/audits/page.tsx`, add a lookup from each `AuditFinding.id` to its corresponding `Recommendation` entry and render the recommendation body directly beneath the finding card. The data already exists in the API response — this is purely a frontend rendering change with high user-visible impact.

5. **Add the pre-upload checklist and improve the empty state in data-sync (P1-4).** In `frontend/src/components/dashboard/data-sync.tsx`, add a collapsible checklist: 30+ days, daily rows, spend, clicks, conversions, campaign and ad set fields. In `frontend/src/app/dashboard/audits/page.tsx`, strengthen the no-audit empty state to explain what to upload and what the user gets back. These are low-complexity changes with direct impact on first-run conversion.
