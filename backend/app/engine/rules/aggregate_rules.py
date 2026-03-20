from app.engine.rules.base import AuditRule, register_rule
from app.engine.types import AccountAuditSnapshot, Category, Severity


@register_rule
class AggregateWeakAccountCTRRule(AuditRule):
    rule_id = "aggregate_weak_account_ctr"
    category = Category.ACCOUNT
    severity = Severity.MEDIUM

    def evaluate(self, snapshot: AccountAuditSnapshot):
        if snapshot.data_mode != "period_aggregate":
            return []
        if snapshot.account.total_spend < 100 or snapshot.account.ctr >= 0.5:
            return []
        return [
            self.finding(
                title="Account CTR is weak for imported aggregate history",
                description=f"Imported account history shows CTR of {snapshot.account.ctr:.2f}% across the selected period, which suggests weak traffic efficiency.",
                entity_type="account",
                entity_id=snapshot.ad_account_id,
                entity_name="Imported Report Account",
                metric_value=snapshot.account.ctr,
                threshold_value=0.5,
                estimated_waste=snapshot.account.total_spend * 0.12,
                estimated_uplift=snapshot.account.total_spend * 0.05,
                recommendation_key=self.rule_id,
                score_impact=5,
            )
        ]


@register_rule
class AggregateBudgetConcentrationRule(AuditRule):
    rule_id = "aggregate_budget_concentration"
    category = Category.BUDGET
    severity = Severity.MEDIUM

    def evaluate(self, snapshot: AccountAuditSnapshot):
        if snapshot.data_mode != "period_aggregate" or len(snapshot.campaigns) < 3:
            return []
        leader = max(snapshot.campaigns, key=lambda item: item.spend_share)
        if leader.spend_share < 0.45:
            return []
        return [
            self.finding(
                title="Spend is concentrated in one campaign",
                description=f"{leader.campaign_name} controls {leader.spend_share * 100:.1f}% of imported spend, which increases concentration risk in this account.",
                entity_type="campaign",
                entity_id=leader.campaign_id,
                entity_name=leader.campaign_name,
                metric_value=leader.spend_share * 100.0,
                threshold_value=45.0,
                estimated_waste=leader.total_spend * 0.08,
                estimated_uplift=leader.total_spend * 0.04,
                recommendation_key=self.rule_id,
                score_impact=4,
            )
        ]


@register_rule
class AggregateHighCPMWeakCTRRule(AuditRule):
    rule_id = "aggregate_high_cpm_weak_ctr"
    category = Category.PERFORMANCE
    severity = Severity.HIGH

    def evaluate(self, snapshot: AccountAuditSnapshot):
        if snapshot.data_mode != "period_aggregate":
            return []
        findings = []
        for campaign in snapshot.campaigns:
            if campaign.total_spend < 40:
                continue
            if campaign.cpm > snapshot.account.cpm * 1.05 and campaign.ctr < snapshot.account.ctr * 0.95:
                findings.append(
                    self.finding(
                        title="Campaign pays above-average CPM with weak CTR",
                        description=f"{campaign.campaign_name} is paying ${campaign.cpm:.2f} CPM with CTR of {campaign.ctr:.2f}%, under the imported account average.",
                        entity_type="campaign",
                        entity_id=campaign.campaign_id,
                        entity_name=campaign.campaign_name,
                        metric_value=campaign.cpm,
                        threshold_value=snapshot.account.cpm,
                        estimated_waste=campaign.total_spend * 0.12,
                        estimated_uplift=campaign.total_spend * 0.05,
                        recommendation_key=self.rule_id,
                        score_impact=6,
                    )
                )
        return findings
