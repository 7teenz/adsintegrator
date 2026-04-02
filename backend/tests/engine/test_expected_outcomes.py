"""
Contract-based scenario tests for the deterministic audit engine.

Each test loads a named scenario snapshot, runs all registered rules and
scoring, then verifies it against the explicit expected-outcome contract
defined in datasets/expected_outcomes.py.

Adding a new scenario:
  1. Add a snapshot builder to fixtures.py
  2. Add a ScenarioContract entry to datasets/expected_outcomes.py
  3. Add a test class here that calls _assert_contract(snapshot, "name")
"""
from __future__ import annotations

import app.engine.rules as _rules_module  # noqa: F401 — ensures @register_rule decorators fire
from app.engine.rules.base import get_all_rules
from app.engine.scoring import compute_scores
from app.engine.types import AccountAuditSnapshot

from tests.engine.datasets.expected_outcomes import CONTRACTS, ScenarioContract
from tests.engine.fixtures import (
    aggregate_only_snapshot,
    broken_funnel_snapshot,
    budget_imbalanced_snapshot,
    fatigued_snapshot,
    healthy_snapshot,
    high_cpa_snapshot,
    low_ctr_snapshot,
    weak_cvr_snapshot,
)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _run(snapshot: AccountAuditSnapshot):
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

    class Result:
        pass

    r = Result()
    r.findings = findings
    r.health_score = health_score
    r.fired_rule_ids = {f.rule_id for f in findings}
    return r


def _assert_contract(snapshot: AccountAuditSnapshot, contract_name: str) -> None:
    contract: ScenarioContract = CONTRACTS[contract_name]
    result = _run(snapshot)
    fired = result.fired_rule_ids

    for rule_id in contract.must_fire:
        assert rule_id in fired, (
            f"[{contract_name}] Rule '{rule_id}' must fire but did not.\n"
            f"Contract: {contract.description}\n"
            f"Fired: {sorted(fired)}"
        )

    for rule_id in contract.must_not_fire:
        assert rule_id not in fired, (
            f"[{contract_name}] Rule '{rule_id}' must NOT fire but did.\n"
            f"Contract: {contract.description}\n"
            f"Fired: {sorted(fired)}"
        )

    assert result.health_score >= contract.min_health_score, (
        f"[{contract_name}] Health score {result.health_score:.1f} < min {contract.min_health_score}\n"
        f"Contract: {contract.description}"
    )

    assert result.health_score <= contract.max_health_score, (
        f"[{contract_name}] Health score {result.health_score:.1f} > max {contract.max_health_score}\n"
        f"Contract: {contract.description}"
    )

    if contract.min_findings is not None:
        assert len(result.findings) >= contract.min_findings, (
            f"[{contract_name}] Expected ≥{contract.min_findings} findings, got {len(result.findings)}\n"
            f"Contract: {contract.description}"
        )

    if contract.max_findings is not None:
        assert len(result.findings) <= contract.max_findings, (
            f"[{contract_name}] Expected ≤{contract.max_findings} findings, got {len(result.findings)}\n"
            f"Fired: {sorted(f.rule_id for f in result.findings)}\n"
            f"Contract: {contract.description}"
        )


# ---------------------------------------------------------------------------
# Scenario: healthy baseline
# ---------------------------------------------------------------------------

class TestHealthyContract:
    def test_healthy_meets_contract(self):
        _assert_contract(healthy_snapshot(), "healthy")

    def test_healthy_no_critical_findings(self):
        result = _run(healthy_snapshot())
        critical = [f for f in result.findings if f.severity.value == "critical"]
        assert not critical, (
            f"Healthy scenario should produce no critical findings.\n"
            f"Got: {[(f.rule_id, f.entity_name) for f in critical]}"
        )


# ---------------------------------------------------------------------------
# Scenario: weak CTR
# ---------------------------------------------------------------------------

class TestWeakCTRContract:
    def test_weak_ctr_meets_contract(self):
        _assert_contract(low_ctr_snapshot(), "low_ctr")

    def test_ctr_finding_has_correct_metric(self):
        result = _run(low_ctr_snapshot())
        critical = next(
            (f for f in result.findings
             if f.rule_id == "ctr_low_campaign" and f.severity.value == "critical"),
            None,
        )
        assert critical is not None, "Expected a CRITICAL CTR finding"
        assert abs(critical.metric_value - 0.3) < 0.05, (
            f"Critical CTR metric should be ~0.3%, got {critical.metric_value}"
        )

    def test_ctr_findings_have_positive_waste(self):
        result = _run(low_ctr_snapshot())
        for f in result.findings:
            if f.rule_id == "ctr_low_campaign":
                assert f.estimated_waste > 0, (
                    f"CTR finding for '{f.entity_name}' should have positive estimated_waste"
                )

    def test_weak_ctr_scores_lower_than_healthy(self):
        healthy = _run(healthy_snapshot()).health_score
        weak = _run(low_ctr_snapshot()).health_score
        assert weak < healthy, (
            f"Weak-CTR score ({weak:.1f}) should be lower than healthy score ({healthy:.1f})"
        )


# ---------------------------------------------------------------------------
# Scenario: high CPA
# ---------------------------------------------------------------------------

class TestHighCPAContract:
    def test_high_cpa_meets_contract(self):
        _assert_contract(high_cpa_snapshot(), "high_cpa")

    def test_high_cpa_targets_offending_campaign(self):
        result = _run(high_cpa_snapshot())
        cpa_findings = [f for f in result.findings if f.rule_id == "cpa_high_campaign"]
        assert any(f.entity_id == "cmp_high_cpa" for f in cpa_findings), (
            "High-CPA rule must flag 'cmp_high_cpa'; "
            f"flagged entities: {[f.entity_id for f in cpa_findings]}"
        )

    def test_normal_campaign_not_flagged_for_cpa(self):
        result = _run(high_cpa_snapshot())
        cpa_findings = [f for f in result.findings if f.rule_id == "cpa_high_campaign"]
        assert all(f.entity_id != "cmp_normal" for f in cpa_findings), (
            "Normal-CPA campaign 'cmp_normal' must not be flagged by high-CPA rule"
        )

    def test_high_cpa_finding_has_positive_waste(self):
        result = _run(high_cpa_snapshot())
        for f in result.findings:
            if f.rule_id == "cpa_high_campaign":
                assert f.estimated_waste > 0


# ---------------------------------------------------------------------------
# Scenario: fatigued account
# ---------------------------------------------------------------------------

class TestFatiguedContract:
    def test_fatigued_meets_contract(self):
        _assert_contract(fatigued_snapshot(), "fatigued")

    def test_at_least_one_fatigue_rule_fires(self):
        result = _run(fatigued_snapshot())
        fatigue_ids = {"ad_fatigue_trend", "high_frequency", "ctr_declining", "high_frequency_low_ctr"}
        assert fatigue_ids & result.fired_rule_ids, (
            f"Expected a fatigue rule to fire; fired: {sorted(result.fired_rule_ids)}"
        )


# ---------------------------------------------------------------------------
# Scenario: budget imbalanced
# ---------------------------------------------------------------------------

class TestBudgetImbalancedContract:
    def test_budget_imbalanced_meets_contract(self):
        _assert_contract(budget_imbalanced_snapshot(), "budget_imbalanced")

    def test_underfunded_winner_targets_correct_entity(self):
        result = _run(budget_imbalanced_snapshot())
        finding = next(
            (f for f in result.findings if f.rule_id == "underfunded_winner"), None
        )
        if finding:
            assert finding.entity_id == "cmp_winner"


# ---------------------------------------------------------------------------
# Scenario: aggregate-only export
# ---------------------------------------------------------------------------

class TestAggregateOnlyContract:
    def test_aggregate_only_meets_contract(self):
        _assert_contract(aggregate_only_snapshot(), "aggregate_only")


# ---------------------------------------------------------------------------
# Scenario: broken conversion funnel
# ---------------------------------------------------------------------------

class TestBrokenFunnelContract:
    def test_broken_funnel_meets_contract(self):
        _assert_contract(broken_funnel_snapshot(), "broken_funnel")

    def test_findings_cover_both_campaigns(self):
        result = _run(broken_funnel_snapshot())
        entity_ids = {f.entity_id for f in result.findings}
        assert "cmp_no_conv" in entity_ids
        assert "cmp_neg_roas" in entity_ids


# ---------------------------------------------------------------------------
# Scenario: weak CVR
# ---------------------------------------------------------------------------

class TestWeakCVRContract:
    def test_weak_cvr_meets_contract(self):
        _assert_contract(weak_cvr_snapshot(), "weak_cvr")
