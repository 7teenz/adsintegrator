from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.logging_config import get_logger
from app.middleware.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    AuthMessageResponse,
    AuthSuccessResponse,
    ForgotPasswordRequest,
    LoginRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    UserCreate,
    UserResponse,
    VerifyEmailResponse,
)
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_user,
    generate_verify_token,
    get_user_by_email,
    hash_password,
)
from app.services.account_cleanup import AccountCleanupService
from app.services.email import send_reset_email, send_verification_email
from app.services.email import EmailDeliveryError, build_verification_url
from app.services.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
logger = get_logger(__name__)


def _is_local_frontend() -> bool:
    frontend_url = settings.frontend_app_url.lower()
    return "localhost" in frontend_url or "127.0.0.1" in frontend_url


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.environment.lower() == "production",
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


@router.post("/register", response_model=AuthMessageResponse, status_code=status.HTTP_201_CREATED)
def register(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    enforce_rate_limit(request, "auth:register", settings.rate_limit_auth_requests, settings.rate_limit_auth_window_seconds)
    if get_user_by_email(db, payload.email):
        logger.warning("auth.register_conflict", extra={"request_id": getattr(request.state, "request_id", None), "code": "EMAIL_ALREADY_REGISTERED"})
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "Email already registered", "code": "EMAIL_ALREADY_REGISTERED"},
        )

    verify_token = generate_verify_token()
    user = create_user(db, payload, verify_token=verify_token)
    try:
        send_verification_email(user.email, verify_token)
    except EmailDeliveryError:
        logger.exception(
            "auth.register_email_failed",
            extra={"request_id": getattr(request.state, "request_id", None), "user_id": user.id, "code": "EMAIL_DELIVERY_UNAVAILABLE"},
        )
        if _is_local_frontend():
            return AuthMessageResponse(
                message="Email delivery is not configured locally. Use the verification link below to finish setup.",
                verification_url=build_verification_url(verify_token),
            )
        db.delete(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "detail": "Verification email could not be sent. Registration was not completed.",
                "code": "EMAIL_DELIVERY_UNAVAILABLE",
            },
        )

    return AuthMessageResponse(message="Check your email to verify your account")


@router.post("/login", response_model=AuthSuccessResponse)
def login(request: Request, payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    enforce_rate_limit(request, "auth:login", settings.rate_limit_auth_requests, settings.rate_limit_auth_window_seconds)
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        logger.warning(
            "auth.login_invalid",
            extra={"request_id": getattr(request.state, "request_id", None), "code": "AUTH_INVALID_CREDENTIALS"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid credentials", "code": "AUTH_INVALID_CREDENTIALS"},
        )
    if not user.email_verified and not settings.debug:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "Email not verified", "code": "EMAIL_NOT_VERIFIED"},
        )

    token = create_access_token(data={"sub": user.id})
    _set_auth_cookie(response, token)
    return AuthSuccessResponse(user=UserResponse.model_validate(user))


@router.post("/logout", response_model=AuthMessageResponse)
def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return AuthMessageResponse(message="Logged out")


@router.get("/verify-email", response_model=VerifyEmailResponse)
def verify_email(token: str, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email_verify_token == token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": "Invalid or expired token", "code": "VERIFY_INVALID"},
        )

    user.email_verified = True
    user.email_verify_token = None
    db.commit()
    db.refresh(user)

    jwt_token = create_access_token(data={"sub": user.id})
    _set_auth_cookie(response, jwt_token)
    return VerifyEmailResponse(verified=True, user=UserResponse.model_validate(user))


@router.post("/forgot-password", response_model=AuthMessageResponse)
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    enforce_rate_limit(request, "auth:forgot_password", settings.rate_limit_auth_requests, settings.rate_limit_auth_window_seconds)
    user = get_user_by_email(db, payload.email)
    if user:
        token = generate_verify_token()
        user.email_verify_token = token
        db.commit()
        try:
            send_reset_email(user.email, token)
        except Exception:
            logger.exception(
                "auth.forgot_password_email_failed",
                extra={"request_id": getattr(request.state, "request_id", None), "user_id": user.id, "code": "EMAIL_DELIVERY_UNAVAILABLE"},
            )

    return AuthMessageResponse(message="If that email exists, a reset link has been sent")


@router.post("/resend-verification", response_model=AuthMessageResponse)
def resend_verification(request: Request, payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    enforce_rate_limit(request, "auth:resend_verification", settings.rate_limit_auth_requests, settings.rate_limit_auth_window_seconds)
    user = get_user_by_email(db, payload.email)
    if not user:
        return AuthMessageResponse(message="If that email exists, a verification link has been sent")
    if user.email_verified:
        return AuthMessageResponse(message="Email is already verified")

    token = user.email_verify_token or generate_verify_token()
    user.email_verify_token = token
    db.commit()

    try:
        send_verification_email(user.email, token)
    except EmailDeliveryError:
        logger.exception(
            "auth.resend_verification_failed",
            extra={"request_id": getattr(request.state, "request_id", None), "user_id": user.id, "code": "EMAIL_DELIVERY_UNAVAILABLE"},
        )
        if _is_local_frontend():
            return AuthMessageResponse(
                message="Email delivery is not configured locally. Use the verification link below to finish setup.",
                verification_url=build_verification_url(token),
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "detail": "Verification email could not be sent.",
                "code": "EMAIL_DELIVERY_UNAVAILABLE",
            },
        )

    return AuthMessageResponse(message="Verification email sent")


@router.post("/reset-password", response_model=AuthMessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email_verify_token == payload.token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": "Invalid or expired token", "code": "RESET_INVALID"},
        )

    user.hashed_password = hash_password(payload.new_password)
    user.email_verify_token = None
    db.commit()
    return AuthMessageResponse(message="Password updated")


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.delete("/data", response_model=AuthMessageResponse)
def delete_my_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    summary = AccountCleanupService.clear_user_data(db, current_user)
    logger.info(
        "account.data_deleted",
        extra={"request_id": getattr(request.state, "request_id", None), "user_id": current_user.id, "code": "ACCOUNT_DATA_DELETED"},
    )
    return AuthMessageResponse(message=summary.message)


@router.delete("/account", response_model=AuthMessageResponse)
def delete_my_account(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    summary = AccountCleanupService.delete_user_account(db, current_user)
    response.delete_cookie("access_token", path="/")
    logger.info(
        "account.deleted",
        extra={"request_id": getattr(request.state, "request_id", None), "user_id": current_user.id, "code": "ACCOUNT_DELETED"},
    )
    return AuthMessageResponse(message=summary.message)
