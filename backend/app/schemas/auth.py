from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    model_config = {"str_strip_whitespace": True}


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    is_active: bool
    email_verified: bool

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    model_config = {"str_strip_whitespace": True}


class AuthMessageResponse(BaseModel):
    message: str
    verification_url: str | None = None


class AuthSuccessResponse(BaseModel):
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    model_config = {"str_strip_whitespace": True}


class ResendVerificationRequest(BaseModel):
    email: EmailStr
    model_config = {"str_strip_whitespace": True}


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class VerifyEmailResponse(BaseModel):
    verified: bool
    user: UserResponse
