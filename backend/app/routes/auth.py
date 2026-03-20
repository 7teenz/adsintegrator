from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.middleware.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    AuthMessageResponse,
    AuthSuccessResponse,
    ForgotPasswordRequest,
    LoginRequest,
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
from app.services.email import send_reset_email, send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


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
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "Email already registered", "code": "EMAIL_ALREADY_REGISTERED"},
        )

    verify_token = generate_verify_token()
    user = create_user(db, payload, verify_token=verify_token)
    try:
        send_verification_email(user.email, verify_token)
    except Exception:
        pass

    return AuthMessageResponse(message="Check your email to verify your account")


@router.post("/login", response_model=AuthSuccessResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
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
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, payload.email)
    if user:
        token = generate_verify_token()
        user.email_verify_token = token
        db.commit()
        try:
            send_reset_email(user.email, token)
        except Exception:
            pass

    return AuthMessageResponse(message="If that email exists, a reset link has been sent")


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
