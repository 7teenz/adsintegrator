from datetime import datetime, timezone

import httpx

from app.celery_app import celery
from app.config import get_settings
from app.database import SessionLocal
from app.logging_config import get_logger
from app.models.sync_job import SyncJob
from app.services.meta_sync import MetaSyncOrchestrator

logger = get_logger(__name__)
settings = get_settings()
MOCK_MODE = settings.meta_app_id == "mock"


def _start_job(db, job: SyncJob, task_id: str, step: str) -> None:
    job.celery_task_id = task_id
    job.status = "running"
    job.progress = 1
    job.current_step = step
    job.started_at = datetime.now(timezone.utc)
    job.updated_at = datetime.now(timezone.utc)
    db.commit()


@celery.task(bind=True, name="sync.run_initial_sync_job", max_retries=2, default_retry_delay=30)
def run_initial_sync_job(self, sync_job_id: str):
    _run_job(self, sync_job_id, "initial")


@celery.task(bind=True, name="sync.run_incremental_sync_job", max_retries=2, default_retry_delay=30)
def run_incremental_sync_job(self, sync_job_id: str):
    _run_job(self, sync_job_id, "incremental")


def _is_retryable_error(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.RequestError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or code >= 500
    return False


def _run_job(task, sync_job_id: str, sync_type: str) -> None:
    db = SessionLocal()
    try:
        job = db.query(SyncJob).filter(SyncJob.id == sync_job_id).first()
        if job is None:
            logger.error("sync.job_not_found", extra={"job_id": sync_job_id, "task_id": task.request.id})
            return

        _start_job(db, job, task.request.id or "", f"Preparing {sync_type} sync")
        MetaSyncOrchestrator.log(db, job, f"Starting {sync_type} sync")

        mock_payload = None
        if MOCK_MODE:
            from app.services.meta_mock import generate_mock_sync_payload

            mock_payload = generate_mock_sync_payload()

        MetaSyncOrchestrator.run(db, job, mock_payload=mock_payload)
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(
            "sync.completed",
            extra={"job_id": job.id, "task_id": task.request.id, "user_id": job.user_id, "code": "SYNC_COMPLETED"},
        )
    except Exception as exc:
        logger.exception(
            "sync.failed",
            extra={"job_id": sync_job_id, "task_id": task.request.id, "code": "SYNC_FAILED"},
        )
        job = db.query(SyncJob).filter(SyncJob.id == sync_job_id).first()
        if job is not None:
            job.error_message = str(exc)[:2000]
            job.current_step = "Sync failed"
            job.updated_at = datetime.now(timezone.utc)
            if _is_retryable_error(exc) and task.request.retries < task.max_retries:
                job.status = "retrying"
                db.commit()
                MetaSyncOrchestrator.log(db, job, f"Retrying sync ({task.request.retries + 1}/{task.max_retries})", level="warning")
                logger.warning(
                    "sync.retrying",
                    extra={"job_id": job.id, "task_id": task.request.id, "user_id": job.user_id, "code": "SYNC_RETRYING"},
                )
                raise task.retry(exc=exc, countdown=min(30 * (task.request.retries + 1), 120))
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            MetaSyncOrchestrator.log(db, job, job.error_message or "Sync failed", level="error")
        raise
    finally:
        db.close()
