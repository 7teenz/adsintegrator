from datetime import datetime, timezone
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.database import get_db
from app.engine.collector import collect_account_data
from app.engine.scoring import PILLARS
from app.logging_config import get_logger
from app.middleware.deps import get_current_user
from app.models.audit import AuditRun
from app.models.campaign import AdSet, Campaign
from app.models.insights import DailyAccountInsight, DailyAdSetInsight, DailyCampaignInsight
from app.models.user import User
from app.schemas.audit import (
    AuditAISummaryResponse,
    AuditDashboardResponse,
    AuditJobResponse,
    AuditJobStatusResponse,
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
from app.services.rate_limit import enforce_rate_limit
from app.tasks.audit import run_audit_job
from app.routes.helpers import get_selected_account as _get_selected_account

router = APIRouter(prefix="/audit", tags=["audit"])
settings = get_settings()
logger = get_logger(__name__)


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
        strongest_issue=None,
    )


def _derive_finding_confidence(finding, run: AuditRun) -> tuple[str, str]:
    analysis_days = max(1, (run.analysis_end - run.analysis_start).days + 1)
    total_spend = run.total_spend or 0.0

    if analysis_days <= 3:
        return "Low", "The analysis window is very short, so treat this as an early warning signal."
    if total_spend < 150 and finding.estimated_waste == 0 and finding.estimated_uplift == 0:
        return "Low", "Spend is light, so the issue is real but dollar impact cannot be modeled confidently yet."
    if finding.metric_value is None:
        return "Medium", "The signal is structurally meaningful, but it is based on broader account context rather than one direct threshold."
    if analysis_days >= 30 and total_spend >= 1000:
        return "High", "This finding is backed by a longer dataset with enough spend to treat it as decision-grade."
    if analysis_days >= 14 and total_spend >= 300:
        return "Medium", "The signal is directionally reliable, but more history or spend would make it stronger."
    return "Low", "The issue is worth investigating, but the current dataset is still relatively sparse."


def _derive_inspection_target(finding) -> str:
    category = (finding.category or "").lower()
    key = (finding.recommendation_key or "").lower()
    title = f"{finding.title} {finding.description}".lower()

    if "conversion" in title or "tracking" in key or "cpa" in category:
        return "Inspect conversion tracking, landing-page continuity, and the post-click funnel first."
    if "frequency" in category or "fatigue" in title:
        return "Inspect creative rotation, audience overlap, and fatigue across the affected ad sets."
    if "ctr" in category or "click" in title:
        return "Inspect creative hooks, audience targeting, and offer-message fit."
    if "budget" in category or "spend" in category:
        return "Inspect budget allocation, sibling efficiency, and whether spend is concentrated in weak segments."
    if "structure" in category or "placement" in category:
        return "Inspect campaign naming, segmentation logic, placement mix, and optimization settings."
    return "Inspect the affected entity in Ads Manager and compare the weak metric against nearby peers before changing budget."


def _finding_response(finding, run: AuditRun) -> AuditFindingResponse:
    confidence_label, confidence_reason = _derive_finding_confidence(finding, run)
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
        confidence_label=confidence_label,
        confidence_reason=confidence_reason,
        inspection_target=_derive_inspection_target(finding),
    )


def _ai_summary_response(summary, include_detailed: bool = True) -> AuditAISummaryResponse:
    detailed = summary.detailed_audit_explanation
    action_plan = summary.prioritized_action_plan
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
    findings_rows = [_finding_response(finding, run) for finding in run.findings]
    rec_rows = [RecommendationResponse.model_validate(item) for item in run.recommendations]
    finding_map = {score_key: [] for score_key in PILLARS}
    for finding in run.findings:
        for score_key, (_, _, categories) in PILLARS.items():
            if finding.category in {category.value for category in categories}:
                finding_map[score_key].append(finding)
    score_rows = [
        AuditScoreResponse(
            id=score.id,
            score_key=score.score_key,
            label=score.label,
            name=score.label,
            score=score.score,
            weight=score.weight,
            description=score.details,
            details=score.details,
            findings_count=len(finding_map.get(score.score_key, [])),
            strongest_issue=(finding_map.get(score.score_key) or [None])[0].title if finding_map.get(score.score_key) else None,
        )
        for score in run.scores
    ]
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
        ai_summary=_ai_summary_response(run.ai_summary) if run.ai_summary else None,
        job_status=run.job_status,
        job_error=run.job_error,
        celery_task_id=run.celery_task_id,
    )


def _base_run_query(db: Session, user_id: str):
    return (
        db.query(AuditRun)
        .options(
            selectinload(AuditRun.findings),
            selectinload(AuditRun.scores),
            selectinload(AuditRun.recommendations),
            selectinload(AuditRun.ai_summary),
        )
        .filter(AuditRun.user_id == user_id)
    )


def _latest_completed_run_query(db: Session, user_id: str):
    return _base_run_query(db, user_id).filter(AuditRun.job_status == "completed").order_by(AuditRun.created_at.desc())


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


@router.post("/run", response_model=AuditJobResponse, status_code=status.HTTP_201_CREATED)
def run_new_audit(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_rate_limit(
        request,
        "audit:run",
        settings.rate_limit_audit_requests,
        settings.rate_limit_audit_window_seconds,
        user_id=current_user.id,
    )
    account = _get_selected_account(db, current_user.id)
    now = datetime.now(timezone.utc).date()
    run = AuditRun(
        user_id=current_user.id,
        ad_account_id=account.id,
        health_score=0.0,
        total_spend=0.0,
        total_wasted_spend=0.0,
        total_estimated_uplift=0.0,
        findings_count=0,
        campaign_count=0,
        ad_set_count=0,
        ad_count=0,
        analysis_start=now,
        analysis_end=now,
        job_status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    task = run_audit_job.delay(run.id)
    run.celery_task_id = task.id
    db.commit()
    logger.info(
        "audit.started",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "user_id": current_user.id,
            "audit_run_id": run.id,
            "task_id": task.id,
            "code": "AUDIT_STARTED",
        },
    )
    return AuditJobResponse(job_id=run.id, status=run.job_status)


@router.get("/job/{job_id}", response_model=AuditJobStatusResponse)
def get_audit_job_status(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = (
        db.query(AuditRun)
        .filter(AuditRun.id == job_id, AuditRun.user_id == current_user.id)
        .first()
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Audit job not found", "code": "AUDIT_JOB_NOT_FOUND"},
        )
    return AuditJobStatusResponse(
        job_id=run.id,
        status=run.job_status,
        error=run.job_error,
        completed_audit_id=run.id if run.job_status == "completed" else None,
    )


@router.get("/latest", response_model=AuditRunResponse | None)
def get_latest_audit(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = _latest_completed_run_query(db, current_user.id).first()
    if not run:
        return None
    entitlements = EntitlementService.get_entitlements(db, current_user.id)
    return _serialize(run, entitlements)


@router.get("/latest/ai-summary", response_model=AuditAISummaryResponse | None)
def get_latest_ai_summary(
    auto_generate: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entitlements = EntitlementService.get_entitlements(db, current_user.id)
    run = _latest_completed_run_query(db, current_user.id).first()
    if not run:
        return None

    if run.ai_summary and not auto_generate:
        return _ai_summary_response(run.ai_summary)

    summary = AISummaryService.generate_for_run(db, run, regenerate=False)
    return _ai_summary_response(summary)


@router.post("/latest/ai-summary/regenerate", response_model=AuditAISummaryResponse)
def regenerate_latest_ai_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = _latest_completed_run_query(db, current_user.id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "No audit runs yet", "code": "AUDIT_RUN_NOT_FOUND"},
        )
    summary = AISummaryService.generate_for_run(db, run, regenerate=True)
    return _ai_summary_response(summary)


@router.get("/{audit_run_id}/ai-summary", response_model=AuditAISummaryResponse | None)
def get_ai_summary_for_run(
    audit_run_id: str,
    auto_generate: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    run = _get_run_for_user(db, current_user.id, audit_run_id)

    if run.ai_summary and not auto_generate:
        return _ai_summary_response(run.ai_summary)

    summary = AISummaryService.generate_for_run(db, run, regenerate=False)
    return _ai_summary_response(summary)


@router.post("/{audit_run_id}/ai-summary/regenerate", response_model=AuditAISummaryResponse)
def regenerate_ai_summary_for_run(audit_run_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = _get_run_for_user(db, current_user.id, audit_run_id)
    summary = AISummaryService.generate_for_run(db, run, regenerate=True)
    return _ai_summary_response(summary)


@router.get("/dashboard", response_model=AuditDashboardResponse)
def get_audit_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entitlements = EntitlementService.get_entitlements(db, current_user.id)
    account = _get_selected_account(db, current_user.id)
    snapshot = collect_account_data(db, account.id)
    run = _latest_completed_run_query(db, current_user.id).first()
    audit = _serialize(run, entitlements) if run else None

    findings = audit.findings if audit else []
    severity_counts = SeverityCountResponse(
        critical=len([item for item in findings if item.severity == "critical"]),
        high=len([item for item in findings if item.severity == "high"]),
        medium=len([item for item in findings if item.severity == "medium"]),
        low=len([item for item in findings if item.severity == "low"]),
    )
    top_opportunities = sorted(findings, key=lambda item: item.estimated_uplift, reverse=True)[:5]
    kpis = _compute_account_kpis(db, account.id)

    trend: list[TrendPointResponse] = []
    trend_limit = 30
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

    campaign_agg = (
        db.query(
            DailyCampaignInsight.campaign_id,
            func.sum(DailyCampaignInsight.spend).label("total_spend"),
            func.avg(DailyCampaignInsight.roas).label("avg_roas"),
            func.sum(DailyCampaignInsight.conversions).label("total_conversions"),
            func.avg(DailyCampaignInsight.ctr).label("avg_ctr"),
        )
        .group_by(DailyCampaignInsight.campaign_id)
        .subquery()
    )
    worst_campaigns = (
        db.query(Campaign, campaign_agg)
        .join(campaign_agg, campaign_agg.c.campaign_id == Campaign.id)
        .filter(Campaign.ad_account_id == account.id)
        .order_by(campaign_agg.c.avg_roas.asc(), campaign_agg.c.total_spend.desc())
        .limit(5)
        .all()
    )

    adset_agg = (
        db.query(
            DailyAdSetInsight.ad_set_id,
            func.sum(DailyAdSetInsight.spend).label("total_spend"),
            func.avg(DailyAdSetInsight.roas).label("avg_roas"),
            func.sum(DailyAdSetInsight.conversions).label("total_conversions"),
            func.avg(DailyAdSetInsight.ctr).label("avg_ctr"),
        )
        .group_by(DailyAdSetInsight.ad_set_id)
        .subquery()
    )
    worst_adsets = (
        db.query(AdSet, adset_agg)
        .join(adset_agg, adset_agg.c.ad_set_id == AdSet.id)
        .filter(AdSet.ad_account_id == account.id)
        .order_by(adset_agg.c.avg_roas.asc(), adset_agg.c.total_spend.desc())
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
                spend=float(agg.total_spend or 0),
                roas=float(agg.avg_roas or 0),
                cpa=float(agg.total_spend or 0) / max(int(agg.total_conversions or 0), 1) if (agg.total_conversions or 0) > 0 else 0.0,
                ctr=float(agg.avg_ctr or 0),
            )
            for campaign, agg in worst_campaigns
        ],
        worst_adsets=[
            LeaderboardItemResponse(
                entity_id=adset.meta_adset_id,
                entity_name=adset.name,
                spend=float(agg.total_spend or 0),
                roas=float(agg.avg_roas or 0),
                cpa=float(agg.total_spend or 0) / max(int(agg.total_conversions or 0), 1) if (agg.total_conversions or 0) > 0 else 0.0,
                ctr=float(agg.avg_ctr or 0),
            )
            for adset, agg in worst_adsets
        ],
    )


@router.get("/latest/findings", response_model=list[AuditFindingResponse])
def get_latest_findings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = _latest_completed_run_query(db, current_user.id).first()
    if not run:
        return []
    return [_finding_response(finding, run) for finding in run.findings]


@router.get("/latest/score", response_model=list[AuditScoreResponse])
def get_latest_score(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = _latest_completed_run_query(db, current_user.id).first()
    if not run:
        return []
    return _serialize(run, EntitlementService.get_entitlements(db, current_user.id)).scores


@router.get("/history", response_model=list[AuditSummaryResponse])
def get_audit_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=200),
):
    capped_limit = min(limit, 50)
    runs = (
        db.query(AuditRun)
        .filter(AuditRun.user_id == current_user.id, AuditRun.job_status == "completed")
        .order_by(AuditRun.created_at.desc())
        .limit(capped_limit)
        .all()
    )
    return [AuditSummaryResponse.model_validate(run) for run in runs]
