from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.audit import AuditRun
from app.models.meta_connection import MetaConnection
from app.models.sync_job import SyncJob
from app.models.user import User


@dataclass
class CleanupSummary:
    message: str


class AccountCleanupService:
    @staticmethod
    def clear_user_data(db: Session, user: User) -> CleanupSummary:
        connection = db.query(MetaConnection).filter(MetaConnection.user_id == user.id).first()
        if connection is not None:
            db.delete(connection)

        db.query(AuditRun).filter(AuditRun.user_id == user.id).delete()
        db.query(SyncJob).filter(SyncJob.user_id == user.id).delete()
        db.commit()
        return CleanupSummary(message="Imported data, connected Meta accounts, sync history, and audits were deleted.")

    @staticmethod
    def delete_user_account(db: Session, user: User) -> CleanupSummary:
        db.delete(user)
        db.commit()
        return CleanupSummary(message="Your account and all related data were deleted.")
