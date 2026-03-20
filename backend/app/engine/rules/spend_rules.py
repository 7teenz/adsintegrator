"""Spend efficiency and budget audit rules."""

from app.engine.types import AccountAuditSnapshot as AccountSnapshot, Category, Finding, Severity
from app.engine.rules.base import AuditRule, register_rule


@register_rule
class SpendConcentrationRule(AuditRule):
    rule_id = "spend_concentration"
    category = Category.SPEND
    description = "Flags when a single campaign dominates total spend"

    def evaluate(self, snapshot: AccountSnapshot) -> list[Finding]:
        findings: list[Finding] = []
        if snapshot.account.total_spend == 0 or len(snapshot.campaigns) < 2:
            return findings

        for c in snapshot.campaigns:
            share = c.total_spend / snapshot.account.total_spend
            if share > 0.6:
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.WARNING,
                    category=Category.SPEND,
                    title=f"Campaign takes {share * 100:.0f}% of total spend",
                    description=(
                        f"Campaign '{c.campaign_name}' accounts for {share * 100:.0f}% "
                        f"(${c.total_spend:.2f}) of your total ${snapshot.account.total_spend:.2f} spend. "
                        f"Heavy concentration increases risk if this campaign underperforms."
                    ),
                    entity_type="campaign",
                    entity_id=c.campaign_id,
                    entity_name=c.campaign_name,
                    metric_value=share * 100,
                    threshold_value=60,
                ))
        return findings


@register_rule
class SpendWithoutImpressionsRule(AuditRule):
    rule_id = "spend_no_impressions"
    category = Category.SPEND
    description = "Flags campaigns with spend but negligible impressions"

    def evaluate(self, snapshot: AccountSnapshot) -> list[Finding]:
        findings: list[Finding] = []
        for c in snapshot.campaigns:
            if c.total_spend > 20 and c.total_impressions < 100:
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.CRITICAL,
                    category=Category.SPEND,
                    title=f"${c.total_spend:.0f} spent with negligible delivery",
                    description=(
                        f"Campaign '{c.campaign_name}' spent ${c.total_spend:.2f} but "
                        f"only delivered {c.total_impressions} impressions. This may indicate "
                        f"targeting issues, ad rejection, or bidding problems."
                    ),
                    entity_type="campaign",
                    entity_id=c.campaign_id,
                    entity_name=c.campaign_name,
                    metric_value=c.total_impressions,
                    threshold_value=100,
                    estimated_waste=c.total_spend,
                ))
        return findings


@register_rule
class HighCPMRule(AuditRule):
    rule_id = "spend_high_cpm"
    category = Category.SPEND
    description = "Flags campaigns with abnormally high CPM"

    def evaluate(self, snapshot: AccountSnapshot) -> list[Finding]:
        findings: list[Finding] = []

        cpms = [c.avg_cpm for c in snapshot.campaigns if c.avg_cpm > 0 and c.total_impressions >= 1000]
        if not cpms:
            return findings
        median_cpm = sorted(cpms)[len(cpms) // 2]

        for c in snapshot.campaigns:
            if c.status != "ACTIVE" or c.total_impressions < 1000:
                continue
            if c.avg_cpm > median_cpm * 2.5 and c.avg_cpm > 20:
                overpay = (c.avg_cpm - median_cpm) / 1000 * c.total_impressions
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.WARNING,
                    category=Category.SPEND,
                    title=f"High CPM: ${c.avg_cpm:.2f}",
                    description=(
                        f"Campaign '{c.campaign_name}' CPM is ${c.avg_cpm:.2f}, "
                        f"{c.avg_cpm / median_cpm:.1f}x the account median of ${median_cpm:.2f}. "
                        f"Check if audience size is too narrow or competition is driving up costs."
                    ),
                    entity_type="campaign",
                    entity_id=c.campaign_id,
                    entity_name=c.campaign_name,
                    metric_value=c.avg_cpm,
                    threshold_value=median_cpm,
                    estimated_waste=overpay,
                ))
        return findings
