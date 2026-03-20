from collections import defaultdict

from app.engine.rules.base import AuditRule, register_rule
from app.engine.types import AccountAuditSnapshot, Category, Severity


@register_rule
class InefficientAdSetVsSiblingsRule(AuditRule):
    rule_id = "inefficient_adset_vs_siblings"
    category = Category.OPPORTUNITY
    severity = Severity.MEDIUM

    def evaluate(self, snapshot: AccountAuditSnapshot):
        findings = []
        grouped = defaultdict(list)
        for ad_set in snapshot.ad_sets:
            grouped[ad_set.campaign_id].append(ad_set)

        for siblings in grouped.values():
            if len(siblings) < 2:
                continue
            average_roas = sum(ad_set.roas for ad_set in siblings) / len(siblings)
            average_cpa = sum(ad_set.cpa for ad_set in siblings if ad_set.cpa > 0) / max(1, len([ad_set for ad_set in siblings if ad_set.cpa > 0]))
            for ad_set in siblings:
                if ad_set.total_spend < 100:
                    continue
                if ad_set.roas < average_roas * 0.7 or (average_cpa and ad_set.cpa > average_cpa * 1.4):
                    findings.append(self.finding(
                        title="Ad set is inefficient versus siblings",
                        description=f"{ad_set.ad_set_name} is underperforming compared with peer ad sets in {ad_set.campaign_name}.",
                        entity_type="ad_set",
                        entity_id=ad_set.ad_set_id,
                        entity_name=ad_set.ad_set_name,
                        metric_value=ad_set.roas,
                        threshold_value=average_roas,
                        estimated_waste=ad_set.total_spend * 0.14,
                        estimated_uplift=ad_set.total_spend * 0.06,
                        recommendation_key=self.rule_id,
                        score_impact=4,
                    ))
        return findings
