from app.engine.types import Category, Finding, ScoreBreakdown, Severity

SEVERITY_PENALTIES = {
    Severity.LOW: 3,
    Severity.MEDIUM: 7,
    Severity.HIGH: 12,
    Severity.CRITICAL: 18,
}

PILLARS = {
    "acquisition": ("Acquisition Efficiency", 0.22, {Category.PERFORMANCE, Category.ACCOUNT, Category.CTR}),
    "conversion": ("Conversion Efficiency", 0.28, {Category.PERFORMANCE, Category.OPPORTUNITY, Category.CPA}),
    "budget": ("Budget Allocation", 0.20, {Category.BUDGET, Category.SPEND, Category.OPPORTUNITY}),
    "trend": ("Trend Stability", 0.15, {Category.TREND, Category.FREQUENCY}),
    "structure": ("Structure & Hygiene", 0.15, {Category.STRUCTURE, Category.PLACEMENT}),
}


ENTITY_SCOPE_MULTIPLIERS = {
    "account": 1.25,
    "campaign": 1.1,
    "ad_set": 1.0,
    "ad": 0.95,
}


def _data_confidence_multiplier(analysis_days: int, total_spend: float) -> float:
    if analysis_days >= 30 and total_spend >= 1000:
        return 1.1
    if analysis_days >= 14 and total_spend >= 300:
        return 1.0
    return 0.85


def _persistence_multiplier(analysis_days: int) -> float:
    if analysis_days >= 30:
        return 1.1
    if analysis_days >= 14:
        return 1.0
    return 0.9


def _weighted_penalty(
    finding: Finding,
    total_spend: float,
    analysis_days: int,
) -> float:
    base_penalty = SEVERITY_PENALTIES[finding.severity] + max(0.0, finding.score_impact * 1.5)
    scope_multiplier = ENTITY_SCOPE_MULTIPLIERS.get(finding.entity_type, 1.0)
    impact_ratio = 0.0
    if total_spend > 0:
        impact_ratio = min(0.6, (finding.estimated_waste + finding.estimated_uplift) / total_spend)
    confidence_multiplier = _data_confidence_multiplier(analysis_days, total_spend)
    persistence_multiplier = _persistence_multiplier(analysis_days)
    metric_signal_multiplier = 1.05 if finding.metric_value is not None else 0.95
    return base_penalty * scope_multiplier * (1.0 + impact_ratio) * confidence_multiplier * persistence_multiplier * metric_signal_multiplier


def compute_scores(
    findings: list[Finding],
    account_description: str,
    *,
    total_spend: float,
    analysis_days: int,
) -> tuple[float, list[ScoreBreakdown]]:
    scores: list[ScoreBreakdown] = []
    composite = 0.0

    for key, (label, weight, categories) in PILLARS.items():
        relevant = [finding for finding in findings if finding.category in categories]
        penalty = sum(_weighted_penalty(finding, total_spend, analysis_days) for finding in relevant)
        score = max(0.0, min(100.0, 100.0 - penalty))
        strongest_issue = relevant[0].title if relevant else "No material issues detected"
        details = (
            f"{len(relevant)} findings affecting {label.lower()}. "
            f"Strongest issue: {strongest_issue}. "
            f"Weighted for severity, spend exposure, scope, and data confidence. "
            f"{account_description}"
        )
        scores.append(
            ScoreBreakdown(
                key=key,
                label=label,
                score=score,
                weight=weight,
                details=details,
            )
        )
        composite += score * weight

    return round(max(0.0, min(100.0, composite)), 1), scores
