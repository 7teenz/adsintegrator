from app.engine.types import Category, Finding


def _format_metric(value: float | None, category: Category) -> str | None:
    if value is None:
        return None
    if category in {Category.PERFORMANCE, Category.CTR}:
        return f"{value:.2f}%"
    if category in {Category.BUDGET, Category.SPEND, Category.CPA}:
        return f"${value:.2f}"
    if category == Category.FREQUENCY:
        return f"{value:.2f}x"
    return f"{value:.2f}"


def _comparison(finding: Finding) -> str:
    actual = _format_metric(finding.metric_value, finding.category)
    threshold = _format_metric(finding.threshold_value, finding.category)
    if actual and threshold:
        return f"{finding.entity_name} is currently at {actual} versus the target threshold of {threshold}."
    if actual:
        return f"{finding.entity_name} is currently at {actual}."
    return f"The issue is centered on {finding.entity_name}."


def _qualitative_impact(finding: Finding) -> str:
    if finding.estimated_waste > 0 or finding.estimated_uplift > 0:
        parts: list[str] = []
        if finding.estimated_waste > 0:
            parts.append(f"Estimated waste: ${finding.estimated_waste:.0f}")
        if finding.estimated_uplift > 0:
            parts.append(f"Potential lift: ${finding.estimated_uplift:.0f}")
        return ". ".join(parts) + "."

    return (
        "The modelled dollar impact is low or unavailable in this dataset, but the signal still matters because it points to an efficiency issue that can scale as spend increases."
    )


def apply_recommendation(finding: Finding) -> Finding:
    templates = {
        "high_frequency_low_ctr": ("Refresh fatigued creatives", "Rotate creatives or widen the audience before repetition keeps suppressing response rates."),
        "high_spend_low_conversions": ("Pause or narrow weak delivery", "Reduce waste by pausing weak segments and checking whether the conversion path is still working."),
        "low_roas_high_spend": ("Reallocate away from weak return", "Shift budget toward campaigns or ad sets that are proving they can return revenue more efficiently."),
        "poor_placement_efficiency": ("Audit placement mix", "Cut placements that are inflating CPM without producing enough useful clicks or conversions."),
        "ad_fatigue_trend": ("Launch fresh creative variants", "Replace fatigued creative before CTR and conversion efficiency deteriorate further."),
        "budget_concentration_risk": ("Reduce concentration risk", "Spread spend across more validated winners so one weak campaign does not dominate account performance."),
        "objective_mismatch": ("Align objective with outcome", "Match the campaign objective to the real business outcome you expect the algorithm to optimize for."),
        "underfunded_winner": ("Scale the efficient winner", "Increase budget carefully on the entity that is already proving more efficient than the rest of the account."),
        "spend_spike_anomaly": ("Investigate the spend jump", "Check bid changes, audience expansion, or delivery instability behind the sudden cost increase."),
        "roas_drop_anomaly": ("Diagnose the return decline", "Review landing page changes, audience drift, and creative fatigue behind the recent ROAS drop."),
        "cpa_deterioration": ("Contain rising acquisition cost", "Tighten targeting and protect budget while acquisition cost is worsening."),
        "weak_account_ctr": ("Improve top-of-funnel response", "The account needs stronger hooks, clearer angles, or tighter audience alignment."),
        "weak_conversion_funnel_signal": ("Fix conversion leakage", "Clicks are not turning into outcomes efficiently, which usually points to offer, tracking, or landing-page friction."),
        "inefficient_adset_vs_siblings": ("Rebalance within the campaign", "Move delivery away from structurally weaker ad sets and toward stronger sibling sets."),
        "winner_loser_reallocation": ("Reallocate from losers to winners", "Move incremental budget into sibling entities with clearly better efficiency."),
    }
    title, base_body = templates.get(
        finding.recommendation_key,
        ("Review this finding", "Use the affected metrics and thresholds to adjust budget, structure, creative, or tracking."),
    )

    finding.recommendation_title = title
    finding.recommendation_body = " ".join([
        base_body,
        _comparison(finding),
        _qualitative_impact(finding),
    ]).strip()
    return finding
