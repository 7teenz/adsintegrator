from app.engine.types import AuditRunResult, Category, Finding, ScoreBreakdown, Severity

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


def compute_scores(findings: list[Finding], account_description: str) -> tuple[float, list[ScoreBreakdown]]:
    scores: list[ScoreBreakdown] = []
    composite = 0.0

    for key, (label, weight, categories) in PILLARS.items():
        relevant = [finding for finding in findings if finding.category in categories]
        penalty = sum(SEVERITY_PENALTIES[finding.severity] + finding.score_impact for finding in relevant)
        score = max(0.0, min(100.0, 100.0 - penalty))
        scores.append(
            ScoreBreakdown(
                key=key,
                label=label,
                score=score,
                weight=weight,
                details=f"{len(relevant)} findings affecting {label.lower()}. {account_description}",
            )
        )
        composite += score * weight

    return round(max(0.0, min(100.0, composite)), 1), scores
