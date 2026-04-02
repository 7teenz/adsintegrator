from datetime import date
from types import SimpleNamespace

from app.services.ai_summary import AISummaryService


def _make_finding(index: int, *, severity: str, estimated_waste: float, description: str = "Issue detail"):
    return SimpleNamespace(
        id=f"finding-{index}",
        rule_id=f"rule_{index}",
        severity=severity,
        category="performance",
        title=f"Finding {index}",
        description=description,
        entity_name=f"Campaign {index}",
        metric_value=1.0,
        threshold_value=2.0,
        estimated_waste=estimated_waste,
        estimated_uplift=0.0,
    )


def _make_run(findings, recommendations):
    return SimpleNamespace(
        id="run-1",
        analysis_start=date(2026, 3, 1),
        analysis_end=date(2026, 3, 31),
        recommendations=recommendations,
        findings=findings,
        health_score=62.0,
        total_spend=1000.0,
        total_wasted_spend=220.0,
        total_estimated_uplift=180.0,
        findings_count=len(findings),
    )


def test_build_structured_input_keeps_recommendation_body_for_next_step_hints():
    finding = _make_finding(1, severity="high", estimated_waste=75.0)
    recommendation = SimpleNamespace(
        audit_finding_id=finding.id,
        title="Review this issue",
        body="Inspect the landing page and refresh the creative after checking budget allocation.",
    )
    run = _make_run([finding], [recommendation])

    payload = AISummaryService._build_structured_input(run)
    serialized = payload["findings"][0]

    assert serialized["recommendation_title"] == "Review this issue"
    assert serialized["recommendation_body"] == recommendation.body

    next_step = AISummaryService._next_step_for_finding(serialized)
    assert "landing page" in next_step.lower()


def test_build_structured_input_keeps_all_findings_for_prioritization():
    findings = [
        _make_finding(index, severity="critical", estimated_waste=10.0 + index)
        for index in range(10)
    ]
    findings.append(_make_finding(10, severity="medium", estimated_waste=999.0))
    findings.append(_make_finding(11, severity="low", estimated_waste=50.0))
    run = _make_run(findings, [])

    payload = AISummaryService._build_structured_input(run)

    assert len(payload["findings"]) == 12

    action_plan = AISummaryService._fallback_action_plan(payload)
    assert "Finding 10" in action_plan


def test_fallback_action_plan_keeps_percentage_metrics_in_percentage_points():
    payload = {
        "findings": [
            {
                "severity": "critical",
                "category": "ctr",
                "rule_id": "ctr_low_campaign",
                "title": "Critically low CTR: 1.00%",
                "description": "CTR is too low.",
                "entity_name": "Campaign CTR",
                "metric_value": 1.0,
                "threshold_value": 2.0,
                "estimated_waste": 120.0,
            },
            {
                "severity": "high",
                "category": "performance",
                "rule_id": "weak_cvr",
                "title": "Critically low conversion rate: 0.80%",
                "description": "CVR is too low.",
                "entity_name": "Campaign CVR",
                "metric_value": 0.8,
                "threshold_value": 1.5,
                "estimated_waste": 90.0,
            },
            {
                "severity": "medium",
                "category": "frequency",
                "rule_id": "freq_high",
                "title": "Rising frequency",
                "description": "Frequency is elevated.",
                "entity_name": "Campaign Frequency",
                "metric_value": 3.4,
                "threshold_value": 3.0,
                "estimated_waste": 60.0,
            },
            {
                "severity": "medium",
                "category": "cpa",
                "rule_id": "cpa_high_campaign",
                "title": "CPA above average",
                "description": "CPA is elevated.",
                "entity_name": "Campaign CPA",
                "metric_value": 42.0,
                "threshold_value": 25.0,
                "estimated_waste": 30.0,
            },
        ]
    }

    action_plan = AISummaryService._fallback_action_plan(payload)

    assert "Actual is 1.00% versus the threshold of 2.00%." in action_plan
    assert "Actual is 0.80% versus the threshold of 1.50%." in action_plan
    assert "Actual is 3.40x versus the threshold of 3.00x." in action_plan
    assert "Actual is $42.00 versus the threshold of $25.00." in action_plan
    assert "100.00%" not in action_plan
