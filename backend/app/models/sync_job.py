import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    ad_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meta_ad_accounts.id", ondelete="CASCADE"), index=True
    )
    sync_type: Mapped[str] = mapped_column(String(20), default="initial")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[str | None] = mapped_column(String(255), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    campaigns_synced: Mapped[int] = mapped_column(Integer, default=0)
    ad_sets_synced: Mapped[int] = mapped_column(Integer, default=0)
    ads_synced: Mapped[int] = mapped_column(Integer, default=0)
    creatives_synced: Mapped[int] = mapped_column(Integer, default=0)
    insights_account_synced: Mapped[int] = mapped_column(Integer, default=0)
    insights_campaign_synced: Mapped[int] = mapped_column(Integer, default=0)
    insights_adset_synced: Mapped[int] = mapped_column(Integer, default=0)
    insights_ad_synced: Mapped[int] = mapped_column(Integer, default=0)

    window_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_successful_cursor: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    logs: Mapped[list["SyncJobLog"]] = relationship(
        "SyncJobLog", back_populates="job", cascade="all, delete-orphan"
    )


class SyncJobLog(Base):
    __tablename__ = "sync_job_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sync_job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sync_jobs.id", ondelete="CASCADE"), index=True
    )
    level: Mapped[str] = mapped_column(String(16), default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["SyncJob"] = relationship("SyncJob", back_populates="logs")
