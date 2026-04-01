"""
Fixture-based scenario tests for the deterministic audit engine.

Each test takes a named scenario snapshot and runs all registered rules +
the scoring function directly — no database or Celery required.

This is the regression safety net: if a rule refactor or threshold change
breaks expected behaviour, these tests catch it before it reaches production.
"""
from __future__ import annotations

from app.engine import rules as _rules_module  # ensures all @register_rule decorators fire  # noqa: F401
from app.engine.rules.base import get_all_rules
from app.engine.scoring import compute_scores
from app.engine.types import AccountAuditSnapshot

from tests.engine.fixtures import (
    aggregate_only_snapshot,
    broken_funnel_snapshot,
    budget_imbalanced_snapshot,
    fatigued_snapshot,
    healthy_snapshot,
    high_cpa_snapshot,
    low_ctr_snapshot,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(snapshot: AccountAuditSnapshot):
    """Run all registered rules against a snapshot and compute health score."""
    findings = []
    for rule in get_all_rules():
        findings.extend(rule.evaluate(snapshot))

    analysis_days = max(1, (snapshot.analysis_end - snapshot.analysis_start).days + 1)
    health_score, scores = compute_scores(
        findings,
        account_description="test",
        total_spend=snapshot.account.total_spend,
        analysis_days=analysis_days,
    )
    total_wasted = min(snapshot.account.total_spend, sum(f.estimated_waste for f in findings))
    total_uplift = sum(f.estimated_uplift for f in findings)

    class Result:
        pass

    r = Result()
    r.findings = findings
    r.scores = scores
    r.health_score = health_score
    r.total_wasted_spend = total_wasted
    r.total_estimated_uplift = total_uplift
    return r


def fired_rule_ids(snapshot: AccountAuditSnapshot) -> set[str]:
    return {f.rule_id for f in _run(snapshot).findings}


def assert_fires(snapshot: AccountAuditSnapshot, *rule_ids: str):
    fired = fired_rule_ids(snapshot)
    for rule_id in rule_ids:
        assert rule_id in fired, (
            f"Expected rule '{rule_id}' to fire but it did not. Fired: {sorted(fired)}"
        )


def assert_silent(snapshot: AccountAuditSnapshot, *rule_ids: str):
    fired = fired_rule_ids(snapshot)
    for rule_id in rule_ids:
        assert rule_id not in fired, (
            f"Rule '{rule_id}' fired unexpectedly on this scenario. Fired: {sorted(fired)}"
        )


# ---------------------------------------------------------------------------
# Scenario: healthy account
# ---------------------------------------------------------------------------

class TestHealthyScenario:
    """A well-performing account should produce a high score and no major findings."""

    def test_no_ctr_rule(self):
        assert_silent(healthy_snapshot(), "ctr_low_campaign")

    def test_no_high_cpa(self):
        assert_silent(healthy_snapshot(), "cpa_high_campaign")

    def test_no_zero_conversion_spend(self):
        assert_silent(healthy_snapshot(), "cpa_zero_conversions")

    def test_no_negative_roas(self):
        assert_silent(healthy_snapshot(), "cpa_negative_roas")

    def test_no_budget_concentration(self):
        assert_silent(healthy_snapshot(), "budget_concentration_risk")

    def test_no_weak_cvr(self):
        assert_silent(healthy_snapshot(), "weak_cvr")

    def test_health_score_is_high(self):
        result = _run(healthy_snapshot())
        assert result.health_score >= 70, (
            f"Healthy account should score ≥70 but got {result.health_score}"
        )


# ---------------------------------------------------------------------------
# Scenario: low CTR
# ---------------------------------------------------------------------------

class TestLowCTRScenario:
    """An account with critically and marginally low CTR campaigns."""

    def test_low_ctr_rule_fires(self):
        assert_fires(low_ctr_snapshot(), "ctr_low_campaign")

    def test_two_ctr_findings(self):
        result = _run(low_ctr_snapshot())
        ctr_findings = [f for f in result.findings if f.rule_id == "ctr_low_campaign"]
        assert len(ctr_findings) == 2, (
            f"Expected 2 CTR findings (one critical, one warning), got {len(ctr_findings)}"
        )

    def test_critical_finding_metric(self):
        result = _run(low_ctr_snapshot())
        critical = next(
            (f for f in result.findings
             if f.rule_id == "ctr_low_campaign" and f.severity.value == "critical"),
            None,
        )
        assert critical is not None, "Expected a CRITICAL CTR finding"
        assert abs(critical.metric_value - 0.3) < 0.05
        assert abs(critical.threshold_value - 0.5) < 0.05

    def test_all_ctr_findings_have_waste(self):
        result = _run(low_ctr_snapshot())
        for f in result.findings:
            if f.rule_id == "ctr_low_campaign":
                assert f.estimated_waste > 0

    def test_health_score_degraded(self):
        result = _run(low_ctr_snapshot())
        assert result.health_score < 90, (
            f"Low-CTR account score should be degraded, got {result.health_score}"
        )


# ---------------------------------------------------------------------------
# Scenario: high CPA
# ---------------------------------------------------------------------------

class TestHighCPAScenario:
    """One campaign with CPA well above the account average."""

    def test_high_cpa_rule_fires(self):
        assert_fires(high_cpa_snapshot(), "cpa_high_campaign")

    def test_finding_targets_offending_campaign(self):
        result = _run(high_cpa_snapshot())
        findings = [f for f in result.findings if f.rule_id == "cpa_high_campaign"]
        assert any(f.entity_id == "cmp_high_cpa" for f in findings), (
            "Expected finding to target 'cmp_high_cpa'"
        )

    def test_normal_campaign_not_flagged(self):
        result = _run(high_cpa_snapshot())
        findings = [f for f in result.findings if f.rule_id == "cpa_high_campaign"]
        assert all(f.entity_id != "cmp_normal" for f in findings), (
            "Normal CPA campaign should not be flagged"
        )

    def test_estimated_waste_positive(self):
        result = _run(high_cpa_snapshot())
        for f in result.findings:
            if f.rule_id == "cpa_high_campaign":
                assert f.estimated_waste > 0


# ---------------------------------------------------------------------------
# Scenario: fatigued account
# ---------------------------------------------------------------------------

class TestFatiguedScenario:
    """Campaign with high frequency + declining CTR triggers fatigue signals."""

    def test_at_least_one_fatigue_rule_fires(self):
        fatigue_ids = {"ad_fatigue_trend", "high_frequency", "ctr_declining", "high_frequency_low_ctr"}
        fired = fired_rule_ids(fatigued_snapshot())
        assert fatigue_ids & fired, (
            f"Expected at least one fatigue rule to fire. Fired: {sorted(fired)}"
        )

    def test_health_score_degraded(self):
        result = _run(fatigued_snapshot())
        assert result.health_score < 95, (
            f"Fatigued account should have a degraded score, got {result.health_score}"
        )
        assert result.health_score < _run(healthy_snapshot()).health_score, (
            "Fatigued account should score lower than a healthy account"
        )


# ---------------------------------------------------------------------------
# Scenario: budget imbalanced
# ---------------------------------------------------------------------------

class TestBudgetImbalancedScenario:
    """Dominant loser + underfunded winner triggers budget reallocation rules."""

    def test_budget_concentration_fires(self):
        assert_fires(budget_imbalanced_snapshot(), "budget_concentration_risk")

    def test_underfunded_winner_fires(self):
        assert_fires(budget_imbalanced_snapshot(), "underfunded_winner")

    def test_underfunded_finding_targets_winner(self):
        result = _run(budget_imbalanced_snapshot())
        winner_finding = next(
            (f for f in result.findings if f.rule_id == "underfunded_winner"),
            None,
        )
        if winner_finding:
            assert winner_finding.entity_id == "cmp_winner", (
                f"Expected entity_id='cmp_winner', got '{winner_finding.entity_id}'"
            )

    def test_total_wasted_spend_attributed(self):
        result = _run(budget_imbalanced_snapshot())
        assert result.total_wasted_spend > 0


# ---------------------------------------------------------------------------
# Scenario: aggregate-only export
# ---------------------------------------------------------------------------

class TestAggregateOnlyScenario:
    """Aggregate exports trigger aggregate-specific rules; daily rules stay silent."""

    def test_aggregate_rule_fires(self):
        agg_ids = {
            "aggregate_weak_account_ctr",
            "aggregate_high_cpm_weak_ctr",
            "aggregate_budget_concentration",
        }
        fired = fired_rule_ids(aggregate_only_snapshot())
        assert agg_ids & fired, (
            f"Expected at least one aggregate rule to fire. Fired: {sorted(fired)}"
        )

    def test_daily_trend_rules_silent(self):
        """Daily trend rules need daily_points — should stay silent on aggregate exports."""
        assert_silent(aggregate_only_snapshot(), "ad_fatigue_trend", "ctr_declining")


# ---------------------------------------------------------------------------
# Scenario: broken conversion funnel
# ---------------------------------------------------------------------------

class TestBrokenFunnelScenario:
    """High spend / zero conversions — broken funnel."""

    def test_zero_conversion_rule_fires(self):
        assert_fires(broken_funnel_snapshot(), "cpa_zero_conversions")

    def test_negative_roas_rule_fires(self):
        assert_fires(broken_funnel_snapshot(), "cpa_negative_roas")

    def test_findings_cover_both_campaigns(self):
        result = _run(broken_funnel_snapshot())
        entity_ids = {f.entity_id for f in result.findings}
        assert "cmp_no_conv" in entity_ids, "No-conversion campaign should be flagged"
        assert "cmp_neg_roas" in entity_ids, "Negative-ROAS campaign should be flagged"

    def test_health_score_low(self):
        result = _run(broken_funnel_snapshot())
        assert result.health_score < 60, (
            f"Broken-funnel account should score < 60, got {result.health_score}"
        )

    def test_wasted_spend_positive(self):
        result = _run(broken_funnel_snapshot())
        assert result.total_wasted_spend > 0
