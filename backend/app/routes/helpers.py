from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.services.meta_ads import MetaAdsService
from app.services.meta_auth import MetaAuthService


def get_selected_account(db: Session, user_id: str):
    """Return the selected Meta ad account for a user, or raise HTTPException."""
    connection = MetaAuthService.get_connection(db, user_id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": "No Meta connection", "code": "META_NOT_CONNECTED"},
        )
    account = MetaAdsService.get_selected_account(db, connection.id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": "No ad account selected", "code": "META_ACCOUNT_NOT_SELECTED"},
        )
    return account
