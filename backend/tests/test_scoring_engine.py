from app.engine.scoring import compute_scores
from app.engine.types import Category, Finding, Severity


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
    score_a, pillars_a = compute_scores(findings, "Account summary")
    score_b, pillars_b = compute_scores(findings, "Account summary")

    assert score_a == score_b
    assert 0.0 <= score_a <= 100.0
    assert len(pillars_a) == 5
    assert [item.score for item in pillars_a] == [item.score for item in pillars_b]
