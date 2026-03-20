import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.middleware.deps import get_current_user
from app.models.user import User
from app.schemas.meta import (
    AdAccountSelectRequest,
    MetaAdAccountResponse,
    MetaAuthURL,
    MetaCallbackRequest,
    MetaConnectionResponse,
    MetaConnectionStatus,
)
from app.services.entitlements import EntitlementService
from app.services.meta_ads import MetaAdsService
from app.services.meta_auth import MetaAuthService

settings = get_settings()
router = APIRouter(prefix="/meta", tags=["meta"])
MOCK_MODE = settings.meta_app_id == "mock"


def _connection_to_response(connection, db: Session) -> MetaConnectionResponse:
    selected_account = MetaAdsService.get_selected_account(db, connection.id)
    return MetaConnectionResponse(
        id=connection.id,
        meta_user_id=connection.meta_user_id or "",
        meta_user_name=connection.meta_user_name,
        token_expires_at=connection.token_expires_at,
        scopes=connection.scopes,
        created_at=connection.created_at,
        has_selected_account=selected_account is not None,
    )


@router.get("/auth-url", response_model=MetaAuthURL)
def get_auth_url(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        url = MetaAuthService.create_authorization_request(db, current_user.id, settings.meta_redirect_uri)
        if MOCK_MODE:
            return MetaAuthURL(url=f"{settings.meta_redirect_uri}?code=mock_code&state=mock_state")
        return MetaAuthURL(url=url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/callback", response_model=MetaConnectionResponse)
async def oauth_callback(
    payload: MetaCallbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entitlements = EntitlementService.get_entitlements(db, current_user.id)
    try:
        if MOCK_MODE:
            if payload.state != "mock_state":
                MetaAuthService.validate_state(db, current_user.id, payload.state)
            token_data = {
                "access_token": "mock_long_lived_token_abc123",
                "expires_in": 5184000,
                "meta_user_id": "10000000000001",
                "meta_user_name": "Test Advertiser",
                "scopes": settings.meta_oauth_scopes,
            }
            connection = MetaAuthService.save_connection(db, current_user.id, token_data)
            from app.services.meta_mock import MOCK_AD_ACCOUNTS

            MetaAdsService.sync_ad_accounts(
                db,
                connection,
                MOCK_AD_ACCOUNTS,
                max_accounts=entitlements.max_ad_accounts,
            )
            return _connection_to_response(connection, db)

        MetaAuthService.validate_state(db, current_user.id, payload.state)
        token_data = await MetaAuthService.exchange_code(payload.code, settings.meta_redirect_uri)
        connection = MetaAuthService.save_connection(db, current_user.id, token_data)
        access_token = MetaAuthService.get_access_token(connection)
        ad_accounts = await MetaAdsService.fetch_ad_accounts(access_token)
        MetaAdsService.sync_ad_accounts(
            db,
            connection,
            ad_accounts,
            max_accounts=entitlements.max_ad_accounts,
        )
        return _connection_to_response(connection, db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": str(exc), "code": "META_OAUTH_INVALID_REQUEST"},
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": "Meta OAuth exchange failed", "code": "META_OAUTH_EXCHANGE_FAILED"},
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": "Meta connection failed", "code": "META_CONNECTION_FAILED"},
        ) from exc


@router.get("/connection", response_model=MetaConnectionStatus)
def get_connection(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    connection = MetaAuthService.get_connection(db, current_user.id)
    if not MetaAuthService.is_connected(connection):
        return MetaConnectionStatus(connected=False)
    return MetaConnectionStatus(connected=True, connection=_connection_to_response(connection, db))


@router.delete("/connection", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deleted = MetaAuthService.delete_connection(db, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "No connection found", "code": "META_CONNECTION_NOT_FOUND"},
        )


@router.get("/ad-accounts", response_model=list[MetaAdAccountResponse])
def list_ad_accounts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entitlements = EntitlementService.get_entitlements(db, current_user.id)
    connection = MetaAuthService.get_connection(db, current_user.id)
    if not MetaAuthService.is_connected(connection):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "No Meta connection", "code": "META_NOT_CONNECTED"},
        )
    accounts = MetaAdsService.get_ad_accounts(db, connection.id)
    return [MetaAdAccountResponse.model_validate(account) for account in accounts[: entitlements.max_ad_accounts]]


@router.post("/ad-accounts/refresh", response_model=list[MetaAdAccountResponse])
async def refresh_ad_accounts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entitlements = EntitlementService.get_entitlements(db, current_user.id)
    connection = MetaAuthService.get_connection(db, current_user.id)
    if not MetaAuthService.is_connected(connection):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "No Meta connection", "code": "META_NOT_CONNECTED"},
        )

    if MOCK_MODE:
        from app.services.meta_mock import MOCK_AD_ACCOUNTS

        accounts = MetaAdsService.sync_ad_accounts(
            db,
            connection,
            MOCK_AD_ACCOUNTS,
            max_accounts=entitlements.max_ad_accounts,
        )
    else:
        access_token = MetaAuthService.get_access_token(connection)
        raw_accounts = await MetaAdsService.fetch_ad_accounts(access_token)
        accounts = MetaAdsService.sync_ad_accounts(
            db,
            connection,
            raw_accounts,
            max_accounts=entitlements.max_ad_accounts,
        )

    return [MetaAdAccountResponse.model_validate(account) for account in accounts]


@router.post("/ad-accounts/select", response_model=MetaAdAccountResponse)
def select_ad_account(
    payload: AdAccountSelectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entitlements = EntitlementService.get_entitlements(db, current_user.id)
    connection = MetaAuthService.get_connection(db, current_user.id)
    if not MetaAuthService.is_connected(connection):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "No Meta connection", "code": "META_NOT_CONNECTED"},
        )

    allowed_accounts = MetaAdsService.get_ad_accounts(db, connection.id)[: entitlements.max_ad_accounts]
    allowed_ids = {item.account_id for item in allowed_accounts}
    if payload.account_id not in allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "detail": "This ad account is not available on your current plan",
                "code": "AD_ACCOUNT_PLAN_RESTRICTED",
            },
        )

    selected = MetaAdsService.select_ad_account(db, connection.id, payload.account_id)
    if selected is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": f"Ad account {payload.account_id} not found", "code": "AD_ACCOUNT_NOT_FOUND"},
        )
    return MetaAdAccountResponse.model_validate(selected)
