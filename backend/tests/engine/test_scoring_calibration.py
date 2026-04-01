"""
Score calibration tests.

Validates that compute_scores() produces sensible output across the
seven fixture scenarios and that score bands align with expected ranges.

Score band definitions (from Deterministic_Engine_Rule_Depth_Checklist.md):
  80–100  Healthy / no material issues
  60–79   Warning — attention recommended
  40–59   At risk — action required
  0–39    Critical — urgent intervention
"""
from __future__ import annotations

import pytest

from app.engine.rules import get_all_rules
from app.engine.scoring import compute_scores
from app.engine.types import AccountAuditSnapshot, Category, Finding, Severity

from tests.engine.fixtures import (
    aggregate_only_snapshot,
    broken_funnel_snapshot,
    budget_imbalanced_snapshot,
    fatigued_snapshot,
    healthy_snapshot,
    high_cpa_snapshot,
    low_ctr_snapshot,
)


def _score_snapshot(snapshot: AccountAuditSnapshot) -> float:
    """Run all rules on a snapshot and return the composite health score."""
    findings: list[Finding] = []
    for rule in get_all_rules():
        findings.extend(rule.evaluate(snapshot))
    analysis_days = max(1, (snapshot.analysis_end - snapshot.analysis_start).days + 1)
    health_score, _ = compute_scores(
        findings,
        account_description="test",
        total_spend=snapshot.account.total_spend,
        analysis_days=analysis_days,
    )
    return health_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _f(
    severity: Severity,
    category: Category,
    score_impact: float = 0.0,
    estimated_waste: float = 100.0,
    entity_type: str = "campaign",
    metric_value: float | None = 1.5,
) -> Finding:
    return Finding(
        rule_id="test_rule",
        severity=severity,
        category=category,
        title="Test finding",
        description="Test",
        entity_type=entity_type,
        entity_id="cmp_1",
        entity_name="Campaign 1",
        metric_value=metric_value,
        estimated_waste=estimated_waste,
        estimated_uplift=estimated_waste * 0.5,
        score_impact=score_impact,
    )


# ---------------------------------------------------------------------------
# compute_scores unit tests
# ---------------------------------------------------------------------------

class TestComputeScoresContract:

    def test_returns_five_pillars(self):
        score, pillars = compute_scores(
            [], "No issues", total_spend=5000.0, analysis_days=30
        )
        assert len(pillars) == 5

    def test_no_findings_score_is_100(self):
        score, _ = compute_scores([], "No issues", total_spend=5000.0, analysis_days=30)
        assert score == pytest.approx(100.0)

    def test_score_bounded_0_to_100(self):
        findings = [
            _f(Severity.CRITICAL, Category.PERFORMANCE, score_impact=50.0)
            for _ in range(20)
        ]
        score, pillars = compute_scores(findings, "Bad", total_spend=5000.0, analysis_days=30)
        assert 0.0 <= score <= 100.0
        for pillar in pillars:
            assert 0.0 <= pillar.score <= 100.0

    def test_more_findings_lower_score(self):
        score_clean, _ = compute_scores([], "clean", total_spend=5000.0, analysis_days=30)
        score_one, _ = compute_scores(
            [_f(Severity.HIGH, Category.PERFORMANCE)], "one", total_spend=5000.0, analysis_days=30
        )
        score_many, _ = compute_scores(
            [_f(Severity.HIGH, Category.PERFORMANCE) for _ in range(5)],
            "many", total_spend=5000.0, analysis_days=30,
        )
        assert score_clean > score_one > score_many

    def test_critical_worse_than_medium(self):
        score_critical, _ = compute_scores(
            [_f(Severity.CRITICAL, Category.PERFORMANCE)], "x", total_spend=5000.0, analysis_days=30
        )
        score_medium, _ = compute_scores(
            [_f(Severity.MEDIUM, Category.PERFORMANCE)], "x", total_spend=5000.0, analysis_days=30
        )
        assert score_critical < score_medium

    def test_deterministic(self):
        findings = [
            _f(Severity.HIGH, Category.PERFORMANCE, score_impact=4.0),
            _f(Severity.MEDIUM, Category.BUDGET),
        ]
        a, _ = compute_scores(findings, "run_a", total_spend=3000.0, analysis_days=30)
        b, _ = compute_scores(findings, "run_b", total_spend=3000.0, analysis_days=30)
        assert a == b

    def test_account_scope_penalises_more_than_ad_scope(self):
        score_account, _ = compute_scores(
            [_f(Severity.HIGH, Category.PERFORMANCE, entity_type="account")],
            "x", total_spend=5000.0, analysis_days=30,
        )
        score_ad, _ = compute_scores(
            [_f(Severity.HIGH, Category.PERFORMANCE, entity_type="ad")],
            "x", total_spend=5000.0, analysis_days=30,
        )
        assert score_account < score_ad

    def test_sparse_data_reduces_penalty(self):
        """Sparse data (few days, low spend) reduces the data confidence multiplier to 0.85.

        Use zero estimated_waste so the impact_ratio doesn't skew differently between
        cases.  Then the only difference is confidence (1.1) vs sparse (0.85) and
        persistence (1.1 vs 0.9), producing a clearly lower penalty for sparse data.
        """
        finding = _f(Severity.CRITICAL, Category.PERFORMANCE, estimated_waste=0.0)
        score_confident, _ = compute_scores(
            [finding], "x", total_spend=5000.0, analysis_days=30
        )
        score_sparse, _ = compute_scores(
            [finding], "x", total_spend=100.0, analysis_days=5
        )
        # Sparse data should lead to a smaller penalty (higher score) because
        # the engine is less confident — borderline findings should not tank the score.
        assert score_sparse > score_confident

    def test_pillar_keys(self):
        _, pillars = compute_scores([], "x", total_spend=1000.0, analysis_days=14)
        keys = {p.key for p in pillars}
        assert keys == {"acquisition", "conversion", "budget", "trend", "structure"}

    def test_pillar_weights_sum_to_one(self):
        _, pillars = compute_scores([], "x", total_spend=1000.0, analysis_days=14)
        total_weight = sum(p.weight for p in pillars)
        assert total_weight == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# End-to-end score bands via run_audit
# ---------------------------------------------------------------------------

class TestScoreBands:
    """
    Run the full audit engine on each scenario and verify score falls
    in the expected band.  These are intentionally loose ranges to
    accommodate future threshold adjustments without breaking tests.
    """

    def _score(self, snapshot) -> float:
        return _score_snapshot(snapshot)

    def test_healthy_account_scores_above_80(self):
        score = self._score(healthy_snapshot())
        assert score >= 80.0, f"Healthy account scored {score} — expected ≥ 80"

    def test_low_ctr_scores_below_healthy(self):
        healthy_score = self._score(healthy_snapshot())
        low_ctr_score = self._score(low_ctr_snapshot())
        assert low_ctr_score < healthy_score

    def test_high_cpa_scores_below_healthy(self):
        healthy_score = self._score(healthy_snapshot())
        high_cpa_score = self._score(high_cpa_snapshot())
        assert high_cpa_score < healthy_score

    def test_fatigued_account_scores_below_healthy(self):
        healthy_score = self._score(healthy_snapshot())
        fatigued_score = self._score(fatigued_snapshot())
        assert fatigued_score < healthy_score

    def test_budget_imbalanced_scores_below_healthy(self):
        healthy_score = self._score(healthy_snapshot())
        imbalanced_score = self._score(budget_imbalanced_snapshot())
        assert imbalanced_score < healthy_score

    def test_broken_funnel_scores_in_at_risk_or_critical_band(self):
        score = self._score(broken_funnel_snapshot())
        assert score < 60.0, f"Broken funnel scored {score} — expected < 60"

    def test_aggregate_only_scores_below_healthy(self):
        healthy_score = self._score(healthy_snapshot())
        agg_score = self._score(aggregate_only_snapshot())
        assert agg_score < healthy_score

    def test_all_scores_bounded(self):
        for snapshot_fn in [
            healthy_snapshot,
            low_ctr_snapshot,
            high_cpa_snapshot,
            fatigued_snapshot,
            budget_imbalanced_snapshot,
            aggregate_only_snapshot,
            broken_funnel_snapshot,
        ]:
            score = _score_snapshot(snapshot_fn())
            assert 0.0 <= score <= 100.0, (
                f"{snapshot_fn.__name__} health_score {score} out of range"
            )


# ---------------------------------------------------------------------------
# Score ordering: verify severity ranking is preserved at the pillar level
# ---------------------------------------------------------------------------

class TestPillarSeverityOrdering:

    def _acquisition_score(self, severity: Severity) -> float:
        findings = [_f(severity, Category.PERFORMANCE)]
        _, pillars = compute_scores(findings, "x", total_spend=5000.0, analysis_days=30)
        acq = next(p for p in pillars if p.key == "acquisition")
        return acq.score

    def test_severity_order_is_preserved_in_acquisition_pillar(self):
        s_low = self._acquisition_score(Severity.LOW)
        s_medium = self._acquisition_score(Severity.MEDIUM)
        s_high = self._acquisition_score(Severity.HIGH)
        s_critical = self._acquisition_score(Severity.CRITICAL)
        assert s_low > s_medium > s_high > s_critical
