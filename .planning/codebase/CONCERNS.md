# Concerns & Risks
_Last updated: 2026-04-03_

## Summary
The engine layer has just completed a significant bug-fix pass (enum alias removal, CTR recalculation, recommendation key gaps) that is applied in the working tree but not yet committed. The frontend audit report page has a known structural issue — the same data appears three times on one page — and several planned UI features (expandable findings, PDF export, lead capture) are completely unimplemented. Billing is stub-only with no Stripe webhook integration, so plan gating cannot be enforced based on real payment events.

---

## Uncommitted Engine Changes (Immediate Risk)

**All eight engine bug-fix files are unstaged:**
- The working tree contains completed, tested fixes that have not been committed. A crash, stash-pop, or accidental reset could lose the work.
- Files: `backend/app/engine/types.py`, `backend/app/engine/collector.py`, `backend/app/engine/scoring.py`, `backend/app/engine/recommendations.py`, `backend/app/engine/rules/ctr_rules.py`, `backend/app/engine/rules/cpa_rules.py`, `backend/app/engine/rules/frequency_rules.py`, `backend/app/engine/rules/spend_rules.py`
- Fix approach: `git add backend/app/engine/ && git commit` immediately.

---

## Recently Fixed Bugs (Do Not Reintroduce)

**CTR unit mismatch in `_daily_point()`:**
- `_daily_point()` now recalculates CTR (and CPC, CPM, ROAS, CPA) from raw `clicks`/`impressions` columns, ignoring the stored derived value from the CSV (which may be "CTR (all)").
- Files: `backend/app/engine/collector.py` lines 126–149

**`Severity.WARNING` and `Category.SPEND` silent aliases removed:**
- Only `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` exist in `Severity`. Only `BUDGET` (not `SPEND`) exists in `Category`.
- Files: `backend/app/engine/types.py`

**CTR rules missing `recommendation_key`:**
- `recommendation_key` is now set on all `Finding` instances in `backend/app/engine/rules/ctr_rules.py`.

**Missing recommendation templates for `weak_cvr` and `uneven_daily_spend`:**
- Both rules now have entries in `recommendations.py` templates dict and in `AISummaryService._CATEGORY_NEXT_STEPS`.
- Files: `backend/app/engine/recommendations.py`, `backend/app/services/ai_summary.py`

**`HighSpendLowConversionsRule` and `LowROASHighSpendRule` now guard on `status != "ACTIVE"`:**
- Files: `backend/app/engine/rules/performance_rules.py`

**Zero-conversion descriptions now say "zero conversions recorded" not "0.00%":**
- Files: `backend/app/engine/rules/performance_rules.py` (WeakCVRRule), `backend/app/engine/rules/account_rules.py`

**`deriveBiggestLeak()` now uses severity rank as tiebreaker when all waste = $0:**
- Files: `frontend/src/lib/audit.ts` lines 351–371

---

## Tech Debt

**`ZeroConversionSpendRule` and `NegativeROASRule` have no `recommendation_key`:**
- Both rules build `Finding` objects without `recommendation_key`, so they fall through to the generic "Review this finding" template in `apply_recommendation()`.
- Files: `backend/app/engine/rules/cpa_rules.py` lines 78–95 and 99–129
- Fix approach: Add `recommendation_key=self.rule_id` and register matching templates in `backend/app/engine/recommendations.py`.

**`SpendConcentrationRule` has no `recommendation_key`:**
- `backend/app/engine/rules/spend_rules.py` `SpendConcentrationRule` creates `Finding` objects without a `recommendation_key`. The template `"budget_concentration_risk"` already exists in `recommendations.py`.
- Fix approach: Add `recommendation_key="budget_concentration_risk"` to the Finding constructor in `SpendConcentrationRule`.

**AI summary does not include per-campaign best/worst performers:**
- `_build_structured_input()` in `backend/app/services/ai_summary.py` sends only rule-triggered findings to the AI. Top 3 best/worst performers by ROAS, CTR, and CPA are absent.
- Impact: AI summaries cannot give campaign-specific comparative guidance; they comment only on findings that crossed rule thresholds.
- Fix approach: Extend `_build_structured_input()` to append a `top_performers` / `worst_performers` block from sorted campaign metrics. Tracked in `TODO.md`.

**Audit Report page has structural content redundancy:**
- "Top 3 Actions" renders both as the main panel and inside the `overview` tab's `FindingsList`. "Biggest Leak" card appears twice. The TODO.md explicitly calls out that Top 3 Actions appears 3× on page.
- Files: `frontend/src/app/dashboard/audits/page.tsx`
- Fix approach: Extract Top 3 Actions into one canonical component; redesign page layout per `TODO.md`.

**PDF export is `window.print()` only:**
- Files: `frontend/src/app/dashboard/audits/page.tsx`
- Impact: Users expecting a polished PDF get an unstyled browser print dialog.
- Fix approach: Integrate server-side PDF render (Puppeteer, WeasyPrint, or react-pdf). Tracked in `TODO.md`.

**Billing is stub-only (no Stripe integration):**
- `backend/app/routes/billing.py` and `backend/app/services/entitlements.py` expose plan tier switching, but there is no Stripe webhook handler. `stripe_customer_id` and `stripe_subscription_id` columns exist on `Subscription` but are never written.
- Impact: The billing wall is cosmetic; no payment event can upgrade a user automatically.
- Fix approach: Implement a Stripe webhook handler (`POST /api/billing/webhook`) updating `Subscription.plan_tier` on `customer.subscription.updated` and `invoice.payment_succeeded`.

**`/api/billing/dev/plan` is gated only by environment variable, not role:**
- `backend/app/routes/billing.py` line 44 checks `os.getenv("ENVIRONMENT") == "production"`. Any authenticated user in staging/dev can promote themselves to `premium`.
- Fix approach: Remove the endpoint from routing in non-local environments, or replace with an admin-only seed script.

**No shareable public report links:**
- All audit routes require `get_current_user`. There is no signed time-limited token mechanism to share a report with a non-account holder.
- Files: `backend/app/routes/audit.py`, `backend/app/middleware/deps.py`
- Fix approach: `POST /audit/{id}/share-link` → short-lived read-only signed token; matching public route that reads without a session.

**No lead capture / contact form:**
- Privacy and terms pages reference `contact@yourdomain.com` (placeholder). No Calendly embed or lead form exists anywhere.
- Files: `frontend/src/app/privacy/page.tsx`, `frontend/src/app/terms/page.tsx`
- Fix approach: Replace placeholder email; add Calendly embed or contact form component. Tracked in `TODO.md`.

**Findings list is not expandable/collapsible:**
- `FindingsList` renders all findings fully expanded. On accounts with 20+ findings the page becomes very long.
- Files: `frontend/src/components/dashboard/findings-list.tsx`
- Fix approach: Add accordion pattern — severity badge + title by default, expand on click. Tracked in `TODO.md`.

**`datetime.utcnow` used throughout models (deprecated in Python 3.12):**
- All model `DateTime` defaults use `datetime.utcnow` (non-timezone-aware) instead of `datetime.now(timezone.utc)`.
- Files: `backend/app/models/audit.py`, `backend/app/models/user.py`, `backend/app/models/campaign.py`, `backend/app/models/insights.py`, `backend/app/models/subscription.py`, `backend/app/models/sync_job.py`, `backend/app/models/meta_connection.py`
- Fix approach: Replace all `default=datetime.utcnow` with `default=lambda: datetime.now(timezone.utc)`.

**Stored `ctr` column in insight tables is dead data:**
- `csv_import.py` writes a weighted-average CTR to the `ctr` column of insight rows, but `collector.py` ignores it and recalculates from raw clicks/impressions. The stored value is stale.
- Files: `backend/app/services/csv_import.py` lines 726–756, `backend/app/engine/collector.py` lines 131–148
- Impact: No correctness issue (collector ignores it), but misleads anyone querying the DB directly.

**Scoring constants are hardcoded (no configuration path):**
- `SEVERITY_PENALTIES`, `ENTITY_SCOPE_MULTIPLIERS`, and pillar weights in `backend/app/engine/scoring.py` are module-level literals. Tuning scoring requires a code deploy.
- Fix approach: Move scoring constants into a config dict (DB-stored or YAML file) loadable without touching `scoring.py`.

---

## Security Considerations

**Email verify token and password reset token share one DB column:**
- `User.email_verify_token` is used for both email verification and password reset. Requesting a password reset overwrites a pending verification token and vice versa.
- Files: `backend/app/routes/auth.py`, `backend/app/models/user.py`
- Recommendation: Add a separate `password_reset_token` + `password_reset_token_expires_at` column.

**No password reset token expiry:**
- `backend/app/routes/auth.py` `reset_password` does not check any expiry timestamp. A reset link is valid indefinitely until consumed.
- Risk: A leaked reset link remains exploitable forever.
- Recommendation: Add `password_reset_expires_at` and reject tokens older than 1 hour.

**JWT logout is stateless (no server-side revocation):**
- `POST /api/auth/logout` deletes the cookie but the JWT remains valid until its natural expiry (default 60 minutes).
- Files: `backend/app/routes/auth.py`
- Recommendation: Redis-backed token deny-list for high-risk events (password change, account deletion). Redis is already in the stack.

**`X-Forwarded-For` header trusted unconditionally for rate limiting:**
- `_extract_ip()` in `backend/app/services/rate_limit.py` line 27 takes the first value of `X-Forwarded-For` without validating it was set by a trusted proxy.
- Risk: A client can send a spoofed IP and bypass per-IP rate limits.
- Files: `backend/app/services/rate_limit.py` lines 25–29
- Recommendation: Use FastAPI's `ProxyHeadersMiddleware` with a trusted proxy list, or restrict IP extraction to `request.client.host` unless a verified proxy header is present.

**Rate limiter falls back silently to in-memory on Redis failure:**
- Redis connection failure is caught silently; no warning is logged. The memory fallback is process-local and ineffective under multiple workers.
- Files: `backend/app/services/rate_limit.py` lines 57–65
- Recommendation: Log a warning on Redis failure so operators know rate limiting has degraded.

**`debug=True` bypasses email verification in any non-production environment:**
- `backend/app/middleware/deps.py` skips email verification when `settings.debug=True`. The `disable_debug_in_production` validator in `config.py` only protects environments where `ENVIRONMENT=production`.
- Recommendation: Guard the debug bypass by `ENVIRONMENT == "development"` rather than the debug flag alone.

**Fernet encryption key has no rotation mechanism in live service:**
- `backend/app/services/crypto.py` uses a single `Fernet` instance with no key versioning. A `reencrypt_tokens.py` script exists but requires a manual run while the app is live.
- Recommendation: Use `MultiFernet([new_key, old_key])` so key rotation is zero-downtime.

**CSV injection risk not mitigated:**
- Campaign/ad-set names from CSV uploads are stored without sanitization. Formula-prefix values (`=`, `+`, `-`, `@`) in entity names would execute if the data is ever re-exported as CSV and opened in Excel.
- Files: `backend/app/services/csv_import.py` lines 341–343
- Recommendation: Strip or escape leading formula characters at import time.

---

## Architecture Concerns

**N+1 query pattern in `collect_account_data()` — counts per campaign:**
- Lines 80–81 of `backend/app/engine/collector.py` issue two extra DB queries per campaign (`AdSet.count()` and `Ad.count()`). For 50 campaigns this is 100 extra round-trips before any insight row is fetched.
- Fix approach: Issue a single `GROUP BY campaign_id` aggregation before the loop and use a lookup dict.

**N+1 query pattern in insight fetching — one query per ad set:**
- Lines 89–101 of `backend/app/engine/collector.py` issue one `DailyAdSetInsight` query per ad set. 200 ad sets → 200 sequential queries.
- Fix approach: Load all `DailyAdSetInsight` rows in one query filtered by `ad_account_id` and date range; partition in Python by `ad_set_id`. Apply the same pattern to campaign insights.

**`ad_set.campaign` lazy-load in `_aggregate_ad_set`:**
- `backend/app/engine/collector.py` line 241: `ad_set.campaign.name` triggers a lazy SQLAlchemy load per ad set, producing additional N+1 queries.
- Fix approach: Join-load campaigns in the initial `db.query(AdSet)` call or use a lookup dict from `campaign_outputs`.

**AI summary runs synchronously inside the Celery audit task:**
- `AISummaryService.generate_for_run()` uses a blocking `httpx.Client`. With `ai_timeout_seconds=45` and `ai_max_retries=2`, worst-case blocking time is 135 seconds per audit, holding the Celery worker slot throughout.
- Files: `backend/app/tasks/audit.py` lines 42–44
- Fix approach: Dispatch AI summary as a separate Celery chain task after audit completion. Also use `httpx.AsyncClient` if switching to async Celery workers.

**Celery task has only 1 retry, no dead-letter handling:**
- `run_audit_job` has `max_retries=1`. Transient DB timeouts or AI provider failures cause permanent `"failed"` status with no recovery path except the user re-triggering manually.
- Files: `backend/app/tasks/audit.py` line 15
- Fix approach: Increase retries to 2–3 for recoverable errors. Consider a `failed_rules` JSON column on `AuditRun` to record which rules raised exceptions.

**Rule exceptions are swallowed silently in the orchestrator:**
- `backend/app/engine/orchestrator.py` lines 107–124: a `try/except` logs and captures to Sentry but continues. A broken rule silently produces zero findings for its category.
- Impact: A regression in a new rule ships without a visible error; the user receives a lower-quality (but not obviously broken) audit.
- Fix approach: Record failed rule IDs on `AuditRun` (e.g., a `failed_rules` JSON column) so the dashboard can surface a data-quality warning.

**Dashboard endpoint re-runs `collect_account_data()` on every request:**
- `GET /audit/dashboard` calls `collect_account_data(db, account.id)` to fetch `data_mode` and `limitations`. This is the full collector logic on every page load, even though the data changes only after a new audit.
- Files: `backend/app/routes/audit.py` lines 449–450
- Fix approach: Store `data_mode` and `limitations` on the `AuditRun` model after the audit completes.

**`_compute_account_kpis()` loads all daily insight rows without a date filter:**
- `backend/app/routes/audit.py` lines 64–134 queries `DailyAccountInsight` with no date bound. This loads unboundedly more data as historical imports accumulate.
- Fix approach: Limit to the last 90 days, or push aggregation into SQL with `func.sum()`.

**Reach calculation uses `impressions / frequency` summation across days:**
- `_aggregate_account()` in `backend/app/engine/collector.py` lines 160–161 computes reach by summing `impressions / frequency` per day. This double-counts reach for users exposed on consecutive days and is unreliable when `frequency` is 0 for some days (those days are excluded).
- Fix approach: Store raw `reach` from the API/CSV; only use `impressions / frequency` as a fallback.

**`_action_plan_is_generic()` may discard valid AI responses:**
- `AISummaryService._action_plan_is_generic()` in `backend/app/services/ai_summary.py` lines 344–352 rejects any AI response containing phrases like `"review your campaigns"` and replaces it with the deterministic fallback. A valid response that uses one of these phrases in a substantive sentence is silently discarded.

**`_classify_report_type()` only checks first 50 rows:**
- `backend/app/services/csv_import.py` line 495 limits classification to `rows[:50]`. If "Reporting Starts"/"Reporting Ends" headers appear after row 50, the report type is misclassified as `daily_breakdown`, enabling trend rules on data that doesn't support them.

**`_upsert_campaigns()` overwrites status on partial re-imports:**
- Each CSV import can overwrite `status` and `objective` on existing campaigns. A partial upload that doesn't include paused campaigns will silently revert them to whatever the new file says (or the default `"ACTIVE"`).
- Files: `backend/app/services/csv_import.py` lines 537–561

**`HighCPARule` account baseline is skewed by outliers:**
- `backend/app/engine/rules/cpa_rules.py` `HighCPARule.evaluate()` computes `account_avg_cpa` from all campaigns with conversions. One very expensive campaign raises the baseline, potentially masking moderate CPA offenders.

**No compound index on insight tables for the primary query pattern:**
- The collector queries insight tables filtered by `(ad_account_id, date >= X, date <= Y)`. Indexes exist on `ad_account_id` and `campaign_id`/`ad_set_id` separately, but no compound `(id, date)` index exists.
- Files: `backend/app/models/insights.py`, `backend/alembic/versions/`
- Fix approach: Add `Index("ix_insights_daily_account_account_date", "ad_account_id", "date")` and equivalents for campaign and ad set insight tables.

**Audit job polling has a 180-second frontend cap:**
- Frontend polls `GET /audit/job/{id}` every 3 seconds for up to 60 attempts (180 seconds). Large accounts + slow AI provider can exceed 3 minutes, causing a frontend timeout error even when the backend eventually succeeds.
- Files: `frontend/src/app/dashboard/audits/page.tsx`
- Fix approach: Increase cap (e.g., 100 attempts = 5 minutes), or use server-sent events for real-time job status.

---

## Test Coverage Gaps

**No end-to-end Celery task test (audit pipeline):**
- `run_audit_job` is not tested through a real task broker. Tests in `backend/tests/test_audit_and_entitlements_integration.py` call engine functions directly, bypassing Celery.
- Files: `backend/app/tasks/audit.py`
- Risk: Task failure modes (Redis timeout, AI failure mid-task, DB reconnect) are untested.
- Priority: High

**No tests for `meta_sync.py` or `meta_auth.py`:**
- The Meta OAuth and real sync flow have no automated tests. The mock service is used in engine tests but actual HTTP client paths (pagination, token refresh, field mapping) are not exercised.
- Files: `backend/app/services/meta_sync.py`, `backend/app/services/meta_auth.py`
- Priority: High

**No frontend tests:**
- Zero test files exist under `frontend/src/`. The `audit.ts` utility functions (`deriveTopActions`, `deriveBiggestLeak`, `deriveDeterministicActionPlan`) have non-trivial branching logic and no coverage.
- Priority: Medium

**Trend rules have no dedicated unit tests:**
- `AdFatigueTrendRule`, `SpendSpikeAnomalyRule`, `ROASDropAnomalyRule` in `backend/app/engine/rules/trend_rules.py` depend on `calc_wow_delta()`. No tests verify these rules fire at the correct WoW thresholds.
- Files: `backend/tests/engine/test_rules.py`
- Priority: Medium

**Rate limiter in-memory fallback path is not tested:**
- No test simulates Redis failure and verifies that the `_increment_memory()` fallback correctly enforces limits.
- Files: `backend/app/services/rate_limit.py`
- Priority: Low

**`tests/test_phase8.sqlite3` is committed to the repo:**
- The test database artifact is tracked in git, inflating repo size and potentially containing a stale schema.
- Files: `backend/tests/test_phase8.sqlite3`, `backend/tests/test_phase8.sqlite3-journal`
- Fix approach: Add `*.sqlite3` and `*.sqlite3-journal` to `.gitignore` and remove from tracking with `git rm --cached`.

---

*Concerns audit: 2026-04-03*
