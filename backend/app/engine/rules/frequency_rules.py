"""Frequency and ad fatigue audit rules."""

from app.engine.rules.base import AuditRule, register_rule
from app.engine.types import AccountAuditSnapshot as AccountSnapshot, Category, Finding, Severity

FREQUENCY_WARNING = 3.0
FREQUENCY_CRITICAL = 5.0


@register_rule
class HighFrequencyRule(AuditRule):
    rule_id = "freq_high"
    category = Category.FREQUENCY
    description = "Flags campaigns where average frequency indicates ad fatigue"

    def evaluate(self, snapshot: AccountSnapshot) -> list[Finding]:
        findings: list[Finding] = []
        for c in snapshot.campaigns:
            if c.status != "ACTIVE" or c.total_impressions < 1000:
                continue

            if c.avg_frequency >= FREQUENCY_CRITICAL:
                waste = c.total_spend * 0.3
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.CRITICAL,
                    category=Category.FREQUENCY,
                    title=f"Severe ad fatigue: frequency {c.avg_frequency:.1f}",
                    description=(
                        f"Campaign '{c.campaign_name}' has an average frequency of "
                        f"{c.avg_frequency:.1f}, meaning users see your ads ~{c.avg_frequency:.0f} times. "
                        f"Beyond {FREQUENCY_CRITICAL:.0f}x, returns diminish sharply and "
                        f"users experience banner blindness."
                    ),
                    entity_type="campaign",
                    entity_id=c.campaign_id,
                    entity_name=c.campaign_name,
                    metric_value=c.avg_frequency,
                    threshold_value=FREQUENCY_CRITICAL,
                    estimated_waste=waste,
                ))
            elif c.avg_frequency >= FREQUENCY_WARNING:
                waste = c.total_spend * 0.15
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.WARNING,
                    category=Category.FREQUENCY,
                    title=f"Rising frequency: {c.avg_frequency:.1f}",
                    description=(
                        f"Campaign '{c.campaign_name}' frequency is {c.avg_frequency:.1f}. "
                        f"Consider expanding audience or rotating creatives."
                    ),
                    entity_type="campaign",
                    entity_id=c.campaign_id,
                    entity_name=c.campaign_name,
                    metric_value=c.avg_frequency,
                    threshold_value=FREQUENCY_WARNING,
                    estimated_waste=waste,
                ))
        return findings


@register_rule
class FrequencySpikeRule(AuditRule):
    rule_id = "freq_spike"
    category = Category.FREQUENCY
    description = "Detects campaigns where frequency is spiking upward"

    def evaluate(self, snapshot: AccountSnapshot) -> list[Finding]:
        findings: list[Finding] = []
        for c in snapshot.campaigns:
            if c.status != "ACTIVE" or len(c.daily_frequency) < 10:
                continue

            last_7 = c.daily_frequency[-7:]
            prev_7 = c.daily_frequency[-14:-7] if len(c.daily_frequency) >= 14 else c.daily_frequency[:7]

            avg_recent = sum(last_7) / len(last_7) if last_7 else 0
            avg_prev = sum(prev_7) / len(prev_7) if prev_7 else 0

            if avg_prev > 0 and avg_recent > avg_prev * 1.5 and avg_recent >= 2.5:
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.WARNING,
                    category=Category.FREQUENCY,
                    title=f"Frequency spiking: {avg_prev:.1f} -> {avg_recent:.1f}",
                    description=(
                        f"Campaign '{c.campaign_name}' frequency jumped from "
                        f"{avg_prev:.1f} to {avg_recent:.1f} in the last 7 days. "
                        f"Audience saturation may be accelerating."
                    ),
                    entity_type="campaign",
                    entity_id=c.campaign_id,
                    entity_name=c.campaign_name,
                    metric_value=avg_recent,
                    threshold_value=avg_prev,
                ))
        return findings
