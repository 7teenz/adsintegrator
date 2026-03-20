from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.subscription import Subscription

settings = get_settings()


@dataclass
class Entitlements:
    plan_tier: str
    max_ad_accounts: int
    max_findings: int
    max_recommendations: int
    max_history_items: int
    max_trend_points: int
    max_reports_per_month: int
    show_advanced_charts: bool
    show_recurring_monitoring: bool
    show_full_recommendations: bool

    @property
    def is_premium(self) -> bool:
        return self.plan_tier in {"premium", "agency"}


class EntitlementService:
    @staticmethod
    def get_reports_used_last_30_days(db: Session, user_id: str) -> int:
        from app.models.audit import AuditRun

        since = datetime.utcnow() - timedelta(days=30)
        return (
            db.query(AuditRun)
            .filter(AuditRun.user_id == user_id, AuditRun.created_at >= since)
            .count()
        )

    @staticmethod
    def get_or_create_subscription(db: Session, user_id: str) -> Subscription:
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if subscription is None:
            subscription = Subscription(user_id=user_id, plan_tier="free", status="active")
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
        return subscription

    @classmethod
    def get_entitlements(cls, db: Session, user_id: str) -> Entitlements:
        if settings.debug:
            return Entitlements(
                plan_tier="premium",
                max_ad_accounts=50,
                max_findings=1000,
                max_recommendations=1000,
                max_history_items=200,
                max_trend_points=365,
                max_reports_per_month=9999,
                show_advanced_charts=True,
                show_recurring_monitoring=True,
                show_full_recommendations=True,
            )

        subscription = cls.get_or_create_subscription(db, user_id)
        tier = subscription.plan_tier if subscription.status in {"active", "trialing", "past_due"} else "free"

        if tier in {"premium", "agency"}:
            return Entitlements(
                plan_tier=tier,
                max_ad_accounts=50,
                max_findings=1000,
                max_recommendations=1000,
                max_history_items=200,
                max_trend_points=90,
                max_reports_per_month=9999,
                show_advanced_charts=True,
                show_recurring_monitoring=True,
                show_full_recommendations=True,
            )

        return Entitlements(
            plan_tier="free",
            max_ad_accounts=settings.free_max_ad_accounts,
            max_findings=settings.free_max_findings,
            max_recommendations=settings.free_max_recommendations,
            max_history_items=settings.free_max_history_items,
            max_trend_points=settings.free_max_trend_points,
            max_reports_per_month=settings.free_max_reports_per_month,
            show_advanced_charts=False,
            show_recurring_monitoring=False,
            show_full_recommendations=False,
        )

    @classmethod
    def set_plan_tier_local(cls, db: Session, user_id: str, plan_tier: str) -> Subscription:
        if plan_tier not in {"free", "premium", "agency"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"detail": "Invalid plan tier", "code": "INVALID_PLAN_TIER"},
            )

        subscription = cls.get_or_create_subscription(db, user_id)
        subscription.plan_tier = plan_tier
        subscription.status = "active"
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription

    @classmethod
    def enforce_report_quota(cls, db: Session, user_id: str, entitlements: Entitlements) -> None:
        if settings.debug or entitlements.is_premium:
            return

        runs_count = cls.get_reports_used_last_30_days(db, user_id)
        if runs_count >= entitlements.max_reports_per_month:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "detail": f"Free plan report limit reached ({runs_count}/{entitlements.max_reports_per_month} in 30 days)",
                    "code": "FREE_REPORT_LIMIT_REACHED",
                },
            )
