# Coding Conventions
_Last updated: 2026-04-03_

## Summary
The backend is Python 3.12 with FastAPI and SQLAlchemy 2.0, following PEP 8 naming throughout. The frontend is TypeScript 5 / Next.js 14 with strict mode and a `@/` path alias. No project-wide autoformatter (Black, Ruff, or Prettier) is configured; the only pre-commit hook is `detect-secrets`. Conventions are enforced by code review only, not tooling.

---

## Python (Backend)

### File and Module Naming

- Route modules: `snake_case.py` (`audit.py`, `auth.py`, `billing.py`, `meta.py`)
- Model modules: one domain per file (`user.py`, `audit.py`, `campaign.py`, `insights.py`)
- Schema modules: mirror model names (`app/schemas/audit.py` mirrors `app/models/audit.py`)
- Service modules: verb/noun descriptor (`auth.py`, `meta_sync.py`, `csv_import.py`, `ai_summary.py`)
- Rule modules: domain-prefixed (`ctr_rules.py`, `cpa_rules.py`, `budget_rules.py`, `frequency_rules.py`)
- Test files: `test_<domain>.py` or `test_<domain>_integration.py`

### Python Version Features

All engine and test files start with:
```python
from __future__ import annotations
```
This is required in engine files and test fixtures; optional elsewhere.

### Naming Conventions

**Functions:** `snake_case` — `hash_password`, `get_user_by_email`, `create_access_token`, `seed_connected_account`

**Classes:** `PascalCase` — `WeakAccountCTRRule`, `AuditRule`, `EntitlementService`, `MetaSyncOrchestrator`

**Constants:** `UPPER_SNAKE_CASE` at module level — `CTR_CRITICAL_THRESHOLD`, `CTR_WARNING_THRESHOLD`, `CTR_GOOD_THRESHOLD`

**Rule IDs:** lowercase `snake_case` string, domain-prefixed — `"ctr_low_campaign"`, `"budget_concentration_risk"`, `"cpa_negative_roas"`

**Private helpers:** leading underscore — `_is_local_frontend`, `_serialize`, `_get_selected_account`

### SQLAlchemy Model Pattern

Models inherit from `Base` (from `app/database.py`). All columns use `Mapped[T]` / `mapped_column()` (SQLAlchemy 2.x style). UUIDs are `str(uuid.uuid4())` defaults.

```python
# backend/app/models/user.py
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- Nullable columns: `Mapped[T | None]` with `nullable=True`
- Relationships: `Mapped[list["Child"]]` with `back_populates` and `cascade="all, delete-orphan"`
- Foreign keys: `ForeignKey("table.column", ondelete="CASCADE")`
- Indexed columns: flagged inline with `index=True`

### Pydantic Schema Pattern

Schemas inherit from `pydantic.BaseModel`. No shared base class. Naming convention:
- Response schemas end in `Response`: `AuditFindingResponse`, `UserResponse`
- Request schemas end in `Request` or `Create`: `LoginRequest`, `UserCreate`

Use `model_config = {"from_attributes": True}` only when serializing from ORM instances:
```python
class RecommendationResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    title: str
    body: str
```

### Route Pattern

Each route file creates its own `APIRouter` with `prefix` and `tags`:
```python
router = APIRouter(prefix="/audit", tags=["audit"])
settings = get_settings()
logger = get_logger(__name__)
```

Route functions are **synchronous** (`def`, not `async def`). Auth via `Depends(get_current_user)`, DB via `Depends(get_db)`.

Routes return typed Pydantic schemas — never raw dicts:
```python
@router.post("/run", response_model=AuditJobResponse, status_code=status.HTTP_201_CREATED)
def run_new_audit(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuditJobResponse:
    ...
```

Private helpers in route files are prefixed with `_`: `_safe_pct_delta`, `_serialize`, `_score_response`.

### Error Handling Pattern

```python
# Conflict
raise HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail={"detail": "Email already registered", "code": "EMAIL_ALREADY_REGISTERED"},
)

# Unauthorized
raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"detail": "Invalid credentials", "code": "INVALID_CREDENTIALS"},
)

# Simple not-found
raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit run not found")
```

`detail` is a dict with `"detail"` + `"code"` for machine-readable errors; plain string for simple cases.

Broad `except Exception as exc:` is used only in resilience/health wrappers, always annotated `# noqa: BLE001`.

### Logging Pattern

```python
from app.logging_config import get_logger
logger = get_logger(__name__)

# Structured event log
logger.warning(
    "auth.register_conflict",
    extra={"request_id": ..., "code": "EMAIL_ALREADY_REGISTERED"},
)
logger.exception("auth.register_email_failed", extra={"user_id": user.id})
```

Event names use dotted namespaces. No bare `print()`.

### Engine Rule Registration Pattern

Every rule lives in `backend/app/engine/rules/<domain>_rules.py`. Required structure:

```python
@register_rule
class LowCTRRule(AuditRule):
    rule_id = "ctr_low_campaign"          # snake_case, domain-prefixed
    category = Category.CTR
    description = "Flags campaigns with below-benchmark click-through rates"

    def evaluate(self, snapshot: AccountSnapshot) -> list[Finding]:
        findings: list[Finding] = []
        for c in snapshot.campaigns:
            if c.status != "ACTIVE" or c.total_impressions < 1000:
                continue                  # guard clauses first
            ...
        return findings
```

The base class:
```python
class AuditRule(ABC):
    rule_id: str = ""
    category: Category = Category.PERFORMANCE
    severity: Severity = Severity.MEDIUM

    @abstractmethod
    def evaluate(self, snapshot: AccountAuditSnapshot) -> list[Finding]: ...

    def finding(self, **kwargs) -> Finding:
        return Finding(rule_id=self.rule_id, category=self.category, severity=self.severity, **kwargs)
```

**Two finding construction patterns:**

Pattern 1 — `self.finding()` (fixed severity at class level):
```python
return [self.finding(
    title="Account-wide CTR is weak",
    entity_type="account", entity_id=snapshot.ad_account_id, entity_name="Account",
    metric_value=snapshot.account.ctr, threshold_value=1.0,
    estimated_waste=snapshot.account.total_spend * 0.12,
    recommendation_key=self.rule_id, score_impact=8,
)]
```

Pattern 2 — `Finding(...)` directly (severity varies per case within the same rule):
```python
findings.append(Finding(
    rule_id=self.rule_id,
    severity=Severity.CRITICAL,    # overrides class-level severity
    category=Category.CTR,
    title=f"Critically low CTR: {c.avg_ctr:.2f}%",
    entity_type="campaign", entity_id=c.campaign_id, entity_name=c.campaign_name,
    metric_value=c.avg_ctr, threshold_value=CTR_CRITICAL_THRESHOLD,
    estimated_waste=c.total_spend * 0.4,
    recommendation_key="ctr_low_critical",
))
```

All rule modules must be imported in `backend/app/engine/rules/__init__.py` to fire `@register_rule`:
```python
from app.engine.rules import ctr_rules   # noqa: F401
from app.engine.rules import budget_rules  # noqa: F401
# one import per module
```

### Engine Types (Dataclasses)

All engine data objects are pure Python `@dataclass` — no ORM, no Pydantic. In `backend/app/engine/types.py`.

Enums:
```python
class Severity(str, Enum): LOW / MEDIUM / HIGH / CRITICAL
class Category(str, Enum): PERFORMANCE / BUDGET / TREND / CTR / FREQUENCY / CPA / OPPORTUNITY / STRUCTURE / ACCOUNT / PLACEMENT
```

Key dataclasses: `DailyMetricPoint`, `CampaignAuditMetrics`, `AdSetAuditMetrics`, `AccountAuditMetrics`, `AccountAuditSnapshot`, `Finding`, `ScoreBreakdown`, `AuditRunResult`.

`CampaignAuditMetrics` exposes computed properties (`avg_ctr`, `avg_frequency`, `daily_ctr`, `days_active`) as `@property` on top of raw stored fields.

### Import Organization

Order (PEP 8, by convention only):
1. `from __future__ import annotations`
2. Standard library
3. Third-party (`fastapi`, `sqlalchemy`, `pydantic`)
4. Internal app modules (`from app.config import ...`)

`noqa` usage:
- `# noqa: F401` — side-effect imports in `__init__.py` (rule registration)
- `# noqa: BLE001` — intentional broad `except Exception` in resilience code
- `# noqa: E402` — circular import workarounds between `models/campaign.py` and `models/insights.py`

---

## TypeScript (Frontend)

### File Naming

- React components: `kebab-case.tsx` (`health-score.tsx`, `findings-list.tsx`, `ai-summary-block.tsx`)
- Library modules: `kebab-case.ts` (`audit.ts`, `api.ts`, `auth.ts`)
- Pages: `page.tsx` (Next.js App Router)
- Layouts: `layout.tsx`

### Naming Conventions

- Interfaces and types: `PascalCase` — `AuditFinding`, `ScoreBreakdown`, `AuditAISummary`
- Variables and functions: `camelCase`
- Local props interface: `interface Props` scoped to the file

### TypeScript Config (`frontend/tsconfig.json`)

- `"strict": true` — all strict checks enabled
- `"noEmit": true` — type-check only; Next.js handles compilation
- `"isolatedModules": true`
- `"paths": { "@/*": ["./src/*"] }` — use `@/` for all internal imports, never `../../`

### Interface Style

Fixed-value strings use union literals with a trailing `| string` escape for forward-compatibility:
```typescript
severity: "critical" | "high" | "medium" | "low" | string;
status: "completed" | "failed" | "pending" | string;
```

Optional nullable fields:
```typescript
strongest_issue?: string | null;
recommendation_key: string | null;
```

### Component Style

Named exports only (no default exports for components):
```typescript
export function HealthScore({ score, size = "lg" }: Props) { ... }
```

Client components that use hooks begin with:
```typescript
"use client";
import { useState, useCallback } from "react";
```

Server components (pure rendering) omit the directive.

### API Call Pattern

All API calls use `apiFetch<T>` from `frontend/src/lib/api.ts`:
```typescript
const data = await apiFetch<AuditDashboardData>("/audit/dashboard");
```

Error extraction:
```typescript
const message = err instanceof Error ? err.message : "Failed to load data";
```

### Tailwind CSS

Severity color mapping (consistent across all dashboard components):
| Severity | Background | Text |
|----------|------------|------|
| critical | `bg-rose-100` | `text-rose-700` |
| high | `bg-orange-100` | `text-orange-700` |
| medium | `bg-amber-100` | `text-amber-700` |
| low | `bg-sky-100` | `text-sky-700` |

Score health colors: `text-emerald-600` (≥80), `text-amber-600` (≥60), `text-orange-600` (≥40), `text-rose-600` (<40).

Card pattern: `rounded-2xl border border-slate-200 bg-white p-5 shadow-sm`

---

## Linting and Formatting

**Backend:** No linter config file detected (no `.flake8`, `pyproject.toml`, or `ruff.toml`). `noqa` comments are used ad hoc. Adding Ruff is a documented gap.

**Frontend:** `next lint` (ESLint via Next.js built-in config). Runs in CI on every push to `main`.

**Pre-commit:** `pre-commit-config.yaml` runs only `detect-secrets` (Yelp v1.4.0) against `.secrets.baseline`. No formatting or lint hooks are wired.

---

*Convention analysis: 2026-04-03*
