from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.deps import get_current_user
from app.models.audit import AuditRun
from app.models.campaign import Ad, AdSet, Campaign, Creative
from app.models.insights import DailyAccountInsight, DailyAdInsight, DailyAdSetInsight, DailyCampaignInsight
from app.models.sync_job import SyncJob
from app.models.user import User
from app.services.meta_ads import MetaAdsService
from app.services.meta_auth import MetaAuthService
from app.schemas.audit import AuditSummaryResponse
from app.schemas.sync import SyncJobLogResponse, SyncJobResponse

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/jobs", response_model=list[SyncJobResponse])
def debug_jobs(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    jobs = (
        db.query(SyncJob)
        .filter(SyncJob.user_id == current_user.id)
        .order_by(SyncJob.created_at.desc())
        .limit(limit)
        .all()
    )
    return [SyncJobResponse.model_validate(job, from_attributes=True) for job in jobs]


@router.get("/jobs/{job_id}", response_model=SyncJobResponse)
def debug_job(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(SyncJob).filter(SyncJob.id == job_id, SyncJob.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    result = SyncJobResponse.model_validate(job, from_attributes=True)
    result.logs = [SyncJobLogResponse.model_validate(item, from_attributes=True) for item in job.logs]
    return result


@router.get("/audits", response_model=list[AuditSummaryResponse])
def debug_audits(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(AuditRun)
        .filter(AuditRun.user_id == current_user.id)
        .order_by(AuditRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return [AuditSummaryResponse.model_validate(item) for item in rows]


@router.get("/audits/{audit_run_id}", response_model=AuditSummaryResponse)
def debug_audit(audit_run_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(AuditRun).filter(AuditRun.id == audit_run_id, AuditRun.user_id == current_user.id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit run not found")
    return AuditSummaryResponse.model_validate(row)


@router.post("/reset-imported-data")
def reset_imported_data(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    connection = MetaAuthService.get_connection(db, current_user.id)
    if connection is None:
        return {"status": "ok", "message": "No connection to reset"}

    selected = MetaAdsService.get_selected_account(db, connection.id)
    if selected is None:
        return {"status": "ok", "message": "No selected ad account to reset"}

    account_id = selected.id
    db.query(DailyAdInsight).filter(DailyAdInsight.ad_account_id == account_id).delete()
    db.query(DailyAdSetInsight).filter(DailyAdSetInsight.ad_account_id == account_id).delete()
    db.query(DailyCampaignInsight).filter(DailyCampaignInsight.ad_account_id == account_id).delete()
    db.query(DailyAccountInsight).filter(DailyAccountInsight.ad_account_id == account_id).delete()
    db.query(Ad).filter(Ad.ad_account_id == account_id).delete()
    db.query(AdSet).filter(AdSet.ad_account_id == account_id).delete()
    db.query(Campaign).filter(Campaign.ad_account_id == account_id).delete()
    db.query(Creative).filter(Creative.ad_account_id == account_id).delete()
    db.query(AuditRun).filter(AuditRun.user_id == current_user.id, AuditRun.ad_account_id == account_id).delete()
    db.query(SyncJob).filter(SyncJob.user_id == current_user.id, SyncJob.ad_account_id == account_id).delete()
    db.commit()
    return {"status": "ok", "message": "Imported data and related audits were reset"}
