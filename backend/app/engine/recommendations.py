from app.engine.types import Finding


def apply_recommendation(finding: Finding) -> Finding:
    templates = {
        "high_frequency_low_ctr": ("Refresh fatigued creatives", "Reduce frequency by rotating creatives or tightening audiences."),
        "high_spend_low_conversions": ("Pause or narrow the campaign", "Cut waste by pausing the weakest segments and validating conversion tracking."),
        "low_roas_high_spend": ("Reallocate away from low ROAS", "Shift budget toward campaigns or ad sets with stronger return efficiency."),
        "poor_placement_efficiency": ("Audit placement mix", "Review placement breakdowns and exclude placements that inflate CPM without enough click volume."),
        "ad_fatigue_trend": ("Launch fresh variants", "Introduce new creative angles before fatigue pushes CTR and ROAS lower."),
        "budget_concentration_risk": ("Diversify budget allocation", "Reduce account fragility by distributing spend across more validated winners."),
        "objective_mismatch": ("Align objective with outcome", "Match campaign objective to the conversion outcome you expect the algorithm to optimize for."),
        "underfunded_winner": ("Increase budget on winner", "This entity is efficient enough to justify controlled budget expansion."),
        "spend_spike_anomaly": ("Investigate sudden spend jump", "Check bid changes, audience expansion, or delivery instability behind the spike."),
        "roas_drop_anomaly": ("Diagnose ROAS deterioration", "Review landing page changes, audience drift, and creative fatigue behind the recent drop."),
        "cpa_deterioration": ("Contain rising acquisition cost", "Tighten targeting and protect budget while CPA is worsening."),
        "weak_account_ctr": ("Improve top-of-funnel engagement", "The account needs stronger hooks, clearer angles, or tighter audience alignment."),
        "weak_conversion_funnel_signal": ("Fix funnel leakage", "Low conversion yield from clicks points to offer, landing page, or post-click friction issues."),
        "inefficient_adset_vs_siblings": ("Rebalance within the campaign", "Compare sibling ad sets and move spend away from structurally weaker delivery."),
        "winner_loser_reallocation": ("Reallocate from losers to winners", "Shift incremental budget to stronger sibling entities with better efficiency."),
    }
    title, body = templates.get(
        finding.recommendation_key,
        ("Review this finding", "Use the affected metrics and thresholds to adjust budget, structure, or creative."),
    )
    finding.recommendation_title = title
    finding.recommendation_body = body
    return finding
