"""
Deterministic engine rule tests.

Each test instantiates a rule directly, calls evaluate(snapshot), and
asserts on the returned Finding objects — no database required.

Coverage:
  - Every rule fires on a dataset that crosses its threshold
  - Every rule stays silent on a dataset that does not cross its threshold
  - rule_id, severity, category, metric_value, threshold_value, estimated_waste
    are all validated where the rule sets them
"""
from __future__ import annotations

import pytest

from app.engine.rules.account_rules import WeakAccountCTRRule, WeakConversionFunnelSignalRule
from app.engine.rules.aggregate_rules import (
    AggregateBudgetConcentrationRule,
    AggregateHighCPMWeakCTRRule,
    AggregateWeakAccountCTRRule,
)
from app.engine.rules.budget_rules import (
    BudgetConcentrationRiskRule,
    UnderfundedWinnerRule,
    WinnerLoserReallocationRule,
)
from app.engine.rules.cpa_rules import HighCPARule, NegativeROASRule, ZeroConversionSpendRule
from app.engine.rules.ctr_rules import DecliningCTRRule, LowCTRRule
from app.engine.rules.frequency_rules import FrequencySpikeRule, HighFrequencyRule
from app.engine.rules.opportunity_rules import InefficientAdSetVsSiblingsRule
from app.engine.rules.performance_rules import (
    HighFrequencyLowCTRRule,
    HighSpendLowConversionsRule,
    LowROASHighSpendRule,
    ObjectiveMismatchRule,
    PoorPlacementEfficiencyRule,
    UnevenDailySpendRule,
    WeakCVRRule,
)
from app.engine.rules.spend_rules import HighCPMRule, SpendConcentrationRule, SpendWithoutImpressionsRule
from app.engine.rules.structure_rules import ObjectiveMismatchStructureRule
from app.engine.rules.trend_rules import (
    AdFatigueTrendRule,
    CPADeteriorationRule,
    ROASDropAnomalyRule,
    SpendSpikeAnomalyRule,
)
from app.engine.types import Category, Severity

from tests.engine.fixtures import (
    _BASE_DATE,
    aggregate_only_snapshot,
    broken_funnel_snapshot,
    budget_imbalanced_snapshot,
    fatigued_snapshot,
    healthy_snapshot,
    high_cpa_snapshot,
    low_ctr_snapshot,
    make_account,
    make_adset,
    make_campaign,
    make_daily_points,
    make_declining_ctr_points,
    make_snapshot,
    make_spiking_frequency_points,
    uneven_spend_snapshot,
    weak_cvr_snapshot,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rule_ids(findings) -> list[str]:
    return [f.rule_id for f in findings]


def first(findings):
    assert findings, "Expected at least one finding but got none"
    return findings[0]


# ===========================================================================
# CTR Rules
# ===========================================================================

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
        assert f.threshold_value == pytest.approx(0.5)
        assert f.estimated_waste == pytest.approx(1000.0 * 0.4)

    def test_warning_ctr_fires(self):
        snapshot = low_ctr_snapshot()
        findings = self.rule.evaluate(snapshot)
        warnings = [f for f in findings if f.severity == Severity.MEDIUM]
        assert warnings, "Expected a WARNING CTR finding"
        f = warnings[0]
        assert f.metric_value == pytest.approx(0.8)
        assert f.threshold_value == pytest.approx(1.0)
        assert f.estimated_waste == pytest.approx(1000.0 * 0.2)

    def test_good_ctr_no_finding(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings, "Healthy CTR should not trigger LowCTRRule"

    def test_inactive_campaign_skipped(self):
        campaign = make_campaign(status="PAUSED", ctr=0.1, total_impressions=10_000)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_low_impressions_skipped(self):
        campaign = make_campaign(ctr=0.1, total_impressions=500)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings


class TestDecliningCTRRule:
    rule = DecliningCTRRule()

    def test_declining_ctr_fires(self):
        campaign = make_campaign(
            status="ACTIVE",
            daily_points=make_declining_ctr_points(28, start_ctr=2.5, end_ctr=1.0),
        )
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert findings, "Sharply declining CTR should trigger DecliningCTRRule"
        f = first(findings)
        assert f.rule_id == "ctr_declining"
        assert f.severity == Severity.MEDIUM

    def test_stable_ctr_no_finding(self):
        campaign = make_campaign(daily_points=make_daily_points(28, ctr=2.5))
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_insufficient_daily_points_skipped(self):
        campaign = make_campaign(
            daily_points=make_declining_ctr_points(10, start_ctr=3.0, end_ctr=0.5)
        )
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings, "Fewer than 14 daily points should be skipped"


# ===========================================================================
# CPA Rules
# ===========================================================================

class TestHighCPARule:
    rule = HighCPARule()

    def test_critical_high_cpa_fires(self):
        snapshot = high_cpa_snapshot()
        findings = self.rule.evaluate(snapshot)
        critical = [f for f in findings if f.severity == Severity.CRITICAL]
        assert critical, "CPA 3× account average should trigger CRITICAL finding"
        f = critical[0]
        assert f.rule_id == "cpa_high_campaign"
        assert f.category == Category.CPA
        assert f.entity_id == "cmp_high_cpa"
        assert f.metric_value == pytest.approx(100.0)

    def test_warning_cpa_fires(self):
        # cmp_a: spend=1000, conv=50 → contributes to avg
        # cmp_b: spend=400, conv=10, cpa=40 → account_avg = 1400/60 ≈ 23.3
        # 40 > 23.3*1.5 = 34.9 → WARNING
        account = make_account(total_spend=1400.0, cpa=23.3)
        campaigns = [
            make_campaign(campaign_id="cmp_a", cpa=20.0, total_conversions=50, total_spend=1000.0),
            make_campaign(campaign_id="cmp_b", cpa=40.0, total_conversions=10, total_spend=400.0),
        ]
        snapshot = make_snapshot(account=account, campaigns=campaigns)
        findings = self.rule.evaluate(snapshot)
        warning = [f for f in findings if f.severity == Severity.MEDIUM]
        assert warning, "CPA 1.75× average should trigger WARNING"

    def test_normal_cpa_no_finding(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_below_conversion_threshold_skipped(self):
        account = make_account(cpa=20.0)
        campaign = make_campaign(cpa=100.0, total_conversions=2)  # fewer than 3
        snapshot = make_snapshot(account=account, campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings, "Campaign with <3 conversions should be skipped"


class TestZeroConversionSpendRule:
    rule = ZeroConversionSpendRule()

    def test_fires_on_zero_conversions(self):
        snapshot = broken_funnel_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "cpa_zero_conversions"
        assert f.severity == Severity.CRITICAL
        assert f.entity_id == "cmp_no_conv"
        assert f.estimated_waste == pytest.approx(1200.0)

    def test_no_finding_when_conversions_exist(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_below_spend_threshold_skipped(self):
        campaign = make_campaign(total_spend=30.0, total_conversions=0)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings


class TestNegativeROASRule:
    rule = NegativeROASRule()

    def test_fires_on_negative_roas(self):
        snapshot = broken_funnel_snapshot()
        findings = self.rule.evaluate(snapshot)
        negative = [f for f in findings if f.entity_id == "cmp_neg_roas"]
        assert negative, "Campaign with ROAS < 1.0 and conversion value should fire NegativeROASRule"
        f = negative[0]
        assert f.rule_id == "cpa_negative_roas"
        assert f.severity == Severity.CRITICAL
        assert f.estimated_waste == pytest.approx(max(800.0 - 600.0, 0))

    def test_positive_roas_no_finding(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_zero_conversion_value_skipped(self):
        campaign = make_campaign(
            total_spend=500.0, total_conversion_value=0.0, roas=0.0, total_conversions=0,
        )
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings, "Zero conversion value should be skipped (no evidence of lost revenue)"


# ===========================================================================
# Frequency Rules
# ===========================================================================

class TestHighFrequencyRule:
    rule = HighFrequencyRule()

    def test_critical_frequency_fires(self):
        campaign = make_campaign(frequency=6.0, total_impressions=5000)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        critical = [f for f in findings if f.severity == Severity.CRITICAL]
        assert critical
        f = critical[0]
        assert f.rule_id == "freq_high"
        assert f.estimated_waste == pytest.approx(campaign.total_spend * 0.3)

    def test_warning_frequency_fires(self):
        campaign = make_campaign(frequency=3.5, total_impressions=5000)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        warnings = [f for f in findings if f.severity == Severity.MEDIUM]
        assert warnings
        assert warnings[0].estimated_waste == pytest.approx(campaign.total_spend * 0.15)

    def test_healthy_frequency_no_finding(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_low_impressions_skipped(self):
        campaign = make_campaign(frequency=7.0, total_impressions=500)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings


class TestFrequencySpikeRule:
    rule = FrequencySpikeRule()

    def test_spiking_frequency_fires(self):
        campaign = make_campaign(
            status="ACTIVE",
            daily_points=make_spiking_frequency_points(20),
        )
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert findings, "Frequency spike (1.5 → 3.5) should trigger FrequencySpikeRule"
        f = first(findings)
        assert f.rule_id == "freq_spike"

    def test_stable_frequency_no_finding(self):
        campaign = make_campaign(daily_points=make_daily_points(20, frequency=2.0))
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_insufficient_daily_points_skipped(self):
        campaign = make_campaign(
            daily_points=make_spiking_frequency_points(8)
        )
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings, "Fewer than 10 daily points should be skipped"


# ===========================================================================
# Budget / Opportunity Rules
# ===========================================================================

class TestBudgetConcentrationRiskRule:
    rule = BudgetConcentrationRiskRule()

    def test_dominant_low_roas_fires(self):
        snapshot = budget_imbalanced_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "budget_concentration_risk"
        assert f.severity == Severity.HIGH
        assert f.entity_id == "cmp_dominant"

    def test_diversified_spend_no_finding(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_dominant_campaign_high_roas_no_finding(self):
        account = make_account(total_spend=2000.0, roas=3.0)
        campaigns = [
            make_campaign(campaign_id="cmp_a", total_spend=1400.0, roas=4.5, spend_share=0.7),
            make_campaign(campaign_id="cmp_b", total_spend=600.0, roas=2.5, spend_share=0.3),
        ]
        snapshot = make_snapshot(account=account, campaigns=campaigns)
        findings = self.rule.evaluate(snapshot)
        # Dominant campaign has ROAS well above account average — should not fire
        assert not findings


class TestUnderfundedWinnerRule:
    rule = UnderfundedWinnerRule()

    def test_underfunded_winner_fires(self):
        snapshot = budget_imbalanced_snapshot()
        findings = self.rule.evaluate(snapshot)
        winner_findings = [f for f in findings if f.entity_id == "cmp_winner"]
        assert winner_findings, "Underfunded high-ROAS campaign should trigger UnderfundedWinnerRule"
        assert winner_findings[0].rule_id == "underfunded_winner"

    def test_well_funded_winner_no_finding(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings


class TestWinnerLoserReallocationRule:
    rule = WinnerLoserReallocationRule()

    def test_winner_loser_pair_fires(self):
        snapshot = budget_imbalanced_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "winner_loser_reallocation"
        assert f.severity == Severity.HIGH

    def test_no_clear_winner_no_finding(self):
        account = make_account(total_spend=2000.0, roas=2.5)
        campaigns = [
            make_campaign(campaign_id="cmp_a", roas=2.0, total_spend=1000.0),
            make_campaign(campaign_id="cmp_b", roas=2.2, total_spend=1000.0),
        ]
        snapshot = make_snapshot(account=account, campaigns=campaigns)
        findings = self.rule.evaluate(snapshot)
        assert not findings


# ===========================================================================
# Spend Rules
# ===========================================================================

class TestSpendConcentrationRule:
    rule = SpendConcentrationRule()

    def test_concentrated_spend_fires(self):
        account = make_account(total_spend=2000.0)
        campaigns = [
            make_campaign(campaign_id="cmp_a", total_spend=1400.0, spend_share=0.7),
            make_campaign(campaign_id="cmp_b", total_spend=600.0, spend_share=0.3),
        ]
        snapshot = make_snapshot(account=account, campaigns=campaigns)
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "spend_concentration"
        assert f.metric_value == pytest.approx(70.0)

    def test_balanced_spend_no_finding(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_single_campaign_skipped(self):
        campaign = make_campaign(total_spend=1000.0, spend_share=1.0)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings, "Single campaign should not trigger concentration rule"


class TestSpendWithoutImpressionsRule:
    rule = SpendWithoutImpressionsRule()

    def test_fires_on_spend_no_impressions(self):
        campaign = make_campaign(total_spend=150.0, total_impressions=50)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "spend_no_impressions"
        assert f.severity == Severity.CRITICAL
        assert f.estimated_waste == pytest.approx(150.0)

    def test_normal_impressions_no_finding(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_low_spend_skipped(self):
        campaign = make_campaign(total_spend=10.0, total_impressions=10)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings


class TestHighCPMRule:
    rule = HighCPMRule()

    def test_high_cpm_outlier_fires(self):
        account = make_account(total_spend=5000.0)
        campaigns = [
            make_campaign(f"cmp_{i}", total_spend=800.0, cpm=20.0, total_impressions=5000)
            for i in range(4)
        ]
        # One campaign with CPM 3× median
        campaigns.append(
            make_campaign("cmp_outlier", total_spend=800.0, cpm=65.0, ctr=0.8, total_impressions=5000)
        )
        snapshot = make_snapshot(account=account, campaigns=campaigns)
        findings = self.rule.evaluate(snapshot)
        high_cpm = [f for f in findings if f.entity_id == "cmp_outlier"]
        assert high_cpm, "CPM outlier should trigger HighCPMRule"

    def test_uniform_cpm_no_finding(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings


# ===========================================================================
# Performance Rules
# ===========================================================================

class TestHighFrequencyLowCTRRule:
    rule = HighFrequencyLowCTRRule()

    def test_fires_on_high_freq_low_ctr(self):
        account = make_account(total_spend=2000.0)
        campaign = make_campaign(
            status="ACTIVE", total_spend=500.0,
            frequency=4.0, ctr=0.8,
        )
        snapshot = make_snapshot(account=account, campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "high_frequency_low_ctr"
        assert f.severity == Severity.HIGH

    def test_high_freq_high_ctr_no_finding(self):
        campaign = make_campaign(frequency=4.0, ctr=2.5)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_low_freq_low_ctr_no_finding(self):
        campaign = make_campaign(frequency=2.0, ctr=0.5, total_spend=500.0)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings


class TestHighSpendLowConversionsRule:
    rule = HighSpendLowConversionsRule()

    def test_fires_on_high_spend_zero_conversions(self):
        campaign = make_campaign(total_spend=500.0, total_conversions=0)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "high_spend_low_conversions"
        assert f.severity == Severity.CRITICAL
        assert f.estimated_waste == pytest.approx(500.0 * 0.45)

    def test_adequate_conversions_no_finding(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_below_spend_threshold_skipped(self):
        campaign = make_campaign(total_spend=200.0, total_conversions=0)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings


class TestLowROASHighSpendRule:
    rule = LowROASHighSpendRule()

    def test_fires_on_low_roas_high_spend(self):
        campaign = make_campaign(total_spend=800.0, roas=0.9)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "low_roas_high_spend"
        assert f.severity == Severity.CRITICAL
        assert f.estimated_waste == pytest.approx(800.0 * 0.3)

    def test_good_roas_no_finding(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_below_spend_threshold_skipped(self):
        campaign = make_campaign(total_spend=300.0, roas=0.5)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings


class TestObjectiveMismatchRule:
    rule = ObjectiveMismatchRule()

    def test_fires_on_awareness_objective_with_conversions(self):
        account = make_account()
        campaign = make_campaign(
            total_spend=300.0, objective="REACH",
            total_conversions=10, click_to_conversion_rate=1.5,
        )
        snapshot = make_snapshot(account=account, campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "objective_mismatch"

    def test_conversions_objective_no_finding(self):
        campaign = make_campaign(objective="CONVERSIONS", total_spend=300.0, total_conversions=50)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_high_click_to_conversion_no_finding(self):
        campaign = make_campaign(
            objective="TRAFFIC", total_spend=300.0,
            total_conversions=20, click_to_conversion_rate=5.0,
        )
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings


class TestPoorPlacementEfficiencyRule:
    rule = PoorPlacementEfficiencyRule()

    def test_fires_on_high_cpm_low_ctr_adset(self):
        account = make_account(cpm=20.0, ctr=3.0)
        ad_set = make_adset(total_spend=300.0, cpm=35.0, ctr=2.0, total_impressions=10_000)
        snapshot = make_snapshot(account=account, ad_sets=[ad_set])
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "poor_placement_efficiency"

    def test_normal_placement_no_finding(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings


# ===========================================================================
# Trend Rules
# ===========================================================================

class TestAdFatigueTrendRule:
    rule = AdFatigueTrendRule()

    def test_fires_on_fatigued_campaign(self):
        snapshot = fatigued_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "ad_fatigue_trend"
        assert f.severity == Severity.HIGH

    def test_no_finding_on_healthy(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_no_finding_below_spend_threshold(self):
        campaign = make_campaign(total_spend=100.0, wow_ctr_delta=-0.3, frequency=3.0)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings


class TestSpendSpikeAnomalyRule:
    rule = SpendSpikeAnomalyRule()

    def test_fires_on_spend_spike_with_roas_drop(self):
        campaign = make_campaign(
            total_spend=500.0, wow_spend_delta=0.7, wow_roas_delta=-0.1,
        )
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "spend_spike_anomaly"

    def test_spend_spike_with_roas_improvement_no_finding(self):
        campaign = make_campaign(total_spend=500.0, wow_spend_delta=0.7, wow_roas_delta=0.1)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings


class TestROASDropAnomalyRule:
    rule = ROASDropAnomalyRule()

    def test_fires_on_roas_drop(self):
        campaign = make_campaign(total_spend=500.0, wow_roas_delta=-0.35)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "roas_drop_anomaly"
        assert f.severity == Severity.HIGH

    def test_slight_roas_drop_no_finding(self):
        campaign = make_campaign(total_spend=500.0, wow_roas_delta=-0.1)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings


class TestCPADeteriorationRule:
    rule = CPADeteriorationRule()

    def test_fires_on_cpa_deterioration(self):
        campaign = make_campaign(total_conversions=10, wow_cpa_delta=0.35)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "cpa_deterioration"
        assert f.severity == Severity.HIGH

    def test_improving_cpa_no_finding(self):
        campaign = make_campaign(total_conversions=10, wow_cpa_delta=-0.1)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_below_conversion_threshold_skipped(self):
        campaign = make_campaign(total_conversions=3, wow_cpa_delta=0.5)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings


# ===========================================================================
# Structure Rules
# ===========================================================================

class TestObjectiveMismatchStructureRule:
    rule = ObjectiveMismatchStructureRule()

    def test_fires_on_too_many_adsets(self):
        campaign = make_campaign(ad_set_count=15, total_spend=300.0)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "structure_guardrail"

    def test_normal_adset_count_no_finding(self):
        campaign = make_campaign(ad_set_count=5)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings


# ===========================================================================
# Opportunity Rules
# ===========================================================================

class TestInefficientAdSetVsSiblingsRule:
    rule = InefficientAdSetVsSiblingsRule()

    def test_fires_on_poor_adset_vs_siblings(self):
        account = make_account()
        adsets = [
            make_adset(
                ad_set_id="adset_good", campaign_id="cmp_1",
                total_spend=400.0, roas=3.5, cpa=15.0,
            ),
            make_adset(
                ad_set_id="adset_poor", campaign_id="cmp_1",
                total_spend=200.0, roas=1.2, cpa=50.0,
            ),
        ]
        snapshot = make_snapshot(account=account, ad_sets=adsets)
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "inefficient_adset_vs_siblings"
        assert f.entity_id == "adset_poor"

    def test_comparable_adsets_no_finding(self):
        adsets = [
            make_adset(ad_set_id="a1", campaign_id="cmp_1", roas=3.0, cpa=20.0, total_spend=400.0),
            make_adset(ad_set_id="a2", campaign_id="cmp_1", roas=2.8, cpa=22.0, total_spend=400.0),
        ]
        snapshot = make_snapshot(ad_sets=adsets)
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_single_adset_per_campaign_skipped(self):
        adset = make_adset(ad_set_id="only", campaign_id="cmp_1", roas=0.1, cpa=999.0)
        snapshot = make_snapshot(ad_sets=[adset])
        findings = self.rule.evaluate(snapshot)
        assert not findings, "Single ad set per campaign should be skipped"


# ===========================================================================
# Account-level Rules
# ===========================================================================

class TestWeakAccountCTRRule:
    rule = WeakAccountCTRRule()

    def test_fires_on_low_account_ctr(self):
        account = make_account(total_spend=500.0, ctr=0.7)
        snapshot = make_snapshot(account=account)
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "weak_account_ctr"
        assert f.severity == Severity.HIGH
        assert f.estimated_waste == pytest.approx(500.0 * 0.12)
        assert f.estimated_uplift == pytest.approx(500.0 * 0.05)

    def test_good_account_ctr_no_finding(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_below_spend_threshold_skipped(self):
        account = make_account(total_spend=100.0, ctr=0.5)
        snapshot = make_snapshot(account=account)
        findings = self.rule.evaluate(snapshot)
        assert not findings


class TestWeakConversionFunnelSignalRule:
    rule = WeakConversionFunnelSignalRule()

    def test_fires_on_low_click_to_conversion(self):
        account = make_account(total_clicks=300, click_to_conversion_rate=1.0)
        snapshot = make_snapshot(account=account)
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "weak_conversion_funnel_signal"

    def test_good_conversion_rate_no_finding(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_low_clicks_skipped(self):
        account = make_account(total_clicks=100, click_to_conversion_rate=0.5)
        snapshot = make_snapshot(account=account)
        findings = self.rule.evaluate(snapshot)
        assert not findings


# ===========================================================================
# Aggregate Rules (data_mode = "period_aggregate")
# ===========================================================================

class TestAggregateWeakAccountCTRRule:
    rule = AggregateWeakAccountCTRRule()

    def test_fires_on_aggregate_low_ctr(self):
        snapshot = aggregate_only_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert findings
        f = first(findings)
        assert f.rule_id == "aggregate_weak_account_ctr"
        assert f.severity == Severity.MEDIUM

    def test_daily_mode_skipped(self):
        account = make_account(total_spend=500.0, ctr=0.3)
        snapshot = make_snapshot(account=account, data_mode="daily_breakdown")
        findings = self.rule.evaluate(snapshot)
        assert not findings, "Aggregate rule must not fire in daily_breakdown mode"

    def test_good_ctr_no_finding(self):
        account = make_account(total_spend=500.0, ctr=3.0)
        snapshot = make_snapshot(account=account, data_mode="period_aggregate")
        findings = self.rule.evaluate(snapshot)
        assert not findings


class TestAggregateBudgetConcentrationRule:
    rule = AggregateBudgetConcentrationRule()

    def test_fires_on_concentrated_aggregate_spend(self):
        snapshot = aggregate_only_snapshot()
        findings = self.rule.evaluate(snapshot)
        # aggregate_only_snapshot has 4 campaigns, first one gets 25% each — uniform, so no fire.
        # Build a new one with actual concentration.
        account = make_account(total_spend=3000.0)
        campaigns = [
            make_campaign(f"cmp_{i}", total_spend=500.0, spend_share=500 / 3000)
            for i in range(3)
        ]
        campaigns.append(
            make_campaign("cmp_dominant", total_spend=1500.0, spend_share=0.5)
        )
        snapshot2 = make_snapshot(account=account, campaigns=campaigns, data_mode="period_aggregate")
        findings2 = self.rule.evaluate(snapshot2)
        assert findings2
        f = first(findings2)
        assert f.rule_id == "aggregate_budget_concentration"

    def test_daily_mode_skipped(self):
        snapshot = make_snapshot(data_mode="daily_breakdown")
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_fewer_than_three_campaigns_skipped(self):
        account = make_account(total_spend=2000.0)
        campaigns = [
            make_campaign("cmp_a", total_spend=1500.0, spend_share=0.75),
            make_campaign("cmp_b", total_spend=500.0, spend_share=0.25),
        ]
        snapshot = make_snapshot(account=account, campaigns=campaigns, data_mode="period_aggregate")
        findings = self.rule.evaluate(snapshot)
        assert not findings


class TestAggregateHighCPMWeakCTRRule:
    rule = AggregateHighCPMWeakCTRRule()

    def test_fires_on_high_cpm_weak_ctr_campaign(self):
        account = make_account(cpm=20.0, ctr=3.0)
        campaigns = [
            make_campaign("cmp_normal", total_spend=500.0, cpm=20.0, ctr=3.0, spend_share=0.5),
            make_campaign("cmp_bad", total_spend=500.0, cpm=22.0, ctr=2.8, spend_share=0.5),
        ]
        snapshot = make_snapshot(account=account, campaigns=campaigns, data_mode="period_aggregate")
        findings = self.rule.evaluate(snapshot)
        assert findings
        bad_findings = [f for f in findings if f.entity_id == "cmp_bad"]
        assert bad_findings

    def test_daily_mode_skipped(self):
        snapshot = make_snapshot(data_mode="daily_breakdown")
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_better_than_account_no_finding(self):
        account = make_account(cpm=25.0, ctr=2.0)
        campaign = make_campaign(cpm=20.0, ctr=3.0, total_spend=500.0)
        snapshot = make_snapshot(account=account, campaigns=[campaign], data_mode="period_aggregate")
        findings = self.rule.evaluate(snapshot)
        assert not findings


# ===========================================================================
# Cross-scenario: healthy account produces no findings
# ===========================================================================

# ===========================================================================
# WeakCVRRule
# ===========================================================================

class TestWeakCVRRule:
    rule = WeakCVRRule()

    def test_critical_cvr_fires(self):
        snapshot = weak_cvr_snapshot()
        findings = self.rule.evaluate(snapshot)
        critical = [f for f in findings if f.severity == Severity.CRITICAL]
        assert critical, "Expected a CRITICAL CVR finding for zero-conversion campaign"
        f = critical[0]
        assert f.rule_id == "weak_cvr"
        assert f.entity_id == "cmp_zero_cvr"
        assert f.metric_value == pytest.approx(0.0, abs=0.01)
        assert f.threshold_value == pytest.approx(0.5, abs=0.01)
        assert f.estimated_waste > 0

    def test_warning_cvr_fires(self):
        snapshot = weak_cvr_snapshot()
        findings = self.rule.evaluate(snapshot)
        warnings = [f for f in findings if f.severity == Severity.MEDIUM]
        assert warnings, "Expected a WARNING CVR finding for low-CVR campaign"
        f = warnings[0]
        assert f.entity_id == "cmp_low_cvr"
        assert f.metric_value == pytest.approx(1.2, abs=0.1)

    def test_healthy_cvr_no_finding(self):
        snapshot = healthy_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert not findings, "Healthy CVR should not trigger WeakCVRRule"

    def test_low_click_count_skipped(self):
        """Campaigns with < 200 clicks should be skipped — not enough signal."""
        campaign = make_campaign(total_clicks=100, total_conversions=0, total_spend=500.0)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_inactive_campaign_skipped(self):
        campaign = make_campaign(status="PAUSED", total_clicks=500, total_conversions=0)
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings


# ===========================================================================
# UnevenDailySpendRule
# ===========================================================================

class TestUnevenDailySpendRule:
    rule = UnevenDailySpendRule()

    def test_erratic_spend_fires(self):
        snapshot = uneven_spend_snapshot()
        findings = self.rule.evaluate(snapshot)
        assert findings, "Highly erratic pacing should trigger UnevenDailySpendRule"
        f = findings[0]
        assert f.rule_id == "uneven_daily_spend"
        assert f.metric_value > 0.6  # CV is well above warning threshold
        assert f.estimated_waste > 0

    def test_even_spend_no_finding(self):
        """Perfectly even daily spend should not trigger the rule."""
        campaign = make_campaign(
            total_spend=1400.0,
            daily_points=make_daily_points(28, spend_per_day=50.0),
        )
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings, "Even daily spend should not fire UnevenDailySpendRule"

    def test_too_few_days_skipped(self):
        campaign = make_campaign(
            total_spend=500.0,
            daily_points=make_daily_points(7),  # < 14 days required
        )
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings

    def test_low_spend_skipped(self):
        campaign = make_campaign(total_spend=100.0, daily_points=make_daily_points(28))
        snapshot = make_snapshot(campaigns=[campaign])
        findings = self.rule.evaluate(snapshot)
        assert not findings


# ===========================================================================
# Cross-scenario: healthy account produces no findings
# ===========================================================================

ALL_DAILY_RULES = [
    LowCTRRule(),
    DecliningCTRRule(),
    HighCPARule(),
    ZeroConversionSpendRule(),
    NegativeROASRule(),
    HighFrequencyRule(),
    FrequencySpikeRule(),
    BudgetConcentrationRiskRule(),
    UnderfundedWinnerRule(),
    WinnerLoserReallocationRule(),
    SpendConcentrationRule(),
    SpendWithoutImpressionsRule(),
    HighCPMRule(),
    AdFatigueTrendRule(),
    SpendSpikeAnomalyRule(),
    ROASDropAnomalyRule(),
    CPADeteriorationRule(),
    ObjectiveMismatchStructureRule(),
    InefficientAdSetVsSiblingsRule(),
    WeakAccountCTRRule(),
    WeakConversionFunnelSignalRule(),
    HighFrequencyLowCTRRule(),
    HighSpendLowConversionsRule(),
    LowROASHighSpendRule(),
    ObjectiveMismatchRule(),
    PoorPlacementEfficiencyRule(),
    WeakCVRRule(),
    UnevenDailySpendRule(),
]


@pytest.mark.parametrize("rule", ALL_DAILY_RULES, ids=lambda r: r.rule_id)
def test_healthy_snapshot_no_findings(rule):
    """A well-performing account should not trigger any daily-mode rule."""
    snapshot = healthy_snapshot()
    findings = rule.evaluate(snapshot)
    assert not findings, (
        f"{rule.rule_id} fired on a healthy account — check thresholds or fixture values"
    )
