"""
Expected-outcome contracts for named scenario snapshots.

Each entry maps a scenario name to explicit assertions the engine must satisfy:
  - must_fire:       rule_ids that MUST appear in findings
  - must_not_fire:   rule_ids that MUST NOT appear in findings
  - min_health_score / max_health_score: health score must fall in this range
  - min_findings / max_findings:         finding count bounds (None = unconstrained)

These contracts are the authoritative specification for the engine's behaviour on
each scenario.  Update them deliberately when rule thresholds are intentionally
changed.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScenarioContract:
    description: str
    must_fire: list[str] = field(default_factory=list)
    must_not_fire: list[str] = field(default_factory=list)
    min_health_score: float = 0.0
    max_health_score: float = 100.0
    min_findings: int | None = None
    max_findings: int | None = None


CONTRACTS: dict[str, ScenarioContract] = {
    # ── Healthy baseline ────────────────────────────────────────────────────
    "healthy": ScenarioContract(
        description=(
            "Well-performing account: CTR ≥ 3.5%, CPA ≤ 15, frequency ≤ 2, ROAS ≥ 4. "
            "Major problem rules must stay silent and health score must be high."
        ),
        must_not_fire=[
            "ctr_low_campaign",
            "cpa_high_campaign",
            "cpa_zero_conversions",
            "cpa_negative_roas",
            "budget_concentration_risk",
            "weak_cvr",
        ],
        min_health_score=70.0,
        max_findings=5,  # minor warnings allowed but no major findings
    ),

    # ── Weak CTR ────────────────────────────────────────────────────────────
    "low_ctr": ScenarioContract(
        description=(
            "Two campaigns: one at 0.3% CTR (critical) and one at 0.8% CTR (warning). "
            "CTR rule must fire twice, score must be degraded vs healthy baseline."
        ),
        must_fire=["ctr_low_campaign"],
        min_findings=2,   # at least one finding per campaign
        max_health_score=89.0,
    ),

    # ── High CPA ────────────────────────────────────────────────────────────
    "high_cpa": ScenarioContract(
        description=(
            "Normal campaign (CPA ≈ $20) alongside one with CPA ≈ 4× the account average. "
            "High-CPA rule must fire and target only the offending campaign."
        ),
        must_fire=["cpa_high_campaign"],
        must_not_fire=[],
        min_findings=1,
        max_health_score=95.0,
    ),

    # ── Fatigued account ────────────────────────────────────────────────────
    "fatigued": ScenarioContract(
        description=(
            "High frequency (6.0) with a CTR that declines from 2.5% to 0.8% over 28 days. "
            "At least one fatigue-related rule must fire."
        ),
        must_fire=[],  # any of the fatigue rule set
        must_not_fire=[],
        max_health_score=94.0,
        min_findings=1,
    ),

    # ── Budget imbalanced ───────────────────────────────────────────────────
    "budget_imbalanced": ScenarioContract(
        description=(
            "Dominant campaign takes 75% of spend at low ROAS while a winner is underfunded. "
            "Budget concentration and underfunded-winner rules must fire."
        ),
        must_fire=["budget_concentration_risk", "underfunded_winner"],
        min_findings=2,
        max_health_score=90.0,
    ),

    # ── Aggregate-only export ───────────────────────────────────────────────
    "aggregate_only": ScenarioContract(
        description=(
            "Period-aggregate export with no daily rows. "
            "Aggregate rules must fire; daily trend rules must stay silent."
        ),
        must_not_fire=["ad_fatigue_trend", "ctr_declining"],
        min_findings=1,
    ),

    # ── Broken conversion funnel ────────────────────────────────────────────
    "broken_funnel": ScenarioContract(
        description=(
            "High spend + zero or near-zero conversions across both campaigns. "
            "Zero-conversion and negative-ROAS rules must fire; score must be low."
        ),
        must_fire=["cpa_zero_conversions", "cpa_negative_roas"],
        max_health_score=59.0,
        min_findings=2,
    ),

    # ── Weak CVR ────────────────────────────────────────────────────────────
    "weak_cvr": ScenarioContract(
        description=(
            "Campaigns with plenty of clicks but very low / zero conversion rates. "
            "Weak-CVR rule must fire."
        ),
        must_fire=["weak_cvr"],
        min_findings=1,
        max_health_score=95.0,
    ),
}
