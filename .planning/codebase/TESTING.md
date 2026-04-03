# Testing Patterns
_Last updated: 2026-04-03_

## Summary
The backend has a two-tier test suite: pure-Python unit tests for the deterministic audit engine (no DB, no HTTP), and SQLite-backed integration tests for API flows. The frontend has zero tests. pytest is the sole runner; no coverage threshold is enforced. CI runs all backend tests plus frontend lint and build on every push to `main`.

---

## Test Framework

**Runner:** pytest 8.3.5
**Config:** `backend/pytest.ini`

```ini
[pytest]
testpaths = tests
asyncio_default_fixture_loop_scope = function
markers =
    smoke: minimal fast checks for local health
```

**Assertion library:** pytest built-in + `pytest.approx` for float comparisons
**HTTP test client:** `fastapi.testclient.TestClient`
**Async:** `pytest-asyncio 0.25.3` (configured but async tests are minimal)

**Run commands:**
```bash
cd backend
pytest                                          # Run all tests
pytest -m smoke                                 # Only smoke tests
pytest -q                                       # Quiet (used in CI)
pytest tests/engine/                            # Engine unit tests only (no DB)
pytest tests/test_auth_integration.py           # Single file
pytest tests/engine/test_scoring_calibration.py # Single file
```

---

## CI Pipeline (`.github/workflows/ci.yml`)

**Backend job (`ubuntu-latest`, Python 3.12):**
1. Spin up PostgreSQL 16 as a service
2. Install `backend/requirements.txt`
3. Run `pytest -q` with `DATABASE_URL` pointing at the CI Postgres instance

**Frontend job (`ubuntu-latest`, Node 20):**
1. `npm ci`
2. `npm run lint` (ESLint via Next.js)
3. `npm run build`

Integration tests use SQLite locally (see conftest below) but CI points at real Postgres — the `DATABASE_URL` env var drives which database is used.

---

## Test File Organization

```
backend/tests/
├── conftest.py                              # Integration fixtures: TestClient, SQLite, db_session
├── helpers.py                               # DB seeding functions shared across integration tests
├── test_ai_summary.py                       # Unit: AISummaryService prompt building
├── test_audit_and_entitlements_integration.py  # API: audit run flow + entitlement limits
├── test_auth_integration.py                 # API: register / verify / login / /me
├── test_csv_import_integration.py           # API: CSV + XLSX upload and parsing
├── test_entitlements.py                     # Unit: EntitlementService free vs premium
├── test_scoring_engine.py                   # Unit: scoring + deduplication
├── test_sync_job_flow.py                    # Unit: Celery task state-machine
├── test_phase8.sqlite3                      # Auto-created SQLite file (gitignored)
└── engine/
    ├── conftest.py                          # Engine conftest: no DB, overrides reset_db
    ├── fixtures.py                          # Factory functions returning pure dataclasses
    ├── datasets/
    │   ├── expected_outcomes.py             # ScenarioContract definitions
    │   ├── healthy_baseline.csv             # Reference CSV fixtures
    │   ├── high_cpa.csv
    │   └── weak_ctr.csv
    ├── test_expected_outcomes.py            # Contract-based regression tests
    ├── test_fixture_scenarios.py            # Full pipeline tests (rules + scoring)
    ├── test_rules.py                        # Per-rule deterministic unit tests
    └── test_scoring_calibration.py          # compute_scores() contract + score bands
```

---

## Two-Tier Test Architecture

### Tier 1: Engine Unit Tests (`tests/engine/`)

No database, no HTTP, no Celery. Rules are pure Python functions operating on `@dataclass` objects from `backend/app/engine/types.py`.

The engine `conftest.py` overrides the parent `reset_db` fixture so SQLAlchemy never runs:
```python
# backend/tests/engine/conftest.py
os.environ.setdefault("DATABASE_URL", "sqlite:///./engine_test.sqlite3")
os.environ.setdefault("SECRET_KEY", "engine-test-secret-not-for-production")

@pytest.fixture(autouse=True)
def reset_db():
    """Override parent: no DB operations for engine tests."""
    yield
```

### Tier 2: Integration Tests (`tests/`)

Use a real SQLite file (`test_phase8.sqlite3`) with the full schema. The parent `conftest.py` drops and recreates all tables before **every test** via `autouse=True` — guarantees full isolation.

```python
# backend/tests/conftest.py
TEST_DB_PATH = Path(__file__).resolve().parent / "test_phase8.sqlite3"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"

engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

@pytest.fixture()
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c
```

The FastAPI `get_db` dependency is globally overridden:
```python
app.dependency_overrides[get_db] = _override_get_db
```

---

## Engine Test Patterns

### Fixture Factories (`tests/engine/fixtures.py`)

All engine test data is built via factory functions that return pure `@dataclass` objects with sensible defaults. Override only the fields that matter for the test.

**Available factories:**
```python
make_daily_points(n, *, ctr, frequency, spend_per_day, impressions_per_day, ...)
    → list[DailyMetricPoint]

make_declining_ctr_points(n=28, start_ctr=2.5, end_ctr=1.0)
    → list[DailyMetricPoint]   # linear CTR decline

make_spiking_frequency_points(n=28)
    → list[DailyMetricPoint]   # low then high frequency in final 7 days

make_campaign(campaign_id, campaign_name, status, ctr, roas, spend_share, daily_points, ...)
    → CampaignAuditMetrics

make_adset(ad_set_id, campaign_id, ctr, roas, ...)
    → AdSetAuditMetrics

make_account(total_spend, ctr, roas, frequency, ...)
    → AccountAuditMetrics

make_snapshot(account, campaigns, ad_sets, data_mode="daily_breakdown", ad_account_id="act_test")
    → AccountAuditSnapshot
```

Usage:
```python
# Make a healthy campaign with all defaults
campaign = make_campaign()

# Override only the field under test
campaign = make_campaign(ctr=0.3, total_spend=1000.0, total_impressions=50_000)

# Build a full snapshot
snapshot = make_snapshot(
    account=make_account(total_spend=2000.0, ctr=0.55),
    campaigns=[campaign],
)
```

**Named scenario snapshots** (pre-built for common test cases):

| Function | Description |
|----------|-------------|
| `healthy_snapshot()` | CTR ≥ 3.5%, CPA ≤ 15, ROAS ≥ 4 — most rules must NOT fire |
| `low_ctr_snapshot()` | One CRITICAL (0.3%) + one WARNING (0.8%) CTR campaign |
| `high_cpa_snapshot()` | One campaign with CPA ~4× account average |
| `fatigued_snapshot()` | Frequency 6.0 + CTR declining from 2.5% to 0.8% over 28 days |
| `budget_imbalanced_snapshot()` | Dominant low-ROAS (75% spend) + underfunded winner |
| `aggregate_only_snapshot()` | `data_mode="period_aggregate"`, no daily rows |
| `weak_cvr_snapshot()` | Zero and low CVR campaigns |
| `uneven_spend_snapshot()` | Alternating high/low daily spend (pacing issues) |
| `broken_funnel_snapshot()` | Zero conversions + negative ROAS |

### Per-Rule Tests (`tests/engine/test_rules.py`)

Each rule gets a `class TestXxxRule:` block. Rules are instantiated at class level. Tests call `rule.evaluate(snapshot)` directly and assert on the returned `Finding` list.

```python
class TestLowCTRRule:
    rule = LowCTRRule()

    def test_critical_ctr_fires(self):
        snapshot = low_ctr_snapshot()
        findings = self.rule.evaluate(snapshot)
        critical = [f for f in findings if f.severity == Severity.CRITICAL]
        assert critical, "Expected a CRITICAL CTR finding"
        f = critical[0]
        assert f.rule_id == "ctr_low_campaign"
        assert f.category == Category.CTR
        assert f.metric_value == pytest.approx(0.3)

    def test_silent_on_healthy(self):
        findings = self.rule.evaluate(healthy_snapshot())
        assert not findings
```

Every rule should have tests for:
1. **Fire case** — snapshot crosses the threshold → finding returned
2. **Silence case** — healthy snapshot → no findings returned
3. **Metadata validation** — `rule_id`, `severity`, `category`, `metric_value`, `estimated_waste` checked

File-level helper functions used in `test_rules.py`:
```python
def rule_ids(findings) -> list[str]:
    return [f.rule_id for f in findings]

def first(findings):
    assert findings, "Expected at least one finding but got none"
    return findings[0]
```

### Contract Tests (`tests/engine/test_expected_outcomes.py`)

`ScenarioContract` in `tests/engine/datasets/expected_outcomes.py` is the authoritative specification for engine behavior on each named scenario. Tests call `_assert_contract(snapshot, "name")`.

```python
@dataclass
class ScenarioContract:
    description: str
    must_fire: list[str] = field(default_factory=list)      # rule_ids that MUST appear
    must_not_fire: list[str] = field(default_factory=list)  # rule_ids that must NOT appear
    min_health_score: float = 0.0
    max_health_score: float = 100.0
    min_findings: int | None = None
    max_findings: int | None = None
```

Example contracts:
```python
CONTRACTS = {
    "healthy": ScenarioContract(
        must_not_fire=["ctr_low_campaign", "cpa_high_campaign", "budget_concentration_risk", "weak_cvr"],
        min_health_score=70.0,
        max_findings=5,
    ),
    "broken_funnel": ScenarioContract(
        must_fire=["cpa_zero_conversions", "cpa_negative_roas"],
        max_health_score=59.0,
        min_findings=2,
    ),
    "budget_imbalanced": ScenarioContract(
        must_fire=["budget_concentration_risk", "underfunded_winner"],
        min_findings=2,
        max_health_score=90.0,
    ),
}
```

**Adding a new scenario:**
1. Add a snapshot builder function to `tests/engine/fixtures.py`
2. Add a `ScenarioContract` entry to `tests/engine/datasets/expected_outcomes.py`
3. Add a test class to `tests/engine/test_expected_outcomes.py` calling `_assert_contract(snapshot, "name")`

### Scoring Calibration Tests (`tests/engine/test_scoring_calibration.py`)

Tests `compute_scores()` contract independently of individual rules.

```python
class TestComputeScoresContract:
    def test_no_findings_score_is_100(self): ...
    def test_score_bounded_0_to_100(self): ...
    def test_more_findings_lower_score(self): ...
    def test_critical_worse_than_medium(self): ...
    def test_deterministic(self): ...                         # same input → same output
    def test_returns_five_pillars(self): ...
    def test_pillar_keys(self): ...     # {"acquisition","conversion","budget","trend","structure"}
    def test_pillar_weights_sum_to_one(self): ...
    def test_account_scope_penalises_more_than_ad_scope(self): ...
    def test_sparse_data_reduces_penalty(self): ...

class TestScoreBands:                                         # end-to-end with all rules
    def test_healthy_account_scores_above_80(self): ...
    def test_broken_funnel_scores_in_at_risk_or_critical_band(self): ...
    def test_all_scores_bounded(self): ...

class TestPillarSeverityOrdering:
    def test_severity_order_is_preserved_in_acquisition_pillar(self): ...
```

Score band definitions validated by tests:
- 80–100: Healthy
- 60–79: Warning
- 40–59: At risk
- 0–39: Critical

The helper `_f(severity, category, ...)` creates minimal `Finding` objects for isolated scoring tests:
```python
def _f(severity, category, score_impact=0.0, estimated_waste=100.0, entity_type="campaign"):
    return Finding(rule_id="test_rule", severity=severity, category=category, ...)
```

---

## Integration Test Patterns

### Database Seeding (`tests/helpers.py`)

Shared seeding functions, all accepting `db: Session` as first argument:

```python
create_user(db, email="user@example.com", password="secret123") -> User
auth_header_for_user(user_id) -> {"Authorization": "Bearer <token>"}
seed_connected_account(db, user) -> MetaAdAccount
seed_audit_data(db, account) -> None        # 10 days of daily insights + campaign structure
seed_audit_run_with_findings(db, user_id, account_id, count=5) -> AuditRun
```

### Standard Integration Test Shape

```python
def test_run_audit_and_get_latest(client, db_session, monkeypatch):
    # Seed
    user = create_user(db_session, "audit@example.com")
    account = seed_connected_account(db_session, user)
    seed_audit_data(db_session, account)
    headers = auth_header_for_user(user.id)

    # Act
    resp = client.post("/api/audit/run", headers=headers)

    # Assert
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "pending"
```

Always include `resp.text` in assertion failure messages to show the actual API response.

### Monkeypatching Celery Tasks

Celery tasks are executed synchronously in tests by patching `.delay()`:

```python
def _patch_audit_delay(monkeypatch):
    def _delay(audit_run_id: str):
        _run_audit_job(audit_run_id, "test-audit-task")
        return SimpleNamespace(id="test-audit-task")
    monkeypatch.setattr("app.routes.audit.run_audit_job.delay", _delay)
```

### File Upload Tests

```python
upload = client.post(
    "/api/sync/import-report",
    headers=headers,
    files={"file": ("history.csv", csv_content, "text/csv")},
    data={"replace_existing": "true"},
)
assert upload.status_code == 200, upload.text
```

### Smoke Marker

Fast integration tests that verify the core user flow are marked `@pytest.mark.smoke`:
```python
@pytest.mark.smoke
def test_register_login_me_flow(client): ...
```

Run with `pytest -m smoke` for a quick local sanity check.

### SimpleNamespace Fakes

AI summary tests and sync tests use `SimpleNamespace` instead of mocks where the code under test only accesses attributes:
```python
finding = SimpleNamespace(
    id="finding-1", rule_id="rule_1", severity="high",
    category="performance", title="Finding 1",
    estimated_waste=75.0, estimated_uplift=0.0,
)
```

---

## What Is Tested

| Area | File(s) |
|------|---------|
| Every `@register_rule` fires on triggering data | `tests/engine/test_rules.py` |
| Every `@register_rule` is silent on healthy data | `tests/engine/test_rules.py` |
| Rule metadata (`rule_id`, `category`, `metric_value`, `waste`) | `tests/engine/test_rules.py` |
| `compute_scores()` contract (bounds, determinism, pillar keys, weights) | `tests/engine/test_scoring_calibration.py` |
| Score band ordering per severity and per scenario | `tests/engine/test_scoring_calibration.py` |
| Named scenario contracts (`must_fire` / `must_not_fire` / score range) | `tests/engine/test_expected_outcomes.py` |
| Full pipeline (all rules + scoring) on all scenarios | `tests/engine/test_fixture_scenarios.py` |
| Auth flow (register → verify email → login → /me) | `tests/test_auth_integration.py` |
| Audit run creation, job status polling, latest endpoint | `tests/test_audit_and_entitlements_integration.py` |
| Free vs premium findings limit enforcement | `tests/test_audit_and_entitlements_integration.py` |
| Entitlement plan tiers (free / premium) | `tests/test_entitlements.py` |
| CSV import (English headers, Russian headers, XLSX) | `tests/test_csv_import_integration.py` |
| Sync job state transitions (pending → completed / failed / retry) | `tests/test_sync_job_flow.py` |
| AISummaryService prompt building and serialization | `tests/test_ai_summary.py` |
| Scoring engine deduplication | `tests/test_scoring_engine.py` |

---

## Coverage Gaps

**No coverage at all:**
- **Frontend** — zero test files in `frontend/`; no Jest, Vitest, or Playwright configured
- **Meta OAuth flow** — `/api/meta/*` routes (callback, token exchange, ad account listing) have no integration tests
- **Billing / Stripe webhooks** — `backend/app/routes/billing.py` has no test file
- **Alembic migrations** — no migration regression tests; schema changes are validated only by `Base.metadata.create_all` in test setup

**Thin coverage:**
- **Password reset flow** — auth route exists but no dedicated test for reset token issuance and consumption
- **Email delivery** — `EmailDeliveryError` path is exercised indirectly via register flow test; send templates not tested
- **Rate limiting** — `enforce_rate_limit` is called in routes but burst traffic is not simulated
- **Celery task retry logic** — success and failure transitions are tested in `test_sync_job_flow.py` but retry countdown and max-retry exhaustion are not fully exercised

**Rule gap:**
- `InefficientAdSetVsSiblingsRule` (`opportunity_rules.py`) is imported in `test_rules.py` but has no `TestXxx` class; behavior is not verified

---

## CSV Dataset Files

Located in `tests/engine/datasets/`:
- `healthy_baseline.csv` — reference export from a well-performing account
- `high_cpa.csv` — export with high-CPA campaign
- `weak_ctr.csv` — export with sub-benchmark CTR campaigns

These are reference artifacts; the primary fixture mechanism for engine tests is the Python factory functions in `tests/engine/fixtures.py`, not CSV loading.

---

*Testing analysis: 2026-04-03*
