import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.deps import get_current_user
from app.models.user import User
from app.schemas.billing import DevPlanUpdateRequest, EntitlementsResponse, SubscriptionStatusResponse
from app.services.entitlements import EntitlementService
router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/status", response_model=SubscriptionStatusResponse)
def get_billing_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subscription = EntitlementService.get_or_create_subscription(db, current_user.id)
    return SubscriptionStatusResponse(
        plan_tier=subscription.plan_tier,
        status=subscription.status,
        cancel_at_period_end=subscription.cancel_at_period_end,
        current_period_end=subscription.current_period_end.isoformat() if subscription.current_period_end else None,
    )


@router.get("/entitlements", response_model=EntitlementsResponse)
def get_entitlements(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ent = EntitlementService.get_entitlements(db, current_user.id)
    used = EntitlementService.get_reports_used_last_30_days(db, current_user.id)
    remaining = max(ent.max_reports_per_month - used, 0)
    return EntitlementsResponse(
        **ent.__dict__,
        reports_used_last_30_days=used,
        reports_remaining_last_30_days=remaining,
    )


@router.post("/dev/plan", response_model=SubscriptionStatusResponse)
def switch_plan_local(
    payload: DevPlanUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "detail": "Local plan switching is only enabled in non-production environments",
                "code": "DEV_PLAN_SWITCH_DISABLED",
            },
        )

    subscription = EntitlementService.set_plan_tier_local(db, current_user.id, payload.plan_tier)
    return SubscriptionStatusResponse(
        plan_tier=subscription.plan_tier,
        status=subscription.status,
        cancel_at_period_end=subscription.cancel_at_period_end,
        current_period_end=subscription.current_period_end.isoformat() if subscription.current_period_end else None,
    )
