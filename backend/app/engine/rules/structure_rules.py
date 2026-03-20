from app.engine.rules.base import AuditRule, register_rule
from app.engine.types import AccountAuditSnapshot, Category, Severity


@register_rule
class ObjectiveMismatchStructureRule(AuditRule):
    rule_id = "structure_guardrail"
    category = Category.STRUCTURE
    severity = Severity.LOW

    def evaluate(self, snapshot: AccountAuditSnapshot):
        findings = []
        for campaign in snapshot.campaigns:
            if campaign.ad_set_count > 12:
                findings.append(self.finding(
                    title="Campaign structure may be too fragmented",
                    description=f"{campaign.campaign_name} has {campaign.ad_set_count} ad sets, which may dilute learning.",
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=float(campaign.ad_set_count),
                    threshold_value=12.0,
                    estimated_waste=campaign.total_spend * 0.05,
                    estimated_uplift=campaign.total_spend * 0.03,
                    recommendation_key="objective_mismatch",
                    score_impact=2,
                ))
        return findings
