# External Integrations

_Last updated: 2026-04-03_

## Summary

The backend integrates with three categories of external services: Meta (Facebook) Graph API for OAuth and ad data sync, a configurable AI provider (OpenAI, Anthropic, or Gemini) for generating audit summaries, and an SMTP server for transactional email. Redis and PostgreSQL are infrastructure dependencies rather than third-party SaaS. Sentry is integrated in both backend and frontend for error monitoring. There are no incoming webhooks; all external calls are outbound request-response.

---

## APIs & External Services

### Meta (Facebook) Graph API

- **Purpose:** OAuth authorization, ad account discovery, campaign/adset/ad/insight data sync
- **Base URL:** `https://graph.facebook.com/{meta_api_version}` (default version: `v19.0`, set via `META_API_VERSION`)
- **OAuth dialog URL:** `https://www.facebook.com/{meta_api_version}/dialog/oauth`
- **SDK/Client:** `httpx` 0.27.0 — direct REST calls, no official Meta SDK
- **Auth:** OAuth 2.0 — code exchange for short-lived token, then exchange for long-lived token
- **Scopes:** `ads_read,ads_management,business_management` (configurable via `META_OAUTH_SCOPES`)
- **Key files:**
  - `backend/app/services/meta_auth.py` — OAuth flow (state generation, code exchange, token storage)
  - `backend/app/services/meta_ads.py` — ad account fetching and syncing
  - `backend/app/services/meta_sync.py` — full data sync pipeline (campaigns, ad sets, ads, insights)
  - `backend/app/services/meta_mock.py` — mock responses for local development without real credentials
- **Token storage:** access tokens are Fernet-encrypted at rest in `MetaConnection.encrypted_access_token` via `backend/app/services/crypto.py`
- **Pagination:** max 250 pages per request (configurable `META_PAGINATION_MAX_PAGES`, hard cap: 2000)
- **Sync lookback:** 90 days initial sync, 30 days incremental (configurable)
- **HTTP timeout:** 60 seconds default (`META_HTTP_TIMEOUT_SECONDS`)
- **Retry logic:** `with_http_retries_async()` from `backend/app/services/resilience.py`, 3 attempts per call
- **Config env vars:** `META_APP_ID`, `META_APP_SECRET`, `META_REDIRECT_URI`, `META_API_VERSION`, `META_OAUTH_SCOPES`

### AI Summary Providers (multi-provider, pluggable)

- **Purpose:** Generate executive summaries, detailed audit explanations, and prioritized action plans after each audit run
- **Implementation:** `backend/app/services/ai_summary.py` (`AISummaryService`)
- **Provider selection:** `AI_PROVIDER` env var; options: `openai`, `anthropic`, `gemini`, `mock`
- **Auto-detection:** if `AI_API_KEY` is set but `AI_PROVIDER` is `mock`/empty, defaults to `openai`
- **Fallback:** if all AI calls fail or provider is unconfigured, a deterministic fallback summary is generated locally from audit data (`_fallback_output()` / `_fallback_action_plan()`) — no external call needed
- **HTTP client:** `httpx` synchronous client with retry via `with_http_retries()` from `backend/app/services/resilience.py`
- **Config env vars:** `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`, `AI_TIMEOUT_SECONDS` (default: 45), `AI_MAX_RETRIES` (default: 2), `AI_PROMPT_VERSION`

**OpenAI:**
- Endpoint: `{AI_OPENAI_BASE_URL}/chat/completions` (default: `https://api.openai.com/v1`)
- Auth: `Authorization: Bearer {AI_API_KEY}` header
- Output format: `response_format: {"type": "json_object"}`
- Temperature: 0.1

**Anthropic:**
- Endpoint: `{AI_ANTHROPIC_BASE_URL}/messages` (default: `https://api.anthropic.com/v1`)
- Auth: `x-api-key` header + `anthropic-version: 2023-06-01`
- Max tokens: 1200, temperature: 0.1

**Gemini:**
- Endpoint: `{AI_GEMINI_BASE_URL}/models/{AI_MODEL}:generateContent` (default: `https://generativelanguage.googleapis.com/v1beta`)
- Auth: `?key={AI_API_KEY}` query parameter
- Uses `responseSchema` to enforce exact JSON structure (eliminates key aliasing on response)
- `responseMimeType: "application/json"`, temperature: 0.1

---

## Data Storage

### PostgreSQL 16

- **Role:** Primary relational store for all application entities
- **Connection env var:** `DATABASE_URL` (default: `postgresql://postgres:postgres@postgres:5432/meta_ads_audit`)
- **ORM:** SQLAlchemy 2.0.27; `DeclarativeBase` pattern; engine in `backend/app/database.py`
- **Models:** `backend/app/models/` — `user.py`, `meta_connection.py`, `audit.py`, `campaign.py`, `insights.py`, `subscription.py`, `sync_job.py`
- **Migrations:** Alembic 1.13.1; versions in `backend/alembic/versions/`; run on container startup
- **Driver:** psycopg2-binary 2.9.9
- **Docker image:** `postgres:16-alpine`

### Redis 7

- **Role:** Dual-purpose — Celery broker+backend AND in-process rate-limit counter store
- **Connection env var:** `REDIS_URL` (default: `redis://redis:6379/0`)
- **Rate limiter fallback:** if Redis is unavailable, falls back to in-memory `deque` (`backend/app/services/rate_limit.py`)
- **Optional password:** `REDIS_PASSWORD` env var (handled in `docker-compose.yml` startup command)
- **Docker image:** `redis:7-alpine`; `appendonly yes` persistence enabled

### File Storage

- **Local only** — no cloud blob storage (S3, GCS, etc.)
- Uploaded CSV/XLSX files are parsed in memory and not persisted to disk

---

## Authentication & Identity

### App Authentication (JWT + cookies)

- **Implementation:** `backend/app/services/auth.py`, `backend/app/middleware/deps.py`
- **Token type:** HS256 JWT signed with `SECRET_KEY`
- **Expiry:** 60 minutes default (configurable `ACCESS_TOKEN_EXPIRE_MINUTES`, range: 5–1440)
- **Token transport:** `Authorization: Bearer` header OR `access_token` HttpOnly cookie
- **Password hashing:** `passlib` with `pbkdf2_sha256` scheme
- **Email verification:** required; `email_verified` flag on `User` model; verification token is `secrets.token_urlsafe(32)` stored in DB
- **Password reset:** token-based; reset token is `secrets.token_urlsafe(32)` stored in DB

### Meta OAuth 2.0 Flow

- **Implementation:** `backend/app/services/meta_auth.py`
- **Flow steps:**
  1. Backend generates authorization URL; `state` token (SHA-256 hashed) stored in `MetaConnection` with 10-min TTL
  2. User redirected to `https://www.facebook.com/{version}/dialog/oauth`
  3. Meta redirects to `META_REDIRECT_URI` (default: `http://localhost:3000/dashboard/meta/callback`)
  4. Frontend callback page calls backend which validates state hash + exchanges short-lived code for long-lived token
  5. Long-lived access token Fernet-encrypted and stored in `MetaConnection.encrypted_access_token`
- **Token refresh:** not automatic; user must reconnect when token expires
- **Mock mode:** `META_APP_ID=mock` bypasses real OAuth; `backend/app/services/meta_mock.py` provides fake data

---

## Monitoring & Observability

### Sentry

- **Backend SDK:** `sentry-sdk[fastapi]` 2.20.0
- **Frontend SDK:** `@sentry/nextjs` 9.17.0
- **Backend init:** `backend/app/observability.py` — called at startup in `backend/app/main.py`
- **Backend integrations enabled:** `FastApiIntegration`, `CeleryIntegration`, `SqlalchemyIntegration`
- **Config env vars:** `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE` (default: 0.0)
- **PII:** `send_default_pii=False` enforced
- **Disabled when:** `SENTRY_DSN` is empty string (no-op)
- **Explicit capture:** unhandled exceptions captured via `sentry_sdk.capture_exception()` in HTTP exception handlers (`backend/app/main.py`)

### Structured Logging

- **Transport:** stdout, Python `logging.StreamHandler`
- **Implementation:** `backend/app/logging_config.py`; loggers obtained via `get_logger(__name__)` returning `ContextLoggerAdapter`
- **Fields included per log line:** `request_id`, `task_id`, `user_id`, `job_id`, `audit_run_id`, `code`, `method`, `path`, `status_code`
- **Request tracing:** `x-request-id` header propagated through middleware; attached to response headers and all log lines

---

## Email / SMTP

- **Implementation:** `backend/app/services/email.py`
- **Library:** Python stdlib `smtplib` + `email.mime.text.MIMEText` (no third-party email SDK)
- **Transport:** SMTP with STARTTLS (configurable via `SMTP_STARTTLS`, default: `True`)
- **Config env vars:** `SMTP_HOST` (default: `smtp.gmail.com`), `SMTP_PORT` (default: 587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
- **Sent email types:**
  - Account verification: `send_verification_email()` → link to `{FRONTEND_APP_URL}/verify-email?token=...`
  - Password reset: `send_reset_email()` → link to `{FRONTEND_APP_URL}/reset-password?token=...`
- **Error handling:** SMTP errors raise `EmailDeliveryError(RuntimeError)`
- **Local dev mock:** Mailpit SMTP server available via `docker-compose --profile local-tools` (port 1025 SMTP, port 8025 web UI); image `axllent/mailpit:v1.26`

---

## Rate Limiting

- **Implementation:** `backend/app/services/rate_limit.py`
- **Strategy:** Redis INCR pipeline (primary) with in-memory `deque` fallback when Redis is unavailable
- **Applied scopes and defaults (all configurable via env vars):**
  - `global`: 300 req/min per IP — applied in HTTP middleware in `backend/app/main.py`
  - `auth`: 6 req / 300s
  - `upload`: 6 req / 3600s
  - `audit`: 10 req / 3600s
- **Redis key format:** `rate_limit:{scope}:{user_id_or_anon}:{ip}`

---

## CSV/XLSX Import Pipeline

- **Implementation:** `backend/app/services/csv_import.py`
- **Accepted formats:** `.csv`, `.xlsx` (max 10 MB)
- **MIME detection:** magic-byte inspection (PK header = XLSX, decodable text = CSV); `python-magic` also available
- **XLSX parsing:** `openpyxl` 3.1.5 in read-only mode; auto-selects best worksheet via header scoring
- **CSV parsing:** `csv.Sniffer` for delimiter detection; tries encodings: `utf-8-sig`, `utf-8`, `cp1251`, `cp1252`, `latin-1`
- **Column aliasing:** `COLUMN_ALIASES` dict maps ~20 canonical fields to English + Russian header variants
- **Report classification:** `daily_breakdown` (has `date`/`day` column) vs `period_aggregate` (has `reporting starts`/`reporting ends`)
- **Data written to:** `Campaign`, `AdSet`, `Ad`, `DailyCampaignInsight`, `DailyAdSetInsight`, `DailyAdInsight`, `DailyAccountInsight` models via upsert
- **Synthetic IDs:** SHA-1 hash of entity names used when real Meta IDs are absent in the export file
- **Replace mode:** `replace_existing=True` clears all existing account data before import

---

## CI/CD

- **Provider:** GitHub Actions — `.github/workflows/ci.yml`
- **Backend job:** Python 3.12, installs `backend/requirements.txt`, runs `pytest -q`; spins up a real PostgreSQL 16 service container
- **Frontend job:** Node.js 20, runs `npm ci`, `npm run lint`, `npm run build`
- **Secrets used in CI:** `CI_ENCRYPTION_KEY` (GitHub secret, falls back to a base64 test key)
- **Trigger:** push or PR to `main` branch

---

## Frontend API Proxy

- **File:** `frontend/src/app/api/proxy/[...path]/route.ts`
- **Purpose:** All frontend API calls go to `/api/proxy/*` which this route transparently forwards to `BACKEND_INTERNAL_URL` (default: `http://backend:8000/api`)
- **Forwarded headers:** `Content-Type`, `Cookie`, `Authorization`
- **Forwarded response headers:** `content-type`, `set-cookie`
- **Supported methods:** GET, POST, PUT, PATCH, DELETE

---

## Webhooks

**Incoming:** None — Meta OAuth redirect to `META_REDIRECT_URI` is a standard OAuth callback, not a webhook.

**Outgoing:** None — all external calls are outbound request-response (Meta Graph API, AI providers, SMTP).

---

## Freemium / Entitlements

- **Implementation:** `backend/app/services/entitlements.py`
- **Subscription model:** `backend/app/models/subscription.py`
- **Billing routes:** `backend/app/routes/billing.py`
- **Free tier limits (configurable via env vars):**
  - `FREE_MAX_AD_ACCOUNTS`: 1
  - `FREE_MAX_FINDINGS`: 3
  - `FREE_MAX_RECOMMENDATIONS`: 2
  - `FREE_MAX_HISTORY_ITEMS`: 4
  - `FREE_MAX_TREND_POINTS`: 6
  - `FREE_MAX_REPORTS_PER_MONTH`: 3
- **Note:** No payment processor (Stripe, etc.) is detected in dependencies or source. Billing is managed internally.

---

*Integration audit: 2026-04-03*
