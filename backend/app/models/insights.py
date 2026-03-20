import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InsightMetricsMixin:
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    spend: Mapped[float] = mapped_column(Float, default=0.0)
    reach: Mapped[int] = mapped_column(Integer, default=0)
    ctr: Mapped[float] = mapped_column(Float, default=0.0)
    cpc: Mapped[float] = mapped_column(Float, default=0.0)
    cpm: Mapped[float] = mapped_column(Float, default=0.0)
    frequency: Mapped[float] = mapped_column(Float, default=0.0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    conversion_value: Mapped[float] = mapped_column(Float, default=0.0)
    roas: Mapped[float] = mapped_column(Float, default=0.0)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DailyAccountInsight(Base, InsightMetricsMixin):
    __tablename__ = "insights_daily_account"
    __table_args__ = (UniqueConstraint("ad_account_id", "date", name="uq_insights_daily_account_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ad_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meta_ad_accounts.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)


class DailyCampaignInsight(Base, InsightMetricsMixin):
    __tablename__ = "insights_daily_campaign"
    __table_args__ = (UniqueConstraint("campaign_id", "date", name="uq_insights_daily_campaign_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ad_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meta_ad_accounts.id", ondelete="CASCADE"), index=True
    )
    campaign_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="daily_insights")


class DailyAdSetInsight(Base, InsightMetricsMixin):
    __tablename__ = "insights_daily_adset"
    __table_args__ = (UniqueConstraint("ad_set_id", "date", name="uq_insights_daily_adset_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ad_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meta_ad_accounts.id", ondelete="CASCADE"), index=True
    )
    ad_set_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ad_sets.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)

    ad_set: Mapped["AdSet"] = relationship("AdSet", back_populates="daily_insights")


class DailyAdInsight(Base, InsightMetricsMixin):
    __tablename__ = "insights_daily_ad"
    __table_args__ = (UniqueConstraint("ad_id", "date", name="uq_insights_daily_ad_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ad_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meta_ad_accounts.id", ondelete="CASCADE"), index=True
    )
    ad_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ads.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)

    ad: Mapped["Ad"] = relationship("Ad", back_populates="daily_insights")


DailyInsight = DailyCampaignInsight

from app.models.campaign import Ad, AdSet, Campaign  # noqa: E402
