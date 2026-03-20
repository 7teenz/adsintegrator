from app.engine.rules.base import AuditRule, register_rule
from app.engine.types import AccountAuditSnapshot, Category, Severity


@register_rule
class AdFatigueTrendRule(AuditRule):
    rule_id = "ad_fatigue_trend"
    category = Category.TREND
    severity = Severity.HIGH

    def evaluate(self, snapshot: AccountAuditSnapshot):
        findings = []
        for campaign in snapshot.campaigns:
            if campaign.total_spend < 200:
                continue
            if campaign.wow_ctr_delta <= -0.2 and campaign.frequency >= 2.5:
                findings.append(self.finding(
                    title="CTR trend suggests ad fatigue",
                    description=f"{campaign.campaign_name} has a {campaign.wow_ctr_delta * 100:.1f}% WoW CTR decline with elevated frequency.",
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=campaign.wow_ctr_delta * 100,
                    threshold_value=-20.0,
                    estimated_waste=campaign.total_spend * 0.15,
                    estimated_uplift=campaign.total_spend * 0.08,
                    recommendation_key=self.rule_id,
                    score_impact=7,
                ))
        return findings


@register_rule
class SpendSpikeAnomalyRule(AuditRule):
    rule_id = "spend_spike_anomaly"
    category = Category.TREND
    severity = Severity.MEDIUM

    def evaluate(self, snapshot: AccountAuditSnapshot):
        findings = []
        for campaign in snapshot.campaigns:
            if campaign.total_spend < 150:
                continue
            if campaign.wow_spend_delta >= 0.5 and campaign.wow_roas_delta <= 0:
                findings.append(self.finding(
                    title="Spend spike without return improvement",
                    description=f"{campaign.campaign_name} spend increased {campaign.wow_spend_delta * 100:.1f}% WoW while return did not improve.",
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=campaign.wow_spend_delta * 100,
                    threshold_value=50.0,
                    estimated_waste=campaign.total_spend * 0.12,
                    estimated_uplift=campaign.total_spend * 0.05,
                    recommendation_key=self.rule_id,
                    score_impact=4,
                ))
        return findings


@register_rule
class ROASDropAnomalyRule(AuditRule):
    rule_id = "roas_drop_anomaly"
    category = Category.TREND
    severity = Severity.HIGH

    def evaluate(self, snapshot: AccountAuditSnapshot):
        findings = []
        for campaign in snapshot.campaigns:
            if campaign.total_spend < 200:
                continue
            if campaign.wow_roas_delta <= -0.25:
                findings.append(self.finding(
                    title="ROAS dropped materially week over week",
                    description=f"{campaign.campaign_name} shows a {campaign.wow_roas_delta * 100:.1f}% WoW ROAS decline.",
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=campaign.wow_roas_delta * 100,
                    threshold_value=-25.0,
                    estimated_waste=campaign.total_spend * 0.14,
                    estimated_uplift=campaign.total_spend * 0.07,
                    recommendation_key=self.rule_id,
                    score_impact=7,
                ))
        return findings


@register_rule
class CPADeteriorationRule(AuditRule):
    rule_id = "cpa_deterioration"
    category = Category.TREND
    severity = Severity.HIGH

    def evaluate(self, snapshot: AccountAuditSnapshot):
        findings = []
        for campaign in snapshot.campaigns:
            if campaign.total_conversions < 5:
                continue
            if campaign.wow_cpa_delta >= 0.25:
                findings.append(self.finding(
                    title="CPA deterioration detected",
                    description=f"{campaign.campaign_name} CPA worsened {campaign.wow_cpa_delta * 100:.1f}% week over week.",
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=campaign.wow_cpa_delta * 100,
                    threshold_value=25.0,
                    estimated_waste=campaign.total_spend * 0.12,
                    estimated_uplift=campaign.total_spend * 0.06,
                    recommendation_key=self.rule_id,
                    score_impact=7,
                ))
        return findings
