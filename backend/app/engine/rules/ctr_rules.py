"""CTR-related audit rules."""

from app.engine.types import AccountAuditSnapshot as AccountSnapshot, Category, Finding, Severity
from app.engine.rules.base import AuditRule, register_rule

# Industry benchmark CTR for Facebook/Meta ads (%)
CTR_CRITICAL_THRESHOLD = 0.5
CTR_WARNING_THRESHOLD = 1.0
CTR_GOOD_THRESHOLD = 2.0


@register_rule
class LowCTRRule(AuditRule):
    rule_id = "ctr_low_campaign"
    category = Category.CTR
    description = "Flags campaigns with below-benchmark click-through rates"

    def evaluate(self, snapshot: AccountSnapshot) -> list[Finding]:
        findings: list[Finding] = []
        for c in snapshot.campaigns:
            if c.status != "ACTIVE" or c.total_impressions < 1000:
                continue

            if c.avg_ctr < CTR_CRITICAL_THRESHOLD:
                waste = c.total_spend * 0.4  # ~40% of spend on very low CTR is waste
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.CRITICAL,
                    category=Category.CTR,
                    title=f"Critically low CTR: {c.avg_ctr:.2f}%",
                    description=(
                        f"Campaign '{c.campaign_name}' has a CTR of {c.avg_ctr:.2f}%, "
                        f"well below the {CTR_CRITICAL_THRESHOLD}% critical threshold. "
                        f"This suggests poor ad creative or audience targeting."
                    ),
                    entity_type="campaign",
                    entity_id=c.campaign_id,
                    entity_name=c.campaign_name,
                    metric_value=c.avg_ctr,
                    threshold_value=CTR_CRITICAL_THRESHOLD,
                    estimated_waste=waste,
                ))
            elif c.avg_ctr < CTR_WARNING_THRESHOLD:
                waste = c.total_spend * 0.2
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.WARNING,
                    category=Category.CTR,
                    title=f"Below-average CTR: {c.avg_ctr:.2f}%",
                    description=(
                        f"Campaign '{c.campaign_name}' has a CTR of {c.avg_ctr:.2f}%, "
                        f"below the {CTR_WARNING_THRESHOLD}% benchmark. "
                        f"Consider refreshing creatives or narrowing targeting."
                    ),
                    entity_type="campaign",
                    entity_id=c.campaign_id,
                    entity_name=c.campaign_name,
                    metric_value=c.avg_ctr,
                    threshold_value=CTR_WARNING_THRESHOLD,
                    estimated_waste=waste,
                ))
        return findings


@register_rule
class DecliningCTRRule(AuditRule):
    rule_id = "ctr_declining"
    category = Category.CTR
    description = "Detects campaigns where CTR is trending downward"

    def evaluate(self, snapshot: AccountSnapshot) -> list[Finding]:
        findings: list[Finding] = []
        for c in snapshot.campaigns:
            if c.status != "ACTIVE" or len(c.daily_ctr) < 14:
                continue

            first_half = c.daily_ctr[: len(c.daily_ctr) // 2]
            second_half = c.daily_ctr[len(c.daily_ctr) // 2:]

            avg_first = sum(first_half) / len(first_half) if first_half else 0
            avg_second = sum(second_half) / len(second_half) if second_half else 0

            if avg_first > 0 and avg_second < avg_first * 0.7:
                decline_pct = round((1 - avg_second / avg_first) * 100, 1)
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.WARNING,
                    category=Category.CTR,
                    title=f"CTR declining by {decline_pct}%",
                    description=(
                        f"Campaign '{c.campaign_name}' CTR dropped {decline_pct}% "
                        f"from {avg_first:.2f}% to {avg_second:.2f}% over the analysis period. "
                        f"This may indicate ad fatigue."
                    ),
                    entity_type="campaign",
                    entity_id=c.campaign_id,
                    entity_name=c.campaign_name,
                    metric_value=avg_second,
                    threshold_value=avg_first,
                ))
        return findings
