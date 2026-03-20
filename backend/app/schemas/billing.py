from typing import Literal

from pydantic import BaseModel


class SubscriptionStatusResponse(BaseModel):
    plan_tier: Literal["free", "premium", "agency"]
    status: Literal["active", "trialing", "past_due", "canceled", "incomplete"]
    cancel_at_period_end: bool
    current_period_end: str | None


class EntitlementsResponse(BaseModel):
    plan_tier: Literal["free", "premium", "agency"]
    max_ad_accounts: int
    max_findings: int
    max_recommendations: int
    max_history_items: int
    max_trend_points: int
    max_reports_per_month: int
    show_advanced_charts: bool
    show_recurring_monitoring: bool
    show_full_recommendations: bool
    reports_used_last_30_days: int
    reports_remaining_last_30_days: int


class DevPlanUpdateRequest(BaseModel):
    plan_tier: Literal["free", "premium", "agency"]
