import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        UniqueConstraint("ad_account_id", "meta_campaign_id", name="uq_campaign_account_meta"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ad_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meta_ad_accounts.id", ondelete="CASCADE"), index=True
    )
    meta_campaign_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    objective: Mapped[str | None] = mapped_column(String(128), nullable=True)
    buying_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    daily_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    lifetime_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_created_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_updated_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ad_sets: Mapped[list["AdSet"]] = relationship(
        "AdSet", back_populates="campaign", cascade="all, delete-orphan"
    )
    daily_insights: Mapped[list["DailyCampaignInsight"]] = relationship(
        "DailyCampaignInsight", back_populates="campaign", cascade="all, delete-orphan"
    )


class AdSet(Base):
    __tablename__ = "ad_sets"
    __table_args__ = (
        UniqueConstraint("ad_account_id", "meta_adset_id", name="uq_adset_account_meta"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    ad_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meta_ad_accounts.id", ondelete="CASCADE"), index=True
    )
    meta_adset_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    meta_campaign_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    targeting_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    optimization_goal: Mapped[str | None] = mapped_column(String(128), nullable=True)
    billing_event: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bid_strategy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    daily_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    lifetime_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_created_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_updated_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="ad_sets")
    ads: Mapped[list["Ad"]] = relationship(
        "Ad", back_populates="ad_set", cascade="all, delete-orphan"
    )
    daily_insights: Mapped[list["DailyAdSetInsight"]] = relationship(
        "DailyAdSetInsight", back_populates="ad_set", cascade="all, delete-orphan"
    )


class Creative(Base):
    __tablename__ = "creatives"
    __table_args__ = (
        UniqueConstraint("ad_account_id", "meta_creative_id", name="uq_creative_account_meta"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ad_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meta_ad_accounts.id", ondelete="CASCADE"), index=True
    )
    meta_creative_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_object_story_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    object_story_spec_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_feed_spec_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ads: Mapped[list["Ad"]] = relationship("Ad", back_populates="creative")


class Ad(Base):
    __tablename__ = "ads"
    __table_args__ = (
        UniqueConstraint("ad_account_id", "meta_ad_id", name="uq_ad_account_meta"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ad_set_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ad_sets.id", ondelete="CASCADE"), index=True
    )
    ad_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meta_ad_accounts.id", ondelete="CASCADE"), index=True
    )
    creative_pk: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("creatives.id", ondelete="SET NULL"), nullable=True, index=True
    )
    meta_ad_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    meta_adset_id: Mapped[str] = mapped_column(String(64), nullable=False)
    meta_creative_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_created_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_updated_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ad_set: Mapped["AdSet"] = relationship("AdSet", back_populates="ads")
    creative: Mapped["Creative | None"] = relationship("Creative", back_populates="ads")
    daily_insights: Mapped[list["DailyAdInsight"]] = relationship(
        "DailyAdInsight", back_populates="ad", cascade="all, delete-orphan"
    )


from app.models.insights import DailyAdInsight, DailyAdSetInsight, DailyCampaignInsight  # noqa: E402
