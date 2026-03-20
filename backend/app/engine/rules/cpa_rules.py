"""CPA / conversion efficiency audit rules."""

from app.engine.rules.base import AuditRule, register_rule
from app.engine.types import AccountAuditSnapshot as AccountSnapshot, Category, Finding, Severity


@register_rule
class HighCPARule(AuditRule):
    rule_id = "cpa_high_campaign"
    category = Category.CPA
    description = "Flags campaigns with disproportionately high cost per conversion"

    def evaluate(self, snapshot: AccountSnapshot) -> list[Finding]:
        findings: list[Finding] = []

        total_spend = sum(c.total_spend for c in snapshot.campaigns if c.total_conversions > 0)
        total_conv = sum(c.total_conversions for c in snapshot.campaigns if c.total_conversions > 0)
        if total_conv == 0:
            return findings
        account_avg_cpa = total_spend / total_conv

        for c in snapshot.campaigns:
            if c.status != "ACTIVE" or c.total_conversions < 3:
                continue

            if c.cost_per_conversion > account_avg_cpa * 2.5:
                waste = (c.cost_per_conversion - account_avg_cpa) * c.total_conversions
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.CRITICAL,
                    category=Category.CPA,
                    title=f"CPA {c.cost_per_conversion / account_avg_cpa:.1f}x above average",
                    description=(
                        f"Campaign '{c.campaign_name}' has a CPA of ${c.cost_per_conversion:.2f}, "
                        f"which is {c.cost_per_conversion / account_avg_cpa:.1f}x the account average "
                        f"of ${account_avg_cpa:.2f}. This campaign is consuming budget inefficiently."
                    ),
                    entity_type="campaign",
                    entity_id=c.campaign_id,
                    entity_name=c.campaign_name,
                    metric_value=c.cost_per_conversion,
                    threshold_value=account_avg_cpa,
                    estimated_waste=max(waste, 0),
                ))
            elif c.cost_per_conversion > account_avg_cpa * 1.5:
                waste = (c.cost_per_conversion - account_avg_cpa) * c.total_conversions * 0.5
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.WARNING,
                    category=Category.CPA,
                    title=f"CPA above average: ${c.cost_per_conversion:.2f}",
                    description=(
                        f"Campaign '{c.campaign_name}' CPA is ${c.cost_per_conversion:.2f} vs "
                        f"account average ${account_avg_cpa:.2f}. Review targeting and bid strategy."
                    ),
                    entity_type="campaign",
                    entity_id=c.campaign_id,
                    entity_name=c.campaign_name,
                    metric_value=c.cost_per_conversion,
                    threshold_value=account_avg_cpa,
                    estimated_waste=max(waste, 0),
                ))
        return findings


@register_rule
class ZeroConversionSpendRule(AuditRule):
    rule_id = "cpa_zero_conversions"
    category = Category.CPA
    description = "Flags active campaigns spending budget with zero conversions"

    def evaluate(self, snapshot: AccountSnapshot) -> list[Finding]:
        findings: list[Finding] = []
        for c in snapshot.campaigns:
            if c.status != "ACTIVE":
                continue
            if c.total_spend > 50 and c.total_conversions == 0:
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.CRITICAL,
                    category=Category.CPA,
                    title=f"${c.total_spend:.0f} spent with zero conversions",
                    description=(
                        f"Campaign '{c.campaign_name}' has spent ${c.total_spend:.2f} "
                        f"over {c.days_active} days without a single conversion. "
                        f"This entire spend is wasted if conversion is the goal."
                    ),
                    entity_type="campaign",
                    entity_id=c.campaign_id,
                    entity_name=c.campaign_name,
                    metric_value=0,
                    threshold_value=1,
                    estimated_waste=c.total_spend,
                ))
        return findings


@register_rule
class NegativeROASRule(AuditRule):
    rule_id = "cpa_negative_roas"
    category = Category.CPA
    description = "Flags campaigns where return on ad spend is below 1.0"

    def evaluate(self, snapshot: AccountSnapshot) -> list[Finding]:
        findings: list[Finding] = []
        for c in snapshot.campaigns:
            if c.status != "ACTIVE" or c.total_spend < 100 or c.total_conversion_value == 0:
                continue

            if c.roas < 1.0:
                loss = c.total_spend - c.total_conversion_value
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.CRITICAL,
                    category=Category.CPA,
                    title=f"Negative ROAS: {c.roas:.2f}x",
                    description=(
                        f"Campaign '{c.campaign_name}' has a ROAS of {c.roas:.2f}x - "
                        f"spending ${c.total_spend:.2f} but generating only "
                        f"${c.total_conversion_value:.2f} in revenue. Net loss: ${loss:.2f}."
                    ),
                    entity_type="campaign",
                    entity_id=c.campaign_id,
                    entity_name=c.campaign_name,
                    metric_value=c.roas,
                    threshold_value=1.0,
                    estimated_waste=max(loss, 0),
                ))
        return findings
