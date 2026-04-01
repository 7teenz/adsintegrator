from datetime import datetime, time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.logging_config import get_logger
from app.middleware.deps import get_current_user
from app.models.campaign import Ad, AdSet, Campaign, Creative
from app.models.insights import DailyAccountInsight, DailyAdInsight, DailyAdSetInsight, DailyCampaignInsight
from app.models.sync_job import SyncJob
from app.models.user import User
from app.schemas.sync import ReportImportResponse, SyncDataSummary, SyncJobResponse, SyncStartRequest, SyncStartResponse
from app.services.csv_import import CsvImportService
from app.services.meta_ads import MetaAdsService
from app.services.meta_auth import MetaAuthService
from app.services.rate_limit import enforce_rate_limit
from app.tasks.sync import run_incremental_sync_job, run_initial_sync_job
from app.routes.helpers import get_selected_account as _get_selected_account

router = APIRouter(prefix="/sync", tags=["sync"])
settings = get_settings()
logger = get_logger(__name__)


def _serialize_job(job: SyncJob | None) -> SyncJobResponse | None:
    if job is None:
        return None
    return SyncJobResponse.model_validate(job, from_attributes=True)


@router.post("/start", response_model=SyncStartResponse, status_code=status.HTTP_202_ACCEPTED)
def start_sync(
    request: Request,
    payload: SyncStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, "sync:start", 6, 3600, user_id=current_user.id)
    account = _get_selected_account(db, current_user.id)

    running = (
        db.query(SyncJob)
        .filter(SyncJob.user_id == current_user.id, SyncJob.status.in_(["pending", "running"]))
        .order_by(SyncJob.created_at.desc())
        .first()
    )
    if running:
        return SyncStartResponse(job=_serialize_job(running), message="A sync is already in progress")

    job = SyncJob(user_id=current_user.id, ad_account_id=account.id, sync_type=payload.sync_type, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    async_result = run_initial_sync_job.delay(job.id) if payload.sync_type == "initial" else run_incremental_sync_job.delay(job.id)
    job.celery_task_id = async_result.id
    db.commit()
    db.refresh(job)

    return SyncStartResponse(job=_serialize_job(job), message=f"{payload.sync_type.title()} sync started")


@router.get("/status", response_model=SyncJobResponse | None)
def get_sync_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = (
        db.query(SyncJob)
        .filter(SyncJob.user_id == current_user.id)
        .order_by(SyncJob.created_at.desc())
        .first()
    )
    return _serialize_job(job)


@router.get("/history", response_model=list[SyncJobResponse])
def get_sync_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
):
    jobs = (
        db.query(SyncJob)
        .filter(SyncJob.user_id == current_user.id)
        .order_by(SyncJob.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_serialize_job(job) for job in jobs]


@router.get("/summary", response_model=SyncDataSummary)
def get_data_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        account = _get_selected_account(db, current_user.id)
    except HTTPException:
        return SyncDataSummary(
            campaigns=0,
            ad_sets=0,
            ads=0,
            creatives=0,
            account_insight_rows=0,
            campaign_insight_rows=0,
            adset_insight_rows=0,
            ad_insight_rows=0,
            sync_state="pending",
            last_sync=None,
        )

    campaigns = db.query(Campaign).filter(Campaign.ad_account_id == account.id).count()
    ad_sets = db.query(AdSet).filter(AdSet.ad_account_id == account.id).count()
    ads = db.query(Ad).filter(Ad.ad_account_id == account.id).count()
    creatives = db.query(Creative).filter(Creative.ad_account_id == account.id).count()
    account_rows = db.query(DailyAccountInsight).filter(DailyAccountInsight.ad_account_id == account.id).count()
    campaign_rows = db.query(DailyCampaignInsight).filter(DailyCampaignInsight.ad_account_id == account.id).count()
    adset_rows = db.query(DailyAdSetInsight).filter(DailyAdSetInsight.ad_account_id == account.id).count()
    ad_rows = db.query(DailyAdInsight).filter(DailyAdInsight.ad_account_id == account.id).count()

    last_job = (
        db.query(SyncJob)
        .filter(SyncJob.user_id == current_user.id)
        .order_by(SyncJob.created_at.desc())
        .first()
    )

    sync_state = "pending"
    if last_job is not None:
        sync_state = last_job.status
    elif campaigns or campaign_rows:
        sync_state = "completed"

    return SyncDataSummary(
        campaigns=campaigns,
        ad_sets=ad_sets,
        ads=ads,
        creatives=creatives,
        account_insight_rows=account_rows,
        campaign_insight_rows=campaign_rows,
        adset_insight_rows=adset_rows,
        ad_insight_rows=ad_rows,
        sync_state=sync_state,
        last_sync=_serialize_job(last_job),
    )


def _serialize_import_result(result, replace_existing: bool) -> ReportImportResponse:
    return ReportImportResponse(
        campaigns=result.campaigns,
        ad_sets=result.ad_sets,
        ads=result.ads,
        insight_rows=result.insight_rows,
        date_start=datetime.combine(result.date_start, time.min) if result.date_start else None,
        date_end=datetime.combine(result.date_end, time.min) if result.date_end else None,
        replaced_existing=replace_existing,
        report_type=result.report_type,
        source_sheet=result.source_sheet,
        warnings=result.warnings,
    )


@router.post("/import-report", response_model=ReportImportResponse)
async def import_report_history(
    request: Request,
    file: UploadFile = File(...),
    replace_existing: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(
        request,
        "sync:import_report",
        settings.rate_limit_upload_requests,
        settings.rate_limit_upload_window_seconds,
        user_id=current_user.id,
    )
    content = await file.read()
    try:
        result = CsvImportService.import_report(
            db=db,
            user=current_user,
            filename=file.filename or "upload.csv",
            content_bytes=content,
            replace_existing=replace_existing,
        )
    except Exception:
        logger.exception(
            "sync.import_failed",
            extra={"request_id": getattr(request.state, "request_id", None), "user_id": current_user.id, "code": "SYNC_IMPORT_FAILED"},
        )
        raise
    return _serialize_import_result(result, replace_existing)


