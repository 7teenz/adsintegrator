from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    WARNING = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Category(str, Enum):
    PERFORMANCE = "performance"
    BUDGET = "budget"
    SPEND = "budget"
    TREND = "trend"
    ACCOUNT = "account"
    STRUCTURE = "structure"
    OPPORTUNITY = "opportunity"
    PLACEMENT = "placement"
    CTR = "ctr"
    FREQUENCY = "frequency"
    CPA = "cpa"


@dataclass
class DailyMetricPoint:
    date: date
    spend: float
    impressions: int
    clicks: int
    conversions: int
    conversion_value: float
    ctr: float
    cpc: float
    cpm: float
    frequency: float
    roas: float
    cpa: float


@dataclass
class CampaignAuditMetrics:
    campaign_id: str
    campaign_name: str
    status: str
    objective: str | None
    total_spend: float
    total_impressions: int
    total_clicks: int
    total_reach: int
    total_conversions: int
    total_conversion_value: float
    ctr: float
    cpc: float
    cpm: float
    cpa: float
    roas: float
    frequency: float
    click_to_conversion_rate: float
    spend_share: float
    wow_spend_delta: float
    wow_ctr_delta: float
    wow_roas_delta: float
    wow_cpa_delta: float
    ad_set_count: int
    ad_count: int
    daily_points: list[DailyMetricPoint] = field(default_factory=list)

    @property
    def avg_ctr(self) -> float:
        return self.ctr

    @property
    def avg_frequency(self) -> float:
        return self.frequency

    @property
    def avg_cpm(self) -> float:
        return self.cpm

    @property
    def cost_per_conversion(self) -> float:
        return self.cpa

    @property
    def daily_ctr(self) -> list[float]:
        return [point.ctr for point in self.daily_points]

    @property
    def daily_frequency(self) -> list[float]:
        return [point.frequency for point in self.daily_points]

    @property
    def days_active(self) -> int:
        return len(self.daily_points)


@dataclass
class AdSetAuditMetrics:
    ad_set_id: str
    ad_set_name: str
    campaign_id: str
    campaign_name: str
    status: str
    optimization_goal: str | None
    total_spend: float
    total_impressions: int
    total_clicks: int
    total_reach: int
    total_conversions: int
    total_conversion_value: float
    ctr: float
    cpc: float
    cpm: float
    cpa: float
    roas: float
    frequency: float
    click_to_conversion_rate: float
    spend_share_within_campaign: float
    wow_spend_delta: float
    wow_ctr_delta: float
    wow_roas_delta: float
    wow_cpa_delta: float
    daily_points: list[DailyMetricPoint] = field(default_factory=list)


@dataclass
class AccountAuditMetrics:
    total_spend: float
    total_impressions: int
    total_clicks: int
    total_reach: int
    total_conversions: int
    total_conversion_value: float
    ctr: float
    cpc: float
    cpm: float
    cpa: float
    roas: float
    frequency: float
    click_to_conversion_rate: float
    wow_spend_delta: float
    wow_ctr_delta: float
    wow_roas_delta: float
    wow_cpa_delta: float
    daily_points: list[DailyMetricPoint] = field(default_factory=list)


@dataclass
class AccountAuditSnapshot:
    ad_account_id: str
    analysis_start: date
    analysis_end: date
    data_mode: str
    limitations: list[str]
    account: AccountAuditMetrics
    campaigns: list[CampaignAuditMetrics]
    ad_sets: list[AdSetAuditMetrics]
    campaign_count: int
    ad_set_count: int
    ad_count: int


@dataclass
class Finding:
    rule_id: str
    severity: Severity
    category: Category
    title: str
    description: str
    entity_type: str
    entity_id: str
    entity_name: str
    metric_value: float | None = None
    threshold_value: float | None = None
    estimated_waste: float = 0.0
    estimated_uplift: float = 0.0
    recommendation_key: str = ""
    recommendation_title: str = ""
    recommendation_body: str = ""
    score_impact: float = 0.0


@dataclass
class ScoreBreakdown:
    key: str
    label: str
    score: float
    weight: float
    details: str


@dataclass
class AuditRunResult:
    ad_account_id: str
    analysis_start: date
    analysis_end: date
    health_score: float
    total_spend: float
    total_wasted_spend: float
    total_estimated_uplift: float
    campaign_count: int
    ad_set_count: int
    ad_count: int
    findings: list[Finding] = field(default_factory=list)
    scores: list[ScoreBreakdown] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ad_account_id": self.ad_account_id,
            "analysis_start": self.analysis_start.isoformat(),
            "analysis_end": self.analysis_end.isoformat(),
            "health_score": round(self.health_score, 1),
            "total_spend": round(self.total_spend, 2),
            "total_wasted_spend": round(self.total_wasted_spend, 2),
            "total_estimated_uplift": round(self.total_estimated_uplift, 2),
            "campaign_count": self.campaign_count,
            "ad_set_count": self.ad_set_count,
            "ad_count": self.ad_count,
            "scores": [
                {
                    "key": score.key,
                    "label": score.label,
                    "score": round(score.score, 1),
                    "weight": score.weight,
                    "details": score.details,
                }
                for score in self.scores
            ],
            "findings": [
                {
                    "rule_id": finding.rule_id,
                    "severity": finding.severity.value,
                    "category": finding.category.value,
                    "title": finding.title,
                    "description": finding.description,
                    "entity_type": finding.entity_type,
                    "entity_id": finding.entity_id,
                    "entity_name": finding.entity_name,
                    "metric_value": finding.metric_value,
                    "threshold_value": finding.threshold_value,
                    "estimated_waste": round(finding.estimated_waste, 2),
                    "estimated_uplift": round(finding.estimated_uplift, 2),
                    "recommendation_key": finding.recommendation_key,
                    "recommendation_title": finding.recommendation_title,
                    "recommendation_body": finding.recommendation_body,
                    "score_impact": round(finding.score_impact, 2),
                }
                for finding in self.findings
            ],
        }
