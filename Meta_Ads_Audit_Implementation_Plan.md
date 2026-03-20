# Meta Ads Audit Production Fix Checklist

Source: `Meta_Ads_Audit_Implementation_Plan.docx`  
Date: March 20, 2026  
Status: Stripe and billing work deferred until after the items below.

## Scope

This checklist covers the production-blocking and production-readiness work from the implementation plan, excluding Stripe and billing integration.

## Phase Overview

| Phase | Focus | Priority | Estimated Effort |
| --- | --- | --- | --- |
| 1 | Security and critical bugs | Launch blocker | 1-2 days |
| 2 | Auth hardening | Launch blocker | 3-4 days |
| 3 | Async audit pipeline | Launch blocker | 2-3 days |
| 4 | Frontend and UX cleanup | High | 2 days |
| 5 | DevOps and observability | High | 1-2 days |

## Phase 1: Security and Critical Bugs

- [ ] Remove committed secrets from Git tracking and rotate `SECRET_KEY` and `ENCRYPTION_KEY`.
  Files: `backend/.env`, `frontend/.env.local`, `.gitignore`, `backend/.env.example`
- [x] Add `backend/.env`, `frontend/.env.local`, and `.env` to `.gitignore`.
  Files: `.gitignore`
- [x] Update `backend/.env.example` to use placeholders only, never real secrets.
  Files: `backend/.env.example`
- [ ] Create and run a one-time token re-encryption script after key rotation.
  Files: `backend/scripts/reencrypt_tokens.py`
- [ ] Ensure `DEBUG=false` in production.
  Files: production environment config
- [x] Add a production guard so `debug` is forced off when `ENVIRONMENT=production`.
  Files: `backend/app/config.py`
- [x] Add `Severity.WARNING` as a valid alias mapping to medium severity.
  Files: `backend/app/engine/types.py`
- [x] Add missing category enum members: `CTR`, `FREQUENCY`, and `CPA`.
  Files: `backend/app/engine/types.py`
- [x] Update scoring pillars to include the new categories.
  Files: `backend/app/engine/scoring.py`
- [x] Fix `AccountSnapshot` imports by aliasing `AccountAuditSnapshot` in rule files.
  Files: `backend/app/engine/rules/ctr_rules.py`, `backend/app/engine/rules/frequency_rules.py`, `backend/app/engine/rules/cpa_rules.py`, `backend/app/engine/rules/spend_rules.py`
- [x] Add `avg_ctr`, `avg_frequency`, `daily_ctr`, and `daily_frequency` convenience properties to `CampaignAuditMetrics`.
  Files: `backend/app/engine/types.py`
- [x] Guard debug routes so they are unavailable in production.
  Files: `backend/app/main.py`, `backend/app/routes/debug.py`
- [x] Remove `Base.metadata.create_all()` from app startup.
  Files: `backend/app/main.py`
- [x] Run Alembic migrations during deploy startup instead of creating schema at runtime.
  Files: `backend/Dockerfile`
- [x] Add MIME/content-type verification for uploaded report files.
  Files: `backend/app/services/csv_import.py`, `backend/requirements.txt`
- [x] Remove internal AI fallback reason text from user-visible summaries.
  Files: `backend/app/services/ai_summary.py`

Phase 1 status notes:
- Code-complete in repo: engine crash fixes, startup hardening, debug route guarding, upload MIME validation, AI fallback cleanup, Docker migration startup, env template cleanup, and token re-encryption script creation.
- Still manual: rotate real secrets, remove any previously tracked secret files from Git history, install updated backend dependencies, and set production `DEBUG=false`.

## Phase 2: Auth Hardening

- [ ] Move auth from `localStorage` JWTs to `httpOnly` cookies.
  Files: `backend/app/routes/auth.py`, `frontend/src/lib/auth.ts`, `frontend/src/lib/api.ts`
- [ ] Add a logout endpoint that clears the auth cookie.
  Files: `backend/app/routes/auth.py`
- [ ] Update auth dependency resolution to read cookie first and Bearer token as fallback.
  Files: `backend/app/middleware/deps.py`
- [ ] Add `credentials: 'include'` to frontend API requests.
  Files: `frontend/src/lib/api.ts`
- [ ] Remove frontend token persistence from `localStorage`.
  Files: `frontend/src/lib/auth.ts`
- [ ] Add `email_verified` and `email_verify_token` fields to the user model.
  Files: `backend/app/models/user.py`, new Alembic migration
- [ ] Create email delivery helpers for verification and password reset.
  Files: `backend/app/services/email.py`
- [ ] Add register flow email verification handling.
  Files: `backend/app/routes/auth.py`, `backend/app/services/auth.py`
- [ ] Add `GET /auth/verify-email`.
  Files: `backend/app/routes/auth.py`
- [ ] Add `POST /auth/forgot-password`.
  Files: `backend/app/routes/auth.py`
- [ ] Add `POST /auth/reset-password`.
  Files: `backend/app/routes/auth.py`
- [ ] Block unverified users from accessing protected API routes outside debug mode.
  Files: `backend/app/middleware/deps.py`
- [ ] Add SMTP configuration fields.
  Files: `backend/app/config.py`
- [ ] Validate user registration email addresses with `EmailStr`.
  Files: `backend/app/schemas/auth.py`
- [ ] Add a frontend verify-email page.
  Files: `frontend/src/app/verify-email/page.tsx`
- [ ] Add a frontend forgot-password page.
  Files: `frontend/src/app/forgot-password/page.tsx`
- [ ] Add a frontend reset-password page.
  Files: `frontend/src/app/reset-password/page.tsx`
- [ ] Add a "Forgot password?" link to the login UI.
  Files: `frontend/src/components/auth/auth-card.tsx`

## Phase 3: Async Audit Pipeline

- [ ] Add `job_status`, `job_error`, and `celery_task_id` fields to `AuditRun`.
  Files: `backend/app/models/audit.py`, new Alembic migration
- [ ] Create a Celery task to run audits asynchronously.
  Files: `backend/app/tasks/audit.py`
- [ ] Update `POST /audit/run` to create a placeholder audit run and dispatch the Celery task.
  Files: `backend/app/routes/audit.py`
- [ ] Add `GET /audit/job/{job_id}` for polling job status.
  Files: `backend/app/routes/audit.py`
- [ ] Update frontend audit execution to poll for background job completion.
  Files: `frontend/src/app/dashboard/audits/page.tsx`
- [ ] Add frontend progress/loading feedback while an audit is running.
  Files: `frontend/src/app/dashboard/audits/page.tsx`
- [ ] Configure a real AI provider in production.
  Files: production environment config
- [ ] Export a shared `cleanAiSummaryText()` helper and use it everywhere AI summary text is rendered.
  Files: `frontend/src/lib/audit.ts`, all frontend AI summary render paths

## Phase 4: Frontend and UX Cleanup

- [ ] Remove internal MVP and developer-facing strings from the UI.
  Files: multiple files under `frontend/src`
- [ ] Rename "Local MVP Billing" to "Plan & Billing".
  Files: `frontend/src/app/dashboard/settings/page.tsx`
- [ ] Delete the Stripe placeholder paragraph in settings.
  Files: `frontend/src/app/dashboard/settings/page.tsx`
- [ ] Show the debug-only data reset UI only in development.
  Files: `frontend/src/app/dashboard/settings/page.tsx`
- [ ] Remove the local MVP guidance strings from the data sync flow.
  Files: `frontend/src/components/data-sync.tsx`
- [ ] Rename "Deterministic Account Diagnosis" to "Account Audit Report".
  Files: `frontend/src/app/dashboard/audits/page.tsx`
- [ ] Replace "deterministic audit engine" with "performance analysis engine".
  Files: `frontend/src/app/dashboard/audits/page.tsx`
- [ ] Remove the "Phase 2" label from the login page panel.
  Files: `frontend/src/app/login/page.tsx`
- [ ] Remove MVP workflow guidance from the dashboard page.
  Files: `frontend/src/app/dashboard/page.tsx`
- [ ] Fix the broken "How It Works" CTA.
  Files: `frontend/src/components/landing/hero.tsx`
- [ ] Change the primary landing page CTA to send unauthenticated users to `/register`.
  Files: `frontend/src/components/landing/hero.tsx`
- [ ] Update the landing page headline and subheadline to reflect the upload-first flow.
  Files: `frontend/src/components/landing/hero.tsx`
- [ ] Add a footer with links to `/privacy` and `/terms`.
  Files: `frontend/src/app/page.tsx`
- [ ] Add a pricing link in the top navigation.
  Files: landing page navigation components
- [ ] Create a shared spinner component for loading states.
  Files: `frontend/src/components/ui/spinner.tsx`
- [ ] Replace plain-text loading states with the spinner.
  Files: `frontend/src/app/dashboard/page.tsx`, `frontend/src/app/dashboard/audits/page.tsx`
- [ ] Add retry actions to dashboard and audit error states.
  Files: `frontend/src/app/dashboard/page.tsx`, `frontend/src/app/dashboard/audits/page.tsx`
- [ ] Create a privacy policy page.
  Files: `frontend/src/app/privacy/page.tsx`
- [ ] Create a terms of service page.
  Files: `frontend/src/app/terms/page.tsx`

## Phase 5: DevOps and Observability

- [ ] Add a production backend environment example.
  Files: `backend/.env.production.example`
- [ ] Set production values for `DEBUG`, `ENVIRONMENT`, database, Redis, Meta, AI, SMTP, CORS, frontend URL, and Sentry.
  Files: production environment config
- [ ] Add frontend production environment values.
  Files: `frontend/.env.production`
- [ ] Disable FastAPI docs, ReDoc, and OpenAPI in production.
  Files: `backend/app/main.py`
- [ ] Add rate limiting dependencies.
  Files: `backend/requirements.txt`
- [ ] Configure global rate limiting middleware and handlers.
  Files: `backend/app/main.py`
- [ ] Rate-limit auth endpoints.
  Files: `backend/app/routes/auth.py`
- [ ] Rate-limit upload endpoints.
  Files: `backend/app/routes/sync.py`
- [ ] Rate-limit audit run endpoints.
  Files: `backend/app/routes/audit.py`
- [ ] Add backend Sentry integration.
  Files: `backend/requirements.txt`, `backend/app/main.py`
- [ ] Add frontend Sentry integration.
  Files: `frontend/package.json`, `frontend/src/app/layout.tsx`
- [ ] Fix the worst-performers query to aggregate before joining.
  Files: `backend/app/routes/audit.py`
- [ ] Convert the frontend Docker build to a multi-stage image.
  Files: `frontend/Dockerfile`
- [ ] Remove the runtime frontend build command override from Compose.
  Files: `docker-compose.yml`
- [ ] Enable Redis authentication and append-only persistence.
  Files: `docker-compose.yml`, Redis configuration

## Deferred: Stripe and Billing

- [ ] Keep Stripe and billing integration out of this implementation pass.
- [ ] Keep `/billing/dev/plan` available only when `DEBUG=true`.
- [ ] Ensure `/billing/dev/plan` returns `403` in production.
- [ ] When billing resumes, implement Stripe Checkout, subscription webhooks, and subscription state syncing.

## Rollout Order

- [ ] Complete all Phase 1 tasks before Phase 2.
- [ ] Complete Phase 2 before Phase 3.
- [ ] Treat Phases 1-3 as required before launch.
- [ ] Complete Phases 4-5 before public rollout.
