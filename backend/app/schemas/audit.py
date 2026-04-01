from datetime import date, datetime

from pydantic import BaseModel


class AuditFindingResponse(BaseModel):
    id: str
    rule_id: str
    severity: str
    category: str
    title: str
    description: str
    entity_type: str
    entity_id: str
    entity_name: str
    affected_entity: str
    affected_entity_id: str
    metric_value: float | None
    threshold_value: float | None
    estimated_waste: float
    estimated_uplift: float
    recommendation_key: str | None
    score_impact: float
    confidence_label: str
    confidence_reason: str
    inspection_target: str


class RecommendationResponse(BaseModel):
    id: str
    audit_finding_id: str | None = None
    recommendation_key: str
    title: str
    body: str

    model_config = {"from_attributes": True}


class AuditScoreResponse(BaseModel):
    id: str
    score_key: str
    label: str
    name: str
    score: float
    weight: float
    description: str
    details: str
    findings_count: int = 0
    strongest_issue: str | None = None


class TrendPointResponse(BaseModel):
    label: str
    spend: float
    roas: float


class LeaderboardItemResponse(BaseModel):
    entity_id: str
    entity_name: str
    spend: float
    roas: float
    cpa: float
    ctr: float


class SeverityCountResponse(BaseModel):
    critical: int
    high: int
    medium: int
    low: int


class MetricSplitResponse(BaseModel):
    key: str
    label: str
    value: float


class AccountKpiResponse(BaseModel):
    spend: float
    impressions: int
    reach: int
    clicks: int
    ctr: float
    cpc: float
    cpm: float
    conversions: int
    conversion_value: float
    roas: float
    frequency: float
    cpa: float
    wow_spend_delta: float
    wow_ctr_delta: float
    wow_roas_delta: float
    wow_cpa_delta: float
    daily_budget_total: float
    lifetime_budget_total: float
    objective_mix: list[MetricSplitResponse]
    optimization_goal_mix: list[MetricSplitResponse]
    status_mix: list[MetricSplitResponse]


class AuditAISummaryResponse(BaseModel):
    id: str
    audit_run_id: str
    provider: str
    model: str
    prompt_version: str
    status: str
    short_executive_summary: str
    detailed_audit_explanation: str
    prioritized_action_plan: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class AuditRunResponse(BaseModel):
    id: str
    health_score: float
    total_spend: float
    total_wasted_spend: float
    total_estimated_uplift: float
    findings_count: int
    analysis_start: date
    analysis_end: date
    created_at: datetime
    campaign_count: int
    ad_set_count: int
    ad_count: int
    findings: list[AuditFindingResponse]
    scores: list[AuditScoreResponse]
    pillar_scores: list[AuditScoreResponse]
    recommendations: list[RecommendationResponse]
    ai_summary: AuditAISummaryResponse | None = None
    job_status: str = "completed"
    job_error: str | None = None
    celery_task_id: str | None = None


class AuditDashboardResponse(BaseModel):
    audit: AuditRunResponse | None
    kpis: AccountKpiResponse
    data_mode: str = "daily_breakdown"
    limitations: list[str] = []
    severity_counts: SeverityCountResponse
    top_opportunities: list[AuditFindingResponse]
    spend_roas_trend: list[TrendPointResponse]
    worst_campaigns: list[LeaderboardItemResponse]
    worst_adsets: list[LeaderboardItemResponse]


class AuditSummaryResponse(BaseModel):
    id: str
    health_score: float
    total_spend: float
    total_wasted_spend: float
    total_estimated_uplift: float
    findings_count: int
    analysis_start: date
    analysis_end: date
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditJobResponse(BaseModel):
    job_id: str
    status: str


class AuditJobStatusResponse(BaseModel):
    job_id: str
    status: str
    error: str | None = None
    completed_audit_id: str | None = None
