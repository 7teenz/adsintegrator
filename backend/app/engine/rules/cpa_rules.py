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


@register_rule
class WeakCVRAdSetRule(AuditRule):
    """Flags ad sets with meaningful click volume but a poor click-to-conversion rate.

    Mirrors WeakCVRRule (campaign-level) but operates at the ad-set level so that
    a healthy campaign average cannot mask individual ad sets with leaking funnels.

    Thresholds:
    - CRITICAL: CVR < 0.5%
    - WARNING:  CVR < 1.5%

    Minimum guards: 100 clicks and $30 spend.
    """

    rule_id = "weak_cvr_adset"
    category = Category.CPA
    description = "Flags ad sets with meaningful click volume but poor conversion rates"

    CVR_CRITICAL_THRESHOLD = 0.5
    CVR_WARNING_THRESHOLD = 1.5
    MIN_CLICKS = 100

    def evaluate(self, snapshot: AccountSnapshot) -> list[Finding]:
        findings: list[Finding] = []
        for ad_set in snapshot.ad_sets:
            if ad_set.status != "ACTIVE":
                continue
            if ad_set.total_clicks < self.MIN_CLICKS:
                continue
            if ad_set.total_spend < 30:
                continue

            cvr = (ad_set.total_conversions / ad_set.total_clicks) * 100

            if cvr < self.CVR_CRITICAL_THRESHOLD:
                waste = ad_set.total_spend * 0.35
                uplift = ad_set.total_spend * 0.12
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.CRITICAL,
                    category=self.category,
                    title=f"Ad set CVR critically low: {cvr:.2f}%",
                    description=(
                        f"Ad set '{ad_set.ad_set_name}' is driving {ad_set.total_clicks:,} clicks "
                        f"but converting only {cvr:.2f}% of them. "
                        f"Review audience targeting, landing page, and offer relevance."
                    ),
                    entity_type="ad_set",
                    entity_id=ad_set.ad_set_id,
                    entity_name=ad_set.ad_set_name,
                    metric_value=round(cvr, 3),
                    threshold_value=self.CVR_CRITICAL_THRESHOLD,
                    estimated_waste=waste,
                    estimated_uplift=uplift,
                ))
            elif cvr < self.CVR_WARNING_THRESHOLD:
                waste = ad_set.total_spend * 0.15
                uplift = ad_set.total_spend * 0.06
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MEDIUM,
                    category=self.category,
                    title=f"Ad set CVR below benchmark: {cvr:.2f}%",
                    description=(
                        f"Ad set '{ad_set.ad_set_name}' has a CVR of {cvr:.2f}%, "
                        f"below the {self.CVR_WARNING_THRESHOLD}% benchmark. "
                        f"Review audience alignment and landing page quality."
                    ),
                    entity_type="ad_set",
                    entity_id=ad_set.ad_set_id,
                    entity_name=ad_set.ad_set_name,
                    metric_value=round(cvr, 3),
                    threshold_value=self.CVR_WARNING_THRESHOLD,
                    estimated_waste=waste,
                    estimated_uplift=uplift,
                ))
        return findings


@register_rule
class DecliningCVRTrendRule(AuditRule):
    """Detects a significant decline in CVR over the analysis window.

    Compares CVR in the first half of the daily time series against the last 7 days.
    A drop of ≥ 50% signals a deteriorating conversion path (audience saturation,
    offer decay, or tracking degradation).

    Thresholds:
    - HIGH:   recent CVR < 50% of early CVR
    - MEDIUM: recent CVR < 70% of early CVR

    Minimum guards: 14 daily data points, ≥50 clicks in each comparison window.
    """

    rule_id = "cvr_declining_trend"
    category = Category.CPA
    description = "Detects campaigns where CVR is declining significantly over the analysis window"

    MIN_DAILY_POINTS = 14
    MIN_CLICKS_PER_WINDOW = 50
    DECLINE_HIGH_RATIO = 0.50
    DECLINE_MEDIUM_RATIO = 0.70

    def evaluate(self, snapshot: AccountSnapshot) -> list[Finding]:
        findings: list[Finding] = []
        for campaign in snapshot.campaigns:
            if campaign.status != "ACTIVE":
                continue
            if len(campaign.daily_points) < self.MIN_DAILY_POINTS:
                continue
            if campaign.total_spend < 100:
                continue

            points = campaign.daily_points
            mid = len(points) // 2
            first_half = points[:mid]
            last_7 = points[-7:]

            early_clicks = sum(p.clicks for p in first_half)
            early_convs = sum(p.conversions for p in first_half)
            recent_clicks = sum(p.clicks for p in last_7)
            recent_convs = sum(p.conversions for p in last_7)

            if early_clicks < self.MIN_CLICKS_PER_WINDOW or recent_clicks < self.MIN_CLICKS_PER_WINDOW:
                continue
            if early_convs == 0:
                continue

            early_cvr = early_convs / early_clicks
            recent_cvr = recent_convs / recent_clicks if recent_clicks > 0 else 0.0
            ratio = recent_cvr / early_cvr

            if ratio < self.DECLINE_HIGH_RATIO:
                drop_pct = (1 - ratio) * 100
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.HIGH,
                    category=self.category,
                    title=f"CVR declining sharply: -{drop_pct:.0f}% vs early period",
                    description=(
                        f"Campaign '{campaign.campaign_name}' conversion rate has dropped "
                        f"{drop_pct:.0f}% from {early_cvr * 100:.2f}% (early period) to "
                        f"{recent_cvr * 100:.2f}% (last 7 days). "
                        f"Investigate audience saturation, offer decay, or tracking issues."
                    ),
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=round(recent_cvr * 100, 3),
                    threshold_value=round(early_cvr * 100, 3),
                    estimated_waste=campaign.total_spend * 0.20,
                    estimated_uplift=campaign.total_spend * 0.10,
                ))
            elif ratio < self.DECLINE_MEDIUM_RATIO:
                drop_pct = (1 - ratio) * 100
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MEDIUM,
                    category=self.category,
                    title=f"CVR trending down: -{drop_pct:.0f}% vs early period",
                    description=(
                        f"Campaign '{campaign.campaign_name}' conversion rate has softened "
                        f"{drop_pct:.0f}% from {early_cvr * 100:.2f}% (early period) to "
                        f"{recent_cvr * 100:.2f}% (last 7 days). Monitor closely."
                    ),
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=round(recent_cvr * 100, 3),
                    threshold_value=round(early_cvr * 100, 3),
                    estimated_waste=campaign.total_spend * 0.10,
                    estimated_uplift=campaign.total_spend * 0.05,
                ))
        return findings


@register_rule
class LowConversionValueRule(AuditRule):
    """Flags campaigns where value per conversion is significantly below account average.

    This signals either low-quality conversion events (micro-conversions counted as
    primary conversions), a pricing mismatch, or an audience that buys at a much
    lower AOV than the rest of the account. The pattern inflates conversion volume
    without corresponding revenue impact.

    Thresholds:
    - HIGH:   campaign value/conv < 40% of account average
    - MEDIUM: campaign value/conv < 65% of account average

    Minimum guards: account ≥ 20 conversions (reliable average),
                    campaign ≥ 10 conversions, campaign spend ≥ $200.
    """

    rule_id = "low_conversion_value"
    category = Category.CPA
    description = "Flags campaigns generating conversions at much lower value than account average"

    MIN_ACCOUNT_CONVERSIONS = 20
    MIN_CAMPAIGN_CONVERSIONS = 10
    MIN_CAMPAIGN_SPEND = 200.0
    CRITICAL_RATIO = 0.40
    WARNING_RATIO = 0.65

    def evaluate(self, snapshot: AccountSnapshot) -> list[Finding]:
        findings: list[Finding] = []

        if snapshot.account.total_conversions < self.MIN_ACCOUNT_CONVERSIONS:
            return findings
        if snapshot.account.total_conversion_value <= 0:
            return findings

        account_avg_value = snapshot.account.total_conversion_value / snapshot.account.total_conversions

        for campaign in snapshot.campaigns:
            if campaign.status != "ACTIVE":
                continue
            if campaign.total_conversions < self.MIN_CAMPAIGN_CONVERSIONS:
                continue
            if campaign.total_conversion_value <= 0:
                continue
            if campaign.total_spend < self.MIN_CAMPAIGN_SPEND:
                continue

            campaign_value_per_conv = campaign.total_conversion_value / campaign.total_conversions
            ratio = campaign_value_per_conv / account_avg_value

            if ratio < self.CRITICAL_RATIO:
                gap_per_conv = account_avg_value - campaign_value_per_conv
                waste = max(gap_per_conv * campaign.total_conversions * 0.50, 0)
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.HIGH,
                    category=self.category,
                    title=f"Conversion value {ratio * 100:.0f}% of account average",
                    description=(
                        f"Campaign '{campaign.campaign_name}' generates "
                        f"${campaign_value_per_conv:.2f} per conversion, "
                        f"only {ratio * 100:.0f}% of the account average "
                        f"(${account_avg_value:.2f}). "
                        f"This may indicate low-value conversion events or audience mismatch."
                    ),
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=round(campaign_value_per_conv, 2),
                    threshold_value=round(account_avg_value, 2),
                    estimated_waste=waste,
                    estimated_uplift=waste * 0.50,
                ))
            elif ratio < self.WARNING_RATIO:
                gap_per_conv = account_avg_value - campaign_value_per_conv
                waste = max(gap_per_conv * campaign.total_conversions * 0.25, 0)
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MEDIUM,
                    category=self.category,
                    title=f"Below-average conversion value: ${campaign_value_per_conv:.2f}/conv",
                    description=(
                        f"Campaign '{campaign.campaign_name}' conversion value "
                        f"(${campaign_value_per_conv:.2f}/conv) is below the account average "
                        f"(${account_avg_value:.2f}/conv). "
                        f"Review whether the conversion event is aligned with actual revenue."
                    ),
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    entity_name=campaign.campaign_name,
                    metric_value=round(campaign_value_per_conv, 2),
                    threshold_value=round(account_avg_value, 2),
                    estimated_waste=waste,
                    estimated_uplift=waste * 0.50,
                ))
        return findings


@register_rule
class HighCPAAdSetRule(AuditRule):
    rule_id = "cpa_high_adset"
    category = Category.CPA
    description = "Flags ad sets with disproportionately high cost per conversion vs campaign average"

    def evaluate(self, snapshot: AccountSnapshot) -> list[Finding]:
        findings: list[Finding] = []

        # Build a per-campaign CPA map from campaign-level data
        campaign_cpa: dict[str, float] = {}
        for c in snapshot.campaigns:
            if c.total_conversions > 0:
                campaign_cpa[c.campaign_id] = c.cost_per_conversion

        for ad_set in snapshot.ad_sets:
            if ad_set.status != "ACTIVE" or ad_set.total_conversions < 2:
                continue
            if ad_set.total_spend < 20:
                continue

            parent_cpa = campaign_cpa.get(ad_set.campaign_id)
            if parent_cpa is None or parent_cpa == 0:
                continue

            ad_set_cpa = ad_set.cpa  # cost_per_conversion at ad set level

            if ad_set_cpa > parent_cpa * 2.5:
                waste = (ad_set_cpa - parent_cpa) * ad_set.total_conversions
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.CRITICAL,
                    category=Category.CPA,
                    title=f"Ad set CPA {ad_set_cpa / parent_cpa:.1f}x above campaign average",
                    description=(
                        f"Ad set '{ad_set.ad_set_name}' has a CPA of ${ad_set_cpa:.2f}, "
                        f"which is {ad_set_cpa / parent_cpa:.1f}x the campaign average "
                        f"of ${parent_cpa:.2f}. This ad set is dragging down campaign efficiency."
                    ),
                    entity_type="ad_set",
                    entity_id=ad_set.ad_set_id,
                    entity_name=ad_set.ad_set_name,
                    metric_value=ad_set_cpa,
                    threshold_value=parent_cpa,
                    estimated_waste=max(waste, 0),
                ))
            elif ad_set_cpa > parent_cpa * 1.5:
                waste = (ad_set_cpa - parent_cpa) * ad_set.total_conversions * 0.5
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.WARNING,
                    category=Category.CPA,
                    title=f"Ad set CPA above campaign average: ${ad_set_cpa:.2f}",
                    description=(
                        f"Ad set '{ad_set.ad_set_name}' CPA is ${ad_set_cpa:.2f} vs "
                        f"campaign average ${parent_cpa:.2f}. "
                        f"Review audience targeting and bid cap for this ad set."
                    ),
                    entity_type="ad_set",
                    entity_id=ad_set.ad_set_id,
                    entity_name=ad_set.ad_set_name,
                    metric_value=ad_set_cpa,
                    threshold_value=parent_cpa,
                    estimated_waste=max(waste, 0),
                ))
        return findings
