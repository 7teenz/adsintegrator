from app.engine.rules.base import AuditRule, register_rule
from app.engine.types import AccountAuditSnapshot, Category, Finding, Severity


@register_rule
class HighFrequencyLowCTRRule(AuditRule):
    rule_id = "high_frequency_low_ctr"
    category = Category.PERFORMANCE
    severity = Severity.HIGH

    def evaluate(self, snapshot: AccountAuditSnapshot):
        findings = []
        for campaign in snapshot.campaigns:
            if campaign.status != "ACTIVE" or campaign.total_spend < 100:
                continue
            if campaign.frequency >= 3.5 and campaign.ctr <= 1.0:
                findings.append(self.finding(
                    title="High frequency with weak CTR",
                    description=f"{campaign.campaign_name} is showing fatigue signals: frequency {campaign.frequency:.2f} with CTR {campaign.ctr:.2f}%.",
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=campaign.frequency,
                    threshold_value=3.5,
                    estimated_waste=campaign.total_spend * 0.18,
                    estimated_uplift=campaign.total_spend * 0.08,
                    recommendation_key=self.rule_id,
                    score_impact=6,
                ))
        return findings


@register_rule
class HighSpendLowConversionsRule(AuditRule):
    rule_id = "high_spend_low_conversions"
    category = Category.PERFORMANCE
    severity = Severity.CRITICAL

    def evaluate(self, snapshot: AccountAuditSnapshot):
        findings = []
        for campaign in snapshot.campaigns:
            if campaign.total_spend >= 300 and campaign.total_conversions <= 1:
                findings.append(self.finding(
                    title="High spend with little conversion output",
                    description=f"{campaign.campaign_name} spent ${campaign.total_spend:.0f} but produced only {campaign.total_conversions} conversions.",
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=float(campaign.total_conversions),
                    threshold_value=2.0,
                    estimated_waste=campaign.total_spend * 0.45,
                    estimated_uplift=campaign.total_spend * 0.12,
                    recommendation_key=self.rule_id,
                    score_impact=10,
                ))
        return findings


@register_rule
class LowROASHighSpendRule(AuditRule):
    rule_id = "low_roas_high_spend"
    category = Category.PERFORMANCE
    severity = Severity.CRITICAL

    def evaluate(self, snapshot: AccountAuditSnapshot):
        findings = []
        for campaign in snapshot.campaigns:
            if campaign.total_spend >= 500 and campaign.roas < 1.2:
                findings.append(self.finding(
                    title="Low ROAS on a high-spend campaign",
                    description=f"{campaign.campaign_name} is consuming meaningful budget with only {campaign.roas:.2f}x ROAS.",
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=campaign.roas,
                    threshold_value=1.2,
                    estimated_waste=campaign.total_spend * 0.3,
                    estimated_uplift=campaign.total_spend * 0.15,
                    recommendation_key=self.rule_id,
                    score_impact=10,
                ))
        return findings


@register_rule
class PoorPlacementEfficiencyRule(AuditRule):
    rule_id = "poor_placement_efficiency"
    category = Category.PLACEMENT
    severity = Severity.MEDIUM

    def evaluate(self, snapshot: AccountAuditSnapshot):
        findings = []
        for ad_set in snapshot.ad_sets:
            if ad_set.total_spend < 150:
                continue
            if ad_set.cpm > max(snapshot.account.cpm * 1.5, 12) and ad_set.ctr < snapshot.account.ctr * 0.8:
                findings.append(self.finding(
                    title="Placement efficiency looks weak",
                    description=f"{ad_set.ad_set_name} is paying a high CPM (${ad_set.cpm:.2f}) without enough CTR support.",
                    entity_type="ad_set",
                    entity_id=ad_set.ad_set_id,
                    entity_name=ad_set.ad_set_name,
                    metric_value=ad_set.cpm,
                    threshold_value=snapshot.account.cpm,
                    estimated_waste=ad_set.total_spend * 0.16,
                    estimated_uplift=ad_set.total_spend * 0.06,
                    recommendation_key=self.rule_id,
                    score_impact=4,
                ))
        return findings


@register_rule
class ObjectiveMismatchRule(AuditRule):
    rule_id = "objective_mismatch"
    category = Category.STRUCTURE
    severity = Severity.MEDIUM

    def evaluate(self, snapshot: AccountAuditSnapshot):
        findings = []
        mismatch_objectives = {"TRAFFIC", "REACH", "AWARENESS"}
        for campaign in snapshot.campaigns:
            if campaign.total_spend < 150 or campaign.total_conversions == 0:
                continue
            if (campaign.objective or "").upper() in mismatch_objectives and campaign.click_to_conversion_rate < 2.0:
                findings.append(self.finding(
                    title="Objective appears misaligned with conversion intent",
                    description=f"{campaign.campaign_name} is driving clicks but weak post-click performance under a {campaign.objective} objective.",
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=campaign.click_to_conversion_rate,
                    threshold_value=2.0,
                    estimated_waste=campaign.total_spend * 0.14,
                    estimated_uplift=campaign.total_spend * 0.09,
                    recommendation_key=self.rule_id,
                    score_impact=5,
                ))
        return findings


@register_rule
class WeakCVRRule(AuditRule):
    """Flags campaigns with meaningful click volume but a poor click-to-conversion rate.

    Thresholds:
    - CRITICAL: CVR < 0.5% (fewer than 5 conversions per 1,000 clicks)
    - WARNING:  CVR < 1.5%

    Minimum guards: at least 200 clicks so we have a reliable signal.
    """

    rule_id = "weak_cvr"
    category = Category.PERFORMANCE
    severity = Severity.HIGH

    # CVR thresholds in % (conversions / clicks * 100)
    CVR_CRITICAL_THRESHOLD = 0.5
    CVR_WARNING_THRESHOLD = 1.5

    def evaluate(self, snapshot: AccountAuditSnapshot):
        findings = []
        for campaign in snapshot.campaigns:
            if campaign.status != "ACTIVE":
                continue
            if campaign.total_clicks < 200:
                continue

            cvr = (campaign.total_conversions / campaign.total_clicks) * 100 if campaign.total_clicks else 0.0

            if cvr < self.CVR_CRITICAL_THRESHOLD:
                waste = campaign.total_spend * 0.35
                uplift = campaign.total_spend * 0.12
                findings.append(Finding(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=Severity.CRITICAL,
                    title=f"Critically low conversion rate: {cvr:.2f}%",
                    description=(
                        f"Campaign '{campaign.campaign_name}' is driving {campaign.total_clicks:,} clicks "
                        f"but converting only {cvr:.2f}% of them. "
                        f"This indicates a landing-page, offer, or audience-fit problem."
                    ),
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=round(cvr, 3),
                    threshold_value=self.CVR_CRITICAL_THRESHOLD,
                    estimated_waste=waste,
                    estimated_uplift=uplift,
                    recommendation_key=self.rule_id,
                    score_impact=8,
                ))
            elif cvr < self.CVR_WARNING_THRESHOLD:
                waste = campaign.total_spend * 0.15
                uplift = campaign.total_spend * 0.06
                findings.append(Finding(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=Severity.MEDIUM,
                    title=f"Below-average conversion rate: {cvr:.2f}%",
                    description=(
                        f"Campaign '{campaign.campaign_name}' has a CVR of {cvr:.2f}%, "
                        f"below the {self.CVR_WARNING_THRESHOLD}% benchmark. "
                        f"Review landing-page relevance and audience alignment."
                    ),
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=round(cvr, 3),
                    threshold_value=self.CVR_WARNING_THRESHOLD,
                    estimated_waste=waste,
                    estimated_uplift=uplift,
                    recommendation_key=self.rule_id,
                    score_impact=4,
                ))
        return findings


@register_rule
class UnevenDailySpendRule(AuditRule):
    """Detects erratic daily spend pacing — a signal of budget-control or bid-strategy issues.

    The rule computes the coefficient of variation (CV = std / mean) of daily spend.
    A CV above the threshold on a campaign with meaningful spend suggests the
    algorithm is struggling to distribute budget evenly, which can cause
    performance inconsistency and wasted impressions on peak days.

    Requires at least 14 daily data points.
    Threshold: CV > 0.6 (60% relative standard deviation) → WARNING,
               CV > 1.0 (100%)                            → HIGH.
    """

    rule_id = "uneven_daily_spend"
    category = Category.BUDGET
    severity = Severity.MEDIUM

    CV_WARNING_THRESHOLD = 0.6
    CV_HIGH_THRESHOLD = 1.0

    def evaluate(self, snapshot: AccountAuditSnapshot):
        findings = []
        for campaign in snapshot.campaigns:
            if campaign.status != "ACTIVE":
                continue
            if len(campaign.daily_points) < 14:
                continue
            if campaign.total_spend < 200:
                continue

            daily_spends = [p.spend for p in campaign.daily_points]
            mean_spend = sum(daily_spends) / len(daily_spends)
            if mean_spend == 0:
                continue

            variance = sum((s - mean_spend) ** 2 for s in daily_spends) / len(daily_spends)
            std_dev = variance ** 0.5
            cv = std_dev / mean_spend

            if cv >= self.CV_HIGH_THRESHOLD:
                findings.append(Finding(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=Severity.HIGH,
                    title=f"Highly erratic daily spend pacing (CV {cv:.2f})",
                    description=(
                        f"Campaign '{campaign.campaign_name}' has a spend coefficient of variation "
                        f"of {cv:.2f}, meaning daily spend swings wildly around the average. "
                        f"This can cause unpredictable delivery and audience saturation on high-spend days."
                    ),
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=round(cv, 3),
                    threshold_value=self.CV_HIGH_THRESHOLD,
                    estimated_waste=campaign.total_spend * 0.10,
                    estimated_uplift=campaign.total_spend * 0.05,
                    recommendation_key=self.rule_id,
                    score_impact=5,
                ))
            elif cv >= self.CV_WARNING_THRESHOLD:
                findings.append(Finding(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=Severity.MEDIUM,
                    title=f"Uneven daily spend pacing (CV {cv:.2f})",
                    description=(
                        f"Campaign '{campaign.campaign_name}' shows uneven spend distribution across days "
                        f"(CV {cv:.2f}). Consider switching to daily budget or reviewing bid strategy."
                    ),
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=round(cv, 3),
                    threshold_value=self.CV_WARNING_THRESHOLD,
                    estimated_waste=campaign.total_spend * 0.05,
                    estimated_uplift=campaign.total_spend * 0.03,
                    recommendation_key=self.rule_id,
                    score_impact=3,
                ))
        return findings
