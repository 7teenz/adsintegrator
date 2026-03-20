import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AuditRun(Base):
    __tablename__ = "audit_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    ad_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("meta_ad_accounts.id", ondelete="CASCADE"), index=True)
    health_score: Mapped[float] = mapped_column(Float, nullable=False)
    total_spend: Mapped[float] = mapped_column(Float, default=0.0)
    total_wasted_spend: Mapped[float] = mapped_column(Float, default=0.0)
    total_estimated_uplift: Mapped[float] = mapped_column(Float, default=0.0)
    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    campaign_count: Mapped[int] = mapped_column(Integer, default=0)
    ad_set_count: Mapped[int] = mapped_column(Integer, default=0)
    ad_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    analysis_start: Mapped[date] = mapped_column(Date, nullable=False)
    analysis_end: Mapped[date] = mapped_column(Date, nullable=False)

    findings: Mapped[list["AuditFinding"]] = relationship("AuditFinding", back_populates="audit_run", cascade="all, delete-orphan")
    scores: Mapped[list["AuditScore"]] = relationship("AuditScore", back_populates="audit_run", cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship("Recommendation", back_populates="audit_run", cascade="all, delete-orphan")
    ai_summary: Mapped["AuditAISummary | None"] = relationship(
        "AuditAISummary",
        back_populates="audit_run",
        uselist=False,
        cascade="all, delete-orphan",
    )


class AuditFinding(Base):
    __tablename__ = "audit_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    audit_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit_runs.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_waste: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_uplift: Mapped[float] = mapped_column(Float, default=0.0)
    recommendation_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    score_impact: Mapped[float] = mapped_column(Float, default=0.0)

    audit_run: Mapped["AuditRun"] = relationship("AuditRun", back_populates="findings")


class AuditScore(Base):
    __tablename__ = "audit_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    audit_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit_runs.id", ondelete="CASCADE"), index=True)
    score_key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)

    audit_run: Mapped["AuditRun"] = relationship("AuditRun", back_populates="scores")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    audit_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit_runs.id", ondelete="CASCADE"), index=True)
    audit_finding_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("audit_findings.id", ondelete="SET NULL"), nullable=True, index=True)
    recommendation_key: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    audit_run: Mapped["AuditRun"] = relationship("AuditRun", back_populates="recommendations")


class AuditAISummary(Base):
    __tablename__ = "audit_ai_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    audit_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit_runs.id", ondelete="CASCADE"), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="completed")
    short_executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    detailed_audit_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    prioritized_action_plan: Mapped[str] = mapped_column(Text, nullable=False)
    input_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    audit_run: Mapped["AuditRun"] = relationship("AuditRun", back_populates="ai_summary")
