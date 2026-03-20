from datetime import datetime

import sentry_sdk

from app.celery_app import celery
from app.database import SessionLocal
from app.engine.orchestrator import populate_audit_run
from app.logging_config import get_logger
from app.models.audit import AuditRun
from app.services.ai_summary import AISummaryService

logger = get_logger(__name__)


@celery.task(bind=True, name="audit.run_audit_job", max_retries=1, default_retry_delay=15)
def run_audit_job(self, audit_run_id: str) -> None:
    _run_audit_job(audit_run_id, self.request.id or "")


def _run_audit_job(audit_run_id: str, task_id: str) -> None:
    db = SessionLocal()
    try:
        run = db.query(AuditRun).filter(AuditRun.id == audit_run_id).first()
        if run is None:
            logger.error("audit.job_not_found", extra={"audit_run_id": audit_run_id, "task_id": task_id})
            return

        run.job_status = "running"
        run.job_error = None
        run.celery_task_id = task_id
        db.commit()
        logger.info(
            "audit.job_running",
            extra={"audit_run_id": audit_run_id, "task_id": task_id, "user_id": run.user_id, "code": "AUDIT_RUNNING"},
        )

        populate_audit_run(db, run)
        run = db.query(AuditRun).filter(AuditRun.id == audit_run_id).first()
        if run is None:
            return

        AISummaryService.generate_for_run(db, run, regenerate=True)
        run.job_status = "completed"
        run.job_error = None
        db.commit()
        logger.info("audit.completed", extra={"audit_run_id": run.id, "task_id": task_id, "user_id": run.user_id, "code": "AUDIT_COMPLETED"})
    except Exception as exc:
        sentry_sdk.capture_exception(exc)
        logger.exception("audit.failed", extra={"audit_run_id": audit_run_id, "task_id": task_id, "code": "AUDIT_FAILED"})
        run = db.query(AuditRun).filter(AuditRun.id == audit_run_id).first()
        if run is not None:
            run.job_status = "failed"
            run.job_error = str(exc)[:2000]
            db.commit()
        raise
    finally:
        db.close()
