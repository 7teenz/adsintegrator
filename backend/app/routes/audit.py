from datetime import datetime
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.engine.collector import collect_account_data
from app.engine.orchestrator import run_audit
from app.middleware.deps import get_current_user
from app.models.audit import AuditRun
from app.models.campaign import AdSet, Campaign
from app.models.insights import DailyAccountInsight, DailyAdSetInsight, DailyCampaignInsight
from app.models.user import User
from app.schemas.audit import (
    AuditAISummaryResponse,
    AuditDashboardResponse,
    AuditFindingResponse,
    AccountKpiResponse,
    AuditRunResponse,
    AuditScoreResponse,
    AuditSummaryResponse,
    LeaderboardItemResponse,
    MetricSplitResponse,
    RecommendationResponse,
    SeverityCountResponse,
    TrendPointResponse,
)
from app.services.ai_summary import AISummaryService
from app.services.entitlements import EntitlementService, Entitlements
from app.services.meta_ads import MetaAdsService
from app.services.meta_auth import MetaAuthService

router = APIRouter(prefix="/audit", tags=["audit"])


def _get_selected_account(db: Session, user_id: str):
    connection = MetaAuthService.get_connection(db, user_id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": "No Meta connection", "code": "META_NOT_CONNECTED"},
        )
    account = MetaAdsService.get_selected_account(db, connection.id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": "No ad account selected", "code": "META_ACCOUNT_NOT_SELECTED"},
        )
    return account


def _safe_pct_delta(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return ((current - previous) / abs(previous)) * 100.0


def _mix_from_counter(counter: Counter, top_n: int = 5) -> list[MetricSplitResponse]:
    total = sum(counter.values())
    if total == 0:
        return []
    top = counter.most_common(top_n)
    return [
        MetricSplitResponse(key=str(key).lower().replace(" ", "_"), label=str(key), value=round((value / total) * 100.0, 2))
        for key, value in top
    ]


def _compute_account_kpis(db: Session, account_id: str) -> AccountKpiResponse:
    rows = (
        db.query(DailyAccountInsight)
        .filter(DailyAccountInsight.ad_account_id == account_id)
        .order_by(DailyAccountInsight.date.asc())
        .all()
    )

    def _slice_sum(items):
        spend = sum(item.spend for item in items)
        impressions = sum(item.impressions for item in items)
        reach = sum(item.reach for item in items)
        clicks = sum(item.clicks for item in items)
        conversions = sum(item.conversions for item in items)
        conversion_value = sum(item.conversion_value for item in items)
        ctr = (100.0 * clicks / impressions) if impressions > 0 else 0.0
        cpc = (spend / clicks) if clicks > 0 else 0.0
        cpm = (1000.0 * spend / impressions) if impressions > 0 else 0.0
        frequency = (impressions / reach) if reach > 0 else 0.0
        roas = (conversion_value / spend) if spend > 0 else 0.0
        cpa = (spend / conversions) if conversions > 0 else 0.0
        return {
            "spend": spend,
            "impressions": impressions,
            "reach": reach,
            "clicks": clicks,
            "conversions": conversions,
            "conversion_value": conversion_value,
            "ctr": ctr,
            "cpc": cpc,
            "cpm": cpm,
            "frequency": frequency,
            "roas": roas,
            "cpa": cpa,
        }

    aggregate = _slice_sum(rows)
    recent = rows[-7:] if len(rows) >= 7 else rows
    previous = rows[-14:-7] if len(rows) >= 14 else rows[: max(0, len(rows) - len(recent))]
    recent_sum = _slice_sum(recent)
    previous_sum = _slice_sum(previous)

    campaigns = db.query(Campaign).filter(Campaign.ad_account_id == account_id).all()
    adsets = db.query(AdSet).filter(AdSet.ad_account_id == account_id).all()
    objective_counter = Counter([(item.objective or "UNKNOWN") for item in campaigns])
    status_counter = Counter([(item.status or "UNKNOWN") for item in campaigns])
    optimization_counter = Counter([(item.optimization_goal or "UNKNOWN") for item in adsets])

    return AccountKpiResponse(
        spend=round(aggregate["spend"], 2),
        impressions=int(aggregate["impressions"]),
        reach=int(aggregate["reach"]),
        clicks=int(aggregate["clicks"]),
        ctr=round(aggregate["ctr"], 4),
        cpc=round(aggregate["cpc"], 4),
        cpm=round(aggregate["cpm"], 4),
        conversions=int(aggregate["conversions"]),
        conversion_value=round(aggregate["conversion_value"], 2),
        roas=round(aggregate["roas"], 4),
        frequency=round(aggregate["frequency"], 4),
        cpa=round(aggregate["cpa"], 4),
        wow_spend_delta=round(_safe_pct_delta(recent_sum["spend"], previous_sum["spend"]), 2),
        wow_ctr_delta=round(_safe_pct_delta(recent_sum["ctr"], previous_sum["ctr"]), 2),
        wow_roas_delta=round(_safe_pct_delta(recent_sum["roas"], previous_sum["roas"]), 2),
        wow_cpa_delta=round(_safe_pct_delta(recent_sum["cpa"], previous_sum["cpa"]), 2),
        daily_budget_total=round(sum(item.daily_budget or 0.0 for item in campaigns + adsets), 2),
        lifetime_budget_total=round(sum(item.lifetime_budget or 0.0 for item in campaigns + adsets), 2),
        objective_mix=_mix_from_counter(objective_counter),
        optimization_goal_mix=_mix_from_counter(optimization_counter),
        status_mix=_mix_from_counter(status_counter),
    )


def _score_response(score, findings_count: int) -> AuditScoreResponse:
    return AuditScoreResponse(
        id=score.id,
        score_key=score.score_key,
        label=score.label,
        name=score.label,
        score=score.score,
        weight=score.weight,
        description=score.details,
        details=score.details,
        findings_count=findings_count,
    )


def _finding_response(finding) -> AuditFindingResponse:
    return AuditFindingResponse(
        id=finding.id,
        rule_id=finding.rule_id,
        severity=finding.severity,
        category=finding.category,
        title=finding.title,
        description=finding.description,
        entity_type=finding.entity_type,
        entity_id=finding.entity_id,
        entity_name=finding.entity_name,
        affected_entity=finding.entity_name,
        affected_entity_id=finding.entity_id,
        metric_value=finding.metric_value,
        threshold_value=finding.threshold_value,
        estimated_waste=finding.estimated_waste,
        estimated_uplift=finding.estimated_uplift,
        recommendation_key=finding.recommendation_key,
        score_impact=finding.score_impact,
    )


def _ai_summary_response(summary, include_detailed: bool) -> AuditAISummaryResponse:
    detailed = summary.detailed_audit_explanation if include_detailed else "Upgrade to Premium to unlock detailed AI explanation."
    action_plan = summary.prioritized_action_plan if include_detailed else "Upgrade to Premium to unlock full prioritized action plan."
    return AuditAISummaryResponse(
        id=summary.id,
        audit_run_id=summary.audit_run_id,
        provider=summary.provider,
        model=summary.model,
        prompt_version=summary.prompt_version,
        status=summary.status,
        short_executive_summary=summary.short_executive_summary,
        detailed_audit_explanation=detailed,
        prioritized_action_plan=action_plan,
        error_message=summary.error_message,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
    )


def _serialize(run: AuditRun, entitlements: Entitlements) -> AuditRunResponse:
    findings_rows = [_finding_response(finding) for finding in run.findings][: entitlements.max_findings]
    rec_rows = [RecommendationResponse.model_validate(item) for item in run.recommendations][: entitlements.max_recommendations]
    score_rows = [_score_response(score, 0) for score in run.scores]
    return AuditRunResponse(
        id=run.id,
        health_score=run.health_score,
        total_spend=run.total_spend,
        total_wasted_spend=run.total_wasted_spend,
        total_estimated_uplift=run.total_estimated_uplift,
        findings_count=len(findings_rows),
        analysis_start=run.analysis_start,
        analysis_end=run.analysis_end,
        created_at=run.created_at,
        campaign_count=run.campaign_count,
        ad_set_count=run.ad_set_count,
        ad_count=run.ad_count,
        findings=findings_rows,
        scores=score_rows,
        pillar_scores=score_rows,
        recommendations=rec_rows,
        ai_summary=_ai_summary_response(run.ai_summary, entitlements.show_full_recommendations) if run.ai_summary else None,
    )


def _latest_run_query(db: Session, user_id: str):
    return (
        db.query(AuditRun)
        .options(
            selectinload(AuditRun.findings),
            selectinload(AuditRun.scores),
            selectinload(AuditRun.recommendations),
            selectinload(AuditRun.ai_summary),
        )
        .filter(AuditRun.user_id == user_id)
        .order_by(AuditRun.created_at.desc())
    )


def _get_run_for_user(db: Session, user_id: str, audit_run_id: str) -> AuditRun:
    run = (
        db.query(AuditRun)
        .options(
            selectinload(AuditRun.findings),
            selectinload(AuditRun.scores),
            selectinload(AuditRun.recommendations),
            selectinload(AuditRun.ai_summary),
        )
        .filter(AuditRun.id == audit_run_id, AuditRun.user_id == user_id)
        .first()
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Audit run not found", "code": "AUDIT_RUN_NOT_FOUND"},
        )
    return run


@router.post("/run", response_model=AuditRunResponse, status_code=status.HTTP_201_CREATED)
def run_new_audit(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entitlements = EntitlementService.get_entitlements(db, current_user.id)
    EntitlementService.enforce_report_quota(db, current_user.id, entitlements)

    account = _get_selected_account(db, current_user.id)
    run = run_audit(db, account.id, current_user.id)
    run = _latest_run_query(db, current_user.id).filter(AuditRun.id == run.id).first()
    return _serialize(run, entitlements)


@router.get("/latest", response_model=AuditRunResponse | None)
def get_latest_audit(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entitlements = EntitlementService.get_entitlements(db, current_user.id)
    run = _latest_run_query(db, current_user.id).first()
    if not run:
        return None
    return _serialize(run, entitlements)


@router.get("/latest/ai-summary", response_model=AuditAISummaryResponse | None)
def get_latest_ai_summary(
    auto_generate: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entitlements = EntitlementService.get_entitlements(db, current_user.id)
    run = _latest_run_query(db, current_user.id).first()
    if not run:
        return None

    if run.ai_summary and not auto_generate:
        return _ai_summary_response(run.ai_summary, entitlements.show_full_recommendations)

    summary = AISummaryService.generate_for_run(db, run, regenerate=False)
    return _ai_summary_response(summary, entitlements.show_full_recommendations)


@router.post("/latest/ai-summary/regenerate", response_model=AuditAISummaryResponse)
def regenerate_latest_ai_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entitlements = EntitlementService.get_entitlements(db, current_user.id)
    run = _latest_run_query(db, current_user.id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "No audit runs yet", "code": "AUDIT_RUN_NOT_FOUND"},
        )
    summary = AISummaryService.generate_for_run(db, run, regenerate=True)
    return _ai_summary_response(summary, entitlements.show_full_recommendations)


@router.get("/{audit_run_id}/ai-summary", response_model=AuditAISummaryResponse | None)
def get_ai_summary_for_run(
    audit_run_id: str,
    auto_generate: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entitlements = EntitlementService.get_entitlements(db, current_user.id)
    run = _get_run_for_user(db, current_user.id, audit_run_id)

    if run.ai_summary and not auto_generate:
        return _ai_summary_response(run.ai_summary, entitlements.show_full_recommendations)

    summary = AISummaryService.generate_for_run(db, run, regenerate=False)
    return _ai_summary_response(summary, entitlements.show_full_recommendations)


@router.post("/{audit_run_id}/ai-summary/regenerate", response_model=AuditAISummaryResponse)
def regenerate_ai_summary_for_run(audit_run_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entitlements = EntitlementService.get_entitlements(db, current_user.id)
    run = _get_run_for_user(db, current_user.id, audit_run_id)
    summary = AISummaryService.generate_for_run(db, run, regenerate=True)
    return _ai_summary_response(summary, entitlements.show_full_recommendations)


@router.get("/dashboard", response_model=AuditDashboardResponse)
def get_audit_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entitlements = EntitlementService.get_entitlements(db, current_user.id)
    account = _get_selected_account(db, current_user.id)
    snapshot = collect_account_data(db, account.id)
    run = _latest_run_query(db, current_user.id).first()
    audit = _serialize(run, entitlements) if run else None

    findings = audit.findings if audit else []
    severity_counts = SeverityCountResponse(
        critical=len([item for item in findings if item.severity == "critical"]),
        high=len([item for item in findings if item.severity == "high"]),
        medium=len([item for item in findings if item.severity == "medium"]),
        low=len([item for item in findings if item.severity == "low"]),
    )
    top_opportunities = sorted(findings, key=lambda item: item.estimated_uplift, reverse=True)[: entitlements.max_findings]
    kpis = _compute_account_kpis(db, account.id)

    trend: list[TrendPointResponse] = []
    trend_limit = entitlements.max_trend_points if entitlements.show_advanced_charts else min(entitlements.max_trend_points, 14)
    trend_rows = (
        db.query(DailyAccountInsight)
        .filter(DailyAccountInsight.ad_account_id == account.id)
        .order_by(DailyAccountInsight.date.desc())
        .limit(trend_limit)
        .all()
    )
    trend = [
        TrendPointResponse(label=row.date.strftime("%b %d"), spend=row.spend, roas=row.roas)
        for row in reversed(trend_rows)
    ]

    worst_campaigns = (
        db.query(Campaign, DailyCampaignInsight)
        .join(DailyCampaignInsight, DailyCampaignInsight.campaign_id == Campaign.id)
        .filter(Campaign.ad_account_id == account.id)
        .order_by(DailyCampaignInsight.roas.asc(), DailyCampaignInsight.spend.desc())
        .limit(5)
        .all()
    )
    worst_adsets = (
        db.query(AdSet, DailyAdSetInsight)
        .join(DailyAdSetInsight, DailyAdSetInsight.ad_set_id == AdSet.id)
        .filter(AdSet.ad_account_id == account.id)
        .order_by(DailyAdSetInsight.roas.asc(), DailyAdSetInsight.spend.desc())
        .limit(5)
        .all()
    )

    return AuditDashboardResponse(
        audit=audit,
        kpis=kpis,
        data_mode=snapshot.data_mode,
        limitations=snapshot.limitations,
        severity_counts=severity_counts,
        top_opportunities=top_opportunities,
        spend_roas_trend=trend,
        worst_campaigns=[
            LeaderboardItemResponse(
                entity_id=campaign.meta_campaign_id,
                entity_name=campaign.name,
                spend=insight.spend,
                roas=insight.roas,
                cpa=insight.spend / max(insight.conversions, 1) if insight.conversions > 0 else 0.0,
                ctr=insight.ctr,
            )
            for campaign, insight in worst_campaigns
        ],
        worst_adsets=[
            LeaderboardItemResponse(
                entity_id=adset.meta_adset_id,
                entity_name=adset.name,
                spend=insight.spend,
                roas=insight.roas,
                cpa=insight.spend / max(insight.conversions, 1) if insight.conversions > 0 else 0.0,
                ctr=insight.ctr,
            )
            for adset, insight in worst_adsets
        ],
    )


@router.get("/latest/findings", response_model=list[AuditFindingResponse])
def get_latest_findings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entitlements = EntitlementService.get_entitlements(db, current_user.id)
    run = _latest_run_query(db, current_user.id).first()
    if not run:
        return []
    return [_finding_response(finding) for finding in run.findings][: entitlements.max_findings]


@router.get("/latest/score", response_model=list[AuditScoreResponse])
def get_latest_score(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = _latest_run_query(db, current_user.id).first()
    if not run:
        return []
    return [_score_response(score, 0) for score in run.scores]


@router.get("/history", response_model=list[AuditSummaryResponse])
def get_audit_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=200),
):
    entitlements = EntitlementService.get_entitlements(db, current_user.id)
    capped_limit = min(limit, entitlements.max_history_items)
    runs = (
        db.query(AuditRun)
        .filter(AuditRun.user_id == current_user.id)
        .order_by(AuditRun.created_at.desc())
        .limit(capped_limit)
        .all()
    )
    return [AuditSummaryResponse.model_validate(run) for run in runs]
