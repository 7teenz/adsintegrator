from app.engine.orchestrator import _dedupe_hierarchical_findings
from app.engine.scoring import compute_scores
from app.engine.types import Category, Finding, Severity
from tests.engine.fixtures import make_adset, make_campaign, make_snapshot


def _finding(severity: Severity, category: Category, score_impact: float = 0.0) -> Finding:
    return Finding(
        rule_id="rule",
        severity=severity,
        category=category,
        title="title",
        description="description",
        entity_type="campaign",
        entity_id="cmp_1",
        entity_name="Campaign",
        estimated_waste=10.0,
        estimated_uplift=8.0,
        score_impact=score_impact,
    )


def test_compute_scores_is_deterministic_and_bounded():
    findings = [
        _finding(Severity.CRITICAL, Category.PERFORMANCE, 5.0),
        _finding(Severity.HIGH, Category.BUDGET, 2.0),
        _finding(Severity.MEDIUM, Category.TREND, 0.0),
    ]
    score_a, pillars_a = compute_scores(findings, "Account summary", total_spend=5000.0, analysis_days=30)
    score_b, pillars_b = compute_scores(findings, "Account summary", total_spend=5000.0, analysis_days=30)

    assert score_a == score_b
    assert 0.0 <= score_a <= 100.0
    assert len(pillars_a) == 5
    assert [item.score for item in pillars_a] == [item.score for item in pillars_b]


def test_hierarchical_dedupe_keeps_campaign_finding_and_restores_baseline_score():
    snapshot = make_snapshot(
        campaigns=[make_campaign(campaign_id="cmp_1", campaign_name="Campaign 1")],
        ad_sets=[make_adset(ad_set_id="adset_1", campaign_id="cmp_1", campaign_name="Campaign 1")],
    )
    campaign_finding = Finding(
        rule_id="ctr_low_campaign",
        severity=Severity.CRITICAL,
        category=Category.CTR,
        title="Critically low CTR: 0.30%",
        description="Campaign CTR is critically low.",
        entity_type="campaign",
        entity_id="cmp_1",
        entity_name="Campaign 1",
        metric_value=0.3,
        threshold_value=0.5,
        estimated_waste=400.0,
    )
    ad_set_finding = Finding(
        rule_id="ctr_low_adset",
        severity=Severity.CRITICAL,
        category=Category.CTR,
        title="Ad set CTR critically low: 0.30%",
        description="Ad set CTR is critically low.",
        entity_type="ad_set",
        entity_id="adset_1",
        entity_name="Ad Set 1",
        metric_value=0.3,
        threshold_value=0.5,
        estimated_waste=160.0,
    )

    deduped = _dedupe_hierarchical_findings([campaign_finding, ad_set_finding], snapshot)

    assert deduped == [campaign_finding]
    assert sum(finding.estimated_waste for finding in deduped) == 400.0

    baseline_score, _ = compute_scores([campaign_finding], "Account summary", total_spend=1000.0, analysis_days=30)
    deduped_score, _ = compute_scores(deduped, "Account summary", total_spend=1000.0, analysis_days=30)
    duplicated_score, _ = compute_scores(
        [campaign_finding, ad_set_finding],
        "Account summary",
        total_spend=1000.0,
        analysis_days=30,
    )

    assert deduped_score == baseline_score
    assert deduped_score > duplicated_score
