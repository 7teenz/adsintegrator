from app.engine.rules.base import AuditRule, register_rule
from app.engine.types import AccountAuditSnapshot, Category, Severity


@register_rule
class WeakAccountCTRRule(AuditRule):
    rule_id = "weak_account_ctr"
    category = Category.ACCOUNT
    severity = Severity.HIGH

    def evaluate(self, snapshot: AccountAuditSnapshot):
        if snapshot.account.ctr < 1.0 and snapshot.account.total_spend >= 300:
            return [self.finding(
                title="Account-wide CTR is weak",
                description=f"The account is averaging only {snapshot.account.ctr:.2f}% CTR on meaningful spend.",
                entity_type="account",
                entity_id=snapshot.ad_account_id,
                entity_name="Account",
                metric_value=snapshot.account.ctr,
                threshold_value=1.0,
                estimated_waste=snapshot.account.total_spend * 0.12,
                estimated_uplift=snapshot.account.total_spend * 0.05,
                recommendation_key=self.rule_id,
                score_impact=8,
            )]
        return []


@register_rule
class WeakConversionFunnelSignalRule(AuditRule):
    rule_id = "weak_conversion_funnel_signal"
    category = Category.ACCOUNT
    severity = Severity.HIGH

    def evaluate(self, snapshot: AccountAuditSnapshot):
        if snapshot.account.total_clicks >= 200 and snapshot.account.click_to_conversion_rate < 2.0:
            return [self.finding(
                title="Clicks are not converting efficiently",
                description=f"The account click-to-conversion rate is only {snapshot.account.click_to_conversion_rate:.2f}%, which points to funnel friction.",
                entity_type="account",
                entity_id=snapshot.ad_account_id,
                entity_name="Account",
                metric_value=snapshot.account.click_to_conversion_rate,
                threshold_value=2.0,
                estimated_waste=snapshot.account.total_spend * 0.1,
                estimated_uplift=snapshot.account.total_spend * 0.07,
                recommendation_key=self.rule_id,
                score_impact=8,
            )]
        return []
