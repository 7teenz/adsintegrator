from app.engine.rules.base import AuditRule, register_rule
from app.engine.types import AccountAuditSnapshot, Category, Severity


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
