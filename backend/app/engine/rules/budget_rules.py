from app.engine.rules.base import AuditRule, register_rule
from app.engine.types import AccountAuditSnapshot, Category, Severity


@register_rule
class BudgetConcentrationRiskRule(AuditRule):
    rule_id = "budget_concentration_risk"
    category = Category.BUDGET
    severity = Severity.HIGH

    def evaluate(self, snapshot: AccountAuditSnapshot):
        findings = []
        if not snapshot.campaigns:
            return findings
        dominant = max(snapshot.campaigns, key=lambda campaign: campaign.spend_share)
        if dominant.spend_share >= 0.6 and dominant.roas < max(snapshot.account.roas, 1.5):
            findings.append(self.finding(
                title="Budget concentration risk",
                description=f"{dominant.campaign_name} is taking {dominant.spend_share * 100:.1f}% of spend without clearly outperforming the account.",
                entity_type="campaign",
                entity_id=dominant.campaign_id,
                entity_name=dominant.campaign_name,
                metric_value=dominant.spend_share * 100,
                threshold_value=60.0,
                estimated_waste=dominant.total_spend * 0.12,
                estimated_uplift=snapshot.account.total_spend * 0.05,
                recommendation_key=self.rule_id,
                score_impact=7,
            ))
        return findings


@register_rule
class UnderfundedWinnerRule(AuditRule):
    rule_id = "underfunded_winner"
    category = Category.OPPORTUNITY
    severity = Severity.MEDIUM

    def evaluate(self, snapshot: AccountAuditSnapshot):
        findings = []
        for campaign in snapshot.campaigns:
            if campaign.total_spend < 200 and campaign.roas > max(2.5, snapshot.account.roas * 1.25):
                findings.append(self.finding(
                    title="Winner looks underfunded",
                    description=f"{campaign.campaign_name} is generating {campaign.roas:.2f}x ROAS on modest spend and likely has room to scale.",
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=campaign.roas,
                    threshold_value=snapshot.account.roas,
                    estimated_waste=0.0,
                    estimated_uplift=max(campaign.total_spend * 0.2, 25.0),
                    recommendation_key=self.rule_id,
                    score_impact=0,
                ))
        return findings


@register_rule
class WinnerLoserReallocationRule(AuditRule):
    rule_id = "winner_loser_reallocation"
    category = Category.OPPORTUNITY
    severity = Severity.HIGH

    def evaluate(self, snapshot: AccountAuditSnapshot):
        findings = []
        winners = [campaign for campaign in snapshot.campaigns if campaign.roas >= max(2.0, snapshot.account.roas * 1.2)]
        losers = [campaign for campaign in snapshot.campaigns if campaign.total_spend >= 200 and campaign.roas < max(1.0, snapshot.account.roas * 0.7)]
        if winners and losers:
            loser = max(losers, key=lambda campaign: campaign.total_spend)
            findings.append(self.finding(
                title="Budget reallocation opportunity",
                description=f"At least one stronger winner exists while {loser.campaign_name} continues to absorb inefficient spend.",
                entity_type="campaign",
                entity_id=loser.campaign_id,
                entity_name=loser.campaign_name,
                metric_value=loser.roas,
                threshold_value=snapshot.account.roas,
                estimated_waste=loser.total_spend * 0.18,
                estimated_uplift=loser.total_spend * 0.12,
                recommendation_key=self.rule_id,
                score_impact=6,
            ))
        return findings
